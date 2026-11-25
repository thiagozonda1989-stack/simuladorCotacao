import json
from pathlib import Path

import pytest

from tools.criterios_rodada20 import assess

PROTOCOL = (
    Path(__file__).resolve().parents[1] / "docs/colaboracao/evidencias"
    / "WINZ26_decisao_elegibilidade_rodada20_v2/protocolo.json"
)
SETUP = json.loads(PROTOCOL.read_text(encoding="utf-8"))["validacao_inedita"]


def test_criterios_formais_em_amostra_fixa_e_com_custos_ja_descontados():
    days = {f"dia-{day:02d}": [40, 40, 40, -10] for day in range(20)}
    outcome = assess(days, 2, "v58_original", SETUP)
    assert outcome["decisao"] == "aprovado"
    assert outcome["operacoes"] == 80
    assert outcome["liquido_por_pregao"] == 110
    assert outcome["concentracao_top2"] == 0.10
    assert assess(days, 3, "v58_original", SETUP)["decisao"] == "nao_aprovado"
    with pytest.raises(ValueError, match="janela congelada"):
        assess({**days, "extra": []}, 2, "v58_original", SETUP)


def test_concentracao_com_segundo_melhor_negativo():
    days = {f"dia-{day:02d}": [-10] for day in range(20)}
    days["dia-00"] = [2000]
    outcome = assess(days, 2, "v58_original", SETUP)
    assert outcome["top2_liquido_positivo"] == 2000
    assert outcome["concentracao_top2"] == pytest.approx(2000 / 1810)
    assert not outcome["criterios"]["concentracao"]


def test_piloto_e_dias_sem_operacoes():
    assert assess({"dia": [1000] * 80}, 2, "scalper_v11_otimizada", SETUP)["decisao"] == "piloto_descritivo"
    flat_days = {f"dia-{day:02d}": [] for day in range(20)}
    flat_days["dia-01"] = [200]
    outcome = assess(flat_days, 2, "scalper_v11_otimizada", SETUP)
    assert outcome["decisao"] == "amostra_insuficiente"
    assert outcome["liquido_por_pregao"] == 10
    assert outcome["operacoes_por_pregao"] == 0.05