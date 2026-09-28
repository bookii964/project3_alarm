r"""raw / quarantine / mart 의 행 수를 확인한다."""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

target = sys.argv[1] if len(sys.argv) > 1 else "dev"
key = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}[target]
engine = create_engine(os.environ[key])

TABLES = [
    ("raw", "product_catalog"), ("raw", "crm_customers"),
    ("raw", "crm_customer_devices"), ("raw", "orders"),
    ("raw", "support_tickets"), ("raw", "clickstream"),
    ("quarantine", "rejected_rows"),
    ("mart", "dq_daily"), ("mart", "daily_kpi"), ("mart", "batch_log"),
]

print(f"=== {target} ===\n")
for schema, table in TABLES:
    df = pd.read_sql(f"SELECT count(*) AS n FROM {schema}.{table}", engine)
    n = df.iloc[0]["n"]
    mark = "  ← 비어 있음" if n == 0 else ""
    print(f"  {schema}.{table:24s} {n:9,d}{mark}")

# batch_date 별 분포
print("\n[batch_date 별]")
for table in ["crm_customers", "orders", "clickstream"]:
    df = pd.read_sql(
        f"SELECT batch_date, count(*) AS n FROM raw.{table} "
        f"GROUP BY batch_date ORDER BY batch_date", engine)
    if df.empty:
        print(f"  {table:22s} (없음)")
    else:
        detail = ", ".join(f"{r.batch_date}: {r.n:,d}" for r in df.itertuples())
        print(f"  {table:22s} {detail}")