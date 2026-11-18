"""Sessões portáteis do simulador, com gravação atômica."""
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile
from threading import Event
from time import monotonic
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import numpy as np

SCHEMA = 1
MAX_METADATA = 128 * 1024**2


def json_value(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Valor sem representação JSON: {type(value).__name__}")


class Session:
    def __init__(self, output, name, csv, options, resume=None, on_status=None):
        raw = options.get("salvar_minutos", 0)
        if type(raw) is not int or not 0 <= raw <= 1440:
            raise ValueError("Informe de 0 a 1440 minutos para o salvamento automático.")
        self.interval = raw * 60
        self.next_save = monotonic()+self.interval
        self.path = output / "sessoes" / (name + ".sessao.zip")
        self.csv = csv
        self.options = deepcopy({key:value for key,value in options.items()
                                 if key not in {"transferencia","solicitacao"}})
        self.resume = resume
        self.requested = Event()
        self.on_status = on_status
        self.snapshot = lambda: (None, None)

    def service(self):
        now = monotonic()
        if not self.requested.is_set() and not (self.interval and now >= self.next_save):
            return
        self.requested.clear()
        self.next_save = now+self.interval
        temp = None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            state, matrix = self.snapshot()
            metadata = dict(esquema=SCHEMA, opcoes=self.options, estado=state)
            with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as handle:
                temp = Path(handle.name)
            with ZipFile(temp,"w",ZIP_DEFLATED,compresslevel=1) as archive:
                with archive.open("sessao.json", "w") as member:
                    encoder = json.JSONEncoder(ensure_ascii=False, default=json_value)
                    pieces, length = [], 0
                    for piece in encoder.iterencode(metadata):
                        pieces.append(piece)
                        if len(pieces) >= 8192:
                            payload = "".join(pieces).encode("utf-8")
                            length += len(payload)
                            if length > MAX_METADATA:
                                raise ValueError("O estado da sessão excedeu 128 MiB.")
                            member.write(payload)
                            pieces.clear()
                    payload = "".join(pieces).encode("utf-8")
                    if length + len(payload) > MAX_METADATA:
                        raise ValueError("O estado da sessão excedeu 128 MiB.")
                    member.write(payload)
                archive.write(self.csv,"dados.csv")
                if matrix is not None:
                    with archive.open("historico.npy","w",force_zip64=True) as member:
                        np.save(member,matrix,allow_pickle=False)
            with temp.open("r+b") as handle:
                os.fsync(handle.fileno())
            temp.replace(self.path)
            if self.on_status:
                self.on_status({"arquivo": self.path.name, "mensagem": "Sessão salva.",
                                "horario": datetime.now().strftime("%H:%M:%S")})
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            if self.on_status:
                self.on_status({"arquivo":self.path.name if self.path.is_file() else None,
                                "mensagem":f"Falha ao salvar a sessão: {error}"})
        finally:
            self.next_save = monotonic() + self.interval
            if temp:
                temp.unlink(missing_ok=True)

    def checkpoint(self, control):
        while not control.cancelled.is_set():
            self.service()
            if control.ready.wait(.2):
                break
        control.checkpoint()


def load_session(package):
    try:
        with ZipFile(package) as archive:
            names = archive.namelist()
            if sorted(names) not in (["dados.csv","sessao.json"],["dados.csv","historico.npy","sessao.json"]):
                raise ValueError("O arquivo não contém uma sessão válida.")
            with archive.open("sessao.json") as member:
                raw = member.read(MAX_METADATA + 1)
            if len(raw) > MAX_METADATA:
                raise ValueError("Metadados da sessão excedem 128 MiB.")
            metadata = json.loads(raw)
            if not isinstance(metadata,dict) or metadata.get("esquema") != SCHEMA:
                raise ValueError("Versão de sessão incompatível.")
            options = metadata["opcoes"]
            state = metadata.get("estado")
            if (not isinstance(options,dict) or options.get("modo") not in {"otimizar","estrategia"}
                    or not isinstance(options.get("ntsl"),str) or not isinstance(options.get("opcoes"),dict)):
                raise ValueError("Configuração da sessão inválida.")
            if state is not None and not isinstance(state,dict):
                raise ValueError("Estado da sessão inválido.")
            if ("historico.npy" in names) != (options["modo"]=="estrategia" and state is not None):
                raise ValueError("Histórico da sessão ausente ou incompatível.")
            return options, state
    except (BadZipFile, KeyError, TypeError) as error:
        raise ValueError("O arquivo não contém uma sessão válida.") from error


def extract_csv(package, output):
    csv = None
    try:
        with ZipFile(package) as archive:
            info = archive.getinfo("dados.csv")
            if info.file_size + 64*1024**2 > shutil.disk_usage(output).free:
                raise ValueError("Espaço livre insuficiente para restaurar o CSV.")
            with tempfile.NamedTemporaryFile(dir=output, prefix="retomada-", suffix=".csv", delete=False) as handle:
                csv = Path(handle.name)
                with archive.open(info) as member:
                    shutil.copyfileobj(member, handle, 1024**2)
            return csv
    except BaseException:
        if csv:
            csv.unlink(missing_ok=True)
        raise
