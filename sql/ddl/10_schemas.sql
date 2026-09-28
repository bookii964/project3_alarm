-- 스키마 생성
-- raw        : 도착한 데이터. 제약조건이 최후 방어선 역할
-- quarantine : 검증에 걸린 불량 행. 제약조건 없음
-- mart       : 집계 결과. 대시보드가 읽는 곳

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS quarantine;
CREATE SCHEMA IF NOT EXISTS mart;

COMMENT ON SCHEMA raw IS '일별 적재 데이터. batch_date 기준 멱등 적재';
COMMENT ON SCHEMA quarantine IS '검증 실패 행 격리. 제약조건을 두지 않음';
COMMENT ON SCHEMA mart IS '집계 결과. dq_daily / daily_kpi / batch_log';