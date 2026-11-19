"""Integração causal das três fontes ProfitRTD normalizadas."""
import argparse
from bisect import bisect_left, bisect_right
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

KEYS = ["timestamp_evento", "sequencia_fonte", "pregao", "ativo_origem"]
TRADE = ["preco_ultimo", "quantidade_negocio"]
PRICE = ["preco_snapshot"]
BOOK = ["bid", "ask", "qtd_bid", "qtd_ask", "qtd_compra_book", "qtd_venda_book"]


def normalized(path, required, optional=()):
    frame = pd.read_csv(path, sep=";", decimal=",", dtype={"ativo_origem": "string", "pregao": "string"})
    missing = set(KEYS+required)-set(frame)
    if missing:
        raise ValueError(f"{Path(path).name}: faltam {', '.join(sorted(missing))}.")
    fields = required + [name for name in optional if name in frame]
    frame = frame[KEYS+fields]
    # Sem fuso explícito, a hora local é do pregão brasileiro.
    raw = frame["timestamp_evento"].astype("string")
    local = ~raw.str.contains(r"(?:Z|[+-]\d{2}:?\d{2})$", na=False)
    zoned = pd.to_datetime(raw.where(~local), format="ISO8601", utc=True)
    local_time = pd.to_datetime(raw.where(local), format="ISO8601").dt.tz_localize("America/Sao_Paulo",
                                                                                  ambiguous="raise", nonexistent="raise")
    frame["timestamp_evento"] = zoned.fillna(local_time.dt.tz_convert("UTC")).dt.tz_convert("America/Sao_Paulo")
    seq = pd.to_numeric(frame["sequencia_fonte"])
    if (seq.isna().any() or not np.isfinite(seq).all() or (seq < 0).any() or (seq % 1 != 0).any()
            or (seq >= 2**63).any()):
        raise ValueError("A sequência deve ser um inteiro não negativo de até 63 bits.")
    frame["sequencia_fonte"] = seq.astype("int64")
    if (frame[KEYS].isna().any().any() or frame["ativo_origem"].str.strip().eq("").any()
            or not frame["timestamp_evento"].dt.strftime("%Y-%m-%d").eq(frame["pregao"]).all()):
        raise ValueError("Evento sem chave completa ou com data divergente do pregão.")
    for col in fields:
        frame[col] = pd.to_numeric(frame[col])
        if (not np.isfinite(frame[col]).all() or (frame[col] < 0).any()
                or (col in {"preco_ultimo","preco_snapshot","bid","ask"} and (frame[col] <= 0).any())):
            raise ValueError(f"Valor inválido em {col}.")
    original_count = len(frame)
    frame = frame.drop_duplicates()
    if frame.duplicated(KEYS).any():
        raise ValueError(f"{Path(path).name}: registros conflitantes na mesma chave.")
    return frame.sort_values(KEYS, kind="stable"), original_count-len(frame)


def relate(trades, snapshots, fields, max_age_ms, shared):
    groups = {}
    for key, frame in snapshots.groupby(["ativo_origem", "pregao"], sort=False):
        groups[key] = (list(zip(frame.timestamp_evento, frame.sequencia_fonte)),
                       list(frame[fields].itertuples(index=False, name=None)))
    values, ages = [], []
    for stamp, sequence, day, asset, lower in trades[KEYS+["limite_snapshot"]].itertuples(index=False, name=None):
        keys, snapshots_values = groups.get((asset, day), ((), ()))
        index = (bisect_right(keys, (stamp, sequence)) if shared
                 else bisect_left(keys, (stamp, -1))) - 1
        elapsed = stamp-keys[index][0] if index >= 0 else None
        age = elapsed // pd.Timedelta(milliseconds=1) if elapsed is not None else None
        valid = (elapsed is not None and elapsed <= pd.Timedelta(milliseconds=max_age_ms)
                 and (pd.isna(lower) or keys[index][0] > lower))
        values.append(snapshots_values[index] if valid else [None]*len(fields))
        ages.append(age)
    return pd.DataFrame(values, columns=fields, index=trades.index), pd.array(ages, dtype="Int64")


