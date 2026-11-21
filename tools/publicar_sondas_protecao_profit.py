"""Confere as sondas S1 e S2 e extrai resultados compartilháveis."""

import argparse
import csv
import re
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from tools.publicar_sonda_lacuna_profit import debug_blocks, number, raw_operation, write_csv


CASES = (
    ("s1", "sonda_s1", "", "SONDA_S1", "13:15", "13:23"),
    ("s2v1", "sonda_s2", "_variante1", "SONDA_S2", "13:44", "13:50"),
    ("s2v2", "sonda_s2", "_variante2", "SONDA_S2", "15:27", "15:33"),
)
WARNING = re.compile(r"stop em ([\d.]+), acima da abertura do candle \(([\d.]+)\)")
TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"


def read_csv(path, delimiter=","):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def normalize_console(sonda, lines, entry, numeric):
    result = []
    context = None
    for index, line in enumerate(lines, 1):
        _, event, *parts = line.split(";")
        values = dict(part.split("=", 1) for part in parts)
        if event == "AVALIACAO":
            context = values
        if context is None or values["seq"] != context["seq"]:
            raise ValueError(f"{sonda}: evento fora da avaliação correspondente.")
        time = f"{int(numeric(context['hora'])):04}"
        result.append(dict(
            sonda=sonda, seq_console=index, evento=event, seq_avaliacao=int(values["seq"]),
            data_ntsl=int(numeric(context["data"])), hora_contexto=time[:2] + ":" + time[2:],
            currentbar=int(numeric(context["barra"])), posicao=int(context["posicao"]),
            pendentes=int(context["pendentes"]),
            gatilho_pts_entrada=numeric(values["gatilho"]) - entry if "gatilho" in values else "",
            limite_pts_entrada=numeric(values["limite"]) - entry if "limite" in values else "",
        ))
    return result


def native_console(sonda, data, prefix, entry):
    blocks = debug_blocks(data)
    events = [[line for line in block if line.startswith(prefix)] for block in blocks]
    if not events or not events[0] or any(rows != events[0] for rows in events[1:]):
        raise ValueError(f"{sonda}: blocos estruturados divergentes ou vazios.")
    warnings = []
    for block_number, block in enumerate(blocks, 1):
        position = 0
        for line in block:
            position += line.startswith(prefix)
            if line.startswith("SellToCoverStop enviado com stop em"):
                match = WARNING.search(line)
                if match is None:
                    raise ValueError(f"{sonda}: aviso de stop em formato desconhecido.")
                trigger, opening = map(number, match.groups())
                warnings.append(dict(
                    sonda=sonda, bloco=block_number, apos_evento_estruturado=position,
                    gatilho_pts_entrada=trigger - entry, abertura_pts_entrada=opening - entry,
                    abertura_menos_gatilho_pts=opening - trigger,
                    descricao="Stop de venda acima da abertura; comportamento da automação pode diferir",
                ))
    return len(blocks), normalize_console(sonda, events[0], entry, number), warnings


def bar_window(path, start, end):
    date = "2026-10-26"
    bars = {row["timestamp"][11:16]: row for row in read_csv(path, ";")
            if row["timestamp"].startswith(date)}
    first = datetime.fromisoformat(f"{date}T{start}")
    last = datetime.fromisoformat(f"{date}T{end}")
    window = {}
    while first <= last:
        stamp = first.strftime("%H:%M")
        window[stamp] = {field: Decimal(bars[stamp][field])
                         for field in ("abertura", "maxima", "minima", "fechamento")}
        first += timedelta(minutes=1)
    return window


