"""Slack Webhook 발송 확인용 일회성 스크립트."""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

url = os.environ.get("SLACK_WEBHOOK_URL")
if not url:
    raise SystemExit("SLACK_WEBHOOK_URL 이 .env 에 없습니다.")

res = requests.post(url, json={"text": "파이프라인 알람 연결 테스트"})
print(f"응답 {res.status_code}: {res.text}")