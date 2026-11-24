"""Controles sintéticos para decidir a prioridade das saídas da rodada 16."""

import pandas as pd
import pytest

from estrategia import Engine
from ntsl import compile_ntsl
from test_replay import run_ohlc


SOURCE = """
input
  p_RenovaAoSair(0);

begin
  if CurrentBar = 1 then BuyAtMarket(2);

  if IsBought then
  begin
    if (Close <= 975) and (CurrentBar >= 3) then
    begin
      Plot(1);
      SellToCoverAtMarket(2);
    end;
    if (Close > 975) or (CurrentBar < 3) or (p_RenovaAoSair = 1) then
    begin
      SellToCoverLimit(1050, 2);
      SellToCoverStop(950, 925, 2);
    end;
  end;
end;
"""
RULES = {"custo_por_contrato_lado": 0.5, "slippage_ticks": 1, "rastrear_ordens": True}


def fills(engine):
    return [(row["barra"], row["ordem"], row["preco"], row["quantidade"]) for row in engine.fills]


def market_requests(engine):
    return [row["barra"] for row in engine.order_events
            if row["evento"] == "solicitacao" and row["tipo"] == "market" and row["acao"] == "exit_long"]


@pytest.mark.parametrize("touch_stop,expected", [
    (False, [(2, "buyatmarket", 1005, 2), (4, "selltocoveratmarket", 985, 2)]),
    (True, [(2, "buyatmarket", 1005, 2), (3, "selltocoverstop", 945, 2)]),
])
def test_protecao_ja_executada_precede_decisao_do_fechamento(touch_stop, expected):
    engine = run_ohlc(SOURCE, [1000, 1000, 990, 990],
                      [1010, 1010, 1000, 1000], [995, 990, 940 if touch_stop else 960, 960],
                      [1000, 1000, 970, 990], RULES)
    assert fills(engine) == expected
    assert market_requests(engine) == ([] if touch_stop else [3])


@pytest.mark.parametrize("renew,ambiguities", [(False, 0), (True, 1)])
def test_mercado_na_abertura_e_stop_na_faixa_da_barra_seguinte(renew, ambiguities):
    source = SOURCE.replace("p_RenovaAoSair(0)", f"p_RenovaAoSair({int(renew)})")
    engine = run_ohlc(source, [1000, 1000, 990, 990],
                      [1010, 1010, 1000, 1000], [995, 990, 960, 935],
                      [1000, 1000, 970, 940], RULES)
    assert fills(engine) == [(2, "buyatmarket", 1005, 2), (4, "selltocoveratmarket", 985, 2)]
    assert market_requests(engine) == [3]
    assert engine.ambiguities == ambiguities


def test_stop_limit_com_gap_nao_assume_retorno_na_mesma_barra():
    # Em t+1, o stop dispara e o preço com slippage (905) fica abaixo do limite (925).
    # A máxima toca o limite na mesma barra. O OHLC não autoriza preencher nesse retorno.
    source = """
    begin
      if CurrentBar = 1 then BuyAtMarket(2);
      if CurrentBar = 2 then SellToCoverStop(950, 925, 2);
      if CurrentBar = 3 then SellToCoverAtMarket(2);
    end;
    """
    engine = run_ohlc(source, [1000, 1000, 910, 920],
                      [1010, 1010, 940, 940], [995, 990, 900, 910],
                      [1000, 1000, 930, 930], RULES)
    assert fills(engine) == [(2, "buyatmarket", 1005, 2), (4, "selltocoveratmarket", 915, 2)]
    assert [(event["barra"], event["gatilho"], event["limite"]) for event in engine.order_events
            if event["evento"] == "gatilho_stop"] == [(3, 950, 925)]


