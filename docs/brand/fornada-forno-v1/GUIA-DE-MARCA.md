# Fornada — Forno aberto

**Identidade visual · versão 1.0 · 07/10/2026**

A opção 02 foi escolhida pelo usuário, que anexou o símbolo como referência para a formalização. Este é o kit canônico dessa decisão.

## Símbolo

O arco representa o forno. A assadeira horizontal identifica a produção. O centro aberto mantém a leitura simples e acolhedora. O desenho conserva a silhueta escolhida, com curvas regularizadas, cor uniforme e bordas limpas.

Os dois elementos preservam sua posição relativa e o formato da referência. O vetor foi reconstruído a partir do anexo, com ajuste geométrico dos arcos e da cápsula central. A comparação de silhuetas atingiu **99,17% de interseção sobre união**, após desconsiderar ruídos de transparência do raster. Isso verifica a proximidade da forma; a cor e a regularidade das curvas foram consolidadas para a marca.

O nome aparece em **fornada**, em minúsculas, com Segoe UI Semibold e espaçamento ajustado. Nos SVGs entregues, as letras estão convertidas em curvas: os arquivos prontos mantêm a aparência sem depender da instalação de fontes. A interface do produto pode continuar usando Inter.

## Paleta

| Cor | Hexadecimal | Aplicação |
|---|---|---|
| Laranja forno | `#D95D39` | Símbolo principal e fundo do ícone do aplicativo |
| Cacau | `#2E2824` | Nome da marca, textos e fundos escuros |
| Creme | `#FFF6EE` | Fundos claros e apoio visual |
| Branco | `#FFFFFF` | Versões sobre fundo escuro e símbolo do aplicativo |

Em fundos claros, use o símbolo laranja com o nome em cacau. Em fundos escuros, use a assinatura branca. Sobre fotografias, coloque a marca em uma área lisa com contraste suficiente. A paleta da marca não altera automaticamente as cores funcionais de botões, erros ou avisos do sistema.

## Assinaturas

| Uso | Arquivo recomendado |
|---|---|
| Cabeçalho do site e tela de entrada | `svg/logo-horizontal-primary.svg` |
| Material com composição vertical | `svg/logo-vertical-primary.svg` |
| Fundo escuro | `svg/logo-horizontal-white.svg` |
| Aplicação monocromática escura | `svg/logo-horizontal-ink.svg` |
| Marca isolada sobre fundo claro | `svg/simbolo-primary.svg` |
| Marca isolada sobre fundo escuro | `svg/simbolo-white.svg` |
| Navegador | `favicon/favicon.svg` e `favicon/favicon.ico` |
| Ícone comum de aplicativo/PWA | `app/app-icon-1024.png`, `app/app-icon-512.png` e `app/app-icon-192.png` |
| Apple touch icon | `app/apple-touch-icon.png` — 180 × 180 |
| Ícone PWA com máscara | `app/app-maskable-512.png` |
| Camada frontal de ícone Android | `app/android-foreground-432.png` + fundo `#D95D39` |

Os SVGs são os masters para novos tamanhos. Os PNGs de símbolo e logo têm transparência. O ícone de aplicativo tem fundo opaco e quadrado; o sistema aplica a máscara de cantos ou círculo. O PNG Android é apenas a camada frontal transparente, e deve receber o fundo indicado.

O `manifest-example.webmanifest` é um exemplo de integração. Os caminhos estão relativos à pasta `app`; ajuste-os à localização pública escolhida no projeto antes de usá-lo. Ele não foi conectado ao aplicativo ativo.

## Espaçamento e escala

- Preserve uma área livre mínima de **14% da largura visível do símbolo** em aplicações de marca. Os masters do símbolo já incluem essa margem.
- Use o logo horizontal a partir de **160 px de largura**; em espaços menores, prefira apenas o símbolo.
- Use o símbolo comum a partir de **24 px**. Para favicon de **16 px**, use os arquivos específicos da pasta `favicon`, com margem compacta.
- Os exports de aplicativo preservam área livre. A versão `maskable` e o foreground Android têm margem ampliada para máscaras; mantenha essa proporção.
- Dimensione sempre proporcionalmente. Preserve o arco, os pés e a separação da assadeira.

## Uso consistente

Use somente as assinaturas e cores deste kit. Preserve a composição, sem deformação, inclinação, sombras, contornos adicionados ou troca arbitrária de espessuras. Para cores de fundo que prejudiquem o laranja, prefira a versão branca ou cacau.

## Arquivos e verificação

- `prancha.png` e `prancha.svg`: apresentação da identidade.
- `svg/`: símbolo e assinaturas em curvas.
- `png/`: exports transparentes em resolução alta.
- `favicon/`: SVG, PNGs em 16/32/48/64 px e ICO com quatro resoluções.
- `app/`: exports de celular, PWA e exemplo de manifest.
- `source/`: referência aprovada, geometria e scripts de reprodução.
- `kit.json`: paleta, arquivos, composição e evidência da comparação de silhuetas.
- `validacao.json`: resultados da conferência técnica dos arquivos.

A prancha, os símbolos e os favicons foram inspecionados visualmente. A validação técnica confere dimensões, transparência, versões opacas, estrutura do ICO, integridade dos SVGs e margem segura do foreground Android. A aplicação ao produto e a inspeção em dispositivos reais são etapas posteriores.

O pen.dev desktop permanece sem documento aberto. Este kit é entregue em SVG editável, PNG e ICO; um documento `.pen` ainda depende de um canvas aberto para importação pelo MCP.
