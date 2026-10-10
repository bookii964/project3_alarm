# 작업 일지

## Day 0 (2026-09-17)
- 한 일: Python·Git 확인, 폴더 구조 생성, 문서 뼈대 작성
- 막힌 것: 없음
- 내일 할 것: 가상환경 설정, Neon 가입, 스키마 이관

## Day 0-1 (2026-09-18)
- 한 일: 로컬 PG 연결 확인, 샘플 CSV 6종 생성, .gitignore 예외 규칙 적용,
  GitHub remote 주소 수정
- 막힌 것:
  - Copy-Item으로 .env 생성 시 파일명이 .env.example.env로 생성됨 → Rename-Item으로 수정
  - remote origin이 잘못된 레포명으로 등록되어 있었음 → set-url로 교체
- 내일 할 것: NULL 날짜 처리 방식 결정 기록, Neon 가입 및 스키마 이관

## Day 0 완료 (2026-09-18)
- 한 일: 환경 구성 전체, 샘플 CSV 생성 및 공개
- 막힌 것: .gitignore 의 `data/` 가 폴더 단위로 제외되어 `!` 예외가
  적용되지 않음 → `data/*` 방식으로 변경 후 캐시 정리로 해결
- 다음: Neon 프로젝트 생성, 스키마 이관

## Day 1 (2026-09-19)

### 한 일
- Neon 가입 및 프로젝트 생성 (리전: Singapore, Postgres 18.6)
- dev 브랜치 생성, 접속 주소 .env 에 등록
- src/test_conn.py 작성 — dev 브랜치 접속 성공 확인
- pg_dump 로 로컬 portfolio 스키마 구조 추출
  → sql/ddl/01_local_schema.sql (CREATE TABLE 6, PRIMARY KEY 6, INDEX 13)
- src/check_constraints.py 작성 (제약조건 정확한 개수 조회용)

### 막힌 것 / 미해결
- `code` 명령이 PATH에 없어 터미널에서 VS Code 실행 불가
  → VS Code 탐색기에서 직접 파일 열기로 우회. PATH 등록은 보류
- Select-String 으로 센 제약 개수가 부정확
  (CHECK 27로 집계되나 정의서상 55개. 줄바꿈 때문으로 추정)
- **FOREIGN KEY 개수 미확인** — 명령

## 2026-09-19 | 정의서와 실제 DB의 제약조건 불일치 발견
- 정의서 기재: CHECK 55개
- 실제 DB(pg_constraint 조회): CHECK 26개. FK 6개, PK 6개는 일치
- 추정 원인: 정의서가 CHECK '조건절' 수를 센 것으로 보임
  (예: `amount IS NULL OR amount > 0` 은 조건 2개지만 제약 1개)
- 조치: 실제 DB 조회 결과를 기준으로 삼고, 새 DDL 작성 시
  정의서에 기술된 규칙 중 누락된 것은 검증 룰(validate.py)로 옮긴다
- 배운 것: 문서에 적힌 수치는 DB에 직접 조회해 확인해야 한다

## Day 2 완료 (2026-09-20)

### 한 일
- Neon dev/main 양쪽에 스키마 적용 완료
  - raw 6테이블 (batch_date, ingested_at 추가), quarantine 1테이블,
    mart 3테이블 (dq_daily / daily_kpi / batch_log)
  - 검증: PK 7, FK 6, CHECK 25 — dev/main 일치
- run_sql.py / check_neon.py 작성
  - psql 대신 파이썬으로 DDL 실행. GitHub Actions에서 동일 코드 재사용 목적
  - DDL 전체를 한 트랜잭션으로 묶어 중간 실패 시 롤백되도록 처리

### 배운 것 / 정리
- **Parquet(파케이)**: 열 단위로 저장하는 압축 표 형식. CSV 대비 5~10배 작고,
  필요한 열만 읽을 수 있으며, **타입이 파일에 기록되어 보존됨**
  (CSV는 모든 값이 문자열이라 uuid·날짜·앞자리 0이 깨질 수 있음).
  사람이 직접 열어볼 수 없어 샘플은 CSV로 별도 유지.
  사용법은 df.to_parquet() / pd.read_parquet() 로 CSV와 동일
