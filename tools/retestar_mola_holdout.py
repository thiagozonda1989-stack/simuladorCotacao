"""Reteste da mola ajustada (Física v1.1) numa amostra sintética inédita.

Os 60 pregões da rodada 2 (semente 20261124) viraram desenvolvimento: o ajuste da
mola foi desenhado olhando para eles, inclusive para o antigo teste. Por isso o
reteste usa 60 pregões novos (semente 20261202), nunca vistos, e um controle nulo
com a mesma semente nova.

Variantes fixas, registradas antes de rodar a amostra nova:
- original: tudo desligado.
- mola_v10: mola da v1.0 (|x| > 2 bloqueia a entrada esticada).
- mola_ajustada: a mola só bloqueia se a deriva do dia a favor for < 1 (z de difusão).
- deriva: bloqueia entradas com deriva do dia a favor fraca (0 < z <= 1).
- mola_ajustada_deriva: as duas.
Além delas, 30 variações sorteadas; a escolhida é a de maior líquido no desenvolvimento.
"""
from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estrategia import load_bars
from tools.avaliar_fora_amostra import bootstrap_media
from tools.gerar_win_sintetico import gerar, microestrutura
from tools.testar_fisica_modelos import modelos, resumo, rodar

FONTES_V11 = {
    "v58_original": "estrategias/pesquisa/Modelo_Unificado_v5_8_fisica_v1_1.ntsl",
    "scalper_v11_otimizada": "estrategias/pesquisa/modelo_scalper_v1_1_fisica_v1_1.ntsl",
    "pullback_v1_0": "estrategias/pesquisa/pullback_tendencia_v1_2_fisica.ntsl",
}
FIXAS = {
    "original": dict(p_FisTemp=0, p_FisMola=0),
    "mola_v10": dict(p_FisMola=1, p_XMax=2.0, p_JanelaMola=60),
    "mola_ajustada": dict(p_FisMola=1, p_XMax=2.0, p_JanelaMola=60, p_FisMolaDeriva=1, p_ZDia=1.0),
    "deriva": dict(p_FisDeriva=1, p_ZDia=1.0),
    "mola_ajustada_deriva": dict(p_FisMola=1, p_XMax=2.0, p_JanelaMola=60, p_FisMolaDeriva=1, p_FisDeriva=1, p_ZDia=1.0),
}
ESPACO = {
    "p_FisTemp": [0, 1], "p_FatorAlvoT": [1.0, 1.5, 2.0, 3.0], "p_FatorStopT": [0.75, 1.0, 1.5, 2.0],
    "p_HorizonteT": [10, 20, 30], "p_FisMola": [0, 1], "p_XMax": [1.5, 2.0, 2.5, 3.0],
    "p_FisMolaDeriva": [0, 1], "p_FisDeriva": [0, 1], "p_ZDia": [0.5, 1.0, 1.5, 2.0],
}
AMOSTRAS = {
    "desenvolvimento": dict(semente=20261124, versao=2, semente_micro=20261125),
    "inedita": dict(semente=20261202, versao=2, semente_micro=20261203),
    "inedita_nula": dict(semente=20261202, versao=0, semente_micro=20261203),
}


def sortear(quantidade, semente):
    rng = np.random.default_rng(semente)
    vistas = {tuple(sorted(v.items())) for v in FIXAS.values()}
    saida = {}
    while len(saida) < quantidade:
        c = {k: float(v[rng.integers(len(v))]) for k, v in ESPACO.items()}
        if not (c["p_FisTemp"] or c["p_FisMola"] or c["p_FisDeriva"]):
            continue
        chave = tuple(sorted(c.items()))
        if chave not in vistas:
            vistas.add(chave)
            saida[f"sorteada_{len(saida) + 1:02d}"] = c
    return saida


