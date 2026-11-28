# Captura nativa e paridade da v5.8 em WINZ26

Comparador e diagnóstico executados em `3a8d32d3185dfd2686db53df8735e5713667d208`. O motor de replay é o mesmo de `68f1025526be87c52a5fa8cb8f9368dad06062ca`. O replay isolado usa as saídas verificadas da rodada `e54a729150b736173c4fdea16d65579759df6dde`. Windows 10, Python 3.11.3, pandas 3.1.1. [Protocolo, configuração e NTSL da rodada anterior](../WINZ26_v5_8_validacao_20261021_20261026_v1/README.md)

## Resultado

| Pregão | Cenário no simulador | Profit | Simulador | Operações exatas | Primeira solicitação sem par, rótulo NTSL |
|---|---|---:|---:|---:|---|
| 21/10 | Pregão isolado | 7 | 6 | 6 | 10:08, no Profit |
| 21/10 | Com 20/10 no histórico | 7 | 7 | **7** | — |
| 26/10 | Pregão isolado | 10 | 10 | 9 | 10:14, no Profit |
| 26/10 | Com 23/10 no histórico | 10 | 10 | 8 | 09:50, no simulador |
| 26/10 | Histórico + continuidade em 09:39, diagnóstico | 10 | 10 | **9** | — |

Operação exata exige igualdade de horário de entrada e saída, direção, quantidade e preços. Com o histórico adicional de 21/10, os 14 preenchimentos e as 306 solicitações também coincidem. Sinais, filtros, indicadores e posição/estado coincidem nas 509 avaliações do trecho elegível. No diagnóstico final de 26/10, todas as 62 solicitações coincidem no pregão. As 472 avaliações do trecho elegível coincidem em sinais, filtros, indicadores e posição/estado. A única operação diferente tem as mesmas entrada, direção e quantidade, com preço de saída diferente. [Matriz de paridade](matriz_paridade_v5_8.csv) · [Matriz por camada](matriz_camadas_v5_8.csv) · [Operações sanitizadas](operacoes_sanitizadas_por_cenario.csv)

## Inventário e qualidade dos dados

| Captura | Conteúdo conferido |
|---|---|
| Console da estratégia | Dois blocos idênticos de 1.503 eventos. Retido o primeiro, com 1.135 avaliações. |
| Console da sonda v2 | Dois blocos idênticos de 4 eventos. Retido o primeiro. |
| Barras | 20.001 linhas em 36 pregões, 29/09 a 19/11. Cinco colunas, `Data`, `Abertura`, `Máxima`, `Mínima` e `Fechamento`. Ordem decrescente no original, sem timestamps duplicados ou OHLC ausente. |
| Operações | 290 operações WINZ26 em 56 pregões, 13/08 a 19/11. Dezenove colunas após cinco linhas de cabeçalho e zero IDs repetidos. |
| PDF | Uma página, janela configurada de 20/05 a 20/11. O total de 290 operações e a contagem de 151 positivas, 138 negativas e uma zerada coincidem com o CSV completo. Esse é o agregado da janela do relatório. |

O cruzamento por ativo conhecido, pregão e rótulo de minuto encontrou OHLC idêntico nas 565 barras de 21/10 e 553 de 26/10. Em 26/10, faltam 09:30–09:38 nos dois lados. O CSV novo de barras contém apenas OHLC e não identifica o ativo nas linhas. Trades e saldo de agressão do primeiro registro de avaliação de cada barra coincidiram com o insumo do simulador nos dois dias. Quantity e Volume financeiro vieram da exportação histórica já usada no replay. O CSV OHLC atual não permite validá-los de forma independente. Originais, PDF, identificadores de conta e titular, campos brutos de mercado e caminhos privados ficaram no Windows. Foram publicados hashes, contagens, operações sem preços absolutos e recortes de estado. [Inventário e hashes dos originais](inventario_fontes.csv)