- **SyntaxWarning `invalid escape sequence '\d'`**: 문자열 안의
  윈도우 경로에서 `\d` 를 파이썬이 특수문자로 해석하려다 발생.
  docstring 앞에 `r` 을 붙여 raw string 으로 처리

### 막힌 것
- psql 명령에 예시 주소를 그대로 입력 → 파이썬 실행 방식으로 전환
- test_conn.py 들여쓰기 오류 (탭/공백 혼용). VS Code 설정을 Spaces:4 로 고정

### 다음 할 일
1. run_sql.py docstring 에 r 접두어 추가
2. 마스터 테이블 공급 방식 결정 (A: 첫날 전량 / C: 초기+증분)
3. Parquet 추출 스크립트 작성
   - orders / clickstream / support_tickets → dated / undated 분리
   - product_catalog / crm_customers / crm_customer_devices → 마스터

   ## Day 2 완료 — Parquet 추출 (2026-09-28)

### 한 일
- extract_source.py 수정 및 재실행 — 재생 구간(92일) 필터 적용
  - orders_dated 210,000 → 26,356행으로 정정
  - crm_customers를 initial(47,216) / dated(984)로 분할
  - 구간 이후 가입 고객도 initial에 포함하도록 방어 처리 (현재 0명)
- 총 42.3 MB. DB 적재 시 인덱스 포함 약 180MB로 추정

### 막힌 것
- 코드 수정 시 함수 바깥에 중복 블록을 추가해 구간 필터가 무시됨
  (main() 안의 같은 이름 변수가 우선하여 에러 없이 기존 동작 유지)
  → 파일 전체 교체로 해결. 부분 수정 시 어느 함수 안인지 확인할 것

### 비용 검토
- 현재 구성 전부 무료: Neon Free(0.5GB/100CU-h), GitHub Actions(Public),
  Streamlit Community, Slack Free
- 예상 사용량: 용량 180MB(36%), CU-hour 월 5시간(5%)
- 리스크: 순환 재생 2회차부터 용량 누적 → raw 90일 보존 정책으로 대응
- 리스크: GitHub Actions는 레포 60일 무활동 시 예약 자동 비활성화
  → 월 1회 자동 커밋 단계 추가 예정

### 다음 할 일
1. replay.py 작성 — 논리적 날짜 관리, dated 추출, undated 비율 배분
2. state/replay_state.json 설계 (cycle, day_index)
3. load.py — 멱등 적재 + FK 순서 보장

## Day 3 | Neon dev 브랜치 재생성
- 증상: dev 접속 시 password authentication failed. main은 정상
- 원인: dev 브랜치가 삭제되어 .env의 엔드포인트가 존재하지 않는 곳을 가리킴
  (ep-blue-sea-... → 실제로는 없는 브랜치)
- 조치: dev 브랜치 재생성 후 .env 갱신
- 함께 발견: 복제된 dev에 clickstream FK 2개가 누락(전체 6 → 4)
  → raw 테이블 DROP 후 11_raw_tables.sql 재적용으로 복구
- 배운 것:
  - Neon 브랜치는 생성 시마다 엔드포인트와 비밀번호가 새로 발급됨.
    만든 즉시 .env 갱신할 것
  - CREATE TABLE IF NOT EXISTS 는 테이블이 있으면 통째로 건너뛰므로,
    제약조건이 누락된 상태를 고치지 못한다. DROP 후 재생성이 필요
  - 스키마 검증(check_neon.py)을 적재 전에 돌리는 습관이 이 문제를 잡았다

  ## Day 3 (2026-09-28)

### 한 일
- extract_source.py — UUID를 문자열로 변환 (Parquet에 UUID 타입 없음)
- replay.py — 92일 순환 재생, ANCHOR=2026-09-28 확정
  - 논리 날짜 2025-09-02 부터 시작, 결측률 30/9/12% 유지 확인
- load.py — COPY 방식 적재기
  - 초기 적재 47,216행 3.3초 (INSERT 방식 대비 대폭 단축)
  - FK 순서 보장, batch_date 기준 DELETE→INSERT 멱등 처리
- 점검 스크립트 추가: check_rows.py, run_sql.py, check_neon.py
- Neon dev 브랜치 재생성 및 raw 테이블 재구축

### 막힌 것과 해결
1. **UUID가 바이트로 저장됨**
   - Parquet에 UUID 타입이 없어 b'\xfa\x10...' 형태로 저장 → 적재 시 타입 오류
   - astype("string")으로 해결. astype(str)은 NULL을 "None" 문자열로
     바꾸므로 사용 불가 (clickstream.customer_id 30% NULL)
