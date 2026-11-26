# 20 estratégias da literatura · teste e validação no WINZ26 real

**Fontes:** `estrategias/literatura/lit01…lit20*.ntsl`, geradas por `tools/gerar_estrategias_literatura.py` (os arquivos versionados são idênticos ao gerador, conforme `tests/test_estrategias_literatura.py`). O índice está em `estrategias/literatura/catalogo_literatura.json`.

**Pré-registro:** as estratégias, a ferramenta e o `protocolo.json` (SHA-256 `b2030a1f…`) foram publicados no commit `731c889`, antes da execução.

## Molde comum

Cada estratégia tem um bloco de sinal próprio, adaptado da referência para o WIN de 1 minuto, e o mesmo bloco de risco:
- 1 contrato;
- alvo e stop em múltiplos do ATR(14), limitados entre 50 e 400 pontos (alvo até 800), com stop-limit de folga de 50 pontos;
- tempo máximo, saída pelo sinal oposto quando a referência prevê;
- teto diário com a data guardada em variável (lição da rodada 20), espera de 3 barras após a saída e perda diária máxima de R$ 400;
- zeragem às 17:00.

Os parâmetros padrão seguem a literatura e formam sempre a variação 1.

## As 20 estratégias

| # | Arquivo | Estratégia | Família | Ideia | Referência |
|---|---|---|---|---|---|
| 1 | `lit01_orb` | Rompimento da faixa de abertura (ORB) | tendência | A faixa dos primeiros minutos concentra a descoberta de preço; o rompimento dela tende a continuar no dia. | Crabel, T. (1990). Day Trading with Short Term Price Patterns and Opening Range Breakout. Zarattini, C., Barbon, A. & Aziz, A. (2024). A Profitable Day Trading Strategy for the U.S. Equity Market. SSRN 4729284. |
| 2 | `lit02_bollinger_reversao` | Reversão às bandas de Bollinger | reversão | Fechamento que volta para dentro da banda depois de sair dela sinaliza excesso e retorno à média. | Bollinger, J. (2001). Bollinger on Bollinger Bands. McGraw-Hill. |
| 3 | `lit03_bollinger_squeeze` | Compressão das bandas de Bollinger (squeeze) | tendência | Volatilidade comprimida precede expansão; entra no lado do rompimento da banda. | Bollinger, J. (2001). Bollinger on Bollinger Bands, cap. 15 (The Squeeze). |
| 4 | `lit04_rsi2` | RSI(2) de Connors | reversão | RSI de 2 períodos extremo a favor da tendência longa marca recuo de curto prazo que costuma reverter. | Connors, L. & Alvarez, C. (2009). Short Term Trading Strategies That Work. TradingMarkets. |
| 5 | `lit05_macd` | Cruzamento do MACD | tendência | Cruzamento da diferença entre médias exponenciais com sua própria média indica mudança de momento. | Appel, G. (2005). Technical Analysis: Power Tools for Active Investors. FT Press (MACD criado em 1979). |
| 6 | `lit06_medias_moveis` | Cruzamento de médias móveis | tendência | Média curta acima da longa (com banda) indica tendência de alta; regra testada em 90 anos do DJIA. | Brock, W., Lakonishok, J. & LeBaron, B. (1992). Simple Technical Trading Rules and the Stochastic Properties of Stock Returns. Journal of Finance 47(5). |
| 7 | `lit07_donchian` | Canal de Donchian (Turtle) | tendência | Rompimento da máxima ou mínima de N barras segue a tendência; sai no canal de metade do período. | Donchian, R. (1960). High Finance in Copper. Financial Analysts Journal 16(6). Faith, C. (2007). Way of the Turtle. McGraw-Hill. |
| 8 | `lit08_keltner` | Canal de Keltner | tendência | Fechamento fora do canal de média exponencial ± ATR indica impulso direcional. | Keltner, C. (1960). How to Make Money in Commodities. Raschke, L. & Connors, L. (1995). Street Smarts (versão com ATR). |
| 9 | `lit09_vwap_reversao` | Reversão à VWAP | reversão | Afastamento extremo da VWAP, medido em desvios, tende a voltar ao preço médio do dia. | Berkowitz, S., Logue, D. & Noser, E. (1988). The Total Cost of Transactions on the NYSE. Journal of Finance 43(1) (VWAP como preço justo do dia). |
| 10 | `lit10_vwap_tendencia` | Tendência pela VWAP | tendência | Estar comprado acima da VWAP e vendido abaixo dela captura a tendência do dia. | Zarattini, C. & Aziz, A. (2023). Volume Weighted Average Price (VWAP): The Holy Grail for Day Trading Systems. SSRN 4631351. |
| 11 | `lit11_momento_intradiario` | Momento intradiário (primeira meia hora prevê a última) | momento | O retorno da primeira meia hora (incluindo a noite) prevê o retorno da última meia hora do pregão. | Gao, L., Han, Y., Li, S. Z. & Zhou, G. (2018). Market Intraday Momentum. Journal of Financial Economics 129(2). |
| 12 | `lit12_gap_reversao` | Fechamento do gap de abertura | reversão | Gap de abertura grande tende a ser parcialmente devolvido durante o pregão. | Lou, D., Polk, C. & Skouras, S. (2019). A Tug of War: Overnight versus Intraday Expected Returns. Journal of Financial Economics 134(1) (reversão entre retorno noturno e intradiário). |
| 13 | `lit13_estocastico` | Oscilador estocástico | reversão | Cruzamento de %K sobre %D em zona extrema indica reversão do excesso. | Lane, G. (1984). Lane's Stochastics. Technical Analysis of Stocks & Commodities 2(3). |
| 14 | `lit14_williams_r` | Williams %R | reversão | Saída da zona de sobrevenda ou sobrecompra do %R marca o fim do excesso. | Williams, L. (1973). How I Made One Million Dollars Last Year Trading Commodities. |
| 15 | `lit15_cci` | Commodity Channel Index (CCI) | tendência | CCI acima de +100 indica início de tendência; o desvio médio é aproximado pelo desvio-padrão. | Lambert, D. (1980). Commodity Channel Index: Tools for Trading Cyclical Trends. Commodities Magazine. |
| 16 | `lit16_adx_dmi` | ADX e DMI de Wilder | tendência | DI+ acima de DI− com ADX forte e subindo identifica tendência; a suavização de Wilder usa MediaExp(2n−1). | Wilder, J. W. (1978). New Concepts in Technical Trading Systems. Trend Research. |
| 17 | `lit17_fluxo_agressao` | Desequilíbrio do fluxo de agressão (OFI) | microestrutura | Desequilíbrio persistente entre agressão compradora e vendedora antecipa o movimento de curto prazo. | Cont, R., Kukanov, A. & Stoikov, S. (2014). The Price Impact of Order Book Events. Journal of Financial Econometrics 12(1). Chordia, T. & Subrahmanyam, A. (2004). Order Imbalance and Individual Stock Returns. Journal of Financial Economics 72(3). |
| 18 | `lit18_volume_reversao` | Reversão de movimento com volume anormal | reversão | Movimentos grandes acompanhados de volume alto refletem demanda por liquidez e tendem a reverter. | Campbell, J., Grossman, S. & Wang, J. (1993). Trading Volume and Serial Correlation in Stock Returns. Quarterly Journal of Economics 108(4). |
| 19 | `lit19_reversao_curto_prazo` | Reversão de curto prazo | reversão | Retorno extremo numa janela curta, medido em desvios, tende a ser parcialmente devolvido. | Jegadeesh, N. (1990). Evidence of Predictable Behavior of Security Returns. Journal of Finance 45(3). Lehmann, B. (1990). Fads, Martingales, and Market Efficiency. QJE 105(1). |
| 20 | `lit20_momento_serie_temporal` | Momento de série temporal | momento | O sinal do retorno passado, quando significativo frente à volatilidade, prevê o retorno seguinte. | Moskowitz, T., Ooi, Y. H. & Pedersen, L. H. (2012). Time Series Momentum. Journal of Financial Economics 104(2). |

