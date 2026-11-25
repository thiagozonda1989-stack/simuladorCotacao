"""Testa as variáveis físicas (temperatura e mola) nos modelos conhecidos.

Para cada modelo, a variação 1 é o perfil original congelado, com as variáveis
físicas desligadas. As demais variações ligam a temperatura (alvo e stop
proporcionais a sigma * raiz(horizonte)), a mola (bloqueia entradas esticadas) ou
as duas, sorteadas num espaço fixo antes de qualquer resultado.

Cada variação roda uma vez sobre todos os pregões. Como o NTSL é causal, as
métricas do treino não dependem dos pregões seguintes. A seleção usa só o treino.
O teste compara a escolhida com o original, pareado por pregão. Todo pregão
recebe todas as variações, e a tabela por pregão mostra a distribuição.
"""
from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.avaliar_fora_amostra import bootstrap_media, operacoes
from tools.gerar_win_sintetico import gerar, microestrutura

RAIZ = Path(__file__).resolve().parent.parent
REGRAS_MICRO = {"custo_por_contrato_lado": 0.5, "slippage_ticks": 1, "volume_financeiro_ntsl": True,
                "agressao_referencia_injetada": True, "historico_continuo": True, "vwap_continuo_lacunas": True}
ESPACO = {
    "p_FisTemp": [0, 1], "p_FatorAlvoT": [1.0, 1.5, 2.0, 3.0], "p_FatorStopT": [0.75, 1.0, 1.5, 2.0],
    "p_HorizonteT": [10, 20, 30], "p_JanelaT": [20, 30, 60],
    "p_FisMola": [0, 1], "p_XMax": [1.5, 2.0, 2.5, 3.0], "p_JanelaMola": [40, 60, 90],
}


def modelos():
    perfis = json.loads((RAIZ / "docs/colaboracao/evidencias/WINZ26_protocolo_rodada20_v1/protocolo.json")
                        .read_text(encoding="utf-8"))["perfis"]
    return {
        "v58_original": dict(fonte="estrategias/pesquisa/Modelo_Unificado_v5_8_fisica_v1_0.ntsl",
                             parametros=perfis["v58_original"]["parametros"], contratos=2),
        "scalper_v11_otimizada": dict(fonte="estrategias/pesquisa/modelo_scalper_v1_1_fisica_v1_0.ntsl",
                                      parametros=perfis["scalper_v11_otimizada"]["parametros"], contratos=2),
        "pullback_v1_0": dict(fonte="estrategias/pesquisa/pullback_tendencia_v1_1_fisica.ntsl",
                              parametros={}, contratos=1),
    }


def sortear(quantidade, semente):
    rng = np.random.default_rng(semente)
    vistas, saida = set(), [dict(p_FisTemp=0, p_FisMola=0)]
    while len(saida) < quantidade + 1:
        c = {k: v[rng.integers(len(v))] for k, v in ESPACO.items()}
        if c["p_FisTemp"] == 0 and c["p_FisMola"] == 0:
            continue
        # parâmetros de um bloco desligado não mudam nada: normaliza para não contar duplicatas
        if c["p_FisTemp"] == 0:
            c.update(p_FatorAlvoT=1.5, p_FatorStopT=1.0, p_HorizonteT=20, p_JanelaT=30)
        if c["p_FisMola"] == 0:
            c.update(p_XMax=2.0, p_JanelaMola=60)
        chave = tuple(c.values())
        if chave not in vistas:
            vistas.add(chave)
            saida.append({k: float(v) for k, v in c.items()})
    return saida


def rodar(modelo, frame, fisica):
    programa = compile_ntsl(source_text(RAIZ / modelo["fonte"]))
    parametros = {**{k.lower(): v for k, v in modelo["parametros"].items()},
                  **{k.lower(): v for k, v in fisica.items()}}
    motor = Engine(programa, frame, 5, parametros, 60, 0.2, regras=REGRAS_MICRO)
    motor.run(record_trace=False)
    ops = operacoes(motor)
    if abs(ops["liquido_reais"].sum() - sum(f["liquido_reais"] for f in motor.fills
                                            if f["pregao"] in set(ops["pregao"]))) > 0.01:
        raise AssertionError("Operações pareadas não somam o resultado dos fills.")
    return ops


def resumo(ops, pregoes, semente=11):
    ops = ops[ops["pregao"].isin(pregoes)]
    diario = ops.groupby("pregao")["liquido_reais"].sum().reindex(pregoes, fill_value=0.0)
    curva = np.r_[0, ops["liquido_reais"].cumsum().to_numpy()]
    ganhos, perdas = ops.loc[ops.liquido_reais > 0, "liquido_reais"].sum(), -ops.loc[ops.liquido_reais < 0, "liquido_reais"].sum()
    return dict(
        operacoes=int(len(ops)), operacoes_por_pregao=round(len(ops) / len(pregoes), 2),
        acerto=round(float((ops["liquido_reais"] > 0).mean()), 4) if len(ops) else None,
        liquido_reais=round(float(ops["liquido_reais"].sum()), 2),
        fator_lucro=round(float(ganhos / perdas), 3) if perdas > 0 else None,
        drawdown_reais=round(float((np.maximum.accumulate(curva) - curva).max()), 2),
        media_diaria_reais=round(float(diario.mean()), 2),
        media_diaria_ic95=bootstrap_media(diario.to_numpy(), 2000, semente),
        pregoes_positivos=int((diario > 0).sum()),
        saidas=ops["tipo_saida"].value_counts().to_dict(),
    ), diario


