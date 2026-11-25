# Variáveis físicas nos modelos conhecidos · rodada 2 da pesquisa Física (sintético)

**Pergunta:** as variáveis que passaram no estudo da rodada 1 melhoram os modelos conhecidos?

**Variáveis aplicadas:**
- **Temperatura:** σ = √(média de r²). Ela previu a amplitude do movimento, com ρ ≈ +0,13. Aqui define alvo e stop como fator × σ × √horizonte, arredondados ao tick, entre 50 e 400 pontos e congelados no sinal.
- **Mola:** x = (Close − média) / desvio. Ela previu reversão, com ρ ≈ −0,10. Aqui bloqueia compra com x > p_XMax e venda com x < −p_XMax.

As outras variáveis (Hurst, entropia, eficiência e Lua) não passaram no estudo e ficaram de fora.

**Fontes novas** (o original fica preservado; com `p_FisTemp=0` e `p_FisMola=0` os fills são idênticos, conforme `tests/test_fisica_mercado.py`):

| Modelo | Fonte | SHA-256 | Perfil base |
|---|---|---|---|
| v5.8 original | `estrategias/pesquisa/Modelo_Unificado_v5_8_fisica_v1_0.ntsl` | `5422ac30…` | parâmetros congelados da rodada 20, 2 contratos |
| Scalper v1.1 otimizada | `estrategias/pesquisa/modelo_scalper_v1_1_fisica_v1_0.ntsl` | `3bc2cb24…` | parâmetros congelados da rodada 20, 2 contratos |
| Pullback v1.0 | `estrategias/pesquisa/pullback_tendencia_v1_1_fisica.ntsl` | `aaa0f07e…` | padrão, 1 contrato |

**Dados:**
- Gerador sintético, semente 20261124, 60 pregões, com a nova opção `microestrutura`. Ela acrescenta negócios, contratos, volume financeiro e saldo de agressão acumulado sem mudar o OHLC, e é o que permite rodar a v5.8 e a Scalper.
- Gerador v2: CSV com SHA-256 `03f05a57…`. Controle nulo v0: `35e95306…`.
- Treino nos 42 primeiros pregões, teste nos 18 últimos.
- Custos de R$ 0,50 por contrato e lado, 1 tick de slippage e regras das rodadas 19/20 (volume financeiro, agressão injetada, histórico contínuo, VWAP contínua).

**Desenho:**
- Por modelo há 31 variações: a variação 1 é o original e as outras 30 ligam temperatura, mola ou as duas, sorteadas com a semente 7 no espaço de `tools/testar_fisica_modelos.py`.
- **Cada pregão foi testado 31 vezes por modelo e por gerador**, ou seja, 186 replays por pregão no total. A distribuição por pregão está em `gerador_*/<modelo>/por_pregao.csv`.
- A seleção usa só o treino: maior líquido com pelo menos metade das operações do original no treino.
- O teste compara a escolhida com o original, pareado por pregão, com IC 95% por bootstrap.

## Resultado no gerador v2

| Modelo | Treino: original → escolhida | Diferença diária no treino (IC 95%) | Teste: original → escolhida | Diferença diária no teste (IC 95%) | Posição da escolhida no teste |
|---|---|---|---|---|---|
| v5.8 | −R$ 4.436 → −R$ 486 | +94,05 (13,25; 170,71) | **R$ 2.022 → −R$ 290** | **−128,44 (−246,78; −16,43)** | 29 de 31 |
| Scalper v1.1 | −R$ 4.062 → −R$ 2.176 | +44,90 (15,14; 76,48) | −R$ 998 → −R$ 1.330 | −18,44 (−54,78; 18,89) | 16 de 31 |
| Pullback v1.0 | −R$ 1.014 → −R$ 401 | +14,60 (1,45; 28,26) | −R$ 270 → −R$ 431 | −8,94 (−28,28; 9,78) | 30 de 31 |

## Controle nulo (gerador v0, sem estrutura)

| Modelo | Diferença diária no treino (IC 95%) | Diferença diária no teste (IC 95%) |
|---|---|---|
| v5.8 | +8,33 (−18,58; 34,76) | −4,78 (−73,33; 63,34) |
| Scalper v1.1 | **+30,10 (11,52; 49,00)** | +5,89 (−21,00; 33,22) |
| Pullback v1.0 | +4,52 (−19,08; 29,19) | +3,89 (−30,00; 38,95) |

## Média por bloco no teste (gerador v2, diagnóstico; não serve para seleção)

| Modelo | Original | Só temperatura | Só mola | Temperatura + mola |
|---|---:|---:|---:|---:|
| v5.8 | R$ 2.022 | R$ 802 | R$ 1.580 | R$ 1.003 |
| Scalper v1.1 | −R$ 998 | −R$ 1.487 | −R$ 1.003 | −R$ 1.373 |
| Pullback v1.0 | −R$ 270 | −R$ 58 | −R$ 240 | R$ 4 |

## Leitura

1. **Nenhuma versão física escolhida pelo treino melhorou o teste.** Na v5.8 a piora é significativa: −R$ 128 por dia, com IC inteiramente negativo.
2. **Os ganhos do treino são, em grande parte, viés de seleção.** No controle nulo, que não tem nada a aprender, a Scalper escolhida também "melhorou" o treino com IC acima de zero. Escolher o melhor entre 31 já produz ganhos dessa ordem.
3. **A mudança de regime entre treino e teste domina.** A v5.8 original perdeu R$ 4.436 no treino e ganhou R$ 2.022 no teste. O filtro da mola reduziu as perdas do treino justamente cortando as entradas que deram lucro no teste.
4. **A única pista consistente é a temperatura no Pullback.** O bloco só-temperatura foi melhor que o original em média no treino (−R$ 874 contra −R$ 1.014) e no teste (−R$ 58 contra −R$ 270), e 20 das 30 variações superaram o original no teste. No nulo, o mesmo bloco piorou o treino e melhorou o teste, então a pista ainda não é robusta.

**Decisão:** não adotar nenhuma das versões físicas. As variáveis continuam como ferramentas de estudo. O próximo passo útil é medir a temperatura nos dados reais de WINZ26, com `tools/estudar_variaveis_fisicas.py`, antes de qualquer nova otimização.

## Reprodução

```bash
python -m tools.testar_fisica_modelos --saida <dir> --versao-gerador 2
python -m tools.testar_fisica_modelos --saida <dir> --versao-gerador 0
python -m pytest -q tests/test_fisica_mercado.py
```
