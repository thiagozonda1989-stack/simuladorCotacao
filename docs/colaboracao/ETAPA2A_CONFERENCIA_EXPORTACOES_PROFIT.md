# Etapa 2A — conferência e comparação de 21/10/2026

Pregão de referência: WINZ26 em 21/10/2026, candles de 1 minuto, timestamp na abertura da barra em `America/Sao_Paulo`, avaliação da estratégia no fechamento e execução elegível na barra seguinte. O recorte usa somente o dia-alvo. Custos e slippage permanecem zerados para paridade mecânica.

Os CSVs de origem e o JSON detalhado da conferência permanecem privados em `C:\Users\thiag\Documents\ProfitRTD`. Este documento e a matriz publicam somente método e agregados.

## Inventário das fontes

| Fonte | Recorte de 21/10 | Uso |
|---|---:|---|
| `profit_WINZ26_20261021_barras_1min.csv` | 565 barras, 09:00–18:24, sem timestamp repetido | OHLC, Trades, Quantity e Volume financeiro do Profit |
| `profit_WINZ26_20261021_indicadores_v5_7.csv` | 565 barras e oito séries; timestamps/OHLC iguais ao CSV de barras | Indicadores e sinal candidato |
| `profit_WINZ26_20261021_posicao.csv` | 10 operações completas de um contrato | Execuções; não contém eventos de ordens nem posição observada por candle |
| `WINZ26_20261021_1min_paridade.csv` | 563 barras, 09:00–18:31, sem timestamp repetido | Derivado privado da captura local |
| `simulador_v5_7_20261021/execucoes.csv` | 5 operações, 10 preenchimentos | Execuções do replay local |

As sequências temporais dos dois conjuntos de barras estão ordenadas e não têm duplicidades no recorte.

## Barras

- Há 562 horários comuns.
- Profit exclusivo: 09:02, 09:03 e 09:04. A ausência desses minutos no derivado local está confirmada.
- Local exclusivo: 18:31. O Profit termina às 18:24; essa borda não é comparável.
- Na primeira barra comum, 09:00, a abertura coincide em 212.900, mas já divergem máxima (213.015 vs 212.900), mínima (212.365 vs 212.380), fechamento (212.380 vs 212.440), Trades (6.172 vs 902) e Quantity (69.378 vs 3.137). A primeira diferença de abertura ocorre às 09:01 (212.400 vs 212.440).
- Das 562 barras comuns, abertura coincide em 410, máxima em 556, mínima em 555 e fechamento em 534. Trades e Quantity não coincidem em nenhuma barra.
- `Volume` do Profit é financeiro e foi mantido separado de `Quantity`; seu total no recorte é 773.308.875.044. Não foi comparado como se fosse contratos.

Isso distingue a ausência de negócios da falha de captura: 09:02–09:04 têm barras e negócios no Profit, portanto a ausência local é uma descontinuidade de captura, não ausência de negociação.

## Indicadores e sinais candidatos

Foi aplicado aquecimento de 63 candles depois de cada lacuna/novo segmento. Restaram 324 barras comparáveis:

- 10:07–10:30: 24 barras;
- 11:35–16:00: 266 barras;
- 17:03–17:36: 34 barras.

Mesmo nesses trechos, há divergências. A primeira ocorre às 10:07 em VWAP, desvio, média do ATR, agressão e ZScore. ATR diverge primeiro às 10:14; regime, às 10:20. Em 324 sinais candidatos, 312 coincidem e 12 divergem; a primeira divergência é 12:25, com compra no Profit e zero local.

Duas diferenças semânticas foram confirmadas:

1. O ZScore exportado pelo Profit é compatível com a série `Volume` financeira. O motor local atualmente usa contratos como `Volume`.
2. O `AgressionVolBalance` exportado pelo Profit se comporta como saldo da barra: correlação 0,9781 com `agressão_compra - agressão_venda` local e mesmo sinal em 536 de 562 barras comuns. O motor local acumula essa série por segmento. Por isso, chamá-la de “agressão acumulada” entre plataformas é incorreto sem ajustar a semântica.

VWAP e agressão foram sinalizados separadamente: o simulador reinicia ambos nas lacunas; o Profit conserva histórico contínuo. O aquecimento torna as janelas móveis novamente avaliáveis, mas não restaura acumuladores intradiários. Logo, VWAP e agressão permanecem divergentes mesmo depois de 63 barras.

