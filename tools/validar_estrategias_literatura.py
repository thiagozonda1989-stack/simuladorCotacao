"""Teste e validação das 20 estratégias da literatura no WINZ26 real.

Protocolo (docs/colaboracao/evidencias/estrategias_literatura_v1/protocolo.json, registrado antes da execução):
- Base real congelada da rodada 18 (SHA-256 conferido). A reserva inédita não é usada.
- 12 variações por estratégia: a 1ª com os parâmetros da literatura e 11 sorteadas na grade (semente 7).
  Cada pregão recebe as 12 (12 replays por pregão por estratégia).
- Seleção só no desenvolvimento (19 pregões da rodada 18): maior líquido com pelo menos 1 operação por pregão.
- Validação nos 20 pregões conhecidos, uma única avaliação da escolhida.
- Controle nulo: escolhida no gerador sintético v0 (sem estrutura), 60 pregões.
- Correção de Holm para as 20 estratégias sobre o p-valor unilateral (bootstrap por pregão) da média diária.
"""
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.avaliar_fora_amostra import operacoes
from tools.gerar_estrategias_literatura import ESTRATEGIAS, GRADE_RISCO
from tools.gerar_win_sintetico import gerar, microestrutura
from tools.testar_deriva_real import recortes, sha256

RAIZ = Path(__file__).resolve().parent.parent
PROTOCOLO = RAIZ / "docs/colaboracao/evidencias/estrategias_literatura_v1/protocolo.json"


def variacoes(nome, quantidade, semente):
    grade = {**ESTRATEGIAS[nome]["grade"], **GRADE_RISCO}
    rng = np.random.default_rng(semente)
    saida, vistas = [{}], {()}
    tentativas = 0
    while len(saida) < quantidade and tentativas < 10_000:
        tentativas += 1
        c = {k: v[rng.integers(len(v))] for k, v in grade.items()}
        chave = tuple(sorted(c.items()))
        if chave not in vistas:
            vistas.add(chave)
            saida.append({k: float(v) for k, v in c.items()})
    return saida


def rodar(nome, quadro, parametros, regras):
    programa = compile_ntsl(source_text(RAIZ / "estrategias" / "literatura" / f"{nome}.ntsl"))
    motor = Engine(programa, quadro, 5, {k.lower(): v for k, v in parametros.items()}, 60, 0.2, regras=regras)
    motor.run(record_trace=False)
    return operacoes(motor)


def bootstrap(diario, reamostragens=10_000, semente=11):
    rng = np.random.default_rng(semente)
    x = np.asarray(diario, dtype=float)
    medias = rng.choice(x, (reamostragens, len(x))).mean(axis=1)
    return [round(float(np.percentile(medias, 2.5)), 2), round(float(np.percentile(medias, 97.5)), 2)], \
        float((medias <= 0).mean())


def metricas(ops, pregoes):
    ops = ops[ops["pregao"].isin(pregoes)]
    diario = ops.groupby("pregao")["liquido_reais"].sum().reindex(pregoes, fill_value=0.0)
    curva = np.r_[0, ops["liquido_reais"].cumsum().to_numpy()]
    ganhos = ops.loc[ops.liquido_reais > 0, "liquido_reais"].sum()
    perdas = -ops.loc[ops.liquido_reais < 0, "liquido_reais"].sum()
    ic, p = bootstrap(diario.to_numpy())
    return dict(operacoes=int(len(ops)), operacoes_por_pregao=round(len(ops) / len(pregoes), 2),
                acerto=round(float((ops.liquido_reais > 0).mean()), 4) if len(ops) else None,
                liquido_reais=round(float(ops.liquido_reais.sum()), 2),
                fator_lucro=round(float(ganhos / perdas), 3) if perdas > 0 else None,
                drawdown_reais=round(float((np.maximum.accumulate(curva) - curva).max()), 2),
                media_diaria=round(float(diario.mean()), 2), media_diaria_ic95=ic, p_unilateral=round(p, 5),
                pregoes_positivos=int((diario > 0).sum())), diario


