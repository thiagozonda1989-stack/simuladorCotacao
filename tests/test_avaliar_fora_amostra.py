import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from tools.avaliar_fora_amostra import (avaliar, carregar_protocolo, dividir_pregoes, operacoes, rotular,
                                        sortear_variacoes, wilson)
from tools.gerar_win_sintetico import gerar

PROTOCOLO = Path(__file__).resolve().parent.parent / "docs/colaboracao/evidencias/estrategia_pullback_fora_amostra_sintetico_v1/protocolo.json"


def test_gerador_deterministico_na_grade_e_versionado():
    a, regimes = gerar(pregoes=3, versao=2, com_regimes=True)
    b = gerar(pregoes=3, versao=2)
    assert a.equals(b)
    assert len(a) == 3 * 565 and len(regimes) == 3
    precos = a[["abertura", "maxima", "minima", "fechamento"]].to_numpy()
    assert (precos % 5 == 0).all()
    assert (a["maxima"] >= a[["abertura", "fechamento"]].max(axis=1)).all()
    assert (a["minima"] <= a[["abertura", "fechamento"]].min(axis=1)).all()
    v1 = gerar(pregoes=3, versao=1)
    assert not v1.equals(a)
    assert v1["abertura"].iloc[0] == a["abertura"].iloc[0]
    with pytest.raises(ValueError):
        gerar(pregoes=1, versao=9)


def test_divisao_cronologica_sem_sobreposicao():
    dias = ["2026-07-03", "2026-07-01", "2026-07-02", "2026-07-06"]
    treino, teste = dividir_pregoes(dias * 2, 3, 1)
    assert treino == ["2026-07-01", "2026-07-02", "2026-07-03"] and teste == ["2026-07-06"]
    with pytest.raises(ValueError):
        dividir_pregoes(dias, 2, 1)


def test_rotulos_por_primeiro_toque_ambiguo_e_invalido():
    # decisão em t; referência é a abertura de t+1 = 100; níveis 110 e 90; horizonte 2
    frame = pd.DataFrame(dict(
        pregao=["d1"] * 6 + ["d2"] * 2,
        abertura=[100, 100, 100, 100, 100, 100, 100, 100],
        maxima=[100, 105, 111, 100, 112, 100, 100, 100],
        minima=[100, 95, 100, 89, 88, 100, 100, 100],
    ))
    classes = rotular(frame, pontos=10, horizonte=2)
    assert classes[0] == "C"   # barra 2 toca 111 antes de qualquer 90
    assert classes[1] == "C"
    assert classes[2] == "V"   # barra 3 toca 89
    assert classes[3] == "A"   # barra 4 toca 112 e 88 juntas
    assert classes[4] == "I" and classes[5] == "I"   # horizonte cortado pelo fim do pregão
    assert classes[6] == "I" and classes[7] == "I"


def test_rotulo_sem_toque_e_neutro():
    frame = pd.DataFrame(dict(pregao=["d"] * 4, abertura=[100] * 4, maxima=[105] * 4, minima=[95] * 4))
    assert rotular(frame, pontos=10, horizonte=2)[0] == "N"


def test_variacoes_unicas_com_padrao_primeiro():
    protocolo = carregar_protocolo(PROTOCOLO)
    espaco = protocolo["variacoes"]["espaco"]
    padrao = {"p_rapida": 9, "p_lenta": 34, "p_alvo": 200, "p_stop": 150, "p_tempomax": 30,
              "p_maxentradasdia": 4, "p_espera": 3, "p_horainicio": 930}
    a = sortear_variacoes(espaco, 50, 7, padrao)
    assert a == sortear_variacoes(espaco, 50, 7, padrao)
    assert len(a) == 50 and len({tuple(v.values()) for v in a}) == 50
    assert a[0]["p_Rapida"] == 9 and a[0]["p_Alvo"] == 200
    assert all(v["p_Rapida"] < v["p_Lenta"] for v in a)


def test_wilson_e_operacoes_pareadas():
    baixo, alto = wilson(5, 10)
    assert baixo == pytest.approx(0.2366, abs=1e-4) and alto == pytest.approx(0.7634, abs=1e-4)
    assert wilson(0, 0) == (None, None)
    motor = SimpleNamespace(fills=[
        dict(barra=5, pregao="d", acao="long", ordem="buyatmarket", liquido_reais=-0.5, pontos_contrato=0.0),
        dict(barra=9, pregao="d", acao="exit_long", ordem="selltocoverlimit", liquido_reais=39.5, pontos_contrato=200.0),
        dict(barra=12, pregao="d", acao="short", ordem="sellshortatmarket", liquido_reais=-0.5, pontos_contrato=0.0),
        dict(barra=14, pregao="d", acao="exit_short", ordem="buytocoverstop", liquido_reais=-30.5, pontos_contrato=-150.0),
    ])
    ops = operacoes(motor)
    assert ops["barra_sinal"].tolist() == [3, 10]
    assert ops["lado"].tolist() == ["C", "V"]
    assert ops["liquido_reais"].tolist() == [39.0, -31.0]
    assert ops["tipo_saida"].tolist() == ["selltocoverlimit", "buytocoverstop"]


def test_avaliacao_completa_isola_treino_e_escolhe_pelo_treino(tmp_path):
    protocolo = copy.deepcopy(carregar_protocolo(PROTOCOLO))
    protocolo["dados"]["pregoes"] = 6
    protocolo["divisao_cronologica"].update(treino_pregoes=4, teste_pregoes=2)
    protocolo["variacoes"]["quantidade"] = 3
    protocolo["selecao"]["minimo_operacoes_treino"] = 1
    protocolo["incerteza"]["reamostragens"] = 50
    frame, regimes = gerar(6, protocolo["dados"]["semente"], versao=2, com_regimes=True)
    caminho = tmp_path / "dados.csv"
    frame.to_csv(caminho, sep=";", index=False)
    resumo = avaliar(protocolo, caminho, tmp_path / "saida", regimes)

    tabela = pd.read_csv(tmp_path / "saida" / "variacoes_treino.csv", sep=";")
    assert len(tabela) == 3
    elegiveis = tabela[tabela["operacoes"] >= 1]
    assert resumo["variacao_escolhida"] == int(elegiveis.sort_values(
        ["resultado_liquido_reais", "drawdown_liquido_reais"], ascending=[False, True]).iloc[0]["variacao"])
    dias = sorted(frame["timestamp"].str[:10].unique())
    assert resumo["pregoes_treino"] == [dias[0], dias[3]] and resumo["pregoes_teste"] == [dias[4], dias[5]]
    teste = resumo["teste"]
    assert teste["pregoes"] == 2 and teste["barras"] == 2 * 565
    matriz = teste["matriz_confusao"]
    assert sum(sum(linha.values()) for linha in matriz.values()) == teste["rotulos_validos"]
    for classe in ("C", "V"):
        c = teste["por_classe"][classe]
        assert c["falsos_positivos"] == c["previstos"] - c["verdadeiros_positivos"]
    assert set(resumo["teste_por_regime_do_gerador"]) <= {"tendencia", "lateral"}
    gravado = json.loads((tmp_path / "saida" / "resultado.json").read_text(encoding="utf-8"))
    assert gravado["variacao_escolhida"] == resumo["variacao_escolhida"]
