# 테이블 정의서 · ERD 작성 내용

> **이 문서의 용도**
> Claude Design으로 테이블 정의서와 ERD를 제작하기 위한 **내용 정리본**이다.
> 여기에는 디자인 없이 들어갈 내용만 담는다.
>
> 모든 값은 PostgreSQL `portfolio` 스키마에서 직접 추출했다 (추측 아님).
> 추출 기준일 : 적재 완료 시점 / 총 930,554행 / 제약조건 67개

---

## 0. 문서 공통 정보

모든 테이블 시트에 동일하게 들어가는 머리말이다.

| 항목 | 값 |
|---|---|
| System Name | portfolio_db |
| Sub-system Name | ecommerce |
| Schema Name | portfolio |
| RDBMS | **PostgreSQL 16** |
| Author | (작성자명) |
| Created On | (작성일) |
| Modified On | (수정일) |

**예시 파일과 다른 점** : 예시는 MySQL 기준이었으나 이 프로젝트는 PostgreSQL이다. 자료형 표기가 다르므로(`varchar(50)` → `uuid`, `numeric(12,2)` 등) 그대로 쓰면 안 된다.

---

## 1. 시트 구성

예시 파일과 동일한 구조를 따르되, 이 프로젝트에 맞게 시트를 구성한다.

| 순서 | 시트명 | 내용 |
|---|---|---|
| 1 | ERD | 6개 테이블 관계도 |
| 2 | product_catalog | 상품 마스터 |
| 3 | crm_customers | 고객 마스터 |
| 4 | crm_customer_devices | 고객-기기 (1:N) |
| 5 | orders | 주문 거래 |
| 6 | support_tickets | CS 문의 |
| 7 | clickstream | 행동 로그 |

**ERD를 맨 앞에 두는 이유** : 전체 구조를 먼저 보여주고 개별 테이블로 들어가는 흐름이 읽기 쉽다. 예시 파일은 ERD가 마지막이었으나 순서를 바꾸는 편이 낫다.

### 각 시트의 섹션 구성 (예시 파일과 동일)

```
Table info          테이블 기본 정보
Column info         No / Logical Name / Physical Name / Data Type / Not Null / Default / Remark
Index info          No / Index Name / Column List / PK / Unique / Remark
Constraint info     No / Constraint Name / Type / Constraint Definition
FK info             No / FK Name / Column List / Reference Table / Reference Column
FK info (PK Side)   이 테이블을 참조하는 쪽
```

**Trigger info 섹션은 제외한다.** 이 프로젝트에는 트리거가 없다. 빈 섹션을 남기면 "작성하다 만 문서"로 보인다.

---

## 2. ERD 내용

### 2-1. 관계 구조

```
                    ┌──────────────────────┐
                    │   product_catalog    │
                    │   PK product_id      │
                    │   (500)              │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
         ┌────┴─────┐          │        ┌───────┴────────┐
         │  orders  │          │        │   clickstream  │
         │ PK order_id         │        │ PK event_id    │
         │ (300,000)│          │        │ (500,000)      │
         └────┬─────┘          │        └───────┬────────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────┴───────────┐
                    │    crm_customers     │
                    │    PK customer_id    │
                    │    (48,200)          │
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
   ┌──────────┴──────────┐         ┌────────────┴─────────┐
   │ crm_customer_devices│         │   support_tickets    │
   │ PK (customer_id,    │         │   PK ticket_id       │
   │     device_id)      │         │   (30,000)           │
   │ (51,854)            │         └──────────────────────┘
   └─────────────────────┘
```

### 2-2. 관계 목록 (6개)

| No | 부모 테이블 | 자식 테이블 | 관계 | 카디널리티 | FK 컬럼 | NULL 허용 |
|---|---|---|---|---|---|---|
| 1 | crm_customers | crm_customer_devices | 식별 | 1 : N | customer_id | 불가 |
| 2 | crm_customers | orders | 비식별 | 1 : N | customer_id | 불가 |
| 3 | crm_customers | support_tickets | 비식별 | 1 : N | customer_id | 불가 |
| 4 | crm_customers | clickstream | 비식별 | 1 : N | customer_id | **허용** |
| 5 | product_catalog | orders | 비식별 | 1 : N | product_id | 불가 |
| 6 | product_catalog | clickstream | 비식별 | 1 : N | product_id | **허용** |

