from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from estrategia import Engine, Order, run_strategy, source_text
from ntsl import compile_ntsl
from tools.comparar_v5_8 import audit_by_label, compare_audit, compare_bar_inputs, compare_fills, unique_native_capture


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/colaboracao/evidencias/WINZ26_v5_8_validacao_20261021_20261026_v1"
AUDIT = EVIDENCE / "Modelo_Unificado_v5_8_Auditoria_simulador_v1_0.ntsl"
RULES = dict(avaliacao_pos_preenchimento=True, rastrear_ordens=True,
             volume_financeiro_ntsl=True, agressao_referencia_injetada=True,
             vwap_continuo_lacunas=True)
INPUTS = dict(p_exec_tick=0, p_periodo_atr=1, p_periodo_regime_atr=2,
              p_periodo_desvio=3, p_desvio_vwap=0, p_zscore_vol=-100,
              p_stop_pontos=5, p_lote=2, p_max_entradas_dia=2)


def market_frame(day_two=None, size=18, scale=100):
    minutes = list(pd.date_range("2026-10-21 09:15", periods=size, freq="min"))
    if day_two:
        minutes.extend(pd.date_range("2026-10-26 " + day_two, periods=13, freq="min"))
    count = len(minutes)
    index = np.arange(count)
    return pd.DataFrame({
        "timestamp": minutes,
        "pregao": [minute.date().isoformat() for minute in minutes],
        "data_ntsl": [1261021 if minute.day == 21 else 1261026 for minute in minutes],
        "hora_ntsl": [minute.hour * 100 + minute.minute for minute in minutes],
        "barra_ntsl": index + 1,
        "abertura": scale + 5,
        "maxima": scale + 16,
        "minima": scale - 6,
        "fechamento": scale + 10,
        "volume_financeiro": 2000 + index ** 2,
        "volume_contratos": 1,
        "v_vwap_barra": scale,
        "v_trades_atual": 120 + index,
        "v_agressao_saldo_referencia": 1,
    })


def run_control(frame, *, pending=None, **overrides):
    engine = Engine(compile_ntsl(source_text(AUDIT)), frame, 5, INPUTS | overrides,
                    60, 0.2, regras=RULES)
    if pending is not None:
        engine.orders["synthetic_pending"] = pending
    engine.run()
    events = []
    for _, message in engine.logs:
        prefix, event, *fields = message.split(";")
        if prefix == "V58":
            events.append((event, dict((key, float(value)) for key, value in
                                       (field.split("=", 1) for field in fields))))
    return engine, events


def requests(events):
    return [(int(r["data"]), int(r["barra"])) for event, r in events if event == "ENTRADA_COMPRA"]


def test_v5_8_completa_stop_espera_entrada_unica_e_limite_diario():
    engine, events = run_control(market_frame("09:14"))
    assert requests(events) == [(1261021, 9), (1261021, 13), (1261026, 20), (1261026, 24)]
    extra = next(r for event, r in events if event == "AVALIACAO" and r["barra"] == 9 and r["posicao"] == 2)
    assert (extra["ultima_entrada"], extra["pode"], extra["entradas"]) == (9, 0, 1)
    closed = next(r for event, r in events if event == "AVALIACAO" and r["barra"] == 10)
    assert (closed["posicao"], closed["anterior"], closed["ultima_saida"], closed["pode"]) == (0, 1, 10, 0)
    new_day = next(r for event, r in events if event == "AVALIACAO" and r["data"] == 1261026)
    assert new_day["entradas"] == 0
    assert [(f["barra"], f["acao"], f["quantidade"]) for f in engine.fills[:2]] == [
        (10, "long", 2), (10, "exit_long", 2),
    ]


def test_v5_8_completa_caracteriza_reinicio_repetido_na_abertura():
    _, events = run_control(market_frame("09:15"))
    assert requests(events) == [(1261021, 9), (1261021, 13), (1261026, 19),
                                (1261026, 23), (1261026, 27)]
    first_bar = [r for event, r in events if event == "AVALIACAO" and r["barra"] == 19]
    assert [(r["posicao"], r["entradas"]) for r in first_bar] == [(0, 0), (2, 0)]