def integrate(trades, prices, offers, max_age_ms=1000, gap_ms=5000, shared=False):
    if max_age_ms < 0 or gap_ms < 1:
        raise ValueError("Idade máxima e limite de lacuna inválidos.")
    trades, t_dupes = normalized(trades, TRADE, ["agressao_compra", "agressao_venda"])
    if trades.empty:
        raise ValueError("A fonte Negócios está vazia.")
    prices, p_dupes = normalized(prices, PRICE)
    offers, o_dupes = normalized(offers, BOOK)
    if (offers.bid > offers.ask).any():
        raise ValueError("Oferta com bid maior que ask.")
    groups = trades.groupby(["ativo_origem", "pregao"], sort=False)
    gap = groups.timestamp_evento.diff().gt(pd.Timedelta(milliseconds=gap_ms))
    trades["limite_snapshot"] = groups.timestamp_evento.shift().where(gap)
    trades["limite_snapshot"] = trades.groupby(["ativo_origem", "pregao"], sort=False).limite_snapshot.ffill()
    for snapshots, fields, name in ((prices, PRICE, "preco"), (offers, BOOK, "oferta")):
        data, age = relate(trades, snapshots, fields, max_age_ms, shared)
        trades[fields] = data
        trades[f"idade_{name}_ms"] = age
    if {"agressao_compra", "agressao_venda"} <= set(trades):
        trades["saldo_agressao"] = trades.agressao_compra-trades.agressao_venda
    trades["segmento"] = (gap | groups.cumcount().eq(0)).groupby(trades["ativo_origem"]).cumsum()
    trades["qualidade_dados"] = np.select([gap, trades.preco_snapshot.isna() | trades.bid.isna()],
                                               ["lacuna", "parcial"], default="ok")
    trades = trades.drop(columns="limite_snapshot")
    return trades, {"duplicidades_exatas": dict(negocios=t_dupes, precos=p_dupes, ofertas=o_dupes),
                    "eventos": len(trades), "lacunas": int(gap.sum()),
                    "sem_preco_valido": int(trades.preco_snapshot.isna().sum()),
                    "sem_oferta_valida": int(trades.bid.isna().sum())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("negocios", "precos", "ofertas", "saida"):
        parser.add_argument("--"+flag, type=Path, required=True)
    parser.add_argument("--idade-maxima-ms", type=int, default=1000)
    parser.add_argument("--lacuna-ms", type=int, default=5000)
    parser.add_argument("--sequencia-compartilhada", action="store_true")
    args = parser.parse_args()
    try:
        sources = (args.negocios, args.precos, args.ofertas)
        manifest = args.saida.with_suffix(".manifesto.json")
        if args.saida.resolve() in {source.resolve() for source in sources} or args.saida.exists() or manifest.exists():
            raise ValueError("Selecione um caminho novo para a saída; os dados originais são imutáveis.")
        events, metrics = integrate(*sources, args.idade_maxima_ms, args.lacuna_ms, args.sequencia_compartilhada)
        events["timestamp_evento"] = events["timestamp_evento"].map(lambda stamp: stamp.isoformat())
        def digest(path):
            with path.open("rb") as stream:
                return hashlib.file_digest(stream, "sha256").hexdigest()
        inputs = [{"arquivo": path.name, "sha256": digest(path)} for path in sources]
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        events.to_csv(args.saida, sep=";", decimal=",", index=False)
        manifest.write_text(json.dumps(metrics | {"schema":"dados_integrados_v1", "fontes":inputs,
                            "versao_integrador":Path(__file__).with_name("VERSION").read_text().strip(),
                            "sha256_saida":digest(args.saida),"idade_maxima_ms":args.idade_maxima_ms,
                            "lacuna_ms":args.lacuna_ms,"sequencia_compartilhada":args.sequencia_compartilhada},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError, ArithmeticError) as error:
        parser.exit(2, f"Erro: {error}\n")