**Adaptações declaradas:**
- RSI de Cutler, com média simples;
- CCI com desvio-padrão no lugar do desvio médio;
- suavização de Wilder aproximada por MediaExp(2n−1);
- ORB, momento intradiário e gap usam no máximo uma entrada por lado ou por dia;
- o momento intradiário mede o retorno até 09:30 e entra às 16:15;
- o OFI usa o saldo de agressão da base real;
- a reversão com volume usa a quantidade de contratos.

## Protocolo

- **Base:** `win_60s.csv` congelado da rodada 18, SHA-256 `ed9230c9…`, conferido. A base fica fora do Git. Regras de execução congeladas na rodada 20, custo de R$ 0,50 por contrato e lado, 1 tick de slippage.
- **Desenvolvimento:** os 19 pregões de 15/09 a 16/10, quando o WINZ26 ainda não era o contrato principal e havia lacunas.
- **Validação:** os 20 pregões conhecidos, de 19/10 a 18/11.
- **Reserva inédita:** não foi usada.
- **Variações:** 12 por estratégia (a da literatura mais 11 sorteadas na grade com a semente 7). **Cada pregão recebeu 12 replays por estratégia**, ou seja, 240 por pregão no total, listados em `por_pregao/`.
- **Seleção:** maior líquido no desenvolvimento, com pelo menos 19 operações; depois, uma única avaliação nos conhecidos.
- **Controle nulo:** a variação escolhida roda também no gerador sintético v0, sem estrutura, com 60 pregões.
- **Estatística:** p unilateral da média diária por bootstrap de pregão (10.000 reamostragens), ajustado por Holm nas 20 estratégias.

