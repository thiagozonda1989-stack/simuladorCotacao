from pathlib import Path

import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.auditar_reserva_rodada20 import audit_warmup_tail
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

def test_aquecimento_entre_pregoes_e_rejeicao_de_lacuna_tardia(tmp_path):
    previous = pd.date_range("2026-10-19 16:45", "2026-10-19 18:24", freq="1min")
    following = pd.date_range("2026-10-20 09:00", periods=87, freq="1min")
    missing = pd.date_range("2026-10-19 18:00", periods=6, freq="1min")
    gapped = previous.difference(missing)
    assert audit_warmup_tail(previous, previous[-1], 86)["continua"]
    rejected = audit_warmup_tail(gapped, previous[-1], 86)
    assert not rejected["continua"]
    assert rejected["minutos_faltantes"] == 6
    assert not audit_warmup_tail(previous.append(previous[-1:]), previous[-1], 86)["continua"]

    source = source_text(ROOT / "estrategias/execucao/Modelo_Unificado_v5_8.ntsl")
    program = compile_ntsl(source)
    slots = {name: program.symbols[name].slot
             for name in ("v_media_atr", "v_aquecido", "v_entradas_dia")}
    rules = {"volume_financeiro_ntsl": True, "agressao_referencia_injetada": True,
             "historico_continuo": True}
    path = tmp_path / "base_aquecimento.csv"

    def run(prior, continuous):
        stamps = prior.append(following)
        high = [1025 if stamp.hour == 18 else 1050 for stamp in stamps]
        pd.DataFrame(dict(timestamp=stamps, abertura=1000, maxima=high, minima=980,
                          fechamento=1000, v_trades_atual=200, volume_contratos=300,
                          volume_financeiro=60000, v_agressao_saldo_referencia=1)).to_csv(
                              path, sep=";", index=False)
        engine = Engine(program, load_bars(path, 60, "ohlc"), 5,
                        {"p_exec_tick": 0, "p_lote": 2}, 60, 0.20,
                        regras={**rules, "historico_continuo_lacunas": continuous})
        engine.run()
        return engine

    full, full_continuous = run(previous, False), run(previous, True)
    first = len(previous)
    assert not full.gap[first]
    full.cursor = first
    assert full.series("date", 1) == 1261019
    assert full.history[first, slots["v_entradas_dia"]] == 0
    assert full.history[first, slots["v_aquecido"]] == 1
    assert full.history[first, slots["v_media_atr"]] == full_continuous.history[first, slots["v_media_atr"]]

    interrupted, uninterrupted = run(gapped, False), run(gapped, True)
    first_after_gap = len(gapped)
    assert interrupted.history[first_after_gap, slots["v_aquecido"]] == 1
    assert interrupted.history[first_after_gap, slots["v_media_atr"]] != (
        uninterrupted.history[first_after_gap, slots["v_media_atr"]]
    )

    without_warmup = run(previous[:0], False)
    assert not without_warmup.history[:86, slots["v_aquecido"]].any()
    assert without_warmup.history[86, slots["v_aquecido"]] == 1
    assert all(fill["barra"] > 86 for fill in without_warmup.fills)
