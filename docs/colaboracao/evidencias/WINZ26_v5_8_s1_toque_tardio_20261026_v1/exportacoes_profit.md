# Exportações do Profit · S1-Alvo e S1-Stop

Em Backtest OHLC, execute cada sonda com os parâmetros descritos no [relatório](README.md#configuração-das-duas-sondas). Use o mesmo pregão e oito barras consecutivas de **10:51 a 10:58 de 26/10/2026**. Comece cada execução zerada e sem pendências. Preserve os arquivos privados em seus formatos originais.

| Prefixo | Sonda | Proteção única |
|---|---|---|
| `s1_alvo_toque_tardio` | [NTSL de alvo](sonda_s1_alvo_toque_tardio_profit_v1_0.ntsl) | Alvo +430 pontos |
| `s1_stop_toque_tardio` | [NTSL de stop](sonda_s1_stop_toque_tardio_profit_v1_0.ntsl) | Gatilho −795 e limite −895 pontos |

Acrescente estes sufixos ao prefixo de cada execução.

| Sufixo | Conteúdo |
|---|---|
| `_console.txt` | Todas as linhas `SONDA_S1_ALVO;` ou `SONDA_S1_STOP;` e os avisos do Profit. Preserve ordem, sequências, rótulos repetidos, posição, pendências, OHLC e níveis. |
| `_barras.csv` | WINZ26, 1 minuto, fuso, data/hora, abertura, máxima, mínima e fechamento das barras 10:51–10:58. |
| `_operacoes.csv` | Relatório do mesmo backtest com número ou ID, ativo, lado, quantidade, preços e horários de entrada e saída. Preserve os segundos e os cabeçalhos. |
| `_config.txt` ou captura | Build do Profit, modo OHLC, intervalo, lote e máximo, slippage, custos, execução nos limites e valores dos parâmetros. |
| `_ordens.csv`, se disponível | Histórico nativo do mesmo backtest, com IDs e IDs substituídos, estados e motivos, tipo/lado, quantidades, preços e timestamps subminuto dos eventos de aceitação, execução, expiração ou cancelamento. Inclua IDs/vínculo OCO quando o relatório apresentar esse campo. |

A configuração de cada sonda envia uma única proteção, sem par OCO previsto. Caso o histórico nativo esteja indisponível, o console e a operação exportada permitem observar a pendência e o horário de preenchimento. A identidade da ordem e o motivo de um eventual desaparecimento continuam dependentes da linha de estado nativa.
