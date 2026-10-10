# 아키텍처

## 전체 구성

┌─────────────────────────────────────────────────────────┐
│ GitHub Actions (매일 KST 07:00, cron '0 22 * * *') │
│ │
│ run_batch.py │
│ ├─ replay.py 하루치 추출 + 시나리오 주입 │
│ ├─ validate.py 검증 → 격리 + 품질 지표 기록 │
│ ├─ load.py raw 적재 (COPY, 멱등) │
│ ├─ aggregate.py KPI 집계 │
│ └─ alert.py 임계 초과 시 Slack 발송 │
│ │
│ 각 단계의 결과를 mart.batch_log 에 기록 │
└─────────────────────────────────────────────────────────┘
│ │
│ 읽기 │ 쓰기
▼ ▼
┌───────────────┐ ┌──────────────────┐
│ GitHub Release│ │ Neon PostgreSQL │
│ source.zip │ │ raw │
│ (Parquet 64MB)│ │ quarantine │
└───────────────┘ │ mart │
└──────────────────┘
│ 읽기 전용
▼
┌──────────────────┐
│ Streamlit Cloud │
│ 대시보드 (3탭) │
└──────────────────┘

                         ┌──────────────────┐
                         │ Slack #dq-alerts │
                         │ P1 / P2 / P3     │
                         └──────────────────┘

---

## 데이터 흐름

### 1. 재생 (replay.py)

원본 Parquet 에서 "오늘 도착할 하루치"를 꺼낸다.

ANCHOR(2026-09-28) 와 배치 날짜의 차이로 재생 일차를 계산
→ day_index = (batch_date - ANCHOR) % 92
→ 논리 날짜 = 2025-09-02 + day_index

