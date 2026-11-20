import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from estrategia import Engine, Order, run_strategy
from ntsl import compile_ntsl

ROOT = Path(__file__).resolve().parents[1]


def run(source, close, days=None, rules=None, **columns):
    frame = pd.DataFrame(dict(
        pregao=days or ["2026-10-02"] * len(close),
        abertura=close, maxima=close, minima=close, fechamento=close,
        barra_ntsl=range(1, len(close)+1), **columns,
    ))
    engine = Engine(compile_ntsl(source), frame, 5, {}, 60, 1, regras=rules)
    engine.run()
    return engine


def run_ohlc(source, opening, high, low, close, rules=None):
    frame = pd.DataFrame(dict(
        pregao=["2026-10-02"] * len(close),
        abertura=opening, maxima=high, minima=low, fechamento=close,
        barra_ntsl=range(1, len(close)+1),
    ))
    engine = Engine(compile_ntsl(source), frame, 5, {}, 60, 1, regras=rules)
    engine.run()
    return engine


def test_replay_minimo(tmp_path):
    example = ROOT / "exemplos/replay_minimo"
    expected = json.loads((example / "metricas_esperadas.json").read_text())
    actual = run_strategy(example / "candles.csv", (example / "estrategia.ntsl").read_text(),
                          tmp_path / "replay", 5, "ohlc", 5)
    assert actual["versao"] == (ROOT / "VERSION").read_text().strip()
    assert all(actual[key] == value for key, value in expected.items() if key != "versao")


@pytest.mark.parametrize("command", ["BuyAtLimit(85)", "BuyAtStop(115)", "SendOrder(osBuy, otLimit, 1, 85, 0)"])
def test_ordem_expira_ou_e_renovada(command):
    target = 115 if "Stop" in command else 85
    close = [100, 100, 100, target, target]
    single = f"begin if CurrentBar = 1 then {command}; end;"
    repeated = f"begin if CurrentBar <= 3 then {command}; end;"
    assert not run(single, close).fills
    assert run(repeated, close).fills[0]["barra"] == 4
    assert run(single, close, rules={"ordem_so_proxima_barra": False}).fills[0]["barra"] == 4


def test_mod_igual_para_operador_e_funcao():
    result = run("begin Plot(-7 mod 3); Plot2(Mod(-7,3)); Plot3(7 mod -3); end;", [100])
    assert [result.trace[0][key] for key in ("plot", "plot2", "plot3")] == [-1, -1, 1]


def test_historico_e_media_entre_pregoes():
    source = "begin Plot(Close[1]); Plot2(Media(2, Close)); end;"
    days = ["2026-10-02", "2026-10-05"]
    assert (run(source, [100, 120], days).trace[1]["plot"],
            run(source, [100, 120], days).trace[1]["plot2"]) == (100, 110)
    legacy = run(source, [100, 120], days, {"historico_continuo": False})
    assert (legacy.trace[1]["plot"], legacy.trace[1]["plot2"]) == (0, 120)


def test_indicadores_novos():
    source = "begin Plot(VWAP(1)); Plot2(StdDevs(Close, 2)); Plot3(AgressionVolBalance); end;"
    result = run(source, [100, 120, 200], ["2026-10-02", "2026-10-02", "2026-10-05"],
                 volume_contratos=[1, 3, 4], v_agressao_compra=[3, 2, 1], v_agressao_venda=[1, 5, 2])
    assert [(x["plot"], x["plot2"], x["plot3"]) for x in result.trace] == [
        (100, 0, 2), (115, 10, -1), (200, 40, -1)]


def test_input_tick_a_tick_diagnostico():
    with pytest.raises(ValueError, match="p_Exec_Tick para 0"):
        run("input p_Exec_Tick(1); begin end;", [100])


def test_vwap_de_negocios_pondera_cada_preco(tmp_path):
    csv = tmp_path / "negocios.csv"
    csv.write_text(
        "timestamp;preco;quantidade\n2026-10-02T09:00:01;100;1\n"
        "2026-10-02T09:00:02;120;3\n2026-10-02T09:01:02;150;1\n"
    )
    run_strategy(csv, "begin Plot(VWAP(0)); Plot2(VWAP(1)); end;",
                 tmp_path / "replay", 60, "negocios", 5)
    result = pd.read_csv(tmp_path / "replay/candles.csv")
    assert result["plot"].tolist() == [115, 150]
    assert result["plot2"].tolist() == [115, 122]


