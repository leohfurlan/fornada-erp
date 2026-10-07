# CMP-03 — Compra e histórico de preços

Spec r2, 07/10/2026. Fonte [PRD Compras r2](../../compras-produtos-aprovados.md); [contrato](contract.md); [plano](plan.md). Produto aprovado; implementação local concluída.

## Evidência anterior à implementação e escopo

ComprasService confirma itens via EstoqueService e a rota faz commit. Hoje o estabelecimento recebido é descartado; não há compra comercial persistida. Estoque registra movimentação e custo médio, com Decimal e arredondamento a quatro casas. Converter_para_principal já resolve equivalência métrica/alternativas do ingrediente. Repository possui busca for_update, mas registrar_entrada atual não solicita esse lock.

Esta feature entrega compra manual ou revisada, prévia de conversão, confirmação única e histórico por material. Não depende de OCR; consome IDs do catálogo CMP-01. Não cria relatório CMP-04.

## Comportamento verificável

- C3-B1: conservar informação original e fotografia comercial no instante da confirmação. Data da compra pode ser null; data de registro é distinta e gerada no servidor.
- C3-B2: quantidade fiscal de embalagem é multiplicada pelo conteúdo daquele produto e convertida para unidade principal; custo usa total efetivo dividido pela quantidade convertida. Quantidade decimal não representável no estoque exige correção. Não trocar o nome da unidade sem converter os números.
- C3-B3: compra, seus itens, movimentos, criação/aprovação solicitada e vínculo aprendido são atômicos. Falha no último item deixa zero efeitos da tentativa.
- C3-B4: reenvio de confirmação v2 com a mesma chave e conteúdo devolve o mesmo resultado sem nova entrada. Mesma chave com conteúdo diferente devolve 409. Compras distintas concorrentes do mesmo material preservam soma e custo médio.
- C3-B5: produto/material/fornecedor próprios e revisões atuais são obrigatórios. Compra excepcional revisada não aprova permanentemente produto ou fornecedor.
- C3-B6: identidade fiscal confiável repetida pede revisão de duplicidade; coincidência apenas de loja/data/valor não bloqueia compra real distinta. Chave de retry não se confunde com identidade da nota.
- C3-B7: histórico apresenta data, loja, marca, variante, embalagem, quantidade e preços originais/normalizados, com desconhecidos explícitos. Editar cadastros não modifica snapshots.
- C3-B8: chamadas v1 continuam aceitas; consumidor WhatsApp utiliza o mesmo núcleo, conserva dados disponíveis e rejeita conversão não confirmada. Não reconstruir compras anteriores com informações inventadas.
- C3-B9: leitura/prévia/cancelamento não geram entrada; confirmação sem produto comercial pode registrar compra de quantidade já medida, com dados incompletos e exceção revisada explícita.

## Casos de borda e verificação

| Caso | Estado/entrada | Resultado observável | Seam/trace |
|---|---|---|---|
| C3-E1 | 1 UN, conteúdo 1,01 kg, total 35,99, estoque kg | Entrada 1,01 kg; preço 35,63366337/kg no histórico | C3-B1/B2; QA-01/15 |
| C3-E2 | 2 UN, mesmo produto, total 71,98; estoque g | Entrada 2.020 g; total original preservado | C3-B2; QA-03 |
| C3-E3 | Pacote de 1,05 kg com produto de 1,01 kg | 422 até escolher/criar embalagem correta | C3-B2/B5; QA-04 |
| C3-E4 | Zero/negativo/NaN/Infinity ou overflow | 422; nenhuma aprovação/compra/movimento | C3-B2/B3; QA-07 |
| C3-E5 | Preço unitário vezes quantidade difere do total sem desconto informado | 422 para corrigir; desconto explícito consistente é aceito | C3-B2; QA-07/15 |
| C3-E6 | Data/loja/fabricante desconhecidos | null; não usar data do scan; sem aprendizado por loja inexistente | C3-B1/B9; QA-12 |
| C3-E7 | Dois itens, último com ID alheio/unidade inválida | 404/422; rollback integral | C3-B3/B5; QA-09/10 |
| C3-E8 | Dois requests simultâneos de mesma chave | Mesmo resultado; uma compra e um movimento por item | C3-B4; QA-08 |
| C3-E9 | Mesma chave, preço alterado | 409; compra anterior inalterada | C3-B4; QA-08 |
| C3-E10 | Duas chaves válidas, mesmo ingrediente | Ambas persistem sem atualização perdida | C3-B4; QA-08 |
| C3-E11 | Produto editado/inativado entre prévia e salvar | 409 revisão/404 inativo; nenhum efeito; UI conserva revisão para corrigir | C3-B5; QA-11 |
| C3-E12 | Resposta HTTP perdida após commit | Retry com mesma chave recupera resposta original | C3-B4; QA-08 |
| C3-E13 | Nota conhecida repetida versus duas notas de mesma loja/data/valor | Primeiro caso alerta; segundo aceita como distintas sem identidade igual | C3-B6; QA-14 |
| C3-E14 | Compra excepcional/cancelada/item ignorado | Exceção não aprova; cancelamento/ignorado não cria movimento/vínculo | C3-B3/B5/B9; QA-06 |
| C3-E15 | Legado sem dados comerciais; WhatsApp reentrega | Histórico básico incompleto; replay não duplica efeitos | C3-B8; QA-13 |
| C3-E16 | Editar cadastro após compra | Histórico mostra dados e fator originais | C3-B7; QA-11 |
| C3-E17 | ml para g sem fator confirmado | 422 sem inferência de densidade | C3-B2; QA-07 |
| C3-E18 | Chave sem autenticação ou pertencente a outra conta | Auth/tenant antes do replay; nenhum dado exposto | C3-B4/B5; QA-10 |

