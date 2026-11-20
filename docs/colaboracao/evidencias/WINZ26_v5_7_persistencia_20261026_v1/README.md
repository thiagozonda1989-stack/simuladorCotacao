# WINZ26 v5.7 — persistência entre avaliações

Motor e comparador executados a partir de `742b093e29cab338c9345cbe5b42e5de0e4c6f8d`, com o mesmo código validado em `6aeb1f95d8642f7057b04a0dba9bd1612b6ee5fe`. Código da sonda, teste e catálogo em `e7921ef9759ffa783c4aba18cc51b81109a17c58`. Ambiente Windows 10, Python 3.11.3 e pandas 3.1.1.

## Fonte da captura e cálculo de `anterior`

Foram encontradas três cópias do download `Modelo_Unificado_Refatorado_v5_7_Captura_Paridade.ntsl`, incluindo duas com sufixos de download. As três têm 8.810 bytes e SHA-256 `53d165350fd66902df9d0e7e340f8dc07335c47d8d47413a3cf1057aec18f018`. O fonte foi versionado byte a byte e entrou no catálogo e no manifesto. No Profit, a estratégia aberta que mostrou os logs tinha o nome de aba com sufixo `V2`. O TXT apresenta a estrutura, os campos, a data e a janela de log do fonte encontrado. O console original não registra o hash do programa carregado, então a associação usa esses cruzamentos e o nome da variante registrado no relatório. [Fonte recuperado](../../../../estrategias/execucao/Modelo_Unificado_Refatorado_v5_7_Captura_Paridade.ntsl) · [Relatório da captura](../../CAPTURA_PARIDADE_WINZ26_20261026.md)

O SHA-256 do TXT original coincidiu com `65a90e3cc66c1464e0fba0be862036ba568604eadeb1082741cc24212e9de6a2`. Foram 298 linhas, 288 mensagens de paridade e duas sequências idênticas de 144 mensagens. A primeira sequência correspondeu linha a linha aos 144 eventos publicados, com 75 avaliações. Conferimos ordem, data, hora da barra, `CurrentBar`, número da avaliação, evento e os campos que a publicação reteve. O original e os campos retirados na publicação permanecem no Windows. [CSV de eventos publicado](../../captura_paridade_win_20261026_eventos.csv)

Em cada avaliação, o fonte lê `PositionQty` em `v_PosicaoAtual` (linha 46). Com o log ativo, incrementa `v_AvaliacaoLog` e escreve `POSICAO_OBSERVADA` quando a posição mudou. O campo `anterior` é o valor de `v_PosicaoAnterior` lido antes da atribuição. Logo após o bloco de log, na linha 64, executa `v_PosicaoAnterior := v_PosicaoAtual` em toda avaliação, inclusive fora da janela de log. Isso ocorre antes dos indicadores, dos sinais e das chamadas de ordens. A variável é escalar e o cálculo não usa `[1]` nem consulta uma operação anterior.

No recorte histórico, a avaliação 8, com rótulo 13:03, observou +1 e atribuiu +1. A avaliação 9 de 13:04, já zerada, registrou `anterior=1`. O par 10/11 repete o padrão com rótulos 13:04 e 13:05. Trata-se de evidência histórica para o comportamento dessa variável na variante de captura. A coluna de valor atribuído do recorte é reconstruída do fonte e da posição registrada, pois o console original só escreve `anterior` quando há transição. O recorte mantém o rótulo do console. Horários de execução não são inferidos a partir dele. [Avaliações 7–11](profit_captura_historica_recorte.csv) · [Achado do Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7048493016)

## Sonda mínima de persistência

No simulador, uma compra abriu a 100 e o stop preencheu a 95 dentro da barra sintética de 13:04. A avaliação extra leu `v_Anterior=0` e atribuiu `1`. A avaliação regular seguinte, já zerada, leu `0` e atribuiu `0`. A sequência que o NTSL gravou também voltou para 2, pois a atribuição da avaliação extra foi descartada. A coluna `ordem_console` preserva a ordem real das mensagens. [Log sintético executado](simulador_sonda_log.csv)