def test_agressao_sem_dados_tem_diagnostico():
    with pytest.raises(ValueError, match="duas colunas de agressão"):
        run("begin Plot(AgressionVolBalance()); end;", [100])


def test_modo_paridade_volume_financeiro_agressao_e_vwap_sem_reset():
    source = ("begin Plot(Volume); Plot2(AgressionVolBalance); "
              "Plot3(VWAP(1)); Plot5(Close); Plot8(1); end;")
    columns = dict(
        volume=[2, 3, 4], volume_financeiro=[2000, 3600, 8000],
        volume_contratos=[1, 3, 4], v_vwap_barra=[100, 120, 200],
        v_agressao_compra=[3, 2, 1], v_agressao_venda=[1, 5, 2],
        v_agressao_saldo_referencia=[9, -7, 4],
        lacuna_intradiaria=[False, True, False],
    )
    result = run(source, [100, 120, 200], rules={
        "volume_financeiro_ntsl": True,
        "agressao_referencia_injetada": True,
        "vwap_continuo_lacunas": True,
    }, **columns)
    assert [(row["plot"], row["plot2"], row["plot3"], row["plot5"], row["plot8"])
            for row in result.trace] == [
        (2000, 9, 100, 100, 1), (3600, -7, 115, 120, 1),
        (8000, 4, 157.5, 200, 1),
    ]


def test_agressao_por_barra_e_opt_in_sem_mudar_padrao():
    source = "begin Plot(AgressionVolBalance); end;"
    columns = dict(v_agressao_compra=[3, 2], v_agressao_venda=[1, 5])
    assert [row["plot"] for row in run(source, [100, 101], **columns).trace] == [2, -1]
    assert [row["plot"] for row in run(
        source, [100, 101], rules={"agressao_por_barra": True}, **columns).trace] == [2, -3]


def test_protecao_no_candle_da_entrada_e_opt_in():
    source = ("begin if not HasPosition then BuyAtMarket(1) else begin "
              "SellToCoverLimit(BuyPrice+20,1); "
              "SellToCoverStop(BuyPrice-5,BuyPrice-10,1); end; end;")
    o, h, l, c = [100, 100, 94], [100, 101, 96], [100, 94, 90], [100, 96, 92]
    standard = run_ohlc(source, o, h, l, c)
    assert [(fill["barra"], fill["acao"], fill["preco"]) for fill in standard.fills[:2]] == [
        (2, "long", 100), (3, "exit_long", 94),
    ]
    same_candle = run_ohlc(source, o, h, l, c, rules={
        "protecao_no_candle_entrada": True,
        "rastrear_ordens": True,
    })
    assert [(fill["barra"], fill["acao"], fill["preco"]) for fill in same_candle.fills[:2]] == [
        (2, "long", 100), (2, "exit_long", 95),
    ]
    events = [event["evento"] for event in same_candle.order_events if event["barra"] == 2]
    assert "avaliacao_ntsl" in events
    assert "protecao_elegivel_candle_entrada" in events
    assert "gatilho_stop" in events
    stop_fill = next(event for event in same_candle.order_events
                     if event["evento"] == "preenchimento"
                     and event["ordem"] == "selltocoverstop")
    assert stop_fill["gatilho"] == 95
    assert stop_fill["limite"] == 90
    assert stop_fill["preco_execucao"] == 95


def test_stop_limit_ja_ativo_nao_depende_da_nova_regra():
    source = ("begin if CurrentBar=1 then BuyAtMarket(1); "
              "if IsBought then SellToCoverStop(BuyPrice-5,BuyPrice-10,1); end;")
    o = [100, 100, 100, 94]
    h = [100, 101, 101, 96]
    l = [100, 99, 94, 90]
    c = [100, 100, 96, 92]
    standard = run_ohlc(source, o, h, l, c)
    same_candle = run_ohlc(source, o, h, l, c,
                           rules={"protecao_no_candle_entrada": True})
    assert standard.fills[-1]["preco"] == same_candle.fills[-1]["preco"] == 95
    assert standard.fills[-1]["barra"] == same_candle.fills[-1]["barra"] == 3


