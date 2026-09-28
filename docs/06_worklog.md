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