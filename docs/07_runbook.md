	# 대응 절차

	## 용량 경고 시
- 원인: 순환 재생 2회차 이후 raw 누적
- 조치: python src/run_sql.py main sql/maintenance/90_retention.sql
- 항구 조치: daily.yml 마지막 단계에 위 명령 추가
- 확인: Neon 대시보드 → Monitoring → Database size

# 대응 절차 (런북)

알람이 왔을 때 무엇을 확인하고 어떻게 조치하는지 적은 문서다.

**이 내용은 `config/alerts.yml` 의 `rule_info` 에도 들어 있어
Slack 알람 메시지에 함께 표시된다.** 담당자가 문서를 찾아올 필요가 없도록
한 것이며, 이 문서는 더 자세한 조사 절차를 담는다.

---

## 먼저 확인할 것

어떤 알람이든 대시보드의 **배치 탭**을 먼저 본다.
https://project3-dq-dashboard.streamlit.app/


- 실행 이력 격자에서 해당 날짜의 단계가 모두 SUCCESS 인가
- 소요시간이 평소(40초)와 크게 다른가
- 같은 날 다른 알람이 함께 왔는가

여러 알람이 동시에 왔다면 **P1 부터 처리한다.** 배치가 중단된
상태에서 품질 경고를 조사해봐야 의미가 없다.

---

## P1 — 배치 장애

### F01 배치 미실행

**증상** 해당 날짜의 `mart.batch_log` 에 기록이 없음

**확인**

GitHub → Actions → daily batch → 해당 날짜 실행 이력


- 실행 자체가 없으면: 예약이 비활성화됐는지 확인
  (레포에 60일간 활동이 없으면 GitHub 이 자동 중단한다)
- 실행은 됐는데 실패했으면: 로그에서 어느 단계인지 확인

**조치**
```powershell
python -B src/run_batch.py main --date YYYY-MM-DD
```

수동 재실행하거나, Actions 의 **Run workflow** 에서 날짜를 지정해 실행한다.

### F02 단계 실패

**증상** 어느 단계가 FAILED 로 기록됨

**확인** `mart.batch_log` 의 `message` 컬럼에 실패 사유 앞부분이 있다.

```sql
SELECT step, status, message, duration_sec
FROM mart.batch_log
WHERE batch_date = 'YYYY-MM-DD' AND status = 'FAILED';
```

전체 로그는 Actions 의 Artifact 에서 받는다 (30일 보관).

**자주 겪은 원인**

| 단계 | 증상 | 원인 |
|---|---|---|
| replay | `ValueError: 가동 시작일 이전` | ANCHOR 보다 과거 날짜 지정 |
| load | `ForeignKeyViolation` | 검증이 놓친 고아행. validate 룰 점검 필요 |
| load | `UniqueViolation` | 같은 PK 재유입. 재생기 구간 중복 의심 |
| 전체 | `password authentication failed` | DB 비밀번호 변경됨. Secrets 갱신 필요 |

**조치** 원인 제거 후 해당 날짜 재실행. 배치는 멱등하므로
여러 번 돌려도 안전하다.

### F03 RUNNING 잔류

**증상** 단계가 RUNNING 상태로 남아 있음

**원인** 프로세스가 강제 종료되었거나 타임아웃.
Actions 는 15분 제한이 걸려 있다.

**확인** 같은 배치가 중복 실행 중인지 먼저 본다.
두 프로세스가 같은 날짜를 동시에 처리하면 데이터가 꼬인다.

**조치** 실행 중인 것이 없으면 재실행한다.

---

## P2 — 품질 이상

### D02 허용되지 않은 범주값

**증상** 사전 정의 목록에 없는 값이 유입

**확인** 실제 값이 무엇인지 본다.

```sql
SELECT rule_id, reason, payload->>'payment_method' AS value, count(*)
FROM quarantine.rejected_rows
WHERE batch_date = 'YYYY-MM-DD' AND rule_id = 'D02'
GROUP BY 1, 2, 3;
```

**판단**

| 상황 | 조치 |
|---|---|
| 오탈자 (`Card`, `CARD`) | 정제 단계에 매핑 추가 |
| 정식 신규 값 (`kakaopay`) | CHECK 제약과 `baseline.yml` 갱신 후 재적재 |
| 상류 시스템 오류 | 상류에 문의. 격리 상태 유지 |

**정식 신규 값으로 판단한 경우**

```sql
ALTER TABLE raw.orders DROP CONSTRAINT ck_orders_payment;
ALTER TABLE raw.orders ADD CONSTRAINT ck_orders_payment
    CHECK (payment_method IN ('card','cash','upi','wallet','kakaopay'));
```

