"""Gera as 20 estratégias da literatura em NTSL a partir de um molde comum.

Cada estratégia tem um bloco de sinal próprio, inspirado na referência citada e
adaptado para o WIN em 1 minuto, e o mesmo bloco de risco: alvo e stop em
múltiplos do ATR, stop-limit com folga, tempo máximo, teto diário pela data
guardada em variável, espera depois da saída, perda diária máxima e zeragem às
17:00. Os parâmetros padrão seguem a referência. As grades de variação ficam
em `ESTRATEGIAS[...]["grade"]`.

Uso: python -m tools.gerar_estrategias_literatura   (reescreve estrategias/literatura/)
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "estrategias" / "literatura"

COMUM_INPUTS = """  p_AlvoATR({alvo});
  p_StopATR({stop});
  p_PeriodoATR(14);
  p_StopMin(50);
  p_StopMax(400);
  p_Folga(50);
  p_TempoMax({tempo});
  p_MaxEntradasDia({maxdia});
  p_Espera(3);
  p_PerdaMaxDia(400);
  p_Lote(1);
  p_Aquecimento({aquec});
  p_HoraInicio({hini});
  p_HoraFimEntradas({hfim});
  p_HoraZeragem(1700);
"""
COMUM_VARS = """  v_SinalCompra, v_SinalVenda, v_SaiCompra, v_SaiVenda : Boolean;
  v_ATR, v_AlvoSinal, v_StopSinal, v_Alvo, v_Stop, v_FolgaT : Float;
  v_FechAnterior, v_UltimoFech, v_AberturaDia : Float;
  v_Posicionado, v_EstavaPosicionado, v_PodeEntrar, v_Zerar : Boolean;
  v_BarraEntrada, v_BarraSaida, v_EntradasDia, v_DataContagem, v_BarrasDia : Integer;
"""
COMUM_PRE = """  v_SinalCompra := False;
  v_SinalVenda := False;
  v_SaiCompra := False;
  v_SaiVenda := False;
  v_ATR := AvgTrueRange(p_PeriodoATR, 0);
  if Date <> v_DataContagem then
  begin
    v_DataContagem := Date;
    v_EntradasDia := 0;
    v_FechAnterior := v_UltimoFech;
    v_AberturaDia := Open;
    v_BarrasDia := 0;
  end;
  v_BarrasDia := v_BarrasDia + 1;
"""
COMUM_POS = """
  { ---------------- bloco de risco comum ---------------- }
  v_AlvoSinal := Round(Min(Max(p_AlvoATR * v_ATR, p_StopMin), 2 * p_StopMax) / 5) * 5;
  v_StopSinal := Round(Min(Max(p_StopATR * v_ATR, p_StopMin), p_StopMax) / 5) * 5;
  v_FolgaT := Round(p_Folga / 5) * 5;
  v_Posicionado := IsBought or IsSold;
  if v_Posicionado and (not v_EstavaPosicionado) then
    v_BarraEntrada := CurrentBar;
  if v_EstavaPosicionado and (not v_Posicionado) then
    v_BarraSaida := CurrentBar;
  v_Zerar := (Time >= p_HoraZeragem)
             or (v_Posicionado and (CurrentBar - v_BarraEntrada >= p_TempoMax))
             or (IsBought and v_SaiCompra) or (IsSold and v_SaiVenda);
  v_PodeEntrar := (not v_Posicionado) and (CurrentBar > p_Aquecimento)
                  and (Time >= p_HoraInicio) and (Time <= p_HoraFimEntradas)
                  and (v_EntradasDia < p_MaxEntradasDia)
                  and (CurrentBar >= v_BarraSaida + p_Espera)
                  and (DailyResult > -p_PerdaMaxDia);

  if v_Posicionado and v_Zerar then
  begin
    if IsBought then SellToCoverAtMarket(p_Lote)
    else BuyToCoverAtMarket(p_Lote);
  end
  else if IsBought then
  begin
    SellToCoverLimit(BuyPrice + v_Alvo, p_Lote);
    SellToCoverStop(BuyPrice - v_Stop, BuyPrice - v_Stop - v_FolgaT, p_Lote);
  end
  else if IsSold then
  begin
    BuyToCoverLimit(SellPrice - v_Alvo, p_Lote);
    BuyToCoverStop(SellPrice + v_Stop, SellPrice + v_Stop + v_FolgaT, p_Lote);
  end
  else if v_PodeEntrar then
  begin
    if v_SinalCompra then
    begin
      v_Alvo := v_AlvoSinal;
      v_Stop := v_StopSinal;
      BuyAtMarket(p_Lote);
      v_EntradasDia := v_EntradasDia + 1;
    end
    else if v_SinalVenda then
    begin
      v_Alvo := v_AlvoSinal;
      v_Stop := v_StopSinal;
      SellShortAtMarket(p_Lote);
      v_EntradasDia := v_EntradasDia + 1;
    end;
  end;

  v_EstavaPosicionado := v_Posicionado;
  v_UltimoFech := Close;
