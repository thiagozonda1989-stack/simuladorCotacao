"""Publica a conferência da sonda nativa sem divulgar cotações absolutas."""

import argparse
import json
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from tools.publicar_s1_toque_tardio_profit import profit_bars
from tools.publicar_sonda_lacuna_profit import debug_blocks, number, raw_operation, write_csv
from tools.publicar_sondas_protecao_profit import (
    TIMESTAMP_FORMAT, bar_window, normalize_console, read_csv,
)


CASES = (
    ("01_alvo_controle", 1, 0, "01_alvo_mercado_configuracao.png"),
    ("02_alvo_mercado", 1, 1, "02_alvo_mercado_configuracao.png"),
    ("03_stop_controle", 2, 0, "03_stop_controle_configuracao.png"),
    ("04_stop_mercado", 2, 1, "04_stop_mercado_configuracao.png"),
)
OHLC = ("abertura", "maxima", "minima", "fechamento")
HOURS = [f"10:{minute}" for minute in range(51, 59)]
REFERENCES = ("SONDA_S1_ALVO_barras.csv", "SONDA_S1_STOP_barras.csv", "barras_v58.csv")
PANEL = dict(p_Data=1261026, p_Entrada=1051, p_Protecao=1052, p_EnvioMercado=1054,
             p_Limpeza=1056, p_Fim=1058, p_Alvo=428, p_Stop=793, p_Folga=101)


def file_info(path, data):
    return dict(arquivo=path.name, bytes=len(data), sha256=sha256(data).hexdigest())


def window_references(root, prepared):
    window = bar_window(prepared, HOURS[0], HOURS[-1])
    references = []
    for name in REFERENCES:
        path = root / name
        raw = path.read_bytes()
        records = profit_bars(raw)
        target = {stamp.strftime("%H:%M"): prices for stamp, *prices in records
                  if stamp.date().isoformat() == "2026-10-26" and stamp.strftime("%H:%M") in HOURS}
        assert sum(row[0].date().isoformat() == "2026-10-26" and row[0].strftime("%H:%M") in HOURS
                   for row in records) == len(HOURS)
        assert all(tuple(target[hour]) == tuple(window[hour][key] for key in OHLC) for hour in HOURS)
        references.append(file_info(path, raw) | dict(barras_total=len(records), barras_janela=len(target)))
    raw = prepared.read_bytes()
    references.append(file_info(prepared, raw) | dict(barras_total=len(read_csv(prepared, ";")),
                                                    barras_janela=len(window)))
    return window, references


def native_log(case, raw, entry, bars, leg, market):
    blocks = debug_blocks(raw)
    if len(blocks) != 2 or blocks[0] != blocks[1]:
        raise ValueError(f"{case}: blocos completos diferentes, sem deduplicação.")
    lines = raw.decode("utf-8-sig").splitlines()
    retained = [(i, line) for i, line in enumerate(lines, 1) if i <= len(blocks[0]) + 1]
    non_events = [line for _, line in retained if not line.startswith("PRIORIDADE;")]
    if non_events != ["Código em Execução", "Modo de Debug"]:
        raise ValueError(f"{case}: há mensagens adicionais a preservar na inspeção do original.")
    structured = [(i, line) for i, line in retained if line.startswith("PRIORIDADE;")]
    console = normalize_console(case, [line for _, line in structured], entry, number)
    expected_states = [(HOURS[0], 0, 0), (HOURS[0], 1, 0), (HOURS[1], 1, 0),
                       (HOURS[2], 1, 1), (HOURS[3], 1, 1),
                       *((hour, 0, 0) for hour in HOURS[4:])]
    observed_states = []
    for (line_number, line), row in zip(structured, console, strict=True):
        row["linha_original"] = line_number
        assert row["data_ntsl"] == PANEL["p_Data"]
        for key in OHLC:
            row[f"{key}_pts_entrada"] = ""
        if row["evento"] == "AVALIACAO":
            pairs = dict(part.split("=", 1) for part in line.split(";")[2:])
            hour = row["hora_contexto"]
            prices = {key: number(pairs[key]) for key in OHLC}
            assert prices == bars[hour], (case, hour)
            observed_states.append((hour, row["posicao"], row["pendentes"]))
            for key, value in prices.items():
                row[f"{key}_pts_entrada"] = value - entry
    assert observed_states == expected_states
    assert [r["currentbar"] for r in console if r["evento"] == "AVALIACAO"] == [26873, *range(26873, 26881)]
    protection = "SOLICITA_ALVO" if leg == 1 else "SOLICITA_STOP"
    requested = [r for r in console if r["evento"] != "AVALIACAO"]
    orders = [("SOLICITA_COMPRA", "10:51"), (protection, "10:52")]
    if market:
        orders.append(("SOLICITA_MERCADO", "10:54"))
    assert [(r["evento"], r["hora_contexto"]) for r in requested] == orders
    return console, len(blocks)


