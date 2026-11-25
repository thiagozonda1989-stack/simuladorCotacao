"""Teste pareado do filtro de deriva do dia (Física v1.1) na v5.8 com dados reais do WINZ26.

Roda no computador local, sobre a base privada congelada (o SHA-256 é conferido),
com as regras e o perfil da v5.8 original congelados na rodada 20. Grava só agregados.

Decisão pré-registrada: a variante primária é `deriva_z1` (p_FisDeriva=1, p_ZDia=1),
comparada com o original nos 20 pregões conhecidos. As demais variantes são
sensibilidade e não podem trocar a decisão. Cada pregão recebe todas as variantes
(12 replays por pregão).

Os 20 conhecidos já foram vistos nas rodadas 18 a 20, então isto é um diagnóstico
pareado em dados reais, não a validação formal. A reserva inédita continua fechada.
"""
from argparse import ArgumentParser
import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd

from estrategia import load_bars
from tools.avaliar_fora_amostra import bootstrap_media
from tools.testar_fisica_modelos import resumo, rodar

RAIZ = Path(__file__).resolve().parent.parent
FONTE = "estrategias/pesquisa/Modelo_Unificado_v5_8_fisica_v1_1.ntsl"
PROTOCOLO = RAIZ / "docs/colaboracao/evidencias/WINZ26_protocolo_rodada20_v1/protocolo.json"
RODADA18 = RAIZ / "docs/colaboracao/evidencias/WINZ26_ag_rodada18_v1/resultados/Modelo_Unificado_v5_8.json"
PRIMARIA = "deriva_z1"
VARIANTES = {
    "original": {},
    "deriva_z0_5": dict(p_FisDeriva=1, p_ZDia=0.5),
    "deriva_z0_75": dict(p_FisDeriva=1, p_ZDia=0.75),
    "deriva_z1": dict(p_FisDeriva=1, p_ZDia=1.0),
    "deriva_z1_25": dict(p_FisDeriva=1, p_ZDia=1.25),
    "deriva_z1_5": dict(p_FisDeriva=1, p_ZDia=1.5),
    "deriva_z2": dict(p_FisDeriva=1, p_ZDia=2.0),
    "mola_v10": dict(p_FisMola=1, p_XMax=2.0, p_JanelaMola=60),
    "mola_ajustada": dict(p_FisMola=1, p_XMax=2.0, p_JanelaMola=60, p_FisMolaDeriva=1, p_ZDia=1.0),
    "mola_ajustada_deriva_z1": dict(p_FisMola=1, p_XMax=2.0, p_JanelaMola=60, p_FisMolaDeriva=1, p_FisDeriva=1, p_ZDia=1.0),
    "temperatura": dict(p_FisTemp=1, p_FatorAlvoT=1.5, p_FatorStopT=1.0, p_HorizonteT=20, p_JanelaT=30),
    "deriva_z1_temperatura": dict(p_FisDeriva=1, p_ZDia=1.0, p_FisTemp=1, p_FatorAlvoT=1.5, p_FatorStopT=1.0,
                                  p_HorizonteT=20, p_JanelaT=30),
}


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def recortes():
    conhecidos = json.loads(PROTOCOLO.read_text(encoding="utf-8"))["pregoes_conhecidos"]
    r18 = json.loads(RODADA18.read_text(encoding="utf-8"))
    desenvolvimento = sorted(r18["desenvolvimento"]["original"]["metricas"]["por_pregao"])
    return {"conhecidos": conhecidos, "desenvolvimento": desenvolvimento}


def testar(caminho, pregoes_por_recorte, regras=None, perfil=None):
    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    modelo = dict(fonte=FONTE, contratos=protocolo["lote"],
                  parametros=perfil or protocolo["perfis"]["v58_original"]["parametros"])
    quadro = load_bars(caminho, protocolo["segundos"], "ohlc")
    todos = sorted(set().union(*pregoes_por_recorte.values()))
    quadro = quadro.loc[quadro["pregao"].isin(todos)].reset_index(drop=True)
    faltando = sorted(set(todos) - set(quadro["pregao"]))
    import tools.testar_fisica_modelos as tfm
    regras_antigas = tfm.REGRAS_MICRO
    tfm.REGRAS_MICRO = regras or protocolo["regras_execucao"]
    try:
        operacoes = {nome: rodar(modelo, quadro, fisica) for nome, fisica in VARIANTES.items()}
    finally:
        tfm.REGRAS_MICRO = regras_antigas
    saida = dict(pregoes_ausentes=faltando, replays_por_pregao=len(VARIANTES), variante_primaria=PRIMARIA, recortes={})
    tabelas = {}
    for recorte, pregoes in pregoes_por_recorte.items():
        pregoes = [p for p in pregoes if p not in faltando]
        diarios, metricas = {}, {}
        for nome, ops in operacoes.items():
            metricas[nome], diarios[nome] = resumo(ops, pregoes)
        comparacao = {}
        for nome in VARIANTES:
            if nome == "original":
                continue
            diff = (diarios[nome] - diarios["original"]).to_numpy()
            comparacao[nome] = dict(**{k: metricas[nome][k] for k in ("operacoes", "acerto", "liquido_reais",
                                                                       "fator_lucro", "drawdown_reais")},
                                    diferenca_diaria_media=round(float(diff.mean()), 2),
                                    diferenca_diaria_ic95=bootstrap_media(diff, 2000, 13),
                                    pregoes_melhor=int((diff > 0).sum()), pregoes_pior=int((diff < 0).sum()))
        saida["recortes"][recorte] = dict(
            pregoes=len(pregoes), original={k: metricas["original"][k] for k in
                                            ("operacoes", "acerto", "liquido_reais", "fator_lucro", "drawdown_reais")},
            variantes=comparacao)
        matriz = pd.DataFrame(diarios)
        matriz.insert(0, "replays", len(VARIANTES))
        tabelas[recorte] = matriz.rename_axis("pregao").reset_index()
    return saida, tabelas


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, help="base privada congelada da rodada 18/19")
    p.add_argument("--saida", required=True, help="pasta para o JSON e as tabelas agregadas")
    p.add_argument("--sem-conferir-sha", action="store_true", help="só para testes sintéticos")
    a = p.parse_args()
    protocolo = json.loads(PROTOCOLO.read_text(encoding="utf-8"))
    digest = sha256(a.base)
    if not a.sem_conferir_sha and digest != protocolo["base_conhecida_sha256"]:
        raise SystemExit("A base não é a congelada da rodada 19 (SHA-256 diferente).")
    resultado, tabelas = testar(a.base, recortes())
    resultado.update(base_sha256=digest, fonte=FONTE, fonte_sha256=sha256(RAIZ / FONTE),
                     sha_codigo=subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                               cwd=RAIZ).stdout.strip())
    destino = Path(a.saida)
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "resultado_deriva_real.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False),
                                                        encoding="utf-8")
    for recorte, tabela in tabelas.items():
        tabela.to_csv(destino / f"por_pregao_{recorte}.csv", sep=";", index=False)
    for recorte, r in resultado["recortes"].items():
        v = r["variantes"][PRIMARIA]
        print(f"{recorte}: original R$ {r['original']['liquido_reais']} | {PRIMARIA} R$ {v['liquido_reais']} | "
              f"diferença diária {v['diferenca_diaria_media']} IC {v['diferenca_diaria_ic95']}")


if __name__ == "__main__":
    main()
