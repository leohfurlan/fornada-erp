# Markdown em receitas e fichas técnicas — 07/10/2026

## Comportamento entregue

Modo de preparo, descrição do produto, apresentação final, especificações e instruções de montagem aceitam Markdown. O editor oferece botões de negrito, itálico, título, lista e link, além das abas Editar e Prévia. A prévia não salva nem converte o texto: o conteúdo original permanece no formulário e no banco.

São exibidos títulos, listas, citações, links, código e tabelas. A leitura da receita mostra modo de preparo e descrição/apresentação final formatados. Na produção, a renderização usa exclusivamente a ficha congelada da ordem, preservando seu histórico. Instruções reutilizáveis de etapas também recebem a formatação na consulta.

Textos antigos continuam legíveis, incluindo quebras de linha. Os limites de tamanho existentes foram mantidos. A validação da ficha preserva indentação e espaços significativos, mas continua recusando descrição vazia e validando quantidades e vínculos.

Renderizador: [react-markdown](https://github.com/remarkjs/react-markdown), com [remark-gfm](https://github.com/remarkjs/remark-gfm) para tabelas e demais extensões GFM. HTML cru é ignorado; a transformação padrão de URLs foi mantida. Testes verificam que scripts, eventos HTML e links `javascript:` não são executáveis na renderização.

## Validação

- Frontend: 46 testes aprovados, incluindo prévia, seleção na barra de formatação, limite de tamanho, validação de campo obrigatório e envio do Markdown original da ficha.
- Backend: 11 testes aprovados para ficha e preservação de indentação/espaços; repetidos com as dependências exatas da imagem em produção.
- TypeScript e Ruff dos arquivos Python alterados: aprovados.
- Build Linux de produção: aprovado, com instalação pelo lockfile congelado.
- Site publicado: prévia inspecionada em desktop e viewport de 390 × 844, com títulos, negrito, itálico, lista numerada, citação e tabela. Alternância de volta à edição preservou exatamente o Markdown digitado. Nenhuma receita ou dado de cliente foi salvo na conferência visual.

## Publicação

Construção a partir dos fontes atuais da VPS, preservando OCR, administração, modal e ajustes publicados da ficha técnica. O backend final deriva da imagem administrativa que já estava em produção; não altera suas dependências. Os fontes de cada arquivo foram conferidos por SHA256 antes da aplicação, impedindo sobrescrita de mudanças concorrentes.

Pacote de imagens SHA256: `c5f86b0bffbe1e741ae3d1b8af2b2929625efd5247c50f6348b3a704f46f5c4f`.

Fontes anteriores: `/opt/fornada/backups/fornada-source-before-markdown-20261007T132029Z.tgz`. Imagens anteriores preservadas como `fornada-backend:before-markdown-20261007` e `fornada-frontend:before-markdown-20261007`.

Sem migração de banco. Sem commit ou push.

Após a recriação, backend, frontend e worker passaram na espera de saúde do Compose. HTTPS `/health` respondeu `{"status":"ok","version":"0.1.0"}` e `/receitas/nova` respondeu HTTP 200.

Imagens em execução:

- Backend e worker: `sha256:78f0389da11f9c387496eaf5a17833c14584ad9cea8d3d910b356e863a9db29e`.
- Frontend: `sha256:949e69a951b38320125ca36c09ee5715b4be693f7cff0994d308ff26baf6fe30`.

## Arquivos centrais

- `frontend/components/shared/markdown-content.tsx`: renderização compartilhada.
- `frontend/components/shared/markdown-field.tsx`: edição, formatação e prévia.
- `frontend/components/shared/form-receita.tsx`: modo de preparo.
- `frontend/app/(dashboard)/receitas/[id]/ficha-tecnica/page.tsx`: textos da ficha.
- `frontend/app/(dashboard)/receitas/[id]/page.tsx`: leitura da receita/produto.
- `frontend/app/(dashboard)/producao/[id]/page.tsx`: ficha congelada.
- `backend/domain/receitas/ficha_tecnica.py`: preservação do Markdown na validação.