def holm(pvalores):
    ordem = sorted(pvalores, key=pvalores.get)
    ajustado, acumulado, m = {}, 0.0, len(ordem)
    for i, nome in enumerate(ordem):
        acumulado = max(acumulado, min(1.0, (m - i) * pvalores[nome]))
        ajustado[nome] = round(acumulado, 5)
    return ajustado


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--estrategia", action="append")
    a = p.parse_args()
    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    if sha256(a.base) != protocolo["base_sha256"]:
        raise SystemExit("A base não é a congelada da rodada 18 (SHA-256 diferente).")
    regras = protocolo["regras_execucao"]
    rec = recortes()
    dev, conhecidos = rec["desenvolvimento"], rec["conhecidos"]
    quadro = load_bars(a.base, 60, "ohlc")
    quadro = quadro.loc[quadro["pregao"].isin(dev + conhecidos)].reset_index(drop=True)
    destino = Path(a.saida)
    destino.mkdir(parents=True, exist_ok=True)
    nulo_csv = destino / "nulo_v0_micro.csv"
    if not nulo_csv.exists():
        n = protocolo["controle_nulo"]
        microestrutura(gerar(n["pregoes"], n["semente"], versao=0), n["semente_micro"]).to_csv(nulo_csv, sep=";", index=False)
    nulo = load_bars(nulo_csv, 60, "ohlc")
    pregoes_nulo = sorted(nulo["pregao"].unique())

    resultados = {}
    nomes = a.estrategia or list(ESTRATEGIAS)
    for nome in nomes:
        vs = variacoes(nome, protocolo["variacoes_por_estrategia"], protocolo["semente_variacoes"])
        linhas, diarios = [], {}
        for i, parametros in enumerate(vs, start=1):
            ops = rodar(nome, quadro, parametros, regras)
            md, dd = metricas(ops, dev)
            mc, dc = metricas(ops, conhecidos)
            diarios[i] = pd.concat([dd, dc])
            linhas.append(dict(variacao=i, **parametros, operacoes_dev=md["operacoes"], liquido_dev=md["liquido_reais"],
                               operacoes_conhecidos=mc["operacoes"], liquido_conhecidos=mc["liquido_reais"],
                               _md=md, _mc=mc))
        tabela = pd.DataFrame(linhas)
        elegiveis = tabela[tabela.operacoes_dev >= protocolo["selecao"]["minimo_operacoes_dev"]]
        k = int(elegiveis.sort_values("liquido_dev", ascending=False).iloc[0]["variacao"]) if len(elegiveis) else 1
        escolhida = tabela.loc[k - 1]
        mnulo, _ = metricas(rodar(nome, nulo, vs[k - 1], regras), pregoes_nulo)
        resultados[nome] = dict(
            titulo=ESTRATEGIAS[nome]["titulo"], familia=ESTRATEGIAS[nome]["familia"],
            referencia=ESTRATEGIAS[nome]["referencia"],
            fonte_sha256=sha256(RAIZ / "estrategias" / "literatura" / f"{nome}.ntsl"),
            variacao_escolhida=k, parametros_escolhidos=vs[k - 1] or "padrão da literatura",
            literatura=dict(desenvolvimento=tabela.loc[0, "_md"], conhecidos=tabela.loc[0, "_mc"]),
            escolhida=dict(desenvolvimento=escolhida["_md"], conhecidos=escolhida["_mc"], nulo=mnulo),
            spearman_dev_conhecidos=round(float(tabela.liquido_dev.rank().corr(tabela.liquido_conhecidos.rank())), 4),
            variacoes_positivas_conhecidos=int((tabela.liquido_conhecidos > 0).sum()),
        )
        tabela.drop(columns=["_md", "_mc"]).to_csv(destino / f"variacoes_{nome}.csv", sep=";", index=False)
        matriz = pd.DataFrame(diarios)
        matriz.columns = [f"v{c:02d}" for c in matriz.columns]
        matriz.insert(0, "recorte", ["desenvolvimento" if d in dev else "conhecidos" for d in matriz.index])
        matriz.insert(1, "replays", len(vs))
        matriz.rename_axis("pregao").reset_index().to_csv(destino / f"por_pregao_{nome}.csv", sep=";", index=False)
        c = resultados[nome]["escolhida"]["conhecidos"]
        print(f"{nome:30s} v{k:02d} dev R$ {escolhida['_md']['liquido_reais']:8.0f} | conhecidos R$ {c['liquido_reais']:8.0f} "
              f"FL {c['fator_lucro']} IC {c['media_diaria_ic95']} p {c['p_unilateral']} | nulo R$ "
              f"{resultados[nome]['escolhida']['nulo']['liquido_reais']:.0f}", flush=True)

    ajustados = holm({n: r["escolhida"]["conhecidos"]["p_unilateral"] for n, r in resultados.items()})
    cr = protocolo["criterios"]
    for nome, r in resultados.items():
        c, nu = r["escolhida"]["conhecidos"], r["escolhida"]["nulo"]
        r["p_holm"] = ajustados[nome]
        basicos = (c["liquido_reais"] > 0 and (c["fator_lucro"] or 0) >= cr["fator_lucro_minimo"]
                   and c["operacoes_por_pregao"] >= cr["operacoes_por_pregao_minimo"]
                   and r["escolhida"]["desenvolvimento"]["liquido_reais"] > 0)
        nulo_ok = nu["media_diaria_ic95"][0] <= 0
        if basicos and nulo_ok and ajustados[nome] < cr["alfa"]:
            r["status"] = "aprovada para a reserva"
        elif basicos and nulo_ok:
            r["status"] = "promissora (não significativa após Holm)"
        else:
            r["status"] = "rejeitada"
        r["criterios"] = dict(basicos=basicos, nulo_sem_lucro=nulo_ok, holm=ajustados[nome] < cr["alfa"])
    (destino / "resultado.json").write_text(json.dumps(dict(
        protocolo_sha256=sha256(PROTOCOLO), base_sha256=protocolo["base_sha256"], estrategias=resultados),
        indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    ranking = pd.DataFrame([dict(estrategia=n, titulo=r["titulo"], familia=r["familia"], status=r["status"],
                                 variacao=r["variacao_escolhida"],
                                 dev_liquido=r["escolhida"]["desenvolvimento"]["liquido_reais"],
                                 conhecidos_liquido=r["escolhida"]["conhecidos"]["liquido_reais"],
                                 conhecidos_operacoes=r["escolhida"]["conhecidos"]["operacoes"],
                                 conhecidos_acerto=r["escolhida"]["conhecidos"]["acerto"],
                                 conhecidos_fator=r["escolhida"]["conhecidos"]["fator_lucro"],
                                 conhecidos_drawdown=r["escolhida"]["conhecidos"]["drawdown_reais"],
                                 conhecidos_ic95=r["escolhida"]["conhecidos"]["media_diaria_ic95"],
                                 p_unilateral=r["escolhida"]["conhecidos"]["p_unilateral"], p_holm=r["p_holm"],
                                 literatura_conhecidos=r["literatura"]["conhecidos"]["liquido_reais"],
                                 nulo_liquido=r["escolhida"]["nulo"]["liquido_reais"],
                                 nulo_ic95=r["escolhida"]["nulo"]["media_diaria_ic95"])
                            for n, r in resultados.items()]).sort_values("conhecidos_liquido", ascending=False)
    ranking.to_csv(destino / "ranking.csv", sep=";", index=False)
    print(ranking[["estrategia", "status", "conhecidos_liquido", "conhecidos_fator", "p_holm"]].to_string(index=False))


if __name__ == "__main__":
    main()
