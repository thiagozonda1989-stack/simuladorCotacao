"""Avaliação fora da amostra de uma estratégia NTSL com divisão cronológica congelada.

Fluxo, todo definido em protocolo.json antes da execução:
1. divide os pregões em treino (primeiros) e teste (últimos);
2. roda as variações de parâmetros somente nos pregões de treino;
3. escolhe uma variação pelo critério do protocolo;
4. roda a escolhida uma única vez e mede somente os pregões de teste;
5. depois da escolha, roda as demais no teste apenas como diagnóstico de viés de seleção.

Métricas: matriz de confusão por classe (C/V/N), precisão e sensibilidade com intervalo de
Wilson, falsos positivos e seu custo em reais, operações por pregão, exposição,
resultado líquido, drawdown, estabilidade entre pregões e bootstrap por pregão.
"""
import argparse
import json
import math
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl

CLASSES = ("C", "V", "N")


def carregar_protocolo(caminho):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def dividir_pregoes(pregoes, n_treino, n_teste):
    ordenados = sorted(set(pregoes))
    if len(ordenados) != n_treino + n_teste:
        raise ValueError(f"O protocolo pede {n_treino + n_teste} pregões e os dados têm {len(ordenados)}.")
    treino, teste = ordenados[:n_treino], ordenados[n_treino:]
    if max(treino) >= min(teste):
        raise ValueError("O treino precisa terminar antes do teste.")
    return treino, teste


def sortear_variacoes(espaco, quantidade, semente, padrao):
    rng = np.random.default_rng(semente)
    nomes = list(espaco)
    vistos, variacoes = set(), []
    primeira = {nome: padrao[nome.lower()] for nome in nomes}
    for candidata in [primeira] + [None] * 10_000:
        if candidata is None:
            candidata = {nome: espaco[nome][rng.integers(len(espaco[nome]))] for nome in nomes}
        if candidata["p_Rapida"] >= candidata["p_Lenta"]:
            continue
        chave = tuple(float(candidata[n]) for n in nomes)
        if chave in vistos:
            continue
        vistos.add(chave)
        variacoes.append({n: float(candidata[n]) for n in nomes})
        if len(variacoes) == quantidade:
            return variacoes
    raise ValueError("O espaço de parâmetros não comporta a quantidade pedida.")


def rotular(frame, pontos, horizonte):
    """Classe de cada barra de decisão t, medida a partir da abertura de t+1."""
    abertura = frame["abertura"].to_numpy(float)
    maxima = frame["maxima"].to_numpy(float)
    minima = frame["minima"].to_numpy(float)
    pregao = frame["pregao"].to_numpy()
    n = len(frame)
    classes = np.full(n, "I", dtype="<U1")
    for t in range(n - 1):
        fim = t + horizonte
        if fim >= n or pregao[fim] != pregao[t] or pregao[t + 1] != pregao[t]:
            continue
        referencia = abertura[t + 1]
        alto, baixo = referencia + pontos, referencia - pontos
        classe = "N"
        for k in range(t + 1, fim + 1):
            sobe, desce = maxima[k] >= alto, minima[k] <= baixo
            if sobe and desce:
                classe = "A"
                break
            if sobe:
                classe = "C"
                break
            if desce:
                classe = "V"
                break
        classes[t] = classe
    return classes


def regras_execucao(protocolo):
    e = protocolo["execucao"]
    return {"custo_por_contrato_lado": float(e["custo_por_contrato_lado_reais"]),
            "slippage_ticks": float(e["slippage_ticks"])}


def executar(programa, frame, parametros, protocolo):
    d = protocolo["dados"]
    sobrescritas = {k.lower(): v for k, v in parametros.items()}
    motor = Engine(programa, frame, d["tick"], sobrescritas, d["intervalo_segundos"], d["valor_ponto_reais"],
                   regras=regras_execucao(protocolo))
    motor.run()
    return motor


