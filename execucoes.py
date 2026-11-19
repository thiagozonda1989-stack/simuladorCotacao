"""Pacotes reproduzíveis e histórico das execuções do aplicativo."""
from contextlib import contextmanager
import csv
import json
from datetime import datetime
from pathlib import Path
import re
import shutil
from time import monotonic
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

ID = r"[0-9a-f]{32}|\d{8}-\d{6}-\d{6}"
SCHEMA = "simuladorCotacao.execucao/1"
REPORTS = {"relatorio.html", "execucoes.csv", "candles.csv", "console.csv", "metricas.json",
           "inputs_otimizados.json", "estrategia.ntsl", "predicoes.csv", "evolucao.csv",
           "candidatos.csv", "modelo_parametrizado.ntsl"}


def utc_now():
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def to_json(data):
    return json.dumps(data, ensure_ascii=False, allow_nan=False)


class ExecutionArchive:
    def __init__(self, root, key):
        if not isinstance(key, str) or not re.fullmatch(ID, key):
            raise ValueError("Identificador de execução inválido.")
        self.root = root / key
        self.key = key
        self.package = self.root / "execucao.zip"
        self.manifest = self.root / "resumo.json"
        self.log = self.root / "execucao.jsonl"

    def event(self, name, **fields):
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write(to_json(dict(horario=utc_now(), evento=name, **fields)) + "\n")

    def summary(self):
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def save_summary(self, data):
        temporary = self.manifest.with_suffix(".tmp")
        temporary.write_text(to_json(data), encoding="utf-8")
        temporary.replace(self.manifest)

    def seal(self, summary, options, entry, destination):
        temporary = self.package.with_suffix(".tmp")
        try:
            with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=3) as package:
                package.writestr("resumo.json", to_json(summary))
                package.writestr("configuracao.json", to_json({
                    key: options[key] for key in ("modo", "csv", "formato", "segundos", "tick",
                                                  "valor_ponto", "opcoes", "cotacao") if key in options
                }))
                package.writestr("estrategia_original.ntsl", options["ntsl"].encode("utf-8"))
                if entry and entry.is_file():
                    package.write(entry, "dados.csv")
                package.write(self.log, self.log.name)
                trace = self.root / "avaliacoes.csv"
                if trace.is_file():
                    package.write(trace, trace.name)
                for name in sorted(REPORTS):
                    source = destination / name
                    if source.is_file():
                        package.write(source, name)
            temporary.replace(self.package)
        finally:
            temporary.unlink(missing_ok=True)

    def candidate(self, generation, names, genomes):
        trace = self.root / "avaliacoes.csv"
        create = not trace.exists()
        with trace.open("a", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            if create:
                writer.writerow(["geracao", *("input:" + name for name in names), "aptidao", "metricas_json"])
            for genome, fitness, metrics in genomes:
                writer.writerow([generation, *genome, fitness, to_json(metrics)])

    def settings(self, optimized=False):
        with ZipFile(self.package) as package:
            if "dados.csv" not in package.namelist():
                raise ValueError("O pacote não contém dados de entrada reutilizáveis.")
            options = read_small(package, "configuracao.json", 8*1024**2, as_json=True)
            source = "modelo_parametrizado.ntsl" if optimized else "estrategia_original.ntsl"
            if source not in package.namelist():
                raise ValueError("A estratégia otimizada não está disponível nesta execução.")
            if not isinstance(options, dict) or options.get("modo") not in {"estrategia", "otimizar"}:
                raise ValueError("Configuração de execução inválida.")
            options["ntsl"] = read_small(package, source, 8*1024**2)
            return options

    def extract_csv(self, destination, root):
        with ZipFile(self.package) as package:
            size = package.getinfo("dados.csv").file_size
            if size + 64*1024**2 > shutil.disk_usage(root).free:
                raise ValueError("Espaço insuficiente para reutilizar os dados de entrada.")
            with package.open("dados.csv") as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output, 4*1024**2)

    @classmethod
    def import_package(cls, root, source):
        try:
            with ZipFile(source) as package:
                summary = read_small(package, "resumo.json", 8*1024**2, as_json=True)
                if not isinstance(summary, dict) or summary.get("schema") != SCHEMA:
                    raise ValueError("Formato de pacote de execução incompatível.")
                if len(set(package.namelist())) != len(package.namelist()):
                    raise ValueError("O pacote contém arquivos duplicados.")
        except (BadZipFile, KeyError) as error:
            raise ValueError("Selecione um ZIP de execução do simulador.") from error
        record = cls(root, uuid4().hex)
        record.root.mkdir(parents=True)
        try:
            shutil.copyfile(source, record.package)
            record.save_summary(summary | {"id": record.key, "importado": True, "pacote": True})
        except Exception:
            shutil.rmtree(record.root, ignore_errors=True)
            raise
        return record


def read_small(package, name, limit, as_json=False):
    if package.getinfo(name).file_size > limit:
        raise ValueError(f"{name} excede o tamanho permitido.")
    value = package.read(name).decode("utf-8")
    return json.loads(value) if as_json else value


def history(root):
    records = []
    for path in root.glob("*/resumo.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(item, dict):
                records.append(item)
        except (OSError, ValueError):
            continue
    return sorted(records, key=lambda item: str(item.get("inicio", "")), reverse=True)


@contextmanager
def cli_audit(output, source, mode):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_name(output.name + ".execucao.jsonl")
    started = monotonic()
    result = {"estado": "concluido", "motivo": "fim dos dados"}

    def log_event(event, **fields):
        with log.open("a", encoding="utf-8") as stream:
            stream.write(to_json(dict(horario=utc_now(), evento=event, **fields)) + "\n")

    log_event("inicio", modo=mode, arquivo=Path(source).name)
    try:
        yield result
    except BaseException as error:
        result.update(estado="cancelado" if isinstance(error, KeyboardInterrupt) else "erro",
                      motivo="interrupção pelo usuário" if isinstance(error, KeyboardInterrupt) else str(error))
        raise
    finally:
        log_event("parada", segundos=round(monotonic()-started, 3), **result)
