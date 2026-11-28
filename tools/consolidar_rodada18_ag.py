"""Consolida somente os agregados versionáveis da rodada 18."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
                    encoding="utf-8", newline="\n")


def utc_interval(start, end):
    return round(max(0, end.stat().st_mtime-start.stat().st_ctime), 3)


def historical_control(private, research, version, group):
    from types import SimpleNamespace
    from rodada18_ag import EVID, evaluate, frame_for, load_json, mode_rules, normal, strategy_program

    origin = EVID/"estrategia_pullback_confirmacao_v1_1"/"real.json"
    args = SimpleNamespace(pesquisa=research, saida=private)
    program = strategy_program(args,version)
    params = program.inputs | normal(load_json(research/origin)["parametros"])
    prev = {}
    for split in ("desenvolvimento","exploratorio"):
        _, frame = frame_for(args,group,split)
        prev[split] = dict(parametros=params, metricas=evaluate(
            program,frame,group,mode_rules(version["grupo"],None),params,group["lote"]))
    return dict(perfil="publicado", fonte=origin.as_posix(), resultado=prev)


def consolidate(private, evidence, research):
    published = private/"publico"
    locked = load(published/"protocolo.json")
    if load(evidence/"protocolo.json") != locked:
        raise ValueError("O protocolo executado difere do protocolo versionado.")
    expected = {Path(s["arquivo"]).stem: s for s in locked["estrategias"]}
    catalog = load(published/"inventario_estrategias.json")
    by_id = {entry["id"]: entry for entry in catalog if entry["status"]=="apta"}
    stats, ranking, resources = [], defaultdict(list), {}
    files = sorted((published/"resultados").glob("*.json"))
    if {p.stem for p in files} != set(expected):
        raise ValueError("Resultados AG incompletos ou versão inesperada.")
    results = evidence/"resultados"
    results.mkdir(exist_ok=True)
    dedup = {}
    pb = expected["pullback_tendencia_v1_0"]
    historical_baseline = published/"baseline_publicado_v1_0.json"
    if not historical_baseline.exists():
        save(historical_baseline,historical_control(private,research,pb,locked["grupos"][pb["grupo"]]))
    for path in files:
        name = path.stem
        result = load(path)
        version = expected[name]
        if name == "pullback_tendencia_v1_0" and historical_baseline.exists():
            previous = load(historical_baseline)
            result["perfil_publicado_origem"] = previous["fonte"]
            for split, prior in previous["resultado"].items():
                result[split]["publicado"] = prior
                chosen = result[split].get("otimizado")
                if chosen:
                    chosen["delta_publicado_reais"] = round(chosen["metricas"]["liquido"]-prior["metricas"]["liquido"],2)
        if result["congelado"]["sha256"] != version["sha256"]:
            raise ValueError(f"SHA-256 de estratégia divergente: {name}")
        if result["congelado"]["parametros"] != load(published/"congelados"/path.name)["parametros"]:
            raise ValueError(f"Congelamento divergente: {name}")
        if result["recursos"]["avaliados"] != len(result["avaliacoes"]):
            raise ValueError(f"Contagem de candidatos divergente: {name}")
        if result["configuracao"]["parametros"] != version["busca"]:
            raise ValueError(f"Grade do AG divergente: {name}")
        by_id[result["chave"]].update(status="executada", selecionou_candidato=result["congelado"]["apta"],
                                       relatorio=f"resultados/{path.name}")
        resources[name] = result["recursos"]
        group_name = result["grupo"]
        group = locked["grupos"][group_name]
        for split in ("desenvolvimento","exploratorio"):
            for profile,r in result[split].items():
                row = dict(r["metricas"])
                days = row.pop("por_pregao")
                if list(days) != group[split]:
                    raise ValueError(f"Calendário divergente para {name} {split}.")
                if row["operacoes"] != sum(v["operacoes"] for v in days.values()):
                    raise ValueError(f"Contagem diária divergente para {name} {split}.")
                if abs(row["liquido"]-sum(v["liquido"] for v in days.values())) > 0.01:
                    raise ValueError(f"Líquido por pregão divergente para {name} {split}.")
                qty = r["parametros"].get("p_lote", group["lote"])
                if row["max_exposicao"] not in {0,qty}:
                    raise ValueError(f"Lote divergente para {name} {split}.")
                label = "padronizado_lote_modo" if profile=="publicado" and not name.startswith("pullback_") else profile
                stats.append(dict(versao=name, grupo=group_name, recorte=split, perfil=label, lote=qty,
                                  delta_original_reais=r.get("delta_original_reais"),
                                  delta_publicado_reais=r.get("delta_publicado_reais"), **row))
        if result["congelado"]["apta"]:
            dev = result["desenvolvimento"]["otimizado"]
            explore = result["exploratorio"]["otimizado"]
            fingerprint = (tuple(dev["metricas"]["por_pregao"].items()), tuple(explore["metricas"]["por_pregao"].items()))
            normalized = (json.dumps(fingerprint, sort_keys=True), json.dumps(dev["metricas"], sort_keys=True),
                          json.dumps(explore["metricas"], sort_keys=True))
            equivalent = dedup.setdefault((group_name, normalized), name)
            ranking[group_name].append(dict(
                versao=name, desenvolvimento=dev, exploratorio=explore,
                validacao_inedita=None, metricas_agregadas_iguais_a=equivalent if equivalent!=name else None))
        save(results/path.name,result)
    stats.sort(key=lambda r:(r["grupo"],r["versao"],r["recorte"],r["perfil"]))
    with (evidence/"comparativo.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(stats[0]), delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(stats)
    save(evidence/"ranking.json", {
        "exploratorio": {g:sorted(ranking[g], key=lambda r:r["exploratorio"]["metricas"]["liquido"], reverse=True)
                         for g in locked["grupos"]},
        "todos_os_perfis_exploratorios": {
            g:sorted((r for r in stats if r["recorte"]=="exploratorio" and r["grupo"]==g
                      and r["perfil"]!="padronizado_lote_modo"), key=lambda r:r["liquido"], reverse=True)
            for g in locked["grupos"]
        },
        "validacao_inedita": None,
        "grupos": locked["grupos"],
        "criterio": "Líquido exploratório dos candidatos congelados por grupo; ordem de relato sem reseleção.",
    })
    probe = {path.stem:load(path) for path in sorted((published/"piloto").glob("*.json"))}
    save(evidence/"recursos.json", dict(
        candidatos_avaliados=sum(v["avaliados"] for v in resources.values()),
        segundos_busca_somados=round(sum(v["segundos_ag"] for v in resources.values()),2),
        segundos_execucao_ag_somados=round(sum(v["segundos"] for v in resources.values()),2),
        intervalo_parede_aproximado_s=utc_interval(published/"protocolo.json", max(files,key=lambda p:p.stat().st_mtime)),
        rss_somado_pico_por_busca_mib=max(v["rss_somado_pico_mib"] for v in resources.values()),
        menor_memoria_disponivel_mib=min(v["memoria_disponivel_min_mib"] for v in resources.values()),
        log=resources, pilotos=probe,
    ))
    save(evidence/"inventario_estrategias.json",catalog)
    coverage = load(published/"cobertura.json")
    save(evidence/"cobertura.json",coverage)
    return Counter(r["status"] for r in catalog)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--privado", type=Path, required=True)
    parser.add_argument("--evidencias", type=Path, required=True)
    parser.add_argument("--pesquisa", type=Path, required=True)
    args=parser.parse_args()
    print(dict(consolidate(args.privado,args.evidencias,args.pesquisa)))