def test_v5_8_completa_cancela_pendente_quando_zerado():
    engine, events = run_control(market_frame(size=3),
                                pending=Order("synthetic_pending", "long", "limit", 1, 1, eligible_at=2))
    assert [(event, int(row["barra"])) for event, row in events if event.startswith("CANCELA")] == [
        ("CANCELA_PENDENTES", 1),
    ]
    assert not engine.orders and not engine.fills


def test_v5_8_completa_stop_limit_folga_50_gap_e_quantidade_real():
    data = market_frame(scale=1000)
    data.loc[10, ["abertura", "maxima", "minima", "fechamento"]] = [580, 595, 570, 590]
    data.loc[11, ["abertura", "maxima", "minima", "fechamento"]] = [590, 615, 580, 610]
    engine, events = run_control(data, p_stop_pontos=350, p_max_entradas_dia=1)
    stop = next(r for event, r in events if event == "STOP_VENDA")
    assert (stop["qtd"], stop["gatilho"], stop["limite"]) == (2, 655, 605)
    assert [(f["barra"], f["preco"], f["quantidade"]) for f in engine.fills] == [
        (10, 1005, 2), (12, 605, 2),
    ]
    assert [e["barra"] for e in engine.order_events if e["evento"] == "gatilho_stop"] == [11]


def test_v5_8_completa_power_e_referencias_da_barra_anterior():
    data = market_frame(size=25)
    data["fechamento"] = 101 + np.arange(len(data)) % 5
    _, events = run_control(data, p_modo_banda=1, p_max_entradas_dia=0)
    row = next(r for event, r in events if event == "AVALIACAO" and r["barra"] == 25)
    squared = (data["fechamento"].iloc[22:25] - 100) ** 2
    prior_volume = data["volume_financeiro"].iloc[4:24]
    assert row["desvio_banda"] == pytest.approx(np.sqrt(squared.mean()))
    assert row["trades_1"] == data["v_trades_atual"].iloc[23]
    assert row["media_volume_1"] == pytest.approx(prior_volume.mean())
    assert row["desvio_volume_1"] == pytest.approx(prior_volume.std(ddof=0))
    assert row["zvolume"] == pytest.approx((data["volume_financeiro"].iloc[24] - prior_volume.mean())
                                         / prior_volume.std(ddof=0))


def test_sonda_v2_boolean_array_e_historico(tmp_path):
    prior = EVIDENCE.parent / "WINZ26_v5_7_persistencia_20261026_v1"
    result = tmp_path / "sonda"
    run_strategy(prior / "candles_sinteticos.csv",
                 source_text(EVIDENCE / "sonda_persistencia_simulador_v2_0.ntsl"),
                 result, 60, "ohlc", 5, regras=RULES | {"volume_financeiro_ntsl": False,
                                                       "agressao_referencia_injetada": False})
    messages = pd.read_csv(result / "console.csv")["mensagem"].tolist()
    fields = [dict(part.split("=", 1) for part in row.split(";")[2:]) for row in messages]
    assert len(fields) == 4
    assert [fields[1][key] for key in ("boolean_depois", "array_depois", "estado_depois")] == ["1", "17", "23"]
    assert [fields[2][key] for key in ("posicao", "boolean_antes", "array_antes", "estado_1")] == ["0", "1", "0", "0"]


