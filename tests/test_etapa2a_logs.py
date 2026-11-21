import csv
import gzip
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs/colaboracao/logs_paridade/paridade_console_varios_dias.csv.gz"


def test_bloco_console_20261026_preserva_sequencia_publicada():
    with gzip.open(LOG, "rt", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))

    with gzip.open(LOG, "rb") as stream:
        assert hashlib.sha256(stream.read()).hexdigest() == (
            "8c02666ff28d4467d5764efb1d4702ac23ebe595a47718d9dd0c66214a9d8cd0"
        )
    assert len(rows) == 30_155

    selected = [row for row in rows if row["date"] == "2026-10-26"
                and row["arquivo"] == "Texto colado (2).txt"
                and row["bloco"] == "4" and 3542 <= int(row["linha"]) <= 3552]
    assert [int(row["linha"]) for row in selected] == list(range(3542, 3553))
    assert [(row["time"], row["evento"]) for row in selected] == [
        ("13:03", "POSICAO_OBSERVADA"),
        ("13:03", "SOLICITA_ENTRADA_COMPRA"),
        ("13:03", "POSICAO_OBSERVADA"),
        ("13:03", "SOLICITA_ALVO_VENDA"),
        ("13:03", "SOLICITA_STOP_VENDA"),
        ("13:04", "POSICAO_OBSERVADA"),
        ("13:04", "SOLICITA_ENTRADA_COMPRA"),
        ("13:04", "POSICAO_OBSERVADA"),
        ("13:04", "SOLICITA_ALVO_VENDA"),
        ("13:04", "SOLICITA_STOP_VENDA"),
        ("13:05", "POSICAO_OBSERVADA"),
    ]
    assert selected[4]["gatilho"] == "177215.00"
    assert selected[4]["limite"] == "177210.00"
