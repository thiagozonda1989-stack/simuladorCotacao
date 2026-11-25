# Rodada 19 · perfis congelados e diagnóstico do WINZ26

25/11/2026, America/Sao_Paulo. PR #2 em rascunho, branch `research/piloto-ias-etapa1`.

## Perfis congelados

| Referência | SHA Git |
|---|---|
| Evidência da rodada 18 | `4b195d9c6a0e3fd8e2e92eda71c0827dd9870cb5` |
| Execução dos replays, inventário e testes | `0eb89ccd18bc3b3928f58d42215e56cb342c5011` |
| Última alteração no motor de ordens `estrategia.py` | `db9ace693c9396d87198e0973d9708ddeb7668d4` |
| Última alteração do compilador `ntsl.py` | `e3f474453e4186c9df83392af9f6fd7284a3e234` |
| Modelo Unificado v5.8 | `e54a729150b736173c4fdea16d65579759df6dde` |
| Scalper v1.1 | `f5c2c14e34fedc62df026d1d7a8dffc8cd805f82` |

Os dois perfis candidatos são o Modelo Unificado v5.8 com os parâmetros originais, configurado em OHLC com `p_Exec_Tick=0` e `p_Lote=2`, e a Scalper v1.1 com a configuração selecionada no desenvolvimento da rodada 18 e `p_Lote=2`. O terceiro replay, da v5.8 otimizada, é exclusivamente diagnóstico. O congelamento dos perfis registra caminho, SHA-256 de cada fonte, todos os inputs e flags. [Configuração completa](perfis.json).

O replay usa WINZ26 em barras de 60 segundos, grade de 5 pontos, R$ 0,20 por ponto por contrato, custo de R$ 0,50 por contrato e lado e slippage de 1 tick conforme o tipo de ordem. A elegibilidade é a partir da próxima barra, com zero latência adicional. A política do stop-limit OHLC e o encerramento no fim do pregão seguem o motor. A VWAP reconstruída continua através das lacunas intradiárias, com reinício no pregão. O histórico NTSL mantém o comportamento da rodada 18, com aquecimento por segmento depois de lacuna. A avaliação pós-preenchimento, a proteção na barra da entrada, a entrada a mercado através de lacuna, a persistência opcional de proteções e o ajuste experimental de preços ao tick ficam desligados.

## Reprodução em 20 pregões conhecidos

Os três perfis usaram as mesmas 11.288 barras. O replay iniciou no primeiro pregão conhecido, seguindo a rodada 18. O SHA-256 do arquivo preparado de 39 datas foi conferido antes de filtrar a lista fechada de 20 datas publicada em `perfis.json`. Nenhum perfil foi ajustado nesta rodada. Os OHLC, Trades, contratos e volume financeiro são do Profit. O saldo nativo de agressão foi injetado por barra após a junção por timestamp e OHLC idênticos, conforme a preparação da rodada 18. Para VWAP, o motor usou o preço médio estimado por barra com volume financeiro dividido por contratos e valor do ponto. [Origem e limitações da base](../WINZ26_ag_rodada18_v1/README.md).

| Perfil | Ops. (por dia) | Acertos | Líquido | Média/pregão | Média/op. | Fator de lucro | Drawdown | Pior pregão | Duração mediana / P90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| v5.8 original OHLC | 147 (7,35) | 76/147 (51,7%) | R$ 1.902 | R$ 95,10 | R$ 12,94 | 1,21237 | R$ 2.352 | −R$ 1.046 | 15 min / 53 min |
| Scalper v1.1 otimizada | 83 (4,15) | 49/83 (59,0%) | −R$ 58 | −R$ 2,90 | −R$ 0,70 | 0,97148 | R$ 456 | −R$ 212 | 2 min / 7 min |
| v5.8 otimizada, diagnóstico | 86 (4,30) | 36/86 (41,9%) | −R$ 2.022 | −R$ 101,10 | −R$ 23,51 | 0,73147 | R$ 2.056 | −R$ 862 | 25 min / 94 min |