dated 파일에서 해당 논리 날짜의 행을 추출
undated 풀에서 원본 결측률에 맞는 개수만큼 꺼내 합침
config/scenarios.yml 에 해당 날짜가 있으면 오염 주입
batch_date 컬럼을 붙여 data/batch/*.parquet 으로 저장


**상태 파일을 쓰지 않는다.** 실제 날짜에서 계산하므로 로컬과
Actions 가 같은 결과를 내고, `--date` 로 과거 배치를 재생성할 수 있다.

#### undated 풀이란

원본 데이터의 `order_date` 30%, `event_time` 12% 가 NULL 이다.
날짜가 없으니 "어느 날 도착할지" 정할 수 없다.

이 행들을 버리면 결측률이 0이 되어 D01 룰이 감시할 대상이 사라진다.
그래서 **별도 풀로 보관하고, 원본 결측률에 맞춰 매 배치에 배분**한다.

n_null = n_dated × r / (1 - r) r = 원본 결측률


배분 위치는 앞선 날들의 누적 소비량으로 정해 중복을 막는다.

### 2. 검증 (validate.py)

DB 에서 참조 대상 id 조회 (crm_customers, product_catalog)

이번 배치의 신규 마스터를 합침
↓
룰 9종 실행
격리 대상 → drop_mask 에 누적
검사 결과 → mart.dq_daily
↓
통과한 행 → data/batch/clean/*.parquet
격리된 행 → quarantine.rejected_rows (jsonb)

**불리언 마스크로 격리 대상을 누적한다.** 인덱스로 추적하면
파일 왕복이나 필터링 과정에서 어긋나기 쉽다.

### 3. 적재 (load.py)

초기 적재 (최초 1회, batch_date = 재생시작일 - 1)
product_catalog 500 → crm_customers 47,216 → devices 50,798
↓
일별 적재 (트랜잭션 하나)
DELETE: 이벤트 3개만, FK 역순
INSERT: 5개 테이블, FK 정순, COPY 방식


### 4. 집계 (aggregate.py)

`sql/marts/10_daily_kpi.sql` 을 DB 안에서 실행한다.
파이썬으로 데이터를 끌어오지 않아 네트워크 왕복이 없다.

### 5. 알람 (alert.py)

mart.batch_log → P1 판정
mart.dq_daily → P2/P3 판정
(참조 무결성 룰은 기준선 × 배수 초과 시만)
↓
mart.alert_log 조회 → 24시간 내 같은 조합이면 억제 (P1 제외)
↓
Slack 발송 → mart.alert_log 기록


---

## 핵심 설계

### 두 개의 날짜 축

| | `batch_date` | 이벤트 날짜 |
|---|---|---|
| 의미 | 데이터가 우리 시스템에 들어온 날 | 실제로 일이 일어난 때 |
| 예 | 2026-10-17 | `order_date` 2025-09-21 |
| NULL | **절대 없음** | 있을 수 있음 (30%) |
| 용도 | 파티션, 멱등 삭제, 품질 지표 | 분석 |

이벤트 시각은 비어 있을 수 있지만 적재 시각은 비지 않는다.
데이터가 들어온 순간 우리가 찍는 값이기 때문이다.

**이 분리가 없으면 결측 행을 어떻게 다룰지 답이 없다.**
날짜가 없다고 버리면 품질 감시 대상이 사라지고,
억지로 채우면 데이터를 발명하는 것이 된다.

### 세 개의 스키마

| 스키마 | 성격 | 제약조건 |
|---|---|---|
| `raw` | 도착 데이터 | CHECK 25 / FK 6 — 최후 방어선 |
| `quarantine` | 불량 행 보관 | **없음** |
| `mart` | 집계 결과 | PK 위주 |

`quarantine` 에 제약을 두지 않는 것이 핵심이다.
규칙을 어긴 행을 받는 것이 목적인데 규칙이 걸려 있으면
들어올 수가 없다.

`payload` 를 `jsonb` 로 두어 **테이블마다 구조가 달라도 하나로 받는다.**
나중에 `payload->>'order_id'` 로 특정 컬럼을 꺼내볼 수 있다.

### 멱등성

같은 날짜를 몇 번 돌려도 결과가 같아야 한다.
**다만 테이블 성격에 따라 방식이 다르다.**

| 대상 | 방식 |
|---|---|
| 이벤트 (orders, tickets, clickstream) | `DELETE WHERE batch_date = ?` 후 INSERT |
| 마스터 (customers, devices) | 기존 행을 걸러낸 뒤 INSERT |
| 집계 (daily_kpi, dq_daily) | DELETE 후 INSERT |

마스터를 날짜 단위로 지우면 안 된다. 한 번 들어온 고객은
이후 모든 배치의 이벤트가 참조하기 때문이다.
**삭제 범위가 적재 단위와 어긋나면 파이프라인이 스스로
참조 무결성을 파괴한다.**

### 단계 실패 처리

replay / validate / load / aggregate 실패 → 배치 중단 (종료 코드 1)
alert 실패 → 기록만 하고 계속


알람 발송 실패로 배치 전체를 FAILED 로 표시하면,
다음 날 P1 알람이 오탐으로 울린다.

---

## 기술 선택

### 왜 GitHub Actions 인가

| | 비용 | 설정 | 한계 |
|---|---|---|---|
| **GitHub Actions** | 0원 | 30분 | 예약 지연, 백필 빈약 |
| Airflow (로컬) | 0원 | 2~3일 | 메모리 4GB+ |
| AWS 상시 | 월 3~5만원 | 1~2주 | — |

일 1회·6,000행 규모에서는 Actions 가 적절하다.
**실행 이력이 공개 URL 로 남는다**는 점도 포트폴리오에 유리하다.

전환 시점: 일 배치가 수백만 행을 넘거나, 작업 간 의존관계가
복잡해지거나, 실행 시각을 정확히 보장해야 할 때.

### 왜 원본을 Release 에 두는가

Parquet 64MB 를 레포에 커밋하면 clone 이 무거워지고,
Git 이력에 영구 보존되어 되돌릴 수 없다.

Release 는 레포 크기에 포함되지 않고 파일당 2GB 까지 받는다.
워크플로가 매 실행 시 `curl` 로 내려받는다.

**대안이었던 것** — 원본을 DB 에 보관하고 replay 를 SQL 로 구현하면
파일 전달 자체가 불필요하다. 다만 Neon 무료 0.5GB 를 소진하고
설계 변경 비용이 크다. 확장 과제로 남겼다.

### 왜 대시보드가 mart 만 읽는가

두 가지 이유가 있다.

**성능** — `raw.clickstream` 95,194행을 매 새로고침마다 훑으면
Neon 컴퓨트가 빠르게 소모된다. `mart.daily_kpi` 19행,
`mart.dq_daily` 678행이면 조회가 순식간이다.

**보안** — Streamlit Cloud 는 외부 서비스다. 읽기 전용 계정에
`mart` / `quarantine` 권한만 주었고, `raw` 접근과 쓰기는
권한 수준에서 차단된다.

---

## 비용

| 서비스 | 플랜 | 한도 | 현재 사용 |
|---|---|---|---|
| Neon | Free | 0.5GB / 100 CU-시간 | 약 0.1GB / 월 5시간 |
| GitHub Actions | Free (Public) | 무제한 | 일 1분 40초 |
| Streamlit | Community | 앱 1개 | 1개 |
| Slack | Free | 메시지 90일 보관 | 일 0~1건 |
| **합계** | | | **0원** |

### 용량이 늘어나는 지점

92일 순환 재생이 2회차에 접어들면 `raw` 가 계속 쌓인다.
`sql/maintenance/90_retention.sql` 이 90일 경과분을 삭제해
약 180MB 에서 평형을 이루도록 설계했다.

마스터 테이블은 삭제 대상이 아니다. 이벤트가 참조하고 있고,
초기 적재분은 재적재 경로가 없기 때문이다.

### 주의할 점

- **GitHub Actions 는 레포에 60일간 활동이 없으면 예약을 자동 중단한다.**
  월요일 실행 시 `docs/last_run.md` 를 갱신·커밋해 활동을 남긴다.
- Streamlit Community Cloud 는 접속이 없으면 앱이 절전 상태가 된다.
  첫 로딩에 수십 초가 걸릴 수 있다.
- Slack 무료 플랜은 메시지를 90일만 보관한다.
  알람 이력 자체는 `mart.alert_log` 에 영구 보존된다.

---

## 디렉터리 구조

project_3/
├─ .github/workflows/daily.yml 배치 자동 실행
├─ app/dashboard.py Streamlit 대시보드
├─ config/
│ ├─ baseline.yml 검증 기준선
│ ├─ scenarios.yml 주입 시나리오
│ └─ alerts.yml 알람 심각도·억제·런북
├─ sql/
│ ├─ ddl/ 스키마·테이블 정의
│ ├─ marts/ 집계 쿼리
│ ├─ maintenance/ 보존 정책, 초기화
│ └─ check/ 점검용 조회
├─ src/
│ ├─ run_batch.py 배치 실행기
│ ├─ replay.py 재생 + 주입
│ ├─ validate.py 검증
│ ├─ load.py 적재
│ ├─ aggregate.py 집계
│ ├─ alert.py 알람
│ └─ (진단 도구들) query, check_rows, test_conn 등
├─ data/ .gitignore (sample 제외)
│ ├─ source/ 원본 Parquet (Release 에서 복원)
│ ├─ batch/ 당일 배치 (clean/ 포함)
│ └─ sample/ 공개 샘플 30행
└─ docs/ 문서와 증거 자료