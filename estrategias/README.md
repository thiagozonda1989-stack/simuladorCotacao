# Estratégias NTSL do ProfitRTD

Este diretório preserva as versões criadas durante o projeto. Os arquivos foram copiados sem alterar o conteúdo original.

## Famílias

- `Modelo_Unificado_Refatorado_v5_7`: modelo de 1 minuto com regime, VWAP, volume e gestão de risco.
- `modelo_scalper_v1_1` até `v2_3`: evolução do scalper de velocidade, aceleração e agressão em barras de 5 segundos.
- `modelo_scalper_micro_hft_v3_0`: experimento de microestrutura/fluxo para 1 segundo.
- `modelo_micro_scalper_v4_0` até `v4_3_ranges`: estratégia curta com filtros de preço, fluxo e book; versões recentes usam 5 segundos.
- `modelo_1c_antecipado_profit_v1_0/v1_1`: tradução para NTSL de um classificador supervisionado antecipado.
- `indicadores`: diagnóstico dos filtros, marcação de entradas, captura de features e linhas de book.

## Compatibilidade

`status_profit` e `status_simulador` são evidências diferentes. Um código pode compilar no Profit e não compilar no simulador porque o simulador implementa apenas parte do NTSL.

As incompatibilidades atuais incluem `VWAP`, `CalcTime`, `AgressionVolBalance`, `BuyOfferCount`, `Plot5+`, `PlotText` e `SetPlotColor`. Elas estão registradas no catálogo e definem o backlog de unificação.

Os indicadores de dataset possuem muitas chamadas `PlotN` porque a exportação do Profit usa cada plot como uma coluna. Eles não enviam ordens.
