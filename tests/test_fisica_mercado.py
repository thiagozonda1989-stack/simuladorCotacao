"""Regressão da estratégia Física do Mercado v1.0 e do controle nulo do gerador."""
import math
from pathlib import Path

import numpy as np
import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.gerar_win_sintetico import gerar
from tools.estudar_variaveis_fisicas import fase_lunar

RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / "estrategias/pesquisa/fisica_mercado_v1_0.ntsl"


def _quadro(tmp_path, fechamentos, volume=100, dia="2026-11-03"):
    stamps = pd.date_range(f"{dia} 09:00", periods=len(fechamentos), freq="1min")
    linhas = []
    anterior = fechamentos[0]
    for t, c in zip(stamps, fechamentos):
        linhas.append((t.isoformat(), anterior, max(anterior, c) + 5, min(anterior, c) - 5, c, volume))
        anterior = c
    caminho = tmp_path / "barras.csv"
    pd.DataFrame(linhas, columns=["timestamp", "abertura", "maxima", "minima", "fechamento", "volume"]).to_csv(
        caminho, sep=";", index=False)
    return load_bars(caminho, 60, "ohlc")


def _rodar(frame, parametros=None):
    programa = compile_ntsl(source_text(FONTE))
    motor = Engine(programa, frame, 5, parametros or {}, 60, 0.2,
                   regras={"custo_por_contrato_lado": 0.5, "slippage_ticks": 1})
    motor.run()
    return programa, motor


def _valor(programa, motor, nome, linha=-1):
    return motor.history[linha, programa.symbols[nome].slot]


def test_variaveis_em_trajetoria_retilinea(tmp_path):
    # Subida constante de 1 tick por barra: ordem total, persistência e eficiência máxima.
    frame = _quadro(tmp_path, [125000 + 5 * i for i in range(200)])
    programa, motor = _rodar(frame)
    assert _valor(programa, motor, "v_entropia") == 0
    assert _valor(programa, motor, "v_eficiencia") == 1
    assert _valor(programa, motor, "v_templonga") == 25
    assert _valor(programa, motor, "v_cinetica") == 12.5
    assert _valor(programa, motor, "v_massa") == 1


def test_entropia_maxima_e_hurst_de_alternancia(tmp_path):
    # Ciclo +5, -5, 0 repetido: os três estados igualmente prováveis (entropia 1)
    # e caminho que nunca sai do lugar (eficiência 0, reversão: Hurst < 0,5).
    passos = [5, -5, 0]
    preco, fechamentos = 125000, []
    for i in range(240):
        preco += passos[i % 3]
        fechamentos.append(preco)
    programa, motor = _rodar(_quadro(tmp_path, fechamentos), {"p_janela": 30, "p_q": 3})
    assert math.isclose(_valor(programa, motor, "v_entropia"), 1.0, abs_tol=1e-9)
    assert _valor(programa, motor, "v_eficiencia") == 0
    assert _valor(programa, motor, "v_hurst") == 0


def test_contador_diario_por_data_escalar(tmp_path):
    programa = compile_ntsl(source_text(FONTE))
    assert "v_datacontagem" in programa.symbols
    texto = source_text(FONTE)
    assert "Date <> Date[1]" not in texto


def test_gerador_nulo_sem_deriva_e_mesma_estrutura():
    nulo, regimes = gerar(3, 5, versao=0, com_regimes=True)
    assert (regimes["deriva"] == 0).all()
    assert len(nulo) == 3 * 565
    assert (nulo["maxima"] >= nulo[["abertura", "fechamento"]].max(axis=1)).all()
    v2 = gerar(3, 5, versao=2)
    assert not nulo["fechamento"].equals(v2["fechamento"])


def test_fase_lunar_em_datas_conhecidas():
    # Lua cheia em 05/11/2025 10:19 BRT e lua nova em 20/11/2025 03:47 BRT.
    fases = fase_lunar(pd.Series(["2025-11-05T10:19:00", "2025-11-20T03:47:00"]))
    assert abs(fases.iloc[0] - 0.5) < 0.02
    assert min(fases.iloc[1], 1 - fases.iloc[1]) < 0.02


def test_estrategia_executa_e_respeita_teto_diario(tmp_path):
    frame = gerar(4, 20261124, versao=2)
    caminho = tmp_path / "s.csv"
    frame.to_csv(caminho, sep=";", index=False)
    quadro = load_bars(caminho, 60, "ohlc")
    _, motor = _rodar(quadro, {"p_maxentradasdia": 2})
    entradas = pd.Series([f["pregao"] for f in motor.fills if f["acao"] in ("long", "short")])
    assert len(entradas) > 0
    assert entradas.value_counts().max() <= 2
