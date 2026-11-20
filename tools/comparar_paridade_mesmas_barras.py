"""Compara Profit e motor usando exatamente as barras exportadas do Profit.

Gera somente agregado reproduzivel. Os CSVs privados permanecem fora do Git.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from tools.comparar_paridade_profit_win import (
        compare_bars, compare_operations, first_difference, local_round_trips,
        normalize_bars, profit_round_trips, read_local_bars, read_profit,
        read_profit_operations, sha256, target_day,
    )
except ModuleNotFoundError:  # execucao direta: python tools/<script>.py
    from comparar_paridade_profit_win import (
        compare_bars, compare_operations, first_difference, local_round_trips,
        normalize_bars, profit_round_trips, read_local_bars, read_profit,
        read_profit_operations, sha256, target_day,
    )


PLOTS = {
    "v_VWAP_Diaria": ("plot", "vwap", 0.01),
    "v_Desvio_Padrao": ("plot2", "desvio", 0.01),
    "v_ATR": ("plot3", "atr", 0.01),
    "v_Media_ATR": ("plot4", "media_atr", 0.01),
    "v_Saldo_Agressao": ("plot5", "agressao", 0.0),
    "v_Volume_ZScore": ("plot6", "zscore_volume", 0.01),
    "v_Regime_Mercado": ("plot7", "regime", 0.0),
    "v_Sinal": ("plot8", "sinal_candidato", 0.0),
}


def compare_same_bars(profit: pd.DataFrame, prepared: pd.DataFrame) -> dict:
    prepared = prepared.copy()
    prepared["trades"] = prepared["v_trades_atual"]
    prepared["quantity"] = prepared["volume_contratos"]
    result, common = compare_bars(profit, prepared)
    delta = (pd.to_numeric(common["volume_financeiro_profit"]) -
             pd.to_numeric(common["volume_financeiro_local"])).abs()
    result["campos"]["Volume_financeiro"] = {
        "iguais": int((delta == 0).sum()), "diferentes": int((delta != 0).sum()),
        "max_diferenca_absoluta": float(delta.max()),
        "primeira_divergencia": first_difference(
            common, "volume_financeiro_profit", "volume_financeiro_local"),
        "unidade": "R$; nao usada como Quantity",
    }
    return result


def compare_engine_indicators(profit: pd.DataFrame, engine: pd.DataFrame,
                              warmup: int) -> tuple[dict, pd.DataFrame]:
    joined = profit.merge(engine, on="timestamp", how="inner", suffixes=("_profit", "_motor"))
    # Aquecimento significa excluir as primeiras N barras; a primeira barra
    # comparada e N+1. Isso evita tratar a ultima barra de warmup como evidencia.
    comparable = joined.iloc[warmup:].copy()
    fields = {}
    for source, (plot, label, tolerance) in PLOTS.items():
        delta = (pd.to_numeric(comparable[source]) - pd.to_numeric(comparable[plot])).abs()
        fields[label] = {
            "tolerancia": tolerance, "comparados": int(len(comparable)),
            "dentro_tolerancia": int((delta <= tolerance).sum()),
            "fora_tolerancia": int((delta > tolerance).sum()),
            "mediana_diferenca_absoluta": float(delta.median()),
            "max_diferenca_absoluta": float(delta.max()),
            "primeira_divergencia": first_difference(comparable, source, plot, tolerance),
        }
    return {
        "aquecimento_excluido_barras": warmup,
        "primeira_barra_comparada": comparable.timestamp.min().isoformat(),
        "barras_comparadas": int(len(comparable)),
        "rolling_local": "nao usado; permanece apenas diagnostico auxiliar",
        "campos": fields,
        "vwap": "aproximada a partir de Volume/(Quantity*0,20)",
        "agressao": "referencia do plot Profit injetada; rodada diagnostica",
        "volume_zscore": "Volume financeiro exportado pelo Profit",
    }, comparable


def signal_and_order_summary(comparable: pd.DataFrame, execution: pd.DataFrame) -> dict:
    candidates = comparable[["timestamp", "v_Sinal", "plot8"]].copy()
    order_rows = execution[(execution["sinal_compra"].astype(bool)) |
                           (execution["sinal_venda"].astype(bool))].copy()
    first_order = None
    if len(order_rows):
        row = order_rows.iloc[0]
        first_order = {
            "timestamp": row.timestamp.isoformat(),
            "lado": "C" if bool(row.sinal_compra) else "V",
        }
    return {
        "candidatos_profit": {
            str(int(key)): int(value) for key, value in
            candidates["v_Sinal"].value_counts().sort_index().items()
        },
        "candidatos_motor": {
            str(int(key)): int(value) for key, value in
            candidates["plot8"].value_counts().sort_index().items()
        },
        "primeira_divergencia_candidato": first_difference(
            candidates, "v_Sinal", "plot8"),
        "ordens_entrada_emitidas_motor": int(len(order_rows)),
        "primeira_ordem_entrada_motor": first_order,
        "ordens_profit": "historico nativo indisponivel; nao comparavel",
        "nota": "candidato (plot8) e separado da chamada de ordem (sinal_compra/sinal_venda)",
    }


def build(args: argparse.Namespace) -> dict:
    profit_bars = target_day(normalize_bars(
        read_profit(args.profit_barras), "timestamp", "Profit barras"), args.data)
    prepared = target_day(normalize_bars(
        read_local_bars(args.barras_preparadas), "timestamp", "barras preparadas"), args.data)
    profit_indicators = target_day(normalize_bars(
        read_profit(args.profit_indicadores), "timestamp", "Profit indicadores"), args.data)
    engine_indicators = target_day(normalize_bars(
        pd.read_csv(args.motor_indicadores), "timestamp", "motor indicadores"), args.data)
    engine_execution = target_day(normalize_bars(
        pd.read_csv(args.motor_candles), "timestamp", "motor execucao"), args.data)
    bars = compare_same_bars(profit_bars, prepared)
    indicators, comparable = compare_engine_indicators(
        profit_indicators, engine_indicators, args.aquecimento)

    profit_operations = profit_round_trips(read_profit_operations(args.profit_operacoes, args.data))
    fills = pd.read_csv(args.motor_execucoes)
    motor_operations = local_round_trips(fills, engine_execution)
    operations = compare_operations(profit_operations, motor_operations)
    operations.update({
        "primeira_divergencia_em_trecho_comparavel":
            operations["primeira_operacao_profit_sem_correspondencia"],
        "posicao": (
            "derivada das execucoes; coincide se todas as viagens de ida e volta coincidem"
            if operations["sem_correspondencia_profit"] == 0 and
               operations["sem_correspondencia_local"] == 0
            else "derivada; divergente"
        ),
    })
    sources = {
        "profit_barras": args.profit_barras,
        "profit_indicadores": args.profit_indicadores,
        "profit_operacoes": args.profit_operacoes,
        "barras_preparadas_privadas": args.barras_preparadas,
        "motor_indicadores": args.motor_indicadores,
        "motor_candles": args.motor_candles,
        "motor_execucoes": args.motor_execucoes,
    }
    return {
        "schema": "paridade_mesmas_barras_v1", "data": args.data,
        "recorte": "WINZ26; 1 minuto fechado; abertura America/Sao_Paulo; v5.7; 1 contrato",
        "fontes": {name: {"arquivo": path.name, "sha256": sha256(path)}
                    for name, path in sources.items()},
        "barras": bars, "indicadores": indicators,
        "sinais_e_ordens": signal_and_order_summary(comparable, engine_execution),
        "preenchimentos_e_posicao": operations,
        "conclusao_primeira_divergencia": (
            "nenhuma divergencia verificavel apos o aquecimento; camada de ordens Profit indisponivel"
            if all(value["primeira_divergencia"] is None
                   for value in indicators["campos"].values()) and
               operations["sem_correspondencia_profit"] == 0 and
               operations["sem_correspondencia_local"] == 0
            else "consultar primeira_divergencia por camada"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("profit_barras", "profit_indicadores", "profit_operacoes",
                 "barras_preparadas", "motor_indicadores", "motor_candles",
                 "motor_execucoes"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--data", default="2026-10-21")
    parser.add_argument("--aquecimento", type=int, default=63)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    if args.saida.exists():
        parser.error(f"Saida ja existe; preservada: {args.saida}")
    report = build(args)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saida": str(args.saida),
                      "conclusao": report["conclusao_primeira_divergencia"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