def pdf_totals(path):
    import pymupdf

    with pymupdf.open(path) as doc:
        page, = doc
        lines = page.get_text().splitlines()
    assert lines[lines.index("Data:") + 1] == "26/10/2026"
    net = lines[lines.index("Saldo Líquido Total") + 2]
    cost = lines[lines.index("Custos") + 2]
    count = int(lines[lines.index("Número Total de Operações") + 2])
    return number(net.removeprefix("R$ ")), number(cost.removeprefix("R$ ")), count


def replay(path, query):
    entry, exit_fill = read_csv(path / "execucoes.csv")
    assert [r["acao"] for r in (entry, exit_fill)] == ["long", "exit_long"]
    assert all(int(r["quantidade"]) == 1 and r["pregao"] == "2026-10-26" for r in (entry, exit_fill))
    candles = read_csv(path / "candles.csv")
    times = [candles[int(r["barra"]) - 1]["timestamp"][11:19] for r in (entry, exit_fill)]
    assert times == ["10:52:00", "10:55:00"]
    base = Decimal(entry["preco"])
    messages = [row["mensagem"] for row in read_csv(path / "console.csv")
                if row["mensagem"].startswith("PRIORIDADE;")]
    logs = normalize_console(path.name, messages, base, Decimal)
    signature = [(r["hora_contexto"], r["evento"], r["posicao"], r["pendentes"]) for r in logs]
    assert signature == query
    metrics = json.loads((path / "metricas.json").read_text(encoding="utf-8"))
    trace = read_csv(path / "eventos_ordens.csv")
    assert metrics["barras_ambiguas"] == 0 and int(exit_fill["posicao"]) == 0
    return dict(
        entrada=base, entrada_execucao=times[0], saida_execucao=times[1],
        qtd=int(exit_fill["quantidade"]), pontos=Decimal(exit_fill["pontos_contrato"]),
        liquido_brl=Decimal(exit_fill["liquido_reais"]).quantize(Decimal("0.01")),
        ordem_motor=exit_fill["ordem"],
        gatilhos_motor=sum(r["evento"] == "gatilho_stop" for r in trace),
        ambiguidades_motor=metrics["barras_ambiguas"],
    )