def carregar(nome, pasta):
    a = AMOSTRAS[nome]
    caminho = Path(pasta) / f"{nome}.csv"
    if not caminho.exists():
        microestrutura(gerar(60, a["semente"], versao=a["versao"]), a["semente_micro"]).to_csv(caminho, sep=";", index=False)
    return load_bars(caminho, 60, "ohlc")


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--saida", required=True)
    p.add_argument("--modelo", action="append")
    p.add_argument("--variacoes", type=int, default=30)
    a = p.parse_args()
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    quadros = {n: carregar(n, saida) for n in AMOSTRAS}
    variantes = {**FIXAS, **sortear(a.variacoes, 7)}
    for nome, modelo in modelos().items():
        if a.modelo and nome not in a.modelo:
            continue
        modelo = {**modelo, "fonte": FONTES_V11[nome]}
        linhas, diarios, metricas = [], {}, {}
        for amostra, quadro in quadros.items():
            pregoes = sorted(quadro["pregao"].unique())
            for rotulo, fisica in variantes.items():
                m, d = resumo(rodar(modelo, quadro, fisica), pregoes)
                metricas[(amostra, rotulo)] = (m, d)
                diarios[(amostra, rotulo)] = d
                linhas.append(dict(amostra=amostra, variante=rotulo, **fisica, operacoes=m["operacoes"],
                                   acerto=m["acerto"], liquido=m["liquido_reais"], drawdown=m["drawdown_reais"]))
        tabela = pd.DataFrame(linhas)
        dev = tabela[tabela.amostra == "desenvolvimento"].set_index("variante")
        sorteadas = dev[dev.index.str.startswith("sorteada")]
        sorteadas = sorteadas[sorteadas.operacoes >= 0.5 * dev.loc["original", "operacoes"]]
        escolhida = sorteadas.sort_values(["liquido", "drawdown"], ascending=[False, True]).index[0]

        comparacoes = {}
        for amostra in AMOSTRAS:
            base = diarios[(amostra, "original")]
            comparacoes[amostra] = {}
            for rotulo in list(FIXAS)[1:] + [escolhida]:
                diff = (diarios[(amostra, rotulo)] - base).to_numpy()
                m = metricas[(amostra, rotulo)][0]
                comparacoes[amostra][rotulo] = dict(
                    operacoes=m["operacoes"], acerto=m["acerto"], liquido=m["liquido_reais"], drawdown=m["drawdown_reais"],
                    diferenca_diaria_media=round(float(diff.mean()), 2),
                    diferenca_diaria_ic95=bootstrap_media(diff, 2000, 13), pregoes_melhor=int((diff > 0).sum()))
            comparacoes[amostra]["original"] = {k: metricas[(amostra, "original")][0][k]
                                                for k in ("operacoes", "acerto", "liquido_reais", "drawdown_reais")}
        destino = saida / nome
        destino.mkdir(exist_ok=True)
        tabela.to_csv(destino / "variantes.csv", sep=";", index=False)
        for amostra in AMOSTRAS:
            matriz = pd.DataFrame({r: diarios[(amostra, r)] for r in variantes})
            pd.DataFrame({"pregao": matriz.index, "replays": matriz.shape[1], "original": matriz["original"].values,
                          "mola_ajustada": matriz["mola_ajustada"].values, "escolhida": matriz[escolhida].values,
                          "media_variantes": matriz.mean(axis=1).round(2).values,
                          "variantes_acima_do_original": matriz.gt(matriz["original"], axis=0).sum(axis=1).values}
                         ).to_csv(destino / f"por_pregao_{amostra}.csv", sep=";", index=False)
        ined = tabela[tabela.amostra == "inedita"].set_index("variante")
        resultado = dict(
            modelo=nome, fonte=modelo["fonte"], variantes=len(variantes), replays_por_pregao=len(variantes),
            escolhida_no_desenvolvimento=escolhida, fisica_escolhida=variantes[escolhida], comparacoes=comparacoes,
            diagnostico_inedita=dict(
                spearman_desenvolvimento_inedita=round(float(dev["liquido"].rank().corr(ined["liquido"].rank())), 4),
                posicao_escolhida=int((ined["liquido"] > ined.loc[escolhida, "liquido"]).sum()) + 1,
                variantes_acima_do_original=int((ined["liquido"] > ined.loc["original", "liquido"]).sum())),
        )
        (destino / "resultado.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False, default=float),
                                                encoding="utf-8")
        c = comparacoes["inedita"]
        print(nome, "| inédita original", c["original"]["liquido_reais"], "|",
              {k: (v["liquido"], v["diferenca_diaria_ic95"]) for k, v in c.items() if k != "original"}, flush=True)


if __name__ == "__main__":
    main()
