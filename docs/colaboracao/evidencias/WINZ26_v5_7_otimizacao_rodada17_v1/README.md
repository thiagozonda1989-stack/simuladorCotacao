# Rodada 17 — variação da v5.7 no Profit

24/11/2026 · WINZ26 · 1 minuto · America/Sao_Paulo · PR #2 em rascunho.

**Parecer do Codex: reprodução histórica bloqueada.** A assinatura informada por Thiago é uma variação, R$ 5.745 líquidos, fator de lucro 2,22 e 43 operações. A busca no Windows não localizou a tabela dessa variação nem a lista de operações correspondente. As exportações verificadas têm identidade e resultados distintos. O perfil publicado conserva os valores informados e deixa vazios os campos que exigem confirmação nativa.

## SHAs e fonte

| Item | Identificador |
|---|---|
| Branch do PR | `research/piloto-ias-etapa1` |
| Base da rodada | `dd5577279a65497cae2662a6908ba513386fc038` |
| Última alteração do motor na base | `db9ace693c9396d87198e0973d9708ddeb7668d4` |
| Código do roteiro e testes executados | `8c19e06a823f57987b9c7e7fa19eb986cb9a1201` |
| Commit da fonte v5.7 versionada | `f5c2c14e34fedc62df026d1d7a8dffc8cd805f82` |
| SHA-256 da fonte candidata no Windows e no Git | `0cf2d0d90973a46c38af6dd5bbe4cfeba9d97d3b9242f9ad5cc490318395a22a` |
| SHA-256 da fonte associada à variação efetivamente executada no Profit | Pendente de vincular à variação |
| Replay histórico desta variação | Pendente |

A estratégia versionada em `estrategias/execucao/Modelo_Unificado_Refatorado_v5_7.ntsl` é idêntica byte a byte a duas cópias locais do NTSL fornecido, com 3.596 bytes em cada cópia. A variante local `legenda_visual_v1` e a captura instrumentada de paridade têm hashes diferentes. A captura instrumentada usou lote 1. O bloco legado de paridade continua sendo evidência para os dois recortes anteriores, que chegaram a 10/10 em 21/10 e 12/12 em 26/10 no modo pós-preenchimento. [Relatório anterior](../WINZ26_v5_7_persistencia_escalar_20261026_v2/README.md).

## Configuração encontrada

| Campo | Estado |
|---|---|
| Ativo, período e número de variações | WINZ26, 1 minuto, uma variação, conforme informado |
| ATR de regime, desvio VWAP, Z-score de volume | 50, 2,10, 1,50, conforme informado e igual aos padrões da fonte candidata |
| Stop, alvo e folga do stop-limit | 350, 450 e 5 pontos, conforme informado e igual aos padrões da fonte candidata |
| Densidade | `p_MinimoTrades=100`, com comparação estrita `Trades > 100` na fonte candidata |
| `p_Lote` | 5 na variação informada e no padrão da fonte candidata. Lote 12 citado na tela do editor é outra configuração |
| Período ATR | 14 no fonte candidato, efetivo no Profit pendente |
| Datas inicial e final, histórico carregado e modo | Pendentes |
| Slippage, custos, quantidade do painel, máximo e Executar nos Limites | Pendentes |
| Quantidades preenchidas e eventual parcial | Pendentes no CSV de operações da variação |

Na fonte candidata, `v_Regime_Mercado=1` indica tendência e `=2` indica exaustão. As proteções pedem alvo limite e stop-limit. A estratégia pede saída a mercado quando a densidade cai ou a barra está fora do horário permitido. O filtro permite 09:15 a 17:00 inclusive, exceto 10:25–10:35 e 14:25–14:35 inclusive. Quando ambos os filtros falham, o mesmo ramo pede a saída e a classificação exige registrar as duas condições na avaliação que gerou a ordem.

## Inventário e limitações

