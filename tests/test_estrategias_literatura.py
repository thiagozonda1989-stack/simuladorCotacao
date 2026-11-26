"""Regressão das 20 estratégias da literatura e da ferramenta de validação."""
from pathlib import Path

import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.gerar_estrategias_literatura import ESTRATEGIAS, fonte
from tools.gerar_win_sintetico import gerar, microestrutura
from tools.validar_estrategias_literatura import holm, variacoes

RAIZ = Path(__file__).resolve().parents[1]
REGRAS = {"custo_por_contrato_lado": 0.5, "slippage_ticks": 1, "volume_financeiro_ntsl": True,
          "agressao_referencia_injetada": True, "historico_continuo": True, "vwap_continuo_lacunas": True}


def test_vinte_estrategias_versionadas_iguais_ao_gerador():
    assert len(ESTRATEGIAS) == 20
    for nome, e in ESTRATEGIAS.items():
        arquivo = RAIZ / "estrategias" / "literatura" / f"{nome}.ntsl"
        assert arquivo.read_text(encoding="utf-8") == fonte(nome, e)
        assert "Date <> Date[1]" not in arquivo.read_text(encoding="utf-8")


def test_todas_compilam_executam_e_respeitam_risco(tmp_path):
    caminho = tmp_path / "s.csv"
    microestrutura(gerar(5, 20261124, versao=2)).to_csv(caminho, sep=";", index=False)
    quadro = load_bars(caminho, 60, "ohlc")
    for nome in ESTRATEGIAS:
        motor = Engine(compile_ntsl(source_text(RAIZ / "estrategias" / "literatura" / f"{nome}.ntsl")),
                       quadro, 5, {}, 60, 0.2, regras=REGRAS)
        motor.run(record_trace=False)
        fills = pd.DataFrame(motor.fills)
        if fills.empty:
            continue
        entradas = fills[fills.acao.isin(["long", "short"])]
        teto = int(ESTRATEGIAS[nome]["risco"]["maxdia"])
        assert entradas.groupby("pregao").size().max() <= teto, nome
        assert (fills.quantidade.abs() == 1).all(), nome
        horas = pd.to_datetime(quadro["timestamp"].iloc[fills.barra - 1].values).strftime("%H%M").astype(int)
        assert (horas[fills.acao.isin(["long", "short"]).to_numpy()] <= 1701).all(), nome


def test_orb_so_entra_depois_da_faixa_e_uma_vez_por_lado(tmp_path):
    caminho = tmp_path / "s.csv"
    microestrutura(gerar(5, 20261124, versao=2)).to_csv(caminho, sep=";", index=False)
    quadro = load_bars(caminho, 60, "ohlc")
    motor = Engine(compile_ntsl(source_text(RAIZ / "estrategias/literatura/lit01_orb.ntsl")), quadro, 5,
                   {"p_barrasabertura": 15}, 60, 0.2, regras=REGRAS)
    motor.run(record_trace=False)
    fills = pd.DataFrame(motor.fills)
    entradas = fills[fills.acao.isin(["long", "short"])]
    horas = pd.to_datetime(quadro["timestamp"].iloc[entradas.barra - 1].values).strftime("%H%M").astype(int)
    assert (horas >= 915).all()
    assert entradas.groupby(["pregao", "acao"]).size().max() == 1


def test_variacoes_e_holm():
    vs = variacoes("lit02_bollinger_reversao", 12, 7)
    assert vs[0] == {} and len(vs) == 12 and len({tuple(sorted(v.items())) for v in vs}) == 12
    assert holm({"a": 0.01, "b": 0.02, "c": 0.5}) == {"a": 0.03, "b": 0.04, "c": 0.5}
