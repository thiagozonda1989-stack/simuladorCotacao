import pytest

from tools.rodada19 import decompose


def trade(key, regime, cents):
    return dict(chave=key, hora_entrada="09:00", direcao="compra",
                regime_entrada=regime, centavos=cents)


def test_decomposicao_grupo_exclusivo_e_entrada_pareada():
    original = [trade(1, "tendencia", 400), trade(2, "exaustao", -200)]
    optimized = [trade(1, "tendencia", 100)]
    result = decompose(original, optimized)
    assert result["delta_reais"] == -1
    assert result["frequencia_reais"] == -1
    assert result["composicao_reais"] == 3.38
    assert result["resultado_dentro_dos_grupos_reais"] == -3.38
    assert result["pareadas"] == 1
    assert result["delta_pareadas_reais"] == -3
    assert result["liquido_exclusivas_original"] == -2


def test_pareamento_rejeita_identidade_duplicada():
    same = trade(1, "tendencia", 100)
    with pytest.raises(ValueError, match="não é única"):
        decompose([same, same], [same])
