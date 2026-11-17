#!/usr/bin/env bash
# 本机 conda PostgreSQL 启停（环境：paperAgent）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGDATA="${PGDATA:-$ROOT/data/pgdata}"
LOG="$ROOT/data/pglogs/postgres.log"
# 默认 5433，避免与本机其他 Postgres（如 hkpl 的 5432）冲突
PORT="${PGPORT:-5433}"

source /opt/anaconda3/etc/profile.d/conda.sh
conda activate paperAgent

mkdir -p "$PGDATA" "$(dirname "$LOG")"

case "${1:-status}" in
  init)
    if [[ -f "$PGDATA/PG_VERSION" ]]; then
      echo "已初始化: $PGDATA"
      exit 0
    fi
    initdb -D "$PGDATA" --auth-local=trust --auth-host=trust --username=paper_agent --encoding=UTF8 --locale=C
    ;;
  start)
    if pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
      echo "已在运行"
    else
      pg_ctl -D "$PGDATA" -l "$LOG" -o "-p $PORT" start
    fi
    createdb -h localhost -p "$PORT" -U paper_agent paper_agent 2>/dev/null || true
    pg_isready -h localhost -p "$PORT" -U paper_agent
    ;;
  stop)
    pg_ctl -D "$PGDATA" stop -m fast || true
    ;;
  restart)
    pg_ctl -D "$PGDATA" stop -m fast || true
    sleep 1
    pg_ctl -D "$PGDATA" -l "$LOG" -o "-p $PORT" start
    pg_isready -h localhost -p "$PORT" -U paper_agent
    ;;
  status)
    pg_ctl -D "$PGDATA" status || true
    pg_isready -h localhost -p "$PORT" -U paper_agent || true
    ;;
  *)
    echo "用法: $0 {init|start|stop|restart|status}"
    exit 1
    ;;
esac
