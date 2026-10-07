-- 품질 지표 시계열. 이 프로젝트의 1순위 산출물
CREATE TABLE IF NOT EXISTS mart.dq_daily (
    batch_date   date    NOT NULL,
    table_name   text    NOT NULL,
    rule_id      text    NOT NULL,
    column_name  text    NOT NULL DEFAULT '',
    metric       text    NOT NULL,
    value        numeric,
    baseline     numeric,
    threshold    numeric,
    status       text    NOT NULL,
    checked_at   timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (batch_date, table_name, rule_id, column_name),
    CONSTRAINT ck_dq_status CHECK (status IN ('PASS', 'WARN', 'FAIL', 'ERROR'))
);

CREATE INDEX IF NOT EXISTS ix_dq_status ON mart.dq_daily (status, batch_date);

-- 비즈니스 KPI
CREATE TABLE IF NOT EXISTS mart.daily_kpi (
    batch_date        date PRIMARY KEY,
    order_count       integer,
    gmv               numeric(14,2),
    aov               numeric(12,2),
    order_null_rate   numeric(5,4),   -- 모수 표시용
    ticket_count      integer,
    ticket_negative_rate numeric(5,4),
    avg_resolution_hours numeric(8,2),
    event_count       integer,
    computed_at       timestamptz NOT NULL DEFAULT now()
);

-- 배치 실행 이력
CREATE TABLE IF NOT EXISTS mart.batch_log (
    batch_date   date        NOT NULL,
    step         text        NOT NULL,
    status       text        NOT NULL,
    row_count    integer,
    duration_sec numeric(8,2),
    message      text,
    started_at   timestamptz,
    finished_at  timestamptz,

    PRIMARY KEY (batch_date, step),
    CONSTRAINT ck_batch_status CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED', 'SKIPPED'))
);

CREATE TABLE mart.alert_log (
    id          bigserial PRIMARY KEY,
    batch_date  date        NOT NULL,
    severity    text        NOT NULL,   -- P1 / P2 / P3
    rule_id     text,
    table_name  text,
    message     text        NOT NULL,
    sent_at     timestamptz NOT NULL DEFAULT now(),
    channel     text        NOT NULL    -- slack / email
);