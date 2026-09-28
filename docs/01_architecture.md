# 아키텍처

## 실행 환경
- 스케줄러: GitHub Actions (cron, 일 1회)
- DB: Neon PostgreSQL 18.6 (Singapore)
  - main 브랜치 = 운영
  - dev 브랜치 = 실험용 복사본
- 대시보드: Streamlit Community Cloud (예정)
- 알람: Slack Incoming Webhook (예정)

## 스키마 구성
| 스키마 | 역할 | 제약조건 |
|---|---|---|
| raw | 도착한 데이터 적재. batch_date 로 파티션 | CHECK / FK 유지 (최후 방어선) |w
| quarantine | 검증에 걸린 불량 행 보관 | **없음** (불량 행을 받아야 하므로) |
| mart | 집계 결과 (dq_daily / daily_kpi / batch_log) | PK 위주 |

## 데이터 흐름


## 날짜 처리 원칙
이벤트 시각(order_date 등)과 적재 시각(batch_date)을 분리한다.
이벤트 시각은 NULL일 수 있으나 batch_date는 항상 존재한다.
NULL 날짜 행은 원본 결측률에 맞춰 각 배치에 배분한다. (상세: 02_decision_log)