2. **INSERT 방식이 너무 느리고 에러가 거대함**
   - 47,216행 = 파라미터 120만 개. 실패 시 에러 메시지가 수십만 자가 되어
     PowerShell 콘솔까지 깨짐(PSReadLine 예외)
   - COPY 방식으로 전환 + 에러 출력 600자 제한
3. **dev 브랜치 삭제로 접속 실패**
   - .env가 존재하지 않는 엔드포인트를 가리킴 → 브랜치 재생성 후 갱신
4. **clickstream FK 2개 누락**
   - CREATE TABLE IF NOT EXISTS 는 테이블이 있으면 통째로 건너뛰므로
     제약 누락을 고치지 못함 → 09_drop_raw.sql 추가해 DROP 후 재생성
5. **quantity 컬럼이 "4.0"으로 적재 거부**
   - pandas는 NULL이 있는 정수 컬럼을 float로 승격 (orders.quantity 15% NULL)
   - astype("Int64") (nullable 정수)로 해결
   - 주의: age_at_signup, resolution_time_hours 는 numeric이라 소수가 정상

### 현재 상태
- dev/main 스키마 동일: CHECK 25, PK 10, FK 6
- dev 초기 적재 완료 (product 500 / customers 47,216 / devices 50,798)
- orders 적재에서 FK 위반으로 중단 — 가입 전 주문 268건 때문. 의도된 동작

### 다음 할 일
1. validate.py 작성
   - 참조 확인 방식: DB에서 id 목록만 조회 + 이번 배치 신규 고객 합산
   - 1차 룰 9개: X01~X04(FK), C03(PK중복), C05(0건), D01(NULL률),
     D02(신규 범주값), D05(적재량 급변)
   - 통과분 → data/batch/clean/, 위반분 → quarantine.rejected_rows,
     검사 결과 → mart.dq_daily
2. load.py 가 clean/ 을 읽도록 경로 변경
3. 파이프라인 순서: replay → validate → load

## Day 3 | 날짜 체계 정리
- 세 종류의 날짜가 공존한다:
  - 작업일: 실제 개발한 날 (worklog 기준)
  - batch_date: 배치 실행일. 작업일과 동일하며 raw/mart의 파티션 키
  - 논리 날짜: 원본 이벤트 날짜(2025-09-02~12-02). 재생기가 자동 계산
- CLI 인자 `--date` 는 batch_date 를 받는다 (논리 날짜 아님)
- 대시보드 축: 품질 지표는 batch_date, 매출 추이는 order_date 기준

### 한 일
- replay.py / validate.py / load.py 작성 및 파이프라인 관통
- 검증 룰 9종 구현 (C03/C05, X01~X06, D01/D02/D05/D08)
- 1일차·2일차 적재 성공
  - raw.orders 772행, clickstream 7,220행
  - quarantine.rejected_rows 109행, mart.dq_daily 72행

### 검증 결과 (기준선 확보)
| 룰 | 대상 | 1일차 | 2일차 |
|---|---|---|---|
| X01 | orders.customer_id | 7 (1.7%) | 6 (1.6%) |
| X03 | support_tickets.customer_id | 1 (2.5%) | 3 (7.9%) |
| X04 | clickstream.customer_id | 14 (0.8%) | 78 (1.4%) |

- 세 테이블 모두 1~2%대 고아행. "가입 전 활동"이 데이터셋 전반에 존재
- D08이 2일차 support_tickets에서 발동 (7.9% > 임계 3%).
  38건 규모에서 1건 차이가 2.6%p를 움직임
  → **소규모 테이블은 비율 대신 절대 건수 기준을 검토할 것**

### 막힌 것
- 시행착오 6건 (02_decision_log 참조)
- 파이썬 컴파일 캐시로 수정이 반영되지 않는 문제 → `-B` 옵션 상시 사용
- 탭/공백 혼용으로 IndentationError 반복 → VS Code 들여쓰기 설정 고정

### 다음 할 일
1. aggregate.py — mart.daily_kpi 집계
2. batch_log 기록 (현재 0행)
3. D05 기준선 조정 (clickstream 첫날 1,822 vs 기준 5,400)