**NULL 허용 FK 2개를 ERD에 표기해야 한다.** 점선이나 `0..N` 표기를 쓴다.

- `clickstream.customer_id` : 비로그인 이벤트 150,553건(30.1%)은 값이 없다
- `clickstream.product_id` : 상품 페이지가 아닌 이벤트 131,058건은 값이 없다

PostgreSQL의 FK는 값이 NULL이면 검사를 건너뛰므로, NULL 허용과 FK는 모순되지 않는다.

### 2-3. ERD에 함께 표기할 사항

**① 관계로 잇지 않는 컬럼 (중요)**

`clickstream.device_id`와 `crm_customer_devices.device_id`는 **이름이 같지만 다른 체계의 식별자**다. 실제 대조 결과 일치 0건이다.

→ ERD에 선을 긋지 않는다. 대신 **주석으로 "관계 없음"을 명시**한다. 표기가 없으면 보는 사람이 당연히 연결하려 한다.

**② 분석 사용 금지 컬럼**

`clickstream`의 `session_id`, `device_id`, `ingest_run_id` 3개는 값이 정상이지만 분석에 쓸 수 없다. ERD에서 회색 처리하거나 별도 범례로 구분한다.

**③ 테이블별 행 수**

각 엔티티 박스에 행 수를 함께 적으면 규모가 한눈에 들어온다.

**④ 파생 컬럼 표시**

원본에 없던 컬럼은 별도 표기(예: 이탤릭, `*` 기호)를 한다.

| 테이블 | 파생 컬럼 |
|---|---|
| crm_customers | age_at_signup, device_count, phone_ext |
| clickstream | is_logged_in, page_type, product_id |

---

## 3. 테이블별 내용

### 3-1. product_catalog

**Table info**

| 항목 | 값 |
|---|---|
| Logical Table Name | 상품 마스터 |
| Physical Table Name | product_catalog |
| Remark | 판매 상품 목록. 원본 product_catalog_dirty_30pct.csv 정제본 (500행) |

**Column info**

| No | Logical Name | Physical Name | Data Type | Not Null | Default | Remark |
|---|---|---|---|---|---|---|
| 1 | 상품번호 | product_id | varchar(9) | Yes | - | PK. `PROD-0000` 형식 |
| 2 | 상품명 | product_name | text | Yes | - | Title Case로 정규화 |
| 3 | 카테고리 | category | varchar(20) | Yes | - | 8종 + unknown. 원본 46종을 정규화 |
| 4 | 판매단가 | price | numeric(12,2) | No | - | 음수·0원 71건은 NULL 처리 |
| 5 | 상품명 확인사유 | name_flag | text | No | - | `숫자포함_확인필요` (19건) |
| 6 | 가격 확인사유 | price_flag | text | No | - | `음수대체값` / `0원` / `고가이상치_확인필요` |

**Index info**

| No | Index Name | Column List | PK | Unique |
|---|---|---|---|---|
| 1 | pk_product_catalog | product_id | Yes | Yes |

**Constraint info**

| No | Constraint Name | Type | Definition |
|---|---|---|---|
| 1 | pk_product_catalog | PK | PRIMARY KEY (product_id) |
| 2 | ck_product_id_format | CHECK | product_id ~ `'^PROD-[0-9]{4}$'` |
| 3 | ck_product_category | CHECK | category IN (automotive, beauty, clothing, electronics, home, kitchen, sports, toys, unknown) |
| 4 | ck_product_price | CHECK | price IS NULL OR price > 0 |

**FK info** : 없음
**FK info (PK Side)** : orders.product_id, clickstream.product_id 가 참조

---

### 3-2. crm_customers

**Table info**

| 항목 | 값 |
|---|---|
| Logical Table Name | 고객 마스터 |
| Physical Table Name | crm_customers |
| Remark | **분석 전용 사본.** 고객 응대·본인 확인에는 `_raw` 컬럼 또는 원본 파일을 사용할 것. 원본 50,000행 → 중복 1,800행 제거 후 48,200행 |

**Column info**

