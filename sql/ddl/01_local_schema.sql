--
-- PostgreSQL database dump
--

\restrict vBzF3kDGoFcrTyoTudb9PogJ5i1dZEtfOXJgOHc3r2jXokZFJFxctcyMxLGwQ1X

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: portfolio; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA portfolio;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: clickstream; Type: TABLE; Schema: portfolio; Owner: -
--

CREATE TABLE portfolio.clickstream (
    event_id uuid NOT NULL,
    customer_id uuid,
    is_logged_in boolean NOT NULL,
    event_type character varying(20) NOT NULL,
    page_url text,
    page_type character varying(20),
    product_id character varying(9),
    event_time timestamp without time zone,
    session_id uuid NOT NULL,
    device_id uuid,
    ingest_run_id uuid NOT NULL,
    timestamp_raw text,
    page_url_raw text,
    time_flag text,
    device_flag text,
    CONSTRAINT ck_clickstream_event_type CHECK (((event_type)::text = ANY ((ARRAY['page_view'::character varying, 'search'::character varying, 'add_to_cart'::character varying, 'login'::character varying])::text[]))),
    CONSTRAINT ck_clickstream_login_flag CHECK ((is_logged_in = (customer_id IS NOT NULL))),
    CONSTRAINT ck_clickstream_page_pair CHECK (((page_url IS NULL) = (page_type IS NULL))),
    CONSTRAINT ck_clickstream_page_type CHECK (((page_type IS NULL) OR ((page_type)::text = ANY ((ARRAY['product_detail'::character varying, 'search'::character varying, 'category'::character varying, 'cart'::character varying, 'home'::character varying, 'other'::character varying])::text[])))),
    CONSTRAINT ck_clickstream_time_flag CHECK (((event_time IS NOT NULL) OR (time_flag IS NOT NULL))),
    CONSTRAINT ck_clickstream_time_range CHECK (((event_time IS NULL) OR ((event_time >= '2025-09-01 00:00:00'::timestamp without time zone) AND (event_time <= '2025-12-03 00:00:00'::timestamp without time zone))))
);


--
-- Name: TABLE clickstream; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON TABLE portfolio.clickstream IS '클릭스트림 이벤트 로그. 수집 구간 2025-09-02 ~ 2025-12-02 (92일)';


--
-- Name: COLUMN clickstream.customer_id; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.customer_id IS '행동한 고객. NULL은 오염이 아니라 비로그인 상태의 행동(30.1%)';


--
-- Name: COLUMN clickstream.is_logged_in; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.is_logged_in IS '로그인 여부(파생). customer_id 존재 여부로 계산';


--
-- Name: COLUMN clickstream.page_url; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.page_url IS '정규화된 URL. 원본은 page_url_raw (오염 5종: 끝슬래시·스킴과다·스킴누락·대문자·경로축약)';


--
-- Name: COLUMN clickstream.page_type; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.page_type IS '페이지 유형(파생). product_detail / search / category / cart / home';


--
-- Name: COLUMN clickstream.product_id; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.product_id IS 'page_url에서 추출한 상품 코드(파생). 검색·홈 페이지는 NULL';


--
-- Name: COLUMN clickstream.event_time; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.event_time IS '발생 시각(UTC). 표기 3종을 통일하고 상수·범위이탈·결측은 NULL 처리';


--
-- Name: COLUMN clickstream.session_id; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.session_id IS '[분석 사용 금지] 세션 역할 불가. 한 session_id 안에 고객 평균 43.7명, 기기 62.5개가 섞여 있음';


--
-- Name: COLUMN clickstream.device_id; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.device_id IS '[분석 사용 금지] CRM device_id와 다른 체계. crm_customer_devices와 일치 0건, 고유율 99.8%. 형식 오염 4,986건은 NULL';


--
-- Name: COLUMN clickstream.ingest_run_id; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.ingest_run_id IS '[분석 사용 금지] 적재 배치 번호. 50만 행 전체가 동일한 값';


--
-- Name: COLUMN clickstream.time_flag; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.time_flag IS 'NULL 처리 사유: 원본결측 / 상수값 / 범위이탈';


--
-- Name: COLUMN clickstream.device_flag; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.clickstream.device_flag IS 'device_id 처리 사유: 하이픈복원 / 형식오류(복원불가)';


--
-- Name: crm_customer_devices; Type: TABLE; Schema: portfolio; Owner: -
--