# Day 3 — 적재 파이프라인 구축과 시행착오

하루 동안 여섯 건의 실패를 겪었다. 각각 다른 층위의 문제였고,
그 과정이 이 프로젝트에서 가장 많이 배운 부분이다.

## 1. Parquet의 UUID 타입 손실
- 증상: 적재 시 `invalid input syntax for type uuid`.
  값이 `b'\xfa\x10\xca\xb0...'` 형태의 16바이트 이진값
- 원인: Parquet에 UUID 타입이 없어 저장 시 바이트로 떨어지고,
  다시 읽으면 무엇인지 알 수 없는 이진값이 된다
- 조치: 추출 단계에서 `astype("string")`으로 문자열 변환.
  적재 시 Postgres가 다시 uuid로 해석한다
- 주의: `astype(str)`은 NULL을 `"None"` 문자열로 바꾼다.
  clickstream.customer_id는 30%가 NULL이라 치명적이었을 것
- 비용: Parquet 42.3 → 77.6 MB (16바이트 → 36글자). DB 용량은 불변

## 2. NULL이 있는 정수 컬럼의 소수점 승격
- 증상: `invalid input syntax for type smallint: "4.0"`
- 원인: pandas의 기본 정수 타입은 NULL을 표현할 수 없어,
  결측이 하나라도 있으면 컬럼 전체가 float로 승격된다 (4 → 4.0)
- 조치: 적재 직전 nullable 정수 타입(`Int64`)으로 되돌린다
- 주의: `age_at_signup`은 numeric(5,1)이라 소수가 정상. 구분 필요

## 3. 초기 적재와 검증의 순서 역전
- 증상: 1일차 orders 411건 전량 격리, clickstream 92% 격리
- 원인: 실행 순서가 replay → validate → load 인데 마스터 초기 적재가
  load 안에 있어, 검증 시점에 참조 대상이 비어 있었다
  (참조 crm_customers 16건, product_catalog 0건)
- 조치: `--init-only` 옵션으로 초기 적재를 사전 단계로 분리
- 배운 것: 검증은 "무엇을 기준으로 검증하는가"가 먼저 준비되어야 한다.
  그리고 **격리율 100%는 데이터 문제가 아니라 파이프라인 문제의 신호다**

## 4. undated 풀 소비 구간 중복
- 증상: 2일차 적재 시 orders_pkey 중복. 어제 넣은 주문이 오늘도 유입
- 원인: 시작 위치를 `day_index * n_needed`로 계산했는데, n_needed가
  날마다 다르므로(그날 dated 건수에 비례) 구간이 겹쳤다
  - 1일차 0~122(n=123) / 2일차 112~223(n=112) → 112~122 중복
- 조치: 앞선 날들의 n_null 누적합을 offset으로 사용
- 배운 것: PK 제약이 없었다면 중복이 조용히 쌓였을 것.
  **DB 제약이 파이프라인 로직 버그를 잡아낸 사례**

## 5. 초기 적재와 일별 적재의 batch_date 충돌
- 증상: clean 파일에는 FK 위반이 없는데(파이썬 검증상 0건)
  COPY 단계에서 ForeignKeyViolation. 파이썬과 DB의 판단이 엇갈림
- 원인: 초기 적재와 일별 적재가 같은 batch_date를 사용.
  일별 적재의 첫 단계 `DELETE FROM raw.crm_customers WHERE batch_date = 오늘`이
  초기 적재분 47,216명을 통째로 삭제한 뒤 16명만 재적재 → FK 붕괴
- **진단이 어려웠던 이유**: 검증 스크립트는 트랜잭션 밖에서 조회하므로
  삭제 이전 상태를 보고 "문제 없음"으로 판정했다.
  트랜잭션 내부의 중간 상태는 외부에서 보이지 않는다
- 조치: 초기 적재의 batch_date를 재생 시작일 -1로 분리
- 보존 정책(90_retention.sql)에서도 마스터 테이블을 삭제 대상에서 제외

## 6. 마스터 테이블의 멱등성
- 증상: 9/28 재실행 시 `DELETE FROM crm_customers`가
  fk_clickstream_customer 위반. 9/29 배치의 clickstream이 해당 고객을 참조
- 원인: 마스터를 일별 삭제 대상에 포함했으나, 마스터는 이후 모든 배치가
  참조하는 누적 데이터라 날짜 단위로 지울 수 없다
