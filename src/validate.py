r"""
검증기: 배치 데이터를 룰에 통과시켜 정상/격리로 나눈다.

출력 세 가지
  data/batch/clean/*.parquet   통과한 행 → load.py 가 적재
  quarantine.rejected_rows     걸린 행 + 사유 (jsonb)
  mart.dq_daily                룰별 검사 결과 시계열

룰 구분
  격리(BLOCK) : 행 단위. 해당 행만 빼고 나머지는 정상 적재
  경고(WARN)  : 집합 단위. 적재는 그대로 하되 기록

참조 무결성 확인 방식(B+C):
  DB에서 id 컬럼만 조회(가벼움) + 이번 배치의 신규 마스터를 합쳐 대조.
  오늘 가입한 고객의 오늘 주문은 유효해야 하므로 둘 다 필요하다.

사용:
    python src/validate.py dev
    python src/validate.py dev --date 2026-10-01
"""
import argparse
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BATCH = ROOT / "data" / "batch"
CLEAN = BATCH / "clean"
BASELINE = yaml.safe_load((ROOT / "config" / "baseline.yml").read_text(encoding="utf-8"))

TARGETS = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}

TABLES = ["crm_customers", "crm_customer_devices", "orders",
          "support_tickets", "clickstream"]

PK = {
    "crm_customers": ["customer_id"],
    "crm_customer_devices": ["customer_id", "device_id"],
    "orders": ["order_id"],
    "support_tickets": ["ticket_id"],
    "clickstream": ["event_id"],
}

# (룰ID, 대상테이블, 검사할 컬럼, 참조 대상)
FK_RULES = [
    ("X01", "orders", "customer_id", "crm_customers"),
    ("X02", "orders", "product_id", "product_catalog"),
    ("X03", "support_tickets", "customer_id", "crm_customers"),
    ("X04", "clickstream", "customer_id", "crm_customers"),
    ("X05", "clickstream", "product_id", "product_catalog"),
    ("X06", "crm_customer_devices", "customer_id", "crm_customers"),
]


class Result:
    """검사 결과를 모은다."""

    def __init__(self):
        self.checks: list[dict] = []
        self.rejects: list[dict] = []

    def check(self, table, rule_id, metric, value, baseline=None,
              threshold=None, status="PASS", column=""):
        self.checks.append(dict(
            table_name=table, rule_id=rule_id, column_name=column,
            metric=metric, value=value, baseline=baseline,
            threshold=threshold, status=status))

    def reject(self, table, rule_id, reason, rows: pd.DataFrame):
        # pandas 의 NaN/NaT 는 json.dumps 에서 "NaN" 이라는 글자가 되는데
        # JSON 표준에 NaN 은 없어 jsonb 캐스팅이 실패한다.
        # None 으로 바꿔 null 로 직렬화되게 한다.
        safe = rows.astype(object).where(pd.notna(rows), None)
        for rec in safe.to_dict("records"):
            self.rejects.append(dict(
                table_name=table, rule_id=rule_id, reason=reason,
                payload=json.dumps(rec, default=str, ensure_ascii=False)))


def load_ref_ids(engine, batch: dict[str, pd.DataFrame]) -> dict[str, set]:
    """참조 대상 id 집합을 만든다 (DB의 기존 + 이번 배치의 신규)."""
    refs = {}
    with engine.connect() as conn:
        for table, col in [("crm_customers", "customer_id"),
                           ("product_catalog", "product_id")]:
            rows = conn.execute(text(f"SELECT {col} FROM raw.{table}")).scalars()
            ids = {str(r) for r in rows}
            # 이번 배치에 들어올 신규 마스터도 유효한 참조 대상
            if table in batch:
                ids |= set(batch[table][col].dropna().astype(str))
            refs[table] = ids
            print(f"  참조 {table:22s} {len(ids):8,d}건")
    return refs