| No | Logical Name | Physical Name | Data Type | Not Null | Remark |
|---|---|---|---|---|---|
| 1 | 고객번호 | customer_id | uuid | Yes | PK |
| 2 | 이름 | first_name | text | Yes | 오타·특수문자 정제 |
| 3 | 성 | last_name | text | Yes | 오타·특수문자 정제 |
| 4 | 이메일 | email | text | No | 결측 1,000건 |
| 5 | 전화번호 | phone_number | varchar(20) | No | 숫자 10자리로 통일 |
| 6 | 내선번호 | phone_ext | varchar(10) | No | **파생.** 전화번호에서 분리 (28,875건) |
| 7 | 성별 | gender | char(1) | Yes | M / F / O |
| 8 | 생년월일 | dob | date | Yes | |
| 9 | 가입일 | signup_date | date | Yes | |
| 10 | 가입시 나이 | age_at_signup | numeric(5,1) | No | **파생.** signup_date − dob |
| 11 | 주소 | address | text | No | |
| 12 | 도시 | city | text | No | |
| 13 | 주/도 | state | text | No | **country와 모순. 분석 축 사용 비권장** |
| 14 | 국가 | country | text | No | 위와 동일 |
| 15 | 보유기기수 | device_count | smallint | Yes | **파생.** crm_customer_devices 건수 |
| 16 | 유입경로 | source | varchar(10) | Yes | referral / web / app |
| 17 | 이름(원본) | first_name_raw | text | No | **개인정보 원본 보존** |
| 18 | 성(원본) | last_name_raw | text | No | **개인정보 원본 보존** |
| 19 | 이메일(원본) | email_raw | text | No | **개인정보 원본 보존** |
| 20 | 전화번호(원본) | phone_number_raw | text | No | **개인정보 원본 보존** |
| 21 | 이름 확인사유 | name_flag | text | No | `이메일불일치_보류` |
| 22 | 이메일 확인사유 | email_flag | text | No | `공용이메일` / `결측` |
| 23 | 전화번호 확인사유 | phone_flag | text | No | `자릿수이상(≠10)` |
| 24 | 나이 확인사유 | age_flag | text | No | `가입시_14세미만` (2,046건) |

**Index info**

| No | Index Name | Column List | PK | Unique |
|---|---|---|---|---|
| 1 | pk_crm_customers | customer_id | Yes | Yes |

**Constraint info**

| No | Constraint Name | Type | Definition |
|---|---|---|---|
| 1 | pk_crm_customers | PK | PRIMARY KEY (customer_id) |
| 2 | ck_customer_gender | CHECK | gender IN ('M','F','O') |
| 3 | ck_customer_source | CHECK | source IN ('referral','web','app') |
| 4 | ck_customer_dates | CHECK | signup_date >= dob |
| 5 | ck_customer_dob_past | CHECK | dob <= CURRENT_DATE |
| 6 | ck_customer_device_count | CHECK | device_count >= 0 |

**FK info** : 없음
**FK info (PK Side)** : crm_customer_devices, orders, support_tickets, clickstream 이 참조 (4개)

---

### 3-3. crm_customer_devices

**Table info**

| 항목 | 값 |
|---|---|
| Logical Table Name | 고객 보유 기기 |
| Physical Table Name | crm_customer_devices |
| Remark | 원본의 다중값 컬럼 `device_id(s)`(세미콜론 구분)를 **제1정규형으로 분리**한 테이블 (51,854행) |

**Column info**

| No | Logical Name | Physical Name | Data Type | Not Null | Remark |
|---|---|---|---|---|---|
| 1 | 고객번호 | customer_id | uuid | Yes | PK(복합) / FK |
| 2 | 기기번호 | device_id | uuid | Yes | PK(복합) |

**Index info**

| No | Index Name | Column List | PK | Unique | Remark |
|---|---|---|---|---|---|
| 1 | pk_customer_devices | customer_id, device_id | Yes | Yes | **복합 기본키** |
| 2 | idx_devices_device | device_id | No | No | 기기 기준 조회용 |

**Constraint info**

| No | Constraint Name | Type | Definition |
|---|---|---|---|
| 1 | pk_customer_devices | PK | PRIMARY KEY (customer_id, device_id) |
| 2 | fk_devices_customer | FK | FOREIGN KEY (customer_id) REFERENCES crm_customers ON DELETE CASCADE |

