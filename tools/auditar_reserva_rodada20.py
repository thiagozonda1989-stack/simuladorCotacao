"""Audita a coleta do Profit sem avaliar estratégias ou exportar candles."""
from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tools.inventario_rodada19 import OHLC, save
from tools.rodada19 import digest

FIELDS = ("v_Trades", "v_Quantidade_Contratos", "v_Volume_Financeiro",
          "v_Saldo_Agressao", "v_VWAP_Diaria")
DAYS = ("2026-11-19", "2026-11-23", "2026-11-24")


def parse(path):
    # A exportação Profit no Windows usa Windows-1252 e decimal brasileiro.
    # Também aceita UTF-8 com BOM quando o Excel salva nesse formato.
    with path.open("rb") as stream:
        bom = stream.read(3)
    encoding = "utf-8-sig" if bom == b"\xef\xbb\xbf" else "cp1252"
    data = pd.read_csv(path, sep=";", decimal=",", thousands=".", encoding=encoding)
    data["Data"] = pd.to_datetime(data["Data"], format="%d/%m/%Y %H:%M", errors="coerce")
    for column in data.columns.drop("Data"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    return data


def inspect(data):
    good_dates = data["Data"].dropna()
    return dict(
        barras=len(data), colunas=list(data), pregoes=good_dates.dt.normalize().nunique(),
        primeiro_timestamp=good_dates.min().isoformat(), ultimo_timestamp=good_dates.max().isoformat(),
        fisicamente_descendente=good_dates.is_monotonic_decreasing,
        datas_invalidas=int(data["Data"].isna().sum()),
        timestamps_duplicados=int(good_dates.duplicated().sum()),
        linhas_duplicadas=int(data.duplicated().sum()),
        ausentes_ou_invalidos_por_campo={k: int((~np.isfinite(data[k])).sum())
                                        for k in data.columns.drop("Data")},
    )


def coverage(day, data):
    stamp = pd.DatetimeIndex(data["Data"].unique()).sort_values()
    expected = pd.date_range(f"{day} 09:00", f"{day} 18:24", freq="1min")
    gaps = pd.date_range(stamp.min(), stamp.max(), freq="1min").difference(stamp) if len(stamp) else stamp
    prices = data[list(OHLC)]
    ohlc_invalid = (
        (~np.isfinite(prices)).any(axis=1) | prices.le(0).any(axis=1)
        | prices.iloc[:, 1].lt(prices.iloc[:, [0, 2, 3]].max(axis=1))
        | prices.iloc[:, 2].gt(prices.iloc[:, [0, 1, 3]].min(axis=1))
    )
    fields = {}
    for field in FIELDS:
        if field in data:
            x = data[field]
            fields[field] = dict(presentes=int(np.isfinite(x).sum()),
                                 ausentes_ou_invalidos=int((~np.isfinite(x)).sum()),
                                 zeros=int(x.eq(0).sum()), negativos=int(x.lt(0).sum()))
    return dict(barras=len(data), primeiro=stamp.min().strftime("%H:%M") if len(stamp) else None,
                ultimo=stamp.max().strftime("%H:%M") if len(stamp) else None,
                ausencias_na_janela_0900_1824=len(expected.difference(stamp)),
                fora_da_janela_0900_1824=len(stamp.difference(expected)),
                lacunas_internas_minutos=len(gaps), ohlc_invalidos=int(ohlc_invalid.sum()),
                timestamps_duplicados=int(data["Data"].duplicated().sum()), series=fields)


def audit_warmup_tail(stamps, end, bars):
    """Confere os últimos minutos do pregão anterior, inclusive o seu fechamento."""
    if bars < 1:
        raise ValueError("O aquecimento exige pelo menos uma barra.")
    end = pd.Timestamp(end)
    expected = pd.date_range(end=end, periods=bars, freq="1min")
    if expected[0].normalize() != end.normalize():
        raise ValueError("A janela final precisa pertencer a um único pregão.")
    observed = pd.DatetimeIndex(stamps)
    tail = observed[(observed >= expected[0]) & (observed <= end)].sort_values()
    missing = expected.difference(tail)
    duplicates = int(tail.duplicated().sum())
    return dict(
        inicio=expected[0].isoformat(), fim=end.isoformat(), barras_esperadas=bars,
        barras_observadas=len(tail), minutos_faltantes=len(missing),
        timestamps_duplicados=duplicates, continua=tail.equals(expected),
    )


def compare(data, reference):
    # O relatório contém só os totais e a maior diferença por coluna.
    joined = data[["Data", *OHLC]].merge(reference[["Data", *OHLC]], on="Data",
                                        how="outer", suffixes=("_nova", "_ref"),
                                        indicator=True, validate="one_to_one")
    matched = joined.loc[joined["_merge"].eq("both")]
    differences = pd.DataFrame({field: matched[field + "_nova"] - matched[field + "_ref"]
                                for field in OHLC})
    mismatch = differences.ne(0).any(axis=1)
    return dict(
        intersecao=len(matched), somente_nova=int(joined["_merge"].eq("left_only").sum()),
        somente_referencia=int(joined["_merge"].eq("right_only").sum()),
        ohlc_igual=int((~mismatch).sum()), ohlc_diferente=int(mismatch.sum()),
        comparacao_de_cada_preco={field: dict(
            diferentes=int(differences[field].ne(0).sum()),
            desvio_absoluto_maximo=float(differences[field].abs().max()) if len(matched) else None)
            for field in OHLC},
        divergencia_na_ultima_barra_da_referencia=bool(
            mismatch.any() and matched.loc[mismatch, "Data"].eq(reference["Data"].max()).all()),
    )


def audit(paths, cache_path):
    key = ":".join(digest(path) for path in paths)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
    if key not in cache:
        data, reference = map(parse, paths)
        source_stats = [inspect(frame) for frame in (data, reference)]
        if any(s["timestamps_duplicados"] or s["datas_invalidas"] for s in source_stats):
            raise ValueError("Chave temporal inválida ou duplicada, faça a auditoria antes de unir.")
        if any(field not in data for field in FIELDS):
            raise ValueError("A coleta está incompleta, falta pelo menos uma série esperada.")
        days = {}
        for day in DAYS:
            current = data.loc[data["Data"].dt.normalize().eq(day)]
            old = reference.loc[reference["Data"].dt.normalize().eq(day)]
            stat = coverage(day, current)
            qty = current["v_Quantidade_Contratos"]
            trades = current["v_Trades"]
            stat["trades_acima_da_quantidade"] = int(trades.gt(qty).sum())
            stat["barras_com_trades_ou_contratos_fracionarios"] = int(
                (trades.mod(1).ne(0) | qty.mod(1).ne(0)).sum())
            implied = current["v_Volume_Financeiro"].div(qty.where(qty.gt(0)) * 0.20)
            stat["preco_implicito_fora_ohlc_margem_001_pt"] = int(
                (implied.lt(current[OHLC[2]] - 0.01) | implied.gt(current[OHLC[1]] + 0.01)).sum())
            days[day] = dict(captura=stat, referencia_barras=len(old), cruzamento=compare(current, old))
        cache[key] = dict(estatisticas_fontes=source_stats, por_pregao=days,
                          cruzamento_total=compare(data, reference))
        save(cache_path, cache)
    return dict(fontes=[dict(arquivo=path.name, sha256=sha, bytes=path.stat().st_size)
                        for path, sha in zip(paths, key.split(":"), strict=True)],
                **cache[key], replays_na_reserva=0)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--captura", type=Path, required=True)
    parser.add_argument("--referencia", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    save(args.saida, audit((args.captura, args.referencia), args.cache))


if __name__ == "__main__":
    main()