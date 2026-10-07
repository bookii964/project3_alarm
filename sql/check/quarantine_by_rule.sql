-- 룰별 격리

SELECT rule_id, table_name, count(*) AS n
FROM quarantine.rejected_rows
GROUP BY 1, 2
ORDER BY n DESC;