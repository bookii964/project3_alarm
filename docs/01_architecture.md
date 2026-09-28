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

## 배치 구성 (예정: .github/workflows/daily.yml)

실행: 매일 한국시각 07:00 (cron은 UTC 기준이므로 `0 22 * * *`)

    1. replay.py      하루치 추출 + 시나리오 주입
    2. load.py        raw 적재 (FK 순서, batch_date 멱등)
    3. validate.py    검증 → quarantine 격리 + mart.dq_daily 기록
    4. aggregate.py   mart.daily_kpi 갱신
    5. alert.py       임계 초과 시 Slack 발송
    6. 90_retention.sql   (2회차 이후 연결) 90일 경과 raw 삭제

주의사항:
- GitHub Actions는 레포 60일 무활동 시 예약을 자동 비활성화 → 월 1회 자동 커밋 단계 필요
- 실패 시 재시도는 최대 2회로 제한 (무한 재시도 시 Neon CU-hour 소모)
- 스크립트는 건수·상태만 출력. 데이터 행을 로그에 남기지 않음 (퍼블릭 레포이므로 로그가 공개됨)