"""

GRADE_RISCO = {"p_AlvoATR": [1.5, 2.0, 3.0], "p_StopATR": [1.0, 1.5, 2.0], "p_TempoMax": [15, 30, 60]}

ESTRATEGIAS = {
    "lit01_orb": dict(
        titulo="Rompimento da faixa de abertura (ORB)",
        referencia="Crabel, T. (1990). Day Trading with Short Term Price Patterns and Opening Range Breakout. "
                   "Zarattini, C., Barbon, A. & Aziz, A. (2024). A Profitable Day Trading Strategy for the U.S. Equity Market. SSRN 4729284.",
        ideia="A faixa dos primeiros minutos concentra a descoberta de preço; o rompimento dela tende a continuar no dia.",
        familia="tendência", risco=dict(alvo=3.0, stop=1.5, tempo=120, maxdia=2, aquec=20, hini=905, hfim=1600),
        inputs="  p_BarrasAbertura(15);\n",
        vars="  v_MaxAb, v_MinAb : Float;\n  v_ComprouDia, v_VendeuDia : Boolean;\n",
        sinal="""  if v_BarrasDia = 1 then
  begin
    v_MaxAb := High;
    v_MinAb := Low;
    v_ComprouDia := False;
    v_VendeuDia := False;
  end
  else if v_BarrasDia <= p_BarrasAbertura then
  begin
    v_MaxAb := Max(v_MaxAb, High);
    v_MinAb := Min(v_MinAb, Low);
  end;
  if (v_BarrasDia > p_BarrasAbertura) and (not v_ComprouDia) and (Close > v_MaxAb) then
  begin
    v_SinalCompra := True;
  end;
  if (v_BarrasDia > p_BarrasAbertura) and (not v_VendeuDia) and (Close < v_MinAb) then
  begin
    v_SinalVenda := True;
  end;
  if IsBought then v_ComprouDia := True;
  if IsSold then v_VendeuDia := True;
""",
        grade={"p_BarrasAbertura": [5, 15, 30]}),
    "lit02_bollinger_reversao": dict(
        titulo="Reversão às bandas de Bollinger",
        referencia="Bollinger, J. (2001). Bollinger on Bollinger Bands. McGraw-Hill.",
        ideia="Fechamento que volta para dentro da banda depois de sair dela sinaliza excesso e retorno à média.",
        familia="reversão", risco=dict(alvo=2.0, stop=1.5, tempo=30, maxdia=6, aquec=40, hini=915, hfim=1645),
        inputs="  p_Periodo(20);\n  p_Desvios(2.0);\n",
        vars="  v_Media, v_Desvio, v_Sup, v_Inf : Float;\n",
        sinal="""  v_Media := Media(p_Periodo, Close);
  v_Desvio := StdDevs(Close, p_Periodo);
  v_Sup := v_Media + p_Desvios * v_Desvio;
  v_Inf := v_Media - p_Desvios * v_Desvio;
  v_SinalCompra := (Close[1] < v_Inf[1]) and (Close > v_Inf);
  v_SinalVenda := (Close[1] > v_Sup[1]) and (Close < v_Sup);
  v_SaiCompra := Close >= v_Media;
  v_SaiVenda := Close <= v_Media;
""",
        grade={"p_Periodo": [20, 40, 60], "p_Desvios": [2.0, 2.5, 3.0]}),
    "lit03_bollinger_squeeze": dict(
        titulo="Compressão das bandas de Bollinger (squeeze)",
        referencia="Bollinger, J. (2001). Bollinger on Bollinger Bands, cap. 15 (The Squeeze).",
        ideia="Volatilidade comprimida precede expansão; entra no lado do rompimento da banda.",
        familia="tendência", risco=dict(alvo=3.0, stop=1.5, tempo=60, maxdia=4, aquec=150, hini=915, hfim=1630),
        inputs="  p_Periodo(20);\n  p_Desvios(2.0);\n  p_Janela(120);\n  p_Tolerancia(1.1);\n",
        vars="  v_Media, v_Desvio, v_Sup, v_Inf, v_Largura, v_MinLargura : Float;\n  v_Comprimido : Boolean;\n",
        sinal="""  v_Media := Media(p_Periodo, Close);
  v_Desvio := StdDevs(Close, p_Periodo);
  v_Sup := v_Media + p_Desvios * v_Desvio;
  v_Inf := v_Media - p_Desvios * v_Desvio;
  if v_Media > 0 then v_Largura := (v_Sup - v_Inf) / v_Media else v_Largura := 0;
  v_MinLargura := Lowest(v_Largura, p_Janela);
  v_Comprimido := v_Largura[1] <= p_Tolerancia * v_MinLargura[1];
  v_SinalCompra := v_Comprimido and (Close > v_Sup);
  v_SinalVenda := v_Comprimido and (Close < v_Inf);
  v_SaiCompra := Close < v_Media;
  v_SaiVenda := Close > v_Media;
