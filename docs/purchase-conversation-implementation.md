# Integração local da revisão conversacional

Data: 2026-10-12. Implementação incorporada ao checkout principal de Fornada,
a partir dos seis arquivos do worktree fornecido pelo usuário. Nenhum commit,
push, deploy ou banco de produção foi utilizado nesta entrega.

## Arquivos desta entrega

- backend/domain/compras/conversation.py: rascunho parcial, agrupamento inicial
  e após patch, referências estáveis, atribuições absolutas, seleção de catálogo,
  normalização decimal e auditoria de remoção/absorção de grupos.
- backend/api/routers/central.py: endpoint read/patch/lookup, validação estrita,
  persistência atômica, invalidação de aprovação, pendências, sincronização manual
  e preservação do resolve de receitas existente.
- backend/infrastructure/database/central_models.py: coluna dialogo nullable.
- backend/alembic/versions/b208d193ca01_purchase_dialogue.py: migração original.
- backend/alembic/versions/c409e872a103_merge_dialogue_recipes.py: merge sem DDL.
- backend/tests/unit/test_purchase_conversation.py e
  backend/tests/integration/test_purchase_conversation.py: regressões locais.
- docs/purchase-conversation-contract.md e este relatório.

Autenticação, iFood, receitas, custos/unidades, frontend e arquivos de outras
features não foram substituídos. O checkout recebeu alterações concorrentes de
outras sessões, incluindo evolução da migração PWA e commits de receitas;
o grafo e os testes foram novamente conferidos sobre esse estado.

## Correções da implementação recebida

Tipos de cada operação/campo são conferidos antes da aplicação; extras são
rejeitados. Material selecionado limpa produto anterior; produto selecionado
determina material/revisão/unidade canônicos. Alterar metadados de produto
existente prepara proposta nova preservando seus demais dados, sem editar catálogo.
Fornecedor existente/proposto são exclusivos. Contexto fiscal e fornecedor
reconhecido são preservados no seed; unidade sugerida pelo OCR não transforma l em kg.

Agrupamento compara identidades normalizadas e preços decimais equivalentes,
preserva diferenças de marca/embalagem/unidade/preço e usa a mesma regra monetária
HALF_UP do domínio. Quantidade, desconto total e total do grupo são somados.
Linhas inconsistentes, inclusive por um centavo, não contaminam grupos válidos.
Após edição equivalente há novo agrupamento com auditoria das referências absorvidas.

Patch incompleto permanece salvo com pendências e sem hash aprovável; limpa também
a revisão comercial anterior. Review manual sincroniza o diálogo sem atribuir
referências antigas a substituições ambíguas. Edição vencida não estende prazo;
renovação explícita válida mantém 24 horas e exige novo resumo/aprovação. Compras
encerradas/em execução permitem consulta, mas rejeitam patch e não ficam prontas
para nova revisão. Reconcile e decisão/execução existentes continuam separados.

## Evidência local

PostgreSQL 16 em container dedicado fornada-dialogue-qa-20261012, somente
127.0.0.1:55448, credenciais sintéticas e banco fornada_central_test_dialogue_final.
Não foram usados os bancos de desenvolvimento nem de produção. Movimentos nos
testes de execução são sintéticos e ficam exclusivamente nesse banco descartável.

- `python -m pytest tests -q --tb=short`: **439 passed, 4 skipped**.
- Após o último ajuste para consultar compras encerradas: **69 passed** nos
  testes unitários do diálogo e integrações conversation/central/guards/review_errors.
- Upgrade desde banco vazio, downgrade até a85c10b7d302 e upgrade novamente: passaram.
- `alembic heads` e `alembic current`: **c409e872a103**, única ponta.
- Ruff check e format --check: passaram nos sete arquivos Python da entrega.
- `git diff --check`: passou; checkout geral contém avisos LF/CRLF de outras features.

Na primeira suíte completa, dois testes PWA falharam porque o banco havia sido
criado enquanto a migração concorrente ainda era vazia. A migração foi completada
pela outra sessão; um banco novo com o grafo atual eliminou as falhas. Não houve
correção na feature PWA por esta entrega nem alteração de teste para ocultar falha.

Regressões novas cobrem incompletude, agrupamento consistente, catálogo autorizado,
marcas/embalagens/preços/unidades distintos, desconto total, vírgula decimal,
atomicidade, repetição/divergência de mensagem, versão obsoleta, lookup atual,
invalidação de aprovação, edição vencida/renovação explícita, conversão l→kg negada,
revisão manual, consulta encerrada, bloqueio após execução iniciada e acesso revogado.

## Limites e próximas validações

Contrato completo em purchase-conversation-contract.md. Permanecem: homologação
coordenada com Talk2Me/Google/Evolution reais e ativação/publicação autorizadas;
OCR sem itens exige fluxo manual (não há add_item); catálogo público de 200
produtos/fornecedores exige intervenção quando truncated; até 200 mensagens de
patch por proposta. Os códigos estruturados draft_* de conflitos propostos no
Talk2Me ainda não são envelope HTTP do provider: conflitos usam 409 e mensagem
segura, e o consumer deve recarregar/reconciliar. SIM e prova contextual de remoção
continuam responsabilidade do Talk2Me, conforme contrato aprovado.

Os quatro testes ignorados são de OTP WhatsApp e exigem TEST_REDIS_URL isolada,
não configurada nesta validação; não constituem evidência de homologação externa.
Nenhuma interpretação de linguagem natural ou
transporte WhatsApp foi implementado no Fornada.
