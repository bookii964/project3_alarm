r"""
임의 SQL 을 실행해 결과를 표로 출력한다.

Neon 대시보드를 열지 않고 터미널에서 바로 확인하기 위한 도구.

사용:
    python -B src/query.py main "SELECT * FROM mart.daily_kpi LIMIT 5"
    python -B src/query.py main --file sql/check/kpi_trend.sql
    python -B src/query.py dashboard --file sql/check/kpi_trend.sql
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TARGETS = {
    "dev": "DEV_DATABASE_URL",
    "main": "DATABASE_URL",
    "dashboard": "DASHBOARD_DATABASE_URL",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=list(TARGETS))
    parser.add_argument("sql", nargs="?", help="실행할 SQL")
    parser.add_argument("--file", type=Path, help="SQL 파일 경로")
    args = parser.parse_args()

    sql = args.file.read_text(encoding="utf-8") if args.file else args.sql
    if not sql:
        raise SystemExit("SQL 또는 --file 중 하나가 필요합니다.")

    # 마크다운식 주석(#)을 걸러내고 끝 세미콜론을 제거한다.
    # SQL 주석은 -- 이며, read_sql 은 단일 문장만 받는다
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("#")]
    sql = "\n".join(lines).strip().rstrip(";")

    key = TARGETS[args.target]
    url = os.environ.get(key)
    if not url:
        raise SystemExit(f"{key} 가 .env 에 없습니다.")

    engine = create_engine(url)
    df = pd.read_sql(sql, engine)

    pd.set_option("display.max_rows", 100)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False) if len(df) else "(결과 없음)")
    print(f"\n{len(df):,d}행")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n실패: {type(e).__name__}")
        print(str(e)[:400])
        raise