""",
        grade={"p_Janela": [60, 120, 240], "p_Tolerancia": [1.05, 1.1, 1.25]}),
    "lit04_rsi2": dict(
        titulo="RSI(2) de Connors",
        referencia="Connors, L. & Alvarez, C. (2009). Short Term Trading Strategies That Work. TradingMarkets.",
        ideia="RSI de 2 períodos extremo a favor da tendência longa marca recuo de curto prazo que costuma reverter.",
        familia="reversão", risco=dict(alvo=2.0, stop=2.0, tempo=30, maxdia=6, aquec=210, hini=915, hfim=1645),
        inputs="  p_PeriodoRSI(2);\n  p_Tendencia(200);\n  p_Saida(5);\n  p_Limite(10);\n",
        vars="  v_Ganho, v_Perda, v_MG, v_MP, v_RSI, v_MediaLonga, v_MediaSaida : Float;\n",
        sinal="""  v_Ganho := Max(Close - Close[1], 0);
  v_Perda := Max(Close[1] - Close, 0);
  v_MG := Media(p_PeriodoRSI, v_Ganho);
  v_MP := Media(p_PeriodoRSI, v_Perda);
  if v_MG + v_MP > 0 then v_RSI := 100 * v_MG / (v_MG + v_MP) else v_RSI := 50;
  v_MediaLonga := Media(p_Tendencia, Close);
  v_MediaSaida := Media(p_Saida, Close);
  v_SinalCompra := (Close > v_MediaLonga) and (v_RSI < p_Limite);
  v_SinalVenda := (Close < v_MediaLonga) and (v_RSI > 100 - p_Limite);
  v_SaiCompra := Close > v_MediaSaida;
  v_SaiVenda := Close < v_MediaSaida;
""",
        grade={"p_Tendencia": [100, 200, 300], "p_Limite": [5, 10, 20]}),
    "lit05_macd": dict(
        titulo="Cruzamento do MACD",
        referencia="Appel, G. (2005). Technical Analysis: Power Tools for Active Investors. FT Press (MACD criado em 1979).",
        ideia="Cruzamento da diferença entre médias exponenciais com sua própria média indica mudança de momento.",
        familia="tendência", risco=dict(alvo=2.0, stop=1.5, tempo=60, maxdia=6, aquec=60, hini=915, hfim=1645),
        inputs="  p_Rapida(12);\n  p_Lenta(26);\n  p_Sinal(9);\n",
        vars="  v_MACD, v_Linha : Float;\n",
        sinal="""  v_MACD := MediaExp(p_Rapida, Close) - MediaExp(p_Lenta, Close);
  v_Linha := MediaExp(p_Sinal, v_MACD);
  v_SinalCompra := (v_MACD > v_Linha) and (v_MACD[1] <= v_Linha[1]);
  v_SinalVenda := (v_MACD < v_Linha) and (v_MACD[1] >= v_Linha[1]);
  v_SaiCompra := v_MACD < v_Linha;
  v_SaiVenda := v_MACD > v_Linha;
""",
        grade={"p_Rapida": [6, 12], "p_Lenta": [26, 52], "p_Sinal": [9, 18]}),
    "lit06_medias_moveis": dict(
        titulo="Cruzamento de médias móveis",
        referencia="Brock, W., Lakonishok, J. & LeBaron, B. (1992). Simple Technical Trading Rules and the Stochastic "
                   "Properties of Stock Returns. Journal of Finance 47(5).",
        ideia="Média curta acima da longa (com banda) indica tendência de alta; regra testada em 90 anos do DJIA.",
        familia="tendência", risco=dict(alvo=3.0, stop=1.5, tempo=90, maxdia=4, aquec=210, hini=915, hfim=1630),
        inputs="  p_Curta(5);\n  p_Longa(50);\n  p_Banda(0.0005);\n",
        vars="  v_Curta, v_Longa : Float;\n  v_Acima, v_Abaixo : Boolean;\n",
        sinal="""  v_Curta := Media(p_Curta, Close);
  v_Longa := Media(p_Longa, Close);
  v_Acima := v_Curta > v_Longa * (1 + p_Banda);
  v_Abaixo := v_Curta < v_Longa * (1 - p_Banda);
  v_SinalCompra := v_Acima and (not v_Acima[1]);
  v_SinalVenda := v_Abaixo and (not v_Abaixo[1]);
  v_SaiCompra := v_Curta < v_Longa;
  v_SaiVenda := v_Curta > v_Longa;
