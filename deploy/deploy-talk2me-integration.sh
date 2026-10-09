#!/usr/bin/env bash
# Apply only the reviewed adapter/inbox patch to the currently published backend.
set -Eeuo pipefail
umask 077
INSTALL=/opt/talk2me
PACKAGE="$INSTALL/central-integration-20261009"
NEW="$INSTALL/releases/central-integration-20261009"
OLD=$(readlink -f "$INSTALL/current")
exec 9>"$INSTALL/.deploy.lock"
flock -n 9 || exit 1
test "$OLD" = /opt/talk2me/releases/20261009-layout-ed4c4d6
test ! -e "$NEW"
test "$(docker inspect talk2me-api-1 --format '{{.Image}}')" = sha256:8e23d6925689a4a10eca192fa787ca5f6baef50660f578ec8305f71713504c2e
mkdir -p "$NEW" "$INSTALL/backups"
cp -a "$OLD/." "$NEW/"
cp "$PACKAGE/fornada_adapter.py" "$NEW/backend/app/fornada_adapter.py"
cp "$PACKAGE/messaging.py" "$NEW/backend/app/messaging.py"
cat > "$NEW/backend/Dockerfile.integration" <<'DOCKER'
FROM talk2me-backend:20261009T190324Z-748ea77
COPY --chown=10001:10001 backend/app/fornada_adapter.py backend/app/messaging.py /app/app/
DOCKER
cd "$NEW"
docker build --network none -f backend/Dockerfile.integration -t talk2me-backend:central-integration-20261009 .
python3 - <<'PY'
from pathlib import Path
p=Path('compose.production.yml')
s=p.read_text()
assert s.count('talk2me-backend:${CENTRAL_RELEASE:?Set release}') == 1
p.write_text(s.replace('talk2me-backend:${CENTRAL_RELEASE:?Set release}', 'talk2me-backend:central-integration-20261009'))
PY
DC=(docker compose --env-file "$INSTALL/shared/.env" -f "$NEW/compose.production.yml")
PREVIOUS=(docker compose --env-file "$INSTALL/shared/.env" -f "$OLD/compose.production.yml")
"${DC[@]}" config --quiet
PAUSED=false
recover() {
  if "$PAUSED"; then
    "${PREVIOUS[@]}" up -d --no-build --pull never --no-deps api messaging agents operations
    "${PREVIOUS[@]}" restart web
  fi
}
trap recover ERR
"${PREVIOUS[@]}" stop -t 60 messaging agents operations api
PAUSED=true
BACKUP="$INSTALL/backups/central-integration-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker exec talk2me-postgres-1 pg_dump -U central -d central -Fc > "$BACKUP"
test -s "$BACKUP"
VERIFY_DB="central_deploy_verify_$(date +%s)_$$"
docker exec talk2me-postgres-1 createdb -U central "$VERIFY_DB"
docker exec -i talk2me-postgres-1 pg_restore -U central -d "$VERIFY_DB" --exit-on-error < "$BACKUP"
docker exec talk2me-postgres-1 dropdb -U central "$VERIFY_DB"
echo "Backup da central restaurado: $BACKUP"
"${DC[@]}" up -d --no-build --pull never --no-deps --wait --wait-timeout 180 api messaging agents operations
"${DC[@]}" restart web
curl --fail --silent --show-error --retry 6 --retry-delay 3 --retry-all-errors --output /dev/null https://talk2me.atospd.com/
test "$(curl --silent --output /dev/null --write-out '%{http_code}' https://talk2me.atospd.com/api/auth/me)" = 401
ln -s "$NEW" "$INSTALL/current.central-next"
mv -Tf "$INSTALL/current.central-next" "$INSTALL/current"
"${DC[@]}" ps
trap - ERR
echo "Deploy concluído: $NEW"
