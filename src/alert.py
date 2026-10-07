r"""
알람 발송기: 배치 결과를 판정해 Slack 으로 알린다.

판정 흐름
  1. mart.batch_log  → P1 (FAILED / RUNNING 잔류 / 기록 없음)
  2. mart.dq_daily   → P2·P3 (rule_severity 에 배정된 룰의 FAIL/WARN)
                     → 참조 무결성 룰은 기준선 x 배수 초과 시만
  3. 억제            → 24시간 내 같은 (룰, 테이블) 조합은 건너뜀
  4. 발송 + mart.alert_log 기록

사용:
    python -B src/alert.py dev
    python -B src/alert.py dev --date 2026-10-05
    python -B src/alert.py dev --dry-run
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CFG = yaml.safe_load((ROOT / "config" / "alerts.yml").read_text(encoding="utf-8"))
TARGETS = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}

# alert 단계는 자기 자신이 실행 중이므로 검사 대상에서 제외한다
STEPS = ["replay", "validate", "load", "aggregate"]

# 건수형 지표. 소수가 아닌 정수로 표시한다
COUNT_METRICS = {"orphan_count", "new_values", "row_count", "dup_count"}


def check_batch(engine, bd: date) -> list[dict]:
    """배치 실행 상태를 확인한다 (P1)."""
    df = pd.read_sql(
        "SELECT step, status, message, duration_sec FROM mart.batch_log "
        "WHERE batch_date = %(d)s", engine, params={"d": bd})

    alerts = []

    if df.empty:
        alerts.append(dict(
            severity="P1", rule_id="F01", table_name=None,
            message=f"{bd} 배치 기록이 없습니다. 실행되지 않았을 가능성."))
        return alerts

    for r in df.itertuples():
        if r.status == "FAILED":
            alerts.append(dict(
                severity="P1", rule_id="F02", table_name=None,
                message=f"{r.step} 단계 실패: {(r.message or '')[:200]}"))
        elif r.status == "RUNNING" and r.step != "alert":
            alerts.append(dict(
                severity="P1", rule_id="F03", table_name=None,
                message=f"{r.step} 단계가 RUNNING 상태로 남아 있습니다. "
                        f"강제 종료되었을 가능성."))

    done = set(df[df["status"] == "SUCCESS"]["step"])
    missing = [s for s in STEPS if s not in done]
    if missing and not any(a["rule_id"] in ("F02", "F03") for a in alerts):
        alerts.append(dict(
            severity="P1", rule_id="F04", table_name=None,
            message=f"미완료 단계: {', '.join(missing)}"))

    return alerts


def fmt(value, metric: str) -> str:
    """지표 값을 보기 좋게 포맷한다."""
    if value is None:
        return "-"
    if metric in COUNT_METRICS:
        return f"{float(value):,.0f}"
    return f"{value}"


def check_quality(engine, bd: date) -> list[dict]:
    """품질 검사 결과를 판정한다 (P2·P3)."""
    df = pd.read_sql(
        "SELECT rule_id, table_name, column_name, metric, value, baseline, status "
        "FROM mart.dq_daily WHERE batch_date = %(d)s AND status <> 'PASS'",
        engine, params={"d": bd})

    alerts = []
    sev_map = CFG["rule_severity"]
    mult = CFG["baseline_multiplier"]

    for r in df.itertuples():
        col = f".{r.column_name}" if r.column_name else ""
        target = f"{r.table_name}{col}"

        if r.rule_id in mult:
            # 참조 무결성: 기준선 x 배수를 넘을 때만 알린다.
            # 매일 발동하는 룰이라 단순 FAIL 로 알리면 소음이 된다
            m = mult[r.rule_id]
            threshold = m["baseline"] * m["factor"]
            if float(r.value) <= threshold:
                continue
            alerts.append(dict(
                severity=m["severity"], rule_id=r.rule_id,
                table_name=r.table_name,
                message=f"{target} — {r.metric}={fmt(r.value, r.metric)} "
                        f"(평상시 {m['baseline']}건, 임계 {threshold}건)"))

        elif r.rule_id in sev_map:
            base = ""
            if r.baseline is not None:
                base = f" (기준 {fmt(r.baseline, r.metric)})"
            alerts.append(dict(
                severity=sev_map[r.rule_id], rule_id=r.rule_id,
                table_name=r.table_name,
                message=f"{target} — {r.metric}={fmt(r.value, r.metric)}{base}"))

    return alerts


def filter_suppressed(engine, alerts: list[dict]) -> tuple[list, list]:
    """최근 발송 이력이 있는 알람을 걸러낸다."""
    hours = CFG["suppression"]["window_hours"]
    recent = pd.read_sql(
        "SELECT rule_id, table_name FROM mart.alert_log "
        "WHERE sent_at > now() - make_interval(hours => %(h)s)",
        engine, params={"h": hours})

    seen = {(r.rule_id, r.table_name) for r in recent.itertuples()}
    keep, skip = [], []
    for a in alerts:
        key = (a["rule_id"], a["table_name"])
        # P1 은 억제하지 않는다. 장애는 매번 알려야 한다
        if a["severity"] != "P1" and key in seen:
            skip.append(a)
        else:
            keep.append(a)
    return keep, skip


def build_message(bd: date, alerts: list[dict]) -> dict:
    """Slack 메시지를 조립한다.

    담당자가 코드를 보지 않아도 대응할 수 있도록
    룰 ID 와 함께 의미·추정 원인·조치 방법을 함께 표시한다.
    """
    sev_cfg = CFG["severities"]
    info = CFG.get("rule_info", {})
    worst = min(a["severity"] for a in alerts)   # P1 < P2 < P3

    blocks = [{
        "type": "header",
        "text": {"type": "plain_text",
                 "text": f"{sev_cfg[worst]['emoji']} {bd} 배치 알람 "
                         f"({len(alerts)}건)"}
    }]

    for sev in ["P1", "P2", "P3"]:
        group = [a for a in alerts if a["severity"] == sev]
        if not group:
            continue

        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn",
                          "text": f"*{sev} — {sev_cfg[sev]['label']}*"}]
        })

        for a in group:
            meta = info.get(a["rule_id"], {})
            title = meta.get("title", a["rule_id"])

            lines = [f"*{title}*  `{a['rule_id']}`", a["message"]]
            if meta.get("what"):
                lines.append(f"> {meta['what']}")
            if meta.get("why"):
                lines.append(f"> *추정 원인*  {meta['why']}")
            if meta.get("action"):
                lines.append(f"> *조치*  {meta['action'].strip()}")

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)}
            })

        blocks.append({"type": "divider"})

    return {
        "text": f"{bd} 배치 알람 {len(alerts)}건",
        "attachments": [{"color": sev_cfg[worst]["color"], "blocks": blocks}]
    }


def send_slack(payload: dict) -> bool:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("  SLACK_WEBHOOK_URL 이 없어 발송을 건너뜁니다.")
        return False
    res = requests.post(url, json=payload, timeout=10)
    if res.status_code != 200:
        print(f"  Slack 발송 실패 {res.status_code}: {res.text[:100]}")
        return False
    return True


def log_alerts(engine, bd: date, alerts: list[dict]) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO mart.alert_log "
            "(batch_date, severity, rule_id, table_name, message, channel) "
            "VALUES (:d, :sev, :rid, :tbl, :msg, 'slack')"),
            [dict(d=bd, sev=a["severity"], rid=a["rule_id"],
                  tbl=a["table_name"], msg=a["message"]) for a in alerts])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["dev", "main"])
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--dry-run", action="store_true",
                        help="발송하지 않고 판정 결과만 출력")
    args = parser.parse_args()

    engine = create_engine(os.environ[TARGETS[args.target]])
    bd = args.date
    print(f"대상: {args.target}   배치 날짜: {bd}\n")

    alerts = check_batch(engine, bd) + check_quality(engine, bd)

    if not alerts:
        print("알람 없음. 정상입니다.")
        return

    keep, skip = filter_suppressed(engine, alerts)

    print(f"[판정] 전체 {len(alerts)}건  발송 {len(keep)}건  억제 {len(skip)}건\n")
    for a in alerts:
        mark = "억제" if a in skip else "발송"
        print(f"  [{mark}] {a['severity']} {a['rule_id']:4s} {a['message']}")

    if not keep:
        print("\n모두 억제되어 발송하지 않습니다.")
        return

    if args.dry_run:
        print("\n(dry-run: 발송하지 않음)")
        return

    if send_slack(build_message(bd, keep)):
        log_alerts(engine, bd, keep)
        print(f"\nSlack 발송 완료 ({len(keep)}건)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n실패: {type(e).__name__}")
        print(str(e)[:600])
        raise SystemExit(1)