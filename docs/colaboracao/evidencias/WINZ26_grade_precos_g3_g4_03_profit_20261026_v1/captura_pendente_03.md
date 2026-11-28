# Pendência da sonda 03 no Profit

**G3 e G4 estão concluídas no escopo dos exemplos executados.** Para a 03, procure o histórico original da ordem stop-limit do Backtest já executado. A documentação só precisa de uma nova execução se esse histórico não estiver mais acessível e o Profit disponibilizar os campos aceitos durante a execução. O console, o relatório e o CSV de operações já recebidos bastam para confirmar o preenchimento de **−795 pontos relativos à entrada** às **10:55:00**. [Matriz](matriz_profit_simulador.csv)

## Primeira opção · histórico do mesmo Backtest OHLC

1. Abra o resultado da 03 e localize a lista ou os detalhes de ordens vinculados a essa execução. Procure a **ordem de venda stop-limit original** solicitada no contexto 10:52, enquanto estava pendente entre as avaliações de 10:53 e 10:54. Se o registro estiver disponível, capture-o e exporte também a atualização após a saída às 10:55.
2. Exporte a lista de ordens em CSV e faça um print do detalhe da ordem em que apareçam **Preço Stop/Gatilho e Preço/Limite**, o ID da ordem, tipo, lado, quantidade, estado e horários. Inclua horários de criação, disparo e execução e o vínculo entre a ordem original e a ordem executada, se disponíveis. Mantenha a precisão de hora que o Profit mostrar. Use o nome `03_stop_793_894_backtest_ordens.csv` e acrescente um print se o CSV omitir campos visíveis.
3. Caso o resultado anterior tenha se perdido e o Profit permita obter os campos em outra execução do Backtest, use os mesmos parâmetros abaixo. Salve novamente o console Debug, o CSV de operações, os detalhes da ordem e um print da configuração com o seletor OHLC visível. Repetir o Backtest exportando apenas console, operações e relatório produz a mesma limitação.

| Configuração da 03 | Valor |
|---|---|
| Ativo, período e sessão | WINZ26, 1 minuto, 26/10/2026 a 26/10/2026 |
| Execução | Backtest OHLC, quantidade e máximo 1, slippage e custos zero, Executar nos Limites ligado, sem zeragem automática por horário na janela |
| Datas e horários NTSL | `p_Data=1261026`, `p_Entrada=1051`, `p_Protecao=1052`, `p_EnvioMercado=1054`, `p_Limpeza=1056`, `p_Fim=1058` |
| Seleção de perna | `p_Perna=2`, `p_SaidaMercado=0`, `p_Alvo=430` (inativo) |
| Stop-limit de venda | `p_Stop=793`, `p_Folga=101`, solicitando gatilho −793 e limite −894 relativos à compra |

[NTSL versionado da sonda 03](../WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1/sonda_prioridade_mercado_protecao_profit_v1_0.ntsl)

## Se o Profit expuser esses campos apenas no Replay

Em uma execução separada de **Replay com conta de simulação**, use WINZ26 de 26/10/2026, 1 minuto, os parâmetros da 03 acima e inicie antes de 10:51. Enquanto a ordem estiver pendente, pause o Replay em 10:53 ou 10:54 e capture a ordem original. Retome até 10:58, exporte a lista de ordens com os estados e junte o console, o CSV de operações e os prints do modo e dos parâmetros dessa rodada. Use o prefixo `03_stop_793_894_replay`. Verifique os níveis a partir do preço da entrada **da própria rodada**. Este resultado caracteriza o modo Replay, com o preço de entrada e a resolução temporal desse ambiente. Se a interface mostrar somente preço médio de execução ou ocultar o preço limite original, a aceitação desse limite permanece indeterminada.

No Windows, `lista_ordens_s1_stop_replay.csv` e `lista_ordens_s1_alvo_replay.csv` pertencem às sondas S1, com outros níveis e outras estratégias. Os `eventos_ordens.csv` encontrados na comparação de v5.8 foram produzidos pelo simulador. A publicação da 03 mantém a célula de limite aceito vazia enquanto faltar um registro correspondente.

## Complementos para uma ampliação futura da regra

Os exemplos G3/G4 já encerrados praticam ajustes na direção do mercado. Se a etapa seguinte for generalizar a recompra, dois controles adicionais distinguem as hipóteses. Use os [mesmos NTSLs e configuração](../WINZ26_ajuste_tick_saidas_venda_20261026_v1/captura_profit.md), mudando somente um parâmetro por execução.

| Controle complementar | Pedido relativo | Tick mais próximo | Ajuste na direção do mercado |
|---|---:|---:|---:|
| G3 com `p_Alvo=793` | −793 | −795 | −790 |
| G4 com `p_Gatilho=428` e `p_Limite=1000` | +428 | +430 | +425 |

Os dois candidatos de cada linha ficam fora das duas barras intermediárias e dentro da barra de 10:55. Exporte console, CSV de operações, print do seletor OHLC e, se aparecerem, os preços aceitos na lista de ordens. Esses controles só são necessários para ampliar a regra geral. O empate de meio tick e a etapa interna de normalização continuam sem sonda nativa específica.
