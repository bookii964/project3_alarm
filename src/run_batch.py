r"""
배치 실행기: 파이프라인 단계를 순서대로 실행하고 이력을 기록한다.

하는 일
  1. replay → validate → load → aggregate 를 차례로 호출
  2. 각 단계의 시작/종료/건수/소요시간을 mart.batch_log 에 기록
  3. 실패하면 그 지점에서 멈추고 종료 코드 1 을 반환

스크립트들을 수정하지 않고 subprocess 로 호출한다.
replay.py 는 DB를 알 필요가 없는 순수 파일 처리이므로
로그 기록을 위해 DB 연결을 붙이지 않는다.

사용:
    python -B src/run_batch.py dev
    python -B src/run_batch.py dev --date 2026-10-01
    python -B src/run_batch.py main --init                 # 초기 적재부터
    python -B src/run_batch.py dev --log docs/evidence/batch.txt
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# 출력을 파일로 리다이렉트하면 윈도우 기본 인코딩(cp949)이 적용되어
# em dash(—)와 한글이 깨진다. 자기 출력 스트림도 UTF-8 로 고정한다.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BATCH = ROOT / "data" / "batch"
TARGETS = {"dev": "DEV_DATABASE_URL", "main": "DATABASE_URL"}

RAW_TABLES = ["crm_customers", "crm_customer_devices", "orders",
              "support_tickets", "clickstream"]


class Tee:
    """터미널과 파일에 동시에 출력한다."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)

    def flush(self):
        for s in self.streams:
            s.flush()


def log_step(engine, batch_date: date, step: str, status: str,
             row_count: int | None = None, duration: float | None = None,
             message: str | None = None, started_at=None) -> None:
    """batch_log 에 한 단계의 결과를 기록한다 (멱등)."""
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM mart.batch_log WHERE batch_date = :d AND step = :s"),
            {"d": batch_date, "s": step})
        conn.execute(text(
            "INSERT INTO mart.batch_log "
            "(batch_date, step, status, row_count, duration_sec, "
            " message, started_at, finished_at) "
            "VALUES (:d, :s, :st, :n, :sec, :msg, :start, :fin)"),
            {"d": batch_date, "s": step, "st": status, "n": row_count,
             "sec": duration, "msg": message, "start": started_at,
             "fin": datetime.now(timezone.utc)})


def count_batch_files() -> int:
    """replay 가 만든 parquet 의 행 수 합계.

    parquet 은 헤더에 행 수를 기록하므로 데이터를 읽지 않고도 알 수 있다.
    """
    import pyarrow.parquet as pq

    total = 0
    for p in BATCH.glob("*.parquet"):
        total += pq.ParquetFile(p).metadata.num_rows
    return total


def count_checks(engine, batch_date: date) -> int:
    with engine.connect() as conn:
        return conn.execute(text(
            "SELECT count(*) FROM mart.dq_daily WHERE batch_date = :d"),
            {"d": batch_date}).scalar()


def count_loaded(engine, batch_date: date) -> int:
    total = 0
    with engine.connect() as conn:
        for t in RAW_TABLES:
            total += conn.execute(text(
                f"SELECT count(*) FROM raw.{t} WHERE batch_date = :d"),
                {"d": batch_date}).scalar()
    return total


def count_kpi(engine, batch_date: date) -> int:
    with engine.connect() as conn:
        return conn.execute(text(
            "SELECT count(*) FROM mart.daily_kpi WHERE batch_date = :d"),
            {"d": batch_date}).scalar()


def run(cmd: list[str]) -> tuple[bool, str]:
    """하위 스크립트를 실행하고 출력을 그대로 흘려보낸다.

    윈도우에서 subprocess 로 파이썬을 호출하면 출력이 파이프로 가면서
    기본 인코딩(cp949)이 적용되어 한글과 em dash(—)가 깨진다.
    PYTHONIOENCODING 으로 UTF-8 을 강제한다.
    PYTHONDONTWRITEBYTECODE 는 -B 와 같은 효과로 캐시 문제를 차단한다.
    """
    env = {**os.environ,
           "PYTHONIOENCODING": "utf-8",
           "PYTHONDONTWRITEBYTECODE": "1"}

    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    print(proc.stdout, end="")
    if proc.returncode != 0:
        print(proc.stderr, end="")

    tail = (proc.stdout + proc.stderr).strip().splitlines()
    msg = tail[-1][:300] if tail else ""
    return proc.returncode == 0, msg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["dev", "main"])
    parser.add_argument("--date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--init", action="store_true",
                        help="초기 적재를 먼저 수행한다 (최초 1회)")
    parser.add_argument("--log", type=Path, default=None,
                        help="실행 로그를 이 파일에 UTF-8 로 저장한다")
    args = parser.parse_args()

    log_file = None
    if args.log:
        # PowerShell 의 > 리다이렉트는 UTF-8 출력을 중간에서 재인코딩해
        # 파일을 손상시킨다. 파이썬이 직접 파일에 쓰도록 한다.
        args.log.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(args.log, "w", encoding="utf-8")
        sys.stdout = Tee(sys.stdout, log_file)

    try:
        engine = create_engine(os.environ[TARGETS[args.target]])
        bd = args.date
        py = sys.executable

        print("=" * 52)
        print(f"배치 시작  {args.target}  {bd}")
        print("=" * 52 + "\n")

        overall = time.time()

        if args.init:
            print("--- init ---")
            ok, _ = run([py, "-B", str(ROOT / "src" / "load.py"),
                         args.target, "--date", bd.isoformat(), "--init-only"])
            if not ok:
                print("\n초기 적재 실패")
                raise SystemExit(1)

        steps = [
            ("replay", [py, "-B", str(ROOT / "src" / "replay.py"),
                        "--date", bd.isoformat()],
             lambda: count_batch_files()),
            ("validate", [py, "-B", str(ROOT / "src" / "validate.py"),
                          args.target, "--date", bd.isoformat()],
             lambda: count_checks(engine, bd)),
            ("load", [py, "-B", str(ROOT / "src" / "load.py"),
                      args.target, "--date", bd.isoformat()],
             lambda: count_loaded(engine, bd)),
            ("aggregate", [py, "-B", str(ROOT / "src" / "aggregate.py"),
                           args.target, "--date", bd.isoformat()],
             lambda: count_kpi(engine, bd)),
        ]

        for step, cmd, counter in steps:
            print(f"--- {step} ---")
            started = datetime.now(timezone.utc)
            t0 = time.time()
            log_step(engine, bd, step, "RUNNING", started_at=started)

            ok, msg = run(cmd)
            elapsed = time.time() - t0

            if not ok:
                log_step(engine, bd, step, "FAILED", None, elapsed, msg, started)
                print(f"\n{step} 실패 ({elapsed:.1f}초)")
                print(f"배치 중단. 소요 {time.time() - overall:.1f}초")
                raise SystemExit(1)

            n = counter()
            log_step(engine, bd, step, "SUCCESS", n, elapsed, None, started)
            print(f"  → {step} 완료  {n:,d}행  {elapsed:.1f}초\n")

        print("=" * 52)
        print(f"배치 완료  총 {time.time() - overall:.1f}초")
        print("=" * 52)

    finally:
        if log_file:
            sys.stdout = sys.__stdout__
            log_file.close()


if __name__ == "__main__":
    main()