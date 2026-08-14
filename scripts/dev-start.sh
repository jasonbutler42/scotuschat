#!/usr/bin/env bash
# scripts/dev-start.sh
#
# WSL-native start/stop entry point for the SCOTUS Chat dev stack.
# Runs entirely inside WSL: resolves the Windows host IP fresh on every
# run, self-heals (or refuses) a drifted .env DB host, verifies PostgreSQL
# reachability, migrates with Alembic, then launches uvicorn and vite as
# their own process groups with real HTTP health checks and a trap-based
# teardown. No watcher-polling workaround is configured anywhere -- this
# repository lives on native ext4, where inotify works.
#
# Usage:
#   scripts/dev-start.sh          Start the stack (foreground; Ctrl+C to stop)
#   scripts/dev-start.sh --stop   Terminate whatever holds TCP 8000 or 5173
#   scripts/dev-start.sh --help   Show this usage message
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
Usage: scripts/dev-start.sh [--stop|--help]

  (no arguments)   Start the dev stack: resolve the Windows host IP, sync
                   or refuse a drifted .env DB host, verify PostgreSQL
                   reachability, run Alembic migrations, then launch
                   uvicorn and vite as their own WSL-native process
                   groups with real HTTP health checks. Press Ctrl+C to
                   stop both cleanly.

  --stop           Terminate whatever is listening on TCP 8000 or 5173.

  --help           Show this usage message.
EOF
}

ACTION="start"
if [ "$#" -gt 0 ]; then
  case "$1" in
    --stop)
      ACTION="stop"
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  if [ "$#" -gt 1 ]; then
    echo "Unexpected extra arguments: ${*:2}" >&2
    usage >&2
    exit 2
  fi
fi

API_PGID=""
APP_PGID=""

cleanup() {
  local pgid
  for pgid in "$API_PGID" "$APP_PGID"; do
    [ -n "$pgid" ] && kill -TERM -- "-${pgid}" 2>/dev/null || true
  done
  if [ -n "$API_PGID" ] || [ -n "$APP_PGID" ]; then
    sleep 1
  fi
  for pgid in "$API_PGID" "$APP_PGID"; do
    [ -n "$pgid" ] && kill -KILL -- "-${pgid}" 2>/dev/null || true
  done
}

resolve_win_host_ip() {
  WIN_HOST_IP="$(ip route show default | awk '{print $3}' || true)"
  if [ -z "$WIN_HOST_IP" ]; then
    echo "ERROR: could not resolve the Windows host IP via 'ip route show default'." >&2
    exit 1
  fi
  echo "Resolved Windows host IP: ${WIN_HOST_IP}"
}

_extract_env_host() {
  local file="$1" var="$2"
  grep "^${var}=" "$file" 2>/dev/null | head -n1 | sed -E "s#^${var}=[A-Za-z0-9+]+://[^@]*@([^:/]+).*#\\1#" || true
}

sync_env_db_host() {
  local env_file="${REPO_ROOT}/.env"
  if [ ! -f "$env_file" ]; then
    echo "ERROR: ${env_file} not found; cannot verify or sync the database host." >&2
    exit 1
  fi

  local db_host test_host
  db_host="$(_extract_env_host "$env_file" DATABASE_URL)"
  test_host="$(_extract_env_host "$env_file" TEST_DATABASE_URL)"

  if { [ -z "$db_host" ] || [ "$db_host" = "$WIN_HOST_IP" ]; } && \
     { [ -z "$test_host" ] || [ "$test_host" = "$WIN_HOST_IP" ]; }; then
    echo "No .env host change needed (already ${WIN_HOST_IP})."
    return 0
  fi

  if [ -n "${SCOTUS_DEV_NO_ENV_SYNC:-}" ]; then
    echo "WARNING: .env DB host (${db_host:-$test_host}) differs from the resolved Windows host IP (${WIN_HOST_IP}); SCOTUS_DEV_NO_ENV_SYNC is set, skipping the rewrite." >&2
    return 0
  fi

  local host
  for host in "$db_host" "$test_host"; do
    if [ -n "$host" ] && [ "$host" != "$WIN_HOST_IP" ] && ! [[ "$host" =~ ^172\.(1[6-9]|2[0-9]|3[01])\. ]]; then
      echo "ERROR: .env host (${host}) does not look like a WSL2 NAT gateway address. Refusing to rewrite .env automatically -- fix it by hand, or set SCOTUS_DEV_NO_ENV_SYNC=1 to skip this check." >&2
      exit 1
    fi
  done

  cp "$env_file" "${env_file}.bak"
  chmod 600 "${env_file}.bak"

  sed -i -E \
    -e "s#^(DATABASE_URL=[A-Za-z0-9+]+://[^@]*@)[^:/]+#\\1${WIN_HOST_IP}#" \
    -e "s#^(TEST_DATABASE_URL=[A-Za-z0-9+]+://[^@]*@)[^:/]+#\\1${WIN_HOST_IP}#" \
    "$env_file"

  echo ".env DB host updated: ${db_host:-$test_host} -> ${WIN_HOST_IP}"
}