""",
        grade={"p_Curta": [1, 5, 10], "p_Longa": [50, 150, 200], "p_Banda": [0.0, 0.0005]}),
    "lit07_donchian": dict(
        titulo="Canal de Donchian (Turtle)",
        referencia="Donchian, R. (1960). High Finance in Copper. Financial Analysts Journal 16(6). "
                   "Faith, C. (2007). Way of the Turtle. McGraw-Hill.",
        ideia="Rompimento da máxima ou mínima de N barras segue a tendência; sai no canal de metade do período.",
        familia="tendência", risco=dict(alvo=3.0, stop=2.0, tempo=90, maxdia=4, aquec=60, hini=915, hfim=1630),
        inputs="  p_Entrada(20);\n  p_Saida(10);\n",
        vars="  v_Max, v_Min, v_MaxS, v_MinS : Float;\n",
        sinal="""  v_Max := Highest(High, p_Entrada);
  v_Min := Lowest(Low, p_Entrada);
  v_MaxS := Highest(High, p_Saida);
  v_MinS := Lowest(Low, p_Saida);
  v_SinalCompra := Close > v_Max[1];
  v_SinalVenda := Close < v_Min[1];
  v_SaiCompra := Close < v_MinS[1];
  v_SaiVenda := Close > v_MaxS[1];
""",
        grade={"p_Entrada": [20, 55, 120], "p_Saida": [10, 20]}),
    "lit08_keltner": dict(
        titulo="Canal de Keltner",
        referencia="Keltner, C. (1960). How to Make Money in Commodities. "
                   "Raschke, L. & Connors, L. (1995). Street Smarts (versão com ATR).",
        ideia="Fechamento fora do canal de média exponencial ± ATR indica impulso direcional.",
        familia="tendência", risco=dict(alvo=2.0, stop=1.5, tempo=60, maxdia=5, aquec=40, hini=915, hfim=1645),
        inputs="  p_Periodo(20);\n  p_Mult(2.0);\n",
        vars="  v_Centro, v_ATRK, v_Sup, v_Inf : Float;\n",
        sinal="""  v_Centro := MediaExp(p_Periodo, Close);
  v_ATRK := AvgTrueRange(p_Periodo, 0);
  v_Sup := v_Centro + p_Mult * v_ATRK;
  v_Inf := v_Centro - p_Mult * v_ATRK;
  v_SinalCompra := (Close > v_Sup) and (Close[1] <= v_Sup[1]);
  v_SinalVenda := (Close < v_Inf) and (Close[1] >= v_Inf[1]);
  v_SaiCompra := Close < v_Centro;
  v_SaiVenda := Close > v_Centro;
""",
        grade={"p_Periodo": [20, 40], "p_Mult": [1.5, 2.0, 2.5]}),
    "lit09_vwap_reversao": dict(
        titulo="Reversão à VWAP",
        referencia="Berkowitz, S., Logue, D. & Noser, E. (1988). The Total Cost of Transactions on the NYSE. "
                   "Journal of Finance 43(1) (VWAP como preço justo do dia).",
        ideia="Afastamento extremo da VWAP, medido em desvios, tende a voltar ao preço médio do dia.",
        familia="reversão", risco=dict(alvo=2.0, stop=1.5, tempo=45, maxdia=6, aquec=70, hini=930, hfim=1645),
        inputs="  p_Janela(60);\n  p_Z(2.0);\n",
        vars="  v_VWAP, v_Dist, v_DesvDist, v_Z : Float;\n",
        sinal="""  v_VWAP := VWAP(1);
  v_Dist := Close - v_VWAP;
  v_DesvDist := StdDevs(v_Dist, p_Janela);
  if v_DesvDist > 0 then v_Z := v_Dist / v_DesvDist else v_Z := 0;
  v_SinalCompra := (v_Z < -p_Z) and (Close > Close[1]);
  v_SinalVenda := (v_Z > p_Z) and (Close < Close[1]);
  v_SaiCompra := Close >= v_VWAP;
  v_SaiVenda := Close <= v_VWAP;