- 조치:
  - 일별 DELETE를 이벤트 3개(clickstream/support_tickets/orders)로 한정
  - 마스터는 적재 전 `filter_existing`으로 기존 행을 제외해 PK 중복 회피

## 관통하는 원칙
5번과 6번은 같은 이야기다. **삭제 범위는 적재 단위와 정확히 일치해야 한다.**
이벤트는 날짜 단위로 적재되므로 날짜 단위로 지우고,
마스터는 누적 적재되므로 지우지 않고 중복만 거른다.
멱등성을 위한 DELETE가 의도보다 넓으면 파이프라인이
스스로 참조 무결성을 파괴한다.

## Day 4 | subprocess 호출 시 인코딩 문제
- 증상: run_batch.py 로 호출하면 UnicodeEncodeError('cp949').
  직접 실행할 때는 정상
- 원인: 출력이 파이프로 넘어갈 때 윈도우 기본 인코딩(cp949)이 적용됨.
  em dash(—)와 한글이 cp949 로 변환되지 않음
- 조치: subprocess 에 PYTHONIOENCODING=utf-8 환경변수 전달
- 함께 처리: PYTHONDONTWRITEBYTECODE=1 로 캐시 문제도 차단
- 배운 것: 터미널에서 직접 실행할 때와 파이프로 호출할 때 환경이 다르다.
  GitHub Actions(리눅스)에서는 기본이 UTF-8 이라 이 문제가 없지만,
  로컬 개발 환경과의 차이를 인지해야 한다

## Day 4 | Neon dev 브랜치 단일화
- dev 브랜치가 두 차례 소실 (무료 플랜 비기본 브랜치)
- 판단: dev/main 분리를 중단하고 단일 환경으로 운영
- 근거: 모든 데이터가 Parquet 에서 재생성 가능하고 초기화에 10초 소요.
  이 규모에서 환경 분리의 실익이 관리 비용보다 작다
- .env 의 DEV_DATABASE_URL 을 main 과 동일하게 설정.
  스크립트는 그대로 두어 나중에 분리가 필요하면 주소만 바꾸면 된다

  ## Day 4-5 (2026-09-29 ~ 30)

### 한 일
- run_batch.py: replay → validate → load → aggregate 를 한 줄로 실행,
  각 단계를 mart.batch_log 에 기록 (RUNNING → SUCCESS/FAILED)
- aggregate.py + sql/marts/10_daily_kpi.sql: 일별 KPI 집계
- 5일치 배치 실행 완료

### 현재 상태
| 테이블 | 행수 |
|---|---|
| raw.orders | 1,973 |
| raw.clickstream | 23,757 |
| raw.support_tickets | 179 |
| quarantine.rejected_rows | 339 |
| mart.dq_daily | 180 |
| mart.daily_kpi | 5 |
| mart.batch_log | 16 |

### 5일치 KPI
| 날짜 | 주문 | GMV | AOV | 금액결측 | 티켓 | 부정비율 |
|---|---|---|---|---|---|---|
| 9/28 | 404 | 13.3M | 52,860 | 17.6% | 39 | 25.6% |
| 9/29 | 368 | 15.4M | 66,752 | 14.4% | 35 | 25.7% |
| 9/30 | 398 | 14.4M | 53,628 | 13.3% | 45 | 35.6% |
| 10/1 | 393 | 11.6M | 50,391 | 19.1% | 25 | 44.0% |
| 10/2 | 410 | 12.7M | 50,100 | 18.1% | 35 | 37.1% |

관찰:
- X01(orders 고아행)이 6~10건으로 안정적 → **기준선 확보**
- 9/29 AOV 66,752는 다른 날의 1.3배. 주문 수는 최저(368)인데 GMV 최고
  → 고액 주문 소수가 평균을 끌어올린 것으로 보임
- 부정 비율이 25% → 44% 로 상승. 티켓이 25~45건 규모라
  흔들림일 수 있으나 추세라면 주목 필요
- 금액 결측률 13~19%. 기준선 17.2% 대비 D01 임계(±10%p) 안이라 경고 없음

### 막힌 것
- aggregate.py 가 SQL 을 세미콜론으로 나눌 때 주석 블록에 DELETE 문장이
  묻혀 사라짐 → PK 중복 발생. 주석 줄을 먼저 제거하도록 수정,
  문장이 2개 미만이면 실패하는 방어장치 추가
