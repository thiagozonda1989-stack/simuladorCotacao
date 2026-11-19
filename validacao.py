"""Balanço de validação de um modelo parametrizado, por execução e por operação."""
import csv
from html import escape
from collections import defaultdict

import numpy as np
import pandas as pd

from diagnostico import chart


def reference_time(frame, bar):
    row = frame.iloc[bar-1]
    if "minuto" in row:
        stamp = row["minuto"]
        return stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M"), "minuto de origem (Profit)"
    stamp = row["timestamp"] if "timestamp" in row else row["inicio"]
    return stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M:%S"), "referência do candle OHLC"


def ledger(frame, fills, point_value, asset):
    rows = []
    trade = 0
    position = 0
    basis = balance = 0.0
    opened_date = opened_time = ""
    for fill in fills:
        date, time, precision = reference_time(frame, fill["barra"])
        entry = fill["acao"] in {"long", "short"}
        price, quantity = fill["preco"], fill["quantidade"]
        if not position:
            trade += 1
            opened_date, opened_time = date, time
        if entry:
            basis = (basis*abs(position) + price*quantity)/(abs(position)+quantity)
        position = fill["posicao"]
        gross = fill["pontos_contrato"] * point_value
        cost = fill["custo_reais"]
        net = gross-cost
        balance += net
        rows.append(dict(operacao=trade, sequencia=len(rows)+1, ativo=asset, pregao=fill["pregao"],
                         data=date, hora=time, referencia_horario=precision, barra=fill["barra"],
                         data_abertura_operacao=opened_date, hora_abertura_operacao=opened_time,
                         evento="Entrada" if entry else ("Saída parcial" if position else "Saída final"),
                         lado="Compra" if fill["acao"] in {"long","exit_short"} else "Venda",
                         ordem=fill["ordem"], tipo=fill["tipo"], volume_contratos=quantity,
                         preco_execucao=price, preco_medio_entrada=basis, posicao=position,
                         pontos_contrato=fill["pontos_contrato"], bruto_reais=gross, taxas_reais=cost,
                         liquido_reais=net, saldo_acumulado_reais=balance))
        if not position:
            basis = 0.0
    return rows


FIELDS = ("operacao", "sequencia", "ativo", "pregao", "data", "hora", "referencia_horario", "barra",
          "data_abertura_operacao", "hora_abertura_operacao", "evento", "lado", "ordem", "tipo",
          "volume_contratos", "preco_execucao", "preco_medio_entrada", "posicao", "pontos_contrato",
          "bruto_reais", "taxas_reais", "liquido_reais", "saldo_acumulado_reais")


def br(value):
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def export_validation(output, frame, fills, summary, asset):
    rows = ledger(frame, fills, summary["valor_por_ponto"], asset)
    with (output/"validacao.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter=";")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: (f"{value:.12g}".replace(".", ",") if isinstance(value, float) else value)
                             for key,value in row.items()})
    daily = {str(day): [0,0,0.0,0.0,0.0] for day in frame["pregao"].unique()}
    trades = defaultdict(float)
    for row in rows:
        counts = daily[row["pregao"]]
        counts[0] += 1
        counts[1] += row["volume_contratos"]
        for index,key in enumerate(("bruto_reais","taxas_reais","liquido_reais"),2):
            counts[index] += row[key]
        trades[row["operacao"]] += row["liquido_reais"]
    wins = sum(pnl > 1e-9 for pnl in trades.values())
    gains = sum(pnl for pnl in trades.values() if pnl>1e-9)
    losses = -sum(pnl for pnl in trades.values() if pnl < -1e-9)
    stats = dict(operacoes=len(trades), operacoes_positivas=wins,
                 operacoes_negativas=sum(pnl < -1e-9 for pnl in trades.values()),
                 taxa_acerto=wins/len(trades) if trades else None,
                 fator_lucro=gains/losses if losses else None,
                 resultado_medio_reais=sum(trades.values())/len(trades) if trades else None,
                 volume_contratos=sum(row["volume_contratos"] for row in rows), ativo=asset)
    balance = np.r_[0, [row["saldo_acumulado_reais"] for row in rows]]
    drawdown = balance-np.maximum.accumulate(balance)
    indices = np.unique(np.linspace(0, len(balance)-1, min(350,len(balance)), dtype=int))
    series = [dict(geracao=int(i), saldo=float(balance[i]), drawdown=float(drawdown[i])) for i in indices]
    graphs = chart(series, [("saldo", "Saldo líquido (R$)")], "Curva de resultado", axis="Execução")
    graphs += chart(series, [("drawdown", "Drawdown (R$)")], "Queda a partir do pico", axis="Execução")
    graphs += chart([dict(geracao=idx, resultado=totals[4]) for idx,totals in enumerate(daily.values(),1)],
                    [("resultado","Líquido diário (R$)")], "Resultado por pregão", axis="Pregão")
    write_pdf(output/"nota_corretagem_simulada.pdf", rows, daily, summary | stats)
    return stats, graphs