def validate(batch: dict[str, pd.DataFrame], refs: dict[str, set],
             res: Result) -> dict[str, pd.DataFrame]:
    clean = {}

    for table in TABLES:
        if table not in batch:
            print(f"  {table:22s} 파일 없음 — 건너뜀")
            continue

        # 인덱스를 0부터 다시 매겨 마스크 연산이 어긋나지 않게 한다
        df = batch[table].copy().reset_index(drop=True)
        n0 = len(df)
        base = BASELINE.get(table, {})

        # 격리 대상을 인덱스가 아니라 불리언 마스크로 누적한다.
        # 인덱스는 파일 왕복이나 필터링 과정에서 어긋나기 쉽다.
        drop_mask = pd.Series(False, index=df.index)

        # --- C05: 적재 0건 ---
        if n0 == 0:
            res.check(table, "C05", "row_count", 0, base.get("row_count"),
                      status="FAIL")
            clean[table] = df
            print(f"  {table:22s} {0:7,d}행  (적재 없음)")
            continue

        # --- C03: PK 중복 → 격리 ---
        dup_mask = df.duplicated(subset=PK[table], keep="first")
        if dup_mask.any():
            res.reject(table, "C03", "PK 중복", df[dup_mask])
            drop_mask |= dup_mask
        res.check(table, "C03", "dup_count", int(dup_mask.sum()), 0,
                  status="FAIL" if dup_mask.any() else "PASS")

        # --- X0n: 참조 무결성 → 격리 ---
        for rule_id, t, col, ref_table in FK_RULES:
            if t != table or col not in df.columns:
                continue
            valid = refs[ref_table]
            # pandas 의 string 타입은 .astype(str) 시 결측을 '<NA>' 로 바꾼다.
            # 결측을 먼저 제외한 뒤 문자열 비교를 수행한다.
            col_str = df[col].where(df[col].notna()).map(
                lambda v: str(v) if pd.notna(v) else None)
            bad_mask = col_str.notna() & ~col_str.isin(valid)
            if bad_mask.any():
                res.reject(table, rule_id, f"{col} 가 {ref_table} 에 없음",
                           df[bad_mask])
                drop_mask |= bad_mask
            res.check(table, rule_id, "orphan_count", int(bad_mask.sum()), 0,
                      status="FAIL" if bad_mask.any() else "PASS", column=col)

        # --- D01: NULL률 ---
        tol = BASELINE["tolerance"]["null_rate_pp"]
        for col, expected in base.get("null_rate", {}).items():
            if col not in df.columns:
                continue
            actual = float(df[col].isna().mean())
            over = abs(actual - expected) > tol
            res.check(table, "D01", "null_rate", round(actual, 4), expected,
                      tol, "WARN" if over else "PASS", column=col)

        # --- D02: 범주형 신규 값 → 격리 ---
        # 경고로만 두면 DB CHECK 제약에 걸려 배치 전체가 실패한다.
        # 격리해야 나머지 행이 정상 적재되고 파이프라인이 살아남는다.
        for col, allowed in base.get("categories", {}).items():
            if col not in df.columns:
                continue
            bad_mask = df[col].notna() & ~df[col].astype(str).isin(allowed)
            new = set(df.loc[bad_mask, col].astype(str).unique())
            if bad_mask.any():
                res.reject(table, "D02",
                           f"{col} 에 허용되지 않은 값: {sorted(new)[:5]}",
                           df[bad_mask])
                drop_mask |= bad_mask
            res.check(table, "D02", "new_values", len(new), 0,
                      status="FAIL" if new else "PASS", column=col)

        # --- D05: 적재량 급변 ---
        expected_n = base.get("row_count")
        if expected_n:
            ratio = abs(n0 - expected_n) / expected_n
            limit = BASELINE["tolerance"]["row_count_ratio"]
            res.check(table, "D05", "row_count", n0, expected_n, limit,
                      "WARN" if ratio > limit else "PASS")

                # --- D08: 격리 비율 ---
        # 비율과 절대 건수를 모두 초과해야 FAIL 로 판정한다.
        # 비율만 쓰면 support_tickets(일 40건)에서 3건만 걸려도 7.5%가 되어
        # clickstream(5,400건)의 77건(1.4%)보다 심각해 보이는 왜곡이 생긴다.
        n_drop = int(drop_mask.sum())
        rate = n_drop / n0
        tol = BASELINE["tolerance"]
        over = (rate > tol["quarantine_rate"]
                and n_drop >= tol.get("quarantine_min_count", 0))
        res.check(table, "D08", "quarantine_rate", round(rate, 4), 0.0,
                  tol["quarantine_rate"], "FAIL" if over else "PASS")

        clean[table] = df[~drop_mask].copy()
        print(f"  {table:22s} {n0:7,d} → {len(clean[table]):7,d}행  "
              f"(격리 {n_drop:,d})")

    return clean


