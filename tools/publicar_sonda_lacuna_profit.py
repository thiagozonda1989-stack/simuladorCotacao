"""Extrai evidência compartilhável da sonda Profit de retomada de lacuna."""

import argparse
import csv
import io
import re
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def debug_blocks(data):
    blocks = []
    for line in data.decode("utf-8-sig").splitlines():
        if line == "Código em Execução":
            blocks.append([])
        elif blocks:
            blocks[-1].append(line)
    return [block for block in blocks if block]


def read_console(data, case):
    blocks = [
        structured for block in debug_blocks(data)
        if (structured := [line for line in block if line.startswith("LACUNA;")])
    ]
    if not blocks or any(block != blocks[0] for block in blocks):
        raise ValueError("O console precisa conter um bloco ou cópias idênticas.")
    result = []
    for index, line in enumerate(blocks[0], 1):
        _, event, *fields = line.split(";")
        values = dict(item.split("=", 1) for item in fields)
        if event == "AVALIACAO":
            if int(values["caso"]) != case:
                raise ValueError("Valor de p_Caso inconsistente no console.")
            context = values
        elif context["seq"] != values["seq"]:
            raise ValueError("Solicitação fora da sequência da avaliação correspondente.")
        stamp = context["hora"].zfill(4)
        result.append({
            "p_caso": case, "ordem_console": index, "evento": event,
            "data_ntsl": context["data"].replace(".", ""), "hora_contexto_console": stamp[:2] + ":" + stamp[2:],
            "currentbar": context["barra"].replace(".", ""), "sequencia_avaliacao": values["seq"],
            "posicao_avaliacao": context["posicao"], "pendentes_avaliacao": context["pendentes"],
        })
    return len(blocks), result


def number(text):
    return Decimal(text.replace(".", "").replace(",", "."))


def raw_operation(data):
    raw = csv.reader(io.StringIO(data.decode("cp1252")), delimiter=";")
    header = next(row for row in raw if row[:2] == ["Ativo", "Abertura"])
    values, = [row for row in raw if row]
    return dict(zip(header, values, strict=True))


def read_operation(data, case=1):
    def timestamp(value):
        return datetime.strptime(value, "%d/%m/%Y %H:%M:%S")

    operation = raw_operation(data)
    opening, closing = (timestamp(operation[key]) for key in ("Abertura", "Fechamento"))
    return {
        "p_caso": case, "pregao": opening.date(), "ativo": operation["Ativo"], "lado": operation["Lado"],
        "quantidade_compra": operation["Qtd Compra"], "quantidade_venda": operation["Qtd Venda"],
        "hora_entrada_csv": opening.time(), "hora_saida_csv": closing.time(),
        "duracao_segundos": int((closing - opening).total_seconds()),
        "variacao_pontos": number(operation["Preço Venda"]) - number(operation["Preço Compra"]),
        "resultado_brl": number(operation["Total"]), "comissoes_brl": number(operation["Comissões"]),
    }


def read_teste2(source, output):
    inventory = []
    events = []
    operations = []

    def collect(name, format_name, copies="", retained=""):
        data = (source / name).read_bytes()
        inventory.append({
            "arquivo": name, "bytes": len(data), "sha256": sha256(data).hexdigest(),
            "formato": format_name, "blocos_identicos": copies, "linhas_ou_paginas_retidas": retained,
        })
        return data

    for case in (0, 1, 2):
        data = collect(f"console_sondav3_p_{case}_teste2.txt", "TXT UTF-8")
        copies, rows = read_console(data, case)
        events.extend(rows)
        inventory[-1].update(blocos_identicos=copies, linhas_ou_paginas_retidas=len(rows))
        if case:
            operation = collect(f"operacoes_sondav3_p_caso{case}_teste2.csv", "CSV CP1252", retained=1)
            operations.append(read_operation(operation, case))
            collect(f"relatorio_sondav3_p_caso{case}_teste2.pdf", "PDF verificado à parte")
        collect(f"evidencia_sondav3_p_{case}_teste2.png", "PNG verificado à parte")

    entry = number(raw_operation(operation)["Preço Compra"])
    protections = []
    warnings = []
    for block_index, block in enumerate(debug_blocks(data), 1):
        index = 0
        for line in block:
            if line.startswith("LACUNA;"):
                index += 1
                if block_index == 1 and line.startswith(("LACUNA;SOLICITA_ALVO;", "LACUNA;SOLICITA_STOP;")):
                    _, event, *fields = line.split(";")
                    values = dict(item.split("=", 1) for item in fields)
                    protections.append({
                        "p_caso": 2, "ordem_console": index, "evento": event,
                        "sequencia_avaliacao": values["seq"],
                        "gatilho_pontos_relativos": number(values["gatilho"]) - entry if "gatilho" in values else "",
                        "limite_pontos_relativos": number(values["limite"]) - entry,
                    })
            if line.startswith("SellToCoverStop enviado com stop em"):
                pattern = r"stop em ([0-9.]+), acima da abertura do candle \(([0-9.]+)\)"
                threshold, opening = re.search(pattern, line).groups()
                warnings.append({
                    "p_caso": 2, "bloco_console": block_index, "depois_do_evento_estruturado": index,
                    "gatilho_pontos_relativos": number(threshold) - entry,
                    "abertura_mencionada_pontos_relativos": number(opening) - entry,
                    "mensagem_resumida": "Stop de venda acima da abertura, com possível comportamento diferente na automação",
                })

    output.mkdir(exist_ok=False)
    write_csv(output / "console_profit_normalizado.csv", events)
    write_csv(output / "operacoes_profit_relativas.csv", operations)
    write_csv(output / "inventario_fontes.csv", inventory)
    write_csv(output / "solicitacoes_protecao_relativas.csv", protections)
    if warnings:
        write_csv(output / "avisos_profit_relativos.csv", warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originais", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--teste2", action="store_true", help="Processa os três anexos de console da segunda captura.")
    args = parser.parse_args()
    if args.teste2:
        read_teste2(args.originais, args.saida)
        return
    inventory = []
    events = []
    for case in (0, 1):
        file = args.originais / f"console_sondaV3_p_caso{case}.txt"
        content = file.read_bytes()
        copies, rows = read_console(content, case)
        events.extend(rows)
        inventory.append({
            "arquivo": file.name, "bytes": len(content), "sha256": sha256(content).hexdigest(),
            "formato": "TXT UTF-8", "blocos_identicos": copies, "linhas_ou_paginas_retidas": len(rows),
        })
    file = args.originais / "operacoes_sondav3_p_caso1.csv"
    content = file.read_bytes()
    operation = read_operation(content)
    inventory.append({
        "arquivo": file.name, "bytes": len(content), "sha256": sha256(content).hexdigest(),
        "formato": "CSV CP1252", "blocos_identicos": "", "linhas_ou_paginas_retidas": 1,
    })
    file = args.originais / "relatorio_sondav3_p_caso1.pdf"
    content = file.read_bytes()
    inventory.append({
        "arquivo": file.name, "bytes": len(content), "sha256": sha256(content).hexdigest(),
        "formato": "PDF verificado à parte", "blocos_identicos": "", "linhas_ou_paginas_retidas": "",
    })
    args.saida.mkdir(exist_ok=False)
    write_csv(args.saida / "console_profit_normalizado.csv", events)
    write_csv(args.saida / "operacao_profit_relativa.csv", [operation])
    write_csv(args.saida / "inventario_fontes.csv", inventory)


if __name__ == "__main__":
    main()
