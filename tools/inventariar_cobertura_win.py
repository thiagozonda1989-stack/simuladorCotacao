"""Gera agregados de cobertura dos arquivos WIN de negocios sem alterar a origem.

O registro JSON permite reaproveitar resultados de arquivos inalterados. A saida
nao contem negocios individuais, precos, corretoras nem caminhos absolutos.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


VERSION = 3
SESSION_START = 9 * 60
SESSION_END = 18 * 60 + 32
RANGES = (
    ("09:00-09:59", 9 * 60, 10 * 60),
    ("10:00-11:59", 10 * 60, 12 * 60),
    ("12:00-13:59", 12 * 60, 14 * 60),
    ("14:00-15:59", 14 * 60, 16 * 60),
    ("16:00-17:59", 16 * 60, 18 * 60),
    ("18:00-18:31", 18 * 60, SESSION_END),
)
USECOLS = ["Sequencia", "Coluna_1", "Coluna_3", "Coluna_4"]


def _temporal_metrics(values_ms: np.ndarray) -> dict[str, float | int]:
    if values_ms.size == 0:
        return {
            "grupos_empate_ms": 0,
            "negocios_em_empates_ms": 0,
            "negocios_excedentes_empate_ms": 0,
            "lacunas_maiores_5s": 0,
            "lacunas_maiores_60s": 0,
            "maior_lacuna_s": 0.0,
        }
    ordered = np.sort(values_ms)
    changes = np.flatnonzero(np.diff(ordered) != 0) + 1
    counts = np.diff(np.r_[0, changes, ordered.size])
    tied = counts[counts > 1]
    unique = ordered[np.r_[True, np.diff(ordered) != 0]]
    deltas = np.diff(unique)
    result = {
        "grupos_empate_ms": int(tied.size),
        "negocios_em_empates_ms": int(tied.sum()),
        "negocios_excedentes_empate_ms": int((tied - 1).sum()),
        "lacunas_maiores_5s": int((deltas > 5_000).sum()),
        "lacunas_maiores_60s": int((deltas > 60_000).sum()),
        "maior_lacuna_s": round(float(deltas.max() / 1_000), 3) if deltas.size else 0.0,
    }
    return result


def inspect_file(path: Path, chunk_size: int = 250_000) -> dict:
    timestamps: list[np.ndarray] = []
    quantities: list[np.ndarray] = []
    prices: list[np.ndarray] = []
    raw_rows = invalid_rows = sequence_gaps = sequence_repeats = 0
    previous_sequence: int | None = None
    previous_timestamp: int | None = None
    timestamp_inversions_raw = timestamp_equal_consecutive_raw = 0

    for chunk in pd.read_csv(
        path,
        sep=";",
        usecols=USECOLS,
        dtype="string",
        chunksize=chunk_size,
        encoding="utf-8-sig",
    ):
        raw_rows += len(chunk)
        sequence = pd.to_numeric(chunk["Sequencia"], errors="coerce").dropna().to_numpy(dtype=np.int64)
        if sequence.size:
            if previous_sequence is not None:
                delta = int(sequence[0]) - previous_sequence
                sequence_gaps += int(delta > 1)
                sequence_repeats += int(delta <= 0)
            diffs = np.diff(sequence)
            sequence_gaps += int((diffs > 1).sum())
            sequence_repeats += int((diffs <= 0).sum())
            previous_sequence = int(sequence[-1])

        parsed = pd.to_datetime(
            chunk["Coluna_1"], format="%d/%m/%Y %H:%M:%S.%f", errors="coerce"
        )
        quantity = pd.to_numeric(chunk["Coluna_4"], errors="coerce")
        price = pd.to_numeric(chunk["Coluna_3"], errors="coerce")
        valid = parsed.notna() & quantity.notna() & price.notna() & (quantity > 0) & (price > 0)
        invalid_rows += int((~valid).sum())
        if valid.any():
            current_ts = parsed[valid].astype("datetime64[ms]").astype("int64").to_numpy()
            if previous_timestamp is not None:
                timestamp_inversions_raw += int(current_ts[0] < previous_timestamp)
                timestamp_equal_consecutive_raw += int(current_ts[0] == previous_timestamp)
            raw_deltas = np.diff(current_ts)
            timestamp_inversions_raw += int((raw_deltas < 0).sum())
            timestamp_equal_consecutive_raw += int((raw_deltas == 0).sum())
            previous_timestamp = int(current_ts[-1])
            timestamps.append(current_ts)
            quantities.append(quantity[valid].to_numpy(dtype=np.int64))
            prices.append(price[valid].to_numpy(dtype=np.int64))

    ts = np.concatenate(timestamps) if timestamps else np.array([], dtype=np.int64)
    qty = np.concatenate(quantities) if quantities else np.array([], dtype=np.int64)
    price = np.concatenate(prices) if prices else np.array([], dtype=np.int64)
    local = pd.to_datetime(ts, unit="ms")
    minute = local.hour.to_numpy() * 60 + local.minute.to_numpy()
    in_session = (minute >= SESSION_START) & (minute < SESSION_END)
    ts, qty, price, minute = ts[in_session], qty[in_session], price[in_session], minute[in_session]

    by_range = []
    for label, start, end in RANGES:
        mask = (minute >= start) & (minute < end)
        expected = end - start
        covered = int(np.unique(minute[mask]).size)
        row = {
            "faixa_horaria": label,
            "minutos_esperados": expected,
            "minutos_com_negocio": covered,
            "cobertura_pct": round(100 * covered / expected, 2),
            "minutos_sem_negocio": expected - covered,
            "negocios": int(mask.sum()),
            "contratos": int(qty[mask].sum()),
        }
        row.update(_temporal_metrics(ts[mask]))
        by_range.append(row)

    covered_minutes = int(np.unique(minute).size)
    first_minute = int(minute.min()) if minute.size else SESSION_END
    last_minute = int(minute.max()) if minute.size else SESSION_START - 1
    boundary_missing = max(0, first_minute - SESSION_START) + max(0, SESSION_END - 1 - last_minute)
    result = {
        "arquivo": path.name,
        "bytes": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
        "linhas_brutas": raw_rows,
        "linhas_invalidas_metadados": invalid_rows,
        "negocios": int(ts.size),
        "contratos": int(qty.sum()),
        "minutos_com_negocio": covered_minutes,
        "minutos_sem_negocio": SESSION_END - SESSION_START - covered_minutes,
        "minutos_sem_negocio_borda": boundary_missing,
        "cobertura_pct": round(100 * covered_minutes / (SESSION_END - SESSION_START), 2),
        "densidade_negocios_minuto_coberto": round(ts.size / covered_minutes, 2) if covered_minutes else 0,
        "inicio": local[in_session].min().isoformat() if ts.size else "",
        "fim": local[in_session].max().isoformat() if ts.size else "",
        "sequencia_lacunas": sequence_gaps,
        "sequencia_repeticoes": sequence_repeats,
        "precos_fora_grade_5": int((price % 5 != 0).sum()),
        "timestamp_inversoes_ordem_arquivo": timestamp_inversions_raw,
        "timestamp_iguais_consecutivos_arquivo": timestamp_equal_consecutive_raw,
        "faixas": by_range,
    }
    result.update(_temporal_metrics(ts))
    return result


def classify(days: list[dict]) -> None:
    positive = [day["densidade_negocios_minuto_coberto"] for day in days if day["negocios"]]
    median_density = float(np.median(positive)) if positive else 0.0
    minimum_density = median_density * 0.10
    for day in days:
        reasons = []
        if day["cobertura_pct"] < 95:
            reasons.append("cobertura_inferior_95pct")
        if day["densidade_negocios_minuto_coberto"] < minimum_density:
            reasons.append("densidade_inferior_10pct_mediana")
        if day["sequencia_lacunas"] or day["sequencia_repeticoes"]:
            reasons.append("sequencia_nao_continua")
        if day["precos_fora_grade_5"]:
            reasons.append("preco_fora_grade_5")
        day["elegivel_etapa2_negocios"] = 0 if reasons else 1
        day["justificativa_elegibilidade"] = ",".join(reasons) if reasons else "criterios_agregados_atendidos;segmentar_nas_lacunas"
        internal = day["minutos_sem_negocio"] - day["minutos_sem_negocio_borda"]
        if internal <= 0:
            day["interpretacao_ausencia"] = "sem_lacuna_interna_de_minuto"
        elif day["densidade_negocios_minuto_coberto"] >= minimum_density:
            day["interpretacao_ausencia"] = "provavel_falha_captura_em_ativo_liquido"
        else:
            day["interpretacao_ausencia"] = "captura_negocios_incompleta_ou_amostrada"


def write_outputs(days: list[dict], daily_path: Path, ranges_path: Path) -> None:
    daily_fields = [
        "pregao", "negocios", "contratos", "inicio", "fim", "minutos_com_negocio",
        "minutos_sem_negocio", "minutos_sem_negocio_borda", "cobertura_pct",
        "densidade_negocios_minuto_coberto", "sequencia_lacunas", "sequencia_repeticoes",
        "timestamp_inversoes_ordem_arquivo", "timestamp_iguais_consecutivos_arquivo",
        "precos_fora_grade_5", "elegivel_etapa2_negocios", "interpretacao_ausencia",
        "justificativa_elegibilidade", "grupos_empate_ms", "negocios_em_empates_ms",
        "negocios_excedentes_empate_ms", "lacunas_maiores_5s", "lacunas_maiores_60s",
        "maior_lacuna_s",
    ]
    range_fields = [
        "pregao", "faixa_horaria", "minutos_esperados", "minutos_com_negocio",
        "cobertura_pct", "minutos_sem_negocio", "negocios", "contratos",
        "grupos_empate_ms", "negocios_em_empates_ms", "negocios_excedentes_empate_ms",
        "lacunas_maiores_5s", "lacunas_maiores_60s", "maior_lacuna_s",
    ]
    for target, fields, rows in (
        (daily_path, daily_fields, days),
        (ranges_path, range_fields, [dict(row, pregao=day["pregao"]) for day in days for row in day["faixas"]]),
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows)[fields].to_csv(
            target, sep=";", index=False, encoding="utf-8", lineterminator="\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", type=Path, required=True)
    parser.add_argument("--pregoes", type=Path, required=True)
    parser.add_argument("--faixas", type=Path, required=True)
    parser.add_argument("--registro", type=Path, required=True)
    args = parser.parse_args()
    registry = {"version": VERSION, "files": {}}
    if args.registro.exists():
        loaded = json.loads(args.registro.read_text(encoding="utf-8"))
        if loaded.get("version") == VERSION:
            registry = loaded
    days = []
    processed = skipped = 0
    for path in sorted(args.origem.glob("win_negocios_????????.csv")):
        match = re.fullmatch(r"win_negocios_(\d{2})(\d{2})(\d{4})\.csv", path.name)
        if not match:
            continue
        key = path.name
        stat = path.stat()
        cached = registry["files"].get(key)
        if cached and cached.get("bytes") == stat.st_size and cached.get("mtime_ns") == stat.st_mtime_ns:
            result = cached
            skipped += 1
        else:
            result = inspect_file(path)
            registry["files"][key] = result
            processed += 1
        day, month, year = match.groups()
        result["pregao"] = f"{year}-{month}-{day}"
        days.append(result)
    days.sort(key=lambda item: item["pregao"])
    classify(days)
    write_outputs(days, args.pregoes, args.faixas)
    args.registro.parent.mkdir(parents=True, exist_ok=True)
    args.registro.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{processed} arquivo(s) processado(s); {skipped} resultado(s) incrementais reutilizado(s).")


if __name__ == "__main__":
    main()
