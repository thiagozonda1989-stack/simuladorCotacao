"""Audita toques nas proteções elegíveis da v5.8 e a cobertura de Negócios."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.comparar_paridade_profit_win import (
    local_round_trips, profit_round_trips, read_profit_operations, sha256,
)


class ProtectionAudit(Engine):
    def run(self):
        self.protected = []
        super().run(record_trace=False)

    def process_orders(self, only_keys=None):
        exit_action = "exit_long" if self.position > 0 else "exit_short"
        eligible = [order for key, order in self.orders.items()
                    if (only_keys is None or key in only_keys) and order.eligible_at <= self.row
                    and self.position and order.action == exit_action]
        stops = [order for order in eligible if order.kind == "stop" and not order.triggered]
        targets = [order for order in eligible if order.kind == "limit"]
        if len(stops) == len(targets) == 1:
            self.protected.append((self.row, self.position, self.basis, targets[0].price,
                                   stops[0].price, stops[0].limit))
        super().process_orders(only_keys)


def trade_minutes(path, minutes):
    prefixes = {pd.Timestamp(minute).strftime("%d/%m/%Y %H:%M").encode("ascii") for minute in minutes}
    data = defaultdict(list)
    if not prefixes:
        return data
    with path.open("rb") as stream:
        for line in stream:
            # Captura ProfitRTD delimitada por ponto e vírgula, com aspas.
            parts = line.split(b'";"', 6)
            if len(parts) < 7 or parts[2][:16] not in prefixes:
                continue
            seq, _, stamp, _, price, qty, _ = parts
            ts = datetime.strptime(stamp.decode("ascii"), "%d/%m/%Y %H:%M:%S.%f")
            data[ts.replace(second=0, microsecond=0)].append(
                (ts, int(seq.lstrip(b'"')), float(price.replace(b",", b".")), int(qty)))
    return data


def describe_trade_minute(rows, bar, side, entry, target, stop, limit):
    inversions = sum(left[0] > right[0] for left, right in zip(rows, rows[1:]))
    rows = sorted(rows, key=lambda row: (row[0], row[1]))
    if not rows:
        return {"negocios": 0, "primeiro_limiar_observado": "sem_dados"}
    times = Counter(row[0] for row in rows)
    prices = [row[2] for row in rows]
    ohlc = [prices[0], max(prices), min(prices), prices[-1]]
    wanted = [bar.abertura, bar.maxima, bar.minima, bar.fechamento]
    target_hit = lambda price: (price - target) * side >= 0
    stop_hit = lambda price: (price - stop) * side <= 0
    limit_hit = lambda price: limit is not None and (price - limit) * side <= 0
    first = {name: next((row for row in rows if match(row[2])), None) for name, match in (
        ("preco_entrada", lambda price: price == entry), ("alvo", target_hit),
        ("gatilho_stop", stop_hit), ("limite_stop", limit_hit),
        ("preco_exato_alvo", lambda price: price == target),
        ("preco_exato_gatilho", lambda price: price == stop),
    )}
    a, s = first["alvo"], first["gatilho_stop"]
    if not a or not s:
        order = "um_ou_ambos_ausentes"
    else:
        order = "empate_ms" if a[0] == s[0] else "alvo" if a[0] < s[0] else "gatilho_stop"
    time_gaps = [(b, round((b - a).total_seconds() * 1000)) for a, b in zip(times, list(times)[1:])]
    return {
        "negocios": len(rows), "contratos": sum(row[3] for row in rows),
        "trades_profit": int(bar.v_trades_atual), "quantity_profit": int(bar.volume_contratos),
        "inicio": rows[0][0].time().isoformat(timespec="milliseconds"),
        "fim": rows[-1][0].time().isoformat(timespec="milliseconds"),
        "ms_com_empate": sum(count > 1 for count in times.values()),
        "ms_distintos": len(times),
        "sequencias_repetidas": len(rows) - len({row[1] for row in rows}),
        "inversoes_temporais_ordem_fisica": inversions,
        "segundos_com_negocios": len({stamp.second for stamp in times}),
        "maior_intervalo_ms": max((gap for _, gap in time_gaps), default=0),
        "maior_intervalo_ate_o_primeiro_alvo_ms": (
            max((gap for stamp, gap in time_gaps if stamp <= a[0]), default=0) if a else None
        ),
        "delta_ohlc": [observed - reference for observed, reference in zip(ohlc, wanted)],
        "primeiro_limiar_observado": order,
        "primeiros": {name: {"hora": row[0].time().isoformat(timespec="milliseconds"),
                             "sequencia_captura": row[1], "negocios_no_ms": times[row[0]],
                             "preco_relativo": row[2] - entry}
                      if row else None for name, row in first.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("barras", "ntsl", "inputs", "negocios", "operacoes-profit", "saida"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()
    day = args.data
    bars = load_bars(args.barras, 60, "ohlc")
    rules = dict(avaliacao_pos_preenchimento=True, historico_continuo_lacunas=True,
                 vwap_continuo_lacunas=True, volume_financeiro_ntsl=True,
                 agressao_referencia_injetada=True)
    code = compile_ntsl(source_text(args.ntsl))
    engine = ProtectionAudit(code, bars, 5, json.loads(args.inputs.read_text(encoding="utf-8")),
                             60, 0.2, regras=rules)
    engine.run()
    fills = pd.DataFrame(engine.fills, columns=["pregao", "barra", "acao", "quantidade", "preco"])
    fills = fills.loc[fills["pregao"].eq(day)]
    sim = local_round_trips(fills, bars.rename_axis("indice").reset_index())
    profit = profit_round_trips(read_profit_operations(args.operacoes_profit, day))
    fields = ["entrada", "saida", "lado", "quantidade", "preco_entrada"]
    pairs = profit.merge(sim, on=fields, suffixes=("_profit", "_sim"), validate="one_to_one")
    candidates = []
    stamps = pd.to_datetime(bars["timestamp"])
    have_protections = set()
    protected_bars = set()
    for row, position, basis, target, stop, limit in engine.protected:
        ts = stamps.iloc[row]
        side = "C" if position > 0 else "V"
        match = pairs.loc[(pairs["entrada"] <= ts) & (pairs["saida"] >= ts)
                          & pairs["preco_entrada"].eq(basis) & pairs["lado"].eq(side)
                          & pairs["quantidade"].eq(abs(position))]
        if len(match) != 1:
            continue
        number = int(match.iloc[0].numero_operacao)
        have_protections.add(number)
        protected_bars.add(row)
        bar = bars.iloc[row]
        both = (bar.maxima >= target and bar.minima <= stop if position > 0
                else bar.minima <= target and bar.maxima >= stop)
        if both:
            candidates.append((row, number, position, basis, target, stop, limit))
    data = trade_minutes(args.negocios, {stamps.iloc[row] for row, *_ in candidates})
    results = []
    for row, number, position, basis, target, stop, limit in candidates:
        ts = stamps.iloc[row]
        report = describe_trade_minute(data[ts.tz_localize(None)], bars.iloc[row],
                                       1 if position > 0 else -1, basis, target, stop, limit)
        match = pairs.loc[pairs.numero_operacao.eq(number)].iloc[0]
        results.append({
            "hora_barra": ts.strftime("%H:%M"), "hora_entrada_exportacao": match.entrada.strftime("%H:%M"),
            "hora_saida_exportacao": match.saida.strftime("%H:%M"),
            "lado": match.lado, "quantidade": abs(position),
            "alvo_relativo": target - basis, "gatilho_relativo": stop - basis,
            "limite_relativo": None if limit is None else limit - basis,
            "saida_profit_relativa": match.preco_saida_profit - basis,
            "saida_simulador_relativa": match.preco_saida_sim - basis,
            **report,
        })
    with args.saida.open("x", encoding="utf-8") as output:
        json.dump({"pregao": day, "negocios_sha256": sha256(args.negocios),
                   "operacoes_profit": len(profit), "operacoes_replay": len(sim),
                   "pares_mesmos_horarios_entrada_saida_e_preco_entrada": len(pairs),
                   "operacoes_com_protecao_elegivel": len(have_protections),
                   "barras_com_protecao_elegivel": len(protected_bars),
                   "barras_duplo_toque": len({row for row, *_ in candidates}), "casos": results},
                  output, indent=2, ensure_ascii=False)
        output.write("\n")


if __name__ == "__main__":
    main()