def write_pdf(path, rows, daily, metrics):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    styles = getSampleStyleSheet()
    title = "Nota de corretagem simulada"
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=26, rightMargin=26,
                            topMargin=24, bottomMargin=28, title=title)
    def table(data, widths, numeric_from):
        result = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        result.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#183e39")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8), ("ALIGN",(numeric_from,1),(-1,-1),"RIGHT"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#edf4f2")]),
            ("BOTTOMPADDING",(0,0),(-1,-1),5), ("TOPPADDING",(0,0),(-1,-1),5),
        ]))
        return result

    rates = (f"{metrics['taxa_acerto']:.1%}".replace(".",",") if metrics["taxa_acerto"] is not None else "—")
    first, last = next(iter(daily), "—"), next(reversed(daily), "—")
    story = [Paragraph(title, styles["Title"]),
             Paragraph(f"Validação NTSL • {escape(metrics['ativo'])} • {first} a {last}", styles["Heading2"]),
             Paragraph("Demonstrativo de operações simuladas, sem validade fiscal. "
                       "Horários são referências dos candles; no CSV Profit com origem por minuto, "
                       "os segundos ficam indisponíveis.", styles["BodyText"]), Spacer(1,10)]
    story.append(table([
        ["Operações","Execuções","Contratos negociados","Acerto","Bruto (R$)","Taxas (R$)","Líquido (R$)","Drawdown (R$)"],
        [metrics["operacoes"], len(rows), metrics["volume_contratos"], rates,
         *[br(metrics[key]) for key in ("resultado_bruto_convertido","custos_reais","resultado_liquido_reais","drawdown_liquido_reais")]],
    ], [80,80,110,75,100,100,100,105],0))
    story.append(Paragraph("Balanço por pregão", styles["Heading2"]))
    story.append(table([["Pregão","Execuções","Contratos","Bruto (R$)","Taxas (R$)","Líquido (R$)"]] +
                       [[day,*values[:2],*(br(v) for v in values[2:])] for day,values in daily.items()],
                       [105,90,90,110,110,110],1))
    story.append(Paragraph("Detalhamento das execuções", styles["Heading2"]))
    if rows:
        lines = [["Op.","Data","Hora","Evento / lado","Qtd.","Preço","Médio ent.","Bruto (R$)","Taxas (R$)","Líquido (R$)","Acum. (R$)"]]
        for row in rows:
            event = f'{row["evento"]} / {row["lado"]}'
            lines.append([row["operacao"], row["data"], row["hora"], event, row["volume_contratos"],
                          *[br(row[key]) for key in ("preco_execucao","preco_medio_entrada","bruto_reais",
                                                     "taxas_reais","liquido_reais","saldo_acumulado_reais")]])
        story.append(table(lines, [27,62,48,107,36,77,77,72,72,85,85],4))
    else:
        story.append(Paragraph("Nenhuma ordem executada no período.", styles["BodyText"]))

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#405a55"))
        canvas.drawString(26,15,"Simulador de Cotação  |  Demonstrativo simulado")
        canvas.drawRightString(document.pagesize[0]-26,15,f"Página {document.page}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
