import pytest

from estrategia import ExecutionRules
from test_replay import run, run_ohlc


PERSISTENT = {"protecoes_ate_cancelar": True, "rastrear_ordens": True}


@pytest.mark.parametrize("protection,pnl,price", [
    ("SellToCoverLimit(BuyPrice + 430, 1)", 430, 1430),
    ("SellToCoverStop(BuyPrice - 795, BuyPrice - 895, 1)", -795, 205),
])
@pytest.mark.parametrize("keep", [False, True])
def test_protecao_isolada_toca_tres_barras_depois(protection, pnl, price, keep):
    source = f"""begin
        if CurrentBar = 1 then BuyAtMarket(1);
        if (CurrentBar = 2) and IsBought then {protection};
        if HasPendingOrders then Plot(1) else Plot(0);
    end;"""
    engine = run_ohlc(source, [1110, 1000, 715, 1035, 1220, 740],
                      [1375, 1175, 1225, 1405, 1445, 930],
                      [800, 575, 645, 915, 125, 295],
                      [995, 710, 1035, 1220, 740, 910],
                      {"protecoes_ate_cancelar": keep})
    assert [row["plot"] for row in engine.trace[2:5]] == [1, int(keep), 0]
    assert engine.trace[4]["posicao"] == (0 if keep else 1)
    assert [(f["barra"], f["preco"], f["pontos_contrato"]) for f in engine.fills] == [
        (2, 1000, 0), (5, price, pnl) if keep else (6, 910, -90),
    ]


@pytest.mark.parametrize("order", ["BuyAtLimit(85)", "SellShortAtStop(85, 80)",
                                   "SendOrder(osSell, otLimit, 1, 110, 0)"])
def test_protecao_preserva_validade_das_entradas(order):
    source = f"begin if CurrentBar=1 then {order}; end;"
    prices = [100, 100, 100, 85 if "SendOrder" not in order else 110, 100]
    assert not run(source, prices, rules=PERSISTENT).fills
    diagnostic = {"ordem_so_proxima_barra": False}
    old = run(source, prices, rules=diagnostic)
    combined = run(source, prices, rules=diagnostic | PERSISTENT)
    assert combined.fills == old.fills and old.fills[0]["barra"] == 4


def test_stop_sem_limite_preserva_validade():
    engine = run("""begin
        if CurrentBar=1 then BuyAtMarket(1);
        if CurrentBar=2 then SellToCoverStop(95);
    end;""", [100, 100, 100, 94, 100], rules=PERSISTENT)
    assert [fill["ordem"] for fill in engine.fills] == ["buyatmarket", "fim_pregao"]


def test_protecoes_ate_cancelar_rejeita_motor_tick():
    with pytest.raises(ValueError, match="--protecoes-ate-cancelar só se aplica ao motor OHLC"):
        ExecutionRules(protecoes_ate_cancelar=True, motor_ticks=True)


@pytest.mark.parametrize("cleanup,last_fill", [
    ("CancelPendingOrders", "fim_pregao"), ("ClosePosition", "closeposition"),
])
def test_protecao_persistente_cancelamento_e_zeragem(cleanup, last_fill):
    engine = run(f"""begin
        if CurrentBar=1 then BuyAtMarket(1);
        if CurrentBar=2 then SellToCoverLimit(110);
        if HasPendingOrders then Plot(1) else Plot(0);
        if CurrentBar=4 then {cleanup};
    end;""", [100, 100, 100, 100, 115, 120], rules=PERSISTENT)
    assert [row["plot"] for row in engine.trace[2:5]] == [1, 1, 0]
    assert [f["ordem"] for f in engine.fills] == ["buyatmarket", last_fill]
    assert not engine.orders


def test_protecao_persistente_nao_atravessa_pregao():
    engine = run("""begin
        if CurrentBar = 1 then BuyAtMarket(1);
        if CurrentBar = 2 then SellToCoverLimit(110);
        if HasPendingOrders then Plot(1) else Plot(0);
    end;""".replace("CurrentBar", "CurrentBar"), [100, 100, 100, 100, 115, 120],
        days=["2026-10-02"] * 4 + ["2026-10-05"] * 2, rules=PERSISTENT)
    assert [row["plot"] for row in engine.trace[2:5]] == [1, 1, 0]
    assert [(f["barra"], f["ordem"]) for f in engine.fills] == [(2, "buyatmarket"), (4, "fim_pregao")]


