# Evidências — 06/10/2026

## Continuação: composição, estoque preparado e WhatsApp

### Preparação do PR e deploy

- Suítes repetidas antes do commit: 209 testes backend e 28 frontend aprovados; TypeScript sem erros.
- `deploy/deploy.sh`: sintaxe Bash validada e quatro cenários simulados aprovados: modo check sem alterações de serviços, deploy completo com restauração antes da migration, interrupção após falha de restauração e interrupção após falha de migration.
- Testes do script não usam Docker nem a VPS. A execução real do deploy e os testes no piloto continuam pendentes.
- Scripts `.sh` configurados com LF via `.gitattributes`. Backups e lock de deploy ignorados pelo Git.

- Backend: suíte completa com 209 testes aprovados, em PostgreSQL local isolado `fornada_test_v2`, porta 55432. O total inclui testes de alterações concorrentes preservadas no workspace.
- Frontend: 28 testes aprovados, TypeScript sem erros e build Next.js de produção concluído.
- Migrações verificadas desde banco vazio. As novas migrações de composição/estoque intermediário e onboarding foram inspecionadas para retirar alterações de índices alheias ao escopo. Nenhuma migração executada na VPS.
- Composição: vínculos por tenant, unidades compatíveis, prevenção de ciclos, custo proporcional de receitas-base, mão de obra, operação, ingredientes diretos e embalagens.
- Produção: reserva de massas/recheios preparados, consumo sem nova baixa dos ingredientes crus, cancelamento com liberação e proteção das reservas contra vendas. A ordem guarda a ficha e o consumo vigentes na criação.
- OTP: testes com Redis real e transporte Evolution simulado cobrem concorrência, expiração, tentativas, reenvio, falha de envio e provas de autenticação de uso único. Telefones brasileiros conservam o nono dígito.
- Navegador: login real na API local, navegação direta após hidratação da sessão, edição e gravação real da ficha. Conferidos desktop de 1280 px e celular de 390 px sem rolagem horizontal. As telas de telefone/código/endereço foram inspecionadas com envio simulado; isso não comprova entrega pelo WhatsApp.
- Capturas locais: `output/playwright/ficha-mobile.png`, `ficha-desktop.png`, `whatsapp-mobile.png` e `onboarding-mobile.png`.
- Pendências: configurar e conectar uma instância Evolution, validar entrega real e recuperação assistida, preparar atualização da VPS e executar aceite no ambiente piloto. O acesso WhatsApp fica desativado por padrão; login por e-mail permanece disponível para contas existentes.
- Sem commit, push ou deploy. Alterações preexistentes e concorrentes preservadas.

## Primeira etapa: ficha editorial e boas-vindas

Os registros abaixo descrevem a primeira etapa; as funcionalidades então pendentes avançaram conforme a validação acima.

- Backend: 165 testes passaram (unitários e integração), em PostgreSQL local isolado `fornada_test`, porta 55432.
- Frontend: 22 testes passaram; TypeScript sem erros; build Next.js de produção concluído, incluindo `/boas-vindas` e `/receitas/[id]/ficha-tecnica`.
- Migração eb1a9dcd61f4 gerada por Alembic, inspecionada e aplicada somente no banco isolado. Exclusões de índices de outros módulos retiradas antes da entrega.
- Cobertura nova: faixas, decimais, embalagem versus capacidade, camadas repetidas/ordem, tenant, conflito de revisão, cópia, reordenação na tela e rascunho preservado após falha.
- Duas fixtures antigas de compras corrigidas para criar o outro tenant antes do ingrediente. Nenhuma regra de compras alterada nessa correção.
- Inspeção visual em navegador desktop/celular e teste real na VPS pendentes. A estrutura da tela se adapta à largura, mas o build não comprova experiência visual.
- Login WhatsApp, vínculos de receitas-base, custos da composição, histórico/snapshot da ficha e estoque intermediário ainda não implementados. Tutorial é guia de links, não tour interativo com progresso persistido.
- Sem commit, push ou atualização da VPS nesta rodada. Alterações preexistentes preservadas.
