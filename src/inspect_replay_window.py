r"""
재생 구간(92일)을 확정하기 위한 확인 스크립트.

옵션 B 기준: 2025-09-02 ~ 2025-12-02 구간만 재생한다.
이 구간에서 각 테이블이 실제로 얼마나 들어오는지, 그리고
crm_customers 증분이 의미 있는 규모인지 확인한다.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
engine = create_engine(os.environ["LOCAL_DATABASE_URL"])

START, END = "2025-09-02", "2025-12-02"
DAYS = 92

print(f"재생 구간: {START} ~ {END} ({DAYS}일)\n")

# 1. 구간 내 이벤트 건수
print("[이벤트 테이블 — 구간 내 건수]")
for table, col in [("orders", "order_date"),
                   ("support_tickets", "ticket_created"),
                   ("clickstream", "event_time")]:
    row = pd.read_sql(f"""
        SELECT count(*) AS n, count(DISTINCT {col}::date) AS n_days
        FROM portfolio.{table}
        WHERE {col}::date BETWEEN '{START}' AND '{END}'
    """, engine).iloc[0]
    per_day = row["n"] / row["n_days"] if row["n_days"] else 0
    print(f"  {table:20s} {row['n']:8,d}행  {row['n_days']:3d}일  일평균 {per_day:7,.0f}행")

# 2. 고객 증분 규모
print("\n[crm_customers — 초기/증분 분할]")
row = pd.read_sql(f"""
    SELECT
        count(*) FILTER (WHERE signup_date <  '{START}') AS initial,
        count(*) FILTER (WHERE signup_date >= '{START}'
                           AND signup_date <= '{END}')   AS incremental,
        count(*) FILTER (WHERE signup_date >  '{END}')   AS after_window,
        count(*)                                          AS total
    FROM portfolio.crm_customers
""", engine).iloc[0]

print(f"  초기 적재 (구간 이전 가입)  {row['initial']:8,d}명")
print(f"  증분 대상 (구간 내 가입)    {row['incremental']:8,d}명  일평균 {row['incremental']/DAYS:.1f}명")
print(f"  구간 이후 가입              {row['after_window']:8,d}명  → 초기 적재에 포함 필요")
print(f"  전체                        {row['total']:8,d}명")

# 3. FK 위반 재확인 (구간 내 기준)
print("\n[FK 위반 — 구간 내 주문 기준]")
row = pd.read_sql(f"""
    SELECT
        count(*) AS total,
        count(*) FILTER (WHERE o.order_date < c.signup_date) AS violated
    FROM portfolio.orders o
    JOIN portfolio.crm_customers c USING (customer_id)
    WHERE o.order_date BETWEEN '{START}' AND '{END}'
""", engine).iloc[0]
rate = row["violated"] / row["total"] if row["total"] else 0
print(f"  구간 내 주문 {row['total']:,d}건 중 위반 {row['violated']:,d}건 ({rate:.1%})")
print(f"  일평균 격리 예상: {row['violated']/DAYS:.1f}건")