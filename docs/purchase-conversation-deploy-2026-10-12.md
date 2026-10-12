# Publicação da revisão conversacional — 2026-10-12

Autorização explícita do proprietário para commit, push, deploy, migrações e ativação coordenada.

- Código Fornada a36c963, publicado em codex/compras-produtos-aprovados, sem merge em main.
- Release /opt/fornada/releases/dialogue-a36c963; imagem fornada-backend:dialogue-a36c963 nos serviços backend, celery e ifood.
- Frontend PWA preservado: fornada-frontend:pwa-20261012.
- Migração real c409e872a103, aplicada após restauração do backup e ensaio de migração em banco temporário. Backup /opt/fornada/backups/dialogue-20261012T212215Z.dump.
- Hashes dos arquivos anteriores conferidos contra a imagem ativa pwa-0ffee70. Somente cinco arquivos de backend/migração desta feature foram acrescentados à imagem.
- Saúde backend, página de login, iFood e celery verificados após publicação.

Talk2Me: código f1d6a66 mais correção Google 6c57aca, imagem talk2me-backend:dialogue-6c57aca e migração 0013_purchase_dialogue. Diálogo ativado somente para Fornada após 2026-10-12T21:29:13.240961+00:00 (18h29 Brasília), sem replay do histórico e sem alterar controle humano de conversas.

O Google real passou em três testes sintéticos: quantidade, desconto unitário convertido ao total e solicitação de remoção. Resposta Markdown identificada nessa homologação foi tratada no Talk2Me com schema estrito; testes positivos e negativos passaram. Não houve alteração de billing. Orçamento local: 6 chamadas/minuto, 100/dia, 1.000/mês, concorrência 1 e até 2.048 tokens de saída.

Verificação autenticada Talk2Me → Fornada confirmou resolve ALLOWED, catálogo não truncado (40 materiais, 4 produtos, 2 fornecedores) e 404 esperado para conversation-draft com proposta inexistente. Nenhuma proposta histórica foi editada/reexecutada e nenhuma movimentação de estoque foi feita pelos probes.

Falta o aceite de uma compra nova real pelo WhatsApp: foto → correção em linguagem natural → confirmação de remoção → resumo → aprovação final. SIM continua restrito à confirmação de remoção; só APROVAR o resumo atual autoriza cadastros/estoque. OCR sem itens e resultados incertos continuam exigindo revisão humana.

Preservar compose.dialogue.yml e a cadeia efetiva registrada em release.json nos próximos deploys; a configuração privada existente de OCR/iFood foi mantida. Relatório detalhado e guia atualizados no repositório whatsapp-admin, docs/operations/deploy-dialogue-2026-10-12.md e docs/guia-do-operador.md.