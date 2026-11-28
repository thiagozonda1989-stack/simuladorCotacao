# Entrada a mercado através de lacuna intradiária no replay OHLC

PR #2. Código executado `142dbe882ae2a0436c4273a6e5bfa1268222e5d3`. Motor da sonda no Profit e dos replays de referência `0d2f19a47307d5390f5d89bb53d70e6c87a37856`. Evidências revisadas `b2fd88a5dbb951410975c425594a08cf947d3ad6`. WINZ26, 26/10/2026, barras de 1 minuto e fuso America/Sao_Paulo. [Sonda V3, teste 2](../WINZ26_v5_8_sonda_profit_20261026_v3_teste2/README.md) · [Revisão Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7056510702) · [Revisão Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7056520481)

## Opção experimental

`--entrada-mercado-atraves-lacuna` vem desativada, exige `--historico-continuo-lacunas` e é exclusiva do motor OHLC. Na retomada intradiária com posição zerada, mantém entradas a mercado. O processamento usa o mesmo critério de elegibilidade do replay regular. Uma latência adicional configurada continua valendo em número de barras existentes. Ordens limite e stop, proteções e demais pendências continuam sujeitas ao cancelamento na lacuna. A regra de mudança de pregão, a contagem de cancelamentos efetivos e o registro de lacunas com posição exposta foram preservados. A regra stop-limit e `--vwap-continuo-lacunas` seguem independentes.

Com `--avaliacao-pos-preenchimento`, a avaliação adicional pode usar a última barra fechada antes da lacuna. A execução usa a abertura da primeira barra existente em que a ordem está elegível. O processamento grava o horário da execução na barra de retomada e mantém o rótulo de contexto NTSL separado. Usa a mesma regra de criação de novas proteções da avaliação extra existente.

## Controles com a sonda V3

No caso 1, o Profit solicita compra no contexto 09:29 (seq. 3). A seq. 4, também rotulada 09:29, já observa posição +1. A exportação registra o preenchimento na abertura 09:39. No simulador com a opção ativa, o preenchimento registra 09:39, a extra usa o contexto 09:29 e a avaliação regular de 09:39 vê posição +1 e `HasPendingOrders=0`. A saída de limpeza ocorre às 09:42. As duas execuções coincidem em preço e quantidade com o Profit, incluindo +125 pontos (R$ 25,00).

| Caso | Reinício | Continuidade histórica | Continuidade e entrada pela lacuna |
|---|---|---|---|
| 0, controle | 0 cancelamentos e 0 preenchimentos | Igual | Igual |
| 1, entrada pendente | 1 cancelamento, posição 0 às 09:39 | Igual | 0 cancelamentos, compra às 09:39, extra com contexto 09:29 |
| 2, posição com proteções | 2 cancelamentos, posição +1 às 09:39 e saída de limpeza às 09:42 | Igual | Igual |

O **caso 2 continua divergente**. No Profit, a avaliação de 09:39 ainda identifica pendentes e a saída da posição ocorre às 09:40 ao preço do gatilho, a −10.000 pontos da entrada. O simulador cancela o par de proteções na lacuna, mantém a posição aberta na retomada e sai na limpeza às 09:42, a −10.300 pontos. O próximo controle separa a validade sem renovação da hipótese de preenchimento do stop-limit na abertura além do gatilho. Os IDs, o instante de disparo e o vínculo OCO ficam pendentes da evidência nativa. [Matriz dos casos](controles_v3.csv) · [Rastreio na retomada](rastreio_caso1.csv)

## Regressões e testes

Usaram-se barras preparadas, VWAP contínua, agressão exportada, volume financeiro, zero custo e slippage, tick 5 e valor de R$ 0,20 por ponto. O comparador da v5.8 usa o pregão anterior no histórico, `p_Exec_Tick=0`, lote 5, e corte de 63 barras por segmento.

| v5.8 | Reinício | Continuidade histórica | Continuidade e entrada pela lacuna |
|---|---:|---:|---:|
| 21/10 | 7/7 | 7/7 | 7/7 |
| 26/10 | 8/10 | 9/10 | 9/10 |

Os quatro CSVs de operação, candles, ordens e console ficaram idênticos byte a byte aos respectivos replays de referência nos seis cenários, totalizando 24 comparações. Em 26/10 com continuidade, as 62 solicitações e as dez entradas continuam exatas. A saída de **10:15** segue ambígua em OHLC. O Profit registra alvo de +400, e o simulador aplica stop de −350. A nova opção não altera a decisão nessa barra. [Matriz v5.8](regressao_v5_8.csv)

A **v5.7** manteve **10/10** em 21/10 em todos os modos. Em 26/10, foram **8/12** no padrão, **11/12** na proteção legada e **12/12** no pós-preenchimento. A operação **#182** foi conferida diretamente contra o CSV privado por entrada, saída, lado, preço e quantidade. Também ficou exata com continuidade e a opção de entrada ativa. Os 26 arquivos de referência ficaram idênticos. O teste pareado adicional da v5.7 (continuidade com e sem entrada na lacuna) produziu mais oito comparações idênticas. [Matriz v5.7](regressao_v5_7.csv)

