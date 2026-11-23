"""Publica a evidência de toque tardio da S1, sem ordens ou preços brutos."""

import argparse
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from tools.publicar_sonda_lacuna_profit import debug_blocks, number, raw_operation, write_csv
from tools.publicar_sondas_protecao_profit import TIMESTAMP_FORMAT, native_console, read_csv


DAY = "2026-10-26"
HOURS = [f"10:{n}" for n in range(51, 59)]
PRICES = ("abertura", "maxima", "minima", "fechamento")
BR_DATE = "%d/%m/%Y %H:%M"
XML = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def profit_bars(data):
    values = list(csv.reader(io.StringIO(data.decode("cp1252")), delimiter=";"))
    return [(datetime.strptime(time, BR_DATE), *(number(price) for price in prices))
            for time, *prices in values[1:]]


def workbook_bars(data):
    with ZipFile(io.BytesIO(data)) as workbook:
        sheet = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows = sheet.findall("x:sheetData/x:row", XML)
        epoch = datetime(1899, 12, 30)
        result = []
        for row in rows[1:]:
            stamp, *prices = (Decimal(cell.findtext("x:v", namespaces=XML)) for cell in row)
            minute = round(stamp * 1440)
            result.append((epoch + timedelta(minutes=minute), *prices))
        return result


def replay_order_rows(data, sonda, entry_backtest, exit_backtest):
    export = list(csv.reader(io.StringIO(data.decode("cp1252")), delimiter=";"))
    header = export[1]
    if len(header) != 26:
        raise ValueError("Formato inesperado na lista de ordens do Replay.")
    orders = [dict(zip(header, line, strict=True)) for line in export[2:] if len(line) == len(header)]
    buy, = [order for order in orders if order["Lado"] == "C"]
    sell, = [order for order in orders if order["Lado"] == "V"]
    entry_replay = number(buy["Preço Médio"])
    result = []
    aliases = {"C": "entrada", "V": "protecao"}
    for index, line in enumerate(export[2:], 1):
        if not line:
            continue
        row = dict(zip(header, line))
        if row["Status"] != "Trade":
            parent = row
        side = parent["Lado"]
        average = number(row["Preço Médio"])
        result.append(dict(
            sonda=sonda, sequencia_exportacao=index, ordem_alias=aliases[side],
            lado=side, tipo_ordem=parent["Tipo de Ordem"], estado_linha=row["Status"],
            data_hora_replay_coluna_criacao=row["Criação"],
            data_ultima_atualizacao_linha=row.get("Última Atualização", "").split(" ")[0],
            quantidade_executada=row["Qtd Executada"],
            media_pts_entrada_replay=average - entry_replay,
            limite_pts_entrada_replay=number(row["Preço"]) - entry_replay if row.get("Preço") not in (None, "", "-") else "",
            campo_preco_stop_informado=int(row.get("Preço Stop") not in (None, "", "-")),
        ))
    return result, dict(
        sonda=sonda, ordens_resumidas=len(orders), linhas_trade=sum(row["estado_linha"] == "Trade" for row in result),
        entrada_replay_menos_backtest_pts=entry_replay - entry_backtest,
        saida_replay_menos_backtest_pts=number(sell["Preço Médio"]) - exit_backtest,
        resultado_replay_pts=number(sell["Preço Médio"]) - entry_replay,
    )