**Critérios:**
- **Aprovada para a reserva:** todos os critérios abaixo, mais p de Holm < 0,05.
  - líquido > 0 no desenvolvimento e nos conhecidos;
  - fator de lucro ≥ 1,1;
  - pelo menos 1 operação por pregão;
  - controle nulo sem lucro significativo.
- **Promissora:** os mesmos critérios, mas sem significância após Holm.
- **Rejeitada:** os demais casos.

## Resultado (ordenado pelo líquido nos 20 conhecidos)

| Estratégia | Variação escolhida | Desenvolvimento | Operações | Acerto | **Conhecidos** | Fator | IC 95% da média diária | p de Holm | Parâmetros da literatura nos conhecidos | Nulo | Status |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| `lit02_bollinger_reversao` | v08 | R$ 1.295 | 117 | 56,4% | **R$ 515** | 1,17 | (-34,45; 89,25) | 1,000 | −R$ 444 | −R$ 428 | promissora (não significativa após Holm) |
| `lit13_estocastico` | v01 | R$ 101 | 120 | 52,5% | **R$ 67** | 1,02 | (-49,15; 59,70) | 1,000 | R$ 67 | −R$ 828 | rejeitada |
| `lit06_medias_moveis` | v01 | R$ 345 | 80 | 35,0% | **R$ 28** | 1,01 | (-62,65; 65,11) | 1,000 | R$ 28 | −R$ 394 | rejeitada |
| `lit12_gap_reversao` | v01 | R$ 39 | 11 | 36,4% | **R$ 2** | 1,00 | (-33,15; 36,85) | 1,000 | R$ 2 | R$ 29 | rejeitada |
| `lit17_fluxo_agressao` | v06 | −R$ 142 | 4 | 0,0% | **−R$ 42** | 0,00 | (-5,70; 0,00) | 1,000 | R$ 68 | −R$ 809 | rejeitada |
| `lit11_momento_intradiario` | v01 | −R$ 21 | 17 | 47,1% | **−R$ 58** | 0,85 | (-20,90; 15,70) | 1,000 | −R$ 58 | −R$ 433 | rejeitada |
| `lit03_bollinger_squeeze` | v11 | −R$ 342 | 49 | 51,0% | **−R$ 62** | 0,92 | (-26,15; 20,25) | 1,000 | −R$ 474 | −R$ 652 | rejeitada |
| `lit01_orb` | v08 | R$ 407 | 26 | 53,8% | **−R$ 159** | 0,81 | (-41,65; 23,50) | 1,000 | −R$ 146 | −R$ 506 | rejeitada |
| `lit10_vwap_tendencia` | v06 | R$ 274 | 72 | 16,7% | **−R$ 194** | 0,87 | (-45,85; 27,85) | 1,000 | R$ 513 | −R$ 773 | rejeitada |
| `lit15_cci` | v04 | R$ 32 | 35 | 28,6% | **−R$ 201** | 0,73 | (-28,05; 6,05) | 1,000 | −R$ 641 | −R$ 94 | rejeitada |
| `lit19_reversao_curto_prazo` | v05 | R$ 1 | 51 | 35,3% | **−R$ 230** | 0,85 | (-66,00; 36,00) | 1,000 | −R$ 245 | −R$ 158 | rejeitada |
| `lit14_williams_r` | v06 | R$ 656 | 120 | 54,2% | **−R$ 374** | 0,88 | (-73,10; 33,35) | 1,000 | −R$ 518 | −R$ 1.121 | rejeitada |
| `lit16_adx_dmi` | v01 | R$ 422 | 77 | 28,6% | **−R$ 429** | 0,72 | (-53,70; 11,85) | 1,000 | −R$ 429 | −R$ 363 | rejeitada |
| `lit07_donchian` | v10 | R$ 988 | 80 | 25,0% | **−R$ 548** | 0,77 | (-82,10; 28,00) | 1,000 | −R$ 1.028 | −R$ 741 | rejeitada |
| `lit04_rsi2` | v12 | −R$ 183 | 120 | 60,0% | **−R$ 619** | 0,63 | (-65,30; 1,95) | 1,000 | −R$ 751 | −R$ 1.235 | rejeitada |
| `lit20_momento_serie_temporal` | v08 | −R$ 49 | 80 | 43,8% | **−R$ 630** | 0,77 | (-80,65; 17,35) | 1,000 | R$ 54 | −R$ 362 | rejeitada |
| `lit18_volume_reversao` | v12 | R$ 711 | 99 | 27,3% | **−R$ 642** | 0,79 | (-99,00; 37,45) | 1,000 | −R$ 1.142 | −R$ 1.008 | rejeitada |
| `lit05_macd` | v10 | R$ 652 | 120 | 37,5% | **−R$ 877** | 0,73 | (-89,30; 1,80) | 1,000 | −R$ 587 | −R$ 1.131 | rejeitada |
| `lit08_keltner` | v10 | R$ 809 | 100 | 20,0% | **−R$ 890** | 0,69 | (-100,00; 12,40) | 1,000 | −R$ 359 | −R$ 753 | rejeitada |
| `lit09_vwap_reversao` | v02 | R$ 1.015 | 110 | 38,2% | **−R$ 928** | 0,77 | (-134,45; 38,60) | 1,000 | −R$ 307 | R$ 123 | rejeitada |