def operacoes(motor):
    """Pareia entradas e saídas de 1 contrato; a barra de sinal é a anterior à execução da entrada."""
    resultado, aberta = [], None
    for f in motor.fills:
        linha = f["barra"] - 1
        if f["acao"] in ("long", "short"):
            aberta = dict(barra_sinal=linha - 1, barra_entrada=linha, pregao=f["pregao"],
                          lado="C" if f["acao"] == "long" else "V", liquido_reais=f["liquido_reais"])
        elif f["acao"].startswith("exit") and aberta is not None:
            aberta.update(barra_saida=linha, pontos=f["pontos_contrato"], tipo_saida=f["ordem"],
                          liquido_reais=aberta["liquido_reais"] + f["liquido_reais"])
            resultado.append(aberta)
            aberta = None
    return pd.DataFrame(resultado, columns=["barra_sinal", "barra_entrada", "barra_saida", "pregao", "lado",
                                            "pontos", "tipo_saida", "liquido_reais"])


def wilson(acertos, total, z=1.96):
    if total == 0:
        return (None, None)
    p = acertos / total
    centro = (p + z * z / (2 * total)) / (1 + z * z / total)
    margem = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return (round(centro - margem, 4), round(centro + margem, 4))


def bootstrap_media(valores, reamostragens, semente):
    if len(valores) == 0:
        return (None, None)
    rng = np.random.default_rng(semente)
    v = np.asarray(valores, float)
    medias = v[rng.integers(0, len(v), size=(reamostragens, len(v)))].mean(axis=1)
    return (round(float(np.quantile(medias, 0.025)), 2), round(float(np.quantile(medias, 0.975)), 2))


def medir(frame, motor, pregoes, rotulos, protocolo):
    escopo = frame["pregao"].isin(pregoes).to_numpy()
    trace = pd.DataFrame(motor.trace)
    previsto = np.where(trace["sinal_compra"], "C", np.where(trace["sinal_venda"], "V", "N"))
    ops = operacoes(motor)
    ops = ops[ops["pregao"].isin(pregoes)].reset_index(drop=True)

    valido = escopo & np.isin(rotulos, CLASSES)
    matriz = pd.crosstab(pd.Series(rotulos[valido], name="real"), pd.Series(previsto[valido], name="previsto"))
    matriz = matriz.reindex(index=list(CLASSES), columns=list(CLASSES), fill_value=0)

    custo_falso = {}
    for classe in ("C", "V"):
        falsos = set(np.flatnonzero(valido & (previsto == classe) & (rotulos != classe)))
        custo_falso[classe] = round(float(ops.loc[ops["barra_sinal"].isin(falsos), "liquido_reais"].sum()), 2)

    por_classe = {}
    for classe in CLASSES:
        vp = int(matriz.loc[classe, classe])
        previstos, reais = int(matriz[classe].sum()), int(matriz.loc[classe].sum())
        por_classe[classe] = dict(
            verdadeiros_positivos=vp, previstos=previstos, reais=reais,
            taxa_base=round(reais / int(valido.sum()), 4) if valido.any() else None,
            precisao=round(vp / previstos, 4) if previstos else None, precisao_ic95=wilson(vp, previstos),
            sensibilidade=round(vp / reais, 4) if reais else None, sensibilidade_ic95=wilson(vp, reais))
    for classe in ("C", "V"):
        por_classe[classe]["falsos_positivos"] = por_classe[classe]["previstos"] - por_classe[classe]["verdadeiros_positivos"]
        por_classe[classe]["resultado_falsos_positivos_reais"] = custo_falso[classe]

    diario = ops.groupby("pregao")["liquido_reais"].sum().reindex(pregoes, fill_value=0.0)
    curva = np.r_[0, ops["liquido_reais"].cumsum().to_numpy()]
    posicao = trace["posicao"].to_numpy()[escopo]
    inc = protocolo["incerteza"]
    return dict(
        pregoes=len(pregoes), barras=int(escopo.sum()),
        rotulos_validos=int(valido.sum()),
        rotulos_ambiguos=int((escopo & (rotulos == "A")).sum()),
        rotulos_invalidos=int((escopo & (rotulos == "I")).sum()),
        matriz_confusao={r: {c: int(matriz.loc[r, c]) for c in CLASSES} for r in CLASSES},
        por_classe=por_classe,
        operacoes=len(ops), operacoes_por_pregao=round(len(ops) / len(pregoes), 2),
        operacoes_compra=int((ops["lado"] == "C").sum()), operacoes_venda=int((ops["lado"] == "V").sum()),
        operacoes_positivas=int((ops["liquido_reais"] > 0).sum()),
        taxa_acerto_operacoes=round(float((ops["liquido_reais"] > 0).mean()), 4) if len(ops) else None,
        exposicao_barras=round(float((posicao != 0).mean()), 4),
        resultado_liquido_reais=round(float(ops["liquido_reais"].sum()), 2),
        resultado_pontos=round(float(ops["pontos"].sum()), 1),
        drawdown_liquido_reais=round(float((np.maximum.accumulate(curva) - curva).max()), 2),
        pregoes_positivos=int((diario > 0).sum()), pregoes_negativos=int((diario < 0).sum()),
        media_diaria_reais=round(float(diario.mean()), 2), desvio_diario_reais=round(float(diario.std(ddof=1)), 2),
        media_diaria_ic95_bootstrap=bootstrap_media(diario.to_numpy(), inc["reamostragens"], inc["semente"]),
        saidas_por_tipo=ops["tipo_saida"].value_counts().to_dict(),
        barras_ambiguas_execucao=int(motor.ambiguities),
    )


