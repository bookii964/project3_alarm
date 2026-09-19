"""로컬 PostgreSQL의 제약조건 현황을 조회한다."""
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
engine = create_engine(os.environ["LOCAL_DATABASE_URL"])

query = """
SELECT
    rel.relname            AS table_name,
    con.contype            AS type_code,
    CASE con.contype
        WHEN 'c' THEN 'CHECK'
        WHEN 'p' THEN 'PRIMARY KEY'
        WHEN 'f' THEN 'FOREIGN KEY'
        WHEN 'u' THEN 'UNIQUE'
        ELSE con.contype::text
    END                    AS constraint_type,
    count(*)               AS cnt
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace ns ON ns.oid = rel.relnamespace
WHERE ns.nspname = 'portfolio'
GROUP BY rel.relname, con.contype
ORDER BY rel.relname, con.contype
"""

df = pd.read_sql(query, engine)
print(df.pivot_table(index="table_name", columns="constraint_type",
                     values="cnt", fill_value=0))
print()
print("총계:")
print(df.groupby("constraint_type")["cnt"].sum())