def collect_case(args, spec, tables):
    case, stem, suffix, prefix, start, end = spec
    sources = {}
    inventory = {}
    for kind, extension, format_name in (
        ("console", "txt", "TXT UTF-8"),
        ("relatorio", "pdf", "PDF"),
        ("operacoes", "csv", "CSV CP1252"),
        ("evidencia", "png", "PNG"),
    ):
        name = f"{stem}_{kind}{suffix}.{extension}"
        content = (args.originais / name).read_bytes()
        sources[kind] = content
        inventory[kind] = dict(
            sonda=case, arquivo=name, bytes=len(content), sha256=sha256(content).hexdigest(),
            formato=format_name, blocos_estruturados_iguais="", eventos_estruturados_retidos="",
        )

    op = raw_operation(sources["operacoes"])
    opening, closing = (datetime.strptime(op[key], TIMESTAMP_FORMAT) for key in ("Abertura", "Fechamento"))
    if op["Ativo"] != "WINZ26" or op["Lado"] != "C" or (op["Qtd Compra"], op["Qtd Venda"]) != ("1", "1"):
        raise ValueError(f"{case}: operação incompatível com a sonda.")
    entry, exit_price = map(number, (op["Preço Compra"], op["Preço Venda"]))
    count, native, warnings = native_console(case, sources["console"], prefix, entry)
    inventory["console"].update(blocos_estruturados_iguais=count, eventos_estruturados_retidos=len(native))

    local = args.replays / case
    fills = read_csv(local / "execucoes.csv")
    candles = read_csv(local / "candles.csv")
    local_logs = [row["mensagem"] for row in read_csv(local / "console.csv")
                  if row["mensagem"].startswith(prefix)]
    simulated = normalize_console(case, local_logs, entry, Decimal)
    _, exit_fill = fills
    local_times = [datetime.fromisoformat(candles[int(fill["barra"]) - 1]["timestamp"]).replace(tzinfo=None)
                   for fill in fills]
    exact = (local_times == [opening, closing]
             and [row["acao"] for row in fills] == ["long", "exit_long"]
             and [Decimal(row["preco"]) for row in fills] == [entry, exit_price]
             and [int(row["quantidade"]) for row in fills] == [1, 1])
    current = bar_window(args.barras, start, end)
    opened_at, closed_at = (time.strftime("%H:%M") for time in (opening, closing))
    target, = [r["gatilho_pts_entrada"] for r in native if r["evento"] == "SOLICITA_STOP"]
    trigger = entry + target
    bar = current[closed_at]
    tables["comparacao.csv"].append(dict(
        sonda=case, pregao=opening.date(), lado="C", quantidade=1,
        entrada_profit=opening.time(), saida_profit=closing.time(),
        entrada_simulador=local_times[0].time(), saida_simulador=local_times[1].time(),
        entrada_saida_exatas=int(exact), saida_ordem_simulador=exit_fill["ordem"],
        duracao_segundos=int((closing - opening).total_seconds()),
        resultado_pontos_profit=exit_price - entry, resultado_pontos_simulador=Decimal(exit_fill["pontos_contrato"]),
        liquido_brl_profit=number(op["Total"]), liquido_brl_simulador=Decimal(exit_fill["liquido_reais"]),
        comissoes_brl_profit=number(op["Comissões"]),
        entrada_ao_preco_abertura=int(entry == current[opened_at]["abertura"]),
        saida_ao_preco_abertura=int(exit_price == bar["abertura"]),
        gatilho_contido_na_barra_de_saida=int(bar["minima"] <= trigger <= bar["maxima"]),
        saida_pts_ao_gatilho=exit_price-trigger if case != "s1" else "",
    ))
    for time, candle in current.items():
        tables["barras_relativas.csv"].append(dict(
            sonda=case, hora_barra=time,
            **{f"{key}_pts_entrada": value - entry for key, value in candle.items()},
            maxima_pts_ao_gatilho=candle["maxima"] - trigger,
            minima_pts_ao_gatilho=candle["minima"] - trigger,
        ))
    tables["console_profit.csv"].extend(native)
    tables["console_simulador.csv"].extend(simulated)
    tables["avisos.csv"].extend(warnings)
    tables["inventario.csv"].extend(inventory.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("originais", "replays", "barras", "saida"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    tables = {name: [] for name in ("comparacao.csv", "barras_relativas.csv", "console_profit.csv",
                                    "console_simulador.csv", "avisos.csv", "inventario.csv")}
    for spec in CASES:
        collect_case(args, spec, tables)
    args.saida.mkdir(exist_ok=False)
    for name, rows in tables.items():
        if rows:
            write_csv(args.saida / name, rows)


if __name__ == "__main__":
    main()
