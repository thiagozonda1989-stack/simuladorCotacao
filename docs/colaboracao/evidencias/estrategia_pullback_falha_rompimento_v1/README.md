# Rodada 16 · v1.7 com saída por falha de rompimento

**Parecer Codex · rejeitada para avanço.** As quatro variantes pioraram o líquido total e o resultado pareado nos 19 pregões de desenvolvimento. A melhor terminou em **R$ 444**, **R$ 254 abaixo da v1.5**. O protocolo previa avançar aos 20 conhecidos apenas uma variante aprovada. Nesses 20 pregões foram rerodados a v1.5 e o controle v1.7 com o adendo desligado. O painel de Estratégias permanece em **35/100**. [Protocolo e consenso](PROTOCOLO.md)

## Referência, parâmetros e conferência

| Item | SHA ou configuração |
|---|---|
| Motor OHLC executado | `db9ace693c9396d87198e0973d9708ddeb7668d4` |
| Fonte v1.5 | `521f96e2574f501e6d1598ef154fcd30baa77517` |
| Perfil selecionado da v1.5 | `5de205abcaec295953c43476d7ee071529a78d39` |
| Código da v1.7 e protocolo executados | `b872434257248be734206b0a80e717dba02c4dd8` |
| Ativo e execução | WINZ26, barras de 1 min, 2 contratos, tick de 5 pts, R$ 0,20 por ponto/contrato, R$ 0,50 por contrato por lado, 1 tick de slippage |
| Sinal e filtros da v1.5 | Médias 20/21, rompimento ligado, amplitude em 5 barras, alvo dinâmico ×1,6 entre 50 e 220 pts, stop ×0,8 entre 50 e 110 pts, folga 50 pts |
| Gestão fixa | Prazo 5 barras, até 24 sinais de entrada por dia, espera 1 barra, perda diária R$ 150, entradas entre 10:00 e 17:00, zeragem 17:45 |
| Adendo | Janela máxima J=1/2 contando o primeiro fechamento da entrada, tolerância estrita T=0/1 tick, desativa após lacuna para a posição |
| Opções de replay | Execução na barra seguinte. Pós-preenchimento e persistência de proteções desligados no A/B, como na rodada 15. Rastreio de ordens ligado. |

O motor e a v1.5 foram preservados. Adendo desligado e v1.5 produziram preenchimentos, eventos de ordem, trace, logs e contadores idênticos nos dois conjuntos. O controle reproduziu os líquidos, acertos, quantidades e drawdowns publicados na rodada 15. Os dois lados de todas as operações usaram 2 contratos. A avaliação histórica é no simulador. Compilação e paridade da v1.7 no Profit permanecem em aberto. [Configuração completa e datas](protocolo.json) · [NTSL](../../../../estrategias/execucao/pullback_tendencia_v1_7.ntsl)

## Resultados

Os valores monetários são líquidos de custos. Mediana e P90 são durações em minutos, medidas entre os candles de entrada e saída.

| Amostra e variante | Operações | Acerto | Líquido total | Δ vs. v1.5 | Líquido/dia | Drawdown | Mediana / P90 | Operações/dia | R$/op. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Desenvolvimento · v1.5 e v1.7 desligada | 139 | 43,2% | R$ 698 | R$ 0 | R$ 36,74 | R$ 472 | 2 / 5 | 7,32 | R$ 5,02 |
| Desenvolvimento · J1 T0 | 149 | 40,9% | R$ 440 | −R$ 258 | R$ 23,16 | R$ 470 | 1 / 5 | 7,84 | R$ 2,95 |
| Desenvolvimento · J1 T1 | 149 | 40,9% | R$ 444 | −R$ 254 | R$ 23,37 | R$ 448 | 1 / 5 | 7,84 | R$ 2,98 |
| Desenvolvimento · J2 T0 | 148 | 41,2% | R$ 266 | −R$ 432 | R$ 14,00 | R$ 648 | 1 / 5 | 7,79 | R$ 1,80 |
| Desenvolvimento · J2 T1 | 143 | 39,9% | −R$ 36 | −R$ 734 | −R$ 1,89 | R$ 742 | 1 / 5 | 7,53 | −R$ 0,25 |
| Exploratórios conhecidos · v1.5 e v1.7 desligada | 230 | 36,5% | −R$ 480 | R$ 0 | −R$ 24,00 | R$ 1.238 | 1 / 5 | 11,50 | −R$ 2,09 |

