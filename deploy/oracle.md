# Oracle VPS — homologação e publicação

Para criar a instância, seguir [o roteiro de criação](oracle-criacao.md).

Decisão de 06/10/2026: hospedar o Fornada na Oracle VPS. Domínio ainda não comprado.
A existência, os recursos e o sistema operacional da VM ainda devem ser confirmados.

## Topologia

Na VPS ficam Caddy, Next.js, FastAPI, PostgreSQL, Redis e worker Celery em Docker.
PostgreSQL e Redis permanecem internos. Volumes persistem os dados no servidor;
backup deve ter cópia externa. Nenhum serviço externo de banco foi escolhido.

Antes de instalar, conferir sistema operacional, arquitetura (`uname -m`), RAM,
disco livre, containers existentes e portas ocupadas. Não presumir Ubuntu em
Oracle Linux nem substituir serviços já hospedados. Builds Node/Python e os
serviços compartilham recursos: medir consumo no piloto antes de definir capacidade.
As imagens não forçam arquitetura amd64; build ARM precisa de validação real.

Oracle Linux usa normalmente usuário `opc`; Ubuntu, `ubuntu`. Confirmar a imagem
antes de instalar Docker/Compose. Instalação e firewall serão adaptados ao SO real.
Documentação: https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm.

## Piloto sem domínio

Para homologação, usar túnel SSH: a porta HTTP do proxy fica vinculada somente a
127.0.0.1 na VPS. O tráfego remoto é transportado pelo SSH. Não liberar 8080,
3000, 8000, 5432 ou 6379 na rede pública. Isso é acesso privado para testes;
não é o lançamento público nem substitui os gates de autenticação/integração.

Requer Docker Compose 2.24.4+ (`!override`). No servidor, copiar
`.env.pilot.example` para `.env.pilot`, gerar os segredos como descrito no README
de publicação e limitar permissões com `chmod 600 .env.pilot`.

Com o repositório no diretório escolhido da VPS:

```sh
docker compose --env-file .env.pilot -f docker-compose.prod.yml -f docker-compose.pilot.yml config --quiet
docker compose --env-file .env.pilot -f docker-compose.prod.yml -f docker-compose.pilot.yml build
docker compose --env-file .env.pilot -f docker-compose.prod.yml -f docker-compose.pilot.yml up -d db redis
docker compose --env-file .env.pilot -f docker-compose.prod.yml -f docker-compose.pilot.yml run --rm backend alembic upgrade head
docker compose --env-file .env.pilot -f docker-compose.prod.yml -f docker-compose.pilot.yml up -d
curl --fail http://127.0.0.1:8080/health
```

Os segredos de exemplo devem ser substituídos; não executar migrations em banco
existente sem backup. Piloto e produção usam o mesmo nome Compose e os mesmos
volumes: são duas configurações do mesmo ambiente, não ambientes isolados.

No PowerShell local, depois de confirmar o alias SSH:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8080:127.0.0.1:8080 ALIAS_DA_VPS
```

Manter o túnel aberto e acessar http://localhost:8080. Cadastro, login e API
usam o mesmo endereço. Acesso pelo celular requer outra forma de acesso seguro;
o túnel local no PC não valida por si só o uso real no celular.

## Publicação com domínio

Após homologar, comprar ou usar um domínio disponível, apontar o registro A ao
IP público da VPS e configurar APP_DOMAIN em `.env.production` com o hostname,
sem protocolo. Publicar apenas com docker-compose.prod.yml, sem o override piloto.
Seguir deploy/README.md preservando senhas, chave e dados já existentes.

Na OCI, verificar regras de ingresso da VCN/NSG/Security List e firewall do SO.
Liberar TCP 80/443 para web e restringir SSH conforme a administração escolhida.
Verificar conflitos de portas antes de iniciar Caddy. Certificado público via
Caddy depende de DNS e acesso externo adequados:
https://caddyserver.com/docs/quick-starts/https.

## Próxima ação

Identificar a VM (alias SSH ou IP, usuário, SO, RAM) e inspecioná-la antes de
instalar ou publicar. Nenhuma conexão à VPS ou alteração remota foi feita ao
preparar estes arquivos.