A taxa de acerto conta operações líquidas positivas e inclui operações no zero no denominador. O drawdown é o da curva de operações encerradas desde saldo zero. As durações usam rótulos das barras dos fills OHLC. Dias sem operação contam na média. A v5.8 original e a Scalper ficaram 6,70 e 14,04 p.p. acima de 45% de acerto. Ficaram R$ 2.904,90 e R$ 3.002,90 abaixo de R$ 3 mil líquidos por pregão em média. Nenhum dos três perfis alcançou R$ 3 mil em um dia.

O CSV agrega separadamente pregão, hora de entrada, hora de saída, direção, regime da solicitação de entrada e motivo da saída executada. Cada corte foi reconciliado com o total do perfil. A Scalper ficou com regime indisponível porque a fonte não expõe a mesma classificação. Limite de proteção foi classificado como alvo, stop como stop-limit e saídas a mercado pela condição vigente no envio, segundo a precedência no NTSL. Na v5.8, baixa densidade filtra a entrada. As saídas a mercado observadas foram horárias e por notícia. Na Scalper, as 11 saídas a mercado observadas foram pelo máximo de barras em posição. [Agregados](agregados.csv) · [Resultados e células da decomposição](resultado.json).

## De onde veio a diferença da v5.8

O líquido caiu R$ 3.924. Foram 61 operações a menos e a média passou de R$ 12,94 para −R$ 23,51. A decomposição simétrica usa frequência multiplicada pelo ponto médio das médias dos dois perfis. O restante separa as mudanças de peso das 32 células de hora de entrada × direção × regime e as mudanças de resultado médio dentro delas. Nas seis células exclusivas, a média observada é usada nos dois termos para alocar a contribuição à composição. A soma é exata antes do arredondamento. A apresentação em centavos deixa resíduo de R$ 0,01.

| Componente do delta otimizada − original | Reais |
|---|---:|
| Frequência | +322,47 |
| Composição das entradas | +726,67 |
| Resultado por operação dentro das células | −4.973,15 |

O pareamento exato por barra, direção, quantidade e preço da entrada encontrou 48 pares com delta de −R$ 668. As 99 operações exclusivas da original somaram R$ 2.364 e as 38 exclusivas da otimizada somaram −R$ 892. A perda líquida concentrou-se nas vendas, de R$ 438 para −R$ 2.030. O líquido por regime caiu de R$ 218 para −R$ 1.598 em exaustão e de R$ 1.684 para −R$ 424 em tendência. Alvos passaram de 65 para 21 e stops de 59 para 36. A decomposição e o pareamento são análises descritivas. Os parâmetros da otimizada mudam em conjunto e as novas saídas ou tempos de posição podem mudar as entradas elegíveis depois.

| Perfil | Melhor pregão retirado | Retirado | Líquido em 19 pregões | Média/pregão restante |
|---|---|---:|---:|---:|
| v5.8 original | 17/11/2026 | R$ 796 | R$ 1.106 | R$ 58,21 |
| Scalper v1.1 otimizada | 12/11/2026 | R$ 196 | −R$ 254 | −R$ 13,37 |
| v5.8 otimizada, diagnóstico | 13/11/2026 | R$ 296 | −R$ 2.318 | −R$ 122,00 |

Cada linha retira o melhor dia do próprio perfil apenas da agregação dos fills existentes. Nenhuma estratégia foi reexecutada com o dia removido.

## Reserva inédita no Windows

