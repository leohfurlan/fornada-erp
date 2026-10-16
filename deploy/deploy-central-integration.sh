#!/usr/bin/env bash
# Release prepared from the inspected production source tree, not an old checkout.
set -Eeuo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
INSTALL=/opt/fornada
PREVIOUS="$INSTALL/releases/ifood-alertas-20261007-01"
exec 9>"$INSTALL/.deploy.lock"
flock -n 9 || { echo 'Outro deploy está em execução.' >&2; exit 1; }
cd "$ROOT"
DC=(sudo -n docker compose --env-file "$INSTALL/.env.production" -f "$ROOT/docker-compose.prod.yml" -f "$ROOT/docker-compose.micro.yml" -f "$ROOT/docker-compose.ifood.yml" --profile worker --profile ifood)
OLD=(sudo -n docker compose --env-file "$INSTALL/.env.production" -f "$PREVIOUS/docker-compose.prod.yml" -f "$PREVIOUS/docker-compose.micro.yml" -f "$PREVIOUS/docker-compose.ifood.yml" --profile worker --profile ifood)
"${DC[@]}" config --quiet
sudo -n docker image inspect fornada-backend:central-20261009-02 >/dev/null
python3 - "$ROOT/preflight-images.json" <<'PY'
import json, subprocess, sys
for name, expected in json.load(open(sys.argv[1])).items():
    actual = subprocess.check_output(['sudo','-n','docker','inspect',name,'--format','{{.Image}}'], text=True).strip()
    assert actual == expected, 'Published image changed: ' + name
PY
STAMP=$(date -u +%Y%m%dT%H%M%SZ)-$$
BACKUP="$INSTALL/backups/central-$STAMP.dump"
mkdir -p "$INSTALL/backups"
chmod 700 "$INSTALL/backups"
cp "$INSTALL/.env.production" "$INSTALL/backups/env-before-central-$STAMP"
chmod 600 "$INSTALL/backups/env-before-central-$STAMP"
PAUSED=false
recover() {
  echo 'Deploy interrompido; restaurando serviços da release anterior, sem apagar dados.' >&2
  if "$PAUSED"; then "${OLD[@]}" up -d --no-build --pull never --no-deps backend celery ifood; fi
}
trap recover ERR
sudo -n docker stop --time 60 fornada-prod-ifood-1 fornada-prod-celery-1 fornada-prod-backend-1
PAUSED=true
sudo -n docker exec fornada-prod-db-1 pg_dump -U fornada -d fornada -Fc > "$BACKUP"
test -s "$BACKUP"
VERIFY_DB="fornada_central_verify_$(date +%s)_$$"
sudo -n docker exec fornada-prod-db-1 createdb -U fornada "$VERIFY_DB"
sudo -n docker exec -i fornada-prod-db-1 pg_restore -U fornada -d "$VERIFY_DB" --exit-on-error < "$BACKUP"
# Validate the actual backup against the candidate migration before production.
"${DC[@]}" run -T --rm --pull never --no-deps backend python -c 'import os,subprocess,sys; from sqlalchemy.engine import make_url; os.environ["DATABASE_URL"]=make_url(os.environ["DATABASE_URL"]).set(database=sys.argv[1]).render_as_string(hide_password=False); subprocess.run(["alembic","upgrade","head"],check=True)' "$VERIFY_DB" </dev/null
sudo -n docker exec fornada-prod-db-1 dropdb -U fornada "$VERIFY_DB"
echo "Backup restaurado e migration validada: $BACKUP"
"${DC[@]}" run -T --rm --pull never --no-deps backend alembic upgrade head </dev/null
"${DC[@]}" up -d --no-build --pull never --no-deps --wait --wait-timeout 240 backend celery ifood
curl --fail --silent --show-error --retry 8 --retry-delay 3 --retry-all-errors --max-time 15 https://fornada.atospd.com/health
test "$(curl --silent --output /dev/null --write-out '%{http_code}' https://fornada.atospd.com/login)" = 200
sudo -n docker exec fornada-prod-backend-1 python -c 'from core.config import settings; assert not settings.central_enabled; from infrastructure.ocr.factory import get_receipt_extractor; print("Central desativada; OCR atual preservado")'
sudo -n docker exec fornada-prod-db-1 psql -U fornada -d fornada -Atc 'SELECT version_num FROM alembic_version'
"${DC[@]}" ps
trap - ERR
echo "Deploy concluído: $ROOT"
