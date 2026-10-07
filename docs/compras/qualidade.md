# Gates e evidências — CMP-01 a CMP-03

Revisão técnica r1, 07/10/2026. Fonte: [PRD Compras r2](../compras-produtos-aprovados.md). Este arquivo é compartilhado pelas três specs.

## Política e comandos

| Gate | Fonte | Comando e diretório | Pré-requisitos/escopo | Política | Evidência desta entrega |
|---|---|---|---|---|---|
| Backend | CLAUDE.md §10; backend/pyproject.toml | `python -m pytest --tb=short -q`, backend | Ambiente Python do projeto; PostgreSQL de teste com migrations; TEST_DATABASE_URL explícito | Obrigatório antes de commit | 267 passaram, 4 OTP/Redis pulados; cobertura Compras 92% |
| Frontend | CLAUDE.md §10; frontend/package.json | `pnpm test --run`, frontend | Dependências pelo pnpm-lock.yaml; Vitest/jsdom | Obrigatório antes de commit | Passou |
| Tipos | CLAUDE.md §10; frontend/tsconfig.json | `pnpm exec tsc --noEmit`, frontend | Dependências frontend | Obrigatório antes de commit | Passou |
| Ruff direcionado | backend/pyproject.toml | `python -m ruff check api/routers/compras_comerciais.py domain/compras infrastructure/database/compras_models.py domain/whatsapp/service.py infrastructure/ocr/gemma_adapter.py tests/integration/test_compras_comerciais.py tests/unit/test_compras_comerciais.py tests/unit/test_whatsapp_compras.py`, backend | Router/modelos/serviços e testes novos; consumidor WhatsApp e OCR alterados | Gate executado na implementação | Passou no escopo de compras/WhatsApp/OCR/novos modelos e testes |
| Migration | Alembic/env.py; tests/conftest.py | `python -m alembic heads` e `python -m alembic upgrade head`, backend | DATABASE_URL para banco temporário explicitamente validado; nunca o banco de produção | Gate complementar executado | Passou |
| Build | frontend/package.json | `pnpm build`, frontend | Dependências e configuração local sem serviços externos obrigatórios | Gate complementar executado | Passou |
| Revisão do diff | Convenção local | `git diff --check`, raiz | Mudanças locais | Verificação dos arquivos implementados | Passou; novos arquivos e links documentais também verificados |
| UI | CLAUDE.md §14 | Inspeção dos fluxos em desktop e viewport 390 px | Aplicação e conta de teste local | Requisito existente de mobile | Cadastro, compra, OCR/reconhecimento e histórico verificados em 1280×900 e 390×844 |

Os resultados desta implementação são locais e estão detalhados no [relatório](implementacao-2026-10-07.md). Nenhum teste usa ou deve usar a URL de produção ou o fallback implícito do ambiente. `tests/conftest.py` usa rollback mas rotas podem fazer commit; o banco inteiro precisa ser descartável. Preparar um banco temporário com Alembic e declarar DATABASE_URL/TEST_DATABASE_URL nesse processo antes de executar.

Frontend possui `pnpm lint` apontando para `next lint` e não possui configuração global de ESLint: esse comando abriu o assistente de configuração. A implementação usou uma configuração temporária com `next/core-web-vitals` e lint direcionado, que passou, sem iniciar configuração global. Não foram encontrados workflows .github nesta inspeção. Não há validador de arquitetura identificado.

Verificações documentais anteriores à implementação, em 07/10/2026: 13 documentos da rotina, nenhum link local quebrado, três artefatos presentes por feature CMP-01/CMP-02/CMP-03 e ausência de whitespace final/marcadores de conflito nos arquivos novos. Essas verificações não demonstram implementação nem testes funcionais.

## Matriz de aceitação compartilhada