probe_postgres() {
  if ! timeout 5 bash -c "exec 3<>/dev/tcp/${WIN_HOST_IP}/5432" 2>/dev/null; then
    cat >&2 <<EOF
ERROR: could not reach PostgreSQL at ${WIN_HOST_IP}:5432.

Check all three independent access gates -- any one alone produces this
exact symptom. See .planning/phases/46-dev-environment-reliability/46-WINDOWS-POSTGRES-SETUP.md
for this machine's recorded values:
  1. The postgresql-x64-18 Windows service is running.
  2. pg_hba.conf has a host rule covering the WSL subnet.
  3. Windows Firewall has an inbound allow rule for TCP 5432.
EOF
    exit 1
  fi
  echo "PostgreSQL reachable at ${WIN_HOST_IP}:5432."
}

wait_for_http() {
  local url="$1" label="$2" logfile="$3"
  local attempt code
  for attempt in $(seq 1 30); do
    code="$(curl -s -o /dev/null --max-time 2 -w '%{http_code}' "$url" 2>/dev/null || true)"
    if [ -n "$code" ] && [ "$code" != "000" ]; then
      echo "${label} is up (${url}, HTTP ${code})."
      return 0
    fi
    sleep 1
  done
  echo "ERROR: ${label} did not become healthy at ${url} within 30s. Check ${logfile} for details." >&2
  exit 1
}

stop_ports() {
  local port pids pid found_any
  found_any=0
  for port in 8000 5173; do
    pids="$(ss -ltnpH "sport = :${port}" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
    if [ -z "$pids" ]; then
      echo "Port ${port}: nothing listening."
      continue
    fi
    found_any=1
    for pid in $pids; do
      echo "Port ${port}: terminating pid ${pid}."
      kill -TERM -- "-${pid}" 2>/dev/null || kill -TERM "${pid}" 2>/dev/null || true
    done
  done

  if [ "$found_any" -eq 1 ]; then
    sleep 1
    for port in 8000 5173; do
      pids="$(ss -ltnpH "sport = :${port}" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
      for pid in $pids; do
        echo "Port ${port}: pid ${pid} still alive, sending KILL."
        kill -KILL -- "-${pid}" 2>/dev/null || kill -KILL "${pid}" 2>/dev/null || true
      done
    done
  else
    echo "Nothing found listening on 8000 or 5173."
  fi
}

if [ "$ACTION" = "stop" ]; then
  stop_ports
  exit 0
fi

# Registered before the first setsid launch, so a failure during
# health-check polling still tears down whatever already started.
trap cleanup INT TERM EXIT

resolve_win_host_ip
sync_env_db_host
probe_postgres

if [ ! -f "${REPO_ROOT}/.venv/bin/activate" ]; then
  echo "ERROR: ${REPO_ROOT}/.venv/bin/activate not found. Rebuild the WSL-native venv per plan 46-04 (python3.12 -m venv .venv)." >&2
  exit 1
fi
# shellcheck disable=SC1091
source "${REPO_ROOT}/.venv/bin/activate"

if ! alembic upgrade head; then
  echo "ERROR: Alembic migration failed. Check DATABASE_URL in .env and PostgreSQL reachability." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  if [ -f "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]; then
    # shellcheck disable=SC1091
    source "${NVM_DIR:-$HOME/.nvm}/nvm.sh"
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm not found on PATH, and sourcing nvm.sh did not make it available." >&2
    exit 1
  fi
fi

mkdir -p .dev-logs

setsid -w uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload \
  --reload-exclude '.claude/worktrees/*' \
  --reload-exclude '.planning/*' \
  --reload-exclude '.dev-logs/*' \
  </dev/null >.dev-logs/api-out.log 2>.dev-logs/api-err.log &
API_PGID=$!

wait_for_http "http://127.0.0.1:8000/health" "FastAPI" ".dev-logs/api-err.log"

setsid -w bash -c 'cd app && npm run dev' \
  </dev/null >.dev-logs/app-out.log 2>.dev-logs/app-err.log &
APP_PGID=$!

wait_for_http "http://127.0.0.1:5173/" "Vite" ".dev-logs/app-err.log"

echo ""
echo "Ready:"
echo "  FastAPI:   http://127.0.0.1:8000  (http://localhost:8000)"
echo "  SvelteKit: http://127.0.0.1:5173  (http://localhost:5173)"
echo ""
echo "Press Ctrl+C to stop both, or run 'scripts/dev-start.sh --stop' from another shell."

wait
