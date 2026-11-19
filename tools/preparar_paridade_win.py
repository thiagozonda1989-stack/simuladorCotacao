"""Converte Negocios WIN brutos em candles privados para a paridade por candle.

O CSV de saida nao deve ser versionado: ele contem precos e volumes do pregao.
O manifesto agregado registra contagens, cobertura e lacunas sem expor negocios.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


USECOLS = ["Sequencia", "Coluna_1", "Coluna_3", "Coluna_4", "Coluna_6"]
BUY = {"Compra", "Comprador", "Agressao Compra", "Agressão Compra"}
SELL = {"Venda", "Vendedor", "Agressao Venda", "Agressão Venda"}


def prepare(path: Path, gap_ms: int = 5_000) -> tuple[pd.DataFrame, dict]:
    if gap_ms < 1:
        raise ValueError("gap_ms deve ser positivo.")
    parts = []
    invalid = 0
    aggressors: dict[str, int] = {}
    for chunk in pd.read_csv(path, sep=";", dtype="string", usecols=USECOLS,
                             chunksize=250_000, encoding="utf-8-sig"):
        stamp = pd.to_datetime(chunk["Coluna_1"], format="%d/%m/%Y %H:%M:%S.%f",
                               errors="coerce")
        price = pd.to_numeric(chunk["Coluna_3"], errors="coerce")
        quantity = pd.to_numeric(chunk["Coluna_4"], errors="coerce")
        sequence = pd.to_numeric(chunk["Sequencia"], errors="coerce")
        valid = (stamp.notna() & price.gt(0) & quantity.gt(0) & sequence.notna()
                 & sequence.ge(0) & sequence.mod(1).eq(0))
        invalid += int((~valid).sum())
        selected = pd.DataFrame({
            "timestamp": stamp[valid],
            "sequencia": sequence[valid].astype("int64"),
            "preco": price[valid].astype("float64"),
            "quantidade": quantity[valid].astype("int64"),
            "agressor": chunk.loc[valid, "Coluna_6"].fillna("").str.strip(),
        })
        counts = selected["agressor"].value_counts()
        for name, count in counts.items():
            aggressors[str(name)] = aggressors.get(str(name), 0) + int(count)
        parts.append(selected)
    if not parts:
        raise ValueError("Fonte sem linhas.")
    trades = pd.concat(parts, ignore_index=True).sort_values(
        ["timestamp", "sequencia"], kind="stable").reset_index(drop=True)
    if trades.empty:
        raise ValueError("Fonte sem negocios validos.")
    if trades.duplicated(["timestamp", "sequencia"]).any():
        raise ValueError("Chave timestamp/sequencia repetida.")

    elapsed_ms = trades["timestamp"].diff().dt.total_seconds().mul(1_000).fillna(0)
    trades["nova_lacuna"] = elapsed_ms.gt(gap_ms)
    trades["segmento"] = trades["nova_lacuna"].cumsum().add(1)
    trades["minuto"] = trades["timestamp"].dt.floor("min")
    trades["financeiro"] = trades["preco"] * trades["quantidade"]
    trades["agressao_compra"] = trades["quantidade"].where(trades["agressor"].isin(BUY), 0)
    trades["agressao_venda"] = trades["quantidade"].where(trades["agressor"].isin(SELL), 0)

    grouped = trades.groupby("minuto", sort=True)
    bars = grouped.agg(
        abertura=("preco", "first"), maxima=("preco", "max"),
        minima=("preco", "min"), fechamento=("preco", "last"),
        volume_contratos=("quantidade", "sum"), financeiro=("financeiro", "sum"),
        v_trades_atual=("preco", "size"),
        v_agressao_compra=("agressao_compra", "sum"),
        v_agressao_venda=("agressao_venda", "sum"),
        segmento=("segmento", "last"), primeira_cotacao=("timestamp", "first"),
        ultima_cotacao=("timestamp", "last"), lacuna_na_barra=("nova_lacuna", "max"),
    ).reset_index().rename(columns={"minuto": "timestamp"})
    bars["v_vwap_barra"] = bars["financeiro"] / bars["volume_contratos"]
    bars = bars.drop(columns="financeiro")
    # Volume no NTSL representa a quantidade negociada no candle.
    bars["volume"] = bars["volume_contratos"]
    bars["intervalo_minutos"] = bars["timestamp"].diff().dt.total_seconds().div(60).fillna(0)
    bars["comparavel_barras"] = (~bars["lacuna_na_barra"] & bars["intervalo_minutos"].isin([0, 1])).astype(int)

    recognized = sum(count for name, count in aggressors.items() if name in BUY | SELL)
    gap_rows = trades.index[trades["nova_lacuna"]]
    gaps = [
        {
            "anterior": trades.loc[index - 1, "timestamp"].isoformat(),
            "posterior": trades.loc[index, "timestamp"].isoformat(),
            "duracao_ms": int(elapsed_ms.loc[index]),
        }
        for index in gap_rows
    ]
    metrics = {
        "schema": "paridade_win_candles_v1",
        "timestamp_barra": "abertura_do_minuto_America/Sao_Paulo",
        "negocios": int(len(trades)), "contratos": int(trades["quantidade"].sum()),
        "barras": int(len(bars)), "inicio": bars.iloc[0]["timestamp"].isoformat(),
        "fim": bars.iloc[-1]["timestamp"].isoformat(), "linhas_invalidas": invalid,
        "maior_lacuna_ms": int(elapsed_ms.max()), "gap_ms": gap_ms,
        "lacunas_maiores_limite": int(elapsed_ms.gt(gap_ms).sum()),
        "barras_afetadas_lacuna": int(bars["lacuna_na_barra"].sum()),
        "minutos_ausentes": int((bars["intervalo_minutos"] - 1).clip(lower=0).sum()),
        "agressores_reconhecidos": int(recognized),
        "agressores_nao_reconhecidos": int(len(trades) - recognized),
        "contagem_agressor": aggressors,
        "lacunas": gaps,
    }
    return bars, metrics


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--lacuna-ms", type=int, default=5_000)
    args = parser.parse_args()
    if args.saida.exists() or args.manifesto.exists():
        parser.error("A saida e o manifesto devem ser caminhos novos.")
    bars, metrics = prepare(args.entrada, args.lacuna_ms)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    bars.to_csv(args.saida, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    metrics.update({"fonte": args.entrada.name, "sha256_fonte": digest(args.entrada),
                    "sha256_saida": digest(args.saida)})
    args.manifesto.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")


if __name__ == "__main__":
    main()
