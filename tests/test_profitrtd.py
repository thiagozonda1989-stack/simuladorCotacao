from pathlib import Path
import json
import hashlib

import pandas as pd
import pytest

from estrategia import Engine, load_bars, strategy_replay
from integrar_profitrtd import integrate
from ntsl import compile_ntsl
from simulador import walk_forward

ROOT = Path(__file__).resolve().parents[1]
HEADER = "timestamp_evento;sequencia_fonte;pregao;ativo_origem"


def test_hashes_dos_ntsl_publicados():
    manifest = json.loads((ROOT/"estrategias/manifesto_estrategias.json").read_text())
    assert len(manifest["arquivos"]) == 55
    for file in manifest["arquivos"]:
        content = (ROOT/"estrategias"/file["arquivo"]).read_bytes()
        assert len(content) == file["bytes"]
        assert hashlib.sha256(content).hexdigest() == file["sha256"]


def test_integracao_causal_e_lacuna(tmp_path):
    def fixture(name, columns, items):
        path = tmp_path/f"{name}.csv"
        path.write_text(HEADER+";"+columns+"\n"+"\n".join(
            f"2026-11-18T09:15:{clock};{seq};2026-11-18;WIN;{data}"
            for clock,seq,data in items))
        return path
    trades = fixture("negocios","preco_ultimo;quantidade_negocio", [
        ("00.100",2,"100;1"),("00.100",2,"100;1"),("00.200",3,"105;1"),("02.000",4,"110;1")])
    prices = fixture("precos","preco_snapshot",[("00.100",1,"101"),("00.100",9,"103")])
    offers = fixture("ofertas","bid;ask;qtd_bid;qtd_ask;qtd_compra_book;qtd_venda_book",[
        ("00.099",0,"95;100;2;3;4;5"),("00.300",8,"100;105;2;3;4;5")])
    frame, metrics = integrate(trades, prices, offers, gap_ms=500, max_age_ms=3000)
    assert pd.isna(frame.iloc[0].preco_snapshot)
    assert frame.iloc[1].preco_snapshot == 103
    assert frame.iloc[1].bid == 95  # A oferta das 00.300 ainda está no futuro.
    assert pd.isna(frame.iloc[2].preco_snapshot)
    assert frame.iloc[2].bid == 100  # Atualização nova, dentro da janela.
    assert metrics["duplicidades_exatas"]["negocios"] == 1
    shared, _ = integrate(trades, prices, offers, gap_ms=500, max_age_ms=3000, shared=True)
    assert shared.iloc[0].preco_snapshot == 101
    assert shared.iloc[1].preco_snapshot == 103
    path = tmp_path/"integrado.csv"
    frame.to_csv(path, sep=";", decimal=",", index=False)
    bars = load_bars(path, 1, "integrado")
    assert bars.lacuna_intradiaria.tolist() == [False, True]
    assert bars.v_bid.tolist() == [95,100]


def test_lacuna_cancela_ordem_e_reinicia_historico(tmp_path):
    path = tmp_path/"negocios.csv"
    path.write_text("timestamp;preco;quantidade\n2026-11-18T09:00:00;110;1\n"
                    "2026-11-18T09:00:02;85;1\n2026-11-18T09:00:03;80;1\n")
    frame = load_bars(path, 1, "negocios")
    source = "begin if CurrentBar=1 then BuyAtLimit(90); Plot(Close[1]); Plot2(CalcTime(2359,2)); end;"
    engine = Engine(compile_ntsl(source), frame, 5, {}, 1, 1, regras={"ordem_so_proxima_barra":False})
    engine.run()
    assert not engine.fills
    assert engine.orders_cancelled_at_gaps == 1
    assert engine.trace[1]["plot"] == 0
    assert engine.trace[1]["plot2"] == 1
    assert frame.intervalo_barra_segundos.tolist() == [0,2,1]


