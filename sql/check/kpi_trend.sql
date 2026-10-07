-- KPI 추세

SELECT batch_date, order_count, gmv, aov,
       round(order_null_rate * 100, 1) AS null_pct,
       ticket_count, event_count
FROM mart.daily_kpi
ORDER BY batch_date;
