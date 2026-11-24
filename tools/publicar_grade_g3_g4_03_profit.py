"""Confere G3, G4 e 03 em originais locais e publica somente derivados relativos."""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tools.publicar_ajuste_tick_saidas_venda import probe
from tools.publicar_prioridade_protecao_profit import HOURS, OHLC, file_info, pdf_totals, window_references
from tools.publicar_sonda_lacuna_profit import debug_blocks, number, raw_operation, write_csv
from tools.publicar_sondas_protecao_profit import TIMESTAMP_FORMAT, normalize_console, read_csv


EVIDENCIAS = Path("docs/colaboracao/evidencias")
PROTOCOLO = EVIDENCIAS / "WINZ26_ajuste_tick_saidas_venda_20261026_v1"
PRIORIDADE = EVIDENCIAS / "WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1"
NATIVO_ANTERIOR = EVIDENCIAS / "WINZ26_v5_8_prioridade_protecao_profit_20261026_v1"
ARQUIVOS = {
    "G3": ("G3_877_console.txt", "G3_877_OPERACOES.csv", "G3_877_RELATORIO.pdf", "G3_877_configuracao.png"),
    "G4": ("G4_447_1000_console.txt", "G4_447_1000_operacoes.csv", "G4_447_1000_relatorio.pdf",
           "G4_447_1000_configuracoes.png"),
    "03": ("SONDA_03_CONSOLE.txt", "SONDA_03_OPERACOES.csv", "SONDA_03_RELATORIO.pdf", "SONDA_03_CONFIGURACAO.png"),
}
NTSLS = {
    "G3": PROTOCOLO / "g3_alvo_compra_grade_profit_v1_0.ntsl",
    "G4": PROTOCOLO / "g4_stop_compra_grade_profit_v1_0.ntsl",
    "03": PRIORIDADE / "sonda_prioridade_mercado_protecao_profit_v1_0.ntsl",
}
REPLAYS = {
    "G3": (("bruto", {"p_Alvo": 877}, False), ("flag_venda", {"p_Alvo": 877}, True),
           ("grade_manual", {"p_Alvo": 875}, False)),
    "G4": (("bruto", {"p_Gatilho": 447, "p_Limite": 1000}, False),
           ("flag_venda", {"p_Gatilho": 447, "p_Limite": 1000}, True),
           ("grade_manual", {"p_Gatilho": 445, "p_Limite": 1000}, False)),
    "03": (("bruto", {"p_Perna": 2, "p_SaidaMercado": 0, "p_Alvo": 430, "p_Stop": 793, "p_Folga": 101}, False),
           ("flag_venda", {"p_Perna": 2, "p_SaidaMercado": 0, "p_Alvo": 430, "p_Stop": 793, "p_Folga": 101}, True)),
}


def native_console(case, raw, entry, bars):
    blocks = debug_blocks(raw)
    if len(blocks) != 2 or blocks[0] != blocks[1]:
        raise ValueError(f"{case}: esperados dois blocos completos idênticos.")
    prefix = "PRIORIDADE;" if case == "03" else f"GRADE_{case};"
    header, *lines = blocks[0]
    if header != "Modo de Debug" or any(not line.startswith(prefix) for line in lines):
        raise ValueError(f"{case}: há linhas adicionais a inspecionar.")
    assert raw.decode("utf-8-sig").splitlines()[0] == "Código em Execução"
    rows = normalize_console(case, lines, entry, number)
    side = 1 if case == "03" else -1
    entry_event = "SOLICITA_COMPRA" if side == 1 else "SOLICITA_VENDA"
    protection = "SOLICITA_ALVO" if case == "G3" else "SOLICITA_STOP"
    assert [(r["evento"], r["hora_contexto"]) for r in rows if r["evento"] != "AVALIACAO"] == [
        (entry_event, "10:51"), (protection, "10:52"),
    ]
    states = []
    for lineno, (row, line) in enumerate(zip(rows, lines, strict=True), 3):
        values = dict(value.split("=", 1) for value in line.split(";")[2:])
        row["linha_original"] = lineno
        assert row["data_ntsl"] == 1261026
        row["base_pts_entrada"] = number(values["base"]) - entry if "base" in values else ""
        if row["base_pts_entrada"] != "":
            assert row["base_pts_entrada"] == 0
        prices = {key: number(values[key]) for key in OHLC} if row["evento"] == "AVALIACAO" else {}
        if prices:
            assert prices == bars[row["hora_contexto"]]
            states.append((row["hora_contexto"], row["currentbar"], row["seq_avaliacao"],
                           row["posicao"], row["pendentes"]))
        row.update({f"{key}_pts_entrada": prices[key] - entry if key in prices else "" for key in OHLC})
    assert states == [
        (hour, bar, seq, position, pending)
        for seq, (hour, bar, position, pending) in enumerate(zip(
            [HOURS[0], *HOURS], [26873, *range(26873, 26881)],
            [0, side, side, side, side, 0, 0, 0, 0], [0, 0, 0, 1, 1, 0, 0, 0, 0], strict=True,
        ), 1)
    ]
    return rows


