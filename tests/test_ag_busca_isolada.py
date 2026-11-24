from estrategia import strategy_replay
from simulador import optimize


def test_busca_financeira_isolada_exclui_candidato_acima_do_risco(tmp_path):
    source = "input Q(1); begin if not HasPosition then BuyAtMarket(Q); end;"
    csv = tmp_path / "sintetico.csv"
    csv.write_text(
        "timestamp;abertura;maxima;minima;fechamento\n"
        "2026-11-18T09:00:00;100;100;100;100\n"
        "2026-11-18T09:01:00;100;100;100;100\n"
        "2026-11-18T09:02:00;105;105;105;105\n"
        "2026-11-18T09:03:00;120;120;120;120\n",
        encoding="utf-8",
    )
    config = dict(pregoes_teste=0, cache_ram_mb=0, threads=1, parametros={"Q": {"valores":[1,2]}},
                  genetico=dict(populacao=2, geracoes=1, paciencia=0, semente=8, metrica="resultado"))
    replay = strategy_replay(csv, source, 60, "ohlc", config, 5, 1)
    full = optimize(replay, config, tmp_path, search_only=True)
    admitted = optimize(replay, config, tmp_path, search_only=True,
                        candidate_gate=lambda stats: stats["resultado_reais"] <= 20)
    assert full["parametros_otimizados"] == {"Q": 2}
    assert admitted["parametros_otimizados"] == {"Q": 1}
    assert admitted["candidatos_avaliados"] == 2
    assert list(admitted["resultados"]) == ["busca"]
    assert not (tmp_path / "predicoes.csv").exists()