def recorte(caminho_csv, pregoes, destino):
    dados = pd.read_csv(caminho_csv, sep=";")
    dados[dados["timestamp"].str[:10].isin(pregoes)].to_csv(destino, sep=";", index=False)
    return destino


def avaliar(protocolo, caminho_csv, saida, regimes=None):
    raiz = Path(__file__).resolve().parent.parent
    programa = compile_ntsl(source_text(raiz / protocolo["estrategia"]))
    d, div, var, sel = protocolo["dados"], protocolo["divisao_cronologica"], protocolo["variacoes"], protocolo["selecao"]
    completo = load_bars(caminho_csv, d["intervalo_segundos"], "ohlc")
    treino, teste = dividir_pregoes(completo["pregao"], div["treino_pregoes"], div["teste_pregoes"])
    with tempfile.TemporaryDirectory() as tmp:
        quadro_treino = load_bars(recorte(caminho_csv, treino, Path(tmp) / "treino.csv"), d["intervalo_segundos"], "ohlc")
    if set(quadro_treino["pregao"]) & set(teste):
        raise AssertionError("O quadro de treino contém pregão de teste.")
    r = protocolo["rotulos"]
    rot_treino = rotular(quadro_treino, r["pontos"], r["horizonte_barras"])
    variacoes = sortear_variacoes(var["espaco"], var["quantidade"], var["semente"], programa.inputs)

    linhas = []
    for i, parametros in enumerate(variacoes, start=1):
        m = medir(quadro_treino, executar(programa, quadro_treino, parametros, protocolo), treino, rot_treino, protocolo)
        linhas.append(dict(variacao=i, **parametros, operacoes=m["operacoes"],
                           resultado_liquido_reais=m["resultado_liquido_reais"],
                           drawdown_liquido_reais=m["drawdown_liquido_reais"],
                           precisao_C=m["por_classe"]["C"]["precisao"], precisao_V=m["por_classe"]["V"]["precisao"],
                           pregoes_positivos=m["pregoes_positivos"]))
    tabela = pd.DataFrame(linhas)
    elegiveis = tabela[tabela["operacoes"] >= sel["minimo_operacoes_treino"]]
    if elegiveis.empty:
        raise ValueError("Nenhuma variação atingiu o mínimo de operações no treino.")
    escolhida = elegiveis.sort_values(["resultado_liquido_reais", "drawdown_liquido_reais"],
                                      ascending=[False, True]).iloc[0]
    parametros_escolhidos = variacoes[int(escolhida["variacao"]) - 1]

    # Avaliação única no teste: o histórico do treino aquece os indicadores; só o teste é medido.
    rot_completo = rotular(completo, r["pontos"], r["horizonte_barras"])
    motor = executar(programa, completo, parametros_escolhidos, protocolo)
    teste_metricas = medir(completo, motor, teste, rot_completo, protocolo)
    treino_metricas = medir(quadro_treino, executar(programa, quadro_treino, parametros_escolhidos, protocolo),
                            treino, rot_treino, protocolo)

    diagnostico = []
    for i, parametros in enumerate(variacoes, start=1):
        m = medir(completo, executar(programa, completo, parametros, protocolo), teste, rot_completo, protocolo)
        diagnostico.append(dict(variacao=i, operacoes_teste=m["operacoes"],
                                resultado_liquido_teste_reais=m["resultado_liquido_reais"]))
    diag = tabela[["variacao", "resultado_liquido_reais"]].merge(pd.DataFrame(diagnostico), on="variacao")
    posicao_teste = int((diag["resultado_liquido_teste_reais"] > teste_metricas["resultado_liquido_reais"]).sum()) + 1

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(saida / "variacoes_treino.csv", sep=";", index=False)
    diag.rename(columns={"resultado_liquido_reais": "resultado_liquido_treino_reais"}).to_csv(
        saida / "diagnostico_selecao_teste.csv", sep=";", index=False)
    resumo = dict(
        protocolo_versao=protocolo["versao"], pregoes_treino=[treino[0], treino[-1]], pregoes_teste=[teste[0], teste[-1]],
        variacao_escolhida=int(escolhida["variacao"]), parametros_escolhidos=parametros_escolhidos,
        treino=treino_metricas, teste=teste_metricas,
        diagnostico_selecao=dict(
            correlacao_spearman_treino_teste=round(float(diag["resultado_liquido_reais"].rank().corr(
                diag["resultado_liquido_teste_reais"].rank())), 4),
            posicao_da_escolhida_no_teste=posicao_teste, total_variacoes=len(diag),
            variacoes_positivas_no_treino=int((diag["resultado_liquido_reais"] > 0).sum()),
            variacoes_positivas_no_teste=int((diag["resultado_liquido_teste_reais"] > 0).sum())),
    )
    if regimes is not None:
        ops_teste = operacoes(motor)
        ops_teste = ops_teste[ops_teste["pregao"].isin(teste)]
        por_regime = {}
        for regime, grupo in regimes[regimes["pregao"].isin(teste)].groupby("regime"):
            ops_regime = ops_teste[ops_teste["pregao"].isin(grupo["pregao"])]
            por_regime[regime] = dict(pregoes=len(grupo), operacoes=len(ops_regime),
                                      resultado_liquido_reais=round(float(ops_regime["liquido_reais"].sum()), 2))
        resumo["teste_por_regime_do_gerador"] = por_regime
        resumo["pregoes_tendencia"] = dict(
            treino=int((regimes[regimes["pregao"].isin(treino)]["regime"] == "tendencia").sum()),
            teste=int((regimes[regimes["pregao"].isin(teste)]["regime"] == "tendencia").sum()))
    (saida / "resultado.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return resumo


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocolo", required=True)
    p.add_argument("--csv", help="CSV OHLC; se omitido, gera os dados sintéticos do protocolo")
    p.add_argument("--saida", required=True)
    a = p.parse_args()
    protocolo = carregar_protocolo(a.protocolo)
    caminho, regimes = a.csv, None
    if caminho is None:
        from tools.gerar_win_sintetico import gerar
        caminho = Path(a.saida) / "win_sintetico.csv"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        d = protocolo["dados"]
        frame, regimes = gerar(d["pregoes"], d["semente"], versao=d.get("versao_gerador", 1), com_regimes=True)
        frame.to_csv(caminho, sep=";", index=False)
    resumo = avaliar(protocolo, caminho, a.saida, regimes)
    t = resumo["teste"]
    print(f"Escolhida: variação {resumo['variacao_escolhida']} | teste: {t['operacoes']} operações, "
          f"R$ {t['resultado_liquido_reais']} líquido, precisão C {t['por_classe']['C']['precisao']}, "
          f"V {t['por_classe']['V']['precisao']}")


if __name__ == "__main__":
    main()
