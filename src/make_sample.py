"""
로컬 PostgreSQL의 각 테이블에서 소량 샘플을 추출해 CSV로 저장한다.
공개 레포에서 테이블 구조를 보여주는 용도이며, 분석용이 아니다.

_flag 컬럼이 이 프로젝트의 핵심 설계이므로,
플래그가 기록된 행을 의도적으로 일부 포함시킨다.
"""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

LOCAL_PG = os.environ["LOCAL_DATABASE_URL"]
OUT_DIR = Path("data/sample")

N_FLAGGED = 10   # 플래그가 있는 행
N_NORMAL = 20    # 일반 행

FLAG_COLS = {
    "product_catalog": ["name_flag", "price_flag"],
    "crm_customers": ["name_flag", "email_flag", "phone_flag", "age_flag"],
    "crm_customer_devices": [],
    "orders": ["amount_flag", "date_flag"],
    "support_tickets": ["date_flag", "issue_flag", "sentiment_flag", "agent_flag"],
    "clickstream": ["time_flag", "device_flag"],
}


def build_query(table: str, flags: list[str]) -> str:
    if not flags:
        return f"""
            SELECT * FROM portfolio.{table}
            ORDER BY random() LIMIT {N_FLAGGED + N_NORMAL}
        """

    cond = " OR ".join(f"{c} IS NOT NULL" for c in flags)
    return f"""
        (SELECT * FROM portfolio.{table} WHERE {cond}
         ORDER BY random() LIMIT {N_FLAGGED})
        UNION ALL
        (SELECT * FROM portfolio.{table} WHERE NOT ({cond})
         ORDER BY random() LIMIT {N_NORMAL})
    """


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(LOCAL_PG)

    for table, flags in FLAG_COLS.items():
        df = pd.read_sql(build_query(table, flags), engine)

        if flags:
            n_flagged = int(df[flags].notna().any(axis=1).sum())
        else:
            n_flagged = 0

        out_path = OUT_DIR / f"{table}_sample.csv"
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"{table:24s} {len(df):3d}행 (플래그 {n_flagged:2d}건) -> {out_path.name}")


if __name__ == "__main__":
    main()