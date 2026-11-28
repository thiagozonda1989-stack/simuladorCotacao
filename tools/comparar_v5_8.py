"""Compara a auditoria v5.8 no Profit e no simulador pelo contexto NTSL."""

import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal
from itertools import zip_longest
from pathlib import Path

import pandas as pd

try:
    from tools.comparar_paridade_mesmas_barras import compare_same_bars
    from tools.comparar_paridade_profit_win import (
        compare_operations, first_difference, inventory, local_round_trips, normalize_bars, profit_round_trips,
        read_local_bars, read_profit, read_profit_operations, sha256, target_day,
    )
except ModuleNotFoundError:
    from comparar_paridade_mesmas_barras import compare_same_bars
    from comparar_paridade_profit_win import (
        compare_operations, first_difference, inventory, local_round_trips, normalize_bars, profit_round_trips,
        read_local_bars, read_profit, read_profit_operations, sha256, target_day,
    )


def console_lines(path, native):
    if native:
        content = path.read_bytes()
        try:
            return content.decode("utf-8-sig").splitlines()
        except UnicodeDecodeError:
            return content.decode("cp1252").splitlines()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return [row["mensagem"] for row in csv.DictReader(stream)]


def unique_native_capture(lines, prefix="V58", marker="AVALIACAO"):
    blocks = [[]]
    last = None
    for line in lines:
        message = line.strip()
        if not message.startswith(prefix + ";"):
            continue
        if message.startswith(f"{prefix};{marker};"):
            seq = int(next(part[4:] for part in message.split(";") if part.startswith("seq="))
                      .replace(".", ""))
            if last is not None and seq <= last:
                blocks.append([])
            last = seq
        blocks[-1].append(message)
    if any(block != blocks[0] for block in blocks[1:]):
        raise ValueError("O console contém múltiplas execuções distintas. Selecione uma execução.")
    return blocks[0], len(blocks)


def compare_bar_inputs(profit, prepared):
    supplemental = {"trades": "v_trades_atual", "quantity": "volume_contratos",
                    "volume_financeiro": "volume_financeiro"}
    if supplemental.keys() <= set(profit.columns):
        return compare_same_bars(profit, prepared)
    available = {name: source for name, source in supplemental.items() if name in profit}
    prepared = prepared.rename(columns={source: name for name, source in available.items()})
    common = profit.merge(prepared, on="timestamp", suffixes=("_profit", "_local"))
    fields = {}
    for name in ("abertura", "maxima", "minima", "fechamento", *available):
        left, right = f"{name}_profit", f"{name}_local"
        delta = (common[left] - common[right]).abs()
        fields[name] = {
            "iguais": int((delta == 0).sum()), "diferentes": int((delta != 0).sum()),
            "max_diferenca_absoluta": None if delta.empty else float(delta.max()),
            "primeira_divergencia": first_difference(common, left, right),
        }
    return {
        "profit": inventory(profit), "local": inventory(prepared), "comuns": len(common),
        "exclusivos_profit": [stamp.isoformat() for stamp in profit.loc[~profit.timestamp.isin(prepared.timestamp), "timestamp"]],
        "exclusivos_local": [stamp.isoformat() for stamp in prepared.loc[~prepared.timestamp.isin(profit.timestamp), "timestamp"]],
        "campos": fields, "campos_ausentes_exportacao_profit": sorted(set(supplemental) - set(available)),
    }


def audit_by_label(lines, day, native):
    grouped = defaultdict(list)
    day_code = int(day.replace("-", "")) - 19000000
    last_seq = None
    for line in lines:
        if not line.strip().startswith("V58;"):
            continue
        _, event, *raw_fields = line.strip().split(";")
        fields = {}
        for item in raw_fields:
            name, value = item.split("=", 1)
            fields[name] = Decimal(value.replace(".", "").replace(",", ".") if native else value)
        if fields["data"] != day_code:
            continue
        seq = int(fields["seq"])
        if event == "AVALIACAO":
            if last_seq is not None and seq <= last_seq:
                raise ValueError("Sequência reiniciada. Exporte somente uma execução do dia.")
            last_seq = seq
        elif seq != last_seq:
            raise ValueError("Solicitação sem avaliação correspondente em ordem de console.")
        hhmm = int(fields["hora"])
        label = f"{hhmm//100:02d}:{hhmm%100:02d}"
        grouped[label].append((event, fields))
    if not grouped:
        raise ValueError(f"Nenhuma mensagem V58 para {day}.")
    return grouped


