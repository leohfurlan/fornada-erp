#!/usr/bin/env bash
# Execute no servidor, a partir de um checkout/pacote atualizado.
set -Eeuo pipefail
umask 077

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
MODE=pilot
ENV_FILE=
IMAGES=
CHECK=false
usage() {
  echo 'Uso: bash deploy/deploy.sh [--mode pilot|production] [--env-file ARQUIVO] [--images TAR] [--check]'
  echo 'Pilot: usa imagens prontas e acesso privado 127.0.0.1:8080. Production: constrói imagens no servidor.'
  echo '--check valida configuração e imagens sem alterar serviços. --images carrega um docker save antes do deploy.'
}
while (($#)); do
  case "$1" in
    --mode|--env-file|--images)
      (($# >= 2)) || { usage; exit 2; }
      case "$1" in
        --mode) MODE=$2 ;;
        --env-file) ENV_FILE=$2 ;;
        --images) IMAGES=$2 ;;
      esac
      shift 2 ;;
    --check) CHECK=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done
[[ "$MODE" == pilot || "$MODE" == production ]] || { usage; exit 2; }
[[ -n "$ENV_FILE" ]] || ENV_FILE=".env.$MODE"
[[ -f "$ENV_FILE" ]] || { echo "Arquivo ausente: $ENV_FILE. Configure os segredos no servidor." >&2; exit 1; }
for cmd in docker python3 curl flock; do
  command -v "$cmd" >/dev/null || { echo "Instale $cmd antes de continuar." >&2; exit 1; }
done
exec 9>"$ROOT/.deploy.lock"
flock -n 9 || { echo 'Outro deploy está em execução.' >&2; exit 1; }
DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
  "${DOCKER[@]}" info >/dev/null
fi
DC=("${DOCKER[@]}" compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)
if [[ "$MODE" == pilot ]]; then
  DC+=(-f docker-compose.pilot.yml -f docker-compose.micro.yml)
fi
"${DC[@]}" config --quiet
# Ler a configuração efetiva sem imprimir segredos nem executar o arquivo .env.
WORKER=$("${DC[@]}" config --format json | python3 -c 'import json,sys; c=json.load(sys.stdin); print(str(c["services"]["backend"]["environment"].get("EVOLUTION_ENABLED", "false")).lower())')
if [[ "$WORKER" == true || "$WORKER" == 1 ]]; then DC+=(--profile worker); fi
if [[ "$MODE" == pilot ]]; then
  if [[ -n "$IMAGES" ]]; then
    [[ -f "$IMAGES" ]] || { echo "Arquivo de imagens ausente: $IMAGES" >&2; exit 1; }
    if [[ "$CHECK" == false ]]; then "${DOCKER[@]}" image load -i "$IMAGES"; fi
  fi
  for image in fornada-backend:pilot fornada-frontend:pilot; do
    "${DOCKER[@]}" image inspect "$image" >/dev/null || {
      echo "Carregue $image com docker image load ou --images antes de continuar." >&2; exit 1;
    }
  done
fi
if [[ "$CHECK" == true ]]; then echo 'Configuração e imagens locais verificadas; serviços preservados.'; exit 0; fi
chmod 600 "$ENV_FILE"
trap 'echo "Deploy interrompido. Preserve o backup; inspecione os serviços antes de tentar novamente. Não foi feita reversão automática." >&2' ERR
if [[ "$MODE" == production ]]; then "${DC[@]}" build backend frontend celery; fi
"${DC[@]}" pull db redis proxy
"${DC[@]}" up -d --wait --wait-timeout 180 db redis

# Suspender os escritores para um backup consistente com a atualização.
"${DC[@]}" stop proxy frontend backend celery
mkdir -p backups
chmod 700 backups
STAMP=$(date -u +%Y%m%dT%H%M%SZ)-$$
BACKUP="$ROOT/backups/fornada-$STAMP.dump"
DB_CONTAINER=$("${DC[@]}" ps -q db)
[[ -n "$DB_CONTAINER" ]] || { echo 'Container PostgreSQL ausente.' >&2; exit 1; }
echo 'Gerando backup PostgreSQL (sem entrada interativa)...'
"${DOCKER[@]}" exec "$DB_CONTAINER" pg_dump -U fornada -d fornada -Fc > "$BACKUP"
[[ -s "$BACKUP" ]] || { echo 'Backup vazio; deploy cancelado.' >&2; exit 1; }
# Testar restauração em banco temporário antes de aplicar migrations.
VERIFY_DB="fornada_restore_$(date -u +%s)_$$"
echo 'Testando restauração em banco temporário...'
"${DOCKER[@]}" exec "$DB_CONTAINER" createdb -U fornada "$VERIFY_DB"
if ! "${DOCKER[@]}" exec -i "$DB_CONTAINER" pg_restore -U fornada -d "$VERIFY_DB" --exit-on-error < "$BACKUP"; then
  "${DOCKER[@]}" exec "$DB_CONTAINER" dropdb -U fornada "$VERIFY_DB" || true
  echo 'Restauração de verificação falhou; serviços continuam parados e migrations não foram aplicadas.' >&2
  exit 1
fi
"${DOCKER[@]}" exec "$DB_CONTAINER" dropdb -U fornada "$VERIFY_DB"
echo "Backup verificado: $BACKUP"
echo 'Aplicando migrations...'
"${DC[@]}" run -T --rm --pull never backend alembic upgrade head </dev/null
SERVICES=(backend frontend proxy)
if [[ "$MODE" == production || "$WORKER" == true || "$WORKER" == 1 ]]; then SERVICES+=(celery); fi
"${DC[@]}" up -d --no-build --pull never --wait --wait-timeout 240 "${SERVICES[@]}"
if [[ "$MODE" == pilot ]]; then
  URL=http://127.0.0.1:8080
else
  DOMAIN=$("${DC[@]}" config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["proxy"]["environment"]["APP_DOMAIN"])')
  URL="https://$DOMAIN"
fi
curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-connrefused --retry-all-errors --max-time 15 "$URL/health"
echo
curl --fail --silent --show-error --retry 12 --retry-delay 5 --retry-connrefused --retry-all-errors --max-time 15 --output /dev/null "$URL/login"
"${DC[@]}" ps
echo "Deploy concluído. Valide login e operações de negócio. Backup: $BACKUP"
if [[ "$MODE" == pilot ]]; then echo 'Acesso via túnel SSH para localhost:8080; a porta permanece privada.'; fi
