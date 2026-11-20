import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PATH = Path(__file__).parents[1] / "tools" / "preparar_paridade_profit_barras.py"
SPEC = importlib.util.spec_from_file_location("preparar_paridade_profit_barras", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_separa_volume_e_calcula_vwap_aproximada_com_referencia():
    bars = pd.DataFrame([
        ["21/10/2026 09:01", 100, 105, 95, 102, 7, 10, 204],
        ["21/10/2026 09:00", 90, 101, 89, 100, 5, 20, 400],
    ])
    indicators = pd.DataFrame({
        "Data": ["21/10/2026 09:00", "21/10/2026 09:01"],
        "v_Saldo_Agressao": [3, -4],
    })
    # A validacao aceita exportacoes reais com colunas adicionais.
    for index in range(8):
        indicators[f"extra_{index}"] = index
    result, metrics = MODULE.prepare(bars, "2026-10-21", indicators)
    assert result.timestamp.iloc[0].isoformat() == "2026-10-21T09:00:00-03:00"
    assert result.volume.tolist() == [20, 10]
    assert result.volume_financeiro.tolist() == [400, 204]
    assert result.v_vwap_barra.tolist() == [100, 102]
    assert result.v_agressao_saldo_referencia.tolist() == [3, -4]
    assert metrics["agressao_referencia_injetada_disponivel"] is True


def test_rejeita_horario_duplicado():
    bars = pd.DataFrame([
        ["21/10/2026 09:00", 100, 100, 100, 100, 1, 1, 20],
        ["21/10/2026 09:00", 100, 100, 100, 100, 1, 1, 20],
    ])
    with pytest.raises(ValueError, match="Profit barras possui horario duplicado"):
        MODULE.prepare(bars, "2026-10-21")
