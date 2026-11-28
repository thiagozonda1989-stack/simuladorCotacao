from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from tools.reproduzir_v5_7_rodada17 import (
    aggregate, configuration, first_difference, from_fills, metrics, native_trades,
)


def test_perfil_incompleto_impede_replay_da_variacao():
    with pytest.raises(ValueError, match="Faltam dados da variação: modo_profit"):
        configuration({"ativo": "WINZ26", "periodo_segundos": 60})


def test_identidade_inclui_horarios_lado_lote_e_precos(tmp_path: Path):
    native_csv = tmp_path / "profit.csv"
    native_csv.write_text(
        "Ativo;Abertura;Fechamento;Lado;Qtd Compra;Qtd Venda;Preço Compra;Preço Venda;"
        "Res. Operação;Comissões\n"
        "WINZ26;26/10/2026 10:52:00;26/10/2026 10:55:00;V;5;5;173.900;174.775;873,50;1,50\n",
        encoding="cp1252",
    )
    pd.DataFrame({"timestamp": ["2026-10-26 10:52:00-03:00", "2026-10-26 10:55:00-03:00"]}).to_csv(
        tmp_path / "candles.csv", index=False,
    )
    pd.DataFrame([
        dict(barra=1, acao="short", preco=174775, quantidade=5, posicao=-5, tipo="market",
             pontos_contrato=0, custo_reais=0.75),
        dict(barra=2, acao="exit_short", preco=173900, quantidade=5, posicao=0, tipo="limit",
             pontos_contrato=4375, custo_reais=0.75),
    ]).to_csv(tmp_path / "execucoes.csv", index=False)

    native = native_trades(native_csv)
    replay = from_fills(tmp_path)
    assert native[0]["bruto"] == Decimal("875")
    assert metrics(native) == metrics(replay)
    assert first_difference(native, replay) is None
    assert aggregate(replay, ["2026-10-26", "2026-10-27"])["operacoes_por_pregao"] == 0.5
    changed = dict(replay[0], identidade=(*replay[0]["identidade"][:3], 2, *replay[0]["identidade"][4:]))
    assert first_difference(native, [changed]) == {"operacao": 1, "campos": ["quantidade"]}
    assert first_difference(native, []) == {"operacao": 1, "campos": ["operação ausente"]}
