import pandas as pd
import pytest

from tools.auditar_reserva_rodada20 import FIELDS, OHLC
from tools.conferir_subminuto_rodada20 import reconcile


def test_reconstroi_barra_em_ordem_fisica_sem_inventar_segundos():
    stamp = pd.Timestamp("2026-11-23 18:14")
    columns = ["Data", *OHLC, *FIELDS]
    subminute = pd.DataFrame([
        [stamp, 110, 115, 100, 100, 3, 4, 82, -2, 105.0],
        [stamp, 130, 135, 110, 110, 6, 8, 192, 1, 110.0],
    ], columns=columns)
    minute = pd.DataFrame([[stamp, 130, 135, 100, 100, 9, 12, 274, -1, 105.5]], columns=columns)
    row = reconcile(subminute, minute)[stamp]
    assert row["barras"] == 2
    assert row["ohlc_e_series_aditivas_iguais"]
    assert row["diferencas"][FIELDS[-1]] == -0.5
    assert not row["vwap_ultimo_registro_igual"]
    assert not reconcile(subminute.iloc[::-1], minute)[stamp]["ohlc_e_series_aditivas_iguais"]


def test_rejeita_linha_duplicada_sem_confundir_rotulo_repetido_com_segundo():
    stamp = pd.Timestamp("2026-11-23 18:14")
    columns = ["Data", *OHLC, *FIELDS]
    row = [stamp, 110, 115, 100, 100, 3, 4, 82, -2, 105.0]
    with pytest.raises(ValueError, match="duplicadas"):
        reconcile(pd.DataFrame([row, row], columns=columns), pd.DataFrame([row], columns=columns))
