import pandas as pd
import pytest

from tools.inventariar_coletor_win import (
    BASE_COLUMNS, COLLECTOR, COLUMNS, FIELDS, compare_by_day, daily_rows, read_capture,
)


def test_le_plots_em_ordem_com_cabecalho_repetido(tmp_path):
    source = tmp_path / "profit.csv"
    header = (*BASE_COLUMNS, *(COLLECTOR,) * len(FIELDS))
    row = "08/09/2026 09:00;100;110;90;105;2;4;80;-1;100,01"
    source.write_bytes((";".join(header) + "\n" + row + "\n").encode("cp1252"))
    frame, original, encoding = read_capture(source)
    assert encoding == "cp1252"
    assert original == list(header)
    assert frame.loc[0, list(FIELDS)].tolist() == [2, 4, 80, -1, 100.01]
    source.write_bytes((";".join(header) + "\n" + row + ";extra\n").encode("cp1252"))
    with pytest.raises(ValueError, match="colunas"):
        read_capture(source)


def test_cobertura_separa_lacuna_interna_borda_e_diferencas_de_campo():
    rows = [
        [pd.Timestamp("2026-10-01 09:00"), 100, 110, 90, 105, 2, 4, 80, -1, 100],
        [pd.Timestamp("2026-10-01 09:02"), 100, 110, 90, 105, 2, 4, 80, -1, 100],
    ]
    new = pd.DataFrame(rows, columns=COLUMNS)
    old = new.iloc[:1].copy()
    old.loc[0, FIELDS[-1]] = 101
    daily, field_differences = compare_by_day(new, old)
    [day] = daily_rows(new, daily)
    assert day["minutos_ausentes_internos"] == day["maior_lacuna_interna_minutos"] == 1
    assert day["minutos_ausentes_na_janela"] == 563
    assert day["cobertura"] == "lacuna_interna"
    assert day["timestamps_comuns"] == day["comuns_ohlc_iguais"] == day["somente_novo"] == 1
    assert day["comuns_todos_campos_iguais"] == 0
    assert field_differences[FIELDS[-1]] == 1
