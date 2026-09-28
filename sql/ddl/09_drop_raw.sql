-- raw 테이블을 전부 지운다. 데이터가 비어 있을 때만 사용할 것.
-- CASCADE 로 FK 의존관계를 함께 정리한다.
DROP TABLE IF EXISTS raw.clickstream CASCADE;
DROP TABLE IF EXISTS raw.support_tickets CASCADE;
DROP TABLE IF EXISTS raw.orders CASCADE;
DROP TABLE IF EXISTS raw.crm_customer_devices CASCADE;
DROP TABLE IF EXISTS raw.crm_customers CASCADE;
DROP TABLE IF EXISTS raw.product_catalog CASCADE;