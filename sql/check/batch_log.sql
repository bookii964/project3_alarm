SELECT batch_date, step, status, row_count, duration_sec, started_at
FROM mart.batch_log
ORDER BY batch_date DESC, started_at
LIMIT 20;