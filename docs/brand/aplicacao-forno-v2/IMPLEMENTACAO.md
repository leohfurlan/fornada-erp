# Identidade oficial rosa e marrom no sistema

Data: 07/10/2026. A versão rosa e marrom foi aprovada pelo usuário após a preferência da esposa, principal cliente/sócia, e consolidada como identidade oficial do sistema. A aparência implementada foi mantida integralmente.

O Forno aberto ganhou preenchimento rosa suave e contorno marrom. A paleta do sistema usa rosa, marrom claro nas superfícies de apoio, texto marrom e bordas mais definidas nos campos e cartões. Logos, favicons, Apple Touch Icon, ícones maskable e cores do manifest foram atualizados juntos. O desenho original do forno e o nome em curvas foram preservados.

A versão 2 usa URLs `/brand/forno-v2/`, evitando reaproveitar URLs de ícones terracota em cache. O kit e as prévias da versão 1 foram preservados. A aplicação usa tokens em `frontend/app/globals.css` e `frontend/tailwind.config.ts`, logo compartilhado em `frontend/components/shared/brand-logo.tsx` e metadados em `frontend/app/layout.tsx` e `frontend/app/manifest.ts`.

## Validação

- 58 testes passaram em 13 arquivos do frontend.
- TypeScript passou; build de produção passou com lint e tipos, usando a cópia isolada para evitar interferência com o servidor de desenvolvimento compartilhado.
- 23 verificações do kit passaram: geometria preservada, vetores sem imagem/fontes embutidas, dimensões corretas, ICO com quatro tamanhos e símbolo com contorno dentro da área segura maskable.
- Botões com contraste medido no navegador de 5,82:1.
- Login e painel revisados em desktop de 1440 px e celular de 390 px, sem rolagem horizontal e com logo carregado.
- Assets do frontend conferidos contra os mestres da versão 2.
- Manifest e seis ícones declarados responderam HTTP 200, com cores e caminhos da versão 2; PNGs confirmados em 180/192/512 px. Nenhum erro de console no painel.

Os dados e a sessão do painel nas imagens são fictícios e locais. Alterações de outros trabalhos foram preservadas. Não houve commit, push ou deploy; instalação em aparelhos Android/iOS não foi realizada.

## Prévias

- [Identidade e paleta](../fornada-forno-v2/prancha.png)
- [Login desktop](login-desktop.png)
- [Login celular](login-mobile.png)
- [Painel desktop](dashboard-desktop.png)
- [Painel celular](dashboard-mobile.png)

Guia e arquivos mestres: [Forno aberto v2](../fornada-forno-v2/GUIA-DE-MARCA.md).