O campo `v_Sinal` é candidato do indicador. Ele não inclui sozinho horário permitido, densidade, posição atual, ordens pendentes nem a regra de execução na barra seguinte. Não deve ser contado como entrada executada.

## Operações, ordens e posição

O simulador numera `barra` a partir de 1; a associação correta é `candles.indice = execucoes.barra - 1`. Com essa convenção:

- Profit: 10 operações completas;
- simulador: 5 operações completas;
- três operações coincidem exatamente em entrada, saída, lado, quantidade e preços: 10:09–10:16, 10:17–10:19 e 12:48–13:06;
- a primeira operação do Profit sem correspondente local é venda de um contrato às 10:47 por 211.880, encerrada às 11:33 por 211.430.

Às 10:46, o indicador Profit registra candidato de venda, enquanto o cálculo local registra zero. O trecho local tinha apenas 14 barras desde a lacuna iniciada às 10:33, portanto está fora do aquecimento de 63 barras. Há evidência de divergência anterior na camada de estado/indicador e sinal; não há evidência para atribuir a ausência à execução. Os eventos de envio, alteração e cancelamento de ordens do Profit continuam indisponíveis.

A posição do Profit foi reconstruída das operações executadas e é explicitamente **derivada**. A primeira divergência reconstruída ocorre às 10:47: Profit vendido e simulador zerado. A reconstrução não substitui uma série nativa de posição/preço médio por candle e não recupera ordens canceladas.

## Método reproduzível

O script `tools/comparar_paridade_profit_win.py`:

- lê os formatos originais sem modificá-los;
- filtra explicitamente o dia solicitado;
- registra nome e SHA-256 de cada entrada;
- valida ordem temporal e duplicidades;
- gera apenas agregados e primeiras divergências;
- recusa sobrescrever a saída, permitindo processar somente um conjunto novo/novo hash.

Execução usada no Windows, com os caminhos privados abreviados:

```powershell
py -3.11 tools\comparar_paridade_profit_win.py `
  --profit-barras <ProfitRTD>\profit_WINZ26_20261021_barras_1min.csv `
  --profit-indicadores <ProfitRTD>\profit_WINZ26_20261021_indicadores_v5_7.csv `
  --profit-operacoes <ProfitRTD>\profit_WINZ26_20261021_posicao.csv `
  --local-barras <ProfitRTD>\derivados_etapa2a_20261119\WINZ26_20261021_1min_paridade.csv `
  --simulador-execucoes <ProfitRTD>\derivados_etapa2a_20261119\simulador_v5_7_20261021\execucoes.csv `
  --simulador-candles <ProfitRTD>\derivados_etapa2a_20261119\simulador_v5_7_20261021\candles.csv `
  --saida <ProfitRTD>\derivados_etapa2a_20261119\comparacao_profit_local_20261021_v1.json
```

O JSON privado é o registro do que já foi processado; os hashes impedem confundir uma nova exportação com esta rodada.

## SHA-256 das fontes

- Barras Profit: `3726e7dd9a821a109120765e4115e6eb352079e9402d9370ae7565ac9555bb2a`
- Indicadores Profit: `76b79ef839ab6b142a0976c7c3ef1a6b7bb7dc2d013434551e861c892a56b946`
- Operações Profit: `549e22dea388e5f4e272bc906ac3309e9e88a1de7f53e6184ded5796dbe64479`
- Derivado local: `92b10ff97e9c0ff7b2ce03e4ffef33496b67d1dea8b962d8e7638f3c2cc1cc4c`
- Execuções locais: `3142a56a17c3afe17d12fd095c325e6bf7d0a9681b4cf2bf32d8d55fd32e2030`
- Candles do replay: `3b5ad32b5cc67c3bccb0c375a70083bf3d0028eb9ae6512839328b0e26800c1c`

## Pendências

- eventos de ordens do Profit (envio, alteração, cancelamento e OCO);
- posição e preço médio nativos por candle no Profit;
- decisão de paridade para `Volume` financeiro versus contratos;
- correção/parametrização explícita da semântica de `AgressionVolBalance` no simulador;
- evidência causal de book histórico; permanece fora desta rodada;
- repetir o procedimento em 26/10 somente depois de estabilizar essas convenções.
