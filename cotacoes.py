"""Catálogo SQLite com cópias locais dos CSVs originais."""
import csv
from contextlib import closing
from datetime import date, datetime
import json
import shutil
import sqlite3
from uuid import uuid4

from estrategia import csv_format


def dated_rows(path, format_name):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter=";")
        header = next(reader)
        index = header.index("data_minuto_origem" if format_name == "profit" else "timestamp")
        yield header
        for row in reader:
            if not any(row):
                continue
            try:
                value = row[index].strip()
                day = (datetime.strptime(value, "%d/%m/%Y %H:%M").date() if format_name == "profit"
                       else datetime.fromisoformat(value).date())
            except (IndexError, ValueError) as error:
                raise ValueError(f"Data inválida no CSV, linha {reader.line_num}.") from error
            yield day.isoformat(), row


class Quotes:
    def __init__(self, root):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.database = root / "cotacoes.sqlite3"
        with closing(self.connect()) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS series (
                id TEXT PRIMARY KEY, papel TEXT NOT NULL, inicio TEXT NOT NULL, fim TEXT NOT NULL,
                segundos INTEGER NOT NULL, formato TEXT NOT NULL, observacao TEXT NOT NULL,
                arquivo TEXT NOT NULL, linhas INTEGER NOT NULL, colunas TEXT NOT NULL
            )""")

    def connect(self):
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def list(self):
        with closing(self.connect()) as connection:
            return [dict(row) | {"colunas": json.loads(row["colunas"])} for row in connection.execute(
                "SELECT * FROM series ORDER BY papel, inicio DESC, segundos, id")]

    def add(self, path, data):
        papel = str(data.get("papel", "")).strip().upper()
        seconds = data.get("segundos")
        if not papel or len(papel) > 40 or type(seconds) is not int or seconds < 1:
            raise ValueError("Informe o papel e uma periodicidade positiva em segundos.")
        fmt = csv_format(path, data.get("formato", "auto"))
        if fmt == "profit" and 60 % seconds:
            raise ValueError("Para indicador Profit, informe uma periodicidade que divida 60 segundos.")
        rows = dated_rows(path, fmt)
        header = next(rows)
        low, high, count = "9999-12-31", "", 0
        for day, _ in rows:
            low, high, count = min(low, day), max(high, day), count + 1
        if not count:
            raise ValueError("O CSV está vazio.")
        start = data.get("inicio") or low
        end = data.get("fim") or (start if data.get("inicio") else high)
        for day in (start, end):
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("Informe a data no formato AAAA-MM-DD.")
        if not start <= low <= high <= end:
            raise ValueError(f"O intervalo informado precisa conter todas as datas do CSV ({low} a {high}).")
        key = uuid4().hex
        destination = self.root / (key + ".csv")
        try:
            shutil.copyfile(path, destination)
            with closing(self.connect()) as connection, connection:
                connection.execute("INSERT INTO series VALUES (?,?,?,?,?,?,?,?,?,?)",
                                   (key, papel, low, high, seconds, fmt,
                                    str(data.get("observacao", ""))[:2000], str(data.get("arquivo", ""))[:255], count, json.dumps(header)))
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return key

    def select(self, key, start, end):
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT * FROM series WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise ValueError("Selecione uma série da base de cotações.")
        for day in (start, end):
            if day and date.fromisoformat(day).isoformat() != day:
                raise ValueError("Informe a data no formato AAAA-MM-DD.")
        start, end = start or row["inicio"], end or row["fim"]
        if not row["inicio"] <= start <= end <= row["fim"]:
            raise ValueError("Selecione um intervalo dentro das datas disponíveis.")
        return dict(row) | {"colunas": json.loads(row["colunas"])}, self.root / (row["id"] + ".csv"), start, end


def slice_csv(source, destination, fmt, start, end, checkpoint):
    with closing(dated_rows(source, fmt)) as rows, destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(next(rows))
        count = 0
        for index, (day, row) in enumerate(rows):
            if index % 65536 == 0:
                checkpoint()
            if start <= day <= end:
                writer.writerow(row)
                count += 1
        if not count:
            raise ValueError("O intervalo selecionado não contém registros de cotação.")
