"""Métricas da rodada 16 e decomposição do efeito das novas saídas."""

import pandas as pd


ENTRY_KEY = ["pregao", "barra_entrada", "lado", "quantidade", "preco_entrada"]


def metricas(operacoes, pregoes):
    """Resume resultados líquidos de operações completas, incluindo pregões sem operações."""
    if not pregoes or len(set(pregoes)) != len(pregoes):
        raise ValueError("A lista de pregões deve ser não vazia e sem duplicatas.")
    if not operacoes["pregao"].isin(pregoes).all():
        raise ValueError("Há operações fora dos pregões da avaliação.")

    em_ordem = operacoes.sort_values(["pregao", "barra_saida"], kind="stable")
    valores = em_ordem["liquido_reais"]
    curva = valores.cumsum()
    diario = valores.groupby(em_ordem["pregao"]).sum().reindex(pregoes, fill_value=0)
    duracao = em_ordem["duracao_min"]
    quantidade = len(valores)
    vitorias = int((valores > 0).sum())
    return {
        "liquido_reais": float(valores.sum()),
        "liquido_medio_dia_reais": float(diario.mean()),
        "liquido_por_pregao": diario.to_dict(),
        "drawdown_reais": float((curva.cummax().clip(lower=0) - curva).max()) if quantidade else 0.0,
        "operacoes": quantidade,
        "operacoes_por_dia": quantidade / len(pregoes),
        "operacoes_por_pregao": em_ordem["pregao"].value_counts().reindex(pregoes, fill_value=0).to_dict(),
        "acertos": vitorias,
        "acerto": vitorias / quantidade if quantidade else None,
        "resultado_medio_operacao_reais": float(valores.mean()) if quantidade else None,
        "duracao_mediana_min": float(duracao.median()) if quantidade else None,
        "duracao_p90_min": float(duracao.quantile(0.9, interpolation="linear")) if quantidade else None,
        "pregoes_com_3000_reais": int((diario >= 3000).sum()),
    }


def diagnosticar(referencia, candidata):
    """Compara entradas idênticas, marcando à parte as operações sem par."""
    pares = referencia[ENTRY_KEY + ["liquido_reais"]].merge(
        candidata[ENTRY_KEY + ["liquido_reais", "saida_antecipada"]],
        how="outer", on=ENTRY_KEY, suffixes=("_ref", "_cand"), indicator=True, validate="one_to_one",
    )
    comuns = pares[pares["_merge"] == "both"]
    antecipadas = comuns[comuns["saida_antecipada"].eq(True)]
    sem_ref = pares[pares["_merge"] == "right_only"]
    sem_cand = pares[pares["_merge"] == "left_only"]
    perdas_reduzidas = (-antecipadas["liquido_reais_ref"]).clip(lower=0) - (
        -antecipadas["liquido_reais_cand"]
    ).clip(lower=0)
    ganhos_cortados = antecipadas["liquido_reais_ref"].clip(lower=0) - (
        antecipadas["liquido_reais_cand"]
    ).clip(lower=0)

    return {
        "entradas_pareadas": len(comuns),
        "antecipadas_pareadas": len(antecipadas),
        "antecipadas_sem_par": int(sem_ref["saida_antecipada"].eq(True).sum()),
        "perdas_amenizadas_ou_evitadas": int((perdas_reduzidas > 0).sum()),
        "perdas_amenizadas_ou_evitadas_reais": float(perdas_reduzidas.clip(lower=0).sum()),
        "vencedoras_cortadas": int((ganhos_cortados > 0).sum()),
        "ganho_suprimido_reais": float(ganhos_cortados.clip(lower=0).sum()),
        "delta_antecipadas_pareadas_reais": float(
            (antecipadas["liquido_reais_cand"] - antecipadas["liquido_reais_ref"]).sum()
        ),
        "resultado_medio_referencia_nas_antecipadas_pareadas_reais": (
            float(antecipadas["liquido_reais_ref"].mean()) if len(antecipadas) else None
        ),
        "liquido_novas_entradas_reais": float(sem_ref["liquido_reais_cand"].sum()),
        "liquido_entradas_suprimidas_reais": float(sem_cand["liquido_reais_ref"].sum()),
        "delta_pareadas_reais": float((comuns["liquido_reais_cand"] - comuns["liquido_reais_ref"]).sum()),
        "entradas_apenas_referencia": len(sem_cand),
        "entradas_apenas_candidata": len(sem_ref),
        "delta_sem_par_reais": float(sem_ref["liquido_reais_cand"].sum() - sem_cand["liquido_reais_ref"].sum()),
    }
