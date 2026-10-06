# Catálogo de ingredientes e etapas

O importador `backend/scripts/importar_catalogo_receitas.py` extrai o catálogo do arquivo transcrito, sem criar receitas ou presumir rendimentos. A aplicação exige email e UUID do tenant, confirma a conta ativa e usa uma transação. Sem `--aplicar`, simula e desfaz todas as alterações. Reexecuções preservam cadastros existentes.

Ingredientes começam com saldo e custo zero, mínimo 1 na unidade principal. Sólidos usam g, líquidos mL e ovos unidade. Desmoldante: g, com lata de 120 g informada pelo usuário. Plástico filme: unidade. Alternativas de ingredientes permanecem separadas.

Conversões são específicas de cada ingrediente, calculadas com Decimal. As equivalências explícitas do arquivo têm identificação própria; medidas culinárias pesquisadas são aproximações editáveis, com fonte no cadastro. Não existe conversão universal de volume para massa.

Referências: [Receitas Nestlé](https://www.receitasnestle.com.br/artigos/medidas-para-os-ingredientes-na-cozinha) e [King Arthur Baking](https://www.kingarthurbaking.com/learn/ingredient-weight-chart). Validar os medidores usados na cozinha. Pitadas e colheres sem tipo permanecem sem fator; a farinha do pão caseiro apresenta equivalências conflitantes e não recebe um fator universal de copo americano.

Etapas preservam texto e origem. Faixas usam o máximo para cálculo e mantêm a faixa no preparo. Trabalho ativo é direto; descanso, fermentação e forno são indiretos. Tempos ausentes ficam pendentes, sem estimativa. Ao selecionar uma etapa em uma receita, sua instrução é adicionada ao modo de preparo; a receita exige duração positiva para calcular custos.

```bash
python -m scripts.importar_catalogo_receitas --arquivo receitas_transcritas.json --plano
python -m scripts.importar_catalogo_receitas --arquivo receitas_transcritas.json --email EMAIL --tenant-id UUID
# Após conferir a simulação:
python -m scripts.importar_catalogo_receitas --arquivo receitas_transcritas.json --email EMAIL --tenant-id UUID --aplicar
```

## Validação e aplicação em 6 de outubro de 2026

- 38 materiais criados na conta piloto especificada; consulta posterior confirmou saldo e custo zero e mínimo 1 em todos.
- 60 etapas importadas, com 41 durações pendentes. Nenhuma receita criada pelo importador.
- Segunda simulação: zero materiais novos e zero etapas novas.
- Migration aplicada: `2798d1537c70`. Backup restaurado em banco temporário antes das migrações: `/opt/fornada/backups/fornada-20261006T173857Z-79112.dump`.
- HTTPS externo: health e login HTTP 200. Formulário de unidades alternativas conferido em viewport de 390 px, com dados simulados somente na instância local de QA.
- 216 testes da suíte backend e três novos testes focados aprovados; 34 testes frontend, TypeScript e build das imagens aprovados. Oito cenários isolados do deploy aprovados.

O deploy usou `--skip-pull` porque o PR #3 ainda não estava integrado a main. As imagens contêm o novo modelo e as telas; o importador foi executado como utilitário separado, incluindo as duas equivalências explícitas de embalagem de fermento adicionadas na conferência final. Para próximos deploys, integrar o PR e fornecer imagens correspondentes aos fontes atuais. O script bloqueia pull quando há modificações locais rastreadas.
