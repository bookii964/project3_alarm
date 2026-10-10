r"""
품질 모니터링 대시보드.

읽기 전용 계정(dashboard_reader)으로 mart 와 quarantine 만 조회한다.
raw 는 권한이 없으며, 집계 테이블만 읽으므로 조회가 가볍다.

로컬 실행:
    streamlit run app/dashboard.py
"""
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(page_title="데이터 품질 모니터링", layout="wide")


# ---------------------------------------------------------------
# 연결
# ---------------------------------------------------------------
@st.cache_resource
def get_engine():
    """Streamlit Cloud 는 secrets, 로컬은 .env 에서 접속 정보를 읽는다.

    st.secrets 는 secrets.toml 이 없으면 접근 시점에 예외를 던지므로
    try 로 감싸야 한다 (hasattr 로는 막히지 않는다).
    """
    url = None
    try:
        url = st.secrets["DASHBOARD_DATABASE_URL"]
    except Exception:
        pass

    if not url:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        url = os.environ.get("DASHBOARD_DATABASE_URL")

    if not url:
        st.error("DASHBOARD_DATABASE_URL 이 설정되지 않았습니다. "
                 ".env 또는 Streamlit secrets 를 확인하세요.")
        st.stop()

    try:
        return create_engine(url, pool_pre_ping=True)
    except Exception:
        # 퍼블릭 앱이므로 에러 상세를 노출하지 않는다.
        # SQLAlchemy 는 연결 실패 시 접속 문자열을 메시지에 담는다
        st.error("데이터베이스 연결에 실패했습니다.")
        st.stop()

@st.cache_data(ttl=300)
def q(sql: str) -> pd.DataFrame:
    """쿼리 결과를 5분간 캐시한다. Neon 컴퓨트 사용량을 줄이기 위함."""
    try:
        return pd.read_sql(sql, get_engine())
    except Exception as e:
        # 퍼블릭 앱이므로 에러 유형만 표시하고 상세는 감춘다
        st.error(f"조회 실패: {type(e).__name__}")
        st.stop()


@st.cache_data
def load_scenarios() -> pd.DataFrame:
    """주입 시나리오를 읽어 차트 마커로 쓴다."""
    path = ROOT / "config" / "scenarios.yml"
    if not path.exists():
        return pd.DataFrame(columns=["date", "table", "type", "note"])
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return pd.DataFrame(cfg.get("scenarios", []))


def mark_scenarios(fig, scenarios: pd.DataFrame):
    """차트에 주입일 수직선을 그린다."""
    for r in scenarios.itertuples():
        fig.add_vline(
            x=pd.Timestamp(r.date), line_dash="dot", line_color="#888",
            annotation_text="주입", annotation_position="top",
            annotation_font_size=10)
    return fig


# ---------------------------------------------------------------
# 상단 요약
# ---------------------------------------------------------------
st.title("데이터 품질 모니터링")

scenarios = load_scenarios()

latest = q("""
    SELECT batch_date,
           count(*) FILTER (WHERE status = 'FAIL') AS fail,
           count(*) FILTER (WHERE status = 'WARN') AS warn,
           count(*) AS total
    FROM mart.dq_daily
    GROUP BY batch_date ORDER BY batch_date DESC LIMIT 1
""")

batch_ok = q("""
    SELECT count(*) FILTER (WHERE status = 'SUCCESS') AS ok,
           count(*) AS total
    FROM mart.batch_log
    WHERE batch_date = (SELECT max(batch_date) FROM mart.batch_log)
""")

if latest.empty:
    st.warning("데이터가 없습니다.")
    st.stop()

r = latest.iloc[0]
b = batch_ok.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("최신 배치", str(r["batch_date"]))
c2.metric("검사 통과", f"{r['total'] - r['fail'] - r['warn']} / {r['total']}")
c3.metric("FAIL", int(r["fail"]))
c4.metric("배치 단계", f"{int(b['ok'])} / {int(b['total'])}")

tab_dq, tab_kpi, tab_batch = st.tabs(["품질", "KPI", "배치"])


