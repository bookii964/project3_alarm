-- 일별 KPI 집계
--
-- batch_date 기준으로 집계한다. 파이프라인 관점의 지표이며
-- mart.batch_log, mart.dq_daily 와 같은 축에서 비교할 수 있다.
--
-- 핵심 설계: 지표와 함께 "모수"를 기록한다.
--   order_amount 의 17.2%가 NULL 이므로 GMV 는 전체 주문의 합이 아니다.
--   coverage 컬럼이 그 비율을 명시해, 대시보드에서
--   "GMV 1억 2천만원 (전체의 82.8% 기준)" 처럼 표시할 수 있게 한다.
--
-- 실행: python -B src/aggregate.py dev --date 2026-09-28

DELETE FROM mart.daily_kpi WHERE batch_date = :d;

INSERT INTO mart.daily_kpi (
    batch_date, order_count, gmv, aov, order_null_rate,
    ticket_count, ticket_negative_rate, avg_resolution_hours,
    event_count, computed_at
)
SELECT
    :d AS batch_date,

    -- 거래
    (SELECT count(*) FROM raw.orders WHERE batch_date = :d),
    (SELECT sum(order_amount) FROM raw.orders
      WHERE batch_date = :d AND status = 'success'),
    (SELECT avg(order_amount) FROM raw.orders
      WHERE batch_date = :d AND status = 'success'),
    -- 모수: order_amount 결측률
    (SELECT avg(CASE WHEN order_amount IS NULL THEN 1.0 ELSE 0.0 END)
       FROM raw.orders WHERE batch_date = :d),

    -- CS
    (SELECT count(*) FROM raw.support_tickets WHERE batch_date = :d),
    (SELECT avg(CASE WHEN sentiment = 'negative' THEN 1.0 ELSE 0.0 END)
       FROM raw.support_tickets WHERE batch_date = :d),
    (SELECT avg(resolution_time_hours) FROM raw.support_tickets
      WHERE batch_date = :d),

    -- 행동
    (SELECT count(*) FROM raw.clickstream WHERE batch_date = :d),

    now();