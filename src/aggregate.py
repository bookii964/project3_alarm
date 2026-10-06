r"""
집계기: raw 를 읽어 mart.daily_kpi 를 갱신한다.

파이썬으로 데이터를 끌어오지 않고 DB 안에서 INSERT ... SELECT 로
계산한다. 네트워크 왕복이 없어 빠르고, 집계 로직이 SQL 파일로 남아
읽기도 수정하기도 쉽다.

사용:
    python -B src/aggregate.py dev
    python -B src/aggregate.py dev --date 2026-09-28
"""
import argparse
import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SQL_FILE = ROOT / "sql" / "marts" / "10_daily_kpi.sql"
TARGETS = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["dev", "main"])
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    engine = create_engine(os.environ[TARGETS[args.target]])
    bd = args.date
    print(f"대상: {args.target}   배치 날짜: {bd}\n")

    sql = SQL_FILE.read_text(encoding="utf-8")

    with engine.begin() as conn:
        # DELETE + INSERT 를 한 트랜잭션으로 묶어 멱등성을 보장한다
        for stmt in [s.strip() for s in sql.split(";") if s.strip()
                     and not s.strip().startswith("--")]:
            conn.execute(text(stmt), {"d": bd})

    # 결과 확인
    df = pd.read_sql(
        "SELECT * FROM mart.daily_kpi WHERE batch_date = %(d)s",
        engine, params={"d": bd})

    if df.empty:
        print("집계 결과 없음")
        return

    r = df.iloc[0]
    print("[거래]")
    print(f"  주문 건수      {r['order_count']:>12,d}")
    print(f"  GMV            {r['gmv'] or 0:>12,.0f}")
    print(f"  AOV            {r['aov'] or 0:>12,.0f}")
    print(f"  금액 결측률    {r['order_null_rate'] or 0:>12.1%}  "
          f"(GMV 는 나머지 {1 - (r['order_null_rate'] or 0):.1%} 기준)")

    print("\n[CS]")
    print(f"  티켓 건수      {r['ticket_count']:>12,d}")
    print(f"  부정 비율      {r['ticket_negative_rate'] or 0:>12.1%}")
    print(f"  평균 해결시간  {r['avg_resolution_hours'] or 0:>12.1f}h")

    print("\n[행동]")
    print(f"  이벤트 건수    {r['event_count']:>12,d}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n실패: {type(e).__name__}")
        print(str(e)[:600])
        raise SystemExit(1)