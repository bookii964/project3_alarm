"""재생 설계를 위해 각 테이블의 날짜 분포를 확인한다."""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
engine = create_engine(os.environ["LOCAL_DATABASE_URL"])

TARGETS = [
    ("orders", "order_date"),
    ("support_tickets", "ticket_created"),
    ("clickstream", "event_time"),
    ("crm_customers", "signup_date"),
]

print(f"{'테이블':22s} {'전체':>8s} {'날짜있음':>8s} {'NULL':>8s} {'NULL률':>7s} {'최소':>12s} {'최대':>12s} {'일수':>6s}")
print("-" * 95)

for table, col in TARGETS:
    row = pd.read_sql(f"""
        SELECT
            count(*)                              AS total,
            count({col})                          AS dated,
            count(*) - count({col})               AS undated,
            min({col})::date                      AS min_d,
            max({col})::date                      AS max_d,
            count(DISTINCT {col}::date)           AS n_days
        FROM portfolio.{table}
    """, engine).iloc[0]

    rate = row["undated"] / row["total"] if row["total"] else 0
    print(f"{table:22s} {row['total']:8,d} {row['dated']:8,d} {row['undated']:8,d} "
          f"{rate:6.1%} {str(row['min_d']):>12s} {str(row['max_d']):>12s} {row['n_days']:6,d}")

# 마스터 테이블
print()
for table in ["product_catalog", "crm_customer_devices"]:
    n = pd.read_sql(f"SELECT count(*) AS n FROM portfolio.{table}", engine).iloc[0]["n"]
    print(f"{table:22s} {n:8,d}  (날짜 없음)")