def collect(args):
    tables = {name: [] for name in (
        "matriz_profit_simulador.csv", "console_profit.csv", "barras_conferencia.csv",
        "ordens_replay_relativas.csv", "comparacao_replay_backtest.csv", "inventario.csv",
        "cobertura_barras.csv", "operacoes_profit.csv",
    )}

    def source(name, fmt, rows=""):
        data = (args.originais / name).read_bytes()
        tables["inventario.csv"].append(dict(
            arquivo=name, tamanho_bytes=len(data), sha256=sha256(data).hexdigest(), formato=fmt, registros=rows,
        ))
        return data

    previous = read_csv(args.referencia / "matriz_profit_simulador.csv", ";")
    prepared = read_csv(args.referencia / "barras_relativas.csv", ";")
    all_bars = {}
    for kind, expected in (("alvo", Decimal(430)), ("stop", Decimal(-795))):
        sonda = "s1_" + kind
        stem = "SONDA_S1_" + kind.upper()
        operation = raw_operation(source(f"{stem}_operacoes.csv", "CSV CP1252", 1))
        opening, closing = (datetime.strptime(operation[key], TIMESTAMP_FORMAT) for key in ("Abertura", "Fechamento"))
        entry, exit_price = map(number, (operation["Preço Compra"], operation["Preço Venda"]))
        if (opening.strftime("%Y-%m-%d %H:%M"), closing.strftime("%Y-%m-%d %H:%M")) != (DAY + " 10:52", DAY + " 10:55"):
            raise ValueError(f"{sonda}: operação fora da janela.")
        if operation["Ativo"] != "WINZ26" or operation["Lado"] != "C" or (operation["Qtd Compra"],operation["Qtd Venda"]) != ("1", "1"):
            raise ValueError(f"{sonda}: ativo, lado ou quantidade divergentes.")
        points = exit_price - entry
        if points != expected or number(operation["Total"]) != points * Decimal("0.20"):
            raise ValueError(f"{sonda}: execução diferente do nível previsto.")

        tables["operacoes_profit.csv"].append(dict(
            sonda=sonda, pregao=opening.date(), ativo=operation["Ativo"], lado=operation["Lado"],
            quantidade_compra=operation["Qtd Compra"], quantidade_venda=operation["Qtd Venda"],
            hora_entrada_csv=opening.time(), hora_saida_csv=closing.time(),
            entrada_pts_referencia=0, saida_pts_referencia=points,
            duracao_segundos=int((closing - opening).total_seconds()),
            comissoes_brl=number(operation["Comissões"]), resultado_brl=number(operation["Total"]),
        ))

        console_data = source(f"{stem}_console.txt", "TXT UTF-8")
        blocks, console, warnings = native_console(sonda, console_data, stem, entry)
        if blocks != 2 or len(console) != 11 or warnings:
            raise ValueError(f"{sonda}: captura difere da sequência esperada.")
        tables["inventario.csv"][-1]["registros"] = len(console)
        tables["console_profit.csv"].extend(console)
        protection, = [row for row in console if row["evento"] in ("SOLICITA_ALVO", "SOLICITA_STOP")]
        nivel = protection["limite_pts_entrada"] if kind == "alvo" else protection["gatilho_pts_entrada"]
        assert nivel == points and protection["hora_contexto"] == "10:52"
        assert protection["limite_pts_entrada"] == (430 if kind == "alvo" else -895)
        states = {row["hora_contexto"]: row for row in console if row["evento"] == "AVALIACAO"}
        pending = [states[hour]["pendentes"] for hour in HOURS[2:6]]
        assert pending == [1, 1, 0, 0] and states["10:55"]["posicao"] == 0
        assert not any("LIMPEZA" in row["evento"] for row in console)

        bars = profit_bars(source(f"{stem}_barras.csv", "CSV CP1252"))
        all_bars[kind] = bars
        tables["inventario.csv"][-1]["registros"] = len(bars)
        stamps = [row[0] for row in bars]
        assert all(later > earlier for earlier, later in zip(stamps[1:], stamps))
        tables["cobertura_barras.csv"].append(dict(
            sonda=sonda, registros=len(bars), menor_timestamp=stamps[-1],
            maior_timestamp=stamps[0], timestamps_duplicados=len(stamps) - len(set(stamps)),
            lacunas_intradiarias_maiores_60s=sum(
                earlier.date() == later.date() and later - earlier > timedelta(minutes=1)
                for earlier, later in zip(stamps[1:], stamps)
            ),
            lacunas_janela_sonda=0,
        ))
        keys = {row[0].strftime("%H:%M"): row[1:] for row in bars if str(row[0].date()) == DAY}
        assert keys["10:52"][0] == entry
        evaluations = []
        for line in debug_blocks(console_data)[0]:
            if line.startswith(f"{stem};AVALIACAO;"):
                fields = dict(part.split("=", 1) for part in line.split(";")[2:])
                evaluations.append(fields)
        assert [int(number(row["barra"])) for row in evaluations] == [26873, *range(26873, 26881)]
        assert len(evaluations) == len(HOURS) + 1
        for evaluation, hour in zip(evaluations, [HOURS[0], *HOURS], strict=True):
            stamp = str(int(number(evaluation["hora"]))).zfill(4)
            assert f"{stamp[:2]}:{stamp[2:]}" == hour
            assert tuple(number(evaluation[field]) for field in PRICES) == keys[hour]

        for bar in prepared:
            hour = bar["hora_barra"]
            relative = {f"{field}_pts_entrada": value - entry for field, value in zip(PRICES, keys[hour])}
            assert all(Decimal(bar[key]) == value for key, value in relative.items())
            tables["barras_conferencia.csv"].append(dict(sonda=sonda, hora_barra=hour, **relative))
        source(f"{stem}_relatorio.pdf", "PDF conferido à parte", 1)
        source(f"{stem}_config.png", "PNG conferido à parte", 1)
        data = source(f"lista_ordens_s1_{kind}_replay.csv", "CSV CP1252, Replay")
        orders, comparison = replay_order_rows(data, sonda, entry, exit_price)
        tables["inventario.csv"][-1]["registros"] = len(orders)
        tables["ordens_replay_relativas.csv"].extend(orders)
        tables["comparacao_replay_backtest.csv"].append(comparison)

        controls = [row for row in previous if row["sonda"] == sonda]
        diagnostic, = [row for row in controls if row["modo"] == "diagnostico"]
        assert diagnostic["hora_preenchimento_protecao"] == closing.strftime("%H:%M")
        assert Decimal(diagnostic["pontos_saida"]) == points
        tables["matriz_profit_simulador.csv"].extend(
            row for row in controls if row["motor"] == "Simulador"
        )
        tables["matriz_profit_simulador.csv"].append(dict(
            sonda=sonda, motor="Profit", modo="Backtest OHLC", contexto_envio_protecao="10:52",
            nivel_pts_entrada=nivel,limite_pts_entrada=protection["limite_pts_entrada"],
            pendentes_t1=pending[0],pendentes_t2=pending[1],pendentes_t3=pending[2],pendentes_t4=pending[3],
            hora_preenchimento_protecao=closing.strftime("%H:%M"), hora_saida_limpeza="",
            pontos_saida=points, resultado_liquido_brl=number(operation["Total"]),
            classificacao="preenchida após espera",
        ))
    workbook = workbook_bars(source("[Pasta1]SONDA_S1_ALVO_barras", "XLSX sem extensão"))
    tables["inventario.csv"][-1]["registros"] = len(workbook)
    assert workbook == all_bars["alvo"]
    target = {row[0]: row[1:] for row in all_bars["alvo"]}
    stop = {row[0]: row[1:] for row in all_bars["stop"]}
    assert all(target[stamp] == stop[stamp] for stamp in target.keys() & stop.keys())
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("originais", "referencia", "saida"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    tables = collect(args)
    args.saida.mkdir(exist_ok=False)
    for name, rows in tables.items():
        write_csv(args.saida / name, rows)


if __name__ == "__main__":
    main()
