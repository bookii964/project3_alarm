-- raw 스키마: 매일 도착하는 데이터가 쌓이는 곳
--
-- 원본 portfolio 스키마와의 차이:
--   1. batch_date  : 적재 시각 축. 이벤트 시각(order_date 등)과 분리
--   2. ingested_at : 실제 적재 시점. 배치 소요시간 분석용
--   3. ck_clickstream_time_range 제외 — 원본 수집기간이 하드코딩되어
--      재생 시 전 행이 거부됨. 검증 룰 R15로 이관
--
-- 실행 순서: 10_schemas.sql → 11_raw_tables.sql

-- ---------------------------------------------------------------
-- 1. product_catalog (참조 없음)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.product_catalog (
    product_id      character varying(9)  PRIMARY KEY,
    product_name    text                  NOT NULL,
    category        character varying(20) NOT NULL,
    price           numeric(12,2),
    name_flag       text,
    price_flag      text,

    batch_date      date        NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_product_category CHECK (
        category IN ('automotive','beauty','clothing','electronics','home',
                     'kitchen','sports','toys','unknown')),
    CONSTRAINT ck_product_id_format CHECK (product_id ~ '^PROD-[0-9]{4}$'),
    CONSTRAINT ck_product_price CHECK (price IS NULL OR price > 0)
);

CREATE INDEX IF NOT EXISTS ix_product_batch ON raw.product_catalog (batch_date);

-- ---------------------------------------------------------------
-- 2. crm_customers (참조 없음)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.crm_customers (
    customer_id      uuid                  PRIMARY KEY,
    first_name       text                  NOT NULL,
    last_name        text                  NOT NULL,
    email            text,
    phone_number     character varying(20),
    phone_ext        character varying(10),
    gender           character(1)          NOT NULL,
    dob              date                  NOT NULL,
    signup_date      date                  NOT NULL,
    age_at_signup    numeric(5,1),
    address          text,
    city             text,
    state            text,
    country          text,
    device_count     smallint              NOT NULL,
    source           character varying(10) NOT NULL,
    first_name_raw   text,
    last_name_raw    text,
    email_raw        text,
    phone_number_raw text,
    name_flag        text,
    email_flag       text,
    phone_flag       text,
    age_flag         text,

    batch_date       date        NOT NULL,
    ingested_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_customer_dates        CHECK (signup_date >= dob),
    CONSTRAINT ck_customer_device_count CHECK (device_count >= 0),
    CONSTRAINT ck_customer_dob_past     CHECK (dob <= CURRENT_DATE),
    CONSTRAINT ck_customer_gender       CHECK (gender IN ('M','F','O')),
    CONSTRAINT ck_customer_source       CHECK (source IN ('referral','web','app'))
);

CREATE INDEX IF NOT EXISTS ix_customers_batch ON raw.crm_customers (batch_date);

-- ---------------------------------------------------------------
-- 3. crm_customer_devices (→ crm_customers)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.crm_customer_devices (
    customer_id  uuid        NOT NULL,
    device_id    uuid        NOT NULL,

    batch_date   date        NOT NULL,
    ingested_at  timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (customer_id, device_id),
    CONSTRAINT fk_devices_customer FOREIGN KEY (customer_id)
        REFERENCES raw.crm_customers (customer_id)
);

CREATE INDEX IF NOT EXISTS ix_devices_batch ON raw.crm_customer_devices (batch_date);

-- ---------------------------------------------------------------
-- 4. orders (→ crm_customers, product_catalog)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.orders (
    order_id         uuid                  PRIMARY KEY,
    customer_id      uuid                  NOT NULL,
    product_id       character varying(9)  NOT NULL,
    order_amount     numeric(12,2),
    order_date       date,
    payment_method   character varying(10) NOT NULL,
    status           character varying(10) NOT NULL,
    quantity         smallint,
    order_amount_raw text,
    order_date_raw   text,
    quantity_raw     text,
    amount_flag      text,
    date_flag        text,
    quantity_flag    text,
    payment_flag     text,
    status_flag      text,

    batch_date       date        NOT NULL,
    ingested_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_orders_amount      CHECK (order_amount IS NULL OR order_amount > 0),
    CONSTRAINT ck_orders_amount_flag CHECK (order_amount IS NOT NULL OR amount_flag IS NOT NULL),
    CONSTRAINT ck_orders_date        CHECK (order_date IS NULL OR order_date <= CURRENT_DATE),
    CONSTRAINT ck_orders_date_flag   CHECK (order_date IS NOT NULL OR date_flag IS NOT NULL),
    CONSTRAINT ck_orders_payment     CHECK (payment_method IN ('card','cash','upi','wallet')),
    CONSTRAINT ck_orders_quantity    CHECK (quantity IS NULL OR (quantity >= 1 AND quantity <= 5)),
    CONSTRAINT ck_orders_status      CHECK (status IN ('success','failed','refunded')),

    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
        REFERENCES raw.crm_customers (customer_id),
    CONSTRAINT fk_orders_product  FOREIGN KEY (product_id)
        REFERENCES raw.product_catalog (product_id)
);

