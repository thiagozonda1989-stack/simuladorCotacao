# Captura de paridade da v5.7 em 26/10/2026

Referência do simulador: `ec7b6442359367e1e92abe79d9321894ce442583`. O console foi gerado pela variante `Modelo_Unificado_Refatorado_v5_7_Captura_Paridade.ntsl`, com rótulos de barra de 12:58 a 14:07. A comparação usa barras de 1 minuto. As configurações completas do Profit não constam nos anexos.

## Fontes e validação

| Fonte privada | SHA-256 do original | Cobertura |
|---|---|---|
| Texto colado(3).txt | `65a90e3cc66c1464e0fba0be862036ba568604eadeb1082741cc24212e9de6a2` | 298 linhas, 288 de paridade. Os dois blocos de 144 eventos são idênticos na ordem. |
| operacoes_teste_v.csv | `da6261fcdcd58bb6313ab409bd220fae39766665b513da2a9b554c17511d0a97` | 330 operações WINZ26 em 56 datas, de 13/08 a 19/11/2026. CSV delimitado por ponto e vírgula, decodificado como Windows-1252. |

A análise usa o primeiro bloco de paridade e mantém a ordem dentro dele. O console formata inteiros com separador de milhar, por exemplo `1.304` corresponde a 13:04. O CSV contém identificação da conta e do titular. O repositório guarda este resumo e as contagens agregadas.

## Reentrada confirmada no Profit

| Barra do console | Avaliação | Evidência |
|---|---:|---|
| 13:03 | 7–8 | A estratégia observou posição zerada, pediu compra, observou posição comprada e solicitou alvo e stop. |
| 13:04 | 9–10 | A posição anterior estava zerada na avaliação 9. Com o sinal de compra ativo, a estratégia fez uma nova solicitação. Na avaliação 10, observou nova posição comprada e solicitou alvo e stop próprios. |
| 13:05 | 11 | A estratégia voltou a observar posição zerada. |

A exportação do Profit mostra as operações 181 e 182, rotuladas respectivamente às 13:04 e 13:05. Cada uma abriu e fechou no mesmo minuto exibido e registrou −350 pontos e −R$ 70,00 brutos. O preço de entrada de cada operação coincide com o preço médio observado no console na barra rotulada um minuto antes. O preço de saída coincide com o gatilho de stop solicitado em cada caso. Essa associação vale para as operações conferidas. A captura não fornece segundos efetivos de execução nem comprova a trajetória intrabar.

Esta captura conferiu as exportações do Profit. A [rodada de avaliação pós-preenchimento](evidencias/WINZ26_v5_7_20261021_20261026_pos_preenchimento_v1/README.md) registra o rastreamento posterior no simulador, a matriz de 26/10 e a regressão de 21/10.
