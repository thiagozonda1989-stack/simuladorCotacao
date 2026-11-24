import pandas as pd
import pytest

from tools.metricas_pullback_rodada16 import diagnosticar, metricas


def operacoes(linhas):
    return pd.DataFrame(linhas, columns=["pregao", "barra_entrada", "barra_saida", "lado", "quantidade",
                                         "preco_entrada", "liquido_reais", "duracao_min", "saida_antecipada"])


def test_metricas_contam_pregao_sem_operacao_e_drawdown_desde_zero():
    dias = ["2026-01-02", "2026-01-05", "2026-01-06"]
    dados = operacoes([
        (dias[0], 1, 2, "C", 2, 1000, -10, 1, False),
        (dias[0], 3, 5, "V", 2, 1000, 30, 2, False),
        (dias[1], 1, 9, "C", 2, 1000, 0, 8, False),
    ])
    r = metricas(dados, dias)
    assert r["operacoes_por_pregao"] == dict(zip(dias, (2, 1, 0)))
    assert r["liquido_por_pregao"] == dict(zip(dias, (20, 0, 0)))
    assert r["liquido_reais"] == 20
    assert r["drawdown_reais"] == 10
    assert r["acerto"] == pytest.approx(1 / 3)
    assert r["duracao_mediana_min"] == 2
    assert r["duracao_p90_min"] == pytest.approx(6.8)
    assert r["resultado_medio_operacao_reais"] == pytest.approx(20 / 3)


def test_diagnostico_separa_delta_das_pareadas_e_mudanca_de_frequencia():
    dia = "2026-01-02"
    ref = operacoes([
        (dia, 1, 5, "C", 2, 1000, -40, 4, False),
        (dia, 8, 12, "V", 2, 1100, 40, 4, False),
        (dia, 13, 15, "C", 2, 1000, 8, 2, False),
    ])
    cand = operacoes([
        (dia, 1, 3, "C", 2, 1000, -10, 2, True),
        (dia, 8, 10, "V", 2, 1100, 5, 2, True),
        (dia, 13, 14, "C", 2, 1005, 3, 1, True),
        (dia, 16, 17, "V", 2, 1000, 2, 1, False),
    ])
    r = diagnosticar(ref, cand)
    assert r["antecipadas_pareadas"] == 2
    assert r["perdas_amenizadas_ou_evitadas_reais"] == 30
    assert r["ganho_suprimido_reais"] == 35
    assert r["antecipadas_sem_par"] == 1
    assert r["entradas_apenas_referencia"] == 1
    assert r["entradas_apenas_candidata"] == 2
    assert r["delta_pareadas_reais"] == -5
    assert r["delta_sem_par_reais"] == -3
    assert r["delta_pareadas_reais"] + r["delta_sem_par_reais"] == (
        cand["liquido_reais"].sum() - ref["liquido_reais"].sum()
    )
