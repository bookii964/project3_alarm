r"""
재생기: 논리적 날짜를 계산해 그날 도착할 데이터를 만든다.

동작
  1. ANCHOR(가동 시작일)와 배치 날짜의 차이로 재생 일차를 구한다
  2. day_index 에 해당하는 논리 날짜의 dated 행을 꺼낸다
  3. 원본 결측률에 맞는 개수만큼 undated 풀에서 꺼내 섞는다
  4. config/scenarios.yml 에 해당 날짜 시나리오가 있으면 오염을 주입한다
  5. batch_date 컬럼을 붙인다 (이벤트 날짜는 원본 그대로 유지)

상태 파일을 쓰지 않는다. 실제 날짜에서 계산하므로 로컬과 Actions가
항상 같은 결과를 내고, --date 로 과거 배치를 다시 만들 수 있다.

사용:
    python -B src/replay.py
    python -B src/replay.py --date 2026-10-05
    python -B src/replay.py --dry-run
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source"
OUT = ROOT / "data" / "batch"
SCENARIOS = ROOT / "config" / "scenarios.yml"

# 파이프라인 가동 시작일. 이 날이 재생 1일차
ANCHOR = date(2026, 9, 28)

# 원본 재생 구간
REPLAY_START = date(2025, 9, 2)
CYCLE_DAYS = 92

# undated 풀을 섞을 때 쓰는 고정 시드. 재현성 확보용
SHUFFLE_SEED = 42

# 원본 결측률. 이 비율을 유지해야 D01 룰의 기준선이 성립한다
NULL_RATES = {
    "orders": 0.300,
    "support_tickets": 0.090,
    "clickstream": 0.120,
}

EVENTS = [
    ("orders", "order_date"),
    ("support_tickets", "ticket_created"),
    ("clickstream", "event_time"),
]



def resolve_day(batch_date: date) -> tuple[int, int, date]:
    """배치 날짜로부터 (회차, 일차, 논리 날짜)를 구한다."""
    elapsed = (batch_date - ANCHOR).days
    if elapsed < 0:
        raise ValueError(f"가동 시작일({ANCHOR}) 이전 날짜입니다: {batch_date}")
    cycle, day_index = divmod(elapsed, CYCLE_DAYS)
    return cycle + 1, day_index, REPLAY_START + timedelta(days=day_index)


def pick_undated(pool: pd.DataFrame, n_needed: int, offset: int) -> pd.DataFrame:
    """undated 풀에서 n_needed 행을 꺼낸다.

    풀 전체를 고정 시드로 한 번 섞은 뒤 offset 위치부터 순차 소비한다.
    offset 은 앞선 날들이 소비한 누적량이므로 날짜 간 중복이 없다.
    """
    if pool.empty or n_needed <= 0:
        return pool.iloc[0:0]

    shuffled = pool.sample(frac=1, random_state=SHUFFLE_SEED).reset_index(drop=True)
    start = offset % len(shuffled)
    end = start + n_needed

    if end <= len(shuffled):
        return shuffled.iloc[start:end].copy()
    return pd.concat(
        [shuffled.iloc[start:], shuffled.iloc[: end - len(shuffled)]],
        ignore_index=True,
    )


def load_scenarios(batch_date: date) -> list[dict]:
    """해당 날짜에 적용할 시나리오를 읽는다."""
    if not SCENARIOS.exists():
        return []
    cfg = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8")) or {}
    return [s for s in cfg.get("scenarios", [])
            if s.get("date") == batch_date]


def inject(df: pd.DataFrame, sc: dict, seed: int) -> pd.DataFrame:
    """시나리오 한 건을 데이터에 적용한다.

    원본 parquet 은 건드리지 않고 이번 배치 사본에만 적용한다.
    시드를 날짜로 고정해 같은 날짜를 재실행하면 같은 결과가 나온다.
    """
    kind = sc["type"]
    df = df.copy()

    if kind == "inject_category":
        n = min(sc["count"], len(df))
        idx = df.sample(n=n, random_state=seed).index
        df.loc[idx, sc["column"]] = sc["value"]
        print(f"    [주입] {sc['column']} = '{sc['value']}' × {n}행")

    elif kind == "null_out":
        idx = df.sample(frac=sc["rate"], random_state=seed).index
        df.loc[idx, sc["column"]] = None
        if sc.get("flag_column"):
            df.loc[idx, sc["flag_column"]] = sc["flag_value"]
        print(f"    [주입] {sc['column']} 결측 {len(idx)}행 추가")

    elif kind == "shrink":
        before = len(df)
        df = df.sample(frac=sc["rate"], random_state=seed)
        print(f"    [주입] 적재량 {sc['rate']:.0%}로 축소 "
              f"({before:,d} → {len(df):,d}행)")

    else:
        print(f"    [주입] 알 수 없는 유형: {kind} — 건너뜀")

    return df




def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    batch_date = args.date
    cycle, day_index, logical = resolve_day(batch_date)

    print(f"배치 날짜   {batch_date}")
    print(f"재생 위치   {cycle}회차 {day_index + 1}/{CYCLE_DAYS}일차")
    print(f"논리 날짜   {logical}\n")

    scenarios = load_scenarios(batch_date)
    if scenarios:
        print(f"[시나리오] {len(scenarios)}건 적용")
        for sc in scenarios:
            col = f".{sc['column']}" if sc.get("column") else ""
            print(f"  - {sc['table']}{col} ({sc['type']})")
        print()

    if not args.dry_run:
        OUT.mkdir(parents=True, exist_ok=True)

    seed = int(batch_date.strftime("%Y%m%d")) % 100000
    total = 0

    for table, col in EVENTS:
        dated = pd.read_parquet(SRC / f"{table}_dated.parquet")
        dated_dates = pd.to_datetime(dated[col]).dt.date
        today_rows = dated[dated_dates == logical]

        rate = NULL_RATES[table]
        n_null = round(len(today_rows) * rate / (1 - rate))

        offset = 0
        for d in range(day_index):
            prev = REPLAY_START + timedelta(days=d)
            n_prev = int((dated_dates == prev).sum())
            offset += round(n_prev * rate / (1 - rate))

        pool = pd.read_parquet(SRC / f"{table}_undated.parquet")
        today_null = pick_undated(pool, n_null, offset)

        df = pd.concat([today_rows, today_null], ignore_index=True)
        df["batch_date"] = batch_date

        actual = len(today_null) / len(df) if len(df) else 0
        print(f"  {table:22s} {len(today_rows):6,d} + NULL {len(today_null):5,d} "
              f"= {len(df):6,d}행  (결측률 {actual:.1%})")

        for sc in scenarios:
            if sc.get("table") == table:
                df = inject(df, sc, seed)

        if not args.dry_run:
            df.to_parquet(OUT / f"{table}.parquet", index=False)
        total += len(df)

    cust = pd.read_parquet(SRC / "crm_customers_dated.parquet")
    today_cust = cust[pd.to_datetime(cust["signup_date"]).dt.date == logical].copy()
    today_cust["batch_date"] = batch_date

    devices = pd.read_parquet(SRC / "crm_customer_devices.parquet")
    today_dev = devices[devices["customer_id"].isin(today_cust["customer_id"])].copy()
    today_dev["batch_date"] = batch_date

    print(f"  {'crm_customers':22s} {len(today_cust):6,d}행")
    print(f"  {'crm_customer_devices':22s} {len(today_dev):6,d}행")

    if not args.dry_run:
        today_cust.to_parquet(OUT / "crm_customers.parquet", index=False)
        today_dev.to_parquet(OUT / "crm_customer_devices.parquet", index=False)
    total += len(today_cust) + len(today_dev)

    print(f"\n합계 {total:,d}행")
    print("(dry-run: 파일을 쓰지 않음)" if args.dry_run else f"→ {OUT}")


if __name__ == "__main__":
    main()