O [manifesto](inventario_fontes.json) traz tamanhos, SHA-256, colunas e contagens dos candidatos relevantes. A busca conferiu ProfitRTD e candidatos em Desktop, Downloads e pastas de estudos. O relatório local de nome genérico `relatorio_backtest.pdf` confirmou 329 operações, R$ 657 e fator 1,07. O CSV `operacoes_teste_v.csv` tem 330 operações de 1 contrato, R$ 670 e fator 1,08. O CSV `operacoes_v58.csv` tem 290 operações de 5 contratos, R$ 10.365 e fator 1,23. Nenhum deles identifica a variação solicitada.

As barras locais da v5.7 têm OHLC, Trades, Quantity e Volume financeiro. O CSV separado de indicadores tem VWAP diária, desvio, ATR e média do ATR, saldo de agressão, Z-score de volume, regime e sinal. Nos dois arquivos, a ordem física está do mais recente ao mais antigo e há 29.972 rótulos em comum, 992 exclusivos das barras e 11 exclusivos dos indicadores. Entre os minutos em comum, os preços OHLC de um rótulo divergem, em 19/11 às 16:40. A janela efetiva da otimização ainda é desconhecida. A divergência de 19/11 é entre exportações locais.

O cruzamento de candles e indicadores usa os rótulos exatos pelo mesmo ativo, fuso e intervalo. Para investigar divergência com os dados de mercado, a trilha causal anterior agrega Negócios com sequência verificável para volume e contagem e usa Preços e Ofertas conhecidos até cada evento. Empates sem sequência e lacunas limitam a ordenação dos toques. Os candles e indicadores da variação, se vinculados, têm precedência para reproduzir seu Backtest. [Protocolo de paridade](../../ETAPA2A_PROTOCOLO_PARIDADE.md).

## Matriz Profit × simulador

| Métrica | Profit da variação informada | Simulador, lote original | Simulador, 2 contratos |
|---|---:|---|---|
| Líquido total | R$ 5.745 | Pendente | Pendente |
| Fator de lucro | 2,22 | Pendente | Pendente |
| Operações | 43 | Pendente | Pendente |
| Lote preenchido | Pendente | Pendente | Pendente |
| Acertos / operações, drawdown realizado | Pendentes | Pendentes | Pendentes |
| Duração mediana / P90, operações por pregão | Pendentes | Pendentes | Pendentes |

**Primeira divergência da variação:** indeterminada. A primeira incompatibilidade comprovada é de identificação da fonte, antes da comparação de sinais e ordens. Nenhuma série nativa foi usada em replay histórico nesta rodada. Na paridade anterior, OHLC, Trades e volume vieram das exportações do Profit, saldo de agressão foi injetado para diagnóstico e a VWAP do motor foi reconstruída pelo volume financeiro e contratos. [Preparação de barras](../../../../tools/preparar_paridade_profit_barras.py).

## Exportações necessárias no Profit

1. Abra a **Otimização** e selecione a linha que exibe R$ 5.745, fator 2,22 e 43 operações. Exporte a **tabela de resultados com a linha inteira**, todos os inputs, inclusive `p_Periodo_ATR`, e o período analisado. Guarde um print da linha selecionada e um do painel dessa mesma avaliação com WINZ26, 1 minuto, datas, seletor OHLC/Tick a Tick, quantidade e máximo, Executar nos Limites, slippage em ticks e custos. Se a tabela omitir algum campo, capture o painel correspondente. Informe o histórico carregado antes do primeiro pregão ou da primeira barra do recorte.
2. Abra o detalhe dessa mesma linha e exporte **as 43 operações completas** e o relatório de desempenho. Preserve o horário de entrada e saída, direção, preços, quantidade comprada e vendida, comissões e resultado. Exporte a lista de ordens/preenchimentos da mesma avaliação, se o Profit a disponibilizar, com tipo, estado, gatilho e limite, horários, sequência, vínculos, quantidade solicitada e preenchida. Se a lista vier de outro modo, identifique o modo e a execução. Um CSV de operações sem ciclo nativo pode sustentar paridade de preenchimentos.
3. Exporte **os candles de 1 minuto** da mesma janela, com histórico de aquecimento, horário de abertura, OHLC, Trades, Quantity e Volume financeiro. Para Tick a Tick, inclua os eventos nativos com relógio subminuto e sequência em empates. Registre granularidade, fuso, lacunas e o identificador do ativo que gerou o CSV.
4. Exporte a **fonte NTSL associada** à avaliação e, para explicar o primeiro desvio ou classificar regimes e saídas a mercado, o console ou séries nativas com rótulo do candle, VWAP diária, agressão, Volume, Trades, ATR, média do ATR, regime, sinal, posição e filtros de densidade e horário. Se houver evento de ordem, preserve a sequência e mantenha o horário de execução em coluna distinta. A exportação de um estudo sobre o mesmo gráfico serve para comparar indicadores quando os rótulos, histórico e configuração forem compatíveis.

