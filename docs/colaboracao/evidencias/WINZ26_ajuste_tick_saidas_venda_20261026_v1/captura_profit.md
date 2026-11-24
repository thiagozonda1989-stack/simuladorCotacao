# Captura no Profit · G3, G4 e limite do stop-limit

## G3 e G4 · posição vendida

Use **Profit Backtest OHLC**, WINZ26, 1 minuto, análise de **26/10/2026 a 26/10/2026**. Configure quantidade e máxima em **1**, custos e slippage em **zero** e **Executar nos Limites** ativo. Deixe desativados os filtros e a zeragem por horário na janela de 10:51 a 10:58. Inicie cada execução zerado e sem pendências. A interface deve mostrar **OHLC** selecionado no seletor **OHLC/Tick a Tick**.

| Parâmetro | G3 | G4 |
|---|---:|---:|
| `p_Data` | 1261026 | 1261026 |
| `p_Entrada` | 1051 | 1051 |
| `p_Protecao` | 1052 | 1052 |
| `p_Cancela` | 1056 | 1056 |
| `p_Zera` | 1057 | 1057 |
| `p_Fim` | 1058 | 1058 |
| `p_Alvo` | **877** | — |
| `p_Gatilho` | — | **447** |
| `p_Limite` | — | **1000** |

1. Abra cada arquivo no Editor de Estratégias e compile como estratégia de execução. Compare o painel com a tabela antes de iniciar o Backtest. [G3](g3_alvo_compra_grade_profit_v1_0.ntsl) · [G4](g4_stop_compra_grade_profit_v1_0.ntsl)
2. Execute cada sonda separadamente. A venda a mercado é solicitada no rótulo **10:51**; os quatro controles locais preencheram na abertura de **10:52**. A partir do preço da venda, no rótulo **10:52**, G3 envia uma única recompra limite `BuyToCoverLimit(SellPrice - 877, 1)`; G4 envia `BuyToCoverStop(SellPrice + 447, SellPrice + 1000, 1)`. Se necessário, a limpeza é solicitada em 10:56 e 10:57.
3. Exporte o **console Debug completo** de cada execução. Preserve a ordem física, avisos e blocos repetidos. O console traz `GRADE_G3` ou `GRADE_G4`, data, hora, barra, sequência, posição, pendências, OHLC e os níveis solicitados com `SellPrice` de referência.
4. Na aba **Operações**, exporte um **CSV** com ativo, lado, quantidade, horários de entrada e saída e preços. Exporte também o PDF do relatório e, se disponível, o CSV de barras de 10:51 a 10:58.
5. Salve um **print de configuração por execução** com o seletor OHLC/Tick a Tick inteiro, OHLC selecionado, ativo, período, data, quantidade, parâmetros, custos e slippage. Se necessário, capture duas imagens da mesma execução. Identifique arquivos com `G3_877` e `G4_447_1000`, por exemplo `G3_877_console.txt`, `G3_877_operacoes.csv` e `G3_877_config.png`.

A abertura de 10:55 fica **+220 pontos** acima do preço de entrada, a máxima é **+445** e a mínima é **−875**. A posição vendida só pode tocar os níveis em disputa a partir dessa barra. A hipótese de tick mais próximo prevê G3 a **−875** na mínima, com ganho de 875 pontos, e G4 a **+445** na máxima, com perda de 445 pontos. Nos controles locais, os níveis brutos permanecem pendentes às 10:55 e a recompra de limpeza ocorre às 10:58, a −375 pontos de preço relativo. Os controles na grade reproduzem a geometria esperada. A confirmação nativa está pendente. [OHLC relativo](barras_referencia.csv) · [Replays G3 e G4](sondas_g3_g4_simulador.csv)

## Aceitação do gatilho −793 e do limite −894 da sonda 03

1. Repita **03, stop controle**, com a sonda de prioridade já publicada. Use o Backtest OHLC acima, `p_Perna=2`, `p_SaidaMercado=0`, `p_Stop=793` e `p_Folga=101`. A compra é solicitada em 10:51 e a proteção em 10:52, sem zeragem concorrente. No console, confira o gatilho **−793** e o limite **−894**, ambos em relação ao preço real da compra. [NTSL da sonda 03](../WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1/sonda_prioridade_mercado_protecao_profit_v1_0.ntsl)
2. Procure no histórico de ordens **da mesma execução** o registro original do stop-limit enquanto pendente, antes de eventual conversão. Exporte o identificador, estado, hora e tipo da ordem, campos de gatilho e limite, e os registros de execução/cancelamento vinculados. Preserve a resolução original dos horários.
3. Se a captura só estiver disponível no **Replay**, execute separadamente em simulação. Identifique os arquivos com `03_stop_793_894_replay`, guarde o console e as operações dessa rodada e exporte a lista que mostre os valores aceitos. Se possível, capture antes do disparo e depois dele, com os vínculos. Compare sempre os níveis em relação à entrada do **próprio Replay**.
4. Registre os campos aceitos que estiverem presentes. O gatilho pode ser confrontado com −793 solicitado e os candidatos na grade. Para o limite, confronte o valor aceito com −894 e possíveis ticks vizinhos −895 ou −890. Se houver apenas o preço médio executado ou só o registro da ordem convertida sem os campos originais, o gatilho ou o limite aceito correspondente permanece indeterminado. A evidência do Replay caracteriza aquele modo.

Conserve os originais no Windows para sanitização e publicação dos derivados.
