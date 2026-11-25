from pathlib import Path

import pandas as pd

from estrategia import load_bars, source_text
from ntsl import compile_ntsl
from tools.diagnosticar_lacunas_rodada20 import GapDiagnostic, counter_control

ROOT = Path(__file__).resolve().parents[1]
SYMBOL = "v_entradas_dia"


def test_v58_lacuna_reinicia_teto_mas_aquecimento_continua(tmp_path):
    candles = list(pd.date_range("2026-10-19 09:00", periods=100, freq="1min"))
    candles.extend(pd.date_range("2026-10-19 10:45", periods=7, freq="1min"))
    candles.extend(pd.date_range("2026-10-20 09:15", periods=2, freq="1min"))
    rows = []
    for stamp in candles:
        high = 1005
        low = 995
        if stamp.hour == 10 and stamp.minute in {38, 48}:
            high = 1410
        if stamp.hour == 10 and stamp.minute == 45:
            high, low = 1020, 980
        rows.append((stamp, 1000, high, low, 1000, 200, 300, 60000, 1))
    path = tmp_path / "ohlc.csv"
    pd.DataFrame(rows, columns=[
        "timestamp", "abertura", "maxima", "minima", "fechamento",
        "v_trades_atual", "volume_contratos", "volume_financeiro", "v_agressao_saldo_referencia",
    ]).to_csv(path, sep=";", index=False)
    frame = load_bars(path, 60, "ohlc")
    source = source_text(ROOT / "estrategias/execucao/Modelo_Unificado_v5_8.ntsl")
    anchor = "  { ================= Ordens ================= }"
    assert source.count(anchor) == 1
    # Controla apenas a disponibilidade de sinal. Teto, estado, warmup e ordens são da v5.8.
    source = source.replace(anchor, """
  v_Compra_Conf := ((Time = 1036) or (Time = 1046) or (Time = 915));
  v_Venda_Conf := False;
""" + anchor)
    input_values = {"p_exec_tick": 0, "p_lote": 2, "p_max_entradas_dia": 1}
    rules = {"volume_financeiro_ntsl": True, "agressao_referencia_injetada": True,
             "historico_continuo": True}

    def run(code, continuous=False):
        program = compile_ntsl(code)
        engine = GapDiagnostic(program, frame, 5, input_values, 60, 0.2,
                               regras={**rules, "historico_continuo_lacunas": continuous})
        engine.run()
        return engine

    baseline = run(source)
    scalar = run(counter_control(source))
    continuous = run(source, continuous=True)
    before_gap, first_after = 99, 100
    day2 = 107
    for e in (baseline, scalar, continuous):
        slot = e.program.symbols[SYMBOL].slot
        assert e.history[before_gap, slot] == 1
        assert e.trace[day2]["sinal_compra"]
        assert e.history[day2, slot] == 1  # Novo pregão volta a permitir uma entrada.
    assert baseline.trace[first_after + 1]["sinal_compra"]
    assert not scalar.trace[first_after + 1]["sinal_compra"]
    assert not continuous.trace[first_after + 1]["sinal_compra"]
    assert baseline.gaps[0]["date_1"] == scalar.gaps[0]["date_1"] == 0
    assert continuous.gaps[0]["date_1"] == 1261019
    assert baseline.gaps[0]["depois"] == 0
    assert scalar.gaps[0]["depois"] == continuous.gaps[0]["depois"] == 1
    for e in (baseline, scalar):
        state = e.gaps[0]
        assert state["antes"] == 1 and state["posicao"] == 0
        assert state["barra"] == 101 and state["barras_no_segmento"] == 1
        assert state["aquecido"]
        assert state["atr"] == state["media_atr"] == 40
    assert continuous.gaps[0]["media_atr"] < 40
    assert sum(f["acao"] == "long" for f in baseline.fills if f["pregao"] == "2026-10-19") == 2
    assert sum(f["acao"] == "long" for f in scalar.fills if f["pregao"] == "2026-10-19") == 1