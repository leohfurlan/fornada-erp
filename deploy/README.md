# Publicação do Fornada

## Deploy por script

Na VPS, com os fontes atualizados em `/opt/fornada` e o `.env.pilot` existente:

```sh
cd /opt/fornada
# Copie primeiro as novas imagens amd64 construídas fora da VPS.
bash deploy/deploy.sh --images /opt/fornada/fornada-images.tar
```

O modo padrão é o piloto privado de 1 GB. O script valida a configuração, carrega
as imagens, baixa PostgreSQL/Redis/Caddy, suspende os serviços da aplicação,
faz backup com permissões restritas e testa a restauração em banco temporário.
Depois aplica migrations, inicia serviços e verifica `/health` e `/login`.
O worker do piloto é iniciado quando `EVOLUTION_ENABLED=true`.
Backup, criação e remoção do banco temporário usam `docker exec` sem entrada
interativa; somente a restauração usa `-i` para receber o arquivo. Isso evita
o caminho de `docker compose exec` que ficou suspenso durante o piloto.
As imagens devem corresponder aos fontes e migrations desta versão; o script
não constrói imagens no modo piloto. Não envie `.env` ou backups ao Git.

Para conferir sem alterar serviços: `bash deploy/deploy.sh --check` (as imagens
precisam já estar carregadas). Para servidor com domínio e recursos para build:
`bash deploy/deploy.sh --mode production --env-file .env.production`.

Se backup, restauração ou migration falhar, o script interrompe a atualização.
Os serviços podem ficar parados: inspecione o erro e o backup antes de reiniciar.
Não há downgrade automático de schema. Guarde também uma cópia do backup fora
da VPS. O script deve ser executado no servidor; não envia arquivos por SSH.

Hospedagem escolhida: **Oracle VPS**. Sem domínio por enquanto: consultar
[homologação privada por SSH e transição para HTTPS](oracle.md).

Preparação para um servidor Linux com Docker Compose, domínio apontado ao IP do
servidor e portas 80/443 liberadas. Configuração criada em 06/10/2026; ainda requer
teste real dos containers antes de publicar.

1. Copiar `.env.production.example` para `.env.production` no servidor.
2. Configurar APP_DOMAIN, SECRET_KEY aleatória e POSTGRES_PASSWORD aleatória.
   Para a senha do banco, usar caracteres alfanuméricos (ela é interpolada na URL).
   Gerar cada segredo com `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Configurar GOOGLE_AI_API_KEY para habilitar leitura de cupons. Sem chave, OCR
   retorna erro em produção; não produz itens fictícios. SENTRY_DSN é opcional.
4. Executar a sequência abaixo, após concluir os gates do relatório de status.

```sh
docker compose --env-file .env.production -f docker-compose.prod.yml build
docker compose --env-file .env.production -f docker-compose.prod.yml up -d db redis
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm backend alembic upgrade head
docker compose --env-file .env.production -f docker-compose.prod.yml up -d
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

Caddy solicita certificado HTTPS automaticamente. O navegador chama `/api/v1`
no mesmo domínio; PostgreSQL, Redis e API não expõem portas no host. Containers
da aplicação usam usuários sem privilégios e não montam o código do host.
Não definir NEXT_PUBLIC_API_URL local no build de produção.

Validar cadastro, login, renovação de sessão, receita, entrada de ingrediente,
OP → produto acabado → venda e isolamento entre duas contas, em desktop e celular.
`/health` mede apenas se o processo da API responde, não a disponibilidade do banco.

## Dados e atualizações

Antes de cada atualização com migrations, fazer backup PostgreSQL e testar a
restauração em banco separado. Exemplo de backup no servidor Linux:

```sh
mkdir -p backups
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T db pg_dump -U fornada -d fornada -Fc > backups/fornada.dump
```

O backup contém dados de clientes: limitar permissões e manter cópia fora do
servidor. Nunca executar `down -v` num ambiente com dados a preservar.
Não reverter código após migration incompatível sem plano de recuperação.
Definir rotina, retenção e teste de restauração antes de receber dados reais.

## Pendências antes de disponibilizar

Verificar atualização de segurança de dependências, suíte de integração e build.
Migrar refresh token para cookie httpOnly, implementar recuperação de senha e
validar rate limiting atrás do proxy (atualmente a API vê o IP do proxy).
As migrations são etapa explícita, nunca executadas automaticamente no startup.
