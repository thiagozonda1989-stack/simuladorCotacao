import json

import pandas as pd

from tools.inventariar_cobertura_win import classify, inspect_file, write_outputs


def test_agrega_cobertura_empates_lacunas_e_sequencia(tmp_path):
    source = tmp_path / "win_negocios_18112026.csv"
    source.write_text(
        '"Sequencia";"Coluna_1";"Coluna_3";"Coluna_4"\n'
        '"1";"Data";"Valor";"Quantidade"\n'
        '"2";"18/11/2026 09:00:00.000";"170000";"2"\n'
        '"3";"18/11/2026 09:00:00.000";"170005";"3"\n'
        '"4";"18/11/2026 09:00:06.000";"170010";"1"\n',
        encoding="utf-8",
    )
    result = inspect_file(source, chunk_size=2)
    result["pregao"] = "2026-11-18"
    classify([result])
    opening = result["faixas"][0]
    assert result["negocios"] == 3
    assert result["contratos"] == 6
    assert result["sequencia_lacunas"] == 0
    assert opening["grupos_empate_ms"] == 1
    assert opening["negocios_em_empates_ms"] == 2
    assert opening["lacunas_maiores_5s"] == 1
    daily = tmp_path / "pregoes.csv"
    ranges = tmp_path / "faixas.csv"
    write_outputs([result], daily, ranges)
    assert pd.read_csv(ranges, sep=";").loc[0, "negocios"] == 3
    assert "elegivel_etapa2_negocios" in pd.read_csv(daily, sep=";").columns
