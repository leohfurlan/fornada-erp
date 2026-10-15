# Padrão de erros de preenchimento

Implementação local em 15/10/2026, conforme especificação do proprietário.

Erros de preenchimento devem identificar o campo e, quando houver linhas repetidas, o item correspondente. O controle recebe borda vermelha, `aria-invalid` e uma mensagem em português associada por `aria-describedby`. O resumo informa os campos e permite focá-los. Seções recolhidas são abertas para revelar o campo. Editar um campo retira seu aviso sem apagar os erros dos demais campos. Novas tentativas reavaliam os dados e podem apresentar novamente um erro recusado pelo servidor.

Falhas operacionais sem campo responsável permanecem como aviso geral, sem atribuir erro a controles arbitrários. Dados digitados são preservados após uma recusa.

## Implementação

- `frontend/lib/validation.ts`: normalização das mensagens, caminhos e nomes dos campos.
- `frontend/lib/api.ts`: normalização global das respostas Axios, preservando `field_errors`.
- `frontend/lib/form.tsx`: integração com React Hook Form, tratamento de recusas e identificação dos controles de `Controller`.
- `frontend/components/shared/validation-feedback.tsx`: feedback limitado ao formulário/painel, mensagens junto dos controles, resumo, foco e abertura de seções. O adaptador limpa as associações que criou e preserva descrições anteriores dos campos.
- `frontend/app/globals.css`: aparência comum dos controles inválidos.
- `backend/core/validation.py`, `backend/domain/validation.py` e handlers em `backend/main.py`: localização e tradução de erros de schema; respostas não devolvem os valores enviados ou objetos internos das exceções.
- Erros de domínio vinculados a preenchimento podem informar `field`; validações entre campos preservam sua localização.

Aplicado aos formulários de compras e catálogo comercial, histórico de compras, estoque, unidades alternativas, estoque de produtos acabados, receitas e ficha técnica, pedidos e cliente inline, vendas, produção, agenda, configurações, login/cadastro, acesso WhatsApp e motivo do suporte administrativo.

Para novos formulários, usar `ValidatedForm` com os erros locais ou `ValidationScope` com o erro da operação. Controles devem ter `name` correspondente ao caminho do payload. Quando o nome da interface difere do contrato, usar `data-field` como alias. Listas usam índices, como `itens.0.produto_novo.marca`. `ProdutoCompraFields` aceita `fieldPrefix`. Regras de domínio precisam indicar o campo quando a causa for preenchimento.

## Validação realizada

- Suíte frontend: 121 testes passaram; teste adicional da transformação real Axios também passou (122 testes distintos).
- Suíte unitária backend: 277 testes passaram.
- TypeScript e build Docker Linux/amd64 aprovados.
- Ruff aprovado nos novos módulos, testes e schemas centrais alterados.
- Regressões cobrem campos aninhados, múltiplos erros, foco, seções recolhidas, preservação de descrições acessíveis, edição parcial, reenvio, validação nativa, controles decimais, horários, limites de quantidade e seleção de materiais.
- `git diff --check` aprovado. O lint frontend via `next lint` não foi executado com sucesso: o checkout solicita configuração inicial de ESLint.

Alterações simultâneas e preexistentes foram preservadas. Não houve commit, push, migração ou deploy desta atividade. Não foi realizado aceite visual em navegador/aparelho físico nesta etapa; a instância temporária preparada para essa conferência foi encerrada a pedido de conclusão.
