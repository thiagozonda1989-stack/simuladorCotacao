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

## Fronteira entre o replay por candle e o motor por evento

A v0.13.0 integra as fontes antes da agregação e usa os segmentos também na execução NTSL por candle.
A fila de ordens, a prioridade, a capacidade de execução por nível e a mudança de stop dentro da barra ainda exigem um motor separado.

Para um futuro replay por evento, o contrato de entrada deve distinguir atualização de livro, negócio e atualização de preço.
Um relógio monotônico precisa ordenar cada evento por timestamp e sequência comprovadamente compartilhada.
O motor deve manter um estado de livro por ativo e pregão, despertar ordens somente após sua latência configurada e publicar o rastro
de sinal, ordem, execução e posição, incluindo ordens pendentes, canceladas e preenchidas parcialmente.
Snapshots agregados servem para testar hipóteses de liquidez. Prioridade e posição real na fila exigem mensagens por ordem ou
regras explícitas de aproximação, com a hipótese registrada em cada execução.

## Motor por negócios implementado na v0.14.0

O replay NTSL agora tem um modo por negócios ordenados por timestamp e sequência, incluindo eventos integrados. Os negócios são a unidade de avaliação e de histórico do modelo. Latência em milissegundos e orçamento de quantidade por evento permitem simular preenchimento parcial. O histórico de candle continua disponível no motor anterior.

A simulação de fila por ordem e o replay de atualizações de book entre negócios permanecem dependentes de um feed por ordem. Valide sinais e preenchimentos com o comparador usando referências observadas antes de concluir que uma estratégia tem paridade com o Profit.