def test_comparador_v5_8_preserva_rotulo_e_primeira_solicitacao_divergente():
    day = "2026-10-26"
    native = [
        "V58;AVALIACAO;data=1.261.026;hora=1.303;barra=27.005;seq=1;posicao=0",
        "V58;ENTRADA_COMPRA;data=1.261.026;hora=1.303;barra=27.005;seq=1;qtd=5",
        "V58;AVALIACAO;data=1.261.026;hora=1.303;barra=27.005;seq=2;posicao=5",
        "V58;STOP_VENDA;data=1.261.026;hora=1.303;barra=27.005;seq=2;gatilho=1.000,00",
    ]
    local = [
        "V58;AVALIACAO;data=1261026.0;hora=1303.0;barra=2.0;seq=1;posicao=0",
        "V58;ENTRADA_COMPRA;data=1261026.0;hora=1303.0;barra=2.0;seq=1;qtd=5",
        "V58;AVALIACAO;data=1261026.0;hora=1303.0;barra=2.0;seq=2;posicao=5",
        "V58;STOP_VENDA;data=1261026.0;hora=1303.0;barra=2.0;seq=2;gatilho=995.0",
    ]
    profit, motor = audit_by_label(native, day, True), audit_by_label(local, day, False)
    assert compare_audit(profit, motor, {"13:03"}, "posicao", {"posicao": 0})["divergentes"] == 0
    result = compare_audit(profit, motor, {"13:03"}, "solicitacoes", {"qtd": 0, "gatilho": 0})
    first = result["primeira_divergencia"]
    assert (first["hora_barra_contexto"], first["ordem_na_camada"], first["campo"]) == (
        "13:03", 2, "gatilho",
    )
    assert first["profit"]["barra_contexto"] == 27005
    assert first["simulador"]["barra_contexto"] == 2
    with pytest.raises(ValueError, match="Sequência reiniciada"):
        audit_by_label(native + native, day, True)


def test_comparador_v5_8_aponta_saida_como_primeiro_preenchimento_divergente():
    stamps = pd.to_datetime(["2026-10-26T13:04:00-03:00", "2026-10-26T13:05:00-03:00"])
    profit = pd.DataFrame({
        "entrada": stamps[:1], "saida": stamps[1:], "numero_operacao": [1], "lado": ["C"],
        "quantidade": [1], "preco_entrada": [100], "preco_saida": [95],
    })
    candles = pd.DataFrame({"indice": [0, 1], "timestamp": stamps})
    fills = pd.DataFrame({"barra": [1, 2], "acao": ["long", "exit_long"],
                          "quantidade": [1, 1], "preco": [100, 90]})
    first = compare_fills(profit, fills, candles)["primeira_divergencia"]
    assert first["ordem"] == 2
    assert first["profit"] == ("2026-10-26T13:05:00-03:00", "exit_long", 1, 95)


def test_comparador_v5_8_aceita_somente_blocos_nativos_identicos():
    original = ["V58;AVALIACAO;seq=1", "V58;ENTRADA_COMPRA;seq=1", "V58;AVALIACAO;seq=2"]
    capture, copies = unique_native_capture(["Modo de Debug", *original, *original])
    assert capture == original
    assert copies == 2
    with pytest.raises(ValueError, match="execuções distintas"):
        unique_native_capture(original + [original[0], original[2]])


def test_comparador_v5_8_marca_campos_ausentes_na_exportacao_ohlc():
    raw = pd.DataFrame({"timestamp": pd.to_datetime(["2026-10-21 09:00", "2026-10-21 09:01"]),
                        "abertura": [100, 101], "maxima": [103, 104],
                        "minima": [98, 99], "fechamento": [101, 102]})
    prepared = raw.assign(v_trades_atual=10, volume_contratos=15, volume_financeiro=300)
    prepared.loc[1, "fechamento"] = 103
    result = compare_bar_inputs(raw, prepared)
    assert result["comuns"] == 2
    assert result["campos_ausentes_exportacao_profit"] == ["quantity", "trades", "volume_financeiro"]
    assert result["campos"]["fechamento"]["primeira_divergencia"]["timestamp"] == "2026-10-21T09:01:00"


def test_toques_no_mesmo_milissegundo_nao_provam_ordem():
    from datetime import datetime
    from types import SimpleNamespace

    from tools.investigar_protecoes_v5_8 import describe_trade_minute

    start = datetime(2026, 10, 26, 10, 15)
    tie = start.replace(microsecond=1000)
    rows = [(start, 1, 100, 1), (tie, 3, 95, 1), (tie, 2, 105, 1)]
    bar = SimpleNamespace(abertura=100, maxima=105, minima=90, fechamento=95,
                          v_trades_atual=4, volume_contratos=4)
    result = describe_trade_minute(rows, bar, 1, 100, 105, 95, 90)
    assert result["primeiro_limiar_observado"] == "empate_ms"
    assert result["primeiros"]["alvo"]["sequencia_captura"] == 2
    assert result["primeiros"]["limite_stop"] is None
    assert result["delta_ohlc"] == [0, 0, 5, 0]