def write_results(engine, batch_date: date, res: Result) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mart.dq_daily WHERE batch_date = :d"),
                     {"d": batch_date})
        conn.execute(text("DELETE FROM quarantine.rejected_rows "
                          "WHERE batch_date = :d"), {"d": batch_date})

        if res.checks:
            df = pd.DataFrame(res.checks)
            df["batch_date"] = batch_date
            df.to_sql("dq_daily", conn, schema="mart",
                      if_exists="append", index=False)

        if res.rejects:
            # payload 는 jsonb 컬럼이므로 문자열을 명시적으로 캐스팅한다.
            # to_sql 은 이 캐스팅을 지원하지 않아 직접 INSERT 한다.
            sql = text(
                "INSERT INTO quarantine.rejected_rows "
                "(batch_date, table_name, rule_id, reason, payload) "
                "VALUES (:batch_date, :table_name, :rule_id, :reason, "
                "        CAST(:payload AS jsonb))")
            conn.execute(sql, [dict(r, batch_date=batch_date)
                               for r in res.rejects])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["dev", "main"])
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    engine = create_engine(os.environ[TARGETS[args.target]])
    batch_date = args.date
    print(f"대상: {args.target}   배치 날짜: {batch_date}\n")

    batch = {t: pd.read_parquet(BATCH / f"{t}.parquet")
             for t in TABLES if (BATCH / f"{t}.parquet").exists()}

    # data/batch 는 마지막 replay 결과만 담는다.
    # 다른 날짜의 파일을 검증하는 사고를 막는다.
    for t, df in batch.items():
        if "batch_date" in df.columns and len(df):
            file_date = pd.to_datetime(df["batch_date"].iloc[0]).date()
            if file_date != batch_date:
                raise SystemExit(
                    f"{t}.parquet 의 batch_date 가 {file_date} 입니다. "
                    f"{batch_date} 를 검증하려면 replay 를 먼저 실행하세요.")

    print("[참조 대상 로드]")
    refs = load_ref_ids(engine, batch)

    print("\n[검증]")
    res = Result()
    clean = validate(batch, refs, res)

    CLEAN.mkdir(parents=True, exist_ok=True)
    for table, df in clean.items():
        df.to_parquet(CLEAN / f"{table}.parquet", index=False)

    write_results(engine, batch_date, res)

    fails = [c for c in res.checks if c["status"] in ("FAIL", "WARN")]
    print(f"\n검사 {len(res.checks)}건, 격리 {len(res.rejects)}행")
    if fails:
        print("\n[주의]")
        for c in fails:
            col = f".{c['column_name']}" if c["column_name"] else ""
            print(f"  {c['status']:4s} {c['rule_id']} {c['table_name']}{col} "
                  f"— {c['metric']}={c['value']} (기준 {c['baseline']})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n실패: {type(e).__name__}")
        print(str(e)[:600])
        raise SystemExit(1)