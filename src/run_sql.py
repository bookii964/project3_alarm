"""
SQL 파일을 지정한 대상 DB에서 실행한다.

사용:
    python src/run_sql.py dev  sql/ddl/10_schemas.sql
    python src/run_sql.py dev  sql/ddl/10_schemas.sql sql/ddl/12_quarantine.sql
    python src/run_sql.py main sql/ddl/10_schemas.sql

powershell에서 아래 실행
python src\run_sql.py dev sql\ddl\10_schemas.sql    
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TARGETS = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}


def main() -> None:
    if len(sys.argv) < 3:
        print("사용: python src/run_sql.py <dev|main> <sql파일> [sql파일...]")
        sys.exit(1)

    target = sys.argv[1]
    if target not in TARGETS:
        print(f"대상은 dev 또는 main 이어야 합니다. 입력값: {target}")
        sys.exit(1)

    url = os.environ.get(TARGETS[target])
    if not url:
        print(f"{TARGETS[target]} 가 .env 에 없습니다.")
        sys.exit(1)

    engine = create_engine(url)
    print(f"대상: {target}\n")

    for arg in sys.argv[2:]:
        path = Path(arg)
        if not path.exists():
            print(f"  {path} — 파일 없음. 건너뜀")
            continue

        sql = path.read_text(encoding="utf-8")
        try:
            # DDL 전체를 하나의 트랜잭션으로 실행.
            # 중간에 실패하면 전부 롤백되어 어중간한 상태가 남지 않는다.
            with engine.begin() as conn:
                conn.execute(text(sql))
            print(f"  {path.name} — 성공")
        except Exception as e:
            msg = str(e)
            if "://" in msg and "@" in msg:
                msg = f"(접속 정보 포함 메시지 생략) {type(e).__name__}"
            print(f"  {path.name} — 실패\n     {msg[:500]}")
            sys.exit(1)

    print("\n완료")


if __name__ == "__main__":
    main()