def native_case(case, root, bars):
    console, operations, report, screenshot = (root / name for name in ARQUIVOS[case])
    raw = operations.read_bytes()
    row = raw_operation(raw)
    direction = "C" if case == "03" else "V"
    assert (row["Ativo"], row["Lado"], row["Qtd Compra"], row["Qtd Venda"]) == ("WINZ26", direction, "1", "1")
    entry_side, exit_side = ("Compra", "Venda") if direction == "C" else ("Venda", "Compra")
    entry, exit_price = (number(row[f"Preço {side}"]) for side in (entry_side, exit_side))
    assert entry == bars["10:52"]["abertura"]
    timestamps = [datetime.strptime(row[key], TIMESTAMP_FORMAT) for key in ("Abertura", "Fechamento")]
    assert [stamp.isoformat() for stamp in timestamps] == ["2026-10-26T10:52:00", "2026-10-26T10:55:00"]
    net, fees, count = pdf_totals(report)
    delta = exit_price - entry
    points = delta if direction == "C" else -delta
    assert delta == {"G3": -875, "G4": 445, "03": -795}[case]
    assert (net, fees, count) == (number(row["Total"]), number(row["Comissões"]), 1)
    assert fees == 0 and net == points * Decimal("0.20")
    log = native_console(case, console.read_bytes(), entry, bars)
    order = log[4]
    assert (order["gatilho_pts_entrada"], order["limite_pts_entrada"]) == {
        "G3": ("", -877), "G4": (447, 1000), "03": (-793, -894),
    }[case]
    columns = ",".join(row.keys())
    fields = [
        ("console", 22, 11, "evento,data,hora,barra,seq,posicao,pendentes,abertura,maxima,minima,fechamento,"
         "base,gatilho,limite (conforme evento e sonda)"),
        ("operacoes", 1, 1, columns),
        ("relatorio", 1, 1, ""),
        ("configuracao", 1, 1, ""),
    ]
    inventory = [
        dict(sonda=case, fonte=kind, pregao="2026-10-26",
             periodo="10:51–10:58" if kind == "console" else "10:52:00–10:55:00" if kind == "operacoes" else "",
             itens_originais=original, itens_derivados=retained, campos=names,
             blocos_identicos=2 if kind == "console" else "") | file_info(path, path.read_bytes())
        for (kind, original, retained, names), path in zip(fields, (console, operations, report, screenshot), strict=True)
    ]
    return log, inventory, dict(
        fonte="Profit Backtest OHLC", entrada_execucao=str(timestamps[0].time()),
        saida_execucao=str(timestamps[1].time()), posicao_1055=0, pendentes_1055=0,
        solicitado_pts_entrada=order["limite_pts_entrada"] if case == "G3" else order["gatilho_pts_entrada"],
        efetivo_cadastro_pts_entrada="", limite_stop_solicitado_pts_entrada=(
            "" if case == "G3" else order["limite_pts_entrada"]),
        limite_stop_efetivo_cadastro_pts_entrada="", saida_pts_entrada=delta, pontos_contrato=points,
        liquido_brl=net, ordem_simulador="", ajuste_tick_simulador="", coincide_profit=1,
    )


