import pandas as pd
import pytest

from estrategia import Engine, ExecutionRules
from ntsl import compile_ntsl
from test_replay import run, run_ohlc


ADJUST = {"ajuste_tick_saidas_venda": True, "rastrear_ordens": True}


@pytest.mark.parametrize("order,requested,effective,raw_fill,limit", [
    ("SellToCoverLimit(BuyPrice+428, 1)", 2428, 2430, 2428, ""),
    ("SellToCoverLimit(BuyPrice+447, 1)", 2447, 2445, None, ""),
    ("SellToCoverStop(BuyPrice-793, BuyPrice-894, 1)", 1207, 1205, 1207, 1106),
    ("SellToCoverStop(BuyPrice-877, BuyPrice-1000, 1)", 1123, 1125, None, 1000),
])
@pytest.mark.parametrize("active", [False, True])
def test_ajuste_reproduz_g1_g2_e_controles(order, requested, effective, raw_fill, limit, active):
    source = f"""begin
        if CurrentBar=1 then BuyAtMarket(1);
        if CurrentBar=2 then {order};
        if HasPendingOrders then Plot(1) else Plot(0);
        if (CurrentBar=6) and HasPosition then ClosePosition;
    end;"""
    engine = run_ohlc(source, [2110, 2000, 1715, 2035, 2220, 1740, 1625],
                      [2375, 2175, 2225, 2405, 2445, 1930, 1765],
                      [1800, 1575, 1645, 1915, 1125, 1295, 1385],
                      [1995, 1710, 2035, 2220, 1740, 1910, 1460],
                      ADJUST | {"ajuste_tick_saidas_venda": active, "protecoes_ate_cancelar": True})
    assert [row["plot"] for row in engine.trace[2:4]] == [1, 1]
    fill = engine.fills[1]
    price = effective if active else raw_fill
    assert (fill["barra"], fill["preco"]) == ((5, price) if price is not None else (7, 1625))
    if active:
        submit, = [row for row in engine.order_events
                   if row["evento"] == "solicitacao" and row["acao"] == "exit_long"]
        execution, = [row for row in engine.order_events
                      if row["evento"] == "preenchimento" and row["acao"] == "exit_long"]
        for row in (submit, execution):
            assert (row["nivel_solicitado"], row["nivel_efetivo"], row["ajuste_tick"]) == (
                requested, effective, "ajustado")
            assert row["limite_solicitado"] == row["limite_efetivo"] == limit
    else:
        assert all("nivel_solicitado" not in row for row in engine.order_events)


def engine_for_orders(tick, position=1):
    frame = pd.DataFrame(dict(pregao=["2026-10-02"] * 6, abertura=[100] * 6,
                              maxima=[100] * 6, minima=[100] * 6,
                              fechamento=[100] * 6, barra_ntsl=range(1, 7)))
    engine = Engine(compile_ntsl("begin end;"), frame, tick, {}, 60, 1, regras=ADJUST)
    engine.position = position
    return engine


@pytest.mark.parametrize("tick,requested,status,effective", [
    (5, 105, "na_grade", 105),
    (5, 102.5, "empate_meio_tick", 102.5),
    (0.1, 104.15, "empate_meio_tick", 104.15),
    (0.1, 104.16, "ajustado", 104.2),
])
def test_grade_e_meio_tick_exato(tick, requested, status, effective):
    engine = engine_for_orders(tick)
    engine.queue("selltocoverlimit", (requested,))
    assert engine.orders["selltocoverlimit"].price == effective
    event = engine.order_events[0]
    assert (event["nivel_solicitado"], event["nivel_efetivo"], event["ajuste_tick"]) == (
        requested, effective, status)
    is_tie = status == "empate_meio_tick"
    assert ("empate_meio_tick" in [e["evento"] for e in engine.order_events]) == is_tie
    assert engine.tick_adjustments["empate_meio_tick"] == int(is_tie)
    assert engine.tick_adjustments["ajustado"] == int(status == "ajustado")


