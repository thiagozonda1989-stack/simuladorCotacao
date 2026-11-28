"""Resume replays privados de proteção OHLC sem divulgar cotações."""
import argparse
import csv
import json
import re
from decimal import Decimal
from pathlib import Path

import pandas as pd

from tools.comparar_paridade_profit_win import (
    compare_operations, local_round_trips, profit_round_trips, read_profit_operations,
)
from tools.publicar_sonda_lacuna_profit import write_csv
from tools.publicar_sondas_protecao_profit import normalize_console


DAYS = ("2026-10-21", "2026-10-26")
V57 = ("padrao", "protecao-legada", "pos-preenchimento", "pareado-continuidade", "pareado-entrada")
V58 = ("reinicio", "continuidade", "entrada")
DATA_FILES = ("candles.csv", "execucoes.csv", "console.csv", "eventos_ordens.csv")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def metrics_equal_without_flag(left, right):
    left, right = (read_json(path / "metricas.json") for path in (left, right))
    for payload in (left, right):
        payload["regras_execucao"].pop("protecoes_ate_cancelar", None)
    return left == right


def html_equal_without_flag(left, right):
    marker = r", &#x27;protecoes_ate_cancelar&#x27;: (?:True|False)"
    before, after = (re.sub(marker, "", (path / "relatorio.html").read_text(encoding="utf-8"))
                     for path in (left, right))
    return before == after


def regression(args):
    matrices = {"v5.7": [], "v5.8": []}
    comparisons = []
    for day in DAYS:
        native_v57 = profit_round_trips(read_profit_operations(args.operacoes_v57, day))
        for version, modes in (("v5.7", V57), ("v5.8", V58)):
            for mode in modes:
                key = f"{day}-v57-{mode}" if version == "v5.7" else f"v58-{day}-{mode}"
                previous = args.referencia / key
                off, on = (args.atuais / f"{key}-{state}" for state in ("off", "on"))
                for description, left, right in (("referencia_x_off", previous, off), ("off_x_on", off, on)):
                    for name in (*DATA_FILES, "estrategia.ntsl", "metricas.json", "relatorio.html"):
                        equals = (left / name).read_bytes() == (right / name).read_bytes()
                        normalized = ""
                        if name == "metricas.json":
                            normalized = int(metrics_equal_without_flag(left, right))
                        elif name == "relatorio.html":
                            normalized = int(html_equal_without_flag(left, right))
                        comparisons.append(dict(
                            conjunto=key, comparacao=description, arquivo=name, bytes_iguais=int(equals),
                            conteudo_igual_sem_flag=normalized,
                        ))
                for state, folder in (("off", off), ("on", on)):
                    common = dict(pregao=day, modo=mode, protecoes_ate_cancelar=state)
                    if version == "v5.7":
                        local = local_round_trips(pd.read_csv(folder / "execucoes.csv"),
                                                  pd.read_csv(folder / "candles.csv"))
                        report = compare_operations(native_v57, local)
                        target = native_v57.loc[native_v57["numero_operacao"] == 182]
                        exact_182 = compare_operations(target, local)["correspondencias_exatas"] if len(target) else ""
                        fields = dict(operacao_182_exata=exact_182)
                    else:
                        full = read_json(folder.with_suffix(".comparacao.json"))
                        report = full["operacoes"]
                        requests = full["solicitacoes_pregao"]
                        first = full["preenchimentos"]["primeira_divergencia"] or {}
                        fields = dict(
                            solicitacoes_comparadas=requests["comparados"],
                            solicitacoes_divergentes=requests["divergentes"],
                            primeiro_preenchimento_diferente_profit=(first.get("profit") or [""])[0][11:16],
                            primeiro_preenchimento_diferente_simulador=(first.get("simulador") or [""])[0][11:16],
                        )
                    matrices[version].append(common | dict(
                        profit=report["operacoes_profit"], simulador=report["operacoes_local"],
                        exatas=report["correspondencias_exatas"],
                    ) | fields)
    return {"regressao_v57.csv": matrices["v5.7"], "regressao_v58.csv": matrices["v5.8"],
            "comparacao_artefatos.csv": comparisons}


def focused(args):
    s1, priority, v3 = [], [], []
    for leg in ("alvo", "stop"):
        for state in ("off", "on", "global", "global-e-on"):
            folder = args.atuais / f"s1-{leg}-{state}"
            opening, closing = rows(folder / "execucoes.csv")
            times = {row["indice"]: row["timestamp"][11:16] for row in rows(folder / "candles.csv")}
            prefix = "SONDA_S1_" + leg.upper()
            messages = [row["mensagem"] for row in rows(folder / "console.csv")
                        if row["mensagem"].startswith(prefix)]
            console = normalize_console(f"s1_{leg}", messages, Decimal(opening["preco"]), Decimal)
            pending = {item["hora_contexto"]: item["pendentes"] for item in console
                       if item["evento"] == "AVALIACAO"}
            prior = args.referencia_s1 / f"{leg}-{'padrao' if state == 'off' else 'diagnostico'}"
            s1.append(dict(
                perna=leg, modo=state, pendentes_t1=pending["10:53"], pendentes_t2=pending["10:54"],
                pendentes_t3=pending["10:55"], saida=times[str(int(closing["barra"]) - 1)],
                tipo_saida=closing["ordem"], pontos=closing["pontos_contrato"],
                arquivos_iguais_a_referencia=sum((folder / name).read_bytes() == (prior / name).read_bytes()
                                                 for name in DATA_FILES),
            ))
    for leg in (1, 2):
        for market in (0, 1):
            folder = args.atuais / f"prioridade-{leg}-{market}"
            events = rows(folder / "eventos_ordens.csv")
            opening, closing = (event for event in events if event["evento"] == "preenchimento")
            positions = {event["timestamp"][11:16]: event["posicao"] for event in events
                         if event["evento"] == "avaliacao_ntsl"}
            priority.append(dict(
                perna="alvo" if leg == 1 else "stop", solicita_saida_mercado=market,
                hora_entrada=opening["timestamp"][11:16], hora_saida=closing["timestamp"][11:16],
                tipo_saida=closing["ordem"],
                pontos=Decimal(closing["preco_execucao"]) - Decimal(opening["preco_execucao"]),
                fechamento_1055_posicao=positions["10:55"],
                eventos_disparo_stop=sum(event["evento"] == "gatilho_stop" for event in events),
                barras_ambiguas=read_json(folder / "metricas.json")["barras_ambiguas"],
            ))
    for case in (1, 2):
        for state in ("off", "on"):
            folder = args.atuais / f"sonda-{case}-entrada-{state}"
            metrics = read_json(folder / "metricas.json")
            events = rows(folder / "eventos_ordens.csv")
            fills = [event["timestamp"][11:16] for event in events if event["evento"] == "preenchimento"]
            v3.append(dict(caso=case, protecoes_ate_cancelar=state, entrada=fills[0], saida=fills[1],
                           cancelamentos_lacuna=metrics["ordens_canceladas_lacuna"],
                           lacunas_com_posicao=metrics["lacunas_com_posicao"]))
    return {"sondas_s1.csv": s1, "sonda_prioridade_simulador.csv": priority, "controle_lacuna.csv": v3}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("atuais", "referencia", "referencia-s1", "operacoes-v57", "saida"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    tables = regression(args) | focused(args)
    args.saida.mkdir()
    for filename, values in tables.items():
        write_csv(args.saida / filename, values)


if __name__ == "__main__":
    main()
