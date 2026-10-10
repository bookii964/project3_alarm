-- 스키마별 테이블 목록과 크기

SELECT
    schemaname AS schema,
    relname    AS table_name,
    n_live_tup AS est_rows,
    pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_stat_user_tables
WHERE schemaname IN ('raw', 'quarantine', 'mart')
ORDER BY schemaname, relname