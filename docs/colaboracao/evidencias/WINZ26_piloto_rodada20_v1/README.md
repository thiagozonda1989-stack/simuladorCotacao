# Rodada 20 · resultado do piloto WINZ26 em 24/11/2026

O piloto executou uma vez cada perfil congelado. A comparação usa **um pregão avaliado**, 24/11/2026. As 562 barras do dia 23/11 entraram como aquecimento e seus resultados foram excluídos dos agregados. Os dois pregões ficam fora da amostra formal futura. O Replay visual do Profit foi usado para confirmar a abertura do aquecimento. As estratégias foram executadas no simulador OHLC. [Protocolo publicado antes da execução](PROTOCOLO_PRE_REPLAY.md) · [Amostra e hashes](amostra.json)

| Perfil | Operações | Acerto | Líquido no pregão | Fator de lucro líquido | Drawdown realizado | Duração mediana | P90 |
|---|---:|---:|---:|---:|---:|---:|---:|
| v5.8 original | 10 | 3/10 (30,0%) | −R$ 676 | 0,32937 | R$ 706 | 11 min | 47 min 24 s |
| Scalper v1.1 otimizada | 8 | 7/8 (87,5%) | +R$ 142 | 3,21875 | R$ 64 | 2 min | 7 min |

A v5.8 encerrou sete operações por stop-limit, duas no alvo e uma na janela de notícia. A Scalper encerrou cinco operações no alvo, duas pelo limite de duração e uma por stop-limit. A posição máxima foi de dois contratos nos dois perfis. O motor registrou zero barras com ambiguidade de preenchimento no pregão avaliado. A diferença de líquido entre os perfis foi de R$ 818 a favor da Scalper no único pregão. [Agregados e critérios](resultado.json)

A v5.8 ficou 15 pontos percentuais abaixo da referência de 45% de acerto. A Scalper ficou 42,5 pontos percentuais acima. Em relação à referência de R$ 3.000 líquidos por pregão, ficaram abaixo em R$ 3.676 e R$ 2.858, respectivamente. O piloto é descritivo para ambos. A avaliação de aprovação exige 20 pregões inéditos completos e pelo menos 80 operações por perfil.

O motor começou 24/11 com `CurrentBar=563`, 562 barras anteriores disponíveis e `Date[1]` correspondente ao pregão de 23/11. `barras_no_segmento=1` marca a primeira barra da sessão. Nenhuma lacuna intradiária foi assinalada na virada. A entrada privada preparada foi conferida pelo SHA-256 publicado antes da execução. Slippage de 1 tick está nos preços de preenchimento. O custo de R$ 0,50 por contrato e lado já está no líquido apresentado.

**SHA executado** `599e3f0f84a570c345a63e6c52f7a7bc4e677ab1`. **Motor** `db9ace693c9396d87198e0973d9708ddeb7668d4`. A suíte local passou com 145 testes. Os originais, a imagem e os dados intermediários permanecem no Windows. [Hashes das publicações](SHA256SUMS.txt)