def run_replays(case, raw_bars, work, native):
    original = NTSLS[case].read_text(encoding="utf-8-sig")
    converted = re.sub(r"FloatToString\(([^,\n]+),\s*0\)", r"(\1)", original).replace(", clYellow", "")
    source = work / f"{case}.ntsl"
    source.write_text(converted, encoding="utf-8")
    args = [
        sys.executable, "estrategia.py", "--csv", str(raw_bars), "--ntsl", str(source),
        "--formato", "ohlc", "--segundos", "60", "--tick", "5", "--valor-ponto", "0.2",
        "--avaliacao-pos-preenchimento", "--rastrear-ordens", "--protecoes-ate-cancelar",
    ]
    rows = []
    for profile, params, enabled in REPLAYS[case]:
        output = work / f"{case}-{profile}"
        inputs = output.with_suffix(".json")
        inputs.write_text(json.dumps(params), encoding="utf-8")
        cmd = [*args, "--inputs", str(inputs), "--saida", str(output)]
        if enabled:
            cmd.append("--ajuste-tick-saidas-venda")
        with output.with_suffix(".stdout.json").open("xb") as stdout:
            subprocess.run(cmd, check=True, stdout=stdout)
        actual = probe(output)
        actual["efetivo_cadastro_pts_entrada"] = actual.pop("efetivo_pts_entrada")
        actual["limite_stop_solicitado_pts_entrada"] = actual["limite_stop_efetivo_cadastro_pts_entrada"] = (
            actual.pop("limite_stop_pts_entrada"))
        actual["ajuste_tick_simulador"] = actual.pop("ajuste_tick")
        actual["liquido_brl"] = (actual["pontos_contrato"] * Decimal("0.20")).quantize(Decimal("0.01"))
        assert actual["entrada_execucao"] == native["entrada_execucao"]
        rows.append(dict(fonte=f"Simulador {profile}", **actual, coincide_profit=int(
            all(actual[key] == native[key] for key in ("saida_execucao", "saida_pts_entrada",
                                                      "posicao_1055", "pendentes_1055")),
        )))
    if case == "03":
        assert [row["coincide_profit"] for row in rows] == [0, 1]
    else:
        assert [row["coincide_profit"] for row in rows] == [0, 0, 1]
        assert {k: v for k, v in rows[0].items() if k != "fonte"} == {
            k: v for k, v in rows[1].items() if k != "fonte"
        }
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("originais", "barras", "replays", "saida"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args()
    bars, references = window_references(args.originais, args.barras)
    entry = bars["10:52"]["abertura"]
    geometry = [
        dict(hora_barra=hour, **{f"{key}_pts_entrada": values[key] - entry for key in OHLC})
        for hour, values in bars.items()
    ]
    assert [{key: str(value) for key, value in row.items()} for row in geometry] == read_csv(
        PROTOCOLO / "barras_referencia.csv", ";")
    native = {case: native_case(case, args.originais, bars) for case in ARQUIVOS}
    previous = {row["fonte"]: row for row in read_csv(NATIVO_ANTERIOR / "inventario_anexos.csv", ";")
                if row["arquivo"].startswith("03_stop_controle_")}
    comparison = []
    for row in native["03"][1]:
        old = next(item for item in previous.values() if item["arquivo"].split(".")[-1] == row["arquivo"].split(".")[-1])
        comparison.append(dict(fonte=row["fonte"], arquivo_novo=row["arquivo"], sha256_novo=row["sha256"],
                               arquivo_anterior=old["arquivo"], sha256_anterior=old["sha256"],
                               identico=int(row["sha256"] == old["sha256"])))
    assert [row["identico"] for row in comparison] == [1, 1, 0, 0]
    args.replays.mkdir()
    matrix = []
    for case, (_, _, profit) in native.items():
        common = dict(sonda=case, entrada_contexto="10:51", protecao_contexto="10:52", quantidade=1)
        matrix.extend(common | row for row in (profit, *run_replays(case, args.barras, args.replays, profit)))
    args.saida.mkdir()
    tables = {
        "inventario_anexos.csv": [row for _, inventory, _ in native.values() for row in inventory],
        "console_profit.csv": [row for log, _, _ in native.values() for row in log],
        "matriz_profit_simulador.csv": matrix,
        "barras_referencia.csv": geometry,
        "fontes_barras.csv": references,
        "comparacao_sonda_03.csv": comparison,
    }
    for name, rows in tables.items():
        write_csv(args.saida / name, rows)


if __name__ == "__main__":
    main()
