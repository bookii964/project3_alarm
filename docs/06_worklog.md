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