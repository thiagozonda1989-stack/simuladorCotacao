"""Inventaria candles e plots do coletor WINZ26. Publica somente agregados."""
from argparse import ArgumentParser
from collections import Counter
import csv
import json
from pathlib import Path

import pandas as pd

from tools.auditar_reserva_rodada20 import FIELDS, OHLC, coverage, inspect
from tools.inventario_rodada19 import save
from tools.rodada19 import digest

COLLECTOR = "Coleta_Reserva_WINZ26_1Min_V1_0"
BASE_COLUMNS = ("Data", *OHLC)
COLUMNS = (*BASE_COLUMNS, *FIELDS)
COMPARISON_FIELDS = ("timestamps_comuns", "comuns_ohlc_iguais", "comuns_todos_campos_iguais",
                     "somente_novo", "somente_referencia")


def read_capture(path):
    with path.open("rb") as stream:
        encoding = "utf-8-sig" if stream.read(3) == b"\xef\xbb\xbf" else "cp1252"
    with path.open(encoding=encoding, newline="") as stream:
        reader = csv.reader(stream, delimiter=";")
        header = tuple(next(reader, ()))
        for line in reader:
            if line and len(line) != len(header):
                raise ValueError(f"Quantidade de colunas invalida na linha {reader.line_num}.")
    if header not in (COLUMNS, (*BASE_COLUMNS, *(COLLECTOR,) * len(FIELDS))):
        raise ValueError("Cabecalho incompativel com o coletor WINZ26 V1.0.")
    frame = pd.read_csv(path, sep=";", encoding=encoding, header=0, names=COLUMNS,
                        decimal=",", thousands=".")
    frame["Data"] = pd.to_datetime(frame["Data"], format="%d/%m/%Y %H:%M", errors="coerce")
    for field in COLUMNS[1:]:
        frame[field] = pd.to_numeric(frame[field], errors="coerce")
    if frame["Data"].notna().sum() == 0:
        raise ValueError("A captura nao tem timestamps validos.")
    return frame, list(header), encoding


def compare_by_day(data, reference):
    # Chaves duplicadas sao contadas no inventario e excluidas do cruzamento.
    left = data.dropna(subset=["Data"]).drop_duplicates(subset=["Data"], keep=False)
    right = reference.dropna(subset=["Data"]).drop_duplicates(subset=["Data"], keep=False)
    joined = left.merge(right, on="Data", how="outer", suffixes=("_novo", "_ref"),
                        validate="one_to_one", indicator=True)
    counts = {}
    field_totals = Counter({field: 0 for field in COLUMNS[1:]})
    for day, group in joined.groupby(joined["Data"].dt.strftime("%Y-%m-%d")):
        common = group.loc[group["_merge"].eq("both")]
        same = pd.DataFrame({
            field: common[field + "_novo"].eq(common[field + "_ref"])
            for field in COLUMNS[1:]
        })
        field_totals.update({field: int((~same[field]).sum()) for field in same})
        counts[day] = dict(
            timestamps_comuns=len(common),
            comuns_ohlc_iguais=int(same[list(OHLC)].all(axis=1).sum()),
            comuns_todos_campos_iguais=int(same.all(axis=1).sum()),
            somente_novo=int(group["_merge"].eq("left_only").sum()),
            somente_referencia=int(group["_merge"].eq("right_only").sum()),
        )
    return counts, dict(field_totals)


