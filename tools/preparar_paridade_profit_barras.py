"""Prepara candles privados exportados do Profit para replay mecanico.

As fontes nunca sao alteradas. O CSV de saida preserva Quantity (contratos) e
Volume (financeiro) em colunas distintas. A agressao exportada pelo Profit e
opcional e, quando presente, fica explicitamente marcada como referencia
injetada para uma rodada diagnostica, nao como dado independente.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


SAO_PAULO = "America/Sao_Paulo"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_profit(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="cp1252", decimal=",", thousands=".")


def normalize_timestamp(series: pd.Series) -> pd.Series:
    stamps = pd.to_datetime(series, dayfirst=True, errors="raise")
    if stamps.dt.tz is None:
        return stamps.dt.tz_localize(SAO_PAULO, ambiguous="raise", nonexistent="raise")
    return stamps.dt.tz_convert(SAO_PAULO)


def prepare(bars: pd.DataFrame, day: str, indicators: pd.DataFrame | None = None
            ) -> tuple[pd.DataFrame, dict]:
    if len(bars.columns) < 8:
        raise ValueError("Exportacao de barras precisa conter Data, OHLC, Trades, Quantity e Volume.")
    data = bars.iloc[:, :8].copy()
    data.columns = ["timestamp", "abertura", "maxima", "minima", "fechamento",
                    "v_trades_atual", "volume_contratos", "volume_financeiro"]
    data["timestamp"] = normalize_timestamp(data["timestamp"])
    target = pd.Timestamp(day).date()
    data = data[data["timestamp"].dt.date == target].copy()
    if data.empty:
        raise ValueError(f"Fonte sem barras no dia {day}.")
    duplicated = data.loc[data["timestamp"].duplicated(keep=False), "timestamp"]
    if not duplicated.empty:
        raise ValueError(f"Profit barras possui horario duplicado: {duplicated.min().isoformat()}.")
    data = data.sort_values("timestamp", kind="stable").reset_index(drop=True)
    numeric = ["abertura", "maxima", "minima", "fechamento", "v_trades_atual",
               "volume_contratos", "volume_financeiro"]
    data[numeric] = data[numeric].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(data[numeric]).all().all() or (data["volume_contratos"] <= 0).any():
        raise ValueError("Profit barras contem numero invalido ou Quantity nao positiva.")
    for name in ("v_trades_atual", "volume_contratos"):
        if (data[name] < 0).any() or not np.equal(data[name], np.floor(data[name])).all():
            raise ValueError(f"Profit barras contem {name} negativa ou fracionaria.")
    if (data["volume_financeiro"] < 0).any():
        raise ValueError("Profit barras contem Volume financeiro negativo.")

    expected = pd.date_range(data.timestamp.min(), data.timestamp.max(), freq="min")
    missing_minutes = expected.difference(pd.DatetimeIndex(data.timestamp))

    # O WIN vale R$ 0,20 por ponto e contrato. Esta inversao recupera apenas
    # um preco medio aproximado, pois o Volume exportado ja vem arredondado.
    data["v_vwap_barra"] = (
        data["volume_financeiro"] / (data["volume_contratos"] * 0.20)
    )
    data["volume"] = data["volume_contratos"]
    data["v_agressao_compra"] = 0.0
    data["v_agressao_venda"] = 0.0
    reference = False
    if indicators is not None:
        if len(indicators.columns) < 10:
            raise ValueError("Exportacao de indicadores nao contem v_Saldo_Agressao.")
        indicator = indicators.copy()
        indicator.columns = [str(column).strip() for column in indicator.columns]
        timestamp_name = indicator.columns[0]
        aggression_name = next((column for column in indicator.columns
                                if column.lower() == "v_saldo_agressao"), None)
        if aggression_name is None:
            raise ValueError("Exportacao de indicadores sem v_Saldo_Agressao.")
        indicator = indicator[[timestamp_name, aggression_name]].rename(
            columns={timestamp_name: "timestamp", aggression_name: "v_agressao_saldo_referencia"})
        indicator["timestamp"] = normalize_timestamp(indicator["timestamp"])
        indicator = indicator[indicator["timestamp"].dt.date == target]
        if indicator["timestamp"].duplicated().any():
            stamp = indicator.loc[indicator["timestamp"].duplicated(keep=False), "timestamp"].min()
            raise ValueError(f"Profit indicadores possui horario duplicado: {stamp.isoformat()}.")
        data = data.merge(indicator, on="timestamp", how="left", validate="one_to_one")
        missing = int(data["v_agressao_saldo_referencia"].isna().sum())
        if missing:
            raise ValueError(f"Faltam {missing} valores de agressao de referencia nas barras do Profit.")
        balance = pd.to_numeric(data["v_agressao_saldo_referencia"], errors="raise")
        data["v_agressao_compra"] = balance.clip(lower=0)
        data["v_agressao_venda"] = (-balance).clip(lower=0)
        reference = True

    metrics = {
        "schema": "profit_barras_paridade_v1",
        "dia": day, "fuso": SAO_PAULO,
        "timestamp_barra": "abertura_do_minuto",
        "barras": int(len(data)), "inicio": data.timestamp.min().isoformat(),
        "fim": data.timestamp.max().isoformat(),
        "timestamps_duplicados": 0,
        "minutos_ausentes_entre_inicio_fim": int(len(missing_minutes)),
        "primeiros_minutos_ausentes": [stamp.isoformat() for stamp in missing_minutes[:20]],
        "ativo_no_conteudo": None,
        "validacao_ativo": "indisponivel no CSV; identificacao depende do arquivo/exportacao",
        "unidades": {
            "OHLC": "pontos WIN", "Trades": "negocios inteiros",
            "Quantity": "contratos inteiros", "Volume": "R$ financeiro",
        },
        "volume_ntsl_padrao": "volume_contratos",
        "volume_ntsl_modo_paridade": "volume_financeiro",
        "vwap_barra": "Volume_financeiro/(Quantity_contratos*R$0,20); aproximada",
        "agressao_referencia_injetada_disponivel": reference,
        "observacao_agressao": (
            "v_Saldo_Agressao exportado do Profit; uso apenas diagnostico"
            if reference else "indisponivel"
        ),
    }
    return data, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--barras", type=Path, required=True)
    parser.add_argument("--indicadores", type=Path)
    parser.add_argument("--data", default="2026-10-21")
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--manifesto", type=Path, required=True)
    args = parser.parse_args()
    if args.saida.exists() or args.manifesto.exists():
        parser.error("A saida e o manifesto devem ser caminhos novos.")
    prepared, metrics = prepare(
        read_profit(args.barras), args.data,
        read_profit(args.indicadores) if args.indicadores else None,
    )
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_csv(args.saida, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    metrics["fontes"] = {"barras": {"arquivo": args.barras.name, "sha256": digest(args.barras)}}
    if args.indicadores:
        metrics["fontes"]["indicadores"] = {
            "arquivo": args.indicadores.name, "sha256": digest(args.indicadores),
        }
    metrics["sha256_saida_privada"] = digest(args.saida)
    args.manifesto.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")


if __name__ == "__main__":
    main()
