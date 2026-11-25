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


MODELOS_FISICA = [
    ("estrategias/execucao/Modelo_Unificado_v5_8.ntsl", "estrategias/pesquisa/Modelo_Unificado_v5_8_fisica_v1_0.ntsl",
     {"p_exec_tick": 0, "p_lote": 2}),
    ("estrategias/execucao/modelo_scalper_v1_1.ntsl", "estrategias/pesquisa/modelo_scalper_v1_1_fisica_v1_0.ntsl",
     {"p_alvopontos": 100, "p_stoppontos": 150, "p_offsetstop": 10, "p_lote": 2, "p_periodomediafluxo": 12,
      "p_thresholdfluxo": 2.3, "p_mintradesbarra": 400, "p_maxbarrasposicao": 6, "p_cooldownminutos": 10}),
    ("estrategias/pesquisa/pullback_tendencia_v1_0.ntsl", "estrategias/pesquisa/pullback_tendencia_v1_1_fisica.ntsl", {}),
]
REGRAS_MICRO = {"custo_por_contrato_lado": 0.5, "slippage_ticks": 1, "volume_financeiro_ntsl": True,
                "agressao_referencia_injetada": True, "historico_continuo": True, "vwap_continuo_lacunas": True}


def _quadro_micro(tmp_path, pregoes=6):
    from tools.gerar_win_sintetico import microestrutura
    caminho = tmp_path / "micro.csv"
    microestrutura(gerar(pregoes, 20261124, versao=2)).to_csv(caminho, sep=";", index=False)
    return load_bars(caminho, 60, "ohlc")


def test_modelos_fisica_desligados_reproduzem_original(tmp_path):
    quadro = _quadro_micro(tmp_path)
    for original, fisica, parametros in MODELOS_FISICA:
        fills = []
        for fonte in (original, fisica):
            motor = Engine(compile_ntsl(source_text(RAIZ / fonte)), quadro, 5, parametros, 60, 0.2, regras=REGRAS_MICRO)
            motor.run(record_trace=False)
            fills.append(motor.fills)
        assert len(fills[0]) > 0, original
        assert fills[0] == fills[1], fisica


def test_modelos_fisica_ligados_mudam_alvo_e_filtram(tmp_path):
    quadro = _quadro_micro(tmp_path)
    original, fisica, parametros = MODELOS_FISICA[0]
    base = Engine(compile_ntsl(source_text(RAIZ / fisica)), quadro, 5, parametros, 60, 0.2, regras=REGRAS_MICRO)
    base.run(record_trace=False)
    temp = Engine(compile_ntsl(source_text(RAIZ / fisica)), quadro, 5,
                  {**parametros, "p_fistemp": 1, "p_fatoralvot": 0.5, "p_fatorstopt": 0.5}, 60, 0.2, regras=REGRAS_MICRO)
    temp.run(record_trace=False)
    mola = Engine(compile_ntsl(source_text(RAIZ / fisica)), quadro, 5,
                  {**parametros, "p_fismola": 1, "p_xmax": 0.0}, 60, 0.2, regras=REGRAS_MICRO)
    mola.run(record_trace=False)
    assert temp.fills != base.fills
    entradas = lambda m: sum(f["acao"] in ("long", "short") for f in m.fills)
    assert entradas(mola) < entradas(base)


MODELOS_FISICA_V11 = [
    (orig, fis.replace("v5_8_fisica_v1_0", "v5_8_fisica_v1_1").replace("v1_1_fisica_v1_0", "v1_1_fisica_v1_1")
     .replace("pullback_tendencia_v1_1_fisica", "pullback_tendencia_v1_2_fisica"), par)
    for orig, fis, par in MODELOS_FISICA
]


def test_fisica_v11_desligada_reproduz_original(tmp_path):
    quadro = _quadro_micro(tmp_path)
    for original, fisica, parametros in MODELOS_FISICA_V11:
        fills = []
        for fonte in (original, fisica):
            motor = Engine(compile_ntsl(source_text(RAIZ / fonte)), quadro, 5, parametros, 60, 0.2, regras=REGRAS_MICRO)
            motor.run(record_trace=False)
            fills.append(motor.fills)
        assert fills[0] == fills[1], fisica


def test_fisica_v11_deriva_do_dia_e_mola_ajustada(tmp_path):
    quadro = _quadro_micro(tmp_path)
    original, fisica, parametros = MODELOS_FISICA_V11[0]
    programa = compile_ntsl(source_text(RAIZ / fisica))

    def rodar(extra):
        m = Engine(programa, quadro, 5, {**parametros, **extra}, 60, 0.2, regras=REGRAS_MICRO)
        m.run(record_trace=False)
        return m

    base = rodar({})
    h = lambda n: base.history[:, programa.symbols[n].slot]
    # z do dia = (Close - abertura do pregão) / (sigma * raiz(n)), com n contado desde a 1ª barra do pregão
    primeira = quadro.groupby("pregao").head(1).index
    abertura = quadro["abertura"].groupby(quadro["pregao"]).transform("first").to_numpy()
    n = quadro.groupby("pregao").cumcount().to_numpy() + 1
    esperado = (quadro["fechamento"].to_numpy() - abertura) / (h("v_fissigma") * np.sqrt(n))
    linhas = np.flatnonzero(h("v_fissigma") > 0)
    assert np.allclose(h("v_fiszdia")[linhas], esperado[linhas])
    assert (h("v_fisn")[primeira] == 1).all()
    entradas = lambda m: sum(f["acao"] in ("long", "short") for f in m.fills)
    mola = rodar({"p_fismola": 1, "p_xmax": 0.0})
    # deriva exigida impossível: a mola ajustada bloqueia o mesmo que a mola v1.0
    ajustada_igual = rodar({"p_fismola": 1, "p_xmax": 0.0, "p_fismoladeriva": 1, "p_zdia": 1e9})
    assert ajustada_igual.fills == mola.fills
    # deriva exigida trivial: a mola ajustada libera tudo que vai a favor da deriva
    ajustada_livre = rodar({"p_fismola": 1, "p_xmax": 0.0, "p_fismoladeriva": 1, "p_zdia": -1e9})
    assert entradas(ajustada_livre) > entradas(mola)
    assert entradas(rodar({"p_fisderiva": 1, "p_zdia": 1e9})) < entradas(base)


def test_deriva_real_recortes_e_guarda_de_sha(tmp_path, monkeypatch):
    import sys
    import pytest
    from tools import testar_deriva_real as tdr
    r = tdr.recortes()
    assert len(r["conhecidos"]) == 20 and len(r["desenvolvimento"]) == 19
    assert not set(r["conhecidos"]) & set(r["desenvolvimento"])
    assert tdr.PRIMARIA in tdr.VARIANTES and len(tdr.VARIANTES) >= 10
    falsa = tmp_path / "base.csv"
    falsa.write_text("timestamp;abertura;maxima;minima;fechamento;volume\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["x", "--base", str(falsa), "--saida", str(tmp_path / "s")])
    with pytest.raises(SystemExit, match="congelada"):
        tdr.main()