`config/baseline.yml` 의 `categories` 도 함께 수정한 뒤 재실행한다.

### D08 격리율 초과

**증상** 격리 행이 전체의 3% 이상이면서 10건 이상

**확인** 어느 룰에 몰렸는지 본다.

```sql
SELECT rule_id, count(*) AS n
FROM quarantine.rejected_rows
WHERE batch_date = 'YYYY-MM-DD'
GROUP BY 1 ORDER BY n DESC;
```

가장 많이 걸린 룰부터 조사한다. 대개 X01(고객 참조 실패)이며,
이 경우 **마스터 적재 시각**을 확인한다.

### C03 PK 중복

**증상** 같은 식별자를 가진 행이 둘 이상

**원인** 상류 중복 전송, 또는 파이프라인 로직 버그

**확인**
```sql
SELECT payload->>'order_id' AS id, count(*)
FROM quarantine.rejected_rows
WHERE batch_date = 'YYYY-MM-DD' AND rule_id = 'C03'
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
```

중복된 id 가 **다른 날짜 배치에도 있는지** 확인한다.
있다면 재생기의 구간 계산 문제일 가능성이 높다.

---

## P3 — 지표 급변

### D01 결측률 급변

**증상** 특정 컬럼의 NULL 비율이 기준선 ±10%p 를 벗어남

**확인** `_raw` 컬럼을 본다. 정제 전 원본이 남아 있다.

```sql
SELECT order_amount, order_amount_raw, amount_flag, count(*)
FROM raw.orders
WHERE batch_date = 'YYYY-MM-DD' AND order_amount IS NULL
GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 20;
```

| `_raw` 상태 | 해석 |
|---|---|
| 값이 있는데 NULL | 정제 단계가 거부함. flag 사유 확인 |
| `_raw` 도 비어 있음 | 상류에서 아예 안 왔음 |

**추세도 함께 본다.** 하루만 튄 것인지, 며칠째 오르는 중인지에 따라
대응이 다르다. 대시보드 품질 탭의 결측률 차트에서 확인한다.

**연쇄 영향** 결측률이 오르면 KPI 모수가 줄어 지표가 왜곡된다.
`mart.daily_kpi` 의 `order_null_rate` 를 함께 확인하고,
필요하면 해당 날짜 지표에 주석을 남긴다.

### D05 적재량 급변

**증상** 행 수가 기준선 ±50% 를 벗어남

**감소한 경우** 상류 장애 또는 수집 누락.
전송 건수를 상류와 대조하고 누락분 재수집을 요청한다.

**증가한 경우** 중복 전송 또는 백필.
C03(PK 중복)이 함께 발동했는지 확인한다.

### C05 적재 0건

**증상** 테이블에 데이터가 하나도 도착하지 않음

**먼저 판단할 것** 데이터가 없는 것이 정상인지 확인한다.
주말·공휴일에 거래가 없는 업종이라면 0건이 자연스럽다.

이 프로젝트는 재생 방식이라 0건이 나오면 **재생 구간을 벗어났거나
원본에 해당 날짜가 없는 것**이다.

---

## 용량 경고

Neon 무료 플랜은 0.5GB 제한이 있다.

**확인** Neon 대시보드 → Monitoring → Database size

**원인** 순환 재생 2회차 이후 `raw` 데이터 누적

**조치**
```powershell
python -B src/run_sql.py main sql/maintenance/90_retention.sql
```

90일이 지난 이벤트 데이터를 삭제한다.
마스터(`crm_customers`, `product_catalog`)는 삭제 대상이 아니다.
이벤트가 참조하고 있고, 초기 적재분은 재적재 경로가 없다.

**항구 조치** `daily.yml` 마지막 단계에 위 명령을 추가한다.

---

## 알람이 오지 않는 것도 이상이다

**"알람이 없다"가 "문제가 없다"를 의미하려면 감시 장치가
살아 있었다는 증거가 필요하다.**

주 1회 다음을 확인한다.

```sql
SELECT batch_date, count(*) AS steps,
       count(*) FILTER (WHERE status = 'SUCCESS') AS ok
FROM mart.batch_log
WHERE batch_date >= CURRENT_DATE - 7
GROUP BY 1 ORDER BY 1;
```

날짜가 빠져 있으면 배치가 돌지 않은 것이고,
`steps` 가 5 미만이면 중간에 멈춘 것이다.

F01 룰이 이를 자동 감지하지만, **알람 발송 자체가 실패할 수도 있다.**
Slack Webhook 이 만료되거나 네트워크가 막히는 경우다.
이것만은 사람이 주기적으로 확인해야 한다.