@pytest.mark.parametrize("exit_order,entry,protection,opening,high,low", [
    ("SellToCoverAtMarket(1)", "BuyAtMarket(1)", "SellToCoverStop(95, 90, 1)", 100, 105, 90),
    ("SendOrder(osSell, otMarket, 1, 0, 0)", "BuyAtMarket(1)", "SellToCoverStop(95, 90, 1)", 100, 105, 90),
    ("BuyToCoverAtMarket(1)", "SellShortAtMarket(1)", "BuyToCoverStop(105, 110, 1)", 100, 110, 95),
    ("SellToCoverAtMarket(1)", "BuyAtMarket(1)", "SellToCoverLimit(110, 1)", 100, 115, 95),
])
def test_zeragem_a_mercado_na_abertura_antecede_toque_da_protecao(
    exit_order, entry, protection, opening, high, low,
):
    source = f"""begin
        if CurrentBar=1 then {entry};
        if CurrentBar=2 then {protection};
        if CurrentBar=4 then {exit_order};
        if HasPendingOrders then Plot(1) else Plot(0);
    end;"""
    args = (source, [100] * 4 + [opening, opening], [100] * 4 + [high, high],
            [100] * 4 + [low, low], [100] * 6)
    engine = run_ohlc(*args, PERSISTENT)
    assert [(f["barra"], f["tipo"], f["preco"], f["posicao"]) for f in engine.fills] == [
        (2, "market", 100, -1 if "SellShort" in entry else 1), (5, "market", opening, 0),
    ]
    assert engine.ambiguities == 0
    assert [row["plot"] for row in engine.trace[2:6]] == [1, 1, 0, 0]
    assert all(event["evento"] != "gatilho_stop" for event in engine.order_events)

    if "SendOrder" not in exit_order:
        legacy = run_ohlc(*args, {"ordem_so_proxima_barra": False} | PERSISTENT)
        assert legacy.ambiguities == 1
        assert legacy.fills == run_ohlc(*args, {"ordem_so_proxima_barra": False}).fills


def test_protecao_persistente_com_entrada_e_avaliacao_extra_apos_lacuna():
    source = """var enviado: Boolean;
    begin
      if CurrentBar=1 then BuyAtMarket(1);
      if IsBought and (CurrentBar <= 3) then begin
        SellToCoverLimit(BuyPrice + 30);
        if not enviado then ConsoleLog("contexto=" + (Close));
        enviado := True;
      end;
      if HasPendingOrders then Plot(1) else Plot(0);
    end;"""
    engine = run(source, [100, 110, 115, 125, 130, 145],
                 rules=PERSISTENT | {"historico_continuo_lacunas": True,
                                     "entrada_mercado_atraves_lacuna": True,
                                     "avaliacao_pos_preenchimento": True},
                 lacuna_intradiaria=[False, True, False, False, False, False])
    assert engine.orders_cancelled_at_gaps == engine.gaps_with_exposure == 0
    assert engine.logs[-1] == (1, "contexto=100.0")
    assert [row["plot"] for row in engine.trace[2:5]] == [1, 1, 1]
    assert [(f["barra"], f["ordem"], f["preco"]) for f in engine.fills] == [
        (2, "buyatmarket", 110), (6, "selltocoverlimit", 145),
    ]
    submitted = [e for e in engine.order_events if e["ordem"] == "selltocoverlimit"
                 and e["evento"].startswith("solicitacao")]
    assert [e["evento"] for e in submitted] == ["solicitacao", "solicitacao_renovada", "solicitacao_renovada"]
    assert [e["primeira_barra_elegivel"] for e in submitted] == [2, 2, 2]
    assert [e["barra_contexto_ntsl"] for e in submitted] == [1, 2, 3]


def test_protecao_persistente_cancela_na_lacuna_com_posicao_aberta():
    engine = run("""begin
        if CurrentBar=1 then BuyAtMarket(1);
        if CurrentBar=2 then SellToCoverLimit(130);
        if HasPendingOrders then Plot(1) else Plot(0);
    end;""", [100, 100, 100, 100, 130, 140],
        rules=PERSISTENT | {"historico_continuo_lacunas": True, "entrada_mercado_atraves_lacuna": True,
                            "avaliacao_pos_preenchimento": True},
        lacuna_intradiaria=[False, False, False, False, True, False])
    assert engine.orders_cancelled_at_gaps == engine.gaps_with_exposure == 1
    assert [row["plot"] for row in engine.trace[2:5]] == [1, 1, 0]
    assert engine.trace[4]["posicao"] == 1
    assert [fill["ordem"] for fill in engine.fills] == ["buyatmarket", "fim_pregao"]


def test_duplo_toque_de_protecoes_persistentes_preserva_ambiguidade():
    engine = run_ohlc("""begin
        if CurrentBar=1 then BuyAtMarket(1);
        if CurrentBar=2 then begin
            SellToCoverLimit(110);
            SellToCoverStop(95, 90);
        end;
    end;""", [100] * 5, [100, 100, 100, 115, 100], [100, 100, 100, 90, 100],
        [100] * 5, PERSISTENT)
    assert engine.ambiguities == 1
    assert [(f["barra"], f["ordem"], f["preco"]) for f in engine.fills] == [
        (2, "buyatmarket", 100), (4, "selltocoverstop", 95),
    ]
