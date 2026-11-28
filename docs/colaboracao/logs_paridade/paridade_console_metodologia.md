# Console v5.7 — consolidação de vários pregões

Os anexos se sobrepõem e exibem marcadores de execução, debug e trechos omitidos com reticências. O CSV preserva cada fonte e a ordem original; não some os dois para estimar operações. O resumo é por data e arquivo. Os registros são mensagens, incluindo reavaliações e possíveis repetições.

| Arquivo | Mensagens | Datas com eventos | Primeira data | Última data |
|---|---:|---:|---|---|
| Texto colado (2).txt | 15574 | 54 | 2026-08-13 | 2026-11-19 |
| Texto colado(2).txt | 14581 | 51 | 2026-08-13 | 2026-11-19 |

## Normalização

Os dois pares date/time de cada linha foram conferidos antes de reduzir a um par. Datas foram convertidas para AAAA-MM-DD, horas para HH:MM e valores para decimal com ponto. Os CSVs usam UTF-8 com BOM e ponto e vírgula. Bloco é a divisão pelos marcadores do texto, incluindo reticências, e não identifica uma execução independente. Linha é a posição no arquivo original.

## Caso das 13h04 em 26/10

Na avaliação rotulada 13h03, o console registra compra solicitada, posição +1 a 177.565, alvo 178.015 e stop solicitado com gatilho 177.215 e limite 177.210. Às 13h04 registra a zeragem observada e uma segunda compra observada a 176.815, com stop 176.465/176.460 e alvo 177.265. A segunda zeragem é observada às 13h05. A sequência aparece repetida na captura. O relatório de operações anterior rotula a primeira entrada e saída às 13h04; preservar os dois relógios antes de comparar.

O console serve para comparar o momento em que a posição ficou visível à estratégia e a proteção foi solicitada. Preço e horário de preenchimento vêm do relatório de operações. Aceitação, disparo e cancelamento OCO exigem histórico de ordens, quando disponível. Ausência de mensagens num dia ou horário não prova ausência de atividade.
