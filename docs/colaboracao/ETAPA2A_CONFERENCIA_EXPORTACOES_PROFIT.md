# Etapa 2A — paridade de 21/10/2026 com as mesmas barras

Recorte congelado: WINZ26, 21/10/2026, candle fechado de 1 minuto, timestamp na abertura em `America/Sao_Paulo`, estratégia v5.7 original, `p_Lote=1`, custos e slippage zerados. Os CSVs originais e os derivados com preços permanecem privados em `C:\Users\thiag\Documents\ProfitRTD`.

## Resultado principal

A diferença anterior de **10 operações no Profit contra 5 no simulador** não é uma divergência mecânica da v5.7. Ao alimentar o motor com as mesmas 565 barras exportadas do Profit, separar `Quantity` de `Volume` financeiro e usar o saldo de agressão exportado como referência diagnóstica, o motor reproduziu:

- 565 de 565 barras;
- os oito indicadores dentro das tolerâncias em 502 barras, depois de excluir 63 barras de aquecimento;
- 14 candidatos de venda, 11 de compra e 477 zeros, exatamente como o Profit;
- 10 ordens de entrada emitidas pelo motor;
- as 10 operações e os 20 preenchimentos exatamente em horário, lado, quantidade e preço;
- a mesma posição quando reconstruída das operações.

Portanto, **não há primeira divergência verificável com as mesmas barras após o aquecimento**. A camada de ordens ainda não pode ser fechada porque o Profit não exportou o histórico nativo de criação, alteração, cancelamento e OCO. A posição do Profit também é derivada das operações, não observada por candle.

## Fontes privadas e integridade

| Fonte | Recorte | SHA-256 |
|---|---:|---|
| `profit_WINZ26_20261021_barras_1min.csv` | 565 barras, 09:00–18:24 | `3726e7dd9a821a109120765e4115e6eb352079e9402d9370ae7565ac9555bb2a` |
| `profit_WINZ26_20261021_indicadores_v5_7.csv` | 565 linhas, oito plots | `76b79ef839ab6b142a0976c7c3ef1a6b7bb7dc2d013434551e861c892a56b946` |
| `profit_WINZ26_20261021_posicao.csv` | 10 operações completas | `549e22dea388e5f4e272bc906ac3309e9e88a1de7f53e6184ded5796dbe64479` |

`tools/preparar_paridade_profit_barras.py` recusa timestamps repetidos, normaliza o fuso, filtra somente 21/10 e cria uma entrada privada nova. `Quantity` permanece em contratos; `Volume` permanece financeiro. O preço médio da barra para VWAP é aproximado por `Volume/(Quantity*R$ 0,20)`. A exportação arredondada limita a precisão, mas o erro máximo observado da VWAP foi **0,004997 ponto**, abaixo da tolerância de 0,01.

O z-score da v5.7 foi alimentado pela série de **Volume financeiro**, como no Profit. O comportamento padrão do simulador continua usando `volume` e só muda com `--volume-financeiro-ntsl`.

## Comparação por camada

### Barras

Os 565 timestamps foram normalizados para `America/Sao_Paulo` antes do cruzamento. Não houve duplicata. OHLC, Trades, Quantity e Volume financeiro coincidiram integralmente porque esta rodada usa diretamente a exportação Profit, sem alterar o original.

O comparador agora recusa duplicatas com mensagem contendo fonte e horário. Ambiguidade de abertura/fechamento só é marcada quando existem preços distintos no primeiro ou último milissegundo da barra. O inventário da captura local encontrou evidência em 174 barras (161 ocorrências no primeiro milissegundo e 19 no último; algumas barras têm ambas). `Sequencia` ordena a captura, mas não prova a ordem de bolsa. Essa marca não é aplicada ao CSV de barras do Profit, que não contém negócios por milissegundo.

### Indicadores

As primeiras 63 barras, 09:00–10:02 inclusive, foram excluídas; a primeira barra comparada é 10:03. Em 502 barras:

| Campo | Tolerância | Fora da tolerância | Máximo absoluto |
|---|---:|---:|---:|
| VWAP | 0,01 ponto | 0 | 0,004997 |
| Desvio padrão | 0,01 ponto | 0 | 0,004986 |
| ATR | 0,01 ponto | 0 | 0,004286 |
| Média do ATR | 0,01 ponto | 0 | inferior a 0,01 |
| Saldo de agressão | exata | 0 | 0 |
| Z-score de Volume | 0,01 | 0 | 0,004980 |
| Regime | exata | 0 | 0 |
| Sinal candidato | exata | 0 | 0 |

