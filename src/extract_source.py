r"""
로컬 PostgreSQL의 정제 데이터를 Parquet으로 추출한다.

재생 설계(C1, 92일 구간) 기준으로 세 부류로 나눈다:
  이벤트      orders / support_tickets / clickstream
              → dated(구간 내, 날짜순) + undated(NULL 풀, 전량)
  증분 마스터  crm_customers → initial(구간 밖) + dated(구간 내)
              crm_customer_devices → 전량 (고객 적재 시 선별 동반)
  고정 마스터  product_catalog → 전량 (0일차 적재)

사용: python src/extract_source.py
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

OUT = ROOT / "data" / "source"
engine = create_engine(os.environ["LOCAL_DATABASE_URL"])

# 재생 구간. clickstream 수집 기간에 맞춤 (92일)
REPLAY_START = "2025-09-02"
REPLAY_END = "2025-12-02"

EVENTS = [
    ("orders", "order_date"),
    ("support_tickets", "ticket_created"),
    ("clickstream", "event_time"),
]


def save(df: pd.DataFrame, name: str) -> None:
    path = OUT / f"{name}.parquet"
    df.to_parquet(path, index=False)
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"  {name:32s} {len(df):8,d}행  {size_mb:6.1f} MB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"재생 구간: {REPLAY_START} ~ {REPLAY_END}\n")

    print("[이벤트 테이블]")
    for table, col in EVENTS:
        # 구간 내 행만. 날짜순 정렬해두면 재생기가 찾기 쉽다
        dated = pd.read_sql(
            f"SELECT * FROM portfolio.{table} "
            f"WHERE {col}::date BETWEEN '{REPLAY_START}' AND '{REPLAY_END}' "
            f"ORDER BY {col}", engine)
        save(dated, f"{table}_dated")

        # 날짜가 없는 행은 구간 개념이 없으므로 전량 보관.
        # 재생기가 원본 결측률에 맞춰 매 배치에 배분한다
        undated = pd.read_sql(
            f"SELECT * FROM portfolio.{table} WHERE {col} IS NULL", engine)
        save(undated, f"{table}_undated")

    print("\n[증분 마스터]")
    # 구간 밖 가입 고객(이전 + 이후)은 0일차에 한 번에 적재.
    # 구간 이후 가입자를 포함하는 이유: 증분으로 들어올 기회가 없는데
    # 구간 내 주문·티켓에 등장하면 FK 위반이 되기 때문
    initial = pd.read_sql(
        f"SELECT * FROM portfolio.crm_customers "
        f"WHERE signup_date <  '{REPLAY_START}' "
        f"   OR signup_date >  '{REPLAY_END}' "
        f"ORDER BY signup_date", engine)
    save(initial, "crm_customers_initial")

    incremental = pd.read_sql(
        f"SELECT * FROM portfolio.crm_customers "
        f"WHERE signup_date BETWEEN '{REPLAY_START}' AND '{REPLAY_END}' "
        f"ORDER BY signup_date", engine)
    save(incremental, "crm_customers_dated")

    # 기기는 날짜 컬럼이 없다. 고객 적재 시 customer_id로 선별해 함께 넣는다
    devices = pd.read_sql("SELECT * FROM portfolio.crm_customer_devices", engine)
    save(devices, "crm_customer_devices")

    print("\n[고정 마스터]")
    products = pd.read_sql("SELECT * FROM portfolio.product_catalog", engine)
    save(products, "product_catalog")

    total = sum(p.stat().st_size for p in OUT.glob("*.parquet")) / 1024 / 1024
    print(f"\n총 {total:.1f} MB")


if __name__ == "__main__":
    main()