""",
        grade={"p_Janela": [30, 60, 120], "p_Z": [1.5, 2.0, 2.5]}),
    "lit10_vwap_tendencia": dict(
        titulo="Tendência pela VWAP",
        referencia="Zarattini, C. & Aziz, A. (2023). Volume Weighted Average Price (VWAP): The Holy Grail for Day "
                   "Trading Systems. SSRN 4631351.",
        ideia="Estar comprado acima da VWAP e vendido abaixo dela captura a tendência do dia.",
        familia="tendência", risco=dict(alvo=3.0, stop=1.5, tempo=120, maxdia=4, aquec=10, hini=930, hfim=1630),
        inputs="  p_Confirmacao(3);\n",
        vars="  v_VWAP : Float;\n  v_Acima, v_Abaixo : Integer;\n",
        sinal="""  v_VWAP := VWAP(1);
  if Close > v_VWAP then v_Acima := v_Acima + 1 else v_Acima := 0;
  if Close < v_VWAP then v_Abaixo := v_Abaixo + 1 else v_Abaixo := 0;
  v_SinalCompra := v_Acima = p_Confirmacao;
  v_SinalVenda := v_Abaixo = p_Confirmacao;
  v_SaiCompra := Close < v_VWAP;
  v_SaiVenda := Close > v_VWAP;
""",
        grade={"p_Confirmacao": [1, 3, 5, 10]}),
    "lit11_momento_intradiario": dict(
        titulo="Momento intradiário (primeira meia hora prevê a última)",
        referencia="Gao, L., Han, Y., Li, S. Z. & Zhou, G. (2018). Market Intraday Momentum. "
                   "Journal of Financial Economics 129(2).",
        ideia="O retorno da primeira meia hora (incluindo a noite) prevê o retorno da última meia hora do pregão.",
        familia="momento", risco=dict(alvo=3.0, stop=2.0, tempo=60, maxdia=1, aquec=10, hini=1615, hfim=1630),
        inputs="  p_HoraMedida(930);\n  p_RetMin(0.0005);\n",
        vars="  v_Ret, v_PrecoMedida : Float;\n  v_Medido : Boolean;\n",
        sinal="""  if v_BarrasDia = 1 then
  begin
    v_Medido := False;
    v_Ret := 0;
  end;
  if (not v_Medido) and (Time >= p_HoraMedida) and (v_FechAnterior > 0) then
  begin
    v_PrecoMedida := Close;
    v_Ret := (v_PrecoMedida - v_FechAnterior) / v_FechAnterior;
    v_Medido := True;
  end;
  v_SinalCompra := v_Medido and (v_Ret > p_RetMin);
  v_SinalVenda := v_Medido and (v_Ret < -p_RetMin);
""",
        grade={"p_HoraMedida": [930, 1000, 1030], "p_RetMin": [0.0, 0.0005, 0.002]}),
    "lit12_gap_reversao": dict(
        titulo="Fechamento do gap de abertura",
        referencia="Lou, D., Polk, C. & Skouras, S. (2019). A Tug of War: Overnight versus Intraday Expected Returns. "
                   "Journal of Financial Economics 134(1) (reversão entre retorno noturno e intradiário).",
        ideia="Gap de abertura grande tende a ser parcialmente devolvido durante o pregão.",
        familia="reversão", risco=dict(alvo=3.0, stop=2.0, tempo=180, maxdia=1, aquec=10, hini=915, hfim=1030),
        inputs="  p_GapMin(0.002);\n",
        vars="  v_Gap : Float;\n",
        sinal="""  if (v_FechAnterior > 0) then v_Gap := (v_AberturaDia - v_FechAnterior) / v_FechAnterior else v_Gap := 0;
  v_SinalCompra := (v_Gap < -p_GapMin) and (Close < v_FechAnterior);
  v_SinalVenda := (v_Gap > p_GapMin) and (Close > v_FechAnterior);
  v_SaiCompra := Close >= v_FechAnterior;
  v_SaiVenda := Close <= v_FechAnterior;
