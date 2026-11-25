# Física do Mercado v1.0 · variáveis físicas e protocolo fora da amostra (sintético)

**Fonte:** `estrategias/pesquisa/fisica_mercado_v1_0.ntsl`, SHA-256 `eafbfb1a406ace66c4cf97e99b6b5ee1af74529641b99b00fea759669817a9f2`, 8.811 bytes.

**Dados:** gerador `tools/gerar_win_sintetico.py`, semente 20261124, 60 pregões de 565 barras de 1 minuto. Foram usadas duas versões:
- **v2:** a mesma base da Pullback v1.0. CSV com SHA-256 `c1984b62…ed161`, o mesmo da rodada 2 da Pullback, o que permite comparar as duas estratégias.
- **v0 (controle nulo, novo):** martingal sem deriva e sem reversão à abertura, mantendo volatilidade em U, GARCH, caudas pesadas e volume. CSV com SHA-256 `5a6f541c…8fbbf`.

Os CSVs são regenerados pelo protocolo e ficam fora do Git.

**Escopo:** dados sintéticos. O resultado não mede desempenho no mercado real.

## Variáveis

Todas são calculadas no próprio NTSL, só com OHLC e volume, e o estudo lê os valores diretamente do motor, para medir exatamente o que a estratégia calcula. N é a janela `p_Janela`; r = Close − Close[1], em pontos.

| Variável | Analogia | Fórmula |
|---|---|---|
| Massa m | inércia | volume / média do volume em N |
| Momento p | quantidade de movimento | média curta de m·r |
| Energia cinética K | ½mv² | média de ½·m·r² |
| Temperatura T | variância como agitação térmica | média de r²; aquecimento = T curta / T longa |
| Entropia S | desordem (Shannon) | entropia dos estados alta/baixa/parado em N, normalizada de 0 a 1 |
| Hurst H | memória de longo prazo | razão de variância VR(q) = Var(Close − Close[q]) / (q·Var(r)); H = 0,5 + ln VR / (2 ln q), limitado a [0, 1] |
| Eficiência E | geodésica / trajetória | \|Close − Close[N]\| / Σ\|r\| |
| Mola x, v, U | oscilador harmônico | x = (Close − média) / desvio; v = x − x[1]; U = ½x² |
| Pressão P | força por área | média de m·CLV, com CLV = (2C − H − L) / (H − L) |
| Fase da Lua | fenômeno natural externo (controle negativo) | ciclo sinódico de 29,53 dias a partir da lua nova de 06/01/2000; só no estudo, não na estratégia |

## Regras da estratégia

O conjunto de regras foi definido antes de qualquer resultado.
- **Regime ordenado:** S baixa, H alto, E alta e sistema aquecendo. Entra no sentido do deslocamento quando pressão e momento concordam.
- **Regime restaurador (mola):** H baixo, |x| grande e x·v < 0. Entra a favor do retorno ao equilíbrio e sai a mercado quando x cruza zero.
- **Saídas:** alvo e stop proporcionais à escala de difusão σ·√(tempo máximo), congelados no sinal e limitados entre 50 e 300 pontos (alvo até 600). Há stop-limit com folga, tempo máximo e zeragem às 17:00.
- **Riscos:** 1 contrato, teto diário com a data guardada em variável (lição da rodada 20), espera depois de cada saída e perda diária máxima.

## Resultado do protocolo

Protocolo: divisão cronológica com 42 pregões de treino e 18 de teste; 50 variações sorteadas no treino; seleção pelo maior líquido no treino (mínimo de 42 operações); uma única avaliação no teste. Custos de R$ 0,50 por contrato e lado e 1 tick de slippage. Os dois arquivos estão em `protocolo.json` (SHA-256 `e3eec98c…`) e `protocolo_nulo.json` (`05589ad0…`).

| | Gerador v2: treino | Gerador v2: teste | Nulo: treino | Nulo: teste |
|---|---:|---:|---:|---:|
| Variações positivas | 28/50 | 16/50 | 4/50 | 18/50 |
| Escolhida | modo mola, variação 27 | | modo mola, variação 46 | |
| Operações | 233 | 98 | 65 | 22 |
| Acerto | 61,4% | 48,0% | 64,6% | 59,1% |
| Líquido | R$ 1.223 | **−R$ 489** | R$ 218 | −R$ 76 |
| Média diária (IC 95%, bootstrap por pregão) | R$ 29,12 (−3,55; 59,79) | −R$ 27,17 (−75,78; 20,17) | R$ 5,19 (−6,00; 16,43) | −R$ 4,22 (−24,33; 11,39) |
| Drawdown | R$ 603 | R$ 747 | R$ 227 | R$ 186 |
| Precisão C / V (taxa base) | 54,2% / 55,8% (43,3% / 44,7%) | 49,0% / 49,0% (42,1% / 47,2%) | | 40,0% / 58,3% |
| Spearman treino × teste das 50 variações | | −0,12 | | 0,11 |
| Posição da escolhida no teste | | 49 de 50 | | 27 de 50 |

**Decisão: rejeitada.** No teste do gerador v2, a média diária é negativa, o intervalo inclui zero e a variação escolhida ficou em 49º de 50. O ranking do treino não se manteve no teste: a correlação de Spearman foi negativa. O ganho do treino foi sobreajuste ao regime predominante.

