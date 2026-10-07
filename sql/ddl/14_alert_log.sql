-- 알람 발송 이력
--
-- 억제(suppression) 판정의 근거이자, 대시보드의 재료가 된다.
-- "언제 무엇을 알렸나"를 조회할 수 있어야 알람 설계를 개선할 수 있다.

CREATE TABLE IF NOT EXISTS mart.alert_log (
    id          bigserial   PRIMARY KEY,
    batch_date  date        NOT NULL,
    severity    text        NOT NULL,
    rule_id     text,
    table_name  text,
    message     text        NOT NULL,
    channel     text        NOT NULL,
    sent_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_alert_severity CHECK (severity IN ('P1', 'P2', 'P3'))
);

CREATE INDEX IF NOT EXISTS ix_alert_batch ON mart.alert_log (batch_date);
CREATE INDEX IF NOT EXISTS ix_alert_dedup
    ON mart.alert_log (rule_id, table_name, sent_at);