CREATE TABLE portfolio.crm_customer_devices (
    customer_id uuid NOT NULL,
    device_id uuid NOT NULL
);


--
-- Name: TABLE crm_customer_devices; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON TABLE portfolio.crm_customer_devices IS '고객-기기 관계 (1:N). 원본의 다중값 컬럼 device_id(s) 를 제1정규형으로 분리';


--
-- Name: crm_customers; Type: TABLE; Schema: portfolio; Owner: -
--

CREATE TABLE portfolio.crm_customers (
    customer_id uuid NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text,
    phone_number character varying(20),
    phone_ext character varying(10),
    gender character(1) NOT NULL,
    dob date NOT NULL,
    signup_date date NOT NULL,
    age_at_signup numeric(5,1),
    address text,
    city text,
    state text,
    country text,
    device_count smallint NOT NULL,
    source character varying(10) NOT NULL,
    first_name_raw text,
    last_name_raw text,
    email_raw text,
    phone_number_raw text,
    name_flag text,
    email_flag text,
    phone_flag text,
    age_flag text,
    CONSTRAINT ck_customer_dates CHECK ((signup_date >= dob)),
    CONSTRAINT ck_customer_device_count CHECK ((device_count >= 0)),
    CONSTRAINT ck_customer_dob_past CHECK ((dob <= CURRENT_DATE)),
    CONSTRAINT ck_customer_gender CHECK ((gender = ANY (ARRAY['M'::bpchar, 'F'::bpchar, 'O'::bpchar]))),
    CONSTRAINT ck_customer_source CHECK (((source)::text = ANY ((ARRAY['referral'::character varying, 'web'::character varying, 'app'::character varying])::text[])))
);


--
-- Name: TABLE crm_customers; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON TABLE portfolio.crm_customers IS '고객 마스터. 분석 전용 사본. 고객 응대·본인확인에는 _raw 컬럼 또는 원본 파일을 사용해야 함';


--
-- Name: COLUMN crm_customers.age_at_signup; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.crm_customers.age_at_signup IS '가입 시점 나이(파생 컬럼). signup_date - dob 로 계산';


--
-- Name: COLUMN crm_customers.state; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.crm_customers.state IS '주/도. country 와 모순되는 사례가 다수 — 분석 축으로 사용 비권장';


--
-- Name: COLUMN crm_customers.device_count; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.crm_customers.device_count IS '보유 기기 수(파생 컬럼). crm_customer_devices 의 행 수와 일치';


--
-- Name: COLUMN crm_customers.first_name_raw; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.crm_customers.first_name_raw IS '정제 전 원본 표기. 고객이 입력한 값 그대로';


--
-- Name: COLUMN crm_customers.age_flag; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.crm_customers.age_flag IS '가입 시점 14세 미만 등 확인이 필요한 사유';


--
-- Name: orders; Type: TABLE; Schema: portfolio; Owner: -
--

CREATE TABLE portfolio.orders (
    order_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    product_id character varying(9) NOT NULL,
    order_amount numeric(12,2),
    order_date date,
    payment_method character varying(10) NOT NULL,
    status character varying(10) NOT NULL,
    quantity smallint,
    order_amount_raw text,
    order_date_raw text,
    quantity_raw text,
    amount_flag text,
    date_flag text,
    quantity_flag text,
    payment_flag text,
    status_flag text,
    CONSTRAINT ck_orders_amount CHECK (((order_amount IS NULL) OR (order_amount > (0)::numeric))),
    CONSTRAINT ck_orders_amount_flag CHECK (((order_amount IS NOT NULL) OR (amount_flag IS NOT NULL))),
    CONSTRAINT ck_orders_date CHECK (((order_date IS NULL) OR (order_date <= CURRENT_DATE))),
    CONSTRAINT ck_orders_date_flag CHECK (((order_date IS NOT NULL) OR (date_flag IS NOT NULL))),
    CONSTRAINT ck_orders_payment CHECK (((payment_method)::text = ANY ((ARRAY['card'::character varying, 'cash'::character varying, 'upi'::character varying, 'wallet'::character varying])::text[]))),
    CONSTRAINT ck_orders_quantity CHECK (((quantity IS NULL) OR ((quantity >= 1) AND (quantity <= 5)))),
    CONSTRAINT ck_orders_status CHECK (((status)::text = ANY ((ARRAY['success'::character varying, 'failed'::character varying, 'refunded'::character varying])::text[])))
);


