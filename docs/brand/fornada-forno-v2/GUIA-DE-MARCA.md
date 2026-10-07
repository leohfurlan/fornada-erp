# Fornada — identidade oficial Forno aberto, rosa e marrom

Versão 2.0, aprovada em 07/10/2026 pelo usuário e pela principal cliente/sócia: rosa, marrom claro e contorno definido. Esta é a identidade oficial aplicada ao frontend. A forma original do forno e o desenho do nome foram preservados.

| Papel | Cor |
| --- | --- |
| Rosa suave do símbolo e do ícone | `#E7A0B3` |
| Marrom claro de apoio | `#D8BDA6` |
| Contorno do logo e nome | `#8E6D5A` |
| Marrom dos textos principais | `#694B3D` |
| Fundo rosa muito claro | `#FFF7FA` |
| Rosa dos botões e links | `#A34568` |
| Contorno dos campos e cartões | `#AD8870` |

O rosa suave serve à marca e às superfícies. Botões usam rosa mais fechado para manter contraste de 5,82:1 com texto branco. Textos auxiliares usam marrom `#84624F`. As bordas dos campos têm contraste de aproximadamente 3,21:1 sobre branco.

## Assinaturas e contornos

- Logo principal: forno rosa, contorno marrom e nome marrom. Utilize os SVGs prontos; não adicione outra borda pelo CSS.
- Monocromia: variantes `ink` e `white`, com preenchimento e contorno da mesma cor.
- Favicon: contorno reforçado, específico para leitura em 16 e 32 px.
- Aplicativo: fundo rosa, símbolo branco com contorno marrom. A versão maskable mantém símbolo e contorno dentro da área segura central.
- Logo horizontal a partir de 160 px de largura; símbolo isolado a partir de 24 px. Em 16 px, use o favicon específico.

O nome está convertido em curvas. A fonte Inter do sistema continua sendo a fonte de interface.

## Arquivos

- `svg/`: símbolos e logos horizontais/verticais.
- `png/`: exports com transparência.
- `favicon/`: SVG, ICO e PNGs de 16/32/48/64 px.
- `app/`: ícones 192/512/1024 px, Apple Touch Icon 180 px e foreground Android.
- `prancha.png`: apresentação da paleta e dos usos.
- `source/build-kit.cjs`: geração reprodutível a partir da geometria da versão 1.
- `source/validate-kit.cjs` e `validacao.json`: checagens de dimensões, vetores, cópias e área segura.

O frontend usa cópias em `frontend/public/brand/forno-v2`. A versão 1 está preservada como histórico. A aplicação e as prévias estão registradas em [IMPLEMENTACAO.md](../aplicacao-forno-v2/IMPLEMENTACAO.md).
