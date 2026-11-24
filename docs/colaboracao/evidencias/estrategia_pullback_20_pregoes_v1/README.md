# Rodada 12 · Pullback em 20 pregões

Duas candidatas NTSL derivadas da v1.1. A v1.2 exige inclinação da média rápida na direção do sinal em relação a três barras atrás. A v1.3 exige rompimento da máxima ou mínima anterior no fechamento. Foram comparadas 18 configurações no desenvolvimento, combinando as três versões e seis conjuntos de alvo, stop e duração.

Fonte privada: exportação OHLC do Profit, WINZ26, 1 minuto. Desenvolvimento: 19 pregões anteriores ao teste, com pelo menos 500 barras e fechamento às 18:24. Confirmação: 20 pregões de 19/10 a 18/11/2026, com pelo menos 550 barras e fechamento às 18:24. Excluídos 21 e 26/10, já usados na rodada anterior. Candidata selecionada somente no desenvolvimento entre as elegíveis com pelo menos uma operação por pregão em média e 45% de acerto. O motor e os custos são os da rodada 11.

| Confirmação | v1.1 de referência | v1.3 selecionada |
|---|---:|---:|
| Acerto líquido | 54,8% (23/42) | 35,7% (15/42) |
| Resultado líquido | −R$ 286 | −R$ 331 |
| Drawdown | R$ 421 | R$ 331 |

A configuração escolhida teve alvo de 200 pontos, stop de 150 e duração máxima de 10 barras. Ganhou R$ 488 no desenvolvimento (34/62 acertos), mas na confirmação perdeu R$ 45 a mais. O IC bootstrap de 95% da diferença média diária foi de −R$ 26,35 a +R$ 18,04. A candidata foi rejeitada. O baseline superou 45% de acerto e teve perda líquida. O número de operações excedeu a expectativa de duas entradas por sessão na média. O limite diário do NTSL requer auditoria antes de promover qualquer versão. Os testes foram no simulador OHLC.

Para reproduzir na raiz do repo, com PYTHONPATH apontando para a raiz, execute `python tools/validar_pullback_20.py caminho_do_csv_profit.csv`. O JSON registra as 20 datas e as diferenças diárias. Os candles de origem permanecem privados.
