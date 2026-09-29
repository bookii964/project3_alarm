r"""
재생기: 논리적 날짜를 계산해 그날 도착할 데이터를 만든다.

동작
  1. ANCHOR(가동 시작일)와 배치 날짜의 차이로 재생 일차를 구한다
  2. day_index 에 해당하는 논리 날짜의 dated 행을 꺼낸다
  3. 원본 결측률에 맞는 개수만큼 undated 풀에서 꺼내 섞는다
  4. batch_date 컬럼을 붙인다 (이벤트 날짜는 원본 그대로 유지)

상태 파일을 쓰지 않는다. 실제 날짜에서 계산하므로 로컬과 Actions가
항상 같은 결과를 내고, --date 로 과거 배치를 다시 만들 수 있다.

사용:
    python src/replay.py                    # 오늘 배치
    python src/replay.py --date 2026-09-25  # 특정 날짜 (백필)
    python src/replay.py --dry-run          # 건수만 확인
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source"
OUT = ROOT / "data" / "batch"

# 파이프라인 가동 시작일. 이 날이 재생 0일차
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


def pick_undated(pool: pd.DataFrame, day_index: int, n_needed: int,
                 offset: int) -> pd.DataFrame:
    """undated 풀에서 n_needed 행을 꺼낸다.

    풀 전체를 고정 시드로 한 번 섞은 뒤 offset 위치부터 순차 소비한다.
    offset 은 앞선 날들이 소비한 누적량이므로 날짜 간 중복이 없다.
    (day_index * n_needed 로 계산하면 n_needed 가 날마다 달라 구간이 겹친다)
    끝에 도달하면 앞에서 이어 붙인다.
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

    if not args.dry_run:
        OUT.mkdir(parents=True, exist_ok=True)

    total = 0

    # --- 이벤트 테이블 ---
    for table, col in EVENTS:
        dated = pd.read_parquet(SRC / f"{table}_dated.parquet")
        dated_dates = pd.to_datetime(dated[col]).dt.date
        today_rows = dated[dated_dates == logical]

        rate = NULL_RATES[table]
        n_null = round(len(today_rows) * rate / (1 - rate))

        # 앞선 날들이 소비한 누적량을 구해 시작 위치로 삼는다.
        # 각 날짜의 dated 건수로부터 그날의 n_null 을 되계산한다.
        offset = 0
        for d in range(day_index):
            prev = REPLAY_START + timedelta(days=d)
            n_prev = int((dated_dates == prev).sum())
            offset += round(n_prev * rate / (1 - rate))

        pool = pd.read_parquet(SRC / f"{table}_undated.parquet")
        today_null = pick_undated(pool, day_index, n_null, offset)

        df = pd.concat([today_rows, today_null], ignore_index=True)
        df["batch_date"] = batch_date

        actual = len(today_null) / len(df) if len(df) else 0
        print(f"  {table:22s} {len(today_rows):6,d} + NULL {len(today_null):5,d} "
              f"= {len(df):6,d}행  (결측률 {actual:.1%})")

        if not args.dry_run:
            df.to_parquet(OUT / f"{table}.parquet", index=False)
        total += len(df)

    # --- 증분 마스터: 그날 가입한 고객과 그 기기 ---
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