def daily_rows(data, comparison):
    all_rows = []
    valid = data.loc[data["Data"].notna()]
    grouped = valid.groupby(valid["Data"].dt.strftime("%Y-%m-%d"))
    for day, rows in grouped:
        stats = coverage(day, rows)
        stamps = pd.DatetimeIndex(rows["Data"].unique()).sort_values()
        gaps = stamps.to_series().diff().dt.total_seconds().div(60).sub(1)
        unique_sorted = rows.sort_values("Data").drop_duplicates("Data", keep=False)
        qty = unique_sorted[FIELDS[1]]
        volume = unique_sorted[FIELDS[2]]
        trades = unique_sorted[FIELDS[0]]
        implied = volume.div(0.20 * qty.where(qty.gt(0)))
        out_of_range = implied.lt(unique_sorted[OHLC[2]] - 0.01) | implied.gt(unique_sorted[OHLC[1]] + 0.01)
        vwap = volume.cumsum().div(0.20 * qty.cumsum())
        if stats["lacunas_internas_minutos"]:
            status = "lacuna_interna"
        elif stats["ausencias_na_janela_0900_1824"] or stats["fora_da_janela_0900_1824"]:
            status = "borda_diferente"
        else:
            status = "janela_completa"
        all_rows.append(dict(
            pregao=day, barras=stats["barras"], primeiro_rotulo=stats["primeiro"],
            ultimo_rotulo=stats["ultimo"], cobertura=status,
            minutos_ausentes_na_janela=stats["ausencias_na_janela_0900_1824"],
            minutos_fora_da_janela=stats["fora_da_janela_0900_1824"],
            minutos_ausentes_internos=stats["lacunas_internas_minutos"],
            maior_lacuna_interna_minutos=int(gaps.max()) if len(stamps) > 1 else 0,
            timestamps_duplicados=stats["timestamps_duplicados"],
            ohlc_invalidos=stats["ohlc_invalidos"],
            barras_fora_grade_5_pontos=int(rows[list(OHLC)].mod(5).ne(0).any(axis=1).sum()),
            trades_invalidos=int((trades.le(0) | trades.gt(qty) | trades.mod(1).ne(0)).sum()),
            quantity_invalida=int((qty.le(0) | qty.mod(1).ne(0)).sum()),
            volume_financeiro_nao_positivo=int(volume.le(0).sum()),
            preco_implicito_fora_ohlc=int(out_of_range.sum()),
            barras_vwap_compativeis_com_acumulado=int(vwap.sub(unique_sorted[FIELDS[-1]]).abs().le(0.01).sum()),
            **{f"ausentes_{name}": stats["series"][name]["ausentes_ou_invalidos"] for name in FIELDS},
            **comparison.get(day, dict.fromkeys(COMPARISON_FIELDS, 0)),
        ))
    return all_rows


def summarize(source, previous, hashes):
    data, header, encoding = read_capture(source)
    reference, _, _ = read_capture(previous)
    compare_day, field_differences = compare_by_day(data, reference)
    rows = daily_rows(data, compare_day)
    status = inspect(data)
    reference_days = set(reference["Data"].dropna().dt.strftime("%Y-%m-%d"))
    days = {r["pregao"] for r in rows}
    return dict(
        fonte=dict(arquivo=source.name, bytes=source.stat().st_size, sha256=hashes[0],
                   codificacao=encoding, separador=";", cabecalho_original=header, **status),
        referencia=dict(arquivo=previous.name, bytes=previous.stat().st_size, sha256=hashes[1]),
        ativo_indicado="WINZ26",
        ativo_em_coluna=False,
        minutos_por_barra=1,
        janela_de_referencia="09:00-18:24 America/Sao_Paulo, incluindo os dois rotulos",
        dias_por_mes=dict(sorted(Counter(day[:7] for day in days).items())),
        dias_por_cobertura=dict(Counter(row["cobertura"] for row in rows)),
        minutos_ausentes_internos_total=sum(row["minutos_ausentes_internos"] for row in rows),
        maior_lacuna_interna_minutos=max(row["maior_lacuna_interna_minutos"] for row in rows),
        comparacao={metric: sum(row[metric] for row in compare_day.values()) for metric in COMPARISON_FIELDS},
        diferencas_por_campo_em_timestamps_comuns=field_differences,
        datas_somente_na_nova_fonte=sorted(days - reference_days),
        datas_somente_na_referencia=sorted(reference_days - days),
        replays_executados=0,
        pregoes=rows,
    )


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--fonte", type=Path, required=True)
    parser.add_argument("--referencia", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    hashes = [digest(path) for path in (args.fonte, args.referencia)]
    key = "inventario_coletor_v2:" + ":".join(hashes)
    cache = json.loads(args.cache.read_text(encoding="utf-8")) if args.cache.is_file() else {}
    if key not in cache:
        cache[key] = summarize(args.fonte, args.referencia, hashes)
        save(args.cache, cache)
    report = dict(cache[key])
    rows = report.pop("pregoes")
    args.saida.mkdir(parents=True, exist_ok=True)
    save(args.saida / "manifesto.json", report)
    with (args.saida / "pregoes.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
