# Estratégia pullback de tendência · protocolo fora da amostra (dados sintéticos)

**Resultado:** o protocolo fora da amostra está implementado, testado e reprodutível. A estratégia **foi rejeitada**: nenhuma das 50 variações teve resultado líquido positivo no treino, e a escolhida perdeu no teste (−R$ 457; IC 95% da média diária entre −R$ 46,56 e −R$ 4,39). A precisão por classe ficou no nível da taxa base.

> **Dados sintéticos.** As barras saem de `tools/gerar_win_sintetico.py`. Nada aqui mede desempenho no mercado real nem usa dados do Profit. O objetivo é exercitar o protocolo exigido pela frente Estratégias em [DIRETRIZES_PROJETO.md](../../../../DIRETRIZES_PROJETO.md).

## O que foi congelado antes de rodar

Tudo está em [protocolo.json](protocolo.json):
- **Estratégia:** [`pullback_tendencia_v1_0.ntsl`](../../../../estrategias/pesquisa/pullback_tendencia_v1_0.ntsl). Compra com média rápida acima da lenta e subindo, mínima tocando a média rápida e fechamento de alta acima dela; venda simétrica.
- **Saídas:** alvo limite, stop-limit, tempo máximo de posição e zeragem às 17:45.
- **Riscos:** 1 contrato, perda diária máxima em reais, máximo de entradas por dia e espera depois de cada saída. Os níveis ficam sempre na grade de 5 pontos.
- **Divisão cronológica:** 42 pregões de treino seguidos de 18 de teste. O teste é usado uma única vez, depois da escolha.
- **Execução:** motor OHLC padrão (ordem só na barra seguinte, saída adversa em barra ambígua), R$ 0,50 por contrato e lado, slippage de 1 tick em ordens a mercado e stops.
- **Rótulos:** a partir da abertura da barra seguinte à decisão. **C** se +150 pontos vier antes de −150 em até 30 barras; **V** no caso inverso; **N** se nenhum vier. Toque duplo na mesma barra é **ambíguo** e horizonte cortado pelo fim do pregão é **inválido**; os dois casos ficam fora das matrizes.
- **Variações:** 50 sorteadas com semente fixa, sendo a primeira os padrões do NTSL. Espaço: médias, alvo, stop, tempo máximo, entradas por dia, espera e horário inicial.
- **Seleção:** maior resultado líquido no treino, com pelo menos 42 operações, e desempate pelo menor drawdown.
- **Incerteza:** intervalo de Wilson para precisão e sensibilidade, e bootstrap por pregão (2.000 reamostragens) para a média diária.

## Rodada 2 · resultado oficial (gerador v2)

Escolhida: **variação 30**. Parâmetros: `p_Rapida` 20, `p_Lenta` 21, `p_Alvo` 200, `p_Stop` 300, `p_TempoMax` 15, `p_MaxEntradasDia` 2, `p_Espera` 3 e `p_HoraInicio` 1000.

| Métrica | Treino (42 pregões) | Teste (18 pregões) |
|---|---:|---:|
| Operações (por pregão) | 84 (2,0) | 36 (2,0) |
| Resultado líquido | −R$ 137,00 | **−R$ 457,00** |
| Média diária (IC 95% bootstrap) | −R$ 3,26 (−17,93 a 11,72) | −R$ 25,39 (**−46,56 a −4,39**) |
| Drawdown líquido | R$ 569,00 | R$ 552,00 |
| Pregões positivos / negativos | 23 / 19 | 6 / 12 |
| Acerto das operações | 50,0% | 36,1% |
| Exposição (barras posicionadas) | 4,6% | 5,1% |
| Precisão C (taxa base) [IC 95%] | 48,8% (43,3%) [34,3–63,5] | 40,0% (42,1%) [19,8–64,3] |
| Precisão V (taxa base) [IC 95%] | 44,2% (44,7%) [30,4–58,9] | 47,6% (47,2%) [28,3–67,6] |
| Sensibilidade C / V | 0,21% / 0,19% | 0,15% / 0,22% |
| Resultado dos falsos positivos C / V | −R$ 609 / −R$ 539 | −R$ 293 / −R$ 438 |