No desenvolvimento, as ativas ficaram de 3,8 a 5,1 pontos percentuais abaixo de **45%** e de 2,0 a 3,3 pontos abaixo da v1.5. Nos 20 conhecidos, o controle ficou 8,5 pontos abaixo de 45% e R$ 3.024 abaixo da referência de **R$ 3 mil líquidos por pregão** em média. Nenhum pregão atingiu R$ 3 mil em qualquer cenário executado. [19 pregões e detalhe diário](desenvolvimento.json) · [20 pregões e detalhe diário](exploratorio.json)

## Saídas antecipadas e efeito sobre as entradas

| J / T | Executadas / pareadas | Perdas amenizadas ou evitadas | Vencedoras cortadas | Δ pareadas | Novas / suprimidas | Δ sem par |
|---|---:|---:|---:|---:|---:|---:|
| 1 / 0 | 29 / 26 | 10 · R$ 144 | 4 · R$ 156 | −R$ 270 | 11 / 1 | +R$ 12 |
| 1 / 1 | 27 / 24 | 9 · R$ 126 | 4 · R$ 156 | −R$ 266 | 11 / 1 | +R$ 12 |
| 2 / 0 | 32 / 29 | 11 · R$ 150 | 4 · R$ 156 | −R$ 492 | 11 / 2 | +R$ 60 |
| 2 / 1 | 31 / 28 | 11 · R$ 158 | 4 · R$ 156 | −R$ 532 | 11 / 7 | −R$ 202 |

As colunas de perdas e ganhos descrevem as melhoras na parte negativa e os cortes na parte positiva. O delta total pareado inclui também perdas agravadas e ganhos preservados ou melhorados. Pelos critérios congelados, nenhuma variante avançou. Por exemplo, **J1 T1** teve drawdown R$ 24 menor, porém o −R$ 266 nas pareadas superou o +R$ 12 de composição. A distância mediana da entrada ao nível congelado foi 85 pts e o P90 220 pts em todas as variantes. Cada variante teve uma solicitação antecipada a mais que preenchimentos antecipados. A auditoria do motor registra as ordens canceladas nas lacunas. As contagens de barras ambíguas foram 1 no desenvolvimento, incluindo a v1.5 e cada variante, e 2 no controle exploratório. Ausência de divergência do controle OFF não constitui teste de paridade nativa da ativa.

## Cobertura e reserva

Os mesmos candles foram passados às versões dentro de cada amostra. O CSV privado Windows confirmado cobre os 39 pregões acordados, tem SHA-256 `3726e7dd9a821a109120765e4115e6eb352079e9402d9370ae7565ac9555bb2a` e não tem carimbos duplicados na janela conferida. Foram usados 10.186 candles no desenvolvimento e 11.288 nos conhecidos. A divisão nominal veio do artefato publicado antes desta rodada. Uma fonte local alternativa tem 19/11 com cobertura nominal completa, enquanto o arquivo principal deixa esse dia incompleto. A fonte alternativa não foi usada no replay. Sem variante aprovada e congelada, a avaliação de inéditos ficou sem execução. Preços, fills e caminhos do CSV original permanecem no Windows.

## Reprodução

~~~powershell
$saida = 'DIRETORIO_NOVO_PARA_RESULTADOS'
py -3.11 -m pytest -q
py -3.11 -m tools.avaliar_pullback_rodada16 --fase desenvolvimento --csv $barrasPrivadas --saida "$saida/desenvolvimento.json"
py -3.11 -m tools.avaliar_pullback_rodada16 --fase exploratorio --csv $barrasPrivadas --congelamento "$saida/desenvolvimento.json" --saida "$saida/exploratorio.json"
~~~

A suíte local passou com **175 testes**, com os 12 avisos de pandas já conhecidos. Os testes novos cobrem as duas leituras que divergiam, paridade OFF, lados espelhados, nível congelado, tolerância, lacuna, avaliação extra, prioridade de prazo, espera, limite diário, OHLC stop-limit e diagnóstico pareado. [Testes da candidata](../../../../tests/test_pullback_v1_7.py) · [Casos discriminantes](../../../../tests/test_rodada16_saida_por_fechamento.py) · [Funções de métricas](../../../../tools/metricas_pullback_rodada16.py)
