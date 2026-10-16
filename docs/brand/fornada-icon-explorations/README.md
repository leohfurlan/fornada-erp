# Fornada — exploração de ícones

Quatro direções criadas em 07/10/2026 para o ERP de confeiteiras artesanais.

1. **F de Fornada** — monograma laranja com referência à assadeira; moderna e clean.
2. **Forno aberto** — arco e assadeira em laranja queimado; moderna e clean.
3. **Forma de bolo** — forma vista de cima em ameixa; moderna e clean.
4. **Massa em movimento** — espiral de massa em terracota; orgânica e clean.

## Prévia disponível

Abra `index.html` para comparar os quatro PNGs com transparência, os lockups com o nome, amostras de 16/24/32/48px, aplicações de celular e navegador. A página permite alternar fundos e testar máscara circular. No fundo escuro, demonstra versões brancas através de CSS; essas versões ainda não são arquivos de imagem separados. Os conceitos foram gerados individualmente com a ferramenta imagegen. Os prompts completos estão em `prompts.json`.

Os quatro símbolos foram inspecionados individualmente e no navegador em 16/24/32/48px, no lockup e no exemplo de ícone do aplicativo. Os 36 usos de imagem da comparação carregaram e a página não apresentou transbordamento horizontal no viewport desktop. Os controles de fundo e máscara responderam. A arte ameixa requer a versão clara em fundo escuro; a comparação já representa essa adaptação.

O estudo favorece inicialmente a opção 01 pela associação direta com o nome. A opção 03 oferece uma alternativa acolhedora com bom reconhecimento da silhueta.

## Documento pen.dev desktop

O MCP do desktop foi conectado através do servidor oficial instalado. Ele exige um documento aberto antes de ler a skill ou executar edições. A criação vetorial permanece aguardando um documento aberto e salvo em `C:\Projetos TI\fornada\docs\brand\fornada-icones.pen`.

`mcp-generate.json` contém a solicitação preparada para gerar os quatro símbolos vetoriais pelo recurso SVG do pen.dev. `pen-desktop-mcp.py` apenas usa o protocolo MCP oficial por stdio; ele não lê nem escreve arquivos `.pen` diretamente.

Os PNGs são propostas para revisão visual. Ainda não foram integrados ao aplicativo, nem substituíram assets existentes. Não foi feito commit, push ou deploy.
