# Filtro de deriva do dia na v5.8: teste pareado no WINZ26 real

**Base:** `win_60s.csv` congelado da rodada 18, SHA-256 `ed9230c941c186e81fb06a50c79755d4f4b0317d76ddf6bdf84be2e6773cd9d7`, conferido pela ferramenta antes de rodar. A base ficou fora do Git.

**Código:** commit `28fee16`, fonte `Modelo_Unificado_v5_8_fisica_v1_1.ntsl` (SHA-256 `cfdd97aa…`), regras e perfil da v5.8 original congelados na rodada 20, 2 contratos.

**Paridade:** com o filtro desligado, a execução reproduz exatamente a v5.8 original da rodada 18: R$ 1.902 nos 20 pregões conhecidos e R$ 342 nos 19 de desenvolvimento.

**Desenho:** 12 variantes por pregão (`por_pregao_*.csv`). A **variante primária, pré-registrada, é `deriva_z1`**. As outras são sensibilidade e não mudam a decisão. A reserva inédita não foi tocada.

## Resultado (diferença diária em relação ao original, IC 95% por bootstrap de pregão)

| Variante | 20 conhecidos | 19 de desenvolvimento |
|---|---|---|
| original | 147 operações, 51,7% de acerto, R$ 1.902, fator 1,21, drawdown R$ 2.352 | 91 operações, R$ 342, drawdown R$ 1.230 |
| **deriva_z1 (primária)** | 113 operações, R$ 1.714, fator 1,26, drawdown R$ 1.372; **−9,40 (−123,23; 107,13)**; 6 dias melhores e 9 piores | 63 operações, R$ 1.232, drawdown R$ 432; +46,84 (−25,06; 121,27) |
| deriva_z0_5 | R$ 3.388; +74,30 (−4,62; 158,43) | R$ 842; +26,32 (−30,53; 81,27) |
| deriva_z0_75 | R$ 2.442; +27,00 (−67,10; 129,60) | R$ 1.102; +40,00 (−27,16; 105,69) |
| deriva_z1_5 | R$ 944; −47,90 (−195,41; 91,83) | R$ 1.112; +40,53 (−34,63; 114,66) |
| mola_v10 | R$ 1.172; −36,50 (−156,10; 82,80) | R$ 34; −16,21 (−91,48; 67,28) |
| mola_ajustada | R$ 1.666; −11,80 (−111,71; 87,70) | R$ 404; +3,26 (−73,37; 90,95) |
| temperatura | **R$ 134; −88,40 (−151,01; −30,50)** | R$ 646; +16,00 (−34,53; 82,85) |

## Decisão

- **O filtro de deriva não é adotado.** A variante primária não melhorou o resultado dos 20 conhecidos, e o IC é largo e centrado perto de zero. Ela reduziu o drawdown de R$ 2.352 para R$ 1.372, mas com menos operações. No desenvolvimento a melhora também não é significativa.
- **O z = 0,5 foi o melhor nos conhecidos, mas não serve como decisão.** Ele foi escolhido depois de ver o resultado, o IC toca zero e no desenvolvimento ele é o pior dos filtros de deriva. Trocar a variante agora seria sobreajuste.
- **A temperatura piora a v5.8 nos dados reais**, com IC inteiramente negativo nos conhecidos. A hipótese de alvo e stop pela volatilidade fica descartada para a v5.8.
- **O efeito forte do sintético não se repetiu no WIN real.** Como previsto na ressalva da rodada 3, o gerador tinha exatamente o mecanismo que o filtro mede.

## Reprodução

```powershell
py -3.11 -m tools.testar_deriva_real --base <win_60s.csv da rodada 18> --saida <pasta>
```
