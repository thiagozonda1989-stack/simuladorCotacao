"""Reproduz uma variante identificada da v5.7. Entradas e saídas ficam no Windows."""

import argparse
import csv
from dataclasses import fields
from decimal import Decimal, ROUND_HALF_UP
from itertools import zip_longest
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from estrategia import ExecutionRules, load_bars, run_strategy, source_text
from ntsl import compile_ntsl
from tools.preparar_paridade_profit_barras import digest


def configuration(config):
    required = (
        "modo_profit", "inicio", "fim", "quantidade_painel", "quantidade_maxima",
        "executar_nos_limites", "inputs_profit", "regras_ohlc",
        "origem_agressao", "origem_vwap", "fontes_sha256",
    )
    missing = [key for key in required if config.get(key) is None]
    if missing:
        raise ValueError("Faltam dados da variação: " + ", ".join(missing))
    if config["modo_profit"] != "OHLC":
        raise ValueError("Este roteiro usa OHLC. Uma referência Tick a Tick requer os eventos nativos.")
    if config["ativo"] != "WINZ26" or config["periodo_segundos"] != 60:
        raise ValueError("A variação alvo usa WINZ26 em 1 minuto.")
    start, end = (pd.Timestamp(config[key]).date() for key in ("inicio", "fim"))
    if start > end:
        raise ValueError("Intervalo da variação invertido.")
    rules = config["regras_ohlc"]
    if set(rules) != {field.name for field in fields(ExecutionRules)}:
        raise ValueError("Declare todos os campos de ExecutionRules no perfil congelado.")
    if rules["motor_ticks"] or not rules["rastrear_ordens"]:
        raise ValueError("Use OHLC e habilite o rastreamento de ordens.")
    ExecutionRules(**rules)
    maximum = config["quantidade_maxima"]
    quantity = config["quantidade_painel"]
    if type(maximum) is not int or type(quantity) is not int or not 0 < quantity <= maximum:
        raise ValueError("Quantidade e máximo do painel devem ser inteiros positivos e compatíveis.")
    if type(config["executar_nos_limites"]) is not bool:
        raise ValueError("Registre o valor de Executar nos Limites visto no Profit.")
    if config["tick_pontos"] != 5:
        raise ValueError("Confirme a grade WINZ26 de 5 pontos.")
    return start, end


def money(value):
    return Decimal(value.replace(".", "").replace(",", "."))


def native_trades(path):
    raw = path.read_bytes()
    try:
        contents = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        contents = raw.decode("cp1252")
    rows = iter(csv.reader(contents.splitlines(), delimiter=";"))
    header = next((r for r in rows if r and r[0] == "Ativo"), [])
    names = ("Ativo", "Abertura", "Fechamento", "Lado", "Qtd Compra", "Qtd Venda",
             "Preço Compra", "Preço Venda", "Res. Operação", "Comissões")
    if not set(names) <= set(header):
        raise ValueError("CSV de operações sem ativo, horários, lado, quantidades, preços, resultado ou comissões.")
    trades = []
    for row in rows:
        if not any(row):
            continue
        if len(row) != len(header):
            raise ValueError("CSV de operações contém linha incompleta.")
        rec = dict(zip(header, row))
        if rec["Ativo"] != "WINZ26" or rec["Lado"] not in {"C", "V"}:
            raise ValueError("Operação com ativo ou lado inesperado.")
        qty_buy, qty_sell = (int(rec[name]) for name in ("Qtd Compra", "Qtd Venda"))
        if qty_buy <= 0 or qty_buy != qty_sell:
            raise ValueError("Quantidades de abertura e fechamento incompatíveis.")
        buy = rec["Lado"] == "C"
        prices = [money(rec[name]) for name in ("Preço Compra", "Preço Venda")]
        entry, exit_ = prices if buy else prices[::-1]
        open_, close = (pd.to_datetime(rec[name], dayfirst=True) for name in ("Abertura", "Fechamento"))
        gross = (prices[1] - prices[0]) * qty_buy * Decimal("0.20")
        commission = money(rec["Comissões"])
        operation = money(rec["Res. Operação"])
        if commission < 0 or operation not in {gross, gross - commission} or close < open_:
            raise ValueError("Horários ou convenção de resultado/comissão do Profit precisam ser auditados.")
        trades.append({
            "identidade": (open_, close, rec["Lado"], qty_buy, entry, exit_),
            "bruto": gross, "liquido": gross - commission, "causa": "não identificada",
        })
    return trades