| Ordem do log | Fase no simulador | Rótulo NTSL | `seq` | Posição | Antes | Depois |
|---:|---|---|---:|---:|---:|---:|
| 1 | Regular, solicita compra | 13:03 | 1 | 0 | 0 | 0 |
| 2 | Pós-preenchimento na abertura de 13:04 | 13:03 | 2 | +1 | 0 | 1 |
| 3 | Regular, depois do stop | 13:04 | 2 | 0 | 0 | 0 |
| 4 | Regular | 13:05 | 3 | 0 | 0 | 0 |

### Resultado no Profit

O usuário executou a sonda no Profit em modo Debug e forneceu as quatro linhas do console. O CSV conserva a ordem original e normaliza os separadores de milhar, a data e a hora. Os horários são rótulos da barra da avaliação NTSL.

| Ordem do log | Hora da barra | `CurrentBar` | `seq` | Posição | Antes | Depois |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 13:03 | 27005 | 1 | 0 | 0 | 0 |
| 2 | 13:03 | 27005 | 2 | +1 | 0 | 1 |
| 3 | 13:04 | 27006 | 3 | 0 | 1 | 0 |
| 4 | 13:05 | 27007 | 4 | 0 | 0 | 0 |

A avaliação extra comprada, de sequência 2, gravou `depois=1`. A avaliação regular zerada das 13:04, de sequência 3, leu `antes=1`. Isso confirma a persistência da variável escalar entre as duas avaliações neste Backtest. O simulador leu `antes=0` na passagem correspondente do caso sintético. A evidência se refere à sonda escalar. Uma alteração no motor requer teste de decisão dependente do estado e regressões de histórico, médias e ordens. [Log da sonda no Profit](profit_sonda_log.csv)

### Reproduzir no Profit

1. Abra a [sonda NTSL do Profit](sonda_persistencia_profit_v1_0.ntsl) como nova estratégia de execução no Editor. Compile e execute no **Backtest OHLC**, ativo **WINZ26**, período **1 minuto**, com histórico incluindo **26/10/2026**. Use quantidade e quantidade máxima 1, slippage zero e execução nos limites. A sonda tem a data, a janela 13:03–13:05, o stop de 350 pontos e o offset de 5 nos inputs.
2. Copie somente as linhas iniciadas em `PERSISTENCIA;` do console, na ordem em que aparecem. Cada linha registra data e hora da barra, `CurrentBar`, `seq`, posição, valor antes e valor depois. Preserve a repetição de rótulos ou de `seq`. Use a ordem do console para distinguir as passagens.
3. Verifique se a passagem extra comprada grava `depois=1` e se a passagem regular zerada seguinte lê `antes=1`. As duas passagens precisam aparecer na ordem do console para decidir a questão.

## Regressões com configuração única

As comparações usam as mesmas barras privadas do Profit, WINZ26 em 1 minuto, OHLC, timestamps na abertura em `America/Sao_Paulo`. Para **todas as execuções de estratégia e indicadores**, usei `--vwap-continuo-lacunas`. A comparação de indicadores e candidatos usa `--aquecimento 63 --aquecimento-por-segmento`. Essa opção filtra a comparação, enquanto o replay recebe todo o histórico exportado. Controles da estratégia, custos, slippage, latência, tick, volume financeiro e agressão de referência seguem a [rodada anterior](../WINZ26_v5_7_20261021_20261026_pos_preenchimento_v1/README.md). As exportações e os derivados privados foram reaproveitados, sem modificar os originais.

| Pregão | Padrão | Proteção legada | Pós-preenchimento | Oito indicadores | Primeira barra elegível |
|---|---:|---:|---:|---:|---|
| 21/10/2026 | 10/10 | 10/10 | 10/10 | 502/502 cada | 10:03 |
| 26/10/2026 | 8/12 | 11/12 | 12/12 | 463/463 cada | 10:42 |

Os arquivos `execucoes.csv`, `candles.csv` e `eventos_ordens.csv` dos seis replays ficaram byte a byte iguais aos da rodada anterior para o mesmo modo. Em 26/10, a #182 continua comprada em um contrato de 176.815 a 176.465 às 13:05 na exportação. A diferença da camada de indicadores vem da configuração: com VWAP contínua e corte por segmento, 26/10 passa a ser medido nas 463 barras elegíveis, frente ao corte histórico por dia de 490 barras. A VWAP coincide nessa amostra. A cobertura continua parcial no pregão inteiro.

