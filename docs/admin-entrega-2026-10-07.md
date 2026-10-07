# Entrega administrativa — 07/10/2026

Conta `leonardo.furlan@atospd.com` criada como superusuário em tenant administrativo separado. Login: https://fornada.atospd.com/login. Diretório de contas: https://fornada.atospd.com/admin.

Credenciais geradas em arquivo local ignorado pelo Git; senha não está neste relatório, nos fontes publicados ou nos logs. A criação rejeita e-mail já cadastrado e não promove silenciosamente contas existentes. A senha tem 32 caracteres aleatórios e hash bcrypt com custo 12. Ainda não há troca autônoma de senha nem MFA; esses requisitos estão no planejamento.

## Funcionalidade publicada

- Perfil `is_superuser` persistido; cadastro público não concede o perfil.
- Busca paginada por nome, e-mail ou negócio; sem exposição de hashes.
- Acesso de suporte a usuário ativo de empresa ativa, exigindo motivo, válido por 15 minutos.
- Operador mantém o próprio token; sessão de suporte identifica operador, usuário de destino e empresa. O backend revalida os privilégios a cada requisição.
- Requisições de negócio continuam passando pelos filtros de tenant dos módulos existentes.
- Banner de suporte, identificação da conta e retorno à administração; recarga ao trocar o contexto descarta consultas/formulários anteriores.
- Persistência de início, motivo, prazo e encerramento; logs de requisições com operador e destino. Interface de auditoria e valores antes/depois ainda não implementados.

## Publicação e preservação da versão existente

A VPS estava no commit `bae8bfac6b74868ce8d48d8cf734a65d987301f4`, com OCR híbrido mais recente que o checkout local. As imagens publicadas foram construídas a partir desse commit com apenas o conjunto administrativo sobreposto. Preservados código/configuração do OCR, integração Evolution, worker e segredos existentes.

O pacote de fontes e imagens foi verificado por SHA256 na VPS. Fontes anteriores arquivados em `backups/fornada-source-before-admin-*`; imagens anteriores preservadas como `fornada-backend:before-admin-20261007` e `fornada-frontend:before-admin-20261007`. Não houve commit, push ou merge. Os fontes administrativos foram aplicados ao checkout da VPS; ele possui alterações versionadas locais e o deploy com pull deve considerar isso antes da próxima atualização.

Backup PostgreSQL: `/opt/fornada/backups/fornada-20261007T121212Z-420255.dump`. Restauração integral verificada em banco temporário antes da migração. Migration aplicada: `2798d1537c70` → `91ae81c71007`; Alembic confirmou a revisão final como `head`.

Deploy em modo `public-micro`, com `--skip-pull`, imagens compatíveis construídas fora da VPS. API, frontend, PostgreSQL, Redis, Caddy e worker retornaram ao estado operacional; API confirmou `/health`. O deploy teve parada temporária dos serviços de aplicação durante backup/migração. Volumes e dados existentes foram preservados.

## Validação

| Verificação | Resultado |
|---|---|
| Backend local, banco PostgreSQL temporário | 226 aprovados, 4 pulados |
| Backend da base de produção + alterações administrativas | 250 aprovados, 4 pulados |
| Cenários administrativos de integração | 11 aprovados; incluídos nos totais acima |
| Frontend com testes de acesso administrativo | 37 aprovados |
| TypeScript | Aprovado |
| Ruff nos arquivos de acesso/rotas/criação/testes | Aprovado |
| Builds Linux/amd64 do backend e frontend de produção | Aprovados |
| `git diff --check` | Aprovado |
| Login HTTPS da conta criada | 200 e perfil superusuário confirmado |
| Diretório administrativo HTTPS | 200; três contas visíveis na validação |
| Abertura de suporte, apenas para consultas | 201 |
| Identidade e dashboard da conta de destino | 200 |
| Encerramento da sessão de verificação | 204 |
| Tentativa de reutilizar a sessão encerrada | 403 |

A validação pública não alterou receitas, estoque, pedidos ou dados operacionais de clientes. Criou e encerrou uma sessão identificada como verificação após publicação. Os testes de escrita e isolamento rodaram exclusivamente no banco temporário.

Aceite visual completo em desktop e 390 px segue pendente: o navegador de automação não alcançou o servidor local. Build e testes de componentes foram concluídos, mas não substituem essa inspeção. O painel completo de gestão/manutenção permanece proposto em [painel-admin.md](painel-admin.md).

## Arquivos centrais

Autorização: `backend/api/dependencies.py`; rotas: `backend/api/routers/admin.py`; modelos: `backend/infrastructure/database/models.py`; migration: `backend/alembic/versions/91ae81c71007_superusuario_suporte.py`; criação: `backend/scripts/criar_superusuario.py`; tela: `frontend/app/(dashboard)/admin/page.tsx`; banner: `frontend/components/shared/support-banner.tsx`; contexto por aba: `frontend/lib/admin-session.ts`.

Próxima proposta: ADM-02 (gestão de usuários/negócios) e ADM-03 (auditoria consultável), antes de operações em lote, integrações e manutenção de infraestrutura. As políticas e prioridades ainda precisam ser confirmadas.

## Ajuste do motivo de acesso — 07/10/2026

Por solicitação do usuário, o formulário de motivo deixou de aparecer abaixo da lista de contas. Agora abre em modal fixo no topo da área visível ao clicar em “Acessar conta”, independentemente da rolagem. O campo recebe foco inicial, o fundo fica bloqueado e Cancelar/Escape fecham o modal sem iniciar suporte. Durante a abertura da sessão, o modal não pode ser dispensado acidentalmente.

Validação: TypeScript, cinco testes de acesso/modal e build Linux de produção aprovados. Inspeção realizada no site publicado em desktop e 390 px: no celular o modal ficou a 16 px do topo e das laterais, com largura de 358 px e campo do motivo focado; cancelamento conferido sem confirmar acesso a cliente.

Atualização aplicada somente ao frontend, usando cópia dos fontes atuais da VPS. API, worker, banco e cache mantiveram os containers existentes. Fonte anterior preservado em `backups/admin-page-before-modal-20261007T124743Z.tsx`; imagem anterior preservada como `fornada-frontend:before-admin-modal-20261007`. Imagem nova: `fornada-frontend:admin-modal-20261007`. A rota pública `/admin` respondeu após a recriação do frontend. Não houve migration, commit ou push nesta correção.
