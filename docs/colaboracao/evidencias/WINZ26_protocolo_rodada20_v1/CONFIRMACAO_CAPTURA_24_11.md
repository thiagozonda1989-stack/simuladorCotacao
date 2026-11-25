# Rodada 20 · identificação da captura de 24/11 e verificação do aquecimento

Complemento à cobertura publicada no SHA `cfc6bc2cd40f9f5dbb44bb7c66e7cbc08496f8dd`. PR #2 em rascunho. Replays na reserva até esta verificação: **0**.

## O que o print confirma

O cabeçalho mostra **WINZ26**, **1 Min**, o indicador `Coleta_Reserva_WINZ26_1Min_V1_0` e o rótulo **24/11/2026 18:24**. Os quatro preços OHLC e os valores exibidos de Trades, Quantity, volume financeiro e saldo de agressão batem exatamente com a linha 24/11 18:24 do CSV. A VWAP coincide após arredondar a linha do CSV para a precisão exibida no cabeçalho. Junto com as 565 barras de 09:00 a 18:24 já auditadas, isso confirma a identificação da captura de 24/11. A conferência visual abrange o último rótulo. Os demais candles de 24/11 têm validação de cobertura e consistência no CSV.

O resumo sob o ponteiro informa **23/10/2026 às 09:02**. A data **23/11/2026** na barra inferior aparece no seletor de Replay, que está configurado para IBOV. O print deixa pendentes a abertura de 23/11 para WINZ26 e a comparação do candle fechado de 18:14 desse dia. A imagem original contém identificação da plataforma e permanece fora da publicação.

## Aquecimento proposto para o piloto de 24/11

O Claude aprovou com ressalvas um piloto de 24/11 com 23/11 como pregão de aquecimento, usando a captura nova como fonte canônica e reservando 23/11 apenas ao aquecimento nessa execução. A sequência esperada para as 86 últimas barras de 23/11 vai de 16:59 a 18:24. [Parecer Claude sobre a rodada 20](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7152416269)

| Fonte | Rótulos observados na janela final | Duplicatas | Rótulos faltantes |
|---|---:|---:|---:|
| `Coleta_Reserva_WINZ26_1Min_V1_0.csv` | 86/86 | 0 | 0 |
| `SONDA_S1_STOP_barras.csv` | 76/86 | 0 | 10, de 18:15 a 18:24 |

A nova fonte passa na checagem de continuidade. Essa janela inclui o candle de 18:14 cujo OHLC difere da captura anterior. Para confirmar a fonte, no gráfico de WINZ26 em 1 minuto, posicione o cursor no candle **23/11/2026 18:14** e capture o resumo com a data e os quatro preços. Para confirmar a abertura, posicione o cursor no primeiro candle de **23/11/2026** e inclua na imagem a transição entre pregões. Se o primeiro rótulo for 09:03, a imagem documenta a ausência de 09:00–09:02 naquela visualização.

`audit_warmup_tail` confere a janela final por timestamp e rejeita buracos e duplicatas no trecho. O novo teste sintético confirmou que uma lacuna tardia no pregão anterior muda a média do ATR na abertura seguinte, mesmo com `v_Aquecido=true`. Com a janela anterior contínua, a média coincide nos dois modos de histórico. Com o frame iniciado no pregão avaliado, o aquecimento da v5.8 aparece a partir da barra 87. **138 testes locais passaram.**

Os perfis e critérios do protocolo publicado permanecem fixados. A revisão do Gemini para esta rodada não estava no PR na última conferência. Caso a consolidação libere apenas 24/11, o resultado deve ser publicado como piloto descritivo, sem aprovação formal. [Protocolo pré-replay](https://github.com/thiagozonda1989-stack/simuladorCotacao/blob/cfc6bc2cd40f9f5dbb44bb7c66e7cbc08496f8dd/docs/colaboracao/evidencias/WINZ26_protocolo_rodada20_v1/README.md)