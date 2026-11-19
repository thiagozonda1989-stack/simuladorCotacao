# Etapa 2A — conferência das exportações do Profit Ultra

Pregão de referência: WINZ26, 21/10/2026, candles de 1 minuto. A comparação usa registros desse pregão. Os arquivos de origem permanecem preservados; este registro contém somente evidências agregadas, conforme a política de dados do PR #2.

| Arquivo de origem | Conteúdo conferido | Uso na matriz |
|---|---|---|
| `profit_WINZ26_20261021_barras_1min.csv` | 30.964 registros em 59 datas. No pregão-alvo, 565 candles de 09:00 a 18:24, sem timestamps repetidos, com OHLC, Trades, Quantity e Volume. | Referência para presença de candles, OHLC e unidades de volume. |
| `profit_WINZ26_20261021_indicadores_v5_7.csv` | 29.983 registros em 57 datas. No pregão-alvo, 565 candles e oito séries. Timestamps e OHLC coincidem integralmente com o CSV de barras no recorte. | Referência de indicadores e sinal candidato do indicador. |
| `profit_WINZ26_20261021_posicao.csv` | Relatório de operações com 329 registros no período. Em 21/10, 10 operações de um contrato, com horários e preços de entrada e saída. | Usar como operações executadas. A posição líquida observada por candle e os eventos de envio, alteração e cancelamento seguem indisponíveis. |
| `relatorio_backtest.pdf` | Resumo de 19/08 a 19/11/2026, com 329 operações e saldo de R$ 657,00. | Conferência do período completo. O resultado diário deve vir do recorte do CSV de operações. |

## Divergência confirmada

O Profit contém os candles de 09:02, 09:03 e 09:04. Os três minutos inteiros estão ausentes na captura local entre 09:01:29.821 e 09:05:18.253, conforme o protocolo e a matriz parcial. Essa é a primeira diferença de cobertura identificada. A primeira diferença em valores OHLC nas barras presentes em ambos ainda precisa de comparação com o derivado privado local. A última barra exportada pelo Profit é 18:24; investigar a borda final separadamente.

O Profit registra 10 operações e −R$ 109,00 em 21/10. O replay local publicado registra 5 operações e +R$ 130,00. Essa diferença agregada não identifica a primeira divergência de sinal ou execução. A comparação segue a ordem barras → indicadores → sinais → ordens → preenchimentos → posição.

## Continuação no Windows

1. Juntar os candles pelo timestamp de abertura no fuso de São Paulo e apurar presença, OHLC, Trades e Quantity. Manter Volume em coluna separada.
2. Marcar as lacunas e aplicar o aquecimento do protocolo antes da comparação dos indicadores móveis. Tratar VWAP e agressão acumulada separadamente por dependerem do histórico anterior.
3. Comparar as operações por horário, lado, quantidade e preço. Se reconstruir a posição a partir das operações, confirmar posição inicial e convenção do timestamp e identificar a série como reconstruída. A reconstrução não recupera ordens canceladas nem o estado interno no instante de avaliação do NTSL.
4. Atualizar a matriz de 21/10 antes de repetir em 26/10.

## SHA-256 dos originais

- Barras: `3726e7dd9a821a109120765e4115e6eb352079e9402d9370ae7565ac9555bb2a`
- Indicadores: `76b79ef839ab6b142a0976c7c3ef1a6b7bb7dc2d013434551e861c892a56b946`
- Operações (arquivo nomeado posição): `549e22dea388e5f4e272bc906ac3309e9e88a1de7f53e6184ded5796dbe64479`
- PDF: `87a8691f3cd57cf71ccfdcdaec13e3f83509d0d9d446efa3507831d39f8af8e2`