""",
        grade={"p_GapMin": [0.001, 0.002, 0.004]}),
    "lit13_estocastico": dict(
        titulo="Oscilador estocástico",
        referencia="Lane, G. (1984). Lane's Stochastics. Technical Analysis of Stocks & Commodities 2(3).",
        ideia="Cruzamento de %K sobre %D em zona extrema indica reversão do excesso.",
        familia="reversão", risco=dict(alvo=2.0, stop=1.5, tempo=30, maxdia=6, aquec=30, hini=915, hfim=1645),
        inputs="  p_Periodo(14);\n  p_Suave(3);\n  p_Zona(20);\n",
        vars="  v_Max, v_Min, v_K, v_D : Float;\n",
        sinal="""  v_Max := Highest(High, p_Periodo);
  v_Min := Lowest(Low, p_Periodo);
  if v_Max > v_Min then v_K := 100 * (Close - v_Min) / (v_Max - v_Min) else v_K := 50;
  v_D := Media(p_Suave, v_K);
  v_SinalCompra := (v_K > v_D) and (v_K[1] <= v_D[1]) and (v_D < p_Zona);
  v_SinalVenda := (v_K < v_D) and (v_K[1] >= v_D[1]) and (v_D > 100 - p_Zona);
  v_SaiCompra := v_K > 100 - p_Zona;
  v_SaiVenda := v_K < p_Zona;
""",
        grade={"p_Periodo": [14, 28], "p_Zona": [10, 20, 30]}),
    "lit14_williams_r": dict(
        titulo="Williams %R",
        referencia="Williams, L. (1973). How I Made One Million Dollars Last Year Trading Commodities.",
        ideia="Saída da zona de sobrevenda ou sobrecompra do %R marca o fim do excesso.",
        familia="reversão", risco=dict(alvo=2.0, stop=1.5, tempo=30, maxdia=6, aquec=30, hini=915, hfim=1645),
        inputs="  p_Periodo(14);\n  p_Extremo(90);\n  p_Gatilho(80);\n",
        vars="  v_Max, v_Min, v_R : Float;\n",
        sinal="""  v_Max := Highest(High, p_Periodo);
  v_Min := Lowest(Low, p_Periodo);
  if v_Max > v_Min then v_R := -100 * (v_Max - Close) / (v_Max - v_Min) else v_R := -50;
  v_SinalCompra := (Lowest(v_R, 5) < -p_Extremo) and (v_R > -p_Gatilho) and (v_R[1] <= -p_Gatilho);
  v_SinalVenda := (Highest(v_R, 5) > -(100 - p_Extremo)) and (v_R < -(100 - p_Gatilho)) and (v_R[1] >= -(100 - p_Gatilho));
  v_SaiCompra := v_R > -50;
  v_SaiVenda := v_R < -50;
""",
        grade={"p_Periodo": [14, 28], "p_Extremo": [90, 95], "p_Gatilho": [70, 80]}),
    "lit15_cci": dict(
        titulo="Commodity Channel Index (CCI)",
        referencia="Lambert, D. (1980). Commodity Channel Index: Tools for Trading Cyclical Trends. Commodities Magazine.",
        ideia="CCI acima de +100 indica início de tendência; o desvio médio é aproximado pelo desvio-padrão.",
        familia="tendência", risco=dict(alvo=2.0, stop=1.5, tempo=60, maxdia=5, aquec=30, hini=915, hfim=1645),
        inputs="  p_Periodo(20);\n  p_Nivel(100);\n",
        vars="  v_TP, v_MediaTP, v_DesvTP, v_CCI : Float;\n",
        sinal="""  v_TP := (High + Low + Close) / 3;
  v_MediaTP := Media(p_Periodo, v_TP);
  v_DesvTP := StdDevs(v_TP, p_Periodo);
  if v_DesvTP > 0 then v_CCI := (v_TP - v_MediaTP) / (0.015 * v_DesvTP) else v_CCI := 0;
  v_SinalCompra := (v_CCI > p_Nivel) and (v_CCI[1] <= p_Nivel);
  v_SinalVenda := (v_CCI < -p_Nivel) and (v_CCI[1] >= -p_Nivel);
  v_SaiCompra := v_CCI < 0;
  v_SaiVenda := v_CCI > 0;
