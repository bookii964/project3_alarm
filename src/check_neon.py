"""Neon에 무엇이 만들어졌는지 확인한다."""
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

target = sys.argv[1] if len(sys.argv) > 1 else "dev"
key = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}[target]
engine = create_engine(os.environ[key])

print(f"=== {target} ===\n")

print("[스키마]")
print(pd.read_sql("""
    SELECT nspname AS schema
    FROM pg_namespace
    WHERE nspname IN ('raw', 'quarantine', 'mart')
    ORDER BY nspname
""", engine).to_string(index=False))

print("\n[테이블]")
df = pd.read_sql("""
    SELECT schemaname AS schema, tablename AS table
    FROM pg_tables
    WHERE schemaname IN ('raw', 'quarantine', 'mart')
    ORDER BY schemaname, tablename
""", engine)
print(df.to_string(index=False) if len(df) else "  (없음)")

print("\n[제약조건 수]")
df = pd.read_sql("""
    SELECT ns.nspname AS schema, rel.relname AS table,
           CASE con.contype WHEN 'c' THEN 'CHECK'
                            WHEN 'p' THEN 'PK'
                            WHEN 'f' THEN 'FK' END AS type,
           count(*) AS cnt
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace ns ON ns.oid = rel.relnamespace
    WHERE ns.nspname IN ('raw', 'quarantine', 'mart')
      AND con.contype IN ('c', 'p', 'f')
    GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
""", engine)
print(df.to_string(index=False) if len(df) else "  (없음)")