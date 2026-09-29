-- 모든 데이터를 비운다. 개발 중 재시작용.
-- TRUNCATE 는 FK 의존관계를 자동으로 처리하고 DELETE 보다 빠르다.
--
-- 주의: 되돌릴 수 없다. main 에 실행하기 전 대상을 반드시 확인할 것.

TRUNCATE raw.clickstream, raw.support_tickets, raw.orders,
         raw.crm_customer_devices, raw.crm_customers, raw.product_catalog;
TRUNCATE quarantine.rejected_rows;
TRUNCATE mart.dq_daily, mart.daily_kpi, mart.batch_log;