**FK info**

| No | FK Name | Column List | Reference Table | Reference Column | 비고 |
|---|---|---|---|---|---|
| 1 | fk_devices_customer | customer_id | crm_customers | customer_id | ON DELETE CASCADE |

---

### 3-4. orders

**Table info**

| 항목 | 값 |
|---|---|
| Logical Table Name | 주문 거래 |
| Physical Table Name | orders |
| Remark | 주문 1건 = 1행. 300,000행 (행 삭제 없음) |

**Column info**

| No | Logical Name | Physical Name | Data Type | Not Null | Remark |
|---|---|---|---|---|---|
| 1 | 주문번호 | order_id | uuid | Yes | PK |
| 2 | 고객번호 | customer_id | uuid | Yes | FK → crm_customers |
| 3 | 상품번호 | product_id | varchar(9) | Yes | FK → product_catalog |
| 4 | 주문금액 | order_amount | numeric(12,2) | No | 상수 오염 3종 51,525건 NULL 처리 |
| 5 | 주문일 | order_date | date | No | 비표준 형식 90,000건 NULL 처리 |
| 6 | 결제수단 | payment_method | varchar(10) | Yes | 4종. 원본 11종을 정규화 |
| 7 | 주문상태 | status | varchar(10) | Yes | 3종. 원본 10종을 정규화 |
| 8 | 주문수량 | quantity | smallint | No | 1~5. 비정상 44,867건 NULL 처리 |
| 9 | 주문금액(원본) | order_amount_raw | text | No | **원본 보존** |
| 10 | 주문일(원본) | order_date_raw | text | No | **원본 보존** |
| 11 | 주문수량(원본) | quantity_raw | text | No | **원본 보존** |
| 12 | 금액 처리사유 | amount_flag | text | No | `상수값(0)` / `상수값(1,200)` / `상수값(-50)` / `원본결측` |
| 13 | 날짜 처리사유 | date_flag | text | No | `상수값(...)` / `적재시각추정(ISO8601)` / `원본결측` |
| 14 | 수량 처리사유 | quantity_flag | text | No | `음수` / `0개` / `공백(실질결측)` |
| 15 | 결제수단 처리사유 | payment_flag | text | No | 복원 실패 시 기록 (0건) |
| 16 | 상태 처리사유 | status_flag | text | No | 복원 실패 시 기록 (0건) |

**Index info**

| No | Index Name | Column List | PK | Unique |
|---|---|---|---|---|
| 1 | pk_orders | order_id | Yes | Yes |
| 2 | idx_orders_customer | customer_id | No | No |
| 3 | idx_orders_product | product_id | No | No |
| 4 | idx_orders_date | order_date | No | No |
| 5 | idx_orders_status | status | No | No |

**Constraint info**

| No | Constraint Name | Type | Definition |
|---|---|---|---|
| 1 | pk_orders | PK | PRIMARY KEY (order_id) |
| 2 | ck_orders_payment | CHECK | payment_method IN (card, cash, upi, wallet) |
| 3 | ck_orders_status | CHECK | status IN (success, failed, refunded) |
| 4 | ck_orders_amount | CHECK | order_amount IS NULL OR order_amount > 0 |
| 5 | ck_orders_quantity | CHECK | quantity IS NULL OR quantity BETWEEN 1 AND 5 |
| 6 | ck_orders_date | CHECK | order_date IS NULL OR order_date <= CURRENT_DATE |
| 7 | ck_orders_amount_flag | CHECK | order_amount IS NOT NULL OR amount_flag IS NOT NULL |
| 8 | ck_orders_date_flag | CHECK | order_date IS NOT NULL OR date_flag IS NOT NULL |

> 7·8번은 **"값을 비웠으면 반드시 사유가 있어야 한다"**는 규칙을 DB가 강제하는 제약이다.
> 정의서에 이 의도를 Remark로 적어두면 설계 의도가 드러난다.

**FK info**

| No | FK Name | Column List | Reference Table | Reference Column |
|---|---|---|---|---|
| 1 | fk_orders_customer | customer_id | crm_customers | customer_id |
| 2 | fk_orders_product | product_id | product_catalog | product_id |

