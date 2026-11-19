"""Inventaria CSVs novos/alterados sem modificar os arquivos de origem."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

TIMESTAMP_NAMES = ("timestamp", "data_hora", "datetime", "datahora", "data_minuto_origem", "data")
FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S.%f", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
)


def parse_time(value: str) -> datetime | None:
    for fmt in FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            pass
    return None


def dialect(path: Path) -> csv.Dialect:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t,")
    except csv.Error:
        return csv.get_dialect("excel")


def inspect(path: Path, root: Path, gap_seconds: float) -> dict[str, Any]:
    stat = path.stat()
    result: dict[str, Any] = {
        "arquivo": path.relative_to(root).as_posix(), "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns, "linhas": 0, "colunas": [],
        "coluna_temporal": "", "inicio": "", "fim": "",
        "timestamps_invalidos": 0, "fora_de_ordem": 0,
        "timestamps_duplicados_consecutivos": 0, "lacunas_acima_limite": 0,
        "maior_lacuna_segundos": 0.0,
    }
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
        reader = csv.DictReader(stream, dialect=dialect(path))
        headers = reader.fieldnames or []
        result["colunas"] = headers
        normalized = {name.strip().lower(): name for name in headers}
        time_col = next((normalized[name] for name in TIMESTAMP_NAMES if name in normalized), "")
        result["coluna_temporal"] = time_col
        first = previous = last = None
        for row in reader:
            result["linhas"] += 1
            if not time_col:
                continue
            current = parse_time(row.get(time_col, ""))
            if current is None:
                result["timestamps_invalidos"] += 1
                continue
            if first is None:
                first = current
            if previous is not None:
                delta = (current - previous).total_seconds()
                if delta < 0:
                    result["fora_de_ordem"] += 1
                elif delta == 0:
                    result["timestamps_duplicados_consecutivos"] += 1
                else:
                    result["maior_lacuna_segundos"] = max(result["maior_lacuna_segundos"], delta)
                    if gap_seconds > 0 and delta > gap_seconds:
                        result["lacunas_acima_limite"] += 1
            previous = last = current
        if first:
            result["inicio"] = first.isoformat()
        if last:
            result["fim"] = last.isoformat()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", type=Path, required=True)
    parser.add_argument("--saida", type=Path, default=Path("inventario_dados.csv"))
    parser.add_argument("--registro", type=Path, default=Path(".inventario_dados.json"))
    parser.add_argument("--lacuna-segundos", type=float, default=0.0)
    args = parser.parse_args()
    root = args.origem.resolve()
    registry: dict[str, Any] = {}
    if args.registro.exists():
        registry = json.loads(args.registro.read_text(encoding="utf-8"))
    processed = skipped = 0
    for path in sorted(root.rglob("*.csv")):
        key = path.relative_to(root).as_posix()
        stat = path.stat()
        old = registry.get(key, {})
        if old.get("bytes") == stat.st_size and old.get("mtime_ns") == stat.st_mtime_ns:
            skipped += 1
            continue
        registry[key] = inspect(path, root, args.lacuna_segundos)
        processed += 1
    args.registro.parent.mkdir(parents=True, exist_ok=True)
    args.registro.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = [
        "arquivo", "bytes", "linhas", "coluna_temporal", "inicio", "fim",
        "timestamps_invalidos", "fora_de_ordem", "timestamps_duplicados_consecutivos",
        "lacunas_acima_limite", "maior_lacuna_segundos", "colunas",
    ]
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    with args.saida.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for item in sorted(registry.values(), key=lambda value: value["arquivo"]):
            row = dict(item)
            row["colunas"] = "|".join(row["colunas"])
            writer.writerow(row)
    print(f"{processed} arquivo(s) processado(s); {skipped} inalterado(s) ignorado(s).")


if __name__ == "__main__":
    main()
