"""Neon 접속 확인용 일회성 스크립트."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

for label, key in [("운영(main)", "DATABASE_URL"), ("개발(dev)", "DEV_DATABASE_URL")]:
    url = os.environ.get(key)
    if not url:
        print(f"{label:12s} 건너뜀 ({key} 없음)")
        continue

    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
        print(f"{label:12s} 접속 성공 — {version.split(',')[0]}")
    except Exception as e:
        print(f"{label:12s} 실패 — {type(e).__name__}: {str(e)[:100]}")