---

### 3-5. support_tickets

**Table info**

| 항목 | 값 |
|---|---|
| Logical Table Name | 고객 지원 티켓 |
| Physical Table Name | support_tickets |
| Remark | 문의 1건 = 1행. 30,000행. **날짜 12,626건은 처리시간 기준 계산 복원값** (date_flag 확인 필요) |

**Column info**

| No | Logical Name | Physical Name | Data Type | Not Null | Remark |
|---|---|---|---|---|---|
| 1 | 티켓번호 | ticket_id | uuid | Yes | PK |
| 2 | 고객번호 | customer_id | uuid | Yes | FK → crm_customers |
| 3 | 문의유형 | issue_type | varchar(10) | Yes | 4종. 원본 35종을 정규화 |
| 4 | 고객감정 | sentiment | varchar(10) | Yes | 3종. 원본 18종을 정규화 |
| 5 | 접수일시 | ticket_created | timestamp | No | 복원 불가 2,687건 NULL |
| 6 | 해결일시 | ticket_resolved | timestamp | No | 위와 동일 |
| 7 | 처리시간(h) | resolution_time_hours | numeric(6,1) | Yes | **원본이 완전히 깨끗한 컬럼.** 날짜 복원의 기준 |
| 8 | 담당 상담원 | support_agent | text | Yes | 200명. 원본 1,556종 표기를 정규화 |
| 9 | 접수일시(원본) | ticket_created_raw | text | No | **원본 보존** |
| 10 | 해결일시(원본) | ticket_resolved_raw | text | No | **원본 보존** |
| 11 | 담당자(원본) | support_agent_raw | text | No | **원본 보존** |
| 12 | 날짜 처리사유 | date_flag | text | No | `접수일시_복원(...)` / `해결일시_복원(...)` / `복원불가(양쪽무효)` |
| 13 | 유형 처리사유 | issue_flag | text | No | 복원 실패 시 기록 (0건) |
| 14 | 감정 처리사유 | sentiment_flag | text | No | 복원 실패 시 기록 (0건) |
| 15 | 담당자 처리사유 | agent_flag | text | No | `글자중복이나_정상이름(유지)` (269건) |

**Index info**

| No | Index Name | Column List | PK | Unique |
|---|---|---|---|---|
| 1 | pk_support_tickets | ticket_id | Yes | Yes |
| 2 | idx_tickets_customer | customer_id | No | No |
| 3 | idx_tickets_created | ticket_created | No | No |
| 4 | idx_tickets_issue | issue_type | No | No |

**Constraint info**

| No | Constraint Name | Type | Definition |
|---|---|---|---|
| 1 | pk_support_tickets | PK | PRIMARY KEY (ticket_id) |
| 2 | ck_tickets_issue | CHECK | issue_type IN (payment, delay, refund, product) |
| 3 | ck_tickets_sentiment | CHECK | sentiment IN (positive, neutral, negative) |
| 4 | ck_tickets_resolution | CHECK | resolution_time_hours > 0 |
| 5 | ck_tickets_order | CHECK | ticket_resolved >= ticket_created |
| 6 | ck_tickets_date_pair | CHECK | (ticket_created IS NULL) = (ticket_resolved IS NULL) |

> 6번은 **"두 날짜는 함께 있거나 함께 없어야 한다"**는 제약이다.
> 한쪽만 있으면 복원 로직이 빠뜨린 케이스라는 뜻이므로 DB가 막는다.

**FK info**

| No | FK Name | Column List | Reference Table | Reference Column |
|---|---|---|---|---|
| 1 | fk_tickets_customer | customer_id | crm_customers | customer_id |

---

### 3-6. clickstream

**Table info**

| 항목 | 값 |
|---|---|
| Logical Table Name | 클릭스트림 이벤트 로그 |
| Physical Table Name | clickstream |
| Remark | 사용자 행동 1건 = 1행. 500,000행. **수집 구간 2025-09-02 ~ 2025-12-02 (92일)** — 다른 테이블(2년)과 기간이 다르므로 조인 분석 시 기간을 맞춰야 함 |

**Column info**

