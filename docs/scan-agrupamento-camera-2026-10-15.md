# Scan: produtos repetidos e foto da câmera

Implementação local em 15/10/2026, preservando alterações existentes. Sem commit, deploy, reprocessamento por IA ou movimentação de estoque nesta atividade.

## Agrupamento

A leitura web encaminhava cada linha extraída separadamente à revisão. Um teste no caminho real `ReconhecimentoCompras.ler`, com extração simulada e valores transcritos da nota fornecida, reproduziu nove linhas em vez dos cinco produtos esperados.

Agora a leitura agrupa deterministicamente observações com a mesma identidade, embalagem, unidade, preço unitário e demais evidências. Soma quantidade, desconto e total, preservando a origem das linhas em `linhas_origem`. A interface informa quantas linhas foram agrupadas. Não agrega preços/embalagens distintos, dados incompletos, valores inconsistentes ou casos em que o agrupamento mudaria os centavos por arredondamento.

No exemplo fornecido: quatro refrigerantes de R$ 3,08 resultam em quantidade 4 e R$ 12,32; dois cremes de leite de R$ 2,89 resultam em quantidade 2 e R$ 5,78. Os demais itens e o desconto de R$ 0,81 são preservados. Total dos cinco produtos: R$ 50,05. O teste comprova o agrupamento dessa transcrição; não comprova a qualidade da extração real da fotografia.

## Upload da câmera

Foi reproduzido o apagamento imediato do input de arquivo antes de terminar a tentativa de leitura. O input agora só é limpo ao concluir a tentativa, inclusive quando há falha, permitindo selecionar novamente a mesma foto sem descartar antecipadamente sua referência.

Fotos acima do limite de 8 MB são preparadas no navegador: orientação EXIF na decodificação, dimensões limitadas, preservação de proporção e redução JPEG antes de enviar. PDFs permanecem limitados a 8 MB. MIME JPEG alternativo (`image/jpg`, `image/pjpeg`) é normalizado no cliente e no endpoint. Arquivos sem MIME conhecido têm o cabeçalho verificado para JPEG/PNG/WebP/PDF. Falhas de preparação indicam o campo de anexo, com o botão visível destacado e mensagem em português. A requisição de leitura possui prazo máximo e mensagem de rede/tempo limite, sem assumir que uma falha operacional seja preenchimento inválido.

As imagens anexadas não conservam necessariamente o formato/tamanho original retornado pela câmera. A consulta read-only às contagens dos logs disponíveis não trouxe registro suficiente para identificar a causa exata da falha relatada. A pergunta sobre o comportamento após confirmar a foto foi apresentada ao usuário; a reprodução em câmera Android física permanece pendente. Os ajustes cobrem falhas reproduzíveis de upload e não permitem afirmar que todo problema do retorno da câmera do aparelho foi eliminado.

## Validação

- Agrupamento: regressão da nota fornecida, preços/embalagens distintos, valores incompletos, conservação de desconto/total, proveniência e proteção de arredondamento.
- Upload: referência do arquivo até concluir, repetição após falha, JPEG alternativo, redução de foto acima de 8 MB, falha de decodificação, PDF grande e destaque do controle visível.
- Suíte backend: 281 testes unitários aprovados, mais quatro testes novos do endpoint de upload aprovados separadamente (285 testes distintos).
- Suíte frontend: 127 testes aprovados; teste adicional do controle visível de anexo validado na etapa final.
- TypeScript e Ruff dos módulos/testes centrais aprovados. Aceite com foto real no Android e publicação permanecem pendentes.
