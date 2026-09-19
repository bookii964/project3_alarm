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