# ---------------------------------------------------------------
# 품질
# ---------------------------------------------------------------
with tab_dq:
    st.subheader("검사 결과 추이")
    st.caption("PASS 는 제외하고 FAIL·WARN 만 표시한다. "
               "평상시 FAIL 2~4건이 기준선 — 참조 무결성 룰(X01/X03/X04)이 "
               "매일 발동하는 데이터셋 특성 때문이다.")

    # status 를 그대로 행으로 받아 컬럼명 대소문자 문제를 피한다.
    # (Postgres 는 따옴표 없는 별칭을 소문자로 바꾼다)
    trend = q("""
        SELECT batch_date, status, count(*) AS n
        FROM mart.dq_daily
        WHERE status <> 'PASS'
        GROUP BY batch_date, status
        ORDER BY batch_date
    """)
    fig = px.bar(trend, x="batch_date", y="n", color="status",
                 color_discrete_map={"FAIL": "#d32f2f", "WARN": "#f57c00",
                                     "ERROR": "#424242"},
                 category_orders={"status": ["FAIL", "WARN"]},
                 labels={"n": "건수", "batch_date": "", "status": ""})
    fig.update_layout(height=280, barmode="stack",
                      legend=dict(orientation="h", y=1.15),
                      yaxis=dict(dtick=1))
    st.plotly_chart(mark_scenarios(fig, scenarios), use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.subheader("룰별 격리 건수")
        rej = q("""
            SELECT rule_id, table_name, count(*) AS n
            FROM quarantine.rejected_rows
            GROUP BY 1, 2 ORDER BY n DESC
        """)
        fig = px.bar(rej, x="n", y="rule_id", color="table_name",
                     orientation="h", log_x=True,
                     labels={"n": "건수 (로그 스케일)", "rule_id": "",
                             "table_name": ""})
        fig.update_layout(height=300, legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("X04 가 가장 많지만 clickstream 행 수가 크기 때문이다. "
                   "비율로는 X01(orders) 2.0%, X04 1.3% 로 역전된다. "
                   "D02 3건은 주입 시나리오로 만든 것이고, "
                   "나머지는 원본 데이터셋이 가진 참조 무결성 문제다.")

    with right:
        st.subheader("결측률 추이")
        nulls = q("""
            SELECT batch_date, table_name || '.' || column_name AS col,
                   value, baseline
            FROM mart.dq_daily
            WHERE rule_id = 'D01' AND column_name <> ''
            ORDER BY batch_date
        """)
        cols = sorted(nulls["col"].unique())
        default = [c for c in cols if c == "orders.order_amount"] or cols[:2]
        picked = st.multiselect("컬럼 선택", cols, default=default,
                                label_visibility="collapsed")
        sub = nulls[nulls["col"].isin(picked)] if picked else nulls

        fig = px.line(sub, x="batch_date", y="value", color="col",
                      markers=True,
                      labels={"value": "결측률", "batch_date": "", "col": ""})
        # 기준선을 점선으로 겹쳐 그린다
        for c in picked:
            vals = nulls.loc[nulls["col"] == c, "baseline"]
            if len(vals) and pd.notna(vals.iloc[0]):
                base = float(vals.iloc[0])
                fig.add_hline(y=base, line_dash="dash", line_color="#aaa",
                              annotation_text=f"기준 {base:.1%}",
                              annotation_font_size=10)
        fig.update_layout(height=300, yaxis_tickformat=".0%",
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(mark_scenarios(fig, scenarios), use_container_width=True)

    st.subheader("최근 격리 내역")
    summary = q("""
        SELECT batch_date, rule_id, table_name, count(*) AS n,
               max(reason) AS reason
        FROM quarantine.rejected_rows
        WHERE batch_date >= (SELECT max(batch_date) - 6
                             FROM quarantine.rejected_rows)
        GROUP BY 1, 2, 3
        ORDER BY batch_date DESC, n DESC
    """)
    summary.columns = ["배치일", "룰", "테이블", "건수", "사유"]
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption("최근 7일, 룰·테이블별 집계. "
               "배치일은 논리적 재생 날짜이고 실제 실행 시각과는 분리돼 있다.")

    with st.expander("개별 격리 행 보기 (orders)"):
        rows = q("""
            SELECT batch_date, rule_id,
                   payload->>'order_id' AS order_id,
                   payload->>'customer_id' AS customer_id,
                   payload->>'payment_method' AS payment_method,
                   payload->>'order_amount' AS order_amount
            FROM quarantine.rejected_rows
            WHERE table_name = 'orders'
            ORDER BY created_at DESC LIMIT 30
        """)
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("jsonb 로 원본 행 전체를 보관하므로 어떤 컬럼이든 "
                   "꺼내볼 수 있다. payment_method 가 'bitcoin' 인 행이 "
                   "주입 시나리오 01의 결과다.")


# ---------------------------------------------------------------
# KPI
# ---------------------------------------------------------------
with tab_kpi:
    kpi = q("SELECT * FROM mart.daily_kpi ORDER BY batch_date")

    st.subheader("거래 지표")
    st.caption("GMV 는 금액이 기록된 주문만 집계한다(status='success' 한정). "
               "모수 비율을 함께 표시해 지표의 신뢰 범위를 드러낸다.")

    fig = go.Figure()
    fig.add_bar(x=kpi["batch_date"], y=kpi["gmv"], name="GMV",
                marker_color="#1976d2")
    fig.add_scatter(x=kpi["batch_date"], y=kpi["order_count"], name="주문 건수",
                    yaxis="y2", mode="lines+markers", line_color="#f57c00")
    fig.update_layout(
        height=320, yaxis=dict(title="GMV"),
        yaxis2=dict(title="주문", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12), xaxis_title="")
    st.plotly_chart(mark_scenarios(fig, scenarios), use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.subheader("GMV 집계 모수")
        cov = kpi.assign(coverage=1 - kpi["order_null_rate"])
        fig = px.area(cov, x="batch_date", y="coverage",
                      labels={"coverage": "집계 대상 비율", "batch_date": ""})
        # 0~100% 로 두면 변화가 납작하게 눌린다. 실제 범위에 맞춘다
        fig.update_layout(height=260, yaxis_tickformat=".0%",
                          yaxis_range=[0.5, 1.0])
        fig.update_traces(line_color="#388e3c",
                          fillcolor="rgba(56,142,60,.2)")
        st.plotly_chart(mark_scenarios(fig, scenarios), use_container_width=True)
        st.caption("10/06 결측률 주입 시 모수가 82% → 65% 로 하락했다. "
                   "같은 날 AOV 가 64,671 로 평소보다 30% 높게 나왔는데, "
                   "표본이 줄어 평균이 이동한 결과다.")

    with right:
        st.subheader("CS 지표")
        fig = go.Figure()
        fig.add_bar(x=kpi["batch_date"], y=kpi["ticket_count"], name="티켓 수",
                    marker_color="#7b1fa2")
        fig.add_scatter(x=kpi["batch_date"], y=kpi["ticket_negative_rate"],
                        name="부정 비율", yaxis="y2", mode="lines+markers",
                        line_color="#d32f2f")
        fig.update_layout(
            height=260, yaxis=dict(title="건수"),
            yaxis2=dict(title="부정 비율", overlaying="y", side="right",
                        tickformat=".0%"),
            legend=dict(orientation="h", y=1.18), xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("일별 지표")
    show = kpi[["batch_date", "order_count", "gmv", "aov",
                "order_null_rate", "ticket_count", "event_count"]].copy()
    show["order_null_rate"] = (show["order_null_rate"] * 100).round(1)
    show["gmv"] = show["gmv"].round(0)
    show["aov"] = show["aov"].round(0)
    show.columns = ["날짜", "주문", "GMV", "AOV", "결측률(%)", "티켓", "이벤트"]
    st.dataframe(
        show, use_container_width=True, hide_index=True,
        column_config={
            "주문": st.column_config.NumberColumn(format="%,d"),
            "GMV": st.column_config.NumberColumn(format="%,d"),
            "AOV": st.column_config.NumberColumn(format="%,d"),
            "결측률(%)": st.column_config.NumberColumn(format="%.1f"),
            "티켓": st.column_config.NumberColumn(format="%,d"),
            "이벤트": st.column_config.NumberColumn(format="%,d"),
        })


# ---------------------------------------------------------------
# 배치
# ---------------------------------------------------------------
with tab_batch:
    st.subheader("실행 이력")

    log = q("""
        SELECT batch_date, step, status, duration_sec, row_count
        FROM mart.batch_log ORDER BY batch_date, started_at
    """)

    if log.empty:
        st.info("배치 기록이 없습니다.")
    else:
        # batch_log 의 PK 가 (batch_date, step) 이라 중복이 없다
        grid = log.pivot(index="batch_date", columns="step", values="status")

        # 배치를 돌리지 않은 날을 공백으로 드러낸다.
        # 행 자체가 없으면 누락이 보이지 않는다
        full = pd.date_range(grid.index.min(), grid.index.max(), freq="D").date
        grid = grid.reindex(full)

        order = [c for c in ["replay", "validate", "load", "aggregate", "alert"]
                 if c in grid.columns]
        st.dataframe(grid[order].fillna("—"), use_container_width=True)
        st.caption("빈 칸(—)은 해당 단계를 실행하지 않은 날이다. "
                   "aggregate·alert 는 나중에 추가되어 초기 배치에는 없고, "
                   "행 전체가 비어 있는 날은 배치를 돌리지 않은 날이다. "
                   "이 공백을 alert.py 의 F01 룰이 감지해 P1 알람을 발송했다.")

        st.subheader("단계별 소요시간")
        fig = px.line(log, x="batch_date", y="duration_sec", color="step",
                      markers=True,
                      labels={"duration_sec": "초", "batch_date": "",
                              "step": ""})
        fig.update_layout(height=280, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("알람 발송 내역")
    alerts = q("""
        SELECT batch_date, severity, rule_id, table_name, message,
               sent_at AT TIME ZONE 'Asia/Seoul' AS sent_kst
        FROM mart.alert_log ORDER BY sent_at DESC LIMIT 50
    """)
    if alerts.empty:
        st.info("발송된 알람이 없습니다.")
    else:
        alerts.columns = ["배치일", "등급", "룰", "테이블", "메시지",
                          "발송시각(KST)"]
        st.dataframe(alerts, use_container_width=True, hide_index=True)
        st.caption("P1 은 배치 장애, P2 는 품질 이상, P3 은 지표 급변이다. "
                   "참조 무결성 룰(X01/X03/X04)은 매일 발동하므로 "
                   "기준선의 3~5배를 넘을 때만 알린다.")


st.caption("데이터는 5분간 캐시됩니다. "
           "읽기 전용 계정으로 mart·quarantine 만 조회합니다.")