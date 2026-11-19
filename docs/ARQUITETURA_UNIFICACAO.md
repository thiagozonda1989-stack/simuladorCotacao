# Arquitetura de unificação

## Estado atual

O simulador possui três caminhos de entrada: exportação do indicador Profit, Negócios e candles OHLC. Estratégias NTSL são executadas uma vez no fechamento de cada barra. Book e agressão só existem quando já foram exportados como colunas na mesma linha.

## Arquitetura alvo

```text
Arquivos brutos imutáveis
  ├─ Negócios
  ├─ Preços
  └─ Ofertas
          │
          ▼
Inventário + validação + manifesto de fontes
          │
          ▼
Normalização de eventos e junção temporal causal
          │
          ├─ dataset de eventos Tick a Tick
          ├─ candles 1s/5s/1min
          └─ dataset supervisionado com targets separados
          │
          ▼
Motor de execução
  ├─ replay por candle, explicitamente aproximado
  └─ replay por evento/tick, com latência, spread e fila configuráveis
          │
          ▼
Walk-forward → Profit Replay → conta simulada
```

## Oportunidades de integração imediata

1. Fazer o `Engine` respeitar `segmento` e duração real das lacunas.
2. Implementar as funções usadas pelas estratégias publicadas: `VWAP`, `CalcTime`, `AgressionVolBalance`, `BuyOfferCount`, `SellOfferCount`, `Plot5+`, `PlotText` e `SetPlotColor`.
3. Separar plots de exportação de features dos plots visuais, permitindo mais de quatro séries sem impactar o replay.
4. Adicionar um carregador canônico capaz de unir Negócios, Preços e Ofertas causalmente.
5. Criar modo event-driven. Estratégias de 1s/5s não devem ser chamadas de Tick a Tick quando executadas somente no fechamento.
6. Modelar custos, slippage, latência, fila, preenchimento parcial e validade do book.
7. Adicionar comparação automática: sinais do simulador versus sinais/execuções exportados pelo Profit.
8. Usar walk-forward com vários blocos e um teste final intocado.

## Critérios de paridade

- mesmo número e lado dos sinais;
- mesmo preço teórico dentro de um tick;
- mesma posição após cada evento;
- mesmos cancelamentos e substituições de ordens;
- explicação explícita para divergências intrabar;
- nenhuma ordem atravessando lacuna sem política configurada;
- resultado líquido com custos separado do resultado bruto.