CREATE INDEX IF NOT EXISTS ix_orders_batch    ON raw.orders (batch_date);
CREATE INDEX IF NOT EXISTS ix_orders_customer ON raw.orders (customer_id);
CREATE INDEX IF NOT EXISTS ix_orders_product  ON raw.orders (product_id);

-- ---------------------------------------------------------------
-- 5. support_tickets (→ crm_customers)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.support_tickets (
    ticket_id             uuid                  PRIMARY KEY,
    customer_id           uuid                  NOT NULL,
    issue_type            character varying(10) NOT NULL,
    sentiment             character varying(10) NOT NULL,
    ticket_created        timestamp,
    ticket_resolved       timestamp,
    resolution_time_hours numeric(6,1)          NOT NULL,
    support_agent         text                  NOT NULL,
    ticket_created_raw    text,
    ticket_resolved_raw   text,
    support_agent_raw     text,
    date_flag             text,
    issue_flag            text,
    sentiment_flag        text,
    agent_flag            text,

    batch_date            date        NOT NULL,
    ingested_at           timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_tickets_date_pair CHECK ((ticket_created IS NULL) = (ticket_resolved IS NULL)),
    CONSTRAINT ck_tickets_issue     CHECK (issue_type IN ('payment','delay','refund','product')),
    CONSTRAINT ck_tickets_order     CHECK (ticket_created IS NULL OR ticket_resolved IS NULL
                                           OR ticket_resolved >= ticket_created),
    CONSTRAINT ck_tickets_resolution CHECK (resolution_time_hours > 0),
    CONSTRAINT ck_tickets_sentiment CHECK (sentiment IN ('positive','neutral','negative')),

    CONSTRAINT fk_tickets_customer FOREIGN KEY (customer_id)
        REFERENCES raw.crm_customers (customer_id)
);

CREATE INDEX IF NOT EXISTS ix_tickets_batch ON raw.support_tickets (batch_date);

-- ---------------------------------------------------------------
-- 6. clickstream (→ crm_customers, product_catalog)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.clickstream (
    event_id       uuid                  PRIMARY KEY,
    customer_id    uuid,
    is_logged_in   boolean               NOT NULL,
    event_type     character varying(20) NOT NULL,
    page_url       text,
    page_type      character varying(20),
    product_id     character varying(9),
    event_time     timestamp,
    session_id     uuid                  NOT NULL,
    device_id      uuid,
    ingest_run_id  uuid                  NOT NULL,
    timestamp_raw  text,
    page_url_raw   text,
    time_flag      text,
    device_flag    text,

    batch_date     date        NOT NULL,
    ingested_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_clickstream_event_type CHECK (
        event_type IN ('page_view','search','add_to_cart','login')),
    CONSTRAINT ck_clickstream_login_flag CHECK (is_logged_in = (customer_id IS NOT NULL)),
    CONSTRAINT ck_clickstream_page_pair  CHECK ((page_url IS NULL) = (page_type IS NULL)),
    CONSTRAINT ck_clickstream_page_type  CHECK (
        page_type IS NULL OR page_type IN (
            'product_detail','search','category','cart','home','other')),
    CONSTRAINT ck_clickstream_time_flag  CHECK (event_time IS NOT NULL OR time_flag IS NOT NULL),

    CONSTRAINT fk_clickstream_customer FOREIGN KEY (customer_id)
        REFERENCES raw.crm_customers (customer_id),
    CONSTRAINT fk_clickstream_product  FOREIGN KEY (product_id)
        REFERENCES raw.product_catalog (product_id)
);

CREATE INDEX IF NOT EXISTS ix_clickstream_batch    ON raw.clickstream (batch_date);
CREATE INDEX IF NOT EXISTS ix_clickstream_customer ON raw.clickstream (customer_id);