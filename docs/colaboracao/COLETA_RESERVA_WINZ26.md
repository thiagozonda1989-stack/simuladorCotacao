# Coleta da reserva WINZ26 em um CSV

Use o [indicador de coleta v1.0](../../estrategias/indicadores/indicador_coleta_reserva_winz26_1min_v1_0.ntsl) no gráfico de **WINZ26, 1 minuto**, com candles temporais comuns. Ele fornece cinco séries nativas. A opção **Copiar Estudos para Excel** do gráfico acrescenta a data e os preços OHLC e reúne tudo na mesma tabela. [Central de Ajuda da Nelogica](https://ajuda.nelogica.com.br/hc/pt-br/articles/56471751476891-Por-que-n%C3%A3o-consigo-exportar-mais-de-20-000-linhas-para-o-Excel)

## Como exportar

1. No Editor de Estratégias, crie um **Indicador**, cole o fonte, salve como `Coleta_Reserva_WINZ26_1Min_V1_0` e compile. O indicador não tem parâmetros e não envia ordens.
2. Insira o indicador no gráfico de **WINZ26, 1 minuto**. Carregue a sessão inteira de 23/11 e 24/11/2026, os demais pregões fechados destinados à reserva e o pregão anterior ao primeiro dia, para aquecimento. Use o horário do gráfico em America/Sao_Paulo. A cópia tem limite de 20.000 linhas. Se a janela não couber, copie em lotes e confira a primeira e a última data em cada arquivo.
3. Clique com o botão direito no gráfico e selecione **Copiar Estudos para Excel**. Cole em uma planilha vazia. Salve como CSV, mantendo o cabeçalho e os valores numéricos originais. Use ponto e vírgula como separador e vírgula decimal se o Excel estiver em português. Guarde o arquivo no Windows com um nome como `WINZ26_1min_reserva_20261123_20261124.csv`. Um print do contrato, da periodicidade e do período copiado ajuda a identificar a fonte.
4. Confira se o cabeçalho tem `Data` com hora e os quatro preços (`Abertura`, `Máxima`, `Mínima`, `Fechamento)), além das cinco séries abaixo. Se a sua versão nomear os campos pelo número do plot, preserve os nomes originais. Se faltar coluna ou houver linhas vazias nas séries exigidas, envie também o cabeçalho original para conferência.

| Plot | Coluna esperada | Série nativa e uso |
|---|---|---|
| 1 | `v_Trades` | `Trades`, número de negócios no candle |
| 2 | `v_Quantidade_Contratos` | `Quantity`, total de contratos negociados no candle |
| 3 | `v_Volume_Financeiro` | `Volume`, volume financeiro do candle |
| 4 | `v_Saldo_Agressao` | `AgressionVolBalance`, saldo nativo lido no candle, usado pelos perfis |
| 5 | `v_VWAP_Diaria` | `VWAP(1)`, referência nativa para conferência |

A coleta conserva o saldo nativo sem recalcular, diferenciar ou acumular a série. A VWAP nativa é uma referência de auditoria. O protocolo da rodada 19 reconstrói a VWAP usada no motor com os mesmos insumos da rodada 18. Na ingestão, a coluna `v_Trades` corresponde a `Trades`, `v_Quantidade_Contratos` a `Quantity` e `v_Volume_Financeiro` a `Volume`. O saldo conserva o mesmo nome da exportação anterior. [Manual NTSL da Nelogica](https://downloadserver-cdn.nelogica.com.br/content/profit/manual_ntsl/ManualNTSL.pdf) · [Protocolo da rodada 19](evidencias/WINZ26_congelamento_rodada19_v1/README.md)

Teste local do indicador com candles sintéticos pelo compilador do simulador. A primeira compilação no Profit e a conferência do cabeçalho exportado são pendências da captura.