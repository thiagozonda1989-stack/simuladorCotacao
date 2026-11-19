"""Copia estratégias novas/alteradas sem modificar as fontes e atualiza um manifesto."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def destination(root: Path, source: Path) -> Path:
    kind = "execucao" if source.name.lower().startswith(("modelo_", "modelo-")) else "indicadores"
    return root / kind / source.name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origem", type=Path, required=True)
    parser.add_argument("--destino", type=Path, default=Path("estrategias"))
    args = parser.parse_args()

    target_root = args.destino.resolve()
    manifest_path = target_root / "manifesto_estrategias.json"
    previous_payload = None
    if manifest_path.exists():
        previous_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    records = []
    copied = 0
    sources = sorted(args.origem.glob("validacao_modelo*/**/*.ntsl"))
    for source in sources:
        sha = digest(source)
        target = destination(target_root, source)
        target.parent.mkdir(parents=True, exist_ok=True)
        relative = target.relative_to(target_root).as_posix()
        if not target.exists() or digest(target) != sha:
            shutil.copy2(source, target)
            copied += 1
        records.append({
            "arquivo": relative,
            "sha256": sha,
            "bytes": source.stat().st_size,
            "origem_relativa": source.relative_to(args.origem).as_posix(),
        })

    if (
        copied == 0
        and previous_payload is not None
        and previous_payload.get("arquivos") == records
    ):
        print(f"{len(records)} estratégias já registradas; nenhum arquivo alterado.")
        return

    payload = {
        "versao_manifesto": 1,
        "gerado_utc": datetime.now(timezone.utc).isoformat(),
        "arquivos": records,
    }
    with manifest_path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(records)} estratégias registradas; {copied} copiadas ou atualizadas.")


if __name__ == "__main__":
    main()
