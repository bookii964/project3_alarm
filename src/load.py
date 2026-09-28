r"""
적재기: data/batch/ 의 Parquet을 Neon raw 스키마에 넣는다.

핵심 세 가지
  1. FK 순서 — 참조 대상을 먼저 넣는다
       product_catalog → crm_customers → devices → orders → tickets → clickstream
  2. 멱등성 — 트랜잭션 안에서 DELETE(batch_date) 후 INSERT.
       같은 날짜를 몇 번 돌려도 결과가 같다.
  3. COPY — 행마다 파라미터를 만드는 INSERT는 수만 행에서 매우 느리고
       실패 시 에러가 수십만 자가 된다. COPY는 CSV 스트림을 한 번에 보낸다.

초기 적재는 테이블별로 확인 후 비어 있을 때만 수행한다.
중간에 실패해도 다시 실행하면 남은 것부터 이어진다.

사용:
    python src/load.py dev
    python src/load.py dev --date 2026-10-01   # 백필
    python src/load.py main
"""
import argparse
import io
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SRC = ROOT / "data" / "source"
BATCH = ROOT / "data" / "batch"

TARGETS = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}

# FK 의존 순서. 이 순서를 바꾸면 적재가 실패한다
LOAD_ORDER = [
    "crm_customers",
    "crm_customer_devices",
    "orders",
    "support_tickets",
    "clickstream",
]

# 정수 컬럼. pandas는 NULL이 있는 정수 컬럼을 float로 승격시켜
# 4 를 4.0 으로 만들고, Postgres의 smallint/integer가 이를 거부한다.
# nullable 정수 타입(Int64)으로 되돌려 소수점을 없앤다.
INT_COLS = {
    "crm_customers": ["device_count"],
    "orders": ["quantity"],
    "clickstream": [],
    "support_tickets": [],
    "crm_customer_devices": [],
    "product_catalog": [],
}


def fix_int_cols(df: pd.DataFrame, table: str) -> pd.DataFrame:
    for col in INT_COLS.get(table, []):
        if col in df.columns:
            df[col] = df[col].astype("Int64")
    return df

def copy_df(conn, df: pd.DataFrame, table: str) -> int:
    """COPY로 대량 적재한다."""
    if df.empty:
        return 0

    df = fix_int_cols(df, table)

    buf = io.StringIO()
    # na_rep='\\N' : 결측값을 COPY가 NULL로 인식하는 표기로 기록
    df.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)

    cols = ", ".join(f'"{c}"' for c in df.columns)
    sql = (f'COPY raw.{table} ({cols}) FROM STDIN '
           f"WITH (FORMAT csv, NULL '\\N')")

    raw_conn = conn.connection.driver_connection
    with raw_conn.cursor().copy(sql) as cp:
        cp.write(buf.read())

    return len(df)


def row_count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM raw.{table}")).scalar()


def initial_load(engine, batch_date: date) -> None:
    """0일차 적재: 상품 전량 + 구간 밖 가입 고객 + 그들의 기기.

    테이블별로 트랜잭션을 나눠 부분 재시도가 가능하게 한다.
    이미 들어간 테이블은 건너뛴다.
    """
    products = pd.read_parquet(SRC / "product_catalog.parquet")
    products["batch_date"] = batch_date

    customers = pd.read_parquet(SRC / "crm_customers_initial.parquet")
    customers["batch_date"] = batch_date

    devices = pd.read_parquet(SRC / "crm_customer_devices.parquet")
    devices = devices[devices["customer_id"].isin(customers["customer_id"])].copy()
    devices["batch_date"] = batch_date

    print("[초기 적재]")
    for table, df in [("product_catalog", products),
                      ("crm_customers", customers),
                      ("crm_customer_devices", devices)]:
        existing = row_count(engine, table)
        if existing > 0:
            print(f"  {table:22s} 이미 {existing:,d}행 — 건너뜀")
            continue

        t0 = time.time()
        with engine.begin() as conn:
            n = copy_df(conn, df, table)
        print(f"  {table:22s} {n:8,d}행  {time.time() - t0:5.1f}초")
    print()


def daily_load(engine, batch_date: date) -> dict[str, int]:
    """일별 적재. 트랜잭션 하나로 묶어 중간 실패 시 전부 롤백한다."""
    counts = {}

    with engine.begin() as conn:
        # 삭제는 FK 역순 (참조하는 쪽 먼저)
        for table in reversed(LOAD_ORDER):
            conn.execute(
                text(f"DELETE FROM raw.{table} WHERE batch_date = :d"),
                {"d": batch_date})

        # 삽입은 FK 정순
        for table in LOAD_ORDER:
            path = BATCH / f"{table}.parquet"
            if not path.exists():
                print(f"  {table:22s} 파일 없음 — 건너뜀")
                counts[table] = 0
                continue

            df = pd.read_parquet(path)
            t0 = time.time()
            n = copy_df(conn, df, table)
            counts[table] = n
            print(f"  {table:22s} {n:8,d}행  {time.time() - t0:5.1f}초")

    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["dev", "main"])
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    url = os.environ.get(TARGETS[args.target])
    if not url:
        raise SystemExit(f"{TARGETS[args.target]} 가 .env 에 없습니다.")

    engine = create_engine(url)
    batch_date = args.date
    print(f"대상: {args.target}   배치 날짜: {batch_date}\n")

    started = time.time()
    initial_load(engine, batch_date)

    print("[일별 적재]")
    counts = daily_load(engine, batch_date)

    total = sum(counts.values())
    print(f"\n합계 {total:,d}행  {time.time() - started:.1f}초")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 파라미터 덤프가 수십만 자에 달할 수 있어 앞부분만 남긴다
        print(f"\n실패: {type(e).__name__}")
        print(str(e)[:600])
        raise SystemExit(1)