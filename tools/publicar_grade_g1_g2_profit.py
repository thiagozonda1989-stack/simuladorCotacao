"""Confere e publica a coleta nativa das sondas de grade G1 e G2."""
import argparse
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from tools.publicar_prioridade_protecao_profit import OHLC, file_info, pdf_totals, window_references
from tools.publicar_sonda_lacuna_profit import debug_blocks, number, raw_operation, write_csv
from tools.publicar_sondas_protecao_profit import TIMESTAMP_FORMAT, normalize_console, read_csv


CASES = (
    ("G1", "G1_ALVO_LIMITE", "SOLICITA_ALVO", "", 447, 445),
    ("G2", "G2_STOP_LIMITE", "SOLICITA_STOP", -877, -1000, -875),
)
EXTENSIONS = {"CONSOLE": "txt", "OPERACOES": "csv", "RELATORIO": "pdf", "CONFIGURACAO": "png"}


def read_native_log(case, data, entry, bars, kind):
    blocks = debug_blocks(data)
    if len(blocks) != 2 or blocks[0] != blocks[1]:
        raise ValueError(f"{case}: blocos completos não são idênticos.")
    header, *structured = blocks[0]
    if header != "Modo de Debug" or any(not line.startswith(f"GRADE_{case};") for line in structured):
        raise ValueError(f"{case}: mensagens não estruturadas exigem inspeção.")
    assert data.decode("utf-8-sig").splitlines()[0] == "Código em Execução"
    rows = normalize_console(case, structured, entry, number)
    requests = [r for r in rows if r["evento"] != "AVALIACAO"]
    assert [(r["evento"], r["hora_contexto"]) for r in requests] == [
        ("SOLICITA_COMPRA", "10:51"), (kind, "10:52"),
    ]
    states = []
    for index, (row, source) in enumerate(zip(rows, structured, strict=True), 3):
        original = dict(field.split("=", 1) for field in source.split(";")[2:])
        assert row["data_ntsl"] == 1261026
        row["linha_original"] = index
        row["base_pts_entrada"] = number(original["base"]) - entry if "base" in original else ""
        for field in OHLC:
            row[f"{field}_pts_entrada"] = ""
        if row["evento"] == "AVALIACAO":
            hour = row["hora_contexto"]
            prices = {field: number(original[field]) for field in OHLC}
            assert prices == bars[hour]
            for field in OHLC:
                row[f"{field}_pts_entrada"] = prices[field] - entry
            states.append((hour, row["posicao"], row["pendentes"]))
    assert states == [
        ("10:51", 0, 0), ("10:51", 1, 0), ("10:52", 1, 0), ("10:53", 1, 1), ("10:54", 1, 1),
        ("10:55", 0, 0), ("10:56", 0, 0), ("10:57", 0, 0), ("10:58", 0, 0),
    ]
    assert requests[1]["base_pts_entrada"] == 0
    return rows, requests[1], len(blocks)


def replay(name, root, expected, entry):
    target = root / name
    buy, sell = read_csv(target / "execucoes.csv")
    assert [r["acao"] for r in (buy, sell)] == ["long", "exit_long"]
    assert all(r["quantidade"] == "1" and r["pregao"] == "2026-10-26" for r in (buy, sell))
    assert Decimal(buy["preco"]) == entry and int(sell["posicao"]) == 0
    candles = read_csv(target / "candles.csv")
    times = [candles[int(row["barra"]) - 1]["timestamp"][11:19] for row in (buy, sell)]
    points = Decimal(sell["preco"]) - entry
    assert times == ["10:52:00", expected["saida_execucao"]]
    assert points == Decimal(expected["saida_pts_entrada"]) and sell["ordem"] == expected["ordem_simulador"]
    logs = normalize_console(name, [row["mensagem"] for row in read_csv(target / "console.csv")
                                    if row["mensagem"].startswith("GRADE_")], entry, Decimal)
    states = {row["hora_contexto"]: row for row in logs if row["evento"] == "AVALIACAO"}
    status = {f"{field}_{hour.replace(':', '')}": states[hour][field]
              for hour in ("10:53", "10:54", "10:55") for field in ("posicao", "pendentes")}
    assert all(status[key] == int(expected[key]) for key in expected.keys() & status.keys())
    return dict(entrada_execucao=times[0], saida_execucao=times[1], **status,
                saida_pts_entrada=points, resultado_brl=Decimal(sell["liquido_reais"]).quantize(Decimal("0.01")),
                ordem_simulador=sell["ordem"])


