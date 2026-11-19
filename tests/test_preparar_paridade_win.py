from pathlib import Path

from tools.preparar_paridade_win import prepare


def test_prepara_candles_agressao_e_lacuna(tmp_path: Path):
    source = tmp_path / "win_negocios_21102026.csv"
    source.write_text(
        "Sequencia;Coluna_1;Coluna_3;Coluna_4;Coluna_6\n"
        "1;21/10/2026 09:15:00.100;100;2;Compra\n"
        "2;21/10/2026 09:15:00.100;105;3;Venda\n"
        "3;21/10/2026 09:15:07.000;110;4;Compra\n"
        "4;21/10/2026 09:16:00.000;115;1;Leilão\n",
        encoding="utf-8",
    )
    bars, metrics = prepare(source, gap_ms=5_000)
    assert bars[["abertura", "maxima", "minima", "fechamento"]].iloc[0].tolist() == [100, 110, 100, 110]
    assert bars.iloc[0].volume_contratos == 9
    assert bars.iloc[0].volume == 9
    assert bars.iloc[0].v_agressao_compra == 6
    assert bars.iloc[0].v_agressao_venda == 3
    assert bars.iloc[0].lacuna_na_barra
    assert metrics["lacunas_maiores_limite"] == 2
    assert metrics["lacunas"][0]["anterior"].endswith("09:15:00.100000")
    assert metrics["agressores_nao_reconhecidos"] == 1