def test_renovacao_compara_gatilho_efetivo_e_limite_bruto():
    engine = engine_for_orders(5)
    name = "selltocoverstop"
    engine.queue(name, (97, 93))
    first = engine.orders[name]
    assert engine.match(first, 90, 92, 88) is None
    assert first.triggered and (first.price, first.limit, first.eligible_at) == (95, 93, 1)

    engine.row = 2
    engine.queue(name, (96, 93))
    renewed = engine.orders[name]
    assert renewed.triggered and (renewed.price, renewed.limit, renewed.eligible_at) == (95, 93, 1)
    assert len(engine.orders) == 1
    assert engine.order_events[-1]["evento"] == "solicitacao_renovada"
    assert engine.order_events[-1]["nivel_solicitado"] == 96

    engine.row = 3
    engine.queue(name, (102, 93))
    replacement = engine.orders[name]
    assert not replacement.triggered and (replacement.price, replacement.limit, replacement.eligible_at) == (100, 93, 4)
    assert engine.order_events[-1]["evento"] == "solicitacao"


def test_gatilho_ajustado_ainda_respeita_limite_stop_bruto():
    engine = engine_for_orders(5)
    engine.queue("selltocoverstop", (97, 96))
    order = engine.orders["selltocoverstop"]
    assert (order.price, order.limit) == (95, 96)
    assert engine.match(order, 95, 95, 94) is None
    assert order.triggered
    assert engine.match(order, 95, 96, 94) == 96


@pytest.mark.parametrize("opening,order,price,limit", [
    ("", "BuyAtLimit(98)", 98, ""),
    ("", "SellShortAtStop(97, 92)", 97, 92),
    ("SellShortAtMarket(1)", "BuyToCoverLimit(97)", 97, ""),
    ("SellShortAtMarket(1)", "BuyToCoverStop(103, 107)", 103, 107),
    ("BuyAtMarket(1)", "SendOrder(osSell, otLimit, 1, 103, 0)", 103, ""),
    ("BuyAtMarket(1)", "SendOrder(osSell, otStopLimit, 1, 94, 97)", 97, 94),
])
def test_ordens_fora_do_escopo_preservam_precos(opening, order, price, limit):
    entry = f"if CurrentBar=1 then {opening};" if opening else ""
    source = f"begin {entry} if CurrentBar=2 then {order}; end;"
    engine = run(source, [100] * 4, rules=ADJUST)
    event, = [row for row in engine.order_events
              if row["evento"] == "solicitacao" and row["tipo"] in {"limit", "stop"}]
    assert (event["nivel_solicitado"], event["nivel_efetivo"], event["ajuste_tick"]) == (price, price, "")
    assert event["limite_solicitado"] == event["limite_efetivo"] == limit
    assert engine.tick_adjustments == {"ajustado": 0, "empate_meio_tick": 0}


def test_protecao_pos_preenchimento_e_zeragem_a_mercado():
    source = """begin
        if CurrentBar=1 then BuyAtMarket(1);
        if IsBought and (CurrentBar=1) then SellToCoverStop(BuyPrice-3, BuyPrice-12, 1);
        if IsBought and (CurrentBar=2) then SellToCoverAtMarket(1);
    end;"""
    engine = run_ohlc(source, [100, 100, 101, 100], [105, 106, 110, 110],
                      [98, 98, 92, 95], [100, 101, 100, 100],
                      ADJUST | {"protecoes_ate_cancelar": True, "avaliacao_pos_preenchimento": True})
    stop, = [row for row in engine.order_events if row["ordem"] == "selltocoverstop"]
    assert (stop["barra"], stop["barra_contexto_ntsl"], stop["primeira_barra_elegivel"]) == (2, 1, 2)
    assert (stop["nivel_solicitado"], stop["nivel_efetivo"], stop["limite_efetivo"]) == (97, 95, 88)
    assert [(f["barra"], f["ordem"], f["preco"]) for f in engine.fills] == [
        (2, "buyatmarket", 100), (3, "selltocoveratmarket", 101),
    ]
    assert engine.ambiguities == 0 and engine.trace[2]["posicao"] == 0


def test_ajuste_de_saidas_de_venda_rejeita_tick_a_tick():
    with pytest.raises(ValueError, match="só se aplica ao motor OHLC"):
        ExecutionRules(ajuste_tick_saidas_venda=True, motor_ticks=True)