## Roteiro e resultados locais

```powershell
py -3.11 -m pytest -q
py -3.11 tools/reproduzir_v5_7_rodada17.py --config docs/colaboracao/evidencias/WINZ26_v5_7_otimizacao_rodada17_v1/configuracao.json
```

132 testes passaram. A suíte emitiu 12 avisos de pandas em testes existentes de datas. O segundo comando retornou código 2 por campos nativos ausentes antes de abrir os candles ou rodar a estratégia. A leitura de três CSVs anteriores também conferiu a convenção local de resultado por operação. O simulador usa os mesmos arquivos e regras nas duas quantidades quando o lote original estiver pareado.

Depois de confirmar a variação, copie o JSON para uma pasta privada. Preencha datas, modo, inputs efetivos, origem das séries, quantidade e máximo do painel. Congele os SHA-256 em `fontes_sha256` nas chaves `variacao`, `operacoes`, `barras` e `ntsl`. A chave `regras_ohlc` usa todos os campos de `ExecutionRules`, incluindo custo por contrato por lado, slippage em ticks, aquecimento/lacunas, avaliação pós-preenchimento e rastreio. Fixe as regras com base na captura. Para exportações nativas, [o preparador existente](../../../../tools/preparar_paridade_profit_barras.py) documenta as colunas do CSV OHLC normalizado e como registrar agressão exportada. Confira continuidade, lacunas e correspondência do histórico antes de congelar os candles. O roteiro rejeita candles fora das datas efetivas. Se houver aquecimento anterior separado sem permissão de negociação, valide o recorte e a inicialização antes do replay.

```powershell
py -3.11 tools/reproduzir_v5_7_rodada17.py --config <perfil-privado.json> --variacao <variacao.csv> --operacoes <operacoes.csv> --barras <barras-ohlc-integradas.csv> --ntsl <fonte-da-variacao.ntsl> --saida-privada <pasta-nova-fora-do-repositorio>
```

O roteiro coteja direção, lote, preços e horários de entrada e saída sem deslocamento temporal. Se disponíveis, sinais e solicitações do Profit devem ser cruzados com `candles.csv`, `console.csv` e `eventos_ordens.csv` no Windows para localizar um evento anterior à primeira diferença de preenchimento. O pareamento automático cobre operações de uma entrada e uma saída integrais. A decisão de equivalência exige os 43 fechamentos, identidade dos preenchimentos e métricas compatíveis. Para o cenário de 2 contratos, o replay troca `p_Lote` e calcula custos e slippage novamente com as regras congeladas.

Os agregados do roteiro usam P/L líquido, fator bruto, acertos líquidos positivos / operações fechadas, drawdown realizado no encerramento das operações, duração mediana e P90, frequência incluindo pregões sem operações, lado e causas comprovadas. O roteiro marca regime, causas nativas sem ciclo da ordem e as causas de saídas a mercado ainda não identificadas. Atribua tendência/exaustão pelo regime do sinal de entrada e baixa densidade/horário pelos filtros no contexto da solicitação de saída, quando os logs permitirem.

Os originais permanecem no Windows. O manifesto publica hashes, cabeçalhos e contagens. Nenhuma operação individual ou linha de mercado foi publicada. A fonte v5.7, a semântica OHLC e o motor ficaram como estavam nesta rodada. O adendo segue para consenso após a reprodução.
