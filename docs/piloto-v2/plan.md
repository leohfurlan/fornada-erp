# Plano de implementação

## Situação após a continuação de 06/10/2026

- T01: implementação e inspeção visual desktop/390 px concluídas. Corrigida a espera da sessão persistida para acesso direto às páginas.
- T02: vínculos por ID, seleção no editor, validação de unidades/tenant/ciclos, proteção de remoção e classificação receita-base/produto implementados. Classificação derivada da composição ativa; não há nova tabela de produtos.
- T03: custo da composição e preço existente integrados, incluindo ingredientes, embalagem, preparo proporcional da base e trabalho local de montagem. Resumo consolidado por fornada disponível. Tempo exibido é o tempo local de montagem; bases já prontas carregam o custo de preparo.
- T04: usuário escolheu estoque de massas/recheios prontos. Reserva e consumo dessas bases implementados, sem expansão dos ingredientes na montagem. Cancelamento libera reservas. Ordens novas congelam instruções, revisão, rendimento, unidade e consumo ao criar. Ordens antigas planejadas congelam ao iniciar; ordens já em execução não são retroativamente reconstruídas.
- T05: desafio/código/prova, Redis compartilhado, transporte Evolution v2 e telas implementados. Envio real ainda depende de instância conectada e teste autorizado de entrega.
- T06: cadastro após posse do telefone (nome, loja, endereço e e-mail), login por código e vínculo de conta antiga autenticada implementados. Recuperação autônoma e troca de telefone permanecem pendentes; nenhuma associação automática por e-mail.

Flag `WHATSAPP_AUTH_ENABLED` permanece false por padrão. [Ativação e limites](evolution-login.md). Sem publicação na VPS nesta rodada. Itens abaixo preservam o planejamento original para rastreabilidade.

1. UX-01 + FT-01: primeira entrega local. Boas-vindas, retorno Início, nomenclatura, ficha editorial, API tenant-scoped, validação decimal, concorrência, migração e testes. Implementado; não publicado na VPS.
2. FT-02: separar receita-base e produto; selecionar componentes existentes por ID; cálculo por rendimento e unidade; validação de ciclos; migração compatível. Tela mantém camadas individuais e lista consolidada. Depende da entrega 1.
3. FT-03: integrar componentes ao custo/preço, testes com Sedução e bolo; confirmar política de perdas e embalagem. Depende da entrega 2.
4. FT-04: snapshot em produção, tutorial operacional e consumo de estoque. Definir com o usuário produção/estoque intermediário para evitar dupla baixa. Depende de 2/3.
5. AUTH-01/02: normalização internacional, desafio OTP seguro e adaptador Evolution configurado. Validar envio e indisponibilidade em ambiente de teste antes de ativação.
6. AUTH-03: onboarding com endereço/e-mail, migração de login atual, recuperação, primeira entrada. Depende de 5 e decisões de vinculação/recuperação.

Validação: pytest isolado em PostgreSQL; tsc/Vitest/build; UI desktop e 390 px; verificar camadas repetidas, faixa inválida, tenant diferente, revisão desatualizada; composição exige custo/rendimento/ciclos e baixa sem duplicação. Publicação/migração VPS fica fora desta execução.

## Tickets locais — rascunho para revisão

Tickets não publicados em tracker. Cada item é uma fatia demonstrável com backend/frontend/testes correspondentes:

- T01 (UX-01/FT-01): visualizar e salvar montagem por unidade, reordenar e preservar revisão; critérios na spec; implementação local concluída, validação visual pendente.
- T02 (FT-02): montar Sedução com receitas-base e embalagem selecionadas; isolar tenant e impedir ciclo; depende T01.
- T03 (FT-03): mostrar custo nominal do Sedução consolidando brigadeiro 60 g e morango 50 g; custo inclui copo/tampa/adesivo; depende T02.
- T04 (FT-04): executar produção com ficha congelada e consumo escolhido sem dupla baixa; depende T03 e decisão de estoque intermediário.
- T05 (AUTH-01/02): receber e verificar código via Evolution com expiração/tentativas/reenvio; depende instância de teste configurada.
- T06 (AUTH-03): concluir cadastro validado e acessar Início pelo guia; incluir vinculação/recuperação para usuários atuais; depende T05.
