# Validação formal WINZ26 · verificação de cobertura em 28/11/2026

**Estado: amostra insuficiente para iniciar.** O inventário conferido tem três pregões posteriores à última data do piloto, todos com a abertura ainda por confirmar. A lista de 20 pregões formais permanece por congelar e foram executados zero replays formais. Nenhum resultado por perfil foi medido nessas três datas. [Inventário e hashes das fontes](../WINZ26_inventario_20260908_20261127_v1/manifesto.json) · [Cobertura diária do inventário](../WINZ26_inventario_20260908_20261127_v1/pregoes.csv)

| Pregão | Barras | Rótulos | Lacunas internas | Pendência |
|---|---:|---|---:|---|
| 25/11/2026 | 562 | 09:03–18:24 | 0 | Confirmar a primeira barra histórica de WINZ26 e a cobertura anterior a 09:03. |
| 26/11/2026 | 562 | 09:03–18:24 | 0 | Confirmar a primeira barra histórica de WINZ26 e a cobertura anterior a 09:03. |
| 27/11/2026 | 562 | 09:03–18:24 | 0 | Confirmar a primeira barra histórica de WINZ26 e a cobertura anterior a 09:03. |

Os 20 pregões de desenvolvimento terminam em 18/11. O dia 19/11 já era conhecido. O piloto anterior expôs 23/11 como aquecimento e 24/11 como pregão avaliado, e ambos ficaram excluídos da futura amostra formal. Os dias de setembro e outubro são anteriores ao recorte cronológico da reserva. Mesmo que os três candidatos acima sejam confirmados, ainda faltam **pelo menos 17 pregões inéditos completos**. [Corte do piloto](../WINZ26_piloto_rodada20_v1/amostra.json)

## Exportação necessária

Para 25, 26 e 27/11, conferir no Profit a abertura entre **09:00:00 e 09:03:59**, no contrato WINZ26. Usar a lista histórica de Negócios ou a captura do Replay de 1 segundo com contrato, data, primeiro candle e transição do pregão visíveis. Se aparecerem negócios válidos em minutos ausentes do CSV de 1 minuto, recuperar os candles correspondentes antes de classificar o dia.

Para os demais pregões, exportar o gráfico WINZ26 de **1 minuto** com o indicador `Coleta_Reserva_WINZ26_1Min_V1_0`, incluindo a sessão completa. Manter data e hora, OHLC, Trades, Quantity, Volume financeiro, saldo de agressão e VWAP diária. Preservar a abertura observada e o histórico do pregão imediatamente anterior necessário ao aquecimento. Guardar os CSVs e prints originais no Windows.

## Regra congelada

A v5.8 original e a Scalper v1.1 otimizada usam o mesmo recorte cronológico de **20 pregões inéditos completos**. Congelar datas, fontes, hashes e aquecimento antes da primeira execução. Exigir **80 operações encerradas por perfil** no recorte fixo. Se um perfil ficar abaixo desse mínimo, a conclusão daquele perfil será amostra insuficiente, sem estender a janela após observar o resultado. A configuração existente usa OHLC de 1 minuto, dois contratos, slippage de um tick e R$ 0,50 por contrato e lado. [Parâmetros, motor e critérios](../WINZ26_decisao_elegibilidade_rodada20_v2/protocolo.json)