## Leitura

1. **Nenhuma estratégia foi aprovada.** Só a reversão às bandas de Bollinger (período 40, 2,5 desvios, stop 2 ATR) passou nos critérios básicos e ficou como **promissora**: R$ 515 nos conhecidos, fator 1,17 e 56% de acerto. Mas o intervalo da média diária vai de −R$ 34 a +R$ 89 e o p de Holm é 1, então não há evidência estatística.
2. **O desenvolvimento quase não previu os conhecidos.** A correlação de Spearman entre as 12 variações dos dois períodos é negativa ou próxima de zero na maioria das estratégias. Quinze das escolhidas lucraram no desenvolvimento e só quatro nos conhecidos. O desenvolvimento é o período anterior à rolagem, com lacunas, e não representa o contrato principal.
3. **Os parâmetros da literatura, sem seleção, também não se sustentam.** Só seis ficaram positivos nos conhecidos. O maior foi a tendência pela VWAP (R$ 513), mas a variação escolhida no desenvolvimento perdeu R$ 194, o que mostra a instabilidade.
4. **O controle nulo ficou limpo.** Nenhuma estratégia lucrou de forma significativa nos dados sem estrutura, então não há sinal de vazamento de informação futura. Duas fecharam levemente positivas no nulo: VWAP reversão (R$ 123) e gap (R$ 29), ambas com intervalo cruzando zero.
5. **Fluxo de agressão:** a variação escolhida quase não operou nos conhecidos (4 operações). O limiar de z escolhido no desenvolvimento não se transferiu.

## Recomendação

- Não levar nenhuma estratégia à reserva com base nesta rodada.
- Se for testar uma candidata, que seja a reversão às bandas de Bollinger com os parâmetros escolhidos congelados. Ela deve ser avaliada só na reserva inédita, sem novo ajuste, e comparada com a v5.8 original, que segue sendo a referência.
- Para uma nova rodada de busca, usar como desenvolvimento só pregões do contrato principal e exigir um platô de vizinhança antes de qualquer seleção.

## Reprodução

```bash
python -m tools.gerar_estrategias_literatura
python -m tools.validar_estrategias_literatura --base <win_60s.csv da rodada 18> --saida <pasta>
python -m pytest -q tests/test_estrategias_literatura.py
```
