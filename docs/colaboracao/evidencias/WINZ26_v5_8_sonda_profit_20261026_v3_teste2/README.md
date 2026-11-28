# Sonda V3, teste 2 · execução do Profit através da lacuna de 26/10

PR #2. Motor do simulador `0d2f19a47307d5390f5d89bb53d70e6c87a37856`. Base desta publicação `006ef4c5e268ebb17616bd62c34434b2bc60b151`. Os casos 0, 1 e 2 foram executados no Profit. Os controles locais usam a sonda v1.0 publicada em `f51b1fe289a38a347b5e542aab72e3db57099f03`. As capturas mostram o fonte da sonda V3 parcialmente e seus inputs efetivos. A correspondência de comportamento com a sonda versionada foi conferida nas saídas. A identidade byte a byte do fonte compilado no Profit fica sem verificação. [Controles e fonte versionado](../WINZ26_v5_8_controles_lacuna_20261026_v1/README.md) · [Primeira captura dos casos 0 e 1](../WINZ26_v5_8_sonda_profit_20261026_v3/README.md)

## Configuração e cobertura

Profit Ultra **5.0.4.33**, ativo **WINZ26**, 1 minuto, Backtest **OHLC**, quantidade e máximo 1, slippage 0, execução nos limites ativa, filtro de horário e pausa com zeragem horária desmarcados. As capturas mostram período de análise de seis meses. Os relatórios dos casos 1 e 2 imprimem 20/05/2026 a 20/11/2026 e custos zero. O input `p_Data=1261026` limita a sonda a 26/10/2026. A janela de log vai de 09:27 a 09:43. Mantiveram-se entrada antecipada 09:27, início das proteções 09:28, última barra pré-lacuna 09:29, limpeza 09:41, alvo 100 pontos, stop 10.000 e folga do stop-limit 500. A captura do caso 0 mostra a aba Operações vazia. A do caso 1 mostra as duas pernas da única operação. A do caso 2 mostra o resumo de desempenho e o aviso do stop. [Configuração transcrita](configuracao_profit.csv)

O console dos três casos passa diretamente de 09:29, `CurrentBar=26800`, para 09:39, `CurrentBar=26801`. As barras preparadas de referência do replay também têm a lacuna de 09:30 a 09:38. Os horários do console representam o contexto NTSL. Os horários de execução vêm dos CSVs de operações. O fuso de referência nos replays é America/Sao_Paulo. [Console normalizado](console_profit_normalizado.csv) · [Operações em pontos relativos](operacoes_profit_relativas.csv)

## Resultado por caso

| Caso | Profit | Simulador em reinício e continuidade |
|---|---|---|
| 0 · controle sem ordens | Oito avaliações, sempre posição zero e sem pendências. Nenhuma solicitação ou operação. | Zero preenchimentos e cancelamentos. |
| 1 · entrada antes da lacuna | Solicitação no contexto 09:29. Compra às 09:39 e saída de limpeza às 09:42. Uma operação, **+125 pontos**, **R$ 25,00** líquidos. | Cancela uma compra na retomada às 09:39. Posição zero e nenhum preenchimento. |
| 2 · posição com alvo e stop | Compra às 09:28. Às 09:39, posição +1 e presença de pendentes. Venda às 09:40 ao preço do gatilho do stop. Uma operação, **−10.000 pontos**, **−R$ 2.000,00** líquidos. | Cancela duas proteções às 09:39. Fica comprado na retomada e às 09:40. Sai na limpeza às 09:42, **−10.300 pontos**, **−R$ 2.060,00** líquidos. |

Os consolidados do PDF e os CSVs individuais concordam. O caso 1 dura 3 min e o caso 2 dura 12 min. Os TXT dos casos 0 e 1 e o CSV de operações do caso 1 têm os mesmos hashes da rodada anterior. O novo PDF do caso 1 tem outro hash e as mesmas métricas conferidas. Os resultados dos casos 0 e 1 ficam registrados com a evidência adicional das capturas de configuração. [Matriz dos nove controles](comparacao_controles.csv) · [Resumo dos PDFs](resumo_relatorios_profit.csv) · [Inventário e SHA-256](inventario_fontes.csv)

## Caso 1

No contexto 09:29, a sequência 3 observa posição zero e solicita uma compra. A sequência 4 ainda usa 09:29 e a mesma `CurrentBar` e vê posição +1. A exportação atribui a entrada à abertura de 09:39. A primeira avaliação com rótulo 09:39, sequência 5, vê posição +1 e pendências zero. Em 09:41, a sequência 7 solicita a limpeza. A exportação registra a saída na abertura de 09:42, quando a avaliação vê posição zero. A primeira divergência do simulador é o cancelamento da compra antes de processar a abertura de 09:39. A avaliação extra fica ausente. [Console](console_profit_normalizado.csv) · [Rastreio do simulador](rastreio_simulador.csv)

## Caso 2