Todos os nove critérios CMP-03 do PRD estão refinados por C3-B1 a B9. O histórico não oferece edição/reordenação de eventos; operações fora de ordem relevantes são revisão comercial e retry acima. Estorno comercial completo é incremento futuro, não endpoint fictício.

## Decisões técnicas e atomicidade

Owner da transação é o serviço de aplicação de compras, com sessão fornecida pela rota/worker; commits continuam no limite HTTP/WhatsApp. Tabelas novas compras e compra_itens mais vínculos a movimentos, conforme contrato. Snapshot JSONB inclui atributos e fator usados; totais/quantidades consultáveis em Decimal. Todas as tabelas de negócio têm tenant/UUID/timestamps/soft delete e índices de filtros; nenhuma exclusão em cascata.

A confirmação trava o tenant como o fluxo de composição existente, resolve a chave idempotente e valida referências/revisões antes de gravar. Leituras/escritas de saldo devem usar lock de linha e dados atualizados; ordem de locks estável. O checkpoint deve verificar entradas diretas e operações concorrentes de produção, para não prometer serialização quando outro escritor ignorar o protocolo. Ajuste é limitado à fronteira de estoque afetada.

Alternativa de idempotência só no frontend foi rejeitada: clique duplo e timeout exigem unicidade persistida por tenant/chave. Não criar sistema genérico de eventos/ledger; compra confirmada e resposta persistida são suficientes. Replays confirmados são resolvidos antes de revalidar produto atual, pois a compra já salva deve continuar recuperável mesmo após inativação do catálogo.

Para material novo, criar saldo zero e registrar entrada de compra uma vez; não usar estoque inicial e depois dar entrada outra vez. Custo médio segue função existente com ROUND_HALF_UP a 0,0001; preço histórico normalizado usa oito casas. Total efetivo não é reconstruído a partir do custo médio arredondado.

```mermaid
sequenceDiagram
  actor U as Confeiteira
  participant UI as Revisao ou entrada manual
  participant C as Compras
  participant P as Catalogo CMP-01
  participant E as Estoque
  participant DB as PostgreSQL
  U->>UI: Conferir e salvar
  UI->>C: Confirmar v2 com chave persistente
  C->>DB: Lock e consultar resultado da chave
  alt replay identico
    C-->>UI: Resultado ja salvo
  else nova compra
    C->>P: Validar IDs, revisoes e aprovacoes
    C->>E: Calcular conversao e custo
    alt qualquer erro
      C->>DB: Rollback de todos os efeitos
      C-->>UI: Erro em portugues; manter revisao
    else valido
      C->>DB: Compra, snapshots, aprovacoes e movimentos
      C->>DB: Commit no limite da operacao
      C-->>UI: Compra registrada e historico
    end
  end
```

## Integração e gates

Prévia usa catálogo/estoque reais; resposta não aceita quantidade normalizada arbitrária do cliente. Contratos v2 são [autoritativos](contract.md) e chamados por CMP-02. Núcleo legado/WhatsApp deve gerar histórico básico sem inventar original da nota se já recebeu valores normalizados. Teste de WhatsApp inclui rascunho com metadados conhecidos e chave estável do rascunho.

Aplicar [matriz QA e gates](../qualidade.md). Testes concorrentes exigem conexões reais separadas; mocks não provam atomicidade. Migration aditiva preserva estoque/custo; sem backfill inferido. Spec preparada para tickets; compra comercial e protocolo novo ainda não implementados.

## Evidência de implementação

Implementação local integrada em 07/10/2026. [Relatório, arquivos e validações](../implementacao-2026-10-07.md). Não houve commit, publicação, migração de produção ou deploy.
