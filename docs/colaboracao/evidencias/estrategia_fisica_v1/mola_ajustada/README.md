# Rodada 3 da pesquisa Física · mola ajustada e reteste em amostra inédita (sintético)

**Pedido:** ajustar a mola para deixar passar as entradas vencedoras. Na rodada 2, a mola da v5.8 cortou justamente as entradas que deram lucro no teste.

## Diagnóstico (v5.8 original na amostra da rodada 2)

| Entradas esticadas a favor (x > 2 no sentido da entrada) | Treino | Teste antigo |
|---|---|---|
| Todas | 33 operações, −R$ 2.146 | 22 operações, +R$ 634 |
| Com deriva do dia a favor > 1 | 7 operações, +R$ 398 | 15 operações, +R$ 904 |
| Com deriva do dia a favor entre 0 e 1 | 24 operações, −R$ 2.256 | 7 operações, −R$ 270 |

Deriva do dia em unidades de difusão: **z = (Close − abertura do pregão) / (σ · √n)**, com σ igual à temperatura da barra e n o número de barras desde a abertura. É o deslocamento do dia comparado ao que um passeio aleatório produziria.

Leitura: a entrada esticada ganha quando o dia tem deriva forte a favor, porque ali a mola "rompeu" e há tendência. Quando a deriva é fraca, o preço volta.

No conjunto de todas as entradas, as que tinham deriva a favor entre 0 e 1 perderam −R$ 7.808 no treino e −R$ 1.074 no teste antigo. As que tinham deriva acima de 1 ganharam nos dois períodos.

## Ajuste (Física v1.1, desligado por padrão)

| Opção | Regra |
|---|---|
| `p_FisMolaDeriva=1` (mola ajustada) | a mola só bloqueia a entrada esticada se a deriva do dia a favor for menor que `p_ZDia` |
| `p_FisDeriva=1` (filtro de deriva) | bloqueia a entrada se a deriva do dia a favor estiver entre 0 e `p_ZDia` |

As fontes novas preservam a v1.0. Com tudo desligado, os fills são idênticos ao original (`tests/test_fisica_mercado.py`):

| Fonte | SHA-256 |
|---|---|
| `estrategias/pesquisa/Modelo_Unificado_v5_8_fisica_v1_1.ntsl` | `cfdd97aa…` |
| `estrategias/pesquisa/modelo_scalper_v1_1_fisica_v1_1.ntsl` | `8877e8cb…` |
| `estrategias/pesquisa/pullback_tendencia_v1_2_fisica.ntsl` | `a2b858b9…` |

## Por que uma amostra inédita

O ajuste foi desenhado olhando para os 60 pregões da rodada 2, incluindo o antigo teste, que portanto deixou de ser teste. Os 60 pregões viraram **desenvolvimento**. O reteste usa **60 pregões novos**, nunca vistos: gerador v2, semente 20261202, CSV `db1b7b63…`. Há também um **controle nulo** com a mesma semente nova: gerador v0, CSV `6600d4c7…`.

As variantes fixas foram registradas antes de rodar a amostra nova:

| Variante | Configuração |
|---|---|
| `mola_v10` | x > 2 bloqueia |
| `mola_ajustada` | x > 2 bloqueia só com deriva a favor < 1 |
| `deriva` | bloqueia entradas com deriva a favor entre 0 e 1 |
| `mola_ajustada_deriva` | as duas |

Além delas, 30 variações sorteadas (semente 7). A escolhida é a de maior líquido no desenvolvimento.

**Cada pregão foi testado 35 vezes por modelo em cada amostra**, ou seja, 315 replays por pregão no total. As tabelas `por_pregao_*.csv` trazem a distribuição. A ferramenta é `tools/retestar_mola_holdout.py`.

## Resultado na amostra inédita (diferença diária em relação ao original, IC 95% por bootstrap de pregão)

| Modelo | Original | Mola v1.0 | Mola ajustada | Deriva | Mola ajustada + deriva | Escolhida no desenvolvimento |
|---|---|---|---|---|---|---|
| v5.8 | −R$ 2.254 | −R$ 766; +24,80 (6,13; 44,50) | −R$ 864; +23,17 (8,30; 39,87) | **R$ 2.702; +82,60 (38,60; 130,10)** | **R$ 2.722; +82,93 (38,92; 130,12)** | R$ 3.060; +88,57 (43,30; 137,07) |
| Scalper v1.1 | −R$ 4.820 | −R$ 3.712; +18,47 (3,33; 33,23) | −R$ 4.080; +12,33 (0,80; 23,94) | −R$ 2.280; +42,33 (23,57; 63,93) | −R$ 2.094; +45,43 (25,30; 67,40) | −R$ 1.870; +49,17 (26,20; 71,63) |
| Pullback v1.0 | −R$ 1.381 | −R$ 1.065; +5,27 (0,00; 11,13) | −R$ 1.331; +0,83 (−2,72; 4,73) | **R$ 508; +31,48 (14,23; 49,39)** | R$ 437; +30,30 (13,51; 48,02) | −R$ 29; +22,53 (−3,15; 47,75) |

Detalhes da v5.8 na amostra inédita:

| Variante | Operações | Acerto | Drawdown |
|---|---:|---:|---:|
| Original | 257 | 45,5% | R$ 4.012 |
| Deriva | 185 | 51,9% | R$ 1.238 |

## Controle nulo (mesma semente nova, sem estrutura)

| Modelo | Mola ajustada | Deriva | Mola ajustada + deriva |
|---|---|---|---|
| v5.8 | −9,93 (−30,40; 9,37) | +8,80 (−44,63; 60,77) | +8,53 (−46,87; 61,27) |
| Scalper v1.1 | +10,40 (−1,83; 23,70) | +18,13 (−3,20; 43,53) | +23,97 (0,63; 50,83) |
| Pullback v1.0 | +1,83 (−2,05; 6,23) | +0,73 (−13,67; 16,02) | +1,75 (−13,05; 16,80) |

## Leitura

1. **A mola ajustada sozinha não resolveu.** Na amostra inédita ela empata com a mola v1.0 na v5.8 e fica abaixo dela na Scalper. Condicionar a mola à deriva liberou entradas, mas não as certas.
2. **A variável que funcionou foi a própria deriva do dia, usada como filtro.** Ela melhorou os três modelos na amostra inédita, com IC acima de zero. A v5.8 passou de −R$ 2.254 para R$ 2.702, com o acerto subindo de 45,5% para 51,9% e o drawdown caindo de R$ 4.012 para R$ 1.238.
3. **No nulo o efeito some.** Nenhum IC da deriva sozinha exclui zero, então o ganho não vem só de operar menos e pagar menos custo. Na Scalper, a combinação com a mola fica no limite (0,63), coerente com a mola cortando operações de um modelo que perde por custo.
4. **Ressalva principal:** o gerador v2 tem exatamente o mecanismo que a deriva mede. Os dias laterais revertem à abertura e os dias de tendência têm deriva constante. O resultado prova que a regra detecta esse mecanismo sem informação futura, mas **não prova que o WIN real se comporte assim**.

## Recomendação

- Manter `p_FisDeriva=1` com `p_ZDia=1` como candidato, não como versão adotada.
- Validar primeiro no WINZ26 real, como cenário pareado com a v5.8 original congelada, pelo protocolo da rodada 20 e sem reotimizar `p_ZDia`.
- A mola ajustada pode ser descartada.

## Reprodução

```bash
python -m tools.retestar_mola_holdout --saida <dir>
python -m pytest -q tests/test_fisica_mercado.py
```