""",
        grade={"p_Periodo": [20, 40], "p_Nivel": [100, 150, 200]}),
    "lit16_adx_dmi": dict(
        titulo="ADX e DMI de Wilder",
        referencia="Wilder, J. W. (1978). New Concepts in Technical Trading Systems. Trend Research.",
        ideia="DI+ acima de DI− com ADX forte e subindo identifica tendência; a suavização de Wilder usa MediaExp(2n−1).",
        familia="tendência", risco=dict(alvo=3.0, stop=1.5, tempo=60, maxdia=5, aquec=60, hini=915, hfim=1630),
        inputs="  p_Periodo(14);\n  p_ADXMin(25);\n",
        vars="  v_SobeDM, v_DesceDM, v_DMMais, v_DMMenos, v_TR, v_DIMais, v_DIMenos, v_DX, v_ADX : Float;\n",
        sinal="""  v_SobeDM := High - High[1];
  v_DesceDM := Low[1] - Low;
  if (v_SobeDM > v_DesceDM) and (v_SobeDM > 0) then v_DMMais := v_SobeDM else v_DMMais := 0;
  if (v_DesceDM > v_SobeDM) and (v_DesceDM > 0) then v_DMMenos := v_DesceDM else v_DMMenos := 0;
  v_TR := MediaExp(2 * p_Periodo - 1, TrueRange);
  if v_TR > 0 then
  begin
    v_DIMais := 100 * MediaExp(2 * p_Periodo - 1, v_DMMais) / v_TR;
    v_DIMenos := 100 * MediaExp(2 * p_Periodo - 1, v_DMMenos) / v_TR;
  end;
  if v_DIMais + v_DIMenos > 0 then v_DX := 100 * Abs(v_DIMais - v_DIMenos) / (v_DIMais + v_DIMenos) else v_DX := 0;
  v_ADX := MediaExp(2 * p_Periodo - 1, v_DX);
  v_SinalCompra := (v_DIMais > v_DIMenos) and (v_DIMais[1] <= v_DIMenos[1]) and (v_ADX > p_ADXMin);
  v_SinalVenda := (v_DIMenos > v_DIMais) and (v_DIMenos[1] <= v_DIMais[1]) and (v_ADX > p_ADXMin);
  v_SaiCompra := v_DIMenos > v_DIMais;
  v_SaiVenda := v_DIMais > v_DIMenos;
""",
        grade={"p_Periodo": [14, 28], "p_ADXMin": [20, 25, 30]}),
    "lit17_fluxo_agressao": dict(
        titulo="Desequilíbrio do fluxo de agressão (OFI)",
        referencia="Cont, R., Kukanov, A. & Stoikov, S. (2014). The Price Impact of Order Book Events. Journal of "
                   "Financial Econometrics 12(1). Chordia, T. & Subrahmanyam, A. (2004). Order Imbalance and Individual "
                   "Stock Returns. Journal of Financial Economics 72(3).",
        ideia="Desequilíbrio persistente entre agressão compradora e vendedora antecipa o movimento de curto prazo.",
        familia="microestrutura", risco=dict(alvo=2.0, stop=1.5, tempo=20, maxdia=6, aquec=70, hini=915, hfim=1645),
        inputs="  p_Janela(5);\n  p_Normal(60);\n  p_Z(2.0);\n",
        vars="  v_Saldo, v_Fluxo, v_Soma, v_DesvFluxo, v_Z : Float;\n",
        sinal="""  v_Saldo := AgressionVolBalance;
  if v_BarrasDia = 1 then v_Fluxo := v_Saldo else v_Fluxo := v_Saldo - v_Saldo[1];
  v_Soma := Summation(v_Fluxo, p_Janela);
  v_DesvFluxo := StdDevs(v_Fluxo, p_Normal);
  if v_DesvFluxo > 0 then v_Z := v_Soma / (v_DesvFluxo * Sqrt(p_Janela)) else v_Z := 0;
  v_SinalCompra := v_Z > p_Z;
  v_SinalVenda := v_Z < -p_Z;
  v_SaiCompra := v_Z < 0;
  v_SaiVenda := v_Z > 0;
""",
        grade={"p_Janela": [3, 5, 10], "p_Z": [1.5, 2.0, 3.0]}),
    "lit18_volume_reversao": dict(
        titulo="Reversão de movimento com volume anormal",
        referencia="Campbell, J., Grossman, S. & Wang, J. (1993). Trading Volume and Serial Correlation in Stock "
                   "Returns. Quarterly Journal of Economics 108(4).",
        ideia="Movimentos grandes acompanhados de volume alto refletem demanda por liquidez e tendem a reverter.",
        familia="reversão", risco=dict(alvo=1.5, stop=1.5, tempo=20, maxdia=6, aquec=70, hini=915, hfim=1645),
        inputs="  p_Janela(60);\n  p_ZRet(2.0);\n  p_MultVol(2.0);\n",
        vars="  v_Ret, v_DesvRet, v_MediaVol : Float;\n",
        sinal="""  v_Ret := Close - Close[1];
  v_DesvRet := StdDevs(v_Ret, p_Janela);
  v_MediaVol := Media(p_Janela, Quantity);
  v_SinalCompra := (v_Ret < -p_ZRet * v_DesvRet) and (Quantity > p_MultVol * v_MediaVol);
  v_SinalVenda := (v_Ret > p_ZRet * v_DesvRet) and (Quantity > p_MultVol * v_MediaVol);
