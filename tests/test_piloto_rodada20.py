import pandas as pd
import pytest

from estrategia import load_bars
from tools.auditar_reserva_rodada20 import FIELDS
from tools.piloto_rodada20 import (
    DAY, PROFILES, PROTOCOL, WARMUP, evaluate_profile, validate_coverage,
)
from tools.rodada19 import read_json


def sessions():
    prior = pd.date_range(f"{WARMUP} 09:03", f"{WARMUP} 18:24", freq="min")
    pilot = pd.date_range(f"{DAY} 09:00", f"{DAY} 18:24", freq="min")
    return [pd.DataFrame({"Data": dates, "Abertura": 1000, "Máxima": 1005, "Mínima": 995,
                          "Fechamento": 1000, **{field: 1 for field in FIELDS}})
            for dates in (prior, pilot)]


def test_elegibilidade_rejeita_lacuna_no_piloto_e_no_aquecimento():
    prior, pilot = sessions()
    assert validate_coverage(prior, pilot)["barras_observadas"] == 86
    with pytest.raises(ValueError, match=WARMUP):
        validate_coverage(prior.drop(prior.index[-10]), pilot)
    with pytest.raises(ValueError, match=DAY):
        validate_coverage(prior, pilot.drop(pilot.index[20]))


def test_piloto_com_os_perfis_congelados_tem_aquecimento_e_nao_aprova(tmp_path):
    prior, pilot = sessions()
    times = pd.concat([prior["Data"], pilot["Data"]], ignore_index=True)
    path = tmp_path / "entrada_sintetica.csv"
    pd.DataFrame(dict(timestamp=times, abertura=1000, maxima=1005, minima=995, fechamento=1000,
                      v_trades_atual=1, volume_contratos=1, volume_financeiro=200,
                      v_agressao_saldo_referencia=0, v_vwap_barra=1000)).to_csv(path, sep=";", index=False)
    frame = load_bars(path, 60, "ohlc")
    config = read_json(PROTOCOL)
    for name in PROFILES:
        report = evaluate_profile(name, config, frame, len(prior))
        assert report["no_inicio"] == dict(currentbar=563, barras_previas_disponiveis=562,
                                          barras_no_segmento=1, lacuna_intradiaria=False)
        assert report["totais"]["operacoes"] == 0
        assert report["avaliacao"]["decisao"] == "piloto_descritivo"
