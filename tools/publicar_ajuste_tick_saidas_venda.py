"""Compara replays da regra de grade e gera derivados sem cotações absolutas."""

import argparse
import html
from decimal import Decimal
from pathlib import Path

import pandas as pd

from tools.comparar_paridade_profit_win import (
    compare_operations, local_round_trips, profit_round_trips, read_profit_operations,
)
from tools.publicar_protecoes_ohlc import DATA_FILES, DAYS, V57, V58, read_json, rows
from tools.publicar_sonda_lacuna_profit import write_csv
from tools.publicar_sondas_protecao_profit import normalize_console, read_csv


FILES = (*DATA_FILES, "estrategia.ntsl", "metricas.json", "relatorio.html")
AUDIT_FIELDS = {"nivel_solicitado", "nivel_efetivo", "limite_solicitado", "limite_efetivo", "ajuste_tick"}


def assertion_metrics(off, on):
    off_report, on_report = (read_json(path / "metricas.json") for path in (off, on))
    counters = on_report.pop("ajustes_tick_saidas_venda")
    assert on_report["regras_execucao"].pop("ajuste_tick_saidas_venda") is True
    assert off_report == on_report and counters == {"ajustado": 0, "empate_meio_tick": 0}
    return counters, off_report


def check_artifacts(reference, off, on):
    baseline_equal = [name for name in FILES if (reference / name).read_bytes() == (off / name).read_bytes()]
    assert len(baseline_equal) == len(FILES), (off.name, set(FILES) - set(baseline_equal))
    on_equal = [name for name in FILES if (on / name).read_bytes() == (off / name).read_bytes()]
    assert set(on_equal) == {"execucoes.csv", "candles.csv", "console.csv", "estrategia.ntsl"}, on.name
    counters, metric = assertion_metrics(off, on)
    marker = ", &#x27;ajuste_tick_saidas_venda&#x27;: True"
    counter_row = f"<tr><th>ajustes tick saidas venda</th><td>{html.escape(str(counters))}</td></tr>"
    old_html = (off / "relatorio.html").read_text(encoding="utf-8")
    new_html = (on / "relatorio.html").read_text(encoding="utf-8")
    assert old_html == new_html.replace(marker, "").replace(counter_row, ""), on.name
    old_events, new_events = (rows(folder / "eventos_ordens.csv") for folder in (off, on))
    assert all(AUDIT_FIELDS <= event.keys() for event in new_events)
    projected = [{key: value for key, value in event.items() if key not in AUDIT_FIELDS} for event in new_events]
    assert projected == old_events, on.name
    count_grade = sum(event["ajuste_tick"] == "na_grade" and event["evento"].startswith("solicitacao")
                      for event in new_events)
    return dict(
        arquivos_off_iguais_referencia=len(baseline_equal), arquivos_on_iguais_off=len(on_equal),
        rastreio_igual_sem_colunas_novas=1, metricas_html_iguais_sem_metadados_novos=1,
        solicitacoes_na_grade=count_grade, solicitacoes_ajustadas=counters["ajustado"],
        empates=counters["empate_meio_tick"], preenchimentos=metric["preenchimentos"],
        saidas=metric["saidas"], barras_ambiguas=metric["barras_ambiguas"],
        resultado_liquido_brl=metric["resultado_liquido_reais"],
    )


def regression(args):
    result = []
    for day in DAYS:
        profit = profit_round_trips(read_profit_operations(args.operacoes_v57, day))
        for version, modes in (("v5.7", V57), ("v5.8", V58)):
            for mode in modes:
                name = f"{day}-v57-{mode}" if version == "v5.7" else f"v58-{day}-{mode}"
                off, on = (args.replays / f"{name}-{flag}" for flag in ("off", "on"))
                comparison = check_artifacts(args.referencia / f"{name}-on", off, on)
                exact_182 = ""
                if version == "v5.7":
                    local = local_round_trips(pd.read_csv(on / "execucoes.csv"), pd.read_csv(on / "candles.csv"))
                    result_ops = compare_operations(profit, local)
                    target = profit.loc[profit["numero_operacao"] == 182]
                    if len(target):
                        exact_182 = compare_operations(target, local)["correspondencias_exatas"]
                else:
                    off_comparison, on_comparison = (
                        folder.with_suffix(".comparacao.json") for folder in (off, on)
                    )
                    assert off_comparison.read_bytes() == on_comparison.read_bytes()
                    result_ops = read_json(on_comparison)["operacoes"]
                result.append(dict(estrategia=version, pregao=day, modo=mode,
                                   operacoes_profit=result_ops["operacoes_profit"],
                                   operacoes_simulador=result_ops["operacoes_local"],
                                   operacoes_exatas=result_ops["correspondencias_exatas"],
                                   operacao_182_exata=exact_182) | comparison)
    minimal = check_artifacts(*(args.replays / f"minimo-{mode}" for mode in ("ref", "off", "on")))
    return result, [minimal]


