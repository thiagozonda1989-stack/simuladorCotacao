"""Compara sinais, ordens, execuções e posição exportados para um formato comum."""
import argparse
from pathlib import Path

import pandas as pd

STAGES = ("sinal", "ordem", "execucao", "posicao")
KEYS = ("timestamp", "sequencia", "etapa")


def read(path):
    data = pd.read_csv(path, sep=";", dtype="string", keep_default_na=False)
    if not set(KEYS) <= set(data):
        raise ValueError("O CSV precisa de timestamp, sequencia, etapa e campos comparáveis.")
    data["timestamp"] = pd.to_datetime(data.timestamp, format="ISO8601", utc=True)
    seq = pd.to_numeric(data.sequencia)
    if seq.isna().any() or (seq < 0).any() or (seq >= 2**63).any() or (seq % 1 != 0).any():
        raise ValueError("A sequência deve ser inteira, não negativa e caber em 63 bits.")
    data["sequencia"] = seq.astype("int64")
    if not data.etapa.isin(STAGES).all() or data[list(KEYS)].isna().any().any() or data.duplicated(list(KEYS)).any():
        raise ValueError("Etapa ou chave de paridade inválida ou repetida.")
    return data.set_index(list(KEYS)).sort_index()


def compare(reference, simulated):
    left, right = read(reference), read(simulated)
    fields = list(left.columns)
    if not fields or set(fields) != set(right.columns):
        raise ValueError("Use os mesmos campos comparáveis nas duas fontes.")
    keys = left.index.union(right.index)
    detail = left.reindex(keys).add_suffix("_profit").join(right.reindex(keys).add_suffix("_simulador"))
    same = left.reindex(keys).eq(right.reindex(keys)).fillna(False).all(axis=1)
    present_left = keys.isin(left.index)
    present_right = keys.isin(right.index)
    detail["resultado"] = "divergente"
    detail.loc[same, "resultado"] = "igual"
    detail.loc[~present_left, "resultado"] = "somente_simulador"
    detail.loc[~present_right, "resultado"] = "somente_profit"
    detail = detail.reset_index()
    matrix = pd.crosstab(detail.etapa, detail.resultado).reindex(STAGES, fill_value=0)
    return detail, matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("profit", "simulador", "saida"):
        parser.add_argument("--"+flag, type=Path, required=True)
    args = parser.parse_args()
    detail, matrix = compare(args.profit, args.simulador)
    args.saida.mkdir(parents=True, exist_ok=False)
    detail.to_csv(args.saida/"divergencias.csv", sep=";", index=False)
    matrix.to_csv(args.saida/"matriz.csv", sep=";")


if __name__ == "__main__":
    main()
