# Correção da origem do checklist — 19/10/2026

O checklist deve representar os registros de `ReceitaEtapa`, e não linhas do campo `modo_preparo`. Esta correção substitui o comportamento documentado na entrega inicial de 18/10.

- A seção **Etapas** mostra somente etapas cadastradas, com nome, duração e ordem. O identificador de cada card inclui o UUID do registro real.
- **Modo de preparo** mantém o conteúdo integral em um único bloco somente para leitura. Não há conclusão, navegação por supostas etapas de texto nem contagem desse conteúdo no progresso.
- A Alexa continua lendo o modo de preparo, com divisão técnica em partes de fala quando necessário. Ela não anuncia esse texto como uma etapa selecionada do checklist.
- Montagem e ingredientes permanecem consultáveis, sem integrarem o checklist de ETAPAS.
- Receitas sem etapas cadastradas têm zero itens de checklist, mesmo que o texto de preparo contenha uma lista numerada.
- O servidor rejeita tentativas de concluir texto ou montagem.

## Arquitetura e persistência

O snapshot já consulta `Receita.etapas` no mesmo SELECT isolado por tenant. A opção `include_steps=True`, usada somente pelo Modo Cozinha, expõe esses registros estruturados à projeção; a resposta e a versão padrão da integração com a Central permanecem inalteradas.

Os blocos da seção `steps` são explicitamente marcáveis (`checkable: true`). Conclusões usam IDs `step-<UUID>`, sem associação por posição. O estado continua no JSONB da estação existente, com lease, revisão e idempotência, sem migration ou dependência nova.

A versão da projeção inclui agora os registros reais de etapas. Sessões da implementação anterior serão invalidadas na próxima sincronização, exigindo reabrir a receita; marcações feitas sobre trechos de texto não serão convertidas em marcações de etapas reais.

## Regressões

Os testes da projeção reproduziram duas falhas antes da correção: ausência dos registros cadastrados no checklist e aceitação indevida de conclusão do texto. Ambos passaram após a alteração.

Novas verificações cobrem: origem em ETAPAS e respectivos UUIDs, nome/duração/ordem, modo de preparo numerado preservado como um texto, leitura pela Alexa sem anunciar posição de etapa, receita sem etapas, exclusão de montagem do progresso, texto sem botão ou eventos de conclusão e rejeição HTTP de marcação de texto. A integração de persistência agora cria registros reais de `ReceitaEtapa` no PostgreSQL de testes.

Validação no checkout local: frontend completo com 158 testes passando e TypeScript aprovado; backend com 512 passando, 4 ignorados e as mesmas duas falhas preexistentes de formatação de quantidades na Central, já reproduzidas antes desta correção. Ruff dos módulos e testes da correção aprovado.

Os arquivos alterados pertencem à projeção/snapshot de cozinha, schema de seção, rótulos de fala da Alexa, tela e componente de checklist e seus testes. As alterações paralelas de edição de receitas/rascunhos e compras são preservadas e não fazem parte desta correção.