| Seq. do console | Rótulo da barra do console | Hora da execução exportada | Evidência |
|---|---|---|---|
| 1 | 09:27 | | Posição zero e solicitação de compra. |
| 2 | 09:27 | | Nova avaliação observa posição +1. |
| | | 09:28:00 | Entrada de um contrato, ao preço de abertura da barra. |
| 3 | 09:28 | | Posição +1. Solicita alvo +100 e stop-limit com gatilho −10.000 e limite −10.500, em pontos relativos à entrada. |
| 4 | 09:29 | | Posição +1, `HasPendingOrders=1`. A sonda solicita as duas proteções novamente. |
| 5 | 09:39 | | Posição +1, `HasPendingOrders=1`. Nenhuma nova solicitação. |
| | | 09:40:00 | Venda de um contrato a −10.000 pontos, preço do gatilho. |
| 6 | 09:40 | | Posição zero e `HasPendingOrders=0`. |
| 7 | 09:41 | | Posição zero e sem nova solicitação de limpeza. |

O alerta do Profit aparece **uma vez**, no primeiro bloco, entre a segunda solicitação do stop e a avaliação de 09:39. Ele avisa que o stop de venda estava acima da abertura do candle e que a automação pode se comportar de outra forma. O preço de abertura mencionado coincide com a barra de 09:39 no insumo privado. Na abertura de 09:39, o preço estava a −10.425 pontos da entrada, 425 pontos abaixo do gatilho e 75 pontos acima do limite. A máxima dessa barra ficou abaixo do gatilho e do alvo. Em 09:40, a barra cobriu o preço do gatilho, que coincide com a saída registrada. [Solicitações e níveis](solicitacoes_protecao_relativas.csv) · [Aviso em pontos relativos](avisos_profit_relativos.csv) · [OHLC relativo por barra](barras_caso2_relativas.csv)

A primeira divergência do caso 2 é o estado de ordens na retomada. O Profit ainda mostra pendências e o simulador já cancelou as duas proteções. Às 09:40 o Profit já está zerado, e o simulador continua comprado até a saída de limpeza. `HasPendingOrders` é booleano. A captura prova a presença de pendências às 09:39 e uma saída às 09:40 ao preço do gatilho, coerente com a proteção solicitada. O ciclo detalhado continua indeterminado. Faltam IDs, status e timestamps nativos para atribuir o disparo, identificar quais ordens ou versões sobreviveram e confirmar o cancelamento da outra perna OCO. A primeira barra após a lacuna tem abertura dentro da faixa do stop-limit, mas o Profit não registrou preenchimento nessa abertura. Portanto, preservar pendências e aplicar imediatamente a regra atual de preenchimento do simulador nessa abertura não reproduziria esta observação.

## Publicação e reprodução

Os dez originais ficam no Windows. Cada console contém dois blocos idênticos de eventos estruturados `LACUNA;`. A análise manteve o primeiro em ordem de emissão (8, 11 e 14 eventos) e registrou o aviso fora desse conjunto, com seu bloco e posição. Os dois CSVs de operações usam CP1252, têm 19 colunas e uma operação cada. Os dois PDFs têm uma página e foram conferidos por extração de texto e inspeção da página renderizada. As três imagens confirmam a configuração. O inventário inclui SHA-256, tamanhos e formatos. Esta pasta publica somente dados normalizados, parâmetros, resumos e preços relativos.

Use uma pasta de saída nova para extrair os dados. Os seis replays locais usam as barras privadas preparadas de 26/10, os três casos, `--avaliacao-pos-preenchimento` e `--rastrear-ordens`. O segundo modo acrescenta `--historico-continuo-lacunas`. A suíte passou com **75 testes** e os 12 avisos já conhecidos de timezone do pandas. O processamento da primeira captura reproduziu os três CSVs anteriores byte a byte.

```powershell
py -3.11 tools/publicar_sonda_lacuna_profit.py --teste2 --originais $pastaPrivada --saida $destinoNovo
$ref = 'docs/colaboracao/evidencias/WINZ26_v5_8_controles_lacuna_20261026_v1'
# Use {"p_Caso":0}, {"p_Caso":1} ou {"p_Caso":2} no JSON, um por replay.
$flags = @()  # Ou @('--historico-continuo-lacunas').
py -3.11 estrategia.py --csv $barrasPrivadas --formato ohlc --segundos 60 `
  --tick 5 --valor-ponto 0.2 --ntsl "$ref/sonda_lacuna_simulador_v1_0.ntsl" `
  --inputs $inputs --saida $replayNovo --avaliacao-pos-preenchimento --rastrear-ordens @flags
py -3.11 -m pytest -q
```

Os resultados são de Backtest OHLC. A rodada documenta evidências e preserva o motor e a classificação da saída de 10:15 da v5.8 como ambígua em OHLC. [Ambiguidade das 10:15](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/README.md#saída-das-1015-em-2610) · [Fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto](SHA256SUMS.txt)