- run_batch.py 의 subprocess 인코딩 (cp949) → PYTHONIOENCODING=utf-8
- 여러 줄 커밋 메시지가 PowerShell 에서 깨짐 → -m 한 줄 또는 -m 반복 사용

### 다음 할 일
1. 시나리오 주입기 (config/scenarios.yml) — 품질 오염 재현
2. alert.py — Slack 발송
3. baseline.yml 조정: crm_customer_devices row_count 11 → 18
   (고객 1명이 기기 2대 이상 보유하는 경우 반영)

   ## Day 6 | 알람 설계

### 심각도 분류
| 등급 | 조건 | 억제 |
|---|---|---|
| P1 | batch_log 의 FAILED / RUNNING 잔류 / 기록 없음 | **없음** |
| P2 | D02, D08, C03 | 24시간 1회 |
| P3 | D01, D05, C05 | 24시간 1회 |

### 핵심 판단 세 가지

**1. 참조 무결성 룰은 기준선 배수로 판정**
X01/X03/X04 는 이 데이터셋의 상수에 가깝다(매일 5~80건 발동).
단순 FAIL 로 알리면 매일 울리는 소음이 되어 진짜 이상을 가린다.
평상시 기준선의 3~5배를 넘을 때만 알린다.
→ 알람을 끄는 게 아니라 "평소보다 심한 경우"를 거르는 설계

**2. P1 은 억제하지 않는다**
품질 경고는 하루 한 번이면 충분하지만 배치 장애는 매번 알려야 한다.
어제 울렸다고 오늘 안 울리면 장애가 방치된다.

**3. alert 실패는 배치를 중단시키지 않는다 (NON_FATAL)**
데이터는 이미 적재됐는데 Slack 일시 장애로 배치 전체를 FAILED 로
표시하면, 다음 날 P1 알람이 오탐으로 울린다.
실제로 alert.py 에 문법 오류가 있던 상태에서 배치가 끝까지
완주하는 것을 확인했다.

### 알람 메시지에 런북을 포함
담당자가 `D01` 만 보고는 무엇을 해야 할지 알 수 없다.
config/alerts.yml 의 rule_info 에 의미·추정 원인·조치를 정의하고
Slack 메시지에 함께 출력한다. docs/07_runbook.md 의 내용을
알람 자체에 끌어온 셈이다.

### 검증 결과
- 10/04 (평상시) → 알람 0건. X01/X03/X04 가 기준선 이하로 걸러짐
- 10/05 (bitcoin 주입) → P2 D02 발송
- 10/06 (결측률 주입) → P3 D01 발송
- 10/08 (배치 미실행) → P1 F01 발송
- 재실행 시 억제 작동 확인

## Day 7 | GitHub Actions 자동화

### 구성
- 매일 KST 07:00 (cron `0 22 * * *`, UTC 기준)
- workflow_dispatch 로 수동 실행 및 날짜 지정 가능
- 실행 로그를 Artifact 로 30일 보관

### 원본 데이터 전달 — GitHub Releases
- 문제: replay.py 가 읽는 Parquet 이 64MB 라 레포에 커밋할 수 없음
- 선택: Release(`data-v1`)에 zip 으로 분리, 워크플로가 매 실행 시 내려받음
- 버린 대안:
  - 레포 커밋 → clone 이 무거워지고 Git 이력에 영구 보존됨
  - DB 에 원본 보관 → Neon 무료 0.5GB 를 소진
  - 재생 로직을 SQL 로 이전 → 설계 변경 비용이 큼 (확장 과제)

### 시간대
- 러너는 UTC 이므로 `TZ: Asia/Seoul` 을 지정.
  없으면 `date +%F` 가 전날을 반환해 배치 날짜가 어긋난다

### 60일 비활성화 대응
- GitHub 은 레포에 60일간 활동이 없으면 예약 워크플로를 자동 중단한다
- 월요일 실행 시 docs/last_run.md 를 갱신·커밋해 활동을 남긴다
- 수동 실행(workflow_dispatch)에서는 커밋하지 않는다

### 첫 실행 결과
- 소요 1분 38초 (로컬 45초 + 의존성 설치·데이터 복원)
- 5단계 전부 SUCCESS