| No | Logical Name | Physical Name | Data Type | Not Null | Remark |
|---|---|---|---|---|---|
| 1 | 이벤트번호 | event_id | uuid | Yes | PK |
| 2 | 고객번호 | customer_id | uuid | No | FK. **NULL = 비로그인 행동** (150,553건, 30.1%) |
| 3 | 로그인여부 | is_logged_in | boolean | Yes | **파생.** customer_id 존재 여부 |
| 4 | 행동유형 | event_type | varchar(20) | Yes | page_view / search / add_to_cart / login. **purchase 없음** |
| 5 | 페이지 URL | page_url | text | No | 표기 오염 5종을 정규화 (고유값 3,020 → 504) |
| 6 | 페이지유형 | page_type | varchar(20) | No | **파생.** product_detail / search / category / cart / home |
| 7 | 상품번호 | product_id | varchar(9) | No | **파생.** page_url에서 추출 (368,942건) / FK |
| 8 | 발생시각 | event_time | timestamp | No | UTC. 표기 3종 통일. 신뢰 불가 60,090건 NULL |
| 9 | 세션번호 | session_id | uuid | Yes | **[분석 사용 금지]** 세션당 고객 43.7명·기기 62.5개 |
| 10 | 기기번호 | device_id | uuid | No | **[분석 사용 금지]** CRM 기기와 일치 0건. 형식오염 4,986건 NULL |
| 11 | 적재배치번호 | ingest_run_id | uuid | Yes | **[분석 사용 금지]** 전 행 동일값 |
| 12 | 발생시각(원본) | timestamp_raw | text | No | **원본 보존** |
| 13 | 페이지URL(원본) | page_url_raw | text | No | **원본 보존** |
| 14 | 시각 처리사유 | time_flag | text | No | `원본결측` / `상수값` / `범위이탈` |
| 15 | 기기 처리사유 | device_flag | text | No | `하이픈복원` / `형식오류(복원불가)` |

**Index info**

| No | Index Name | Column List | PK | Unique |
|---|---|---|---|---|
| 1 | pk_clickstream | event_id | Yes | Yes |
| 2 | idx_clickstream_customer | customer_id | No | No |
| 3 | idx_clickstream_product | product_id | No | No |
| 4 | idx_clickstream_time | event_time | No | No |
| 5 | idx_clickstream_type | event_type | No | No |
| 6 | idx_clickstream_pagetype | page_type | No | No |

**Constraint info**

| No | Constraint Name | Type | Definition |
|---|---|---|---|
| 1 | pk_clickstream | PK | PRIMARY KEY (event_id) |
| 2 | ck_clickstream_event_type | CHECK | event_type IN (page_view, search, add_to_cart, login) |
| 3 | ck_clickstream_page_type | CHECK | page_type IS NULL OR page_type IN (product_detail, search, category, cart, home, other) |
| 4 | ck_clickstream_login_flag | CHECK | is_logged_in = (customer_id IS NOT NULL) |
| 5 | ck_clickstream_page_pair | CHECK | (page_url IS NULL) = (page_type IS NULL) |
| 6 | ck_clickstream_time_range | CHECK | event_time IS NULL OR (event_time BETWEEN '2025-09-01' AND '2025-12-03') |
| 7 | ck_clickstream_time_flag | CHECK | event_time IS NOT NULL OR time_flag IS NOT NULL |

> 4·5번은 **파생 컬럼의 정합성**을 DB가 검산하는 제약이다.
> Python에서 계산한 값이 맞는지 DB가 한 번 더 확인한다.

**FK info**

| No | FK Name | Column List | Reference Table | Reference Column | 비고 |
|---|---|---|---|---|---|
| 1 | fk_clickstream_customer | customer_id | crm_customers | customer_id | NULL 허용 |
| 2 | fk_clickstream_product | product_id | product_catalog | product_id | NULL 허용 |

---

## 4. 정의서에 함께 넣을 부가 정보

예시 파일에는 없지만, 이 프로젝트에서는 넣는 것이 좋은 항목이다.

### 4-1. 컬럼 분류 범례

이 프로젝트의 테이블에는 성격이 다른 컬럼이 섞여 있다. 범례로 구분하면 읽기 쉽다.

