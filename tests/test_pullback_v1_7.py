from pathlib import Path

import pandas as pd
import pytest

from estrategia import Engine
from ntsl import compile_ntsl
from test_rodada16_saida_por_fechamento import RULES, fills


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/colaboracao/evidencias/estrategia_pullback_adaptativo_v1/pullback_tendencia_v1_5.ntsl"
CANDIDATE = ROOT / "estrategias/execucao/pullback_tendencia_v1_7.ntsl"
PARAMETERS = {"p_rapida": 2, "p_lenta": 3, "p_janelaamplitude": 2, "p_tempomax": 5}


def run(source=CANDIDATE, *, closes=(1000, 1020, 1020), short=False, gap=False, opening_evaluation=False, **params):
    opening = [1000] * 7 + [1030, 1020, 1020, 1020, 1020]
    close = [1000] * 6 + [1030, *closes, 1020, 1020]
    high = [1005] * 6 + [1040] * 6
    low = [995] * 6 + [1000] + [990] * 5
    if short:
        opening, high, low, close = ([2000 - p for p in column]
                                     for column in (opening, low, high, close))
    times = list(range(1000, 1012))
    if gap:
        times[8:] = [time + 3 for time in times[8:]]
    frame = pd.DataFrame({
        "pregao": ["2026-01-02"] * 12, "barra_ntsl": list(range(1, 13)),
        "abertura": opening, "maxima": high, "minima": low, "fechamento": close,
        "data_ntsl": [1260102] * 12, "hora_ntsl": times,
        "lacuna_intradiaria": [gap and i == 8 for i in range(12)],
    })
    engine = Engine(compile_ntsl(source.read_text(encoding="utf-8")), frame, 5, PARAMETERS | params,
                    60, 0.2, regras=RULES | {"avaliacao_pos_preenchimento": opening_evaluation})
    engine.run()
    return engine


def early_requests(engine):
    return [i for i, row in enumerate(engine.trace, 1) if row.get("plot4") == 1]


@pytest.mark.parametrize("short", [False, True])
def test_adendo_desligado_reproduz_v15(short):
    reference = run(REFERENCE, short=short)
    candidate = run(short=short)
    assert reference.fills and reference.fills[0]["quantidade"] == 2
    assert candidate.fills == reference.fills
    assert candidate.order_events == reference.order_events
    assert candidate.trace == reference.trace


@pytest.mark.parametrize("short", [False, True])
@pytest.mark.parametrize("janela,tolerancia,closes,expected", [
    (1, 0, (1005, 1020, 1020), []),
    (1, 0, (1000, 1020, 1020), [8]),
    (1, 1, (1000, 1020, 1020), []),
    (1, 1, (995, 1020, 1020), [8]),
    (2, 0, (1010, 1000, 1020), [9]),
    (2, 0, (1010, 1010, 1000), []),
    (1, 0, (1010, 1010, 1010), []),  # Entre a máxima rompida e a máxima do sinal.
])
def test_adendo_fechamento_nivel_congelado_e_tolerancia(short, janela, tolerancia, closes, expected):
    engine = run(short=short, closes=closes, p_ativarsaidafalha=1, p_janelafalha=janela,
                 p_toleranciafalhaticks=tolerancia)
    assert engine.trace[6]["plot5"] == (995 if short else 1005)
    assert early_requests(engine) == expected
    if expected:
        market = [row for row in fills(engine) if row[1] in {"selltocoveratmarket", "buytocoveratmarket"}]
        assert market == [(expected[0] + 1, "buytocoveratmarket" if short else "selltocoveratmarket",
                           985 if short else 1015, 2)]


def test_adendo_deixa_de_valer_ao_atravessar_lacuna():
    engine = run(closes=(1000, 1000, 1000), gap=True, p_ativarsaidafalha=1, p_janelafalha=2)
    assert early_requests(engine) == [8]
    assert engine.orders_cancelled_at_gaps == 1
    assert not any(row[1] == "selltocoveratmarket" for row in fills(engine))
    assert any(event["evento"] == "solicitacao" and event["tipo"] == "stop" and event["barra"] == 9
               for event in engine.order_events)


def test_contexto_pos_preenchimento_ignora_o_adendo_ate_fechamento_regular():
    engine = run(opening_evaluation=True, p_ativarsaidafalha=1)
    assert early_requests(engine) == [8]
    evaluate = [e for e in engine.order_events if e["evento"] == "avaliacao_ntsl_pos_preenchimento"]
    assert [(e["barra"], e["barra_contexto_ntsl"]) for e in evaluate] == [(8, 7)]
    assert not any(e["evento"] == "solicitacao" and e["tipo"] == "market" and e["acao"] == "exit_long"
                   and e["barra_contexto_ntsl"] == 7 for e in engine.order_events)


def test_prazo_original_tem_prioridade_na_classificacao_da_saida():
    engine = run(p_ativarsaidafalha=1, p_tempomax=0)
    assert early_requests(engine) == []
    assert fills(engine)[1] == (9, "selltocoveratmarket", 1015, 2)