| Caso | Resultado exigido | Ponto de verificação |
|---|---|---|
| QA-01 primeira compra do exemplo | Sem ingrediente duplicado; 1 barra = 1,01 kg; total 35,99; fabricante ausente preservado | UI → HTTP → PostgreSQL real; snapshot e estoque |
| QA-02 segunda leitura | Mesmo produto/material sugeridos; nova compra somente após confirmação | FakeOCR com itens contratuais + catálogo e compra reais |
| QA-03 duas barras | 2,02 kg; total 71,98; preço por kg igual ao de uma barra | Prévia e confirmação v2, saldo e histórico |
| QA-04 outra embalagem | 1,05 kg não usa fator 1,01; exige outra variante/embalagem | CRUD, OCR e confirmação |
| QA-05 mesma marca, outra variante | Ao leite não vira branco; ambiguidade não escolhe por ordem de lista | Matching e resposta HTTP |
| QA-06 aprovação/exceção/cancelamento | Aprovar grava só após confirmar; exceção não aprova; cancelar/ignorar não aprende | UI e consultas posteriores |
| QA-07 unidade e valor inválidos | 422; nenhum estoque/histórico/aprovação parcial | HTTP e banco real |
| QA-08 retry/concorrência | Mesma chave = uma compra; chave com corpo diferente = 409; duas compras válidas somam saldo sem perda | Duas conexões/transações reais; não a fixture de conexão única |
| QA-09 erro no último item | Nenhum item anterior persistido; retry válido funciona | HTTP e banco real |
| QA-10 identidade/tenant | IDs de outra conta retornam 404; lista/histórico/match não vazam | Duas contas; controle positivo na conta dona |
| QA-11 revisão/arquivo histórico | Edição concorrente retorna 409; editar/inativar produto não altera compra antiga | HTTP, snapshots e nova leitura |
| QA-12 campos ausentes | Data/loja/marca desconhecidas não são inventadas; entrada só com conversão confirmada | OCR determinístico, UI e histórico |
| QA-13 legado e WhatsApp | Chamadas existentes continuam válidas; histórico básico marcado; reentrega não duplica efeitos | Testes atuais de compras e WhatsApp + cenário integrado |
| QA-14 duplicidade fiscal | Identidade confiável alerta; coincidência de valor/data não bloqueia compra distinta | Confirmar v2 e UI |
| QA-15 precisão | Total original exato; quantidade compatível com escala de estoque; custo médio segue arredondamento existente | Decimal e PostgreSQL, não igualdade de floats |

Fixtures de OCR vêm de um ResultadoOCR/ItemOCR sintético compatível com o adapter atual, com os campos opcionais implementados. O cupom apresentado é referência de aceitação, não prova de variante. Mock não substitui teste de integração de catálogo, confirmação e histórico.

Reusar `test_compras_matching.py`, `test_compras_fluxo.py`, `test_unidades_ingrediente.py`, `test_whatsapp_compras.py` e `test_whatsapp_fluxo.py`. Acrescentar cenários pelos comportamentos públicos; não testar apenas estruturas internas. Cobertura mínima documentada no CLAUDE.md continua aplicável. As suítes foram reavaliadas na execução completa; veja os resultados no relatório de implementação.

## Migração e entrega operacional

- Gerar novas revisions via Alembic, revisar o diff para descartar mudanças alheias e assegurar uma única head integrada às migrations locais existentes.
- Aplicar somente em banco temporário na implementação. Comparar saldos/custos anteriores e posteriores ao upgrade; cadastro novo não deve alterá-los.
- Não fazer backfill inferido. Entrada antiga continua no histórico de movimentos com atributos comerciais desconhecidos.
- Downgrade destrutivo não é recuperação de produção: para incidentes, desativar UI nova e manter schema/dados; recuperação de backup exige procedimento separado e autorização.
- Antes de qualquer publicação, preparar evidência dos gates e plano de migration/backup. Nenhum comando de produção está autorizado por estes artefatos.

## Consolidação em 07/10/2026

Seis fatias implementadas e validadas localmente. Frontend: 53 testes passaram, tipos e build passaram. Backend: 267 testes passaram, quatro testes OTP sem Redis isolado foram pulados; domínio Compras com cobertura de 92% e serviços novos acima de 80%. Upgrade aditivo validado em dois bancos descartáveis, preservando saldo/custo e rascunho anterior. Nenhuma chamada ao Google/Evolution real, commit, push ou deploy. [Relatório, cenários, arquivos e capturas](implementacao-2026-10-07.md).