def compare_audit(profit, simulator, labels, layer, tolerances):
    is_evaluation = layer != "solicitacoes"
    first = None
    compared = differing = 0
    for label in sorted(labels):
        left = [event for event in profit.get(label, []) if (event[0] == "AVALIACAO") == is_evaluation]
        right = [event for event in simulator.get(label, []) if (event[0] == "AVALIACAO") == is_evaluation]
        for rank, (p, s) in enumerate(zip_longest(left, right), 1):
            compared += 1
            field = None
            if p is None or s is None or p[0] != s[0]:
                field = "evento"
            else:
                field = next((name for name, tolerance in tolerances.items()
                              if name in p[1] or name in s[1]
                              if name not in p[1] or name not in s[1]
                              or abs(p[1][name] - s[1][name]) > tolerance), None)
            if field:
                differing += 1
                if first is None:
                    def evidence(record):
                        if record is None:
                            return None
                        event, values = record
                        return {"evento": event, "seq": int(values["seq"]), "barra_contexto": int(values["barra"]),
                                "valor": str(values[field]) if field in values else None}
                    first = {"hora_barra_contexto": label, "ordem_na_camada": rank, "campo": field,
                             "profit": evidence(p), "simulador": evidence(s)}
    return {"comparados": compared, "divergentes": differing, "primeira_divergencia": first}


def compare_fills(operations, fills, candles):
    profit = []
    for row in operations.sort_values("numero_operacao").itertuples(index=False):
        entry_side = "long" if row.lado == "C" else "short"
        profit.extend([
            (row.entrada.isoformat(), entry_side, row.quantidade, row.preco_entrada),
            (row.saida.isoformat(), "exit_" + entry_side, row.quantidade, row.preco_saida),
        ])
    profit.sort(key=lambda row: row[0])
    stamps = pd.Series(pd.to_datetime(candles["timestamp"]).array, index=candles["indice"])
    simulator = [(stamps.loc[int(row.barra) - 1].isoformat(), row.acao, row.quantidade, row.preco)
                 for row in fills.itertuples(index=False)]
    first = next(({"ordem": i, "profit": p, "simulador": s}
                  for i, (p, s) in enumerate(zip_longest(profit, simulator), 1) if p != s), None)
    return {"profit": len(profit), "simulador": len(simulator), "primeira_divergencia": first,
            "criterio_empate_profit": "Número da operação e entrada antes da saída; precisão da exportação."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("console-profit", "operacoes-profit", "barras-profit", "barras-preparadas",
                 "console-simulador", "candles-simulador", "execucoes-simulador", "saida"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--aquecimento", type=int, default=63)
    args = parser.parse_args()
    if args.saida.exists():
        parser.error("A saída já existe.")
    capture, copies = unique_native_capture(console_lines(args.console_profit, True))
    profit = audit_by_label(capture, args.data, True)
    motor = audit_by_label(console_lines(args.console_simulador, False), args.data, False)
    if args.aquecimento < 0:
        parser.error("Aquecimento deve ser não negativo.")
    candles = pd.read_csv(args.candles_simulador)
    target = candles.loc[candles["timestamp"].astype(str).str.startswith(args.data)]
    eligible = target.loc[target["barras_no_segmento"] > args.aquecimento]
    labels = set(eligible["timestamp"].astype(str).str[11:16])
    if not labels:
        parser.error("Nenhuma barra elegível.")
    original = target_day(normalize_bars(read_profit(args.barras_profit), "Data"), args.data)
    prepared = target_day(normalize_bars(read_local_bars(args.barras_preparadas), "timestamp"), args.data)
    bars = compare_bar_inputs(original, prepared)
    layers = {
        "sinais": dict.fromkeys(("compra", "venda"), 0),
        "filtros": dict.fromkeys(("regime", "densidade", "aquecido"), 0),
        "indicadores": dict.fromkeys(("vwap", "atr", "media_atr", "desvio_banda", "zvolume",
                                     "media_volume_1", "desvio_volume_1"), Decimal("0.01")),
        "posicao": dict.fromkeys(("posicao", "preco_medio"), 0),
        "estado": dict.fromkeys(("anterior", "pode", "entradas", "pendentes", "zerar"), 0),
        "solicitacoes": dict.fromkeys(("qtd", "gatilho", "limite"), 0),
    }
    profit_fills = profit_round_trips(read_profit_operations(args.operacoes_profit, args.data))
    fills = pd.read_csv(args.execucoes_simulador)
    fills = fills.loc[fills["pregao"] == args.data]
    motor_fills = local_round_trips(fills, candles)
    report = {
        "data": args.data,
        "barras": bars,
        "copias_identicas_console_profit": copies,
        "aquecimento_por_segmento": args.aquecimento,
        "rotulos_elegiveis": len(labels),
        "criterio": "Ordem de emissão da camada no mesmo rótulo de contexto. Execuções usam horários da exportação.",
        "camadas": {layer: compare_audit(profit, motor, labels, layer, fields) for layer, fields in layers.items()},
        "solicitacoes_pregao": compare_audit(profit, motor, set(target["timestamp"].astype(str).str[11:16]),
                                            "solicitacoes", layers["solicitacoes"]),
        "preenchimentos": compare_fills(profit_fills, fills, candles),
        "operacoes": compare_operations(profit_fills, motor_fills),
        "sha256_fontes": {key: sha256(path) for key, path in vars(args).items()
                          if isinstance(path, Path) and key != "saida"},
    }
    with args.saida.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