def avaliar_modelo(nome, modelo, frame, treino, teste, quantidade, semente, saida):
    variacoes = sortear(quantidade, semente)
    linhas, diarios = [], {}
    for i, fisica in enumerate(variacoes, start=1):
        ops = rodar(modelo, frame, fisica)
        tr, d_tr = resumo(ops, treino)
        te, d_te = resumo(ops, teste)
        diarios[i] = pd.concat([d_tr, d_te])
        linhas.append(dict(variacao=i, **fisica, operacoes_treino=tr["operacoes"], liquido_treino=tr["liquido_reais"],
                           drawdown_treino=tr["drawdown_reais"], operacoes_teste=te["operacoes"],
                           liquido_teste=te["liquido_reais"]))
    tabela = pd.DataFrame(linhas)
    original = tabela.iloc[0]
    minimo = 0.5 * original["operacoes_treino"]
    elegiveis = tabela[tabela["operacoes_treino"] >= minimo]
    escolhida = elegiveis.sort_values(["liquido_treino", "drawdown_treino"], ascending=[False, True]).iloc[0]
    k = int(escolhida["variacao"])

    ops_o, ops_e = rodar(modelo, frame, variacoes[0]), rodar(modelo, frame, variacoes[k - 1])
    metricas = {}
    for rotulo, pregoes in (("treino", treino), ("teste", teste)):
        mo, do = resumo(ops_o, pregoes)
        me, de = resumo(ops_e, pregoes)
        diff = (de - do).to_numpy()
        metricas[rotulo] = dict(original=mo, escolhida=me, diferenca_diaria_media=round(float(diff.mean()), 2),
                                diferenca_diaria_ic95=bootstrap_media(diff, 2000, 13),
                                pregoes_escolhida_melhor=int((diff > 0).sum()), pregoes_iguais=int((diff == 0).sum()))

    matriz = pd.DataFrame(diarios)  # pregões x variações
    por_pregao = pd.DataFrame({
        "pregao": matriz.index, "recorte": ["treino" if p in treino else "teste" for p in matriz.index],
        "replays": matriz.shape[1], "original": matriz[1].values, "escolhida": matriz[k].values,
        "media_variacoes": matriz.mean(axis=1).round(2).values, "mediana_variacoes": matriz.median(axis=1).values,
        "minimo_variacoes": matriz.min(axis=1).values, "maximo_variacoes": matriz.max(axis=1).values,
        "variacoes_acima_do_original": (matriz.gt(matriz[1], axis=0)).sum(axis=1).values,
    })
    destino = Path(saida) / nome
    destino.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino / "variacoes.csv", sep=";", index=False)
    por_pregao.to_csv(destino / "por_pregao.csv", sep=";", index=False)
    resultado = dict(
        modelo=nome, fonte=modelo["fonte"], contratos=modelo["contratos"], parametros_base=modelo["parametros"],
        variacoes=len(variacoes), replays_por_pregao=int(matriz.shape[1]),
        minimo_operacoes_treino=float(minimo), variacao_escolhida=k, fisica_escolhida=variacoes[k - 1],
        **metricas,
        diagnostico=dict(
            spearman_treino_teste=round(float(tabela["liquido_treino"].rank().corr(tabela["liquido_teste"].rank())), 4),
            posicao_escolhida_no_teste=int((tabela["liquido_teste"] > tabela.loc[k - 1, "liquido_teste"]).sum()) + 1,
            variacoes_acima_do_original_treino=int((tabela["liquido_treino"] > original["liquido_treino"]).sum()),
            variacoes_acima_do_original_teste=int((tabela["liquido_teste"] > original["liquido_teste"]).sum()),
            por_bloco_teste=tabela.assign(bloco=np.select(
                [(tabela.p_FisTemp == 1) & (tabela.p_FisMola == 1), tabela.p_FisTemp == 1, tabela.p_FisMola == 1],
                ["temperatura+mola", "temperatura", "mola"], "original"))
            .groupby("bloco")[["liquido_treino", "liquido_teste"]].mean().round(2).to_dict(orient="index"),
        ),
    )
    (destino / "resultado.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False, default=float),
                                            encoding="utf-8")
    return resultado


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--saida", required=True)
    p.add_argument("--versao-gerador", type=int, default=2)
    p.add_argument("--modelo", action="append", help="limita aos modelos indicados")
    p.add_argument("--variacoes", type=int, default=30)
    p.add_argument("--semente", type=int, default=7)
    p.add_argument("--pregoes", type=int, default=60)
    p.add_argument("--treino", type=int, default=42)
    a = p.parse_args()
    caminho = Path(a.saida) / f"win_sintetico_v{a.versao_gerador}_micro.csv"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if not caminho.exists():
        microestrutura(gerar(a.pregoes, 20261124, versao=a.versao_gerador)).to_csv(caminho, sep=";", index=False)
    frame = load_bars(caminho, 60, "ohlc")
    pregoes = sorted(frame["pregao"].unique())
    treino, teste = pregoes[:a.treino], pregoes[a.treino:]
    for nome, modelo in modelos().items():
        if a.modelo and nome not in a.modelo:
            continue
        r = avaliar_modelo(nome, modelo, frame, treino, teste, a.variacoes, a.semente, a.saida)
        t = r["teste"]
        print(f"{nome}: escolhida {r['variacao_escolhida']} {r['fisica_escolhida']} | teste original "
              f"R$ {t['original']['liquido_reais']} x escolhida R$ {t['escolhida']['liquido_reais']} | "
              f"diferença diária {t['diferenca_diaria_media']} IC {t['diferenca_diaria_ic95']}", flush=True)


if __name__ == "__main__":
    main()