@pytest.mark.parametrize("mode", ["protecao_no_candle_entrada", "avaliacao_pos_preenchimento"])
def test_saida_a_mercado_decidida_no_fechamento_nao_retroage_para_abertura(mode):
    source = ("begin if CurrentBar=1 then BuyAtMarket(1); "
              "if IsBought and (Close < BuyPrice) then SellToCoverAtMarket(1); end;")
    engine = run_ohlc(source, [100, 100, 80], [100, 105, 85],
                      [100, 90, 75], [100, 90, 80],
                      rules={mode: True})
    assert [(fill["barra"], fill["acao"], fill["preco"]) for fill in engine.fills[:2]] == [
        (2, "long", 100), (3, "exit_long", 80),
    ]


@pytest.mark.parametrize(
    "entry,opening,high,low,entry_price",
    [
        ("BuyAtLimit(90)", 100, 110, 90, 90),
        ("BuyAtStop(105)", 100, 115, 100, 105),
    ],
)
def test_protecao_nao_retroage_quando_entrada_nao_e_a_mercado(
        entry, opening, high, low, entry_price):
    source = (f"begin if CurrentBar=1 then {entry}; "
              "if IsBought then SellToCoverLimit(BuyPrice+5,1); end;")
    engine = run_ohlc(source, [100, opening, 100], [100, high, 100],
                      [100, low, 100], [100, 100, 100],
                      rules={"protecao_no_candle_entrada": True})
    assert engine.fills[0]["barra"] == 2
    assert engine.fills[0]["preco"] == entry_price
    assert not any(fill["acao"] == "exit_long" and fill["barra"] == 2
                   for fill in engine.fills)


def test_segunda_passagem_nao_reprocessa_ordem_antiga_disparada():
    frame = pd.DataFrame(dict(
        pregao=["2026-10-02"], abertura=[100], maxima=[120],
        minima=[80], fechamento=[100], barra_ntsl=[1],
    ))
    engine = Engine(compile_ntsl("begin end;"), frame, 5, {}, 60, 1)
    engine.row = engine.cursor = 0
    engine.position = 1
    engine.basis = 100
    old = Order("buyatstop", "long", "stop", 1, 105, 110,
                triggered=True, eligible_at=0, sent_at=-1)
    protection = Order("selltocoverlimit", "exit_long", "limit", 1, 130,
                       eligible_at=0, sent_at=0)
    engine.orders = {"old": old, "protection": protection}
    engine.process_orders({"protection"})
    assert engine.orders["old"] is old
    assert old.triggered
    assert not engine.fills


def test_gap_pelo_limite_na_protecao_nova_nao_presume_retorno_na_mesma_barra():
    source = ("begin if CurrentBar=1 then BuyAtMarket(1); if IsBought then "
              "SellToCoverStop(Close-5,Close-10,1); end;")
    engine = run_ohlc(source, [100, 100, 100], [100, 125, 112],
                      [100, 95, 100], [100, 120, 105],
                      rules={"protecao_no_candle_entrada": True})
    exits = [fill for fill in engine.fills if fill["acao"] == "exit_long"]
    assert (exits[0]["barra"], exits[0]["preco"]) == (3, 110)


def test_alvo_e_stop_tocados_na_barra_da_entrada_escolhem_saida_adversa():
    source = ("begin if CurrentBar=1 then BuyAtMarket(1); if IsBought then begin "
              "SellToCoverLimit(BuyPrice+20,1); "
              "SellToCoverStop(BuyPrice-5,BuyPrice-10,1); end; end;")
    engine = run_ohlc(source, [100, 100], [100, 125], [100, 94], [100, 110],
                      rules={"protecao_no_candle_entrada": True})
    assert [(fill["acao"], fill["preco"]) for fill in engine.fills] == [
        ("long", 100), ("exit_long", 95),
    ]
    assert engine.ambiguities == 1


