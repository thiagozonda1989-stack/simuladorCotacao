# Sondas S1 e S2 no Profit · validade sem renovação e stop-limit

PR #2. Motor executado `142dbe882ae2a0436c4273a6e5bfa1268222e5d3`. Protocolo e sondas publicados em `5166699dabb51b787db977fbc8028d8e2474437a`. As capturas do Profit mostram os parâmetros e parte do fonte. A saída observada corresponde ao protocolo. A identidade byte a byte da versão compilada no Profit fica sem verificação. [Sondas e instruções originais](../WINZ26_v5_8_entrada_mercado_lacuna_20261026_v1/README.md)

## Resultados

| Sonda | Resultado observado no Profit | Comparação com o simulador |
|---|---|---|
| S1 · validade | Após um único envio às 13:16, `HasPendingOrders=1` em todas as avaliações de 13:17 a 13:21. Depois da solicitação de cancelamento às 13:21, o estado passa a zero às 13:22. A limpeza fecha a operação às 13:23. | A primeira diferença é **13:18**. O simulador observa pendentes em 13:17 e zero de 13:18 em diante. A entrada e a saída de limpeza são exatas. |
| S2 · variante 1 | Stop solicitado às 13:45. Saída às **13:46**, no preço de abertura, **5 pontos abaixo do gatilho**. A faixa de 13:46 contém o gatilho. | Entrada e saída exatas. A avaliação de 13:46 vê posição e pendentes zero. |
| S2 · variante 2 | Stop solicitado às 15:28. Saída às **15:29**, no preço de abertura, **5 pontos abaixo do gatilho**. Toda a barra de 15:29 fica abaixo do gatilho. | Entrada e saída exatas. A avaliação de 15:29 vê posição e pendentes zero. |

Os três pares de entrada e saída coincidem por horário exportado, direção, quantidade e preço, para um contrato comprado em cada execução. Os CSVs e PDFs conferem os totais líquidos de **−R$ 240,00**, **−R$ 5,00** e **R$ 2,00**, todos com custos reportados de zero. A duração foi de 7 min na S1 e 1 min em cada variante da S2. Os PDFs mostram uma operação por sonda. [Comparação de operações](comparacao.csv) · [Totais dos PDFs](resumo_relatorios.csv)

## S1 · duração das pendências

O contexto 13:15 registra a solicitação de compra e, em avaliação posterior com o mesmo rótulo, já vê posição +1. A entrada exportada é 13:16. No contexto 13:16, a sonda envia alvo a +2.000 pontos, gatilho a −2.000 e limite a −2.500, relativos à entrada. Cada proteção aparece em uma única solicitação. O histórico privado preparado mostra barras consecutivas e níveis fora da faixa no intervalo observado antes da limpeza. Em 13:21, o Profit ainda vê uma ou mais ordens pendentes e a sonda solicita cancelamento. Às 13:22, o Profit vê posição +1 e pendências zero. A saída exportada às 13:23 corresponde à zeragem de limpeza solicitada em 13:22.

No replay local, `ordem_so_proxima_barra=True` deixa as proteções elegíveis na barra seguinte. A avaliação de 13:17 ainda vê as pendências e elas expiram depois da avaliação porque a sonda não as renova. Em 13:18, o estado já é zero. A S1 demonstra que pelo menos uma pendência permanece após a primeira barra elegível no backtest nativo, sem renovação observada no console. Como `HasPendingOrders` é booleano, identificar cada perna, a duração individual e o vínculo OCO exige a lista nativa de ordens. [Estado por barra](persistencia_s1.csv) · [Console Profit](console_profit.csv) · [Console simulador](console_simulador.csv)

## S2 · preço de abertura abaixo do gatilho

As duas variantes enviam um stop-limit de venda no fechamento da barra programada. O gatilho é o fechamento menos 5 pontos, com limite 500 pontos abaixo. O Profit emitiu um aviso em cada variante, logo após a solicitação de stop no primeiro bloco. O aviso confirma que a abertura estava 5 pontos abaixo do gatilho. A saída exportada coincide com a abertura na barra imediatamente seguinte, dentro da faixa entre gatilho e limite.

| Variante | Contexto da solicitação | Hora de saída exportada | Abertura em relação ao gatilho | Máxima em relação ao gatilho |
|---|---|---|---:|---:|
| 1 | 13:45 | 13:46:00 | −5 | +70 |
| 2 | 15:28 | 15:29:00 | −5 | −5 |

