"""Confere barras subminuto do Profit com a coleta de 1 minuto, sem executar NTSL."""
from argparse import ArgumentParser
from datetime import timedelta
from itertools import groupby
import json
from pathlib import Path

from tools.auditar_reserva_rodada20 import FIELDS, OHLC, parse, save
from tools.rodada19 import digest

SOURCE_ROLES = ("barras_subminuto", "coleta_1min", "referencia_1min_anterior")
FOCUS = ("09:00", "09:01", "09:02", "09:03", "09:04", "09:05", "18:13", "18:14", "18:15")


def reconcile(subminute, minute):
    fields = [*OHLC, *FIELDS]
    subminute = subminute[["Data", *fields]]
    if subminute.isna().any().any():
        raise ValueError("A exportação subminuto contém campos inválidos.")
    if subminute.duplicated().any() or minute["Data"].duplicated().any():
        raise ValueError("A fonte contém linhas duplicadas na granularidade esperada.")
    reference = minute.set_index("Data")
    if minute[["Data", *fields]].isna().any().any():
        raise ValueError("A coleta de 1 minuto contém campos inválidos.")
    details = {}
    # O Profit escreveu os blocos em ordem decrescente dentro de cada recorte.
    # A chave tem resolução de minuto. Não atribua segundos às linhas.
    rows_in_file_order = subminute.itertuples(index=False, name=None)
    for stamp, contiguous_rows in groupby(rows_in_file_order, key=lambda row: row[0]):
        rows = list(contiguous_rows)
        if stamp in details:
            raise ValueError("As linhas do mesmo minuto precisam ser contíguas.")
        if len(rows) > 60:
            raise ValueError("Há mais de 60 barras para um minuto.")
        if stamp not in reference.index:
            details[stamp] = {"barras": len(rows), "referencia_presente": False}
            continue
        aggregate = [rows[-1][1], max(row[2] for row in rows), min(row[3] for row in rows), rows[0][4]]
        aggregate.extend(sum(row[index] for row in rows) for index in range(5, 9))
        aggregate.append(rows[0][9])
        expected = reference.loc[stamp, fields]
        differences = {field: round(float(value - expected[field]), 2)
                       for field, value in zip(fields, aggregate, strict=True)}
        details[stamp] = {
            "barras": len(rows), "referencia_presente": True,
            "ohlc_e_series_aditivas_iguais": all(differences[field] == 0 for field in fields[:-1]),
            "vwap_ultimo_registro_igual": differences[FIELDS[-1]] == 0,
            "diferencas": differences,
        }
    return details


def audit(paths, cache_path):
    hashes = [digest(path) for path in paths]
    key = "rodada20-subminuto-v2:" + ":".join(hashes)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.is_file() else {}
    if key not in cache:
        bars, minute, old = map(parse, paths)
        details = reconcile(bars, minute)
        focus = {}
        dates = bars["Data"].dt.strftime("%Y-%m-%d").unique()
        if len(dates) != 1:
            raise ValueError("O recorte subminuto deve conter um único pregão.")
        for hour in FOCUS:
            match = next((record for stamp, record in details.items() if stamp.strftime("%H:%M") == hour), {})
            focus[hour] = match or {"barras": 0}
        complete = [record for record in details.values() if record["barras"] == 60]
        close_stamp = bars["Data"].dt.normalize().iloc[0] + timedelta(hours=18, minutes=14)
        new_ohlc = minute.set_index("Data").loc[close_stamp, list(OHLC)]
        old_ohlc = old.set_index("Data").loc[close_stamp, list(OHLC)]
        deltas = bars["Data"].diff().dt.total_seconds()
        vwap_check = {}
        for day in (str(dates[0]), "2026-11-24"):
            day_bars = minute.loc[minute["Data"].dt.strftime("%Y-%m-%d").eq(day)].sort_values("Data")
            contracts = day_bars[FIELDS[1]].cumsum()
            financial = day_bars[FIELDS[2]].cumsum()
            implied_vwap = financial.div(contracts.where(contracts.gt(0)) * 0.20)
            vwap_difference = day_bars[FIELDS[-1]].sub(implied_vwap).abs()
            vwap_check[day] = dict(
                barras=len(day_bars), barras_dentro_de_001_ponto=int(vwap_difference.le(0.01).sum())
            )
        cache[key] = {
            "pregao": str(dates[0]), "linhas": len(bars), "colunas": list(bars),
            "primeiro_rotulo": bars["Data"].min().isoformat(timespec="minutes"),
            "ultimo_rotulo": bars["Data"].max().isoformat(timespec="minutes"),
            "resolucao_exportada_do_rotulo": "minuto",
            "avancos_na_ordem_fisica_entre_recortes": int(deltas.gt(0).sum()),
            "minutos_distintos": len(details), "repeticoes_esperadas_do_rotulo_minuto": len(bars) - len(details),
            "minutos_com_60_linhas": len(complete),
            "minutos_com_60_linhas_e_ohlc_e_aditivos_iguais": sum(r.get("ohlc_e_series_aditivas_iguais", False) for r in complete),
            "minutos_com_60_linhas_e_vwap_igual": sum(r.get("vwap_ultimo_registro_igual", False) for r in complete),
            "janelas": focus,
            "vwap_1min_vs_volume_e_quantidade_acumulados": vwap_check,
            "diferenca_ohlc_18h14_coleta_1min_menos_referencia_anterior": {
                name: float(new_ohlc[name] - old_ohlc[name]) for name in OHLC
            },
        }
        save(cache_path, cache)
    return dict(fontes=[dict(papel=role, sha256=sha, bytes=path.stat().st_size)
                        for role, path, sha in zip(SOURCE_ROLES, paths, hashes, strict=True)], **cache[key])


def main():
    parser = ArgumentParser(description=__doc__)
    for name in ("subminuto", "minuto", "referencia", "cache", "saida"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    save(args.saida, audit((args.subminuto, args.minuto, args.referencia), args.cache))


if __name__ == "__main__":
    main()