def test_avaliacao_pos_preenchimento_reentrada_em_quatro_barras():
    source = """
    begin
      if IsBought then begin
        SellToCoverLimit(BuyPrice+20,1);
        SellToCoverStop(BuyPrice-5,BuyPrice-10,1);
      end
      else if Close >= 90 then BuyAtMarket(1);
    end;
    """
    candles = ([100, 100, 92, 88], [102, 101, 93, 89],
               [99, 94, 86, 87], [101, 97, 88, 88])

    standard = run_ohlc(source, *candles)
    legacy = run_ohlc(source, *candles, rules={"protecao_no_candle_entrada": True})
    assert [(f["barra"], f["acao"], f["preco"]) for f in standard.fills] == [
        (2, "long", 100), (3, "exit_long", 92),
    ]
    assert [(f["barra"], f["acao"], f["preco"]) for f in legacy.fills] == [
        (2, "long", 100), (2, "exit_long", 95),
    ]

    experimental = run_ohlc(source, *candles, rules={
        "avaliacao_pos_preenchimento": True, "rastrear_ordens": True,
    })
    assert [(f["barra"], f["acao"], f["preco"]) for f in experimental.fills] == [
        (2, "long", 100), (2, "exit_long", 95),
        (3, "long", 92), (3, "exit_long", 87),
    ]
    events = experimental.order_events
    assert [(e["barra"], e["posicao"]) for e in events if e["evento"] == "avaliacao_ntsl"] == [
        (1, 0), (2, 0), (3, 0), (4, 0),
    ]
    assert [(e["barra"], e["chave"]) for e in events if e["evento"] == "solicitacao"] == [
        (1, "buyatmarket"),
        (2, "selltocoverlimit"), (2, "selltocoverstop"), (2, "buyatmarket"),
        (3, "selltocoverlimit"), (3, "selltocoverstop"),
    ]
    assert [e["gatilho"] for e in events if e["evento"] == "gatilho_stop"] == [95, 87]
    assert experimental.ambiguities == standard.ambiguities == legacy.ambiguities == 0
    assert not experimental.orders


def test_protecao_na_abertura_usa_ohlc_e_rotulo_da_barra_anterior():
    source = """
    begin
      if CurrentBar=1 then begin
        if IsBought then begin
          SellToCoverLimit(BuyPrice+30+High-Low,1);
          SellToCoverStop(Close-5,Close-10,1);
        end
        else BuyAtMarket(1);
      end;
    end;
    """
    engine = run_ohlc(source, [100, 100, 120], [103, 130, 125],
                      [99, 95, 115], [101, 125, 120],
                      rules={"avaliacao_pos_preenchimento": True, "rastrear_ordens": True})
    assert [(f["barra"], f["preco"]) for f in engine.fills] == [(2, 100), (2, 96)]
    requests = [e for e in engine.order_events if e["barra"] == 2 and e["evento"] == "solicitacao"]
    assert [(e["chave"], e["gatilho"], e["limite"], e["barra_contexto_ntsl"]) for e in requests] == [
        ("selltocoverlimit", 134, "", 1), ("selltocoverstop", 96, 91, 1),
    ]


def test_avaliacao_na_abertura_isola_estado_e_renova_protecao_sem_duplicar():
    source = """
    var n: Integer;
        visits: array[1..1] of Integer;
    begin
      n := n+1;
      visits[1] := visits[1]+1;
      Plot(n);
      Plot2(visits[1]);
      Plot3(Media(2, Close));
      Plot4(n[1]);
      if IsBought then begin
        if CurrentBar=1 then BuyAtMarket(2);
        SellToCoverStop(BuyPrice-5,BuyPrice-10,1);
      end
      else if CurrentBar=1 then BuyAtMarket(1);
    end;
    """
    engine = run_ohlc(source, [100, 100, 108, 98], [100, 110, 111, 99],
                      [100, 98, 94, 97], [100, 110, 96, 98],
                      rules={"avaliacao_pos_preenchimento": True, "rastrear_ordens": True})
    assert [(r["plot"], r["plot2"], r["plot3"], r["plot4"]) for r in engine.trace] == [
        (1, 1, 100, 0), (2, 2, 105, 1), (3, 3, 103, 2), (4, 4, 97, 3),
    ]
    assert engine.history[:, engine.program.symbols["n"].slot].tolist() == [1, 2, 3, 4]
    assert [(f["barra"], f["acao"], f["quantidade"]) for f in engine.fills] == [
        (2, "long", 1), (3, "exit_long", 1),
    ]
    assert [(e["barra"], e["evento"], e["primeira_barra_elegivel"]) for e in engine.order_events
            if e["chave"] == "selltocoverstop" and e["evento"].startswith("solicitacao")] == [
        (2, "solicitacao", 2), (2, "solicitacao_renovada", 2),
    ]
    assert [(e["barra"], e["quantidade"]) for e in engine.order_events
            if e["chave"] == "buyatmarket" and e["evento"] == "solicitacao"] == [(1, 1)]