def test_latencia_parcial_e_reversao(tmp_path):
    path = tmp_path/"ohlc.csv"
    path.write_text("timestamp;abertura;maxima;minima;fechamento\n"+"".join(
        f"2026-11-18T09:00:0{i};100;100;100;100\n" for i in range(8)))
    frame = load_bars(path, 1, "ohlc")
    strategy = ("begin if CurrentBar=1 then BuyAtMarket(3); if CurrentBar=3 then SellToCoverAtMarket(1); "
                "if CurrentBar=5 then ReversePosition; end;")
    engine = Engine(compile_ntsl(strategy),frame,5,{},1,1,regras={"latencia_barras":1})
    engine.run()
    assert [fill["barra"] for fill in engine.fills] == [3,5,7,7,8]
    assert [fill["posicao"] for fill in engine.fills] == [3,2,0,-2,0]


def test_walk_forward_preserva_reserva(tmp_path):
    source = "input Q(1); begin if not HasPosition then BuyAtMarket(Q); end;"
    path = tmp_path/"ohlc.csv"
    path.write_text("timestamp;abertura;maxima;minima;fechamento\n"+"".join(
        f"2026-11-{day:02d}T09:00:0{i};{100+i*5};{100+i*5};{100+i*5};{100+i*5}\n"
        for day in range(16,21) for i in range(3)))
    config = dict(motor="ntsl", pregoes_teste=1, cache_ram_mb=16, threads=1, parametros={"Q":{"min":1,"max":2,"passo":1}},
                  walk_forward=dict(pregoes_busca=2,pregoes_teste=1,pregoes_reservados=1),
                  genetico=dict(populacao=2,geracoes=1,paciencia=0,min_sinais=0,semente=0,metrica="resultado_estavel"))
    replay = strategy_replay(path,source,1,"ohlc",config,5,.2)
    result = walk_forward(replay,config,tmp_path)
    assert [r["pregoes_teste"] for r in result["janelas"]] == [["2026-11-18"],["2026-11-19"]]
    assert result["pregoes_reservados"] == ["2026-11-20"]


def test_stop_limit_apos_gap_de_preco():
    from estrategia import Order
    frame = pd.DataFrame({"pregao":["2026-11-18"], "abertura":[120], "maxima":[125],
                          "minima":[100], "fechamento":[120]})
    engine = Engine(compile_ntsl("begin end;"), frame, 5, {}, 1, 1)
    order = Order("buyatstop", "long", "stop", 1, 105, 110)
    assert engine.match(order, 120, 125, 100) is None
    assert order.triggered
    assert engine.match(order, 110, 115, 105) == 110


def test_matriz_paridade(tmp_path):
    from tools.comparar_paridade import compare
    left = tmp_path/"profit.csv"
    right = tmp_path/"local.csv"
    header = "timestamp;sequencia;etapa;valor\n"
    left.write_text(header+"2026-11-18T09:15:00-03:00;1;sinal;1\n2026-11-18T09:15:00-03:00;2;execucao;100\n")
    right.write_text(header+"2026-11-18T12:15:00Z;1;sinal;1\n2026-11-18T12:15:00Z;2;execucao;105\n")
    _, matrix = compare(left, right)
    assert matrix.loc["sinal", "igual"] == 1
    assert matrix.loc["execucao", "divergente"] == 1


def test_coletor_reserva_exporta_series_do_mesmo_candle(tmp_path):
    path = tmp_path / "candles.csv"
    path.write_text(
        "timestamp;abertura;maxima;minima;fechamento;v_trades_atual;"
        "volume_contratos;volume_financeiro;v_agressao_saldo_referencia;v_vwap_barra\n"
        "2026-11-23 09:00:00;100;105;95;100;6;10;200;-3;100\n"
        "2026-11-23 09:01:00;110;115;105;110;12;20;440;5;110\n"
    )
    source = ROOT / "estrategias/indicadores/indicador_coleta_reserva_winz26_1min_v1_0.ntsl"
    engine = Engine(
        compile_ntsl(source.read_text(encoding="utf-8")),
        load_bars(path, 60, "ohlc"), 5, {}, 60, 0.20,
        regras={"volume_financeiro_ntsl": True, "agressao_referencia_injetada": True},
    )
    engine.run()

    assert engine.fills == []
    plots = ("plot", "plot2", "plot3", "plot4", "plot5")
    values = [tuple(row[key] for key in plots) for row in engine.trace]
    assert values[0] == (6, 10, 200, -3, 100)
    assert values[1] == pytest.approx((12, 20, 440, 5, (100 * 10 + 110 * 20) / 30))
