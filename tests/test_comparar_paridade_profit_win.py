import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from tools.comparar_paridade_mesmas_barras import PLOTS, compare_engine_indicators


PATH = Path(__file__).parents[1] / "tools" / "comparar_paridade_profit_win.py"
SPEC = importlib.util.spec_from_file_location("comparar_paridade_profit_win", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_aquecimento_por_segmento_usa_contagem_real_do_replay():
    timestamps = pd.to_datetime([
        "2026-10-26 09:00", "2026-10-26 09:01", "2026-10-26 09:02",
        "2026-10-26 09:05", "2026-10-26 09:06", "2026-10-26 09:07", "2026-10-26 09:08",
    ])
    engine = pd.DataFrame({
        "timestamp": timestamps,
        "segmento": [1, 1, 1, 2, 2, 2, 2],
        "barras_no_segmento": [1, 2, 3, 1, 2, 3, 4],
        **{plot: 0 for plot, _, _ in PLOTS.values()},
    })
    profit = pd.DataFrame({"timestamp": timestamps, **{field: 0 for field in PLOTS}})
    profit = profit.drop(index=4)
    _, daily = compare_engine_indicators(profit, engine, 2)
    report, segmented = compare_engine_indicators(profit, engine, 2, by_segment=True)
    assert daily["timestamp"].tolist() == timestamps[[2, 3, 5, 6]].tolist()
    assert segmented["timestamp"].tolist() == timestamps[[2, 5, 6]].tolist()
    assert [s["barras_excluidas_aquecimento"] for s in report["aquecimento_segmentos"]] == [2, 2]
    assert [s["barras_comparadas"] for s in report["aquecimento_segmentos"]] == [1, 2]
    assert report["campos"]["atr"]["dentro_tolerancia"] == 3
    empty, _ = compare_engine_indicators(profit, engine, 4, by_segment=True)
    assert empty["primeira_barra_comparada"] is None
    assert empty["campos"]["atr"]["max_diferenca_absoluta"] is None


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


def test_comparacao_operacoes_lista_pares_e_primeiro_excedente_de_cada_fonte():
    profit = pd.DataFrame([
        {"entrada": pd.Timestamp("2026-10-21 10:00"), "saida": pd.Timestamp("2026-10-21 10:01"),
         "lado": "C", "quantidade": 1, "preco_entrada": 100.0, "preco_saida": 110.0},
        {"entrada": pd.Timestamp("2026-10-21 10:02"), "saida": pd.Timestamp("2026-10-21 10:03"),
         "lado": "V", "quantidade": 1, "preco_entrada": 120.0, "preco_saida": 115.0},
    ])
    local = pd.DataFrame([
        profit.iloc[0].to_dict(),
        {"entrada": pd.Timestamp("2026-10-21 10:04"), "saida": pd.Timestamp("2026-10-21 10:05"),
         "lado": "C", "quantidade": 1, "preco_entrada": 130.0, "preco_saida": 135.0},
    ])
    result = MODULE.compare_operations(profit, local)
    assert result["correspondencias_exatas"] == 1
    assert result["correspondencias_exatas_detalhe"][0]["entrada"].endswith("10:00:00")
    assert result["primeira_operacao_profit_sem_correspondencia"]["entrada"].endswith("10:02:00")
    assert result["primeira_operacao_local_sem_correspondencia"]["entrada"].endswith("10:04:00")


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
