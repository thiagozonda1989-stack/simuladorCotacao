import json
from pathlib import Path

import pandas as pd
import pytest

from estrategia import Engine, run_strategy
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