| Pregão | Barras usadas | Período | Timestamps duplicados | Lacunas no período |
|---|---:|---|---:|---|
| 21/10 | 565 | 09:00–18:24 | 0 | 0 |
| 26/10 | 553 | 09:03–18:24 | 0 | 9 minutos, 09:30–09:38 |

A matriz publica somente contagens e os limites do recorte, com tolerância de 0,01 ponto para VWAP, ATR e média do ATR e igualdade para o regime. Saldo de agressão é referência injetada; conferir reconstrução independente requer a fonte apropriada. Para reproduzir a matriz, são precisos os CSVs privados de barras, plots e operações. Auditar ativação ou cancelamento intrabar ainda exige o histórico nativo de ordens em resolução subminuto. [Matriz](matriz_vwap_continua_segmento.csv)

## Comandos reproduzíveis

Comandos executados no Windows. Use um destino novo e as entradas privadas por pregão para a matriz. O JSON de inputs da v5.7 contém somente `{"p_Lote": 1}`.

```powershell
py -3.11 -m pytest -q
$evid = 'docs/colaboracao/evidencias/WINZ26_v5_7_persistencia_20261026_v1'
py -3.11 estrategia.py --csv "$evid/candles_sinteticos.csv" `
  --ntsl "$evid/sonda_persistencia_simulador_v1_0.ntsl" --saida $saidaSonda `
  --segundos 60 --formato ohlc --avaliacao-pos-preenchimento --rastrear-ordens

$comum = @('--segundos','60','--formato','ohlc','--tick','5','--valor-ponto','0.2',
           '--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas')
# $modo recebe @(), @('--protecao-no-candle-entrada') ou @('--avaliacao-pos-preenchimento').
py -3.11 estrategia.py --csv $barrasPreparadas `
  --ntsl estrategias/execucao/Modelo_Unificado_Refatorado_v5_7.ntsl `
  --inputs $inputs --saida $replay @comum @modo --rastrear-ordens
py -3.11 estrategia.py --csv $barrasPreparadas `
  --ntsl estrategias/indicadores/indicador_paridade_modelo_unificado_v5_7_v1_0.ntsl `
  --saida $plotsMotor @comum
py -3.11 tools/comparar_paridade_mesmas_barras.py --profit-barras $barrasProfit `
  --profit-indicadores $plotsProfit --profit-operacoes $operacoesProfit `
  --barras-preparadas $barrasPreparadas --motor-indicadores "$plotsMotor/candles.csv" `
  --motor-candles "$replay/candles.csv" --motor-execucoes "$replay/execucoes.csv" `
  --data $dia --aquecimento 63 --aquecimento-por-segmento --saida $comparacao
```

A suíte passou com **57 testes** e 12 avisos conhecidos de timezone do pandas. Inclui a sonda sintética, o inventário de hashes NTSL e as regressões existentes de histórico, médias, proteções e duplicação de ordens. O motor e a v5.7 original mantêm os mesmos bytes que no SHA validado.

## Inventário da publicação

| Arquivo | Linhas de dados |
|---|---:|
| [Candles sintéticos](candles_sinteticos.csv) | 4 |
| [Sonda para o Profit](sonda_persistencia_profit_v1_0.ntsl) | Código |
| [Sonda para o simulador](sonda_persistencia_simulador_v1_0.ntsl) | Código |
| [Log sintético normalizado](simulador_sonda_log.csv) | 4 |
| [Log da sonda executada no Profit](profit_sonda_log.csv) | 4 |
| [Recorte histórico derivado do console Profit](profit_captura_historica_recorte.csv) | 5 |
| [Matriz integrada](matriz_vwap_continua_segmento.csv) | 6 |

O [TXT para o Gemini](fontes_gemini.txt) incorpora estas fontes e os 144 eventos já divulgados. A normalização retém apenas identificadores de avaliação, relógios, posição, estado da variável e métricas agregadas. Conta, titular, caminhos privados e séries brutas ficaram fora da publicação. [SHA-256 dos arquivos publicados](SHA256SUMS.txt)