def probe(folder):
    entry, closing = rows(folder / "execucoes.csv")
    base = Decimal(entry["preco"])
    candles = rows(folder / "candles.csv")
    entry_time, exit_time = (candles[int(fill["barra"]) - 1]["timestamp"][11:19] for fill in (entry, closing))
    assert entry_time == "10:52:00" and entry["quantidade"] == closing["quantidade"] == "1"
    events = rows(folder / "eventos_ordens.csv")
    protection, = [event for event in events if event["evento"] == "solicitacao"
                   and event["acao"] in {"exit_long", "exit_short"} and event["tipo"] in {"stop", "limit"}]
    assert protection["timestamp"][11:16] == "10:52"
    messages = [line["mensagem"] for line in rows(folder / "console.csv")
                if line["mensagem"].startswith(("GRADE_", "PRIORIDADE;"))]
    logs = normalize_console(folder.name, messages, base, Decimal)
    states = {row["hora_contexto"]: row for row in logs if row["evento"] == "AVALIACAO"}
    pending = [states[hour]["pendentes"] for hour in ("10:53", "10:54", "10:55")]
    assert pending[:2] == [1, 1]
    raw = protection.get("nivel_solicitado") or protection["gatilho"]
    limit = protection["limite"]
    return dict(
        entrada_execucao=entry_time, saida_execucao=exit_time, posicao_1055=states["10:55"]["posicao"],
        pendentes_1055=pending[2], solicitado_pts_entrada=Decimal(raw) - base,
        efetivo_pts_entrada=Decimal(protection["gatilho"]) - base,
        limite_stop_pts_entrada=Decimal(limit) - base if limit else "",
        saida_pts_entrada=Decimal(closing["preco"]) - base,
        pontos_contrato=Decimal(closing["pontos_contrato"]),
        ordem_simulador=closing["ordem"], ajuste_tick=protection.get("ajuste_tick", ""),
    )


def native_matrix(args):
    native_grade = [row for row in read_csv(args.evidencias_grade / "matriz_profit_simulador.csv", ";")
                    if row["fonte"] == "Profit"]
    native_priority = [row for row in read_csv(args.evidencias_prioridade / "matriz_profit_simulador.csv", ";")
                       if row["fonte"] == "Profit"]
    sources = list(zip((f"g{i}" for i in (1, 2)), native_grade, strict=True)) + [
        (f"prioridade-{row['p_Perna']}-{row['p_SaidaMercado']}", row) for row in native_priority]
    matrix = []
    for name, native in sources:
        for flag in ("off", "on"):
            row = probe(args.replays / f"{name}-{flag}")
            observed = Decimal(native["saida_pts_entrada"])
            equal = row["saida_pts_entrada"] == observed and row["saida_execucao"] == native["saida_execucao"]
            assert row["ajuste_tick"] == ("ajustado" if flag == "on" else "")
            assert equal == (flag == "on" or native.get("p_SaidaMercado") == "1")
            matrix.append(dict(caso=name, ajuste=flag, saida_profit=native["saida_execucao"],
                               saida_profit_pts_entrada=observed, coincide_profit=int(equal)) | row)
    return matrix


def buy_probes(args):
    result = []
    for name in ("g3", "g4"):
        for profile in ("bruto", "grade"):
            row = probe(args.replays / f"{name}-{profile}")
            assert row["ajuste_tick"] == "" and row["solicitado_pts_entrada"] == row["efetivo_pts_entrada"]
            expected_price = {"g3": -875, "g4": 445}[name] if profile == "grade" else -375
            assert row["saida_pts_entrada"] == expected_price
            assert row["saida_execucao"] == ("10:55:00" if profile == "grade" else "10:58:00")
            assert row["posicao_1055"] == (0 if profile == "grade" else -1)
            result.append(dict(sonda=name.upper(), perfil=profile, profit="pendente") | row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("replays", "referencia", "operacoes-v57", "evidencias-grade", "evidencias-prioridade", "saida"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    regressions, minimal = regression(args)
    outputs = {"regressoes.csv": regressions, "replay_minimo.csv": minimal,
               "matriz_sondas.csv": native_matrix(args), "sondas_g3_g4_simulador.csv": buy_probes(args)}
    args.saida.mkdir()
    for filename, table in outputs.items():
        write_csv(args.saida / filename, table)


if __name__ == "__main__":
    main()
