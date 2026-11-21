# Resultado da sonda Profit na retomada de 26/10/2026

PR #2. Controles de referência publicados em `f51b1fe289a38a347b5e542aab72e3db57099f03`. Motor do simulador `0d2f19a47307d5390f5d89bb53d70e6c87a37856`. A captura é identificada como **sonda V3** pelos nomes entregues. Os eventos e parâmetros observáveis dos casos 0 e 1 correspondem aos ramos da sonda publicada no PR como v1.0. A versão exata compilada no Profit e sua configuração completa não vieram anexadas. [Sonda e protocolo de referência](../WINZ26_v5_8_controles_lacuna_20261026_v1/README.md)

## Resultado

| Parâmetro | Profit | Simulador em reinício e continuidade |
|---|---|---|
| `p_Caso=0` | Nenhuma operação, conforme informado pelo operador. O console tem oito avaliações, todas com posição e pendências zero, sem solicitações. | Zero preenchimentos, cancelamentos e avaliações extras. |
| `p_Caso=1` | Uma compra de um contrato preenchida às 09:39 e encerrada às 09:42 após a solicitação de limpeza. Na avaliação de contexto 09:39, posição +1 e pendências zero. | A compra solicitada às 09:29 é cancelada na retomada. Posição zero, zero preenchimentos e nenhuma avaliação pós-preenchimento. |
| `p_Caso=2` | Pendente. Os arquivos recebidos são dos casos 0 e 1. | O controle anterior registrou dois cancelamentos e posição comprada de um contrato na retomada. |

O caso 0 é um controle sem envio de ordens. Na sonda publicada, apenas os casos 1 e 2 habilitam entrada, e somente o caso 2 instala alvo e stop. Assim, o resultado do caso 0 confirma os rótulos e a ausência de operação na janela, sem testar a sobrevivência de uma ordem pendente. [Matriz da comparação](comparacao_controles.csv)

## Primeira divergência no caso 1

| Sequência no Profit | Contexto do console | Hora na exportação de operações | Evidência |
|---|---|---|---|
| 3 | 09:29 | | Posição 0, pendências 0. Solicitação de compra de 1 contrato. |
| 4 | 09:29 | | Nova avaliação da mesma `CurrentBar=26800` observa posição +1 e pendências 0. A associação com a compra é sustentada pela sequência e pela única operação exportada. |
| Operação 1, entrada | | 09:39:00 | Compra de 1 contrato no preço de abertura da barra de 09:39. |
| 5 | 09:39 | | `CurrentBar=26801`. Posição +1 e pendências 0 na primeira avaliação com o novo rótulo. |
| 7 | 09:41 | | A sonda solicita zeragem de limpeza. |
| Operação 1, saída | | 09:42:00 | Venda de 1 contrato no preço de abertura da barra de 09:42. |
| 8 | 09:42 | | Posição 0, pendências 0. |

A primeira divergência é o preenchimento da entrada na retomada. O Profit registra a compra às 09:39 e a avaliação adicional com contexto 09:29 observa a nova posição. O simulador cancela a ordem antes de processar a abertura de 09:39, avalia o primeiro candle da retomada zerado e não executa a avaliação extra. Os dois horários pertencem a registros distintos. Nenhum deslocamento global foi aplicado. Na captura do Profit, a barra de contexto avança de 09:29 a 09:39 com incremento unitário de `CurrentBar`. Os rótulos 09:30–09:38 estão ausentes nos dois consoles. [Console normalizado](console_profit_normalizado.csv) · [Rastreio do simulador](../WINZ26_v5_8_controles_lacuna_20261026_v1/rastreio_simulador.csv)

O CSV de operações contém uma linha de WINZ26 em 26/10/2026, lado compra, um contrato por lado, duração de 3 min e variação de **+125 pontos**, equivalentes a **R$ 25,00** a R$ 0,20 por ponto, sem comissões registradas. A comparação local com as barras preparadas conferiu os preços de entrada e saída com as aberturas de 09:39 e 09:42. O PDF de uma página confirma uma operação vencedora, nenhuma perdedora ou zerada, saldo líquido de R$ 25,00, custos de R$ 0,00 e duração média de 3 min. O intervalo impresso no relatório é 20/05/2026 a 20/11/2026. A operação individual está em 26/10, conforme a exportação. [Operação em pontos relativos](operacao_profit_relativa.csv)

## Limites e reprodução

O caso 1 demonstra que o Profit preencheu a compra no primeiro candle disponível nesse backtest. Os eventos internos da ordem entre a solicitação e o preenchimento, incluindo o momento em que ficou elegível e a resolução abaixo do segundo, dependem do histórico de ordens do mesmo backtest. O comportamento de alvo, stop e OCO na lacuna depende de `p_Caso=2`, com console, operações, barras, configuração e histórico nativo se disponível. A saída da v5.8 às 10:15 continua classificada como ambígua em OHLC. Nenhuma regra do motor foi alterada. [Protocolo para o caso 2](../WINZ26_v5_8_controles_lacuna_20261026_v1/README.md#execução-manual-no-profit) · [Ambiguidade das 10:15](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/README.md#saída-das-1015-em-2610)

Os quatro originais ficaram no Windows. Cada TXT continha dois blocos de eventos idênticos. O processamento manteve o primeiro bloco, sem reordenar, excluiu cabeçalhos de Debug e normalizou a pontuação da data e de `CurrentBar`. Os oito eventos do caso 0 são avaliações. Dos 11 eventos do caso 1, nove são avaliações e dois são solicitações. O CSV usa CP1252 e tem cinco linhas de preâmbulo, 19 colunas e uma operação. A publicação conserva apenas os campos necessários, sem conta, titular, caminho privado ou preços absolutos. O inventário registra SHA-256 e tamanho dos quatro originais. A verificação do PDF foi feita localmente por extração de texto e inspeção da página renderizada. [Inventário](inventario_fontes.csv)

Foram executados quatro replays locais da sonda sobre as barras privadas preparadas de 26/10, cobrindo casos 0 e 1 com reinício e continuidade. Usou-se a CLI OHLC, 60 s, tick 5, R$ 0,20 por ponto, avaliação pós-preenchimento e rastreamento. O modo continuidade adicionou `--historico-continuo-lacunas`. A suíte passou com **75 testes** e 12 avisos de timezone do pandas já conhecidos.

```powershell
py -3.11 tools/publicar_sonda_lacuna_profit.py --originais $pastaPrivada --saida $destinoNovo
$evid = 'docs/colaboracao/evidencias/WINZ26_v5_8_controles_lacuna_20261026_v1'
# Use {"p_Caso":0} ou {"p_Caso":1} no JSON de inputs e um destino por execução.
# Para o segundo modo, $flags = @('--historico-continuo-lacunas').
$flags = @()
py -3.11 estrategia.py --csv $barrasPrivadas --formato ohlc --segundos 60 `
  --tick 5 --valor-ponto 0.2 --ntsl "$evid/sonda_lacuna_simulador_v1_0.ntsl" `
  --inputs $inputs --saida $replayNovo --avaliacao-pos-preenchimento --rastrear-ordens @flags
py -3.11 -m pytest -q
```

[Fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto de publicação](SHA256SUMS.txt)