def collect(args):
    bars, sources = window_references(args.originais, args.barras)
    entry = bars["10:52"]["abertura"]
    geometry = [dict(hora_barra=hour, **{f"{key}_pts_entrada": value-entry for key, value in fields.items()})
                for hour, fields in bars.items()]
    previous_bars = read_csv(args.protocolo / "barras_referencia.csv", ";")
    assert [{key: str(value) for key, value in row.items()} for row in geometry] == previous_bars
    assert [bars["10:55"][k] - entry for k in OHLC] == [220, 445, -875, -260]
    previous = {row["controle"]: row for row in read_csv(args.protocolo / "replays_simulador.csv", ";")}
    all_rows, matrix, inventory = [], [], []
    for case, prefix, kind, gate, limit, native_points in CASES:
        paths = {spec: args.originais / f"{prefix}_{spec}.{ext}" for spec, ext in EXTENSIONS.items()}
        data = {spec: path.read_bytes() for spec, path in paths.items()}
        native = raw_operation(data["OPERACOES"])
        assert (native["Ativo"], native["Lado"], native["Qtd Compra"], native["Qtd Venda"]) == ("WINZ26", "C", "1", "1")
        buy, sell = (datetime.strptime(native[key], TIMESTAMP_FORMAT) for key in ("Abertura", "Fechamento"))
        assert [d.isoformat() for d in (buy, sell)] == ["2026-10-26T10:52:00", "2026-10-26T10:55:00"]
        assert number(native["Preço Compra"]) == entry and number(native["Preço Venda"]) - entry == native_points
        net, fees, count = pdf_totals(paths["RELATORIO"])
        assert (net, fees, count) == (number(native["Total"]), Decimal(0), 1)
        assert fees == number(native["Comissões"]) and net == Decimal(native_points) * Decimal("0.20")
        log, protection, copies = read_native_log(case, data["CONSOLE"], entry, bars, kind)
        assert (protection["gatilho_pts_entrada"], protection["limite_pts_entrada"]) == (gate, limit)
        all_rows.extend(log)
        inventory.extend(dict(sonda=case, fonte=spec.lower()) | file_info(path, data[spec]) | dict(
            blocos_identicos=copies if spec == "CONSOLE" else "",
            registros_retidos=len(log) if spec == "CONSOLE" else 1,
        ) for spec, path in paths.items())
        shared = dict(sonda=case, entrada_contexto="10:51", protecao_contexto="10:52",
                      quantidade=1, abertura_1055_pts_entrada=220, maxima_1055_pts_entrada=445,
                      minima_1055_pts_entrada=-875)
        matrix.append(shared | dict(fonte="Profit", gatilho_pts_entrada=gate, limite_pts_entrada=limit,
                                    entrada_execucao=str(buy.time()), saida_execucao=str(sell.time()),
                                    posicao_1053=1, pendentes_1053=1, posicao_1054=1, pendentes_1054=1,
                                    posicao_1055=0, pendentes_1055=0, saida_pts_entrada=native_points,
                                    resultado_brl=net, ordem_simulador=""))
        for profile, label in (("bruto", "Simulador bruto"), ("mais-proximo", "Simulador com níveis na grade")):
            name = f"{case.lower()}-{profile}"
            expected = previous[name]
            result = replay(name, args.replays, expected, entry)
            matrix.append(shared | dict(fonte=label, gatilho_pts_entrada=expected["gatilho_pts_entrada"],
                                        limite_pts_entrada=expected["limite_pts_entrada"]) | result)
    return {"inventario_anexos.csv": inventory, "console_profit.csv": all_rows,
            "matriz_profit_simulador.csv": matrix, "barras_referencia.csv": geometry,
            "fontes_barras.csv": sources}


def main():
    command = argparse.ArgumentParser(description=__doc__)
    for key in ("originais", "barras", "protocolo", "replays", "saida"):
        command.add_argument(f"--{key}", type=Path, required=True)
    args = command.parse_args()
    outputs = collect(args)
    args.saida.mkdir()
    for filename, rows in outputs.items():
        write_csv(args.saida / filename, rows)


if __name__ == "__main__":
    main()
