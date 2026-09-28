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

# UUID 컬럼 목록.
# Parquet에는 UUID 타입이 없어 그대로 저장하면 16바이트 이진값이 되고,
# 다시 읽었을 때 b'\xfa\x10...' 형태가 되어 적재 시 타입 오류가 난다.
# 문자열로 바꿔 내보내면 Postgres가 적재 시 다시 uuid로 해석한다.
UUID_COLS = {
    "product_catalog": [],
    "crm_customers": ["customer_id"],
    "crm_customer_devices": ["customer_id", "device_id"],
    "orders": ["order_id", "customer_id"],
    "support_tickets": ["ticket_id", "customer_id"],
    "clickstream": ["event_id", "customer_id", "session_id",
                    "device_id", "ingest_run_id"],
}


def to_uuid_str(df: pd.DataFrame, table: str) -> pd.DataFrame:
    """UUID 컬럼을 문자열로 변환한다.

    astype("string")은 NULL을 NULL로 유지한다.
    astype(str)을 쓰면 NULL이 "None"이라는 글자가 되므로 쓰지 않는다.
    (clickstream.customer_id는 30%가 NULL이라 특히 중요)
    """
    for col in UUID_COLS.get(table, []):
        if col in df.columns:
            df[col] = df[col].astype("string")
    return df


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
        dated = to_uuid_str(dated, table)
        save(dated, f"{table}_dated")

        # 날짜가 없는 행은 구간 개념이 없으므로 전량 보관.
        # 재생기가 원본 결측률에 맞춰 매 배치에 배분한다
        undated = pd.read_sql(
            f"SELECT * FROM portfolio.{table} WHERE {col} IS NULL", engine)
        undated = to_uuid_str(undated, table)
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
    initial = to_uuid_str(initial, "crm_customers")
    save(initial, "crm_customers_initial")

    incremental = pd.read_sql(
        f"SELECT * FROM portfolio.crm_customers "
        f"WHERE signup_date BETWEEN '{REPLAY_START}' AND '{REPLAY_END}' "
        f"ORDER BY signup_date", engine)
    incremental = to_uuid_str(incremental, "crm_customers")
    save(incremental, "crm_customers_dated")

    # 기기는 날짜 컬럼이 없다. 고객 적재 시 customer_id로 선별해 함께 넣는다
    devices = pd.read_sql("SELECT * FROM portfolio.crm_customer_devices", engine)
    devices = to_uuid_str(devices, "crm_customer_devices")
    save(devices, "crm_customer_devices")

    print("\n[고정 마스터]")
    # product_catalog는 uuid 컬럼이 없어 변환 불필요
    products = pd.read_sql("SELECT * FROM portfolio.product_catalog", engine)
    save(products, "product_catalog")

    total = sum(p.stat().st_size for p in OUT.glob("*.parquet")) / 1024 / 1024
    print(f"\n총 {total:.1f} MB")


if __name__ == "__main__":
    main()