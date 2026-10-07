-- 품질 추세

SELECT batch_date,
       count(*) FILTER (WHERE status = 'FAIL') AS fail,
       count(*) FILTER (WHERE status = 'WARN') AS warn,
       count(*) FILTER (WHERE status = 'PASS') AS pass
FROM mart.dq_daily
GROUP BY batch_date
ORDER BY batch_date;