`rolling_local()` não fundamenta esta conclusão; ele permanece identificado como diagnóstico auxiliar. Os valores acima foram produzidos pelo próprio compilador/motor NTSL através dos oito plots do indicador instrumentado.

A agressão desta rodada é **dado de referência injetado** (`v_Saldo_Agressao` exportado do Profit). Isso prova que, dadas as mesmas barras e séries semânticas, o cálculo seguinte coincide; não valida a reconstrução independente da agressão local.

### Sinais, ordens, preenchimentos e posição

O `plot8` é o candidato de sinal. A chamada `BuyAtMarket`/`SellShortAtMarket`, registrada em `sinal_compra`/`sinal_venda`, é a ordem de entrada emitida. São eventos diferentes. O primeiro envio ocorreu no fechamento de 10:08 e foi preenchido na abertura de 10:09.

Todas as 10 viagens de ida e volta coincidiram. Logo, a posição reconstruída também coincide. Eventos nativos de ordens e posição por candle do Profit continuam indisponíveis e não foram inventados a partir das execuções.

## O que explica a rodada de 10 contra 5

A captura local possui 563 barras, contra 565 do Profit. Os minutos 09:02–09:04 existem no Profit e faltam localmente; logo é falha de captura, não ausência de negócios. Já na primeira barra comum há diferenças de OHLC, Trades e Quantity.

A venda do Profit às 10:47 permanece fora do trecho local comparável: a captura teve lacuna e ainda não havia completado novo aquecimento. Ela não é usada como primeira divergência válida. A primeira operação Profit sem correspondente dentro de um trecho local aquecido é a **compra de 12:26–12:47**; o candidato nasce às 12:25, quando Profit e cálculo local já divergem.

Contrafactuais, uma mudança por vez, estão em `ETAPA2A_CONTRAFACTUAIS_CAPTURA_LOCAL_20261021.csv`:

- padrão local: 5 operações, 3 correspondências exatas;
- apenas Volume financeiro: continua com 5;
- apenas agressão por candle: 8 operações, 5 correspondências;
- apenas VWAP contínua nas lacunas: 6 operações, 3 correspondências;
- as três mudanças: 9 operações, 6 correspondências.

Assim, nenhuma troca semântica isolada recupera a paridade sobre a captura local. Faltam negócios e 31,22% dos negócios têm agressor RLP/leilão/direto sem lado utilizável. A evidência aponta primeiro para dados de entrada, não para execução da v5.7.

## Comandos reproduzíveis

```powershell
py -3.11 tools\preparar_paridade_profit_barras.py `
  --barras <privado>\profit_WINZ26_20261021_barras_1min.csv `
  --indicadores <privado>\profit_WINZ26_20261021_indicadores_v5_7.csv `
  --data 2026-10-21 `
  --saida <privado>\WINZ26_20261021_profit_1min_privado.csv `
  --manifesto <privado>\manifesto_preparacao.json

py -3.11 estrategia.py `
  --csv <privado>\WINZ26_20261021_profit_1min_privado.csv `
  --ntsl estrategias\execucao\Modelo_Unificado_Refatorado_v5_7.ntsl `
  --saida <privado>\execucao_v5_7_referencia `
  --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --inputs <privado>\inputs_v5_7_paridade.json `
  --volume-financeiro-ntsl --agressao-referencia-injetada

py -3.11 estrategia.py `
  --csv <privado>\WINZ26_20261021_profit_1min_privado.csv `
  --ntsl estrategias\indicadores\indicador_paridade_modelo_unificado_v5_7_v1_0.ntsl `
  --saida <privado>\indicadores_motor_referencia `
  --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --volume-financeiro-ntsl --agressao-referencia-injetada

py -3.11 tools\comparar_paridade_mesmas_barras.py <argumentos privados> `
  --aquecimento 63 --saida <privado>\comparacao_mesmas_barras_v1.json
```

Os scripts recusam sobrescrever saídas. Os manifestos privados guardam hashes do que já foi processado.

## Repetição em 26/10

O procedimento está estabilizado para repetir 26/10 nas camadas barras, indicadores, candidatos e preenchimentos. Permanecem dois limites: a agressão será novamente uma referência injetada se não houver reconstrução independente equivalente; ordens e posição nativas do Profit continuarão bloqueadas sem exportação própria. O pregão de 26/10 ainda não foi aberto nesta rodada.
