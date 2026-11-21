# Coleta nativa das sondas S1 e S2

Use o Editor de Estratégias em Backtest OHLC. Execute S1 uma vez e S2 duas vezes, com `p_Variante=1` e `p_Variante=2`. Use estes prefixos de arquivo local e a janela indicada.

| Execução | Prefixo | Janela de coleta |
|---|---|---|
| S1 | `sonda_s1` | 26/10/2026, 13:15–13:23 |
| S2, variante 1 | `sonda_s2_variante1` | 26/10/2026, 13:44–13:50 |
| S2, variante 2 | `sonda_s2_variante2` | 26/10/2026, 15:27–15:33 |

Para cada prefixo, preserve os seguintes arquivos privados:

| Sufixo | Dados |
|---|---|
| `_console.txt` | Linhas `SONDA_S1;` ou `SONDA_S2;`, mais os avisos do Profit, em ordem de emissão e com rótulo de contexto, CurrentBar, sequência, posição, pendentes e níveis. |
| `_barras.csv` | Ativo, resolução, fuso, data/hora e OHLC de cada barra da janela. |
| `_operacoes.csv` | Operações do mesmo backtest com ID, lado, quantidades, preços e horários de entrada e saída. |
| `_config.txt` ou captura | Build, execução OHLC, intervalo avaliado, quantidade, slippage, custos, execução nos limites e parâmetros da sonda. |
| `_ordens.csv`, se disponível | Eventos do mesmo backtest: IDs e IDs substituídos, vínculo OCO, tipo, lado, quantidade, gatilho, limite, estados e motivos, timestamps subminuto de solicitação, aceitação, renovação, disparo, preenchimento e cancelamento. |

A S1 observa um par de proteções. A S2 envia somente um stop, sem perna OCO. A exportação de uma conta separada não identifica ordens do backtest. Quando o histórico nativo faltar, marque a identidade da ordem e os horários de transição como indeterminados. Preserve os timestamps do console e de execução em colunas distintas.