def metrics(trades):
    net = [row["liquido"] for row in trades]
    gross = [row["bruto"] for row in trades]
    gain = sum((value for value in gross if value > 0), Decimal(0))
    loss = -sum((value for value in gross if value < 0), Decimal(0))
    equity = high = drawdown = Decimal(0)
    duration = []
    for row in sorted(trades, key=lambda row: row["identidade"][1]):
        entry, exit_, *_ = row["identidade"]
        duration.append((exit_ - entry).total_seconds())
        equity += row["liquido"]
        high = max(high, equity)
        drawdown = max(drawdown, high - equity)
    return {
        "operacoes": len(trades), "liquido_reais": format(sum(net), ".2f"),
        "fator_lucro_bruto": str((gain / loss).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if loss else None,
        "acertos": sum(value > 0 for value in net),
        "taxa_acerto": sum(value > 0 for value in net) / len(trades) if trades else None,
        "drawdown_realizado_reais": format(drawdown, ".2f"),
        "duracao_mediana_s": float(pd.Series(duration).median()) if duration else None,
        "duracao_p90_s": float(pd.Series(duration).quantile(0.90)) if duration else None,
    }


def from_fills(output):
    bars = pd.read_csv(output / "candles.csv", usecols=["timestamp"])
    fills = pd.read_csv(output / "execucoes.csv")
    entry = None
    trades = []
    for row in fills.itertuples(index=False):
        stamp = pd.Timestamp(bars["timestamp"].iloc[row.barra - 1]).tz_localize(None)
        price = Decimal(str(row.preco))
        if row.acao in {"long", "short"} and entry is None and abs(row.posicao) == row.quantidade:
            entry = stamp, ("C" if row.acao == "long" else "V"), row.quantidade, price, row.custo_reais
        elif row.acao.startswith("exit") and entry and row.posicao == 0 and row.quantidade == entry[2]:
            start, side, qty, opening, cost = entry
            if row.acao != ("exit_long" if side == "C" else "exit_short"):
                raise ValueError("Saída incompatível com a posição registrada.")
            gross = Decimal(str(row.pontos_contrato)) * Decimal("0.20")
            trades.append({
                "identidade": (start, stamp, side, qty, opening, price),
                "bruto": gross, "liquido": gross - Decimal(str(cost)) - Decimal(str(row.custo_reais)),
                "causa": {"limit": "alvo", "stop": "stop-limit"}.get(row.tipo, "não identificada"),
            })
            entry = None
        else:
            raise ValueError("Pareamento automático requer uma entrada e uma saída integrais por operação.")
    if entry is not None:
        raise ValueError("Posição residual. Confira o encerramento no Profit antes de usar o pareamento.")
    return trades


def aggregate(trades, sessions):
    def bucket(key):
        return {name: metrics([row for row in trades if key(row) == name])
                for name in sorted({key(row) for row in trades})}

    return {
        "total": metrics(trades),
        "pregoes_na_amostra": len(sessions),
        "operacoes_por_pregao": len(trades) / len(sessions),
        "por_pregao_saida": {day: metrics([row for row in trades
                                         if row["identidade"][1].date().isoformat() == day])
                             for day in sessions},
        "por_lado": bucket(lambda row: row["identidade"][2]),
        "por_causa": bucket(lambda row: row["causa"]),
        "por_regime": {"não identificado": metrics(trades)},
    }


def first_difference(native, local):
    pairs = (sorted(rows, key=lambda row: row["identidade"][0]) for rows in (native, local))
    keys = ("hora_entrada", "hora_saida", "lado", "quantidade", "preco_entrada", "preco_saida")
    for index, (profit, sim) in enumerate(zip_longest(*pairs), 1):
        if profit is None or sim is None:
            return {"operacao": index, "campos": ["operação ausente"]}
        differences = [key for key, left, right in zip(keys, profit["identidade"], sim["identidade"]) if left != right]
        if differences:
            return {"operacao": index, "campos": differences}
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("config", "variacao", "operacoes", "barras", "ntsl", "saida-privada"):
        parser.add_argument("--" + arg, type=Path, required=arg == "config")
    args = parser.parse_args()
    try:
        run(args)
    except (KeyError, TypeError, ValueError, OSError) as error:
        parser.exit(2, f"Erro: {error}\n")


def run(args):
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    start, end = configuration(config)
    for key in ("variacao", "operacoes", "barras", "ntsl"):
        path = getattr(args, key)
        if path is None or digest(path) != config["fontes_sha256"].get(key):
            raise ValueError(f"Fonte {key} ausente ou com SHA-256 diferente do congelado.")
    if args.saida_privada is None:
        raise ValueError("Indique uma pasta de saída nova e privada.")
    source = source_text(args.ntsl)
    inputs = {key.lower(): value for key, value in config["inputs_profit"].items()}
    if set(inputs) != set(compile_ntsl(source).inputs) or inputs["p_lote"] > config["quantidade_maxima"]:
        raise ValueError("Confirme todos os inputs e confira p_Lote contra o máximo do Profit.")
    native = native_trades(args.operacoes)
    summary = metrics(native)
    if (summary["operacoes"], Decimal(summary["liquido_reais"]), summary["fator_lucro_bruto"]) != (
        43, Decimal("5745"), "2.22"
    ):
        raise ValueError("CSV não reproduz a assinatura nativa de 43 operações, R$ 5.745 e fator 2,22.")
    if any(not (start <= row["identidade"][0].date() <= row["identidade"][1].date() <= end) for row in native):
        raise ValueError("Exportação de operações contém registros fora da janela confirmada.")
    observed_qty = {row["identidade"][3] for row in native}
    if observed_qty != {inputs["p_lote"]}:
        raise ValueError("Execuções não têm o lote integral solicitado. Audite o limite ou os preenchimentos parciais.")
    bars = load_bars(args.barras, 60, "ohlc")
    columns = {"v_trades_atual", "volume_financeiro", "volume_contratos", "v_vwap_barra"}
    rules = config["regras_ohlc"]
    if rules["agressao_referencia_injetada"]:
        columns.add("v_agressao_saldo_referencia")
    elif "v_agressao_saldo_acumulado" not in bars:
        columns.update(("v_agressao_compra", "v_agressao_venda"))
    if not columns <= set(bars) or bars[sorted(columns)].isna().any().any():
        raise ValueError("Candles preparados sem a série completa de Trades, volumes, VWAP por barra ou agressão.")
    sessions = sorted(bars["pregao"].unique())
    required_days = {row["identidade"][0].date().isoformat() for row in native} | {
        row["identidade"][1].date().isoformat() for row in native
    }
    if not sessions or not required_days <= set(sessions) or sessions[0] < start.isoformat() or sessions[-1] > end.isoformat():
        raise ValueError("Candles fora da janela ou sem pregão de uma execução. Use o mesmo histórico do Backtest.")
    out = args.saida_privada.resolve()
    repo = Path(__file__).resolve().parents[1]
    if out.is_relative_to(repo):
        raise ValueError("A pasta de saída privada deve ficar fora do repositório.")
    out.mkdir(parents=True)
    original = out / "lote_original"
    run_strategy(args.barras, source, original, 60, "ohlc", config["tick_pontos"], inputs, 0.20, regras=rules)
    local = from_fills(original)
    difference = first_difference(native, local)
    result = {"origem_agressao": config["origem_agressao"], "origem_vwap": config["origem_vwap"],
              "profit": aggregate(native, sessions), "simulador": aggregate(local, sessions),
              "primeira_divergencia_preenchimentos": difference, "simulador_2_contratos": None}
    if difference is None and metrics(native) == metrics(local) and config["quantidade_maxima"] >= 2:
        alternative = out / "dois_contratos"
        run_strategy(args.barras, source, alternative, 60, "ohlc", config["tick_pontos"],
                     inputs | {"p_lote": 2}, 0.20, regras=rules)
        result["simulador_2_contratos"] = aggregate(from_fills(alternative), sessions)
    (out / "agregados.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