# Estas sondas executam as duas leituras dos pareceres, com parâmetros sintéticos.
# A estratégia v1.5 e o motor ficam fora do experimento.
DISPUTED = """
input
  p_J(1);
  p_JanelaMaxima(0);
  p_Tolerancia(0);
  p_BordaInclusiva(0);
  p_Venda(0);

var
  nivel : Float;
  entrada, k : Integer;
  falhou : Boolean;

begin
  if CurrentBar = 2 then
  begin
    if p_Venda = 1 then
    begin
      nivel := Low[1];
      SellShortAtMarket(2);
    end
    else
    begin
      nivel := High[1];
      BuyAtMarket(2);
    end;
  end;
  if HasPosition then
  begin
    if entrada = 0 then entrada := CurrentBar;
    k := CurrentBar - entrada + 1;
    if (p_JanelaMaxima = 0) or (BarrasNoSegmento > k) then
    begin
      if ((p_JanelaMaxima = 1) and (k <= p_J))
        or ((p_JanelaMaxima = 0) and (k >= p_J)) then
      begin
        if IsBought and ((Close < nivel - p_Tolerancia)
          or ((p_BordaInclusiva = 1) and (Close = nivel - p_Tolerancia))) then falhou := True;
        if IsSold and ((Close > nivel + p_Tolerancia)
          or ((p_BordaInclusiva = 1) and (Close = nivel + p_Tolerancia))) then falhou := True;
      end;
      if falhou then
      begin
        if IsBought then SellToCoverAtMarket(2)
        else BuyToCoverAtMarket(2);
        if p_JanelaMaxima = 1 then falhou := False;
      end;
    end;
  end;
  Plot(nivel);
end;
"""


def run_dispute(closes, gap=False, short=False, **overrides):
    opening = [995, 1005, 1020, 1010, 990, 990]
    close = [995, 1020, *closes, 1010]
    high = [1000, 1030, 1030, 1030, 1030, 1010]
    low = [990, 1000, 985, 985, 985, 985]
    if short:
        opening, high, low, close = ([2000 - p for p in column]
                                     for column in (opening, low, high, close))
    frame = pd.DataFrame({
        "pregao": ["2026-01-02"] * 6, "barra_ntsl": list(range(1, 7)),
        "abertura": opening, "maxima": high, "minima": low, "fechamento": close,
        "lacuna_intradiaria": [False, False, False, gap, False, False],
        "barras_no_segmento": [1, 2, 3, 1, 2, 3] if gap else list(range(1, 7)),
    })
    engine = Engine(compile_ntsl(DISPUTED), frame, 5, {"p_venda": int(short)} | overrides,
                    60, 0.2, regras=RULES)
    engine.run()
    return engine


def first_exit_request(engine):
    return next((r["barra"] for r in engine.order_events
                 if r["evento"] == "solicitacao" and r["acao"].startswith("exit")), None)


@pytest.mark.parametrize("closes,claude_bar,gemini_bar", [
    ([995, 1010, 1010], None, 3),  # K=1 com J=2
    ([1015, 1010, 995], 5, None),  # K=3 com J=2
])
def test_janela_maxima_e_primeiro_candle_elegivel_dao_saidas_distintas(closes, claude_bar, gemini_bar):
    claude = run_dispute(closes, p_j=2)
    gemini = run_dispute(closes, p_j=2, p_janelamaxima=1)
    assert first_exit_request(claude) == claude_bar
    assert first_exit_request(gemini) == gemini_bar


def test_lacuna_cancela_saida_e_trava_define_reenvio():
    claude = run_dispute([995, 1010, 1010], gap=True)
    gemini = run_dispute([995, 1010, 1010], gap=True, p_janelamaxima=1)
    assert claude.orders_cancelled_at_gaps == gemini.orders_cancelled_at_gaps == 1
    assert market_requests(claude) == [3, 4]
    assert market_requests(gemini) == [3]
    assert fills(claude)[-1] == (5, "selltocoveratmarket", 985, 2)
    assert fills(gemini)[-1][0:2] == (6, "fim_pregao")


@pytest.mark.parametrize("short", [False, True])
@pytest.mark.parametrize("close,strict_bar,inclusive_bar", [(1000, None, None), (995, None, 3), (990, 3, 3)])
def test_borda_da_tolerancia_de_um_tick_muda_o_preenchimento(short, close, strict_bar, inclusive_bar):
    overrides = {"p_janelamaxima": 1, "p_tolerancia": 5}
    strict = run_dispute([close, 1010, 1010], short=short, **overrides)
    inclusive = run_dispute([close, 1010, 1010], short=short, p_bordainclusiva=1, **overrides)
    assert first_exit_request(strict) == strict_bar
    assert first_exit_request(inclusive) == inclusive_bar


def test_nivel_e_o_da_barra_rompida_e_nao_o_da_barra_de_sinal():
    engine = run_dispute([1010, 1010, 1010], p_janelamaxima=1)
    assert engine.trace[1]["plot"] == engine.trace[2]["plot"] == 1000
    assert first_exit_request(engine) is None  # 1010 supera High[S-1]=1000 e fica abaixo de High[S]=1030.