**Por que falhou:**
- O treino teve 12 dias de tendência em 42 (29%). O teste teve 11 em 18 (61%).
- A mola ganhou R$ 413 nos 7 dias laterais do teste e perdeu R$ 902 nos 11 de tendência.
- O filtro de Hurst deveria desligar a mola nos dias de tendência, e não desligou.

**O controle nulo se comportou como esperado:** só 4 das 50 variações foram positivas no treino, e o teste ficou perto de zero, com intervalo cruzando zero. Não há sinal de vazamento de informação futura no pipeline.

## Estudo das variáveis (só treino, 42 pregões, horizonte de 10 barras)

Arquivos: `estudo_variaveis_treino_gerador_v2.json` e `estudo_variaveis_treino_nulo.json`. A tabela mostra a correlação de Spearman; * marca as que têm IC 95% (bootstrap de 500 reamostragens por pregão) que não cruza zero.

| Variável | Direção v2 / nulo | Continuação v2 / nulo | Amplitude v2 / nulo |
|---|---|---|---|
| Deslocamento da mola x | **−0,102\*** / +0,007 | −0,019 / +0,007 | +0,021 / +0,001 |
| Pressão | **−0,077\*** / −0,004 | −0,015 / −0,007 | +0,007 / −0,016 |
| Momento | **−0,060\*** / −0,022 | +0,001 / +0,006 | 0,000 / −0,007 |
| Energia potencial U | −0,006 / +0,018 | **−0,064\*** / +0,004 | +0,033\* / +0,019 |
| Eficiência | −0,033\* / −0,031 | **−0,044\*** / −0,003 | +0,036\* / +0,006 |
| Hurst (VR) | +0,006 / +0,022 | +0,004 / −0,006 | +0,007 / +0,002 |
| Entropia | −0,004 / −0,007 | +0,011 / −0,008 | −0,058\* / −0,052\* |
| Temperatura | +0,001 / +0,005 | −0,025 / +0,026 | **+0,129\*** / **+0,131\*** |
| Energia cinética | +0,001 / +0,005 | −0,034\* / +0,022 | **+0,126\*** / **+0,125\*** |
| Aquecimento | −0,015 / −0,018 | −0,022 / −0,016 | +0,021 / +0,029\* |
| Massa | +0,007 / +0,006 | +0,009 / +0,004 | +0,001 / +0,008 |
| Fase da Lua | −0,035 / −0,007 | +0,025 / −0,007 | −0,014 / −0,026 |
| Iluminação da Lua | −0,025 / −0,004 | −0,010 / +0,009 | −0,040 / −0,027 |

**Leitura:**
- **Temperatura e energia cinética preveem a amplitude do movimento, não a direção.** O efeito aparece também no nulo, porque o agrupamento de volatilidade (GARCH) é uma propriedade real dos dois geradores. São candidatas a dimensionar alvo, stop e lote, não a dar sinal de entrada.
- **Mola, pressão, momento e eficiência só têm sinal no v2, e com sinal negativo.** Elas capturam a reversão plantada nos dias laterais e somem no nulo. A pressão e o momento, que a regra de tendência usa como confirmação, apontam na direção contrária.
- **Hurst e entropia não distinguiram tendência de lateralidade em barras de 1 minuto.** A janela de 30 barras e o arredondamento de 5 pontos dominam o estimador. Isso explica a falha do filtro de regime.
- **A Lua não prevê nada nos dois geradores, como esperado de um fenômeno constante ao longo do pregão.** É o controle negativo do método. No nulo, nenhuma das 26 medições de direção e continuação aparece com asterisco. As quatro marcadas em amplitude (temperatura, energia cinética, entropia e aquecimento) refletem o agrupamento de volatilidade que o gerador nulo também tem.

## Próximos passos sugeridos

1. Rodar `tools/estudar_variaveis_fisicas.py` sobre o CSV real de WINZ26 no computador local e publicar só o JSON agregado. Esse estudo diz quais variáveis têm sinal real antes de qualquer otimização.
2. Se a temperatura confirmar o poder sobre a amplitude, testar alvo e stop proporcionais a √T como um cenário pareado sobre a v5.8 original, sem novos sinais.
3. Trocar o detector de regime: Hurst em 30 barras não serve. Os candidatos são a eficiência ou a entropia em janelas diárias, avaliadas primeiro pelo estudo e depois pelo protocolo.

## Rodada 2: variáveis nos modelos conhecidos

Temperatura e mola foram aplicadas à v5.8, à Scalper v1.1 e à Pullback, com 31 replays por pregão e por modelo. Nenhuma versão escolhida pelo treino melhorou o teste. Detalhes em [modelos/README.md](modelos/README.md).

## Reprodução

```bash
python -m tools.avaliar_fora_amostra --protocolo docs/colaboracao/evidencias/estrategia_fisica_v1/protocolo.json --saida <dir>
python -m tools.avaliar_fora_amostra --protocolo docs/colaboracao/evidencias/estrategia_fisica_v1/protocolo_nulo.json --saida <dir>
python -m tools.gerar_win_sintetico --versao 2 --saida <csv>   # e --versao 0 para o nulo
python -m tools.estudar_variaveis_fisicas --csv <csv> --saida <json> --primeiros-pregoes 42 --reamostragens 500
python -m pytest -q tests/test_fisica_mercado.py tests/test_avaliar_fora_amostra.py
```