No teste, as saídas foram 28 por tempo máximo ou zeragem a mercado, 5 no alvo e 3 no stop. Não houve barra ambígua na execução. A matriz de confusão completa está em [`rodada2_gerador_v2/resultado.json`](rodada2_gerador_v2/resultado.json). A sensibilidade é baixa por construção: a estratégia sinaliza poucas barras, enquanto quase todas as barras válidas pertencem a C ou V.

**Diagnóstico do viés de seleção** (feito só depois da escolha, sem alterá-la; ver [`diagnostico_selecao_teste.csv`](rodada2_gerador_v2/diagnostico_selecao_teste.csv)):
- **Treino:** 0 de 50 variações positivas.
- **Teste:** 16 de 50 positivas.
- **Correlação de postos treino × teste (Spearman):** −0,0006.
- **A escolhida:** ficou em 45º de 50 no teste.

O desempenho no treino não prevê o do teste. É o comportamento esperado quando não existe vantagem a explorar.

**Composição dos regimes** ([`regimes_gerador.csv`](rodada2_gerador_v2/regimes_gerador.csv)): o treino tem 12 de 42 dias de tendência e o teste tem 11 de 18. O teste ficou mais tendencial por acaso. A estratégia perdeu nos dois regimes (tendência −R$ 185; lateral −R$ 272).

**Conferência independente:** o replay pela CLI (`estrategia.py --inputs` com a variação 30, custos e slippage do protocolo) somou, nos pregões de teste, −R$ 457,00, 36 saídas e −2.105 pontos. São os mesmos números da ferramenta.

## Rodada 1 · gerador v1 (registrada, não usada como resultado)

A primeira execução usou o gerador v1, cuja deriva nos dias de tendência produzia movimentos de cerca de 5% (mediana de 5.198 pontos por pregão no teste), irreais para o WIN. Naquela rodada, as 50 variações ficaram positivas no teste porque os dados premiavam qualquer seguidor de tendência. A falha estava no gerador, não na estratégia.

O gerador v2 reduz só a deriva (de 1% a 2% num dia de tendência) e mantém a mesma semente e os mesmos sorteios de regime. Estratégia, divisão, rótulos, variações e seleção não mudaram. Os agregados da rodada 1 e o protocolo 1.0 estão em [`rodada1_gerador_v1/`](rodada1_gerador_v1/).

## Reprodução

```bash
python -m tools.avaliar_fora_amostra \
  --protocolo docs/colaboracao/evidencias/estrategia_pullback_fora_amostra_sintetico_v1/protocolo.json \
  --saida resultados/pullback_v1
python -m pytest -q tests/test_avaliar_fora_amostra.py
```

O CSV gerado não é versionado. SHA-256 esperados:

| Arquivo | SHA-256 |
|---|---|
| `win_sintetico.csv` (gerador v2, semente 20261124, 60 pregões) | `c1984b621d25627659748642c1a47e2e2267e158fc5c00b7154b6962ae1ed161` |
| `estrategias/pesquisa/pullback_tendencia_v1_0.ntsl` | `9d5dd028907c3d4aed2b1fddc2a1a1631d6eee515b4c9096de5554d45b8a9dd7` |
| `protocolo.json` (1.1) | `d0e61be6708f62b87186ba0da0d1e983d07c4c07f0749a1bd7f2f0c99a3b2a2d` |

## Limites e próximo passo

- Dados sintéticos com tendência e reversão sorteadas por dia. Eles não reproduzem a microestrutura, o leilão de abertura nem as lacunas reais.
- Um único corte treino/teste. Com dados reais, convém validação deslizante (walk-forward) com vários cortes e reserva final local intacta, como manda a diretriz.
- O mesmo protocolo roda sem mudanças num CSV OHLC real (`--csv`), por exemplo uma exportação de barras de 1 min do Profit. O próximo passo é aplicá-lo a pregões WINZ26 reais, mantendo os brutos fora do Git e publicando só agregados.
