#!/usr/bin/env bash
# Testes isolados: nenhum Docker, banco, curl ou deploy real é executado.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/app/deploy" "$TMP/bin"
cp "$ROOT/deploy/deploy.sh" "$TMP/app/deploy/"
touch "$TMP/app/.env.pilot"
export TRACE="$TMP/trace"
export REAL_PYTHON
if [[ -f "$ROOT/backend/.venv/Scripts/python.exe" ]]; then
  REAL_PYTHON="$ROOT/backend/.venv/Scripts/python.exe"
else
  REAL_PYTHON=$(command -v python3 || command -v python)
fi
cat > "$TMP/bin/python3" <<'SH'
#!/usr/bin/env bash
exec "$REAL_PYTHON" "$@"
SH
cat > "$TMP/bin/docker" <<'SH'
#!/usr/bin/env bash
echo "$*" >> "$TRACE"
case "$*" in
  *'compose '*'exec '*) echo 'Compose exec interativo proibido neste fluxo' >&2; exit 99 ;;
  *'ps -q db'*) echo 'qa-db-container' ;;
  *'config --format json'*) echo '{"services":{"backend":{"environment":{"EVOLUTION_ENABLED":"false"}},"proxy":{"environment":{"APP_DOMAIN":"example.com"}}}}' ;;
  *'pg_dump '*) echo 'mock-dump' ;;
  *'pg_restore '*) cat >/dev/null; [[ ${FAIL_RESTORE:-0} != 1 ]] ;;
  *'alembic upgrade head'*) [[ ${FAIL_MIGRATION:-0} != 1 ]] ;;
esac
exit ${PIPESTATUS[0]:-0}
SH
cat > "$TMP/bin/curl" <<'SH'
#!/usr/bin/env bash
echo "curl $*" >> "$TRACE"
[[ "$*" == *'--retry-all-errors'* ]] || { echo 'Checagem HTTP sem retry para reset de conexão' >&2; exit 56; }
SH
cat > "$TMP/bin/flock" <<'SH'
#!/usr/bin/env bash
exit 0
SH
chmod +x "$TMP/bin/"*
export PATH="$TMP/bin:$PATH"

bash "$TMP/app/deploy/deploy.sh" --check >/dev/null
if grep -Eq 'pg_dump|alembic| up | stop | pull |image load|curl ' "$TRACE"; then
  echo '--check alterou serviços' >&2; exit 1
fi
: > "$TRACE"
bash "$TMP/app/deploy/deploy.sh" >/dev/null
grep -q 'pg_dump ' "$TRACE"
grep -q 'pg_restore ' "$TRACE"
grep -q 'alembic upgrade head' "$TRACE"
grep -q 'curl .*127.0.0.1:8080/login' "$TRACE"
python3 - "$TRACE" <<'PY'
import sys
from pathlib import Path
trace = Path(sys.argv[1]).read_text()
assert trace.index(" stop ") < trace.index("pg_dump ") < trace.index("pg_restore ") < trace.index("alembic upgrade head") < trace.index("up -d --no-build")
PY

: > "$TRACE"
if FAIL_RESTORE=1 bash "$TMP/app/deploy/deploy.sh" >/dev/null 2>&1; then
  echo 'Falha de restauração foi ignorada' >&2; exit 1
fi
if grep -q 'alembic upgrade head' "$TRACE"; then echo 'Migrou após restauração falhar' >&2; exit 1; fi

: > "$TRACE"
if FAIL_MIGRATION=1 bash "$TMP/app/deploy/deploy.sh" >/dev/null 2>&1; then
  echo 'Falha de migration foi ignorada' >&2; exit 1
fi
if grep -q 'up -d --no-build' "$TRACE"; then echo 'Iniciou aplicação após migration falhar' >&2; exit 1; fi
: > "$TRACE"
touch "$TMP/app/.env.production"
bash "$TMP/app/deploy/deploy.sh" --mode public-micro >/dev/null
grep -q -- '--env-file .env.production -f docker-compose.prod.yml -f docker-compose.micro.yml' "$TRACE"
grep -q 'curl .*https://example.com/login' "$TRACE"
if grep -Eq 'docker-compose.pilot.yml| build ' "$TRACE"; then echo 'Modo público usou configuração privada ou build' >&2; exit 1; fi
echo '5 cenários de deploy aprovados: check, sucesso, falha de restauração, falha de migration e HTTPS público micro.'