WINZ26, barras de 1 minuto, `America/Sao_Paulo`, v5.8 auditada conforme os inputs versionados, `p_Exec_Tick=0`, lote 5, stop 350, alvo 400, offset 50 e máximo diário 10. O lote é confirmado nas operações dos dois dias. O PDF registra custo zero no agregado. Os arquivos recebidos não contêm uma exportação de todos os ajustes da interface. No simulador, tick 5, R$ 0,20 por ponto, custos e slippage zero, Volume financeiro, agressão injetada, VWAP contínua e modo pós-preenchimento. O corte de 63 barras por segmento deixa 502 rótulos elegíveis em 21/10, desde 10:03, e 463 em 26/10, desde 10:42. A v5.8 também aplica `CurrentBar > 86` com os inputs usados.

## Primeiro evento e diagnóstico

**21/10.** No pregão isolado, o Profit já inicia com `aquecido=1`, pois sua série inclui histórico anterior. No primeiro rótulo elegível, 10:03, o simulador ainda tem `aquecido=0`. Às 10:08, ambos registram sinal de compra, mas somente o Profit solicita a entrada. A operação do Profit entra às 10:09 e sai às 10:16. Ao prefixar as 565 barras reais de 20/10, o sinal gera a mesma solicitação e ambas as execuções coincidem.

**26/10, pregão isolado.** A primeira solicitação sem par é a do Profit em 10:14, seq. 635. Há sinal de compra nos dois lados, mas o simulador ainda está abaixo do `CurrentBar` exigido. A ausência dessa compra deixa o contador local uma entrada abaixo durante a sessão. Às 15:26 o Profit já está no limite de 10 e o simulador solicita a compra que preencherá às 15:27. Essas duas operações sem par, uma de cada motor, explicam as nove correspondências do cenário isolado.

**26/10, com histórico e reinício na lacuna.** Prefixar as 563 barras reais de 23/10 faz passar o filtro `CurrentBar`. Na retomada às 09:39, o Profit avança apenas um `CurrentBar` em relação a 09:29. Suas séries de ATR, desvio e Volume histórico mantêm contexto anterior, enquanto o simulador reinicia as janelas e o histórico local na lacuna. Às 09:50, com os dois lados zerados, o Profit registra regime 0 e compra 0. O simulador registra regime 1 e compra 1 e faz a primeira solicitação divergente. O simulador termina com compras sem par às 09:51 e 10:14, enquanto as do Profit às 10:15 e 14:52 ficam sem par. Às 14:51, ambos têm sinal de compra. O Profit tem nove entradas e envia o próximo pedido. O simulador já tem dez.

**26/10, continuidade apenas como diagnóstico.** O teste mantém a janela do simulador através da retomada de 09:39, sem inventar os nove candles ausentes. A execução verifica que nos dois lados as avaliações de 09:29 e 09:39 estão zeradas, sem pendentes ou solicitações. O corte de elegibilidade ainda conta 63 barras após a lacuna. A hipótese elimina as diferenças de solicitação no pregão. O primeiro preenchimento diferente é o segundo, a saída das 10:15. A compra de cinco contratos e os níveis são os mesmos. O rótulo do envio do alvo e stop é 10:14. O OHLC de 10:15 atinge os dois níveis. O Profit registra +400 pontos sobre a entrada e o simulador aplica -350 pontos, seu desfecho adverso para ambas as proteções tocadas na mesma barra. A ordem intrabar dos preços continua indeterminada sem resolução subminuto. O motor distribuído continua aplicando sua regra de lacunas e ambiguidade. [Rastreio do primeiro evento](primeiros_eventos_v5_8.csv) · [Recorte da ambiguidade das 10:15](ambiguidade_10h15.csv)

Os registros preservam dois relógios. O console indica o rótulo da barra de contexto da avaliação. As execuções usam o horário de abertura/fechamento da operação exportada. O comparador conserva a ordem de cada camada no mesmo rótulo, sem deslocar horários. A comparação de preenchimentos usa a precisão da exportação e desempata pelo número da operação. A confirmação de ativação, cancelamento e ordem OCO exige histórico nativo de ordens com resolução subminuto.