--
-- Name: TABLE orders; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON TABLE portfolio.orders IS '주문 거래. 정제본 orders_cleaned.csv';


--
-- Name: COLUMN orders.order_amount; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.orders.order_amount IS '주문 금액. 상수값(0 / 1,200 / -50)은 시스템 대체값으로 판단해 NULL 처리';


--
-- Name: COLUMN orders.order_date; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.orders.order_date IS '주문일. 상수형 오염·적재시각 추정값은 NULL 처리 (사유는 date_flag)';


--
-- Name: COLUMN orders.order_date_raw; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.orders.order_date_raw IS '정제 전 원본 문자열. NULL 처리된 값의 추적용';


--
-- Name: product_catalog; Type: TABLE; Schema: portfolio; Owner: -
--

CREATE TABLE portfolio.product_catalog (
    product_id character varying(9) NOT NULL,
    product_name text NOT NULL,
    category character varying(20) NOT NULL,
    price numeric(12,2),
    name_flag text,
    price_flag text,
    CONSTRAINT ck_product_category CHECK (((category)::text = ANY ((ARRAY['automotive'::character varying, 'beauty'::character varying, 'clothing'::character varying, 'electronics'::character varying, 'home'::character varying, 'kitchen'::character varying, 'sports'::character varying, 'toys'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT ck_product_id_format CHECK (((product_id)::text ~ '^PROD-[0-9]{4}$'::text)),
    CONSTRAINT ck_product_price CHECK (((price IS NULL) OR (price > (0)::numeric)))
);


--
-- Name: TABLE product_catalog; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON TABLE portfolio.product_catalog IS '상품 마스터. 정제본 product_catalog_cleaned.csv';


--
-- Name: COLUMN product_catalog.price; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.product_catalog.price IS '판매 단가. 음수·0원은 정제 시 NULL 처리';


--
-- Name: COLUMN product_catalog.name_flag; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.product_catalog.name_flag IS '사람 확인이 필요한 상품명 사유(끝자리 숫자 등)';


--
-- Name: COLUMN product_catalog.price_flag; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.product_catalog.price_flag IS 'NULL 처리 사유 또는 고가 이상치 표시';


--
-- Name: support_tickets; Type: TABLE; Schema: portfolio; Owner: -
--

CREATE TABLE portfolio.support_tickets (
    ticket_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    issue_type character varying(10) NOT NULL,
    sentiment character varying(10) NOT NULL,
    ticket_created timestamp without time zone,
    ticket_resolved timestamp without time zone,
    resolution_time_hours numeric(6,1) NOT NULL,
    support_agent text NOT NULL,
    ticket_created_raw text,
    ticket_resolved_raw text,
    support_agent_raw text,
    date_flag text,
    issue_flag text,
    sentiment_flag text,
    agent_flag text,
    CONSTRAINT ck_tickets_date_pair CHECK (((ticket_created IS NULL) = (ticket_resolved IS NULL))),
    CONSTRAINT ck_tickets_issue CHECK (((issue_type)::text = ANY ((ARRAY['payment'::character varying, 'delay'::character varying, 'refund'::character varying, 'product'::character varying])::text[]))),
    CONSTRAINT ck_tickets_order CHECK (((ticket_created IS NULL) OR (ticket_resolved IS NULL) OR (ticket_resolved >= ticket_created))),
    CONSTRAINT ck_tickets_resolution CHECK ((resolution_time_hours > (0)::numeric)),
    CONSTRAINT ck_tickets_sentiment CHECK (((sentiment)::text = ANY ((ARRAY['positive'::character varying, 'neutral'::character varying, 'negative'::character varying])::text[])))
);


--
-- Name: TABLE support_tickets; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON TABLE portfolio.support_tickets IS '고객 지원 티켓. 정제본 support_tickets_cleaned.csv';


--
-- Name: COLUMN support_tickets.ticket_created; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.support_tickets.ticket_created IS '접수 일시. 12,626건은 resolution_time_hours 기준 계산으로 복원된 값 (date_flag 확인 필요)';


--
-- Name: COLUMN support_tickets.resolution_time_hours; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.support_tickets.resolution_time_hours IS '처리 소요 시간. 원본이 완전히 깨끗한 컬럼으로, 날짜 복원의 기준이 되었다';


--
-- Name: COLUMN support_tickets.date_flag; Type: COMMENT; Schema: portfolio; Owner: -
--

COMMENT ON COLUMN portfolio.support_tickets.date_flag IS '접수일시_복원(...) / 해결일시_복원(...) / 복원불가(양쪽무효). NULL이면 원본 그대로';


--
-- Name: clickstream pk_clickstream; Type: CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.clickstream
    ADD CONSTRAINT pk_clickstream PRIMARY KEY (event_id);


--
-- Name: crm_customers pk_crm_customers; Type: CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.crm_customers
    ADD CONSTRAINT pk_crm_customers PRIMARY KEY (customer_id);


--
-- Name: crm_customer_devices pk_customer_devices; Type: CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.crm_customer_devices
    ADD CONSTRAINT pk_customer_devices PRIMARY KEY (customer_id, device_id);


--
-- Name: orders pk_orders; Type: CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.orders
    ADD CONSTRAINT pk_orders PRIMARY KEY (order_id);


--
-- Name: product_catalog pk_product_catalog; Type: CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.product_catalog
    ADD CONSTRAINT pk_product_catalog PRIMARY KEY (product_id);


--
-- Name: support_tickets pk_support_tickets; Type: CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.support_tickets
    ADD CONSTRAINT pk_support_tickets PRIMARY KEY (ticket_id);


--
-- Name: idx_clickstream_customer; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_clickstream_customer ON portfolio.clickstream USING btree (customer_id);


--
-- Name: idx_clickstream_pagetype; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_clickstream_pagetype ON portfolio.clickstream USING btree (page_type);


--
-- Name: idx_clickstream_product; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_clickstream_product ON portfolio.clickstream USING btree (product_id);


--
-- Name: idx_clickstream_time; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_clickstream_time ON portfolio.clickstream USING btree (event_time);


--
-- Name: idx_clickstream_type; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_clickstream_type ON portfolio.clickstream USING btree (event_type);


--
-- Name: idx_devices_device; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_devices_device ON portfolio.crm_customer_devices USING btree (device_id);


--
-- Name: idx_orders_customer; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_orders_customer ON portfolio.orders USING btree (customer_id);


--
-- Name: idx_orders_date; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_orders_date ON portfolio.orders USING btree (order_date);


--
-- Name: idx_orders_product; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_orders_product ON portfolio.orders USING btree (product_id);


--
-- Name: idx_orders_status; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_orders_status ON portfolio.orders USING btree (status);


--
-- Name: idx_tickets_created; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_tickets_created ON portfolio.support_tickets USING btree (ticket_created);


--
-- Name: idx_tickets_customer; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_tickets_customer ON portfolio.support_tickets USING btree (customer_id);


--
-- Name: idx_tickets_issue; Type: INDEX; Schema: portfolio; Owner: -
--

CREATE INDEX idx_tickets_issue ON portfolio.support_tickets USING btree (issue_type);


--
-- Name: clickstream fk_clickstream_customer; Type: FK CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.clickstream
    ADD CONSTRAINT fk_clickstream_customer FOREIGN KEY (customer_id) REFERENCES portfolio.crm_customers(customer_id);


--
-- Name: clickstream fk_clickstream_product; Type: FK CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.clickstream
    ADD CONSTRAINT fk_clickstream_product FOREIGN KEY (product_id) REFERENCES portfolio.product_catalog(product_id);


--
-- Name: crm_customer_devices fk_devices_customer; Type: FK CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.crm_customer_devices
    ADD CONSTRAINT fk_devices_customer FOREIGN KEY (customer_id) REFERENCES portfolio.crm_customers(customer_id) ON DELETE CASCADE;


--
-- Name: orders fk_orders_customer; Type: FK CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.orders
    ADD CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES portfolio.crm_customers(customer_id);


--
-- Name: orders fk_orders_product; Type: FK CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.orders
    ADD CONSTRAINT fk_orders_product FOREIGN KEY (product_id) REFERENCES portfolio.product_catalog(product_id);


--
-- Name: support_tickets fk_tickets_customer; Type: FK CONSTRAINT; Schema: portfolio; Owner: -
--

ALTER TABLE ONLY portfolio.support_tickets
    ADD CONSTRAINT fk_tickets_customer FOREIGN KEY (customer_id) REFERENCES portfolio.crm_customers(customer_id);


--
-- PostgreSQL database dump complete
--

\unrestrict vBzF3kDGoFcrTyoTudb9PogJ5i1dZEtfOXJgOHc3r2jXokZFJFxctcyMxLGwQ1X

