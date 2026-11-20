"""Compara, sem alterar as fontes, exportacoes Profit e replay local WIN.

O artefato gerado contem somente contagens, metricas e primeiras divergencias.
Os CSVs de origem continuam privados e sao identificados por nome e SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


PRICE = ("abertura", "maxima", "minima", "fechamento")
SAO_PAULO = "America/Sao_Paulo"
PROFIT_INDICATORS = {
    "v_VWAP_Diaria": "vwap",
    "v_Desvio_Padrao": "desvio",
    "v_ATR": "atr",
    "v_Media_ATR": "media_atr",
    "v_Saldo_Agressao": "agressao",
    "v_Volume_ZScore": "zscore_volume",
    "v_Regime_Mercado": "regime",
    "v_Sinal": "sinal",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_profit(path: Path, skiprows: int = 0) -> pd.DataFrame:
    return pd.read_csv(
        path, sep=";", encoding="cp1252", decimal=",", thousands=".",
        skiprows=skiprows,
    )


def read_local_bars(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", decimal=",")


def _timestamp_sao_paulo(value) -> pd.Timestamp:
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        return stamp.tz_localize(SAO_PAULO, ambiguous="raise", nonexistent="raise")
    return stamp.tz_convert(SAO_PAULO)


def reject_duplicate_timestamps(frame: pd.DataFrame, source: str) -> None:
    duplicated = frame.loc[frame["timestamp"].duplicated(keep=False), "timestamp"]
    if not duplicated.empty:
        first = duplicated.sort_values().iloc[0]
        count = int((frame["timestamp"] == first).sum())
        raise ValueError(
            f"Fonte {source} possui {count} linhas no horario duplicado "
            f"{first.isoformat()}; cruzamento recusado."
        )


def normalize_bars(frame: pd.DataFrame, timestamp: str, source: str = "desconhecida") -> pd.DataFrame:
    result = frame.copy()
    result.columns = [str(column).strip() for column in result.columns]
    aliases = {
        "Data": "timestamp", "Abertura": "abertura", "Máxima": "maxima",
        "Mínima": "minima", "Fechamento": "fechamento", "Trades": "trades",
        "Quantity": "quantity", "Volume": "volume_financeiro",
    }
    result = result.rename(columns=aliases)
    if timestamp != "timestamp":
        result = result.rename(columns={timestamp: "timestamp"})
    if result["timestamp"].isna().any():
        raise ValueError(f"Fonte {source} possui timestamp vazio.")
    try:
        result["timestamp"] = result["timestamp"].map(_timestamp_sao_paulo)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Fonte {source} possui timestamp invalido: {error}") from error
    reject_duplicate_timestamps(result, source)
    return result.sort_values("timestamp", kind="stable").reset_index(drop=True)


def target_day(frame: pd.DataFrame, day: str) -> pd.DataFrame:
    target = pd.Timestamp(day).date()
    return frame[frame["timestamp"].dt.date == target].copy().reset_index(drop=True)


def inventory(frame: pd.DataFrame) -> dict:
    return {
        "linhas": int(len(frame)),
        "inicio": frame["timestamp"].min().isoformat() if len(frame) else None,
        "fim": frame["timestamp"].max().isoformat() if len(frame) else None,
        "timestamps_duplicados": int(frame["timestamp"].duplicated().sum()),
        "ordem_temporal_valida": bool(frame["timestamp"].is_monotonic_increasing),
    }


def boundary_price_evidence(trades: pd.DataFrame, timestamp: str = "timestamp",
                            price: str = "preco") -> dict:
    """Detecta ambiguidade somente se o milissegundo-limite tem precos distintos.

    Uma barra pode conter muitos negocios no primeiro ou no ultimo milissegundo sem
    tornar OHLC ambiguo. A evidencia existe apenas quando esses negocios simultaneos
    carregam mais de um preco e a ordem de bolsa entre eles nao esta demonstrada.
    """
    data = trades[[timestamp, price]].copy()
    data[timestamp] = data[timestamp].map(_timestamp_sao_paulo)
    data["minuto"] = data[timestamp].dt.floor("min")
    records = []
    for minute, group in data.groupby("minuto", sort=True):
        first_stamp, last_stamp = group[timestamp].min(), group[timestamp].max()
        for edge, stamp in (("primeiro_milissegundo", first_stamp),
                            ("ultimo_milissegundo", last_stamp)):
            edge_rows = group[group[timestamp] == stamp]
            distinct = int(pd.to_numeric(edge_rows[price], errors="raise").nunique())
            if distinct > 1:
                records.append({
                    "barra": minute.isoformat(), "limite": edge,
                    "timestamp": stamp.isoformat(), "negocios": int(len(edge_rows)),
                    "precos_distintos": distinct,
                })
    return {
        "criterio": "mais de um preco no primeiro ou ultimo milissegundo da barra",
        "barras_com_evidencia": len({row["barra"] for row in records}),
        "ocorrencias": records,
    }


def first_difference(joined: pd.DataFrame, left: str, right: str,
                     tolerance: float = 0.0) -> dict | None:
    delta = (pd.to_numeric(joined[left]) - pd.to_numeric(joined[right])).abs()
    mask = delta > tolerance
    if not mask.any():
        return None
    index = mask.idxmax()
    return {
        "timestamp": joined.loc[index, "timestamp"].isoformat(),
        "profit": float(joined.loc[index, left]),
        "local": float(joined.loc[index, right]),
        "diferenca_absoluta": float(delta.loc[index]),
    }


def compare_bars(profit: pd.DataFrame, local: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    common = profit.merge(local, on="timestamp", how="inner", suffixes=("_profit", "_local"))
    profit_only = profit.loc[~profit.timestamp.isin(local.timestamp), "timestamp"]
    local_only = local.loc[~local.timestamp.isin(profit.timestamp), "timestamp"]
    fields = {}
    mapping = {**{name: name for name in PRICE}, "Trades": "trades", "Quantity": "quantity"}
    for label, name in mapping.items():
        left, right = f"{name}_profit", f"{name}_local"
        delta = (pd.to_numeric(common[left]) - pd.to_numeric(common[right])).abs()
        fields[label] = {
            "iguais": int((delta == 0).sum()), "diferentes": int((delta != 0).sum()),
            "max_diferenca_absoluta": float(delta.max()),
            "primeira_divergencia": first_difference(common, left, right),
        }
    result = {
        "profit": inventory(profit), "local": inventory(local),
        "comuns": int(len(common)),
        "exclusivos_profit": [stamp.isoformat() for stamp in profit_only],
        "exclusivos_local": [stamp.isoformat() for stamp in local_only],
        "campos": fields,
        "volume_financeiro_profit": {
            "unidade": "financeira; mantida separada de Quantity",
            "soma": float(profit["volume_financeiro"].sum()),
        },
    }
    return result, common


def rolling_local(local: pd.DataFrame, atr_period: int = 14, regime_period: int = 50) -> pd.DataFrame:
    """Reproduz as series atualmente implementadas pelo simulador, por segmento."""
    rows = []
    for _, group in local.groupby("segmento", sort=False):
        group = group.copy()
        close = group["fechamento"].astype(float)
        previous = close.shift(1).fillna(group["abertura"].astype(float))
        true_range = pd.concat([
            group["maxima"] - group["minima"],
            (group["maxima"] - previous).abs(),
            (group["minima"] - previous).abs(),
        ], axis=1).max(axis=1)
        atr = true_range.rolling(atr_period, min_periods=1).mean()
        media_atr = atr.rolling(regime_period, min_periods=1).mean()
        volume = group["volume_contratos"].astype(float)
        mean_volume = volume.rolling(20, min_periods=1).mean()
        std_volume = volume.rolling(20, min_periods=1).std(ddof=0)
        zscore = ((volume - mean_volume) / std_volume.replace(0, np.nan)).fillna(0)
        desvio = close.rolling(20, min_periods=1).std(ddof=0)
        aggression_bar = group["v_agressao_compra"] - group["v_agressao_venda"]
        aggression_engine = aggression_bar.cumsum()
        vwap = group["v_vwap_barra"].mul(volume).cumsum() / volume.cumsum()
        regime = np.where(
            (atr > media_atr) & ((close - vwap).abs() > 1.2 * desvio), 1,
            np.where(((group["minima"] <= vwap - 2.1 * desvio) |
                      (group["maxima"] >= vwap + 2.1 * desvio)) & (zscore > 1.5), 2, 0),
        )
        signal = np.where(
            ((regime == 1) & (close > vwap) & (aggression_engine > 0) & (zscore > 1.5)) |
            ((regime == 2) & (group["minima"] <= vwap - 2.1 * desvio) & (aggression_engine > 0)), 1,
            np.where(
                ((regime == 1) & (close < vwap) & (aggression_engine < 0) & (zscore > 1.5)) |
                ((regime == 2) & (group["maxima"] >= vwap + 2.1 * desvio) & (aggression_engine < 0)),
                -1, 0,
            ),
        )
        group = group.assign(
            desvio=desvio, atr=atr, media_atr=media_atr, zscore_volume=zscore,
            agressao=aggression_engine, agressao_por_barra=aggression_bar, vwap=vwap,
            regime=regime, sinal=signal,
            barras_desde_lacuna=np.arange(1, len(group) + 1),
        )
        rows.append(group)
    return pd.concat(rows, ignore_index=True)


def compare_indicators(profit: pd.DataFrame, local: pd.DataFrame, warmup: int) -> dict:
    calculated = rolling_local(local)
    comparable = calculated[calculated["barras_desde_lacuna"] >= warmup]
    joined = profit.merge(comparable, on="timestamp", how="inner", suffixes=("_profit", "_local"))
    tolerances = {"vwap": .01, "desvio": .01, "atr": .01, "media_atr": .01,
                  "agressao": 0, "zscore_volume": .01, "regime": 0, "sinal": 0}
    fields = {}
    for source, target in PROFIT_INDICATORS.items():
        left = source
        right = target
        delta = (pd.to_numeric(joined[left]) - pd.to_numeric(joined[right])).abs()
        tolerance = tolerances[target]
        fields[target] = {
            "tolerancia": tolerance, "comparados": int(len(joined)),
            "dentro_tolerancia": int((delta <= tolerance).sum()),
            "fora_tolerancia": int((delta > tolerance).sum()),
            "mediana_diferenca_absoluta": float(delta.median()),
            "max_diferenca_absoluta": float(delta.max()),
            "primeira_divergencia": first_difference(joined, left, right, tolerance),
        }
    # Diagnostico sem mudar a semantica do motor: export Profit se parece com saldo por candle.
    all_common = profit.merge(calculated, on="timestamp", how="inner")
    per_bar = all_common["v_Saldo_Agressao"].corr(all_common["agressao_por_barra"])
    same_sign = np.sign(all_common["v_Saldo_Agressao"]) == np.sign(all_common["agressao_por_barra"])
    segments = comparable.groupby("segmento").agg(
        inicio=("timestamp", "min"), fim=("timestamp", "max"), barras=("timestamp", "size")
    )
    return {
        "aquecimento_barras": warmup, "barras_comparadas": int(len(joined)),
        "trechos_comparaveis": [
            {"segmento": int(index), "inicio": row.inicio.isoformat(),
             "fim": row.fim.isoformat(), "barras": int(row.barras)}
            for index, row in segments.iterrows()
        ],
        "campos": fields,
        "diagnostico_agressao": {
            "correlacao_profit_com_saldo_local_por_candle": float(per_bar),
            "mesmo_sinal": int(same_sign.sum()), "comparados": int(len(all_common)),
            "observacao": "Profit exporta serie por candle; motor local acumula por segmento",
        },
        "sinais_candidatos_profit": {
            str(int(key)): int(value) for key, value in profit["v_Sinal"].value_counts().sort_index().items()
        },
        "sinais_candidatos_local": {
            str(int(key)): int(value) for key, value in calculated["sinal"].value_counts().sort_index().items()
        },
    }


def read_profit_operations(path: Path, day: str) -> pd.DataFrame:
    frame = read_profit(path, skiprows=5)
    for name in ("Abertura", "Fechamento"):
        frame[name] = pd.to_datetime(frame[name], dayfirst=True).map(_timestamp_sao_paulo)
    target = pd.Timestamp(day).date()
    return frame[frame["Abertura"].dt.date == target].copy().reset_index(drop=True)


def profit_round_trips(frame: pd.DataFrame) -> pd.DataFrame:
    buy_side = frame["Lado"].astype(str).str.upper().str.startswith("C")
    return pd.DataFrame({
        "entrada": frame["Abertura"], "saida": frame["Fechamento"],
        "lado": np.where(buy_side, "C", "V"),
        "quantidade": np.where(buy_side, frame["Qtd Compra"], frame["Qtd Venda"]).astype(int),
        "preco_entrada": np.where(buy_side, frame["Preço Compra"], frame["Preço Venda"]).astype(float),
        "preco_saida": np.where(buy_side, frame["Preço Venda"], frame["Preço Compra"]).astype(float),
        "numero_operacao": frame["Número Operação"].astype(int),
    })


def local_round_trips(fills: pd.DataFrame, candles: pd.DataFrame) -> pd.DataFrame:
    candle_time = pd.Series(pd.to_datetime(candles["timestamp"]).to_numpy(), index=candles["indice"])
    records, opened = [], None
    for fill in fills.itertuples(index=False):
        # execucoes.csv e 1-based; candles.indice e 0-based.
        timestamp = candle_time.loc[int(fill.barra) - 1]
        if fill.acao in {"long", "short"}:
            opened = {
                "entrada": timestamp, "lado": "C" if fill.acao == "long" else "V",
                "quantidade": int(fill.quantidade), "preco_entrada": float(fill.preco),
            }
        elif opened is not None and str(fill.acao).startswith("exit"):
            records.append(opened | {"saida": timestamp, "preco_saida": float(fill.preco)})
            opened = None
    return pd.DataFrame(records)


def compare_operations(profit: pd.DataFrame, local: pd.DataFrame) -> dict:
    keys = ["entrada", "saida", "lado", "quantidade", "preco_entrada", "preco_saida"]
    matched_profit, matched_local = set(), set()
    for pi, prow in profit.iterrows():
        for li, lrow in local.iterrows():
            if li in matched_local:
                continue
            if all(prow[key] == lrow[key] for key in keys):
                matched_profit.add(pi); matched_local.add(li); break
    missing = profit.loc[~profit.index.isin(matched_profit)]
    extra = local.loc[~local.index.isin(matched_local)]
    first = None
    if len(missing):
        row = missing.sort_values("entrada").iloc[0]
        first = {key: (row[key].isoformat() if key in {"entrada", "saida"} else
                       row[key].item() if hasattr(row[key], "item") else row[key]) for key in keys}
    return {
        "operacoes_profit": int(len(profit)), "operacoes_local": int(len(local)),
        "correspondencias_exatas": int(len(matched_profit)),
        "sem_correspondencia_profit": int(len(missing)),
        "sem_correspondencia_local": int(len(extra)),
        "primeira_operacao_profit_sem_correspondencia": first,
        "eventos_ordens_profit": "indisponiveis",
        "posicao_profit": "derivada das operacoes executadas; nao observada por candle",
    }


def build_report(args: argparse.Namespace) -> dict:
    profit_bars = target_day(normalize_bars(
        read_profit(args.profit_barras), "timestamp", "Profit barras"), args.data)
    local = target_day(normalize_bars(
        read_local_bars(args.local_barras), "timestamp", "captura local"), args.data)
    local["trades"] = local["v_trades_atual"]
    local["quantity"] = local["volume_contratos"]
    indicators = target_day(normalize_bars(
        read_profit(args.profit_indicadores), "timestamp", "Profit indicadores"), args.data)
    operations = profit_round_trips(read_profit_operations(args.profit_operacoes, args.data))
    fills = pd.read_csv(args.simulador_execucoes)
    simulator_candles = target_day(normalize_bars(
        pd.read_csv(args.simulador_candles), "timestamp", "simulador candles"), args.data)
    local_operations = local_round_trips(fills, simulator_candles)
    bars, _ = compare_bars(profit_bars, local)
    return {
        "versao_relatorio": 1, "data_alvo": args.data,
        "fontes": {
            name: {"arquivo": path.name, "sha256": sha256(path)}
            for name, path in {
                "profit_barras": args.profit_barras, "profit_indicadores": args.profit_indicadores,
                "profit_operacoes": args.profit_operacoes, "local_barras": args.local_barras,
                "simulador_execucoes": args.simulador_execucoes,
                "simulador_candles": args.simulador_candles,
            }.items()
        },
        "barras": bars,
        "indicadores": compare_indicators(indicators, local, args.aquecimento),
        "operacoes": compare_operations(operations, local_operations),
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser()
    for name in ("profit_barras", "profit_indicadores", "profit_operacoes", "local_barras",
                 "simulador_execucoes", "simulador_candles"):
        command.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    command.add_argument("--data", default="2026-10-21")
    command.add_argument("--aquecimento", type=int, default=63)
    command.add_argument("--saida", type=Path, required=True)
    return command


def main() -> None:
    args = parser().parse_args()
    if args.saida.exists():
        raise FileExistsError(f"Saida ja existe; fonte preservada: {args.saida}")
    report = build_report(args)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"saida": str(args.saida), "data": args.data,
                      "barras_comuns": report["barras"]["comuns"],
                      "operacoes_exatas": report["operacoes"]["correspondencias_exatas"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