| 구분 | 표기 | 설명 |
|---|---|---|
| 원본 컬럼 | (기본) | 원본 파일에 있던 컬럼 |
| 파생 컬럼 | `+` | 정제 과정에서 계산해 만든 컬럼 |
| 원본 보존 | `_raw` | 정제 전 값을 보관하는 컬럼 |
| 처리 사유 | `_flag` | NULL 처리·판단 보류 사유를 기록 |
| 사용 금지 | 회색 | 값은 정상이나 분석에 쓸 수 없음 |

**`_raw`와 `_flag` 컬럼이 전체의 상당수를 차지한다.** 이것이 이 프로젝트의 설계 특징이므로 범례로 설명해야 한다. 설명이 없으면 "컬럼이 왜 이렇게 많은가"라는 의문만 남는다.

### 4-2. 분석 가능 모수 표

컬럼마다 NULL 건수가 달라서, 분석할 때 모수가 달라진다. 정의서에 한 장으로 정리해두면 분석 단계에서 계속 참조하게 된다.

| 테이블 | 컬럼 | 사용 가능 | 사용 가능률 |
|---|---|---|---|
| orders | order_amount | 248,475 | 82.8% |
| orders | order_date | 210,000 | 70.0% |
| orders | quantity | 255,133 | 85.0% |
| support_tickets | ticket_created | 27,313 | 91.0% |
| clickstream | event_time | 439,910 | 88.0% |
| clickstream | product_id | 368,942 | 73.8% |
| clickstream | customer_id | 349,447 | 69.9% |
| product_catalog | price | 429 | 85.8% |

### 4-3. 테이블별 수집 기간

**ERD나 정의서 첫 장에 반드시 넣어야 하는 정보다.** 이것을 놓치면 조인 분석에서 전환율 100%가 나온다.

| 테이블 | 수집 기간 | 일수 |
|---|---|---|
| orders | 2023-12-03 ~ 2025-12-01 | 730일 |
| support_tickets | 2023-12-03 ~ 2025-12-02 | 731일 |
| **clickstream** | **2025-09-02 ~ 2025-12-02** | **92일** |

### 4-4. 사용 시 주의사항 (정의서 첫 장)

1. **crm_customers는 분석 전용 사본이다.** 고객 응대·본인 확인·발송에는 `_raw` 컬럼 또는 원본 파일을 사용한다.
2. **clickstream의 `session_id` / `device_id` / `ingest_run_id`는 분석에 사용하지 않는다.** 값은 정상이지만 의미가 없다.
3. **`state` / `country`는 서로 모순된다.** 지역 분석 축으로 사용하지 않는다.
4. **clickstream은 다른 테이블과 수집 기간이 다르다.** 조인 분석 시 기간을 맞춘다.
5. **support_tickets의 날짜 12,626건은 계산 복원값이다.** 원본만 쓰려면 `date_flag IS NULL` 조건을 건다.

---

## 5. 제작 시 참고

### 5-1. 예시 파일과 달라지는 점

| 항목 | 예시 파일 | 이 프로젝트 |
|---|---|---|
| RDBMS | MySQL | **PostgreSQL 16** |
| 자료형 | 대부분 varchar(50) | uuid / numeric / timestamp / boolean 등 실제 타입 |
| Trigger info | 섹션 있음 | **제외** (트리거 없음) |
| ERD 위치 | 마지막 시트 | **첫 시트** |
| 컬럼 성격 | 단일 | 원본 / 파생 / `_raw` / `_flag` 4종 → **범례 필요** |

### 5-2. 전체 규모 요약 (표지용)

| 항목 | 값 |
|---|---|
| 테이블 | 6개 |
| 총 행 수 | 930,554 |
| 컬럼 | 78개 |
| 기본키 | 6 |
| 외래키 | 6 |
| CHECK 제약 | 55 |
| 인덱스 | 19 (PK 포함) |

### 5-3. Claude Design에 요청할 때 포함할 사항

- 형식은 첨부한 `데이터_테이블정의서.xlsx`와 동일하게
- 시트 순서 : ERD → product_catalog → crm_customers → crm_customer_devices → orders → support_tickets → clickstream
- ERD는 관계 6개 + **NULL 허용 FK 2개 점선 표기** + **device_id 관계 없음 주석**
- 컬럼 분류 범례 포함
- Trigger info 섹션 제외