A varredura de exportações na pasta ProfitRTD e a conferência das fontes recentes identificaram **23/11/2026 como candidata à reserva**. `SONDA_S1_STOP_barras.csv` traz 552 rótulos de um minuto, 09:03–18:14, sem repetição, buraco interno ou OHLC inválido. A associação ao WINZ26 vem da captura da sonda e da coincidência integral de OHLC nos 19.449 timestamps sobrepostos com `barras_v58.csv`. O CSV candidato tem apenas Data e OHLC. Em relação à janela de referência observada de 09:00 a 18:24, faltam três rótulos no início e dez no fim da exportação. A causa dessa diferença de borda permanece aberta. Trades, Quantity, Volume e saldo de agressão de 23/11 estão ausentes nas fontes localizadas. Não apareceu fonte de 24/11 entre as exportações examinadas. [Manifesto por fonte e cobertura recente](manifesto_fontes.json).

19/11 já foi usado nas exportações de operações da v5.7 e da v5.8. Tem 565 barras OHLC, Trades e volume até 16:40 em outra fonte e saldo de agressão até 16:51. A rodada 18 registrou uma discrepância de OHLC às 16:40. As exportações rápidas e os cinco dias antigos de negócios não completam os campos da reserva. Também não há negócio, Preço ou Oferta contemporâneos da reserva com chave temporal verificada para reconstruir esses campos.

**Exportar no Profit.** Abra WINZ26 com candles de 1 minuto. Para 23/11 e 24/11, e para os pregões fechados posteriores que servirão à reserva, exporte a sessão inteira, mais o pregão anterior necessário ao aquecimento, com:

1. `Data` no fuso America/Sao_Paulo e carimbo de cada candle, `Abertura`, `Máxima`, `Mínima`, `Fechamento`.
2. `Trades` e `Quantity` (contratos) em campos distintos. Exporte também `Volume` financeiro.
3. Saldo de agressão nativo `AgressionVolBalance` por barra, na mesma granularidade, contrato e janela. Se estiver numa exportação separada, mantenha `Data` e os quatro preços OHLC. VWAP nativa pode ser incluída para conferência.
4. Um print da seleção de contrato, datas e periodicidade. Guarde CSVs e print no Windows. Se um minuto não aparece no Profit, registre intervalo e fonte. A conferência mantém os minutos ausentes sem preencher com valores artificiais.

A inspeção fez somente inventário e conferência de cobertura, sem sinais, ordens ou replays na reserva. A elegibilidade e os critérios cronológicos de aceitação ainda dependem da cobertura e da consolidação dos pareceres de Claude e Gemini.

## Reprodução e conferência

No clone, no SHA executado, aponte `$basePrivada` para o `win_60s.csv` congelado da rodada 18 e `$originais` para a pasta local de exportações. `$saidaPrivada` é uma pasta local para as saídas. A etapa de inventário guarda o cache local por SHA-256 e reprocessa apenas arquivos com conteúdo ainda não inventariado.

```powershell
py -3.11 -m tools.rodada19 --base $basePrivada --saida $saidaPrivada
py -3.11 -m tools.inventario_rodada19 --cache (Join-Path $saidaPrivada 'inventario_cache.json') `
  --saida (Join-Path $saidaPrivada 'manifesto_fontes.json') `
  (Join-Path $originais 'SONDA_S1_STOP_barras.csv') `
  (Join-Path $originais 'SONDA_S1_ALVO_barras.csv') `
  (Join-Path $originais 'barras_v58.csv') `
  (Join-Path $originais 'profit_WINZ26_20261021_barras_1min.csv') `
  (Join-Path $originais 'profit_WINZ26_20261021_indicadores_v5_7.csv')
py -3.11 -m pytest -q
```

135 testes passaram, incluindo casos sintéticos de decomposição e pareamento. Houve 12 avisos existentes do pandas em testes de timestamps. Em cada perfil os fills do motor comum e do instrumentado coincidiram integralmente. Os três totais reconfirmam operações, acertos, líquido e drawdown da rodada 18. A análise publica somente totais e estratos, sem preços, linhas de mercado, fills, identificadores ou caminhos privados. [Integridade dos artefatos publicados](SHA256SUMS.txt).
