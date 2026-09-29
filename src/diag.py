"""진단: clean 파일의 고객이 DB에 모두 존재하는지 확인한다."""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
engine = create_engine(os.environ["DEV_DATABASE_URL"])

clean = pd.read_parquet("data/batch/clean/orders.parquet")
ids = set(clean["customer_id"].dropna().astype(str))

with engine.connect() as conn:
    db = {str(r) for r in
          conn.execute(text("SELECT customer_id FROM raw.crm_customers")).scalars()}

missing = ids - db
print(f"clean 고객 {len(ids):,d} / DB 고객 {len(db):,d}")
print(f"DB 에 없는 고객: {len(missing)}")
for m in list(missing)[:5]:
    print("  ", m)