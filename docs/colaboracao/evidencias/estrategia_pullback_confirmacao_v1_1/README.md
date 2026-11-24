# Pullback v1.1 · confirmação no fechamento

Motor e baseline do commit `f8098e50689df9c8e4e74e2cd31f91448eb2d4c3`. A candidata exige fechamento além do anterior e nos 35% da amplitude mais favoráveis à direção. As duas versões usaram os parâmetros da variação 30, 1 contrato, R$ 0,50 por lado e slippage de 1 tick no motor OHLC. A comparação usou uma única candidata, sem busca após os resultados.

| Coorte | Operações por versão | Líquido v1.0 | Líquido v1.1 | Diferença |
|---|---:|---:|---:|---:|
| 18 pregões sintéticos já conhecidos | 36 | −R$ 457 | −R$ 468 | −R$ 11 |
| 54 pregões sintéticos novos (três sementes) | 108 | −R$ 689 | −R$ 762 | −R$ 73 |
| WINZ26 real, 21 e 26/10/2026 | 4 | −R$ 147 | −R$ 46 | +R$ 101 |

A meta foi definida como diferença no líquido de pelo menos 10% do módulo do resultado original. No recorte real a perda caiu 68,7%, com toda a melhora concentrada em 21/10. Em 26/10 a diferença foi zero. A taxa de operações positivas passou de 1/4 a 2/4 e o drawdown de R$ 186 a R$ 124. São dois pregões previamente usados para paridade, com 565 e 553 barras. Nos sintéticos novos, a perda aumentou 10,6%; o IC bootstrap de 95% da diferença diária vai de −R$ 6,58 a +R$ 4,13. A v1.1 permanece candidata de pesquisa, sem melhora consistente demonstrada.

## Reprodução

Na raiz, execute `PYTHONPATH=. python tools/comparar_pullback_v1_1.py` para repetir os sintéticos. Para os reais, converta a exportação Profit de CP1252 para UTF-8, filtre os dois pregões, ordene por data e grave CSV separado por ponto e vírgula com `timestamp` ISO8601 e `abertura;maxima;minima;fechamento`. Passe o arquivo em `--csv`. As barras originais permanecem privadas. Os JSONs desta pasta contêm apenas métricas e diferenças diárias agregadas.

Foram executados a comparação, a compilação NTSL pelo simulador e o replay do baseline no recorte sintético conhecido. A compilação no Profit continua pendente.
