import csv
from pathlib import Path

import pytest

from estrategia import run_strategy

ROOT = Path(__file__).resolve().parents[1]


def test_validacao_com_extremos_ambiguos_e_taxas(tmp_path):
    sample = ROOT / "exemplos/replay_minimo"
    result = run_strategy(sample/"candles.csv", (sample/"estrategia.ntsl").read_text(),
                          tmp_path/"saida", 5, "ohlc", 5, point_value=0.2,
                          regras={"custo_por_contrato_lado":0.25}, validacao="WINZ26")
    assert result["operacoes"] == 1
    assert result["operacoes_negativas"] == 1 and result["taxa_acerto"] == 0
    assert result["resultado_liquido_reais"] == -2.5
    with (tmp_path/"saida"/"validacao.csv").open(encoding="utf-8-sig") as stream:
        data = list(csv.DictReader(stream, delimiter=";"))
    assert [row["evento"] for row in data] == ["Entrada", "Saída final"]
    assert [row["lado"] for row in data] == ["Compra", "Venda"]
    assert data[1]["operacao"] == data[0]["operacao"] == "1"
    assert data[1]["hora_abertura_operacao"] == data[0]["hora"]
    assert len(data[1]["hora"].split(":")) == 3
    assert sum(float(row["liquido_reais"].replace(",", ".")) for row in data) == pytest.approx(-2.5)
    pdf = tmp_path/"saida"/"nota_corretagem_simulada.pdf"
    assert pdf.read_bytes().startswith(b"%PDF-")
    assert "Queda a partir do pico" in (tmp_path/"saida"/"relatorio.html").read_text()


def test_validacao_sem_execucoes(tmp_path):
    sample = ROOT / "exemplos/replay_minimo"
    result = run_strategy(sample/"candles.csv", "begin end;", tmp_path/"saida", 5, "ohlc",
                          5, validacao="WINZ26")
    assert result["operacoes"] == 0 and result["taxa_acerto"] is None
    assert (tmp_path/"saida"/"nota_corretagem_simulada.pdf").is_file()
    assert len((tmp_path/"saida"/"validacao.csv").read_text().splitlines()) == 1
