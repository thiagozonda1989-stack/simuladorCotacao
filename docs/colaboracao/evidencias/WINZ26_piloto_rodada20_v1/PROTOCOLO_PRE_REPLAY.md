# Rodada 20 · protocolo pré-replay do piloto WINZ26

**Amostra congelada antes do replay em 28/11/2026.** O piloto descritivo mede somente **24/11/2026**. O histórico de aquecimento usa **23/11/2026**, o pregão imediatamente anterior. As duas datas ficam excluídas da futura coorte formal a partir da exposição. A avaliação formal continua exigindo 20 pregões inéditos completos e pelo menos 80 operações por perfil. Os dados e a imagem originais ficam privados. [Datas, cobertura e hashes](amostra.json) · [Protocolo, estratégias, inputs, custos e flags congelados](../WINZ26_decisao_elegibilidade_rodada20_v2/protocolo.json)

## Evidência que permite o piloto

O print de Thiago mostra o gráfico WINZ26 em **1 segundo**, no **Replay de 23/11/2026**, com o primeiro candle do pregão rotulado **09:03:30**. O OHLC e a contagem de negócios no resumo coincidem com a primeira barra do CSV subminuto em ordem cronológica. O gráfico mostra a transição do pregão anterior para essa abertura. Em 09:03, as 30 barras exportadas somam os mesmos preços, Trades, Quantity, volume e agressão da primeira barra de 1 minuto. As duas exportações de 1 minuto começam às 09:03. Essa combinação comprova a primeira barra do histórico do Profit para o piloto descritivo. O primeiro negócio subsegundo, o estado de leilão e a sequência de eventos da bolsa ficam fora dessa verificação. [Reconciliação subminuto](../WINZ26_decisao_elegibilidade_rodada20_v3/README.md)

O OHLC fechado de 18:14 foi corroborado pela agregação de 60 segundos. As 86 barras finais de 23/11 são consecutivas. O arquivo canônico de 1 minuto tem 562 barras de 23/11 e 565 de 24/11, sem lacunas intradiárias. A captura visual anterior corroborou a origem WINZ26 1 minuto de 24/11. A comparação adicional com histórico independente de 24/11 fica documentada como pendência formal. [Parecer Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7152416269) · [Parecer Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7152494885)

## Execução congelada

Motor OHLC `db9ace693c9396d87198e0973d9708ddeb7668d4`. Compilador NTSL `e3f474453e4186c9df83392af9f6fd7284a3e234`. Uma execução por perfil, com v5.8 original em `p_Exec_Tick=0` e Scalper v1.1 otimizada. WINZ26 de 1 minuto, 2 contratos, slippage de 1 tick, custo de R$ 0,50 por contrato e lado e semântica OHLC congelada. A preparação mantém os candles reais, usa agressão exportada, Volume financeiro para NTSL e VWAP por barra derivada de Volume financeiro e Quantity. A VWAP diária é reconstruída pelo motor. O relatório do piloto exclui os resultados do dia de aquecimento.

```powershell
py -3.11 -m tools.piloto_rodada20 --preparar $coleta1Min --entrada-privada $entradaLocal --saida $amostra
py -3.11 -m pytest -q
py -3.11 -m tools.piloto_rodada20 --executar --entrada-privada $entradaLocal --saida $resultadoAgregado
```
