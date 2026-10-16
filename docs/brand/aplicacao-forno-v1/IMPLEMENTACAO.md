# Aplicação da identidade Forno aberto

Data: 07/10/2026. Direção aprovada pelo usuário: **Forno aberto**, kit `fornada-forno-v1`.

## Implementação

- Logo vetorial horizontal no cabeçalho do sistema, com link para o início, nome acessível e proporção preservada.
- Layout compartilhado de autenticação com logo, assinatura verbal, fundo creme e cartão branco. Abrange login, cadastro e acesso por WhatsApp, inclusive as alternativas selecionadas pela configuração de disponibilidade.
- Paleta global com terracota, cacau e creme; aplicada aos botões, links, foco, navegação ativa, neutros e destaques do painel.
- Favicons SVG e ICO, Apple Touch Icon de 180 px, ícones de 192/512 px e versão maskable de 512 px.
- Manifest em `/manifest.webmanifest` com nome, idioma, escopo, cores e ícones do Fornada. Metadados Apple e cor do navegador no layout raiz.

## Fontes de verdade

O kit em `docs/brand/fornada-forno-v1` conserva os SVGs mestres. Os 12 arquivos publicados pelo frontend em `frontend/public/brand/forno-v1` são cópias idênticas, verificadas por SHA-256. O caminho inclui a versão da identidade para permitir evoluções sem reutilizar URLs de outra versão.

`frontend/components/shared/brand-logo.tsx` centraliza a assinatura. `frontend/app/(auth)/layout.tsx` centraliza a apresentação de acesso. `frontend/app/globals.css` e `frontend/tailwind.config.ts` centralizam os tokens; `frontend/app/layout.tsx` e `frontend/app/manifest.ts` declaram os metadados e ícones.

## Cores

| Uso | Cor |
| --- | --- |
| Símbolo, ícone e cor do navegador | `#D95D39` |
| Nome e textos principais | `#2E2824` |
| Superfície de autenticação e destaques suaves | `#FFF6EE` |
| Botões e links | `#B5472B` |
| Cartões e texto dos botões | `#FFFFFF` |

O tom mais escuro dos controles mantém contraste de **5,38:1** com texto branco, medido no navegador. Os logos conservam o terracota aprovado. A fonte Inter das telas foi mantida; o nome da marca usa o desenho vetorial do kit. Cores semânticas de erro, alerta e categorias continuam disponíveis.

## Validação

- Suíte existente do frontend: **58 testes passaram em 13 arquivos**.
- TypeScript: `pnpm exec tsc --noEmit` passou no frontend original; checagem da cópia isolada também passou.
- Build de produção: compilação, lint e tipos validados.
- Navegador: login por e-mail e WhatsApp, cadastro e painel; desktop de 1440 px e celular de 390 px. Logo carregado, proporções preservadas e nenhuma rolagem horizontal nas telas verificadas.
- Manifest e todos os seis ícones declarados nos metadados/manifest responderam HTTP 200. PNGs confirmados em 180×180, 192×192 e 512×512.
- Saída da sessão fictícia no painel retornou à tela de login com a nova marca.
- Assets do frontend idênticos ao kit aprovado: 12 de 12.

As telas internas foram avaliadas com dados e sessão fictícios locais, sem operações em contas reais. Um servidor de desenvolvimento compartilhado reconstruía `.next`; a revisão final usou uma cópia isolada em `output/playwright/brand/frontend`.

## Evidências visuais

- [Login desktop](login-desktop.png)
- [Login no celular](login-mobile.png)
- [Cadastro no celular](cadastro-mobile.png)
- [Acesso por WhatsApp no celular](whatsapp-mobile.png)
- [Painel no celular](dashboard-mobile.png)
- [Painel desktop](dashboard-desktop.png)

## Limites e entrega

Implementação local, sem commit, push ou deploy. As alterações de outros trabalhos foram preservadas. A checagem mobile foi feita em navegador com viewport de 390 px; instalação física em Android/iOS não foi realizada. Os ícones e o manifest preparam a identidade do aplicativo web adicionado à tela inicial; este trabalho não adiciona funcionamento offline ou um aplicativo nativo separado.