""",
        grade={"p_ZRet": [2.0, 2.5, 3.0], "p_MultVol": [1.5, 2.0, 3.0]}),
    "lit19_reversao_curto_prazo": dict(
        titulo="Reversão de curto prazo",
        referencia="Jegadeesh, N. (1990). Evidence of Predictable Behavior of Security Returns. Journal of Finance "
                   "45(3). Lehmann, B. (1990). Fads, Martingales, and Market Efficiency. QJE 105(1).",
        ideia="Retorno extremo numa janela curta, medido em desvios, tende a ser parcialmente devolvido.",
        familia="reversão", risco=dict(alvo=2.0, stop=1.5, tempo=30, maxdia=6, aquec=130, hini=915, hfim=1645),
        inputs="  p_Janela(15);\n  p_Normal(120);\n  p_Z(2.5);\n",
        vars="  v_Ret, v_DesvR1, v_Z : Float;\n",
        sinal="""  v_Ret := Close - Close[p_Janela];
  v_DesvR1 := StdDevs(Close - Close[1], p_Normal);
  if v_DesvR1 > 0 then v_Z := v_Ret / (v_DesvR1 * Sqrt(p_Janela)) else v_Z := 0;
  v_SinalCompra := v_Z < -p_Z;
  v_SinalVenda := v_Z > p_Z;
  v_SaiCompra := v_Z > 0;
  v_SaiVenda := v_Z < 0;
""",
        grade={"p_Janela": [5, 15, 30], "p_Z": [2.0, 2.5, 3.0]}),
    "lit20_momento_serie_temporal": dict(
        titulo="Momento de série temporal",
        referencia="Moskowitz, T., Ooi, Y. H. & Pedersen, L. H. (2012). Time Series Momentum. "
                   "Journal of Financial Economics 104(2).",
        ideia="O sinal do retorno passado, quando significativo frente à volatilidade, prevê o retorno seguinte.",
        familia="momento", risco=dict(alvo=3.0, stop=1.5, tempo=60, maxdia=4, aquec=130, hini=915, hfim=1630),
        inputs="  p_Janela(60);\n  p_Z(1.0);\n",
        vars="  v_Ret, v_DesvR1, v_Z : Float;\n",
        sinal="""  v_Ret := Close - Close[p_Janela];
  v_DesvR1 := StdDevs(Close - Close[1], 2 * p_Janela);
  if v_DesvR1 > 0 then v_Z := v_Ret / (v_DesvR1 * Sqrt(p_Janela)) else v_Z := 0;
  v_SinalCompra := (v_Z > p_Z) and (v_Z[1] <= p_Z);
  v_SinalVenda := (v_Z < -p_Z) and (v_Z[1] >= -p_Z);
  v_SaiCompra := v_Z < 0;
  v_SaiVenda := v_Z > 0;
""",
        grade={"p_Janela": [30, 60, 120], "p_Z": [0.5, 1.0, 1.5]}),
}


def fonte(nome, e):
    r = e["risco"]
    return (
        f"{{ {e['titulo']} ({nome}) - WIN 1 min, 1 contrato.\n"
        f"  Referência: {e['referencia']}\n"
        f"  Ideia: {e['ideia']}\n"
        f"  Família: {e['familia']}. Gerado por tools/gerar_estrategias_literatura.py; bloco de risco comum.\n"
        f"  Validação: docs/colaboracao/evidencias/estrategias_literatura_v1/. }}\n\n"
        "input\n" + e["inputs"] + COMUM_INPUTS.format(**r) +
        "\nvar\n" + e["vars"] + COMUM_VARS +
        "\nbegin\n" + COMUM_PRE + "\n  { ---------------- sinal ---------------- }\n" + e["sinal"] + COMUM_POS + "end;\n"
    )


def catalogo():
    return {n: dict(titulo=e["titulo"], referencia=e["referencia"], ideia=e["ideia"], familia=e["familia"],
                    arquivo=f"estrategias/literatura/{n}.ntsl", grade={**e["grade"], **GRADE_RISCO})
            for n, e in ESTRATEGIAS.items()}


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nome, e in ESTRATEGIAS.items():
        (DESTINO / f"{nome}.ntsl").write_text(fonte(nome, e), encoding="utf-8")
    (DESTINO / "catalogo_literatura.json").write_text(json.dumps(catalogo(), indent=2, ensure_ascii=False) + "\n",
                                                      encoding="utf-8")
    print(f"{len(ESTRATEGIAS)} estratégias em {DESTINO}")


if __name__ == "__main__":
    main()
