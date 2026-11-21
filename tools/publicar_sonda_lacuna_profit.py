"""Extrai evidência compartilhável da sonda Profit de retomada de lacuna."""

import argparse
import csv
import io
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_console(data, case):
    blocks = []
    for line in data.decode("utf-8-sig").splitlines():
        if line == "Código em Execução":
            blocks.append([])
        elif line.startswith("LACUNA;"):
            blocks[-1].append(line)
    blocks = [block for block in blocks if block]
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


def read_operation(data):
    def timestamp(value):
        return datetime.strptime(value, "%d/%m/%Y %H:%M:%S")

    raw = csv.reader(io.StringIO(data.decode("cp1252")), delimiter=";")
    header = next(row for row in raw if row[:2] == ["Ativo", "Abertura"])
    values, = [row for row in raw if row]
    operation = dict(zip(header, values, strict=True))
    opening, closing = (timestamp(operation[key]) for key in ("Abertura", "Fechamento"))
    return {
        "p_caso": 1, "pregao": opening.date(), "ativo": operation["Ativo"], "lado": operation["Lado"],
        "quantidade_compra": operation["Qtd Compra"], "quantidade_venda": operation["Qtd Venda"],
        "hora_entrada_csv": opening.time(), "hora_saida_csv": closing.time(),
        "duracao_segundos": int((closing - opening).total_seconds()),
        "variacao_pontos": number(operation["Preço Venda"]) - number(operation["Preço Compra"]),
        "resultado_brl": number(operation["Total"]), "comissoes_brl": number(operation["Comissões"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--originais", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
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