def collect(args):
    bars, references = window_references(args.originais, args.barras)
    prior = {(row["perna"], int(row["solicita_saida_mercado"])): row
             for row in read_csv(args.referencia / "sonda_prioridade_simulador.csv", ";")}
    inventory, panels, logs, matrix = [], [], [], []
    entry_reference = bars["10:52"]["abertura"]
    for case, leg, market, screenshot in CASES:
        perna = "alvo" if leg == 1 else "stop"
        names = {"console": f"{case}_console.txt", "operacoes": f"{case}_operacoes.csv",
                 "relatorio": f"{case}_relatorio.pdf", "print": screenshot}
        paths = {kind: args.originais / name for kind, name in names.items()}
        data = {kind: path.read_bytes() for kind, path in paths.items()}
        operation = raw_operation(data["operacoes"])
        assert (operation["Ativo"], operation["Lado"], operation["Qtd Compra"], operation["Qtd Venda"]) == (
            "WINZ26", "C", "1", "1")
        entry, closing = (number(operation[key]) for key in ("Preço Compra", "Preço Venda"))
        entry_at, exit_at = (datetime.strptime(operation[key], TIMESTAMP_FORMAT)
                             for key in ("Abertura", "Fechamento"))
        assert entry == entry_reference and entry_at.isoformat() == "2026-10-26T10:52:00"
        assert exit_at.isoformat() == "2026-10-26T10:55:00" and exit_at - entry_at == timedelta(minutes=3)
        profit_points = closing - entry
        total, costs, count = pdf_totals(paths["relatorio"])
        assert (total, costs, count) == (number(operation["Total"]), number(operation["Comissões"]), 1)
        console, copies = native_log(case, data["console"], entry, bars, leg, market)
        protection, = [r for r in console if r["evento"] in {"SOLICITA_ALVO", "SOLICITA_STOP"}]
        assert protection["limite_pts_entrada"] == (PANEL["p_Alvo"] if leg == 1 else -PANEL["p_Stop"] - PANEL["p_Folga"])
        assert protection["gatilho_pts_entrada"] == ("" if leg == 1 else -PANEL["p_Stop"])
        logs.extend(console)
        panels.append(dict(rodada=case, print_original=screenshot, ativo="WINZ26", minutos=1,
                           analise_inicio="2026-10-26", analise_fim="2026-10-26",
                           quantidade=1, quantidade_maxima=1, slippage_ticks=0, custos_brl=costs,
                           executar_nos_limites=1, backtest_visivel=1, seletor_ohlc_visivel=0,
                           p_Perna=leg, p_SaidaMercado=market, **PANEL))
        for kind in names:
            inventory.append(dict(rodada=case, fonte=kind) | file_info(paths[kind], data[kind]) | dict(
                bloco_copias=copies if kind == "console" else "",
                unidades_derivadas=len(console) if kind == "console" else 1,
            ))

        signature = [(r["hora_contexto"], r["evento"], r["posicao"], r["pendentes"]) for r in console]
        effective = replay(args.replays / f"painel-{leg}-{market}", signature)
        defaults = replay(args.replays / f"padrao-{leg}-{market}", signature)
        historical = prior[perna, market]
        assert effective["entrada"] == defaults["entrada"] == entry
        assert (defaults["pontos"], defaults["ordem_motor"], defaults["gatilhos_motor"]) == (
            Decimal(historical["pontos"]), historical["tipo_saida"], int(historical["eventos_disparo_stop"]))
        assert [defaults["entrada_execucao"][:5], defaults["saida_execucao"][:5]] == [
            historical["hora_entrada"], historical["hora_saida"]]
        opening_points = bars["10:55"]["abertura"] - entry
        common = dict(
            rodada=case, p_Perna=leg, p_SaidaMercado=market, entrada_contexto="10:51",
            entrada_execucao=str(entry_at.time()), protecao_contexto="10:52",
            posicao_1054=1, pendentes_1054=1, solicita_mercado_contexto="10:54" if market else "",
            abertura_1055_pts_entrada=opening_points, saida_execucao=str(exit_at.time()),
            qtd_compra=1, qtd_venda=1, operacoes=1, posicao_1055=0, pendentes_1055=0,
            posicao_1058=0, pendentes_1058=0,
            alvo_ou_limite_solicitado_pts_entrada=protection["limite_pts_entrada"],
            gatilho_solicitado_pts_entrada=protection["gatilho_pts_entrada"],
        )
        for label, result in (
            ("Profit", dict(pontos=profit_points, liquido_brl=total, ordem_motor="",
                            gatilhos_motor="", ambiguidades_motor="")),
            ("Simulador painel", effective), ("Simulador padrões", defaults),
        ):
            row = common.copy()
            if label == "Simulador padrões":
                row["alvo_ou_limite_solicitado_pts_entrada"] = 430 if leg == 1 else -895
                row["gatilho_solicitado_pts_entrada"] = "" if leg == 1 else -795
            matrix.append(row | dict(
                fonte=label, saida_pts_entrada=result["pontos"],
                saida_menos_abertura_pts=result["pontos"] - opening_points,
                resultado_liquido_brl=result["liquido_brl"],
                ordem_simulador=result["ordem_motor"], gatilhos_simulador=result["gatilhos_motor"],
                ambiguidades_simulador=result["ambiguidades_motor"],
            ))

    distinct_exports = len({row["sha256"] for row in references[:-1]})
    geometry = [
        dict(hora_barra=hour, **{f"{key}_pts_entrada": prices[key] - entry_reference for key in OHLC},
             consoles_concordantes=len(CASES), csvs_anteriores_concordantes=len(REFERENCES),
             conteudos_csv_anteriores_distintos=distinct_exports)
        for hour, prices in bars.items()
    ]
    return {
        "inventario_anexos.csv": inventory, "parametros_por_rodada.csv": panels,
        "console_profit.csv": logs, "barras_conferencia.csv": geometry,
        "fontes_barras.csv": references, "matriz_profit_simulador.csv": matrix,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("originais", "replays", "referencia", "barras", "saida"):
        parser.add_argument(f"--{field}", type=Path, required=True)
    args = parser.parse_args()
    outputs = collect(args)
    args.saida.mkdir()
    for filename, values in outputs.items():
        write_csv(args.saida / filename, values)


if __name__ == "__main__":
    main()
