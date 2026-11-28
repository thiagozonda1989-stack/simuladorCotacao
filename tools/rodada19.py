"""Reproduz os 20 pregões conhecidos e publica somente agregados da rodada 19."""
import argparse
from collections import defaultdict
import csv
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl

EVIDENCE = Path("docs/colaboracao/evidencias/WINZ26_congelamento_rodada19_v1")
MARKET_REASONS = {"horario", "noticia", "duracao_maxima", "bloqueio_diario"}


class DiagnosticEngine(Engine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contexts = []

    def value(self, name):
        return self.values[self.program.symbols[name].slot]

    def place(self, key, order):
        super().place(key, order)
        if self.orders.get(key) is not order or order.kind != "market":
            return
        if order.action in {"long", "short"} and "v_regime_mercado" in self.program.symbols:
            order.diagnostic = {1: "tendencia", 2: "exaustao", 0: "neutro"}[self.value("v_regime_mercado")]
        elif order.action.startswith("exit"):
            if "v_regime_mercado" in self.program.symbols:
                reason = "horario" if not self.value("v_pregao_ativo") else "noticia"
            elif self.frame["hora_ntsl"].iat[self.row] >= self.value("p_horariozeragem"):
                reason = "horario"
            elif self.value("v_bloqueiodiario"):
                reason = "bloqueio_diario"
            elif self.value("v_barrasposicao") >= self.value("p_maxbarrasposicao"):
                reason = "duracao_maxima"
            else:
                raise ValueError("Saída a mercado sem condição identificada.")
            order.diagnostic = reason

    def execute(self, order, price):
        before = len(self.fills)
        super().execute(order, price)
        if len(self.fills) > before:
            self.contexts.append(getattr(order, "diagnostic", None))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def operations(engine, frame, lot):
    entry = None
    trades = []
    for fill, context in zip(engine.fills, engine.contexts, strict=True):
        moment = frame["timestamp"].iat[fill["barra"] - 1]
        if fill["quantidade"] != lot:
            raise ValueError("Lote preenchido diverge do congelamento.")
        if fill["acao"] in {"long", "short"}:
            if entry is not None or abs(fill["posicao"]) != lot:
                raise ValueError("Entrada com posição acumulada.")
            entry = (fill, moment, context or "indisponivel")
            continue
        if entry is None or fill["posicao"] != 0:
            raise ValueError("Saída sem entrada correspondente ou posição residual.")
        opening, started, regime = entry
        if opening["pregao"] != fill["pregao"]:
            raise ValueError("A operação atravessou a troca de pregão.")
        reason = {"limit": "alvo", "stop": "stop_limit"}.get(fill["tipo"])
        if fill["ordem"] == "fim_pregao":
            reason = "fim_pregao_motor"
        elif fill["tipo"] == "market" and context in MARKET_REASONS:
            reason = context
        if reason is None:
            raise ValueError("Motivo não identificado.")
        trades.append(dict(
            pregao=fill["pregao"], hora_entrada=f"{started.hour:02d}:00",
            hora_saida=f"{moment.hour:02d}:00",
            direcao="compra" if opening["acao"] == "long" else "venda",
            regime_entrada=regime, motivo_saida=reason,
            chave=(started, opening["acao"], lot, opening["preco"]),
            centavos=round((opening["liquido_reais"] + fill["liquido_reais"]) * 100),
            segundos=(moment - started).total_seconds(),
        ))
        entry = None
    if entry is not None:
        raise ValueError("Posição não encerrada.")
    return trades


def totals(trades):
    cents = [t["centavos"] for t in trades]
    count = len(cents)
    gain = sum(n for n in cents if n > 0)
    loss = -sum(n for n in cents if n < 0)
    equity = np.r_[0, np.cumsum(cents)]
    times = [t["segundos"] for t in trades]
    return dict(
        operacoes=count, acertos=sum(n > 0 for n in cents), liquido=sum(cents) / 100,
        media_operacao=round(sum(cents) / (100 * count), 5) if count else None,
        fator_lucro_liquido=round(gain / loss, 5) if loss else None,
        drawdown_max=float((np.maximum.accumulate(equity) - equity).max()) / 100,
        duracao_mediana_s=float(np.median(times)) if count else None,
        duracao_p90_s=float(np.percentile(times, 90)) if count else None,
    )


def group_by(trades, key):
    groups = defaultdict(list)
    for trade in trades:
        groups[key(trade)].append(trade)
    return groups


def composition(trades):
    return group_by(trades, lambda t: (t["hora_entrada"], t["direcao"], t["regime_entrada"]))


def decompose(original, optimized):
    def net(trades):
        return sum(t["centavos"] for t in trades)

    n0, n1 = len(original), len(optimized)
    mean0, mean1 = Fraction(net(original), n0), Fraction(net(optimized), n1)
    frequency = (n1 - n0) * (mean0 + mean1) / 2
    scale = Fraction(n0 + n1, 2)
    g0, g1 = composition(original), composition(optimized)
    mix = within = Fraction(0)
    cells = []
    for hour, side, regime in sorted(g0.keys() | g1.keys()):
        key = (hour, side, regime)
        a, b = g0[key], g1[key]
        mean_a, mean_b = (Fraction(net(items), len(items)) if items else None for items in (a, b))
        share_a, share_b = Fraction(len(a), n0), Fraction(len(b), n1)
        # Sem média observada em um perfil, toda a contribuição da célula é composição.
        imputed_a = mean_b if mean_a is None else mean_a
        imputed_b = mean_a if mean_b is None else mean_b
        mix += scale * (share_b - share_a) * (imputed_a + imputed_b) / 2
        within += scale * (share_a + share_b) * (imputed_b - imputed_a) / 2
        cells.append(dict(hora_entrada=hour, direcao=side, regime_entrada=regime,
                          n_original=len(a), n_otimizado=len(b),
                          liquido_original=net(a) / 100, liquido_otimizado=net(b) / 100))
    delta = net(optimized) - net(original)
    assert frequency + mix + within == delta

    p0 = {t["chave"]: t["centavos"] for t in original}
    p1 = {t["chave"]: t["centavos"] for t in optimized}
    if len(p0) != n0 or len(p1) != n1:
        raise ValueError("Identidade de entrada não é única para o pareamento.")
    paired = p0.keys() & p1.keys()
    only0, only1 = p0.keys() - p1.keys(), p1.keys() - p0.keys()
    delta_pairs = sum(p1[k] - p0[k] for k in paired)
    net_only0, net_only1 = sum(p0[k] for k in only0), sum(p1[k] for k in only1)
    assert delta_pairs + net_only1 - net_only0 == delta
    return dict(
        delta_reais=delta / 100,
        frequencia_reais=round(float(frequency / 100), 2),
        composicao_reais=round(float(mix / 100), 2),
        resultado_dentro_dos_grupos_reais=round(float(within / 100), 2),
        pareadas=len(paired), delta_pareadas_reais=delta_pairs / 100,
        exclusivas_original=len(only0), liquido_exclusivas_original=net_only0 / 100,
        exclusivas_otimizada=len(only1), liquido_exclusivas_otimizada=net_only1 / 100,
        grupos=cells,
    )


def profile_results(profile, frame, config):
    source = Path(profile["arquivo"])
    if digest(source) != profile["sha256"]:
        raise ValueError(f"Fonte alterada: {source.name}")
    program = compile_ntsl(source_text(source))
    parameters = profile["parametros"]
    lot = config["lote"]
    if set(parameters) != set(program.inputs) or parameters["p_lote"] != lot:
        raise ValueError("O congelamento deve declarar todos os parâmetros e o lote.")
    args = (program, frame, config["tick_pontos"], parameters,
            config["segundos"], config["reais_por_ponto_contrato"])
    plain = Engine(*args, regras=config["regras_execucao"])
    plain.run(record_trace=False)
    traced = DiagnosticEngine(*args, regras=config["regras_execucao"])
    traced.run(record_trace=False)
    if plain.fills != traced.fills or plain.ambiguities != traced.ambiguities:
        raise ValueError("A instrumentação alterou o replay.")
    return operations(traced, frame, lot), traced.ambiguities


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    config = read_json(EVIDENCE / "perfis.json")
    if digest(args.base) != config["base_sha256"]:
        raise ValueError("SHA-256 do arquivo não corresponde à base privada congelada.")
    days = config["pregoes_conhecidos"]
    frame = load_bars(args.base, config["segundos"], "ohlc")
    frame = frame.loc[frame.pregao.isin(days)].reset_index(drop=True)
    if frame.pregao.unique().tolist() != days or len(days) != 20:
        raise ValueError("O replay exige os mesmos 20 pregões conhecidos.")
    args.saida.mkdir(parents=True, exist_ok=True)
    summary, matrix, all_trades = {}, [], {}
    cuts = ("pregao", "hora_entrada", "hora_saida", "direcao", "regime_entrada", "motivo_saida")
    for name, profile in config["perfis"].items():
        trades, ambiguous = profile_results(profile, frame, config)
        all_trades[name] = trades
        by_day = {}
        for field in cuts:
            groups = group_by(trades, lambda trade: trade[field])
            denominations = days if field == "pregao" else sorted(groups)
            for denomination in denominations:
                values = totals(groups[denomination])
                matrix.append(dict(perfil=name, recorte=field, grupo=denomination, **values))
                if field == "pregao":
                    by_day[denomination] = values
        best = max(days, key=lambda day: by_day[day]["liquido"])
        remaining = totals([t for t in trades if t["pregao"] != best])
        summary[name] = dict(
            **totals(trades), pregoes=len(days), barras=len(frame),
            operacoes_por_pregao=len(trades) / len(days),
            liquido_por_pregao=round(totals(trades)["liquido"] / len(days), 2),
            pior_pregao=min(day["liquido"] for day in by_day.values()),
            ambiguidades_ohlc=ambiguous, pregoes_meta_3000=sum(day["liquido"] >= 3000 for day in by_day.values()),
            melhor_pregao=best, liquido_melhor_pregao=by_day[best]["liquido"],
            sem_melhor_pregao=remaining, liquido_por_pregao_sem_melhor=round(remaining["liquido"] / (len(days) - 1), 2),
        )
        expected = profile["referencia_rodada18"]
        for key in ("operacoes", "acertos", "liquido", "drawdown_max", "barras"):
            if summary[name][key] != expected[key]:
                raise ValueError(f"{name} divergiu da rodada 18 em {key}.")
    result = dict(sha_executado=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  resumo=summary, diagnostico_v58=decompose(all_trades["v58_original"], all_trades["v58_otimizada_diagnostico"]))
    with (args.saida / "agregados.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(matrix[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(matrix)
    (args.saida / "resultado.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
