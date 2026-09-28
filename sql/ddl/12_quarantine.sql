-- 검증에 걸린 행을 원본 그대로 보관한다.
-- 제약조건을 두지 않는 것이 핵심: 규칙을 어긴 행을 받는 것이 목적이므로
-- 규칙이 걸려 있으면 애초에 들어올 수 없다.

CREATE TABLE IF NOT EXISTS quarantine.rejected_rows (
    id          bigserial   PRIMARY KEY,
    batch_date  date        NOT NULL,
    table_name  text        NOT NULL,
    rule_id     text        NOT NULL,
    reason      text,
    payload     jsonb       NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_rejected_batch
    ON quarantine.rejected_rows (batch_date);
CREATE INDEX IF NOT EXISTS ix_rejected_table_rule
    ON quarantine.rejected_rows (table_name, rule_id);

COMMENT ON COLUMN quarantine.rejected_rows.payload
    IS '원본 행 전체를 JSON으로 보관. 테이블마다 구조가 달라도 하나로 받기 위함';