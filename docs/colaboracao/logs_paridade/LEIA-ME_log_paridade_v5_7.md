# Console da v5.7 — análise de paridade

O CSV normaliza 633 mensagens de 13/08 a 19/11/2026. Há 541 solicitações de entrada, 34 de alvo, 34 de stop e 24 observações de mudança de posição. Essas contagens representam mensagens do console, incluindo reavaliações e possíveis repetições da captura, e não totais de operações.

## Formato

O CSV usa UTF-8 com BOM e separador ponto e vírgula. As primeiras colunas são date (AAAA-MM-DD) e time (HH:MM). A data NTSL 1261026 foi convertida para 2026-10-26. Os preços têm decimal com ponto e sem separador de milhar. Campos ausentes ficam vazios. A linha de origem e o bloco delimitado pelos marcadores do console preservam a ordem da cópia. Alguns registros já tinham date/time antes de PARIDADE, outros tinham os campos depois do evento. Ambos foram aceitos e as datas e horas duplicadas foram conferidas.

Os dois fontes NTSL atualizados emitem date;time;PARIDADE;evento;campos. No fonte, date e time conservam a representação numérica do Profit. A normalização ISO é feita no CSV. As regras e os parâmetros de execução foram preservados. Esta mudança de formato ainda precisa ser compilada no Profit.

## WINZ26 em 26/10

No bloco detalhado, a avaliação marcada como 13:03 mostra uma compra solicitada, posição observada de +1 a 177.565, alvo de 178.015 e solicitação de stop de venda com gatilho em 177.215 e limite em 177.210. Às 13:04 aparece a zeragem observada, bem como outro ciclo com posição de +1 a 176.815 e stop de gatilho 176.465 e limite 176.460. Às 13:05 aparece nova zeragem observada.

O relatório de operações identifica o primeiro preenchimento de entrada e saída às 13:04, com saída a 177.215. O log usa o relógio da avaliação da estratégia, enquanto o relatório usa o rótulo da execução. Essa diferença deve ser investigada, sem deslocar automaticamente todos os horários em um minuto.

O log serve para rastrear a observação da posição e a solicitação da proteção. O preço preenchido, a aceitação da ordem, o disparo, o cancelamento OCO e a sequência intrabar exigem o relatório de operações ou histórico de ordens. Os blocos da captura devem permanecer separados ao contar eventos de uma rodada.