## Sonda nativa v2

| Primeira avaliação regular zerada após a extra, 13:04 | Profit | Simulador |
|---|---:|---:|
| Boolean antes | **1** | **1** |
| Array antes | **17** | **0** |
| `estado[1]` | **23** | **0** |

Na avaliação extra comprada, os dois lados atribuem Boolean 1, array 17 e escalar 23. A primeira separação observada na sonda é a sequência 3, com posição zero. A sonda distingue a persistência de escalares já confirmada do comportamento do array e da leitura `[1]` para estado escrito na avaliação extra. O motor atual mantém isolados o array e o histórico. A v5.8 completa não usa arrays, e os resultados após aquecimento para seus indicadores e sinais são comparados separadamente. [Log completo sanitizado da sonda](sonda_v2_profit_simulador.csv)

## Reprodução e limites

Use a auditoria da v5.8 e os inputs versionados da rodada anterior. No cenário histórico, `tools/preparar_paridade_profit_barras.py` prepara 20/10 e 21/10, ou 23/10 e 26/10, a partir das exportações privadas de barras e indicadores. Concatene as saídas com um único cabeçalho, pregão anterior primeiro. Os hashes das concatenações usadas são `f1d85e4454e8c6c61e47c44832f5d9fc7280d60f44fa7ff49ff1d1bda9ffdf6b` (21/10) e `bd13dfa559bb6c26ff0c253d3414b8b9994fe699af3482a80b9129b66ab1ec13` (26/10). O comparador filtra preenchimentos pelo pregão alvo mesmo quando o replay contém histórico anterior.

```powershell
py -3.11 estrategia.py --csv $barrasPreparadas --ntsl $auditoria --inputs $inputs `
  --saida $replay --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --volume-financeiro-ntsl --agressao-referencia-injetada --vwap-continuo-lacunas `
  --avaliacao-pos-preenchimento --rastrear-ordens

# Somente no diagnóstico da lacuna; a referência é o replay com 23/10 e 26/10.
py -3.11 -m tools.diagnosticar_continuidade_v5_8 --barras $barrasComHistorico `
  --ntsl $auditoria --inputs $inputs --console-profit $consoleProfit `
  --console-referencia "$referencia/console.csv" --saida $diagnostico

py -3.11 tools/comparar_v5_8.py --data $dia --aquecimento 63 `
  --console-profit $consoleProfit --operacoes-profit $operacoesProfit `
  --barras-profit $barrasProfit --barras-preparadas $barrasPreparadas `
  --console-simulador "$replay/console.csv" --candles-simulador "$replay/candles.csv" `
  --execucoes-simulador "$replay/execucoes.csv" --saida $comparacao
py -3.11 -m pytest -q
```

A suíte passou com **68 testes** e 12 avisos de timezone já conhecidos. O comparador só remove cópias de console integralmente idênticas, aceita o CSV OHLC e registra os campos ausentes. O teste de continuidade não altera o motor em produção. A regressão da v5.7 foi reexecutada nos seis cenários com VWAP contínua e os mesmos insumos. A comparação usou o corte de 63 barras por segmento. Os 24 arquivos de operações, candles, console e ordens e os dois CSVs de plots coincidiram byte a byte com a rodada anterior. Em 21/10, os três modos mantiveram 10/10. Em 26/10, padrão, proteção legada e pós-preenchimento mantiveram respectivamente 8/12, 11/12 e 12/12. A operação #182 continua exata no pós-preenchimento. Os oito indicadores mantiveram 502/502 e 463/463 barras elegíveis. [Comandos da regressão](../WINZ26_v5_7_persistencia_escalar_20261026_v2/README.md#comandos) A paridade se restringe aos pregões observados e ao trecho elegível. [Matriz v5.7 revalidada](../WINZ26_v5_8_validacao_20261021_20261026_v1/regressao_v5_7.csv)

[TXT completo para o Gemini](fontes_gemini.txt) · [Manifesto de SHA-256](SHA256SUMS.txt)
