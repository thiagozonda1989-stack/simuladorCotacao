import csv

import pytest

from estrategia import ExecutionRules, run_strategy
from replay_ticks import load_events


def sample(tmp_path, rows):
    path = tmp_path/"negocios.csv"
    path.write_text("timestamp;preco;quantidade;sequencia\n"+"".join(
        f"2026-11-18T09:15:{clock};{price};{volume};{sequence}\n"
        for clock, price, volume, sequence in rows))
    return path


def fills(path):
    with (path/"execucoes.csv").open() as stream:
        return list(csv.DictReader(stream))


def test_entrada_saida_no_mesmo_candle_com_parciais(tmp_path):
    path = sample(tmp_path, [
        ("01.100",100,20,1), ("01.120",101,1,2), ("01.130",102,1,3),
        ("01.140",103,2,4), ("01.150",110,1,5), ("01.160",110,3,6),
    ])
    source = """input p_Exec_Tick(1); begin
    if CurrentBar=1 then BuyAtMarket(4);
    if CurrentBar=4 then SellToCoverLimit(110,4);
    end;"""
    output = tmp_path/"tick"
    metrics = run_strategy(path,source,output,60,"negocios",1,regras={"motor_ticks":True},
                           validacao="WIN")
    ledger = fills(output)
    assert [int(row["sequencia_evento"]) for row in ledger]==[2,3,4,5,6]
    assert [int(row["quantidade"]) for row in ledger]==[1,1,2,1,3]
    assert [int(row["posicao"]) for row in ledger]==[1,2,4,3,0]
    assert metrics["eventos"]==6 and metrics["motor_execucao"]=="tick_a_tick"
    assert metrics["resultado_liquido_reais"] == pytest.approx(31)
    assert "09:15:01.120" in (output/"validacao.csv").read_text()


def test_latencia_e_ordem_dos_ticks_empatados(tmp_path):
    path = sample(tmp_path, [
        ("01.100",105,5,2),("01.100",100,5,1),("01.110",106,5,3),
        ("01.120",107,5,4),("01.140",110,5,5)
    ])
    output = tmp_path/"tick"
    source = "begin if CurrentBar=1 then BuyAtMarket(1); end;"
    run_strategy(path,source,output,60,"negocios",1,regras={"motor_ticks":True,"latencia_ticks_ms":20})
    ledger = fills(output)
    assert ledger[0]["sequencia_evento"]=="4"
    assert ledger[0]["preco"]=="107.0"
    assert ledger[-1]["fechamento_sintetico"]=="True"


def test_ordem_nao_executa_no_evento_que_gerou_o_sinal(tmp_path):
    path = sample(tmp_path,[("01.100",105,2,2),("01.100",100,2,1)])
    output = tmp_path/"tick"
    run_strategy(path,"begin if CurrentBar=1 then BuyAtMarket; end;",output,60,"negocios",1,
                 regras={"motor_ticks":True})
    assert fills(output)[0]["sequencia_evento"]=="2"


def test_lacuna_cancela_ordem_tick(tmp_path):
    path = sample(tmp_path,[("01.100",100,2,1),("07.100",90,2,2)])
    output = tmp_path/"tick"
    metrics = run_strategy(path,"begin if CurrentBar=1 then BuyAtLimit(95); end;",output,60,"negocios",1,
                           regras={"motor_ticks":True,"lacuna_ticks_ms":1000})
    assert metrics["ordens_canceladas_lacuna"] == 1
    assert not fills(output)


def test_tick_rejeita_empate_sem_sequencia(tmp_path):
    path = tmp_path/"negocios.csv"
    path.write_text("timestamp;preco;quantidade\n2026-11-18T09:15:01.100;100;1\n2026-11-18T09:15:01.100;101;1\n")
    with pytest.raises(ValueError, match="coluna sequencia"):
        load_events(path,"negocios",ExecutionRules(motor_ticks=True))


def test_tick_stop_limit_dispara_e_aguarda_preco_compativel(tmp_path):
    path = sample(tmp_path,[("01.100",100,2,1),("01.110",115,2,2),("01.120",110,2,3)])
    output = tmp_path/"tick"
    run_strategy(path,"begin if CurrentBar=1 then BuyAtStop(105,110); end;",output,60,"negocios",1,
                 regras={"motor_ticks":True})
    assert fills(output)[0]["sequencia_evento"]=="3"