**89 testes passaram**, com 12 avisos de timezone do pandas já conhecidos. Os 14 novos casos de teste cobrem os três cenários sintéticos da V3, a preservação de compra e venda a mercado, a exclusão de entrada limite/stop e de saída a mercado via `SendOrder`, elegibilidade com latência, troca de pregão, leitura exclusiva do fechamento anterior na extra e horários da barra de replay e do contexto. A CLI também foi testada nos dois modos incompatíveis e retornou código 2, sem criar pastas de replay.

## Sondas S1 e S2 no Profit

As duas sondas estão prontas para o **Backtest OHLC** e ainda precisam ser executadas no Profit. Use WINZ26, 1 minuto, 26/10/2026, lote e máximo 1, slippage e custos zero, execução nos limites e sem zeragem horária externa nas janelas indicadas. As janelas são de barras consecutivas nas barras preparadas. Confira a mesma sequência no histórico efetivamente usado pelo Profit. Use uma execução independente por sonda e variante.

- **S1, validade sem renovação.** Compra solicitada no contexto 13:15. Envia alvo e stop uma só vez em 13:16, a +2.000 e −2.000 pontos da entrada, com folga de 500. Os níveis ficam fora da faixa das barras de 13:17 a 13:20. Observe `HasPendingOrders` nesses quatro rótulos. O encerramento do controle pede cancelamento às 13:21 se ainda houver pendências e zeragem às 13:22. No simulador, a presença registrada é **1, 0, 0, 0**. Se o Profit mostrar pendências a partir de 13:18, isso estabelece persistência além da primeira barra elegível no cenário. A identificação das duas pernas depende dos IDs. [NTSL S1](sonda_s1_validade_profit_v1_0.ntsl)
- **S2, stop-limit com abertura abaixo do gatilho.** A sonda calcula o gatilho como fechamento da barra de envio menos cinco pontos e limite 500 pontos abaixo do gatilho, sem renovação. Em `p_Variante=1`, envia às 13:45 e a primeira barra, 13:46, cobre o gatilho. Em `p_Variante=2`, envia às 15:28; a máxima de 15:29 fica abaixo do gatilho e 15:30 cobre esse preço. As primeiras barras abrem cinco pontos abaixo do gatilho e acima do limite. O simulador preenche na primeira abertura em ambas. O resultado nativo determinará em qual barra e a que preço o Profit preencheu, ou se o stop expirou. Compare com S1 antes de atribuir a diferença a uma fórmula de disparo. [NTSL S2](sonda_s2_stop_limit_profit_v1_0.ntsl)

O replay local das sondas converteu somente a formatação de ConsoleLog para a sintaxe do interpretador. As janelas e condições relativas estão na matriz. O procedimento de coleta descreve os campos necessários e a janela de cada variante. [Janelas e controles locais](sondas_barras_comuns.csv) · [Exportações do Profit](exportacoes_profit.md)

## Comandos de reprodução

Use destinos novos e os mesmos insumos privados dos relatórios de referência. Para o controle V3, escolha o JSON do caso 0, 1 ou 2. Para a v5.8, use o NTSL de auditoria v1.0 e o JSON da validação; para a v5.7, use o NTSL original, `p_Lote=1` e a barra preparada do respectivo pregão.

```powershell
$cli = @('--segundos','60','--formato','ohlc','--tick','5','--valor-ponto','0.2','--rastrear-ordens')
$extra = @('--avaliacao-pos-preenchimento')
$hist = @('--historico-continuo-lacunas')
$entrada = @('--historico-continuo-lacunas','--entrada-mercado-atraves-lacuna')
$paridade = @('--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas')
# Para os três cenários da V3, $flags recebe @(), $hist ou $entrada.
py -3.11 estrategia.py --csv $barrasV3 --ntsl $sondaSimulador --inputs $jsonCaso `
  --saida $saidaV3 @cli @extra @flags
# Para cada cenário v5.8, repetir com @(), $hist e $entrada.
py -3.11 estrategia.py --csv $barrasComPregaoAnterior --ntsl $auditoriaV58 --inputs $jsonV58 `
  --saida $saidaV58 @cli @paridade @extra @flags
py -3.11 tools/comparar_v5_8.py --data $dia --aquecimento 63 `
  --console-profit $consoleProfit --operacoes-profit $operacoesProfit --barras-profit $barrasProfit `
  --barras-preparadas $barrasComPregaoAnterior --console-simulador "$saidaV58/console.csv" `
  --candles-simulador "$saidaV58/candles.csv" --execucoes-simulador "$saidaV58/execucoes.csv" --saida $comparacao
# v5.7: $modoV57 é @(), @('--protecao-no-candle-entrada') ou $extra.
# Para o pareado adicional, usar $extra e acrescentar $hist ou $entrada.
py -3.11 estrategia.py --csv $barrasV57 --ntsl estrategias/execucao/Modelo_Unificado_Refatorado_v5_7.ntsl `
  --inputs $jsonV57 --saida $saidaV57 @cli @paridade @modoV57
py -3.11 -m pytest -q
```

A lista de pendências mantém a vida das proteções, disparo, preenchimento e OCO a cargo da coleta nativa. Os dados brutos continuam no Windows. O PR permanece em rascunho. [Fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto](SHA256SUMS.txt)