def test_stop_disparado_na_posicao_anterior_nao_e_reutilizado():
    source = """
    begin
      if IsBought then begin
        SellToCoverStop(BuyPrice-5,BuyPrice-10,1);
        if CurrentBar=3 then SellToCoverAtMarket(1);
      end
      else if (CurrentBar=1) or (CurrentBar=4) then BuyAtMarket(1);
    end;
    """
    engine = run_ohlc(source, [100, 100, 85, 88, 100, 97], [100, 106, 88, 89, 101, 98],
                      [100, 98, 80, 86, 94, 96], [100, 102, 86, 87, 96, 97],
                      rules={"avaliacao_pos_preenchimento": True, "rastrear_ordens": True})
    assert [(f["barra"], f["ordem"], f["preco"]) for f in engine.fills] == [
        (2, "buyatmarket", 100), (4, "selltocoveratmarket", 88),
        (5, "buyatmarket", 100), (5, "selltocoverstop", 95),
    ]
    assert [(e["barra"], e["gatilho"]) for e in engine.order_events if e["evento"] == "gatilho_stop"] == [
        (3, 95), (5, 95),
    ]


@pytest.mark.parametrize("boundary", ["lacuna", "sessao"])
def test_avaliacao_na_abertura_nao_atravessa_limite_de_historico(boundary):
    source = """
    begin
      if IsBought then SellToCoverStop(BuyPrice-5,BuyPrice-10,1)
      else if CurrentBar<=2 then BuyAtMarket(1);
    end;
    """
    days = ["2026-10-02", "2026-10-05", "2026-10-05"] if boundary == "sessao" else None
    engine = run(source, [100, 110, 120], days,
                 {"avaliacao_pos_preenchimento": True, "rastrear_ordens": True},
                 lacuna_intradiaria=[False, boundary == "lacuna", False])
    assert engine.fills[0]["barra"] == 3
    assert engine.orders_cancelled_at_gaps == (1 if boundary == "lacuna" else 0)
    assert [(e["barra"], e["barra_contexto_ntsl"]) for e in engine.order_events
            if e["evento"] == "avaliacao_ntsl_pos_preenchimento"] == [(3, 2)]


def test_posicao_com_entrada_mista_nao_recebe_protecao_retroativa():
    source = """
    begin
      if CurrentBar=1 then begin
        BuyAtMarket(1);
        BuyAtLimit(90,1);
      end;
      if IsBought then SellToCoverLimit(BuyPrice+5,2);
    end;
    """
    engine = run_ohlc(source, [100, 100, 120], [100, 115, 125], [100, 90, 115], [100, 105, 120],
                      rules={"avaliacao_pos_preenchimento": True, "rastrear_ordens": True})
    assert [(f["barra"], f["acao"], f["preco"]) for f in engine.fills] == [
        (2, "long", 100), (2, "long", 90), (3, "exit_long", 120),
    ]
    assert not any(e["evento"] == "avaliacao_ntsl_pos_preenchimento" for e in engine.order_events)


def test_sonda_persistencia_caracteriza_isolamento_do_modo_atual(tmp_path):
    fixture = ROOT / "docs/colaboracao/evidencias/WINZ26_v5_7_persistencia_20261026_v1"
    source = (fixture / "sonda_persistencia_simulador_v1_0.ntsl").read_text(encoding="utf-8")
    output = tmp_path / "sonda"
    run_strategy(fixture / "candles_sinteticos.csv", source, output, 60, "ohlc", 5,
                 regras={"avaliacao_pos_preenchimento": True, "rastrear_ordens": True})
    with (output / "console.csv").open(newline="", encoding="utf-8") as stream:
        log = list(csv.DictReader(stream))
    states = []
    for row in log:
        fields = dict(part.split("=", 1) for part in row["mensagem"].split(";")[1:])
        states.append((int(row["barra"]), *(int(fields[k]) for k in ("seq", "posicao", "antes", "depois"))))
    assert states == [(2, 1, 0, 0, 0), (2, 2, 1, 0, 1), (3, 2, 0, 0, 0), (4, 3, 0, 0, 0)]
    audit = pd.read_csv(output / "eventos_ordens.csv")
    opening = audit.loc[audit.evento == "avaliacao_ntsl_pos_preenchimento"]
    assert opening[["barra", "barra_contexto_ntsl", "posicao"]].values.tolist() == [[3, 2, 1]]
    fills = pd.read_csv(output / "execucoes.csv")
    assert fills[["barra", "acao", "preco"]].values.tolist() == [
        [3, "long", 100], [3, "exit_long", 95],
    ]
