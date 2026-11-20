import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PATH = Path(__file__).parents[1] / "tools" / "comparar_paridade_profit_win.py"
SPEC = importlib.util.spec_from_file_location("comparar_paridade_profit_win", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_compara_cobertura_e_primeira_divergencia():
    profit = pd.DataFrame({
        "timestamp": pd.to_datetime(["2026-10-21 09:00", "2026-10-21 09:01", "2026-10-21 09:02"]),
        "abertura": [100, 101, 102], "maxima": [101, 102, 103], "minima": [99, 100, 101],
        "fechamento": [100, 101, 102], "trades": [10, 11, 12], "quantity": [20, 21, 22],
        "volume_financeiro": [1000, 1100, 1200],
    })
    local = profit.iloc[:2].copy()
    local.loc[1, "fechamento"] = 99
    result, _ = MODULE.compare_bars(profit, local)
    assert result["comuns"] == 2
    assert result["exclusivos_profit"] == ["2026-10-21T09:02:00"]
    assert result["campos"]["fechamento"]["primeira_divergencia"]["timestamp"] == "2026-10-21T09:01:00"


def test_execucoes_usam_numero_de_barra_a_partir_de_um():
    candles = pd.DataFrame({
        "indice": [0, 1, 2],
        "timestamp": ["2026-10-21 10:08", "2026-10-21 10:09", "2026-10-21 10:10"],
    })
    fills = pd.DataFrame([
        {"barra": 2, "acao": "long", "preco": 100, "quantidade": 1},
        {"barra": 3, "acao": "exit_long", "preco": 110, "quantidade": 1},
    ])
    result = MODULE.local_round_trips(fills, candles)
    assert result.iloc[0].entrada == pd.Timestamp("2026-10-21 10:09")
    assert result.iloc[0].saida == pd.Timestamp("2026-10-21 10:10")


def test_normaliza_fusos_para_abertura_em_sao_paulo():
    naive = pd.DataFrame({"Data": ["21/10/2026 09:00"]})
    utc = pd.DataFrame({"timestamp": ["2026-10-21T12:00:00Z"]})
    left = MODULE.normalize_bars(naive, "timestamp", "Profit")
    right = MODULE.normalize_bars(utc, "timestamp", "simulador")
    assert left.loc[0, "timestamp"] == right.loc[0, "timestamp"]
    assert left.loc[0, "timestamp"].isoformat() == "2026-10-21T09:00:00-03:00"


def test_rejeita_duplicata_informando_fonte_e_horario():
    duplicated = pd.DataFrame({
        "timestamp": ["2026-10-21 09:00", "2026-10-21 09:00"],
    })
    with pytest.raises(ValueError, match=r"captura local.*2026-10-21T09:00:00-03:00"):
        MODULE.normalize_bars(duplicated, "timestamp", "captura local")


def test_ambiguidade_de_limite_exige_precos_distintos_no_mesmo_milissegundo():
    trades = pd.DataFrame({
        "timestamp": [
            "2026-10-21 09:00:00.001", "2026-10-21 09:00:00.001",
            "2026-10-21 09:00:59.999", "2026-10-21 09:00:59.999",
            "2026-10-21 09:01:00.001", "2026-10-21 09:01:59.999",
        ],
        "preco": [100, 105, 110, 110, 111, 112],
    })
    result = MODULE.boundary_price_evidence(trades)
    assert result["barras_com_evidencia"] == 1
    assert result["ocorrencias"][0]["limite"] == "primeiro_milissegundo"
    assert result["ocorrencias"][0]["precos_distintos"] == 2
