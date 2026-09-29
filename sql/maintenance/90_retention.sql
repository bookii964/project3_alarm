-- raw 데이터 보존 정책
--
-- 순환 재생 2회차부터 용량이 계속 누적되므로, 90일이 지난 raw 데이터를
-- 삭제해 무료 플랜(0.5GB) 범위 안에서 평형을 유지한다.
--
-- 삭제하지 않는 것:
--   mart.*       집계 결과. 용량이 작고 품질 지표 시계열이 핵심 산출물
--   quarantine.* 격리 이력. 사후 조사와 D08 룰 기준선에 필요
--
-- 삭제 순서는 FK 역순이어야 한다 (참조하는 쪽 먼저).
-- 실행: python src/run_sql.py <dev|main> sql/maintenance/90_retention.sql

BEGIN;

DELETE FROM raw.clickstream
 WHERE batch_date < CURRENT_DATE - INTERVAL '90 days';

DELETE FROM raw.support_tickets
 WHERE batch_date < CURRENT_DATE - INTERVAL '90 days';

DELETE FROM raw.orders
 WHERE batch_date < CURRENT_DATE - INTERVAL '90 days';

-- crm_customers / crm_customer_devices / product_catalog 는 마스터라 삭제하지 않는다.
-- 이벤트가 참조하고 있고, 초기 적재분(batch_date = 재생시작일-1)은
-- 재적재 경로가 없어 지우면 복구할 수 없다.

COMMIT;