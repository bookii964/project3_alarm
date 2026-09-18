"""
로컬 PostgreSQL의 각 테이블에서 소량 샘플을 추출해 CSV로 저장한다.
공개 레포에 올려 테이블 형태를 보여주는 용도이며, 분석용이 아니다.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

LOCAL_PG = os.environ["LOCAL_DATABASE_URL"]
OUT_DIR = Path("data/sample")
N_ROWS = 30

TABLES = [
    "product_catalog",
    "crm_customers",
    "crm_customer_devices",
    "orders",
    "support_tickets",
    "clickstream",
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(LOCAL_PG)

    for table in TABLES:
        # TABLESAMPLE 대신 ORDER BY random() 사용 — 결과가 재현되지 않아도
        # 샘플 용도로는 무관하고, 적은 행 수에서는 성능 차이가 없다.
        query = f"""
            SELECT * FROM portfolio.{table}
            ORDER BY random()
            LIMIT {N_ROWS}
        """
        df = pd.read_sql(query, engine)
        out_path = OUT_DIR / f"{table}_sample.csv"
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"{table:24s} {len(df):3d}행 -> {out_path}")


if __name__ == "__main__":
    main()