A máxima em 15:30 fica 75 pontos acima do gatilho nas barras preparadas, mas a posição do Profit já está zerada na avaliação de 15:29. Esse caso descarta a hipótese de que, nessas barras consecutivas, o preenchimento precise aguardar uma faixa OHLC que contenha o preço do gatilho. A geometria das barras vem do histórico privado preparado na rodada anterior. A abertura foi conferida também com o aviso nativo e o preço de saída do CSV. O instante intrabar do disparo, os status e a identidade da ordem continuam sem confirmação nativa. A S2 envia apenas o stop. [Barras relativas](barras_relativas.csv) · [Avisos](avisos.csv)

O caso 2 da sonda V3 na lacuna de 09:30–09:38 permanece uma divergência de execução. Ali, a posição e as pendências foram observadas às 09:39 e a saída foi registrada às 09:40 ao preço do gatilho. Os resultados da S2 em barras consecutivas não explicam esse atraso. O funcionamento da automação em tempo real está fora da cobertura deste backtest. O comportamento do motor, a opção de entrada a mercado através de lacuna e a classificação da saída de 10:15 como ambígua em OHLC foram preservados. [Sonda V3, caso 2](../WINZ26_v5_8_sonda_profit_20261026_v3_teste2/README.md#caso-2)

## Configuração e fontes

Capturas do Profit Ultra 5.0.4.33 em WINZ26, 1 minuto, Backtest OHLC, lote e máximo 1, slippage zero, execução nos limites ativa. Período exibido de seis meses (20/05 a 20/11/2026 nos PDFs). `p_Data=1261026` restringe as sondas a 26/10/2026. S1 usou entrada 13:15, proteção 13:16, cancelamento 13:21 e zeragem 13:22, com distância 2.000 e folga 500. S2 usou variantes 1 e 2, distância de gatilho 5 e folga 500. As janelas de referência têm 9, 7 e 7 barras consecutivas em America/Sao_Paulo. As extrações recebidas incluem 12 arquivos. As barras de referência são insumo privado da rodada anterior e nenhum histórico nativo de ordens com IDs e timestamps subminuto foi anexado.

Cada console contém dois blocos estruturados idênticos. Foi retido o primeiro, em ordem de emissão, com 15 eventos para S1 e 10 para cada variante de S2. Cada aviso de S2 aparece apenas no primeiro bloco, após o evento estruturado 5, e foi preservado em pontos relativos. Os CSVs têm 19 colunas e uma operação em cada arquivo. Os três PDFs têm uma página e foram conferidos por extração de texto e inspeção das páginas renderizadas. O inventário tem os tamanhos e SHA-256 dos originais. O GitHub contém somente resultados normalizados, recortes relativos e resumos. Os TXT, PDFs, PNGs e CSVs originais seguem no Windows. [Inventário](inventario.csv)

## Reprodução local

A adaptação ao interpretador local só trocou a formatação de `ConsoleLog`. Foram executadas as três sondas no código indicado no topo, com as barras privadas de referência, tick 5, valor de ponto R$ 0,20, custo e slippage zero, avaliação pós-preenchimento e rastreio. Os 12 CSVs gerados coincidiram byte a byte com os dos controles locais da rodada anterior. A suíte passou com **89 testes** e 12 avisos de timezone do pandas já conhecidos.

```powershell
# Execute cada fonte da sonda adaptada à sintaxe do simulador.
# Em $replays, use subpastas s1, s2v1 e s2v2. Use {} na S1,
# {"p_Variante":1} na S2v1 e {"p_Variante":2} na S2v2.
py -3.11 estrategia.py --csv $barrasPrivadas --ntsl $sondaLocal --inputs $inputs `
  --saida $replay --formato ohlc --segundos 60 --tick 5 --valor-ponto 0.2 `
  --avaliacao-pos-preenchimento --rastrear-ordens
py -3.11 -m tools.publicar_sondas_protecao_profit --originais $pastaPrivada `
  --barras $barrasPrivadas --replays $replays --saida $destinoNovo
py -3.11 -m pytest -q
```

`FloatToString(expr, 0)` virou `(expr)` nas chamadas de log e o parâmetro de cor `clYellow` foi removido nas cópias locais. Os NTSLs do Profit seguem versionados na pasta original. [Fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto de publicação](SHA256SUMS.txt)
