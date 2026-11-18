"""Interface local do Simulador de Cotação e entrada para o executável CLI."""
import argparse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile
from time import monotonic
from threading import Lock, Thread
from urllib.parse import urlsplit
import webbrowser

from diagnostico import charts
from estrategia import csv_format, main as strategy_cli, run_strategy, strategy_replay
from simulador import NTSLModel, Replay, main as simulator_cli, optimize, read_export, validate_ohlc

APP = Path(__file__).resolve().parent
VERSION = (APP/"VERSION").read_text().strip()
REPORTS = {"relatorio.html", "execucoes.csv", "candles.csv", "console.csv", "metricas.json", "inputs_otimizados.json",
           "estrategia.ntsl", "predicoes.csv", "evolucao.csv", "candidatos.csv", "modelo_parametrizado.ntsl"}
MIB = 1024**2


def launcher_cli(args):
    if args == ["--version"]:
        print(VERSION)
        return
    if not args or args[0] in {"-h", "--help"}:
        print("simuladorCotacao", VERSION)
        print("Comandos: estrategia | otimizar | candles")
        print("Use <comando> --help para consultar os argumentos.")
        return
    command = args[0]
    sys.argv = [sys.argv[0], *args[1:]] if command == "estrategia" else [sys.argv[0], *args]
    (strategy_cli if command == "estrategia" else simulator_cli)()


class Workspace:
    def __init__(self, output):
        self.output = output.resolve()
        self.token = secrets.token_urlsafe(24)
        self.pending_input = None
        self.upload_transfer = None
        self.last_request = None
        self.started_at = None
        self.job = {"estado": "pronto"}
        self.lock = Lock()

    def upload(self, stream, length):
        if length <= 0:
            raise ValueError("Selecione um CSV de dados.")
        with self.lock:
            if self.job["estado"] == "executando":
                raise ValueError("Aguarde a execução atual.")
            if length + 64*MIB > shutil.disk_usage(self.output).free:
                raise ValueError("Espaço livre insuficiente para receber o CSV.")
            with tempfile.NamedTemporaryFile(prefix="entrada-", suffix=".csv", dir=self.output,
                                             delete=False) as destination:
                path = Path(destination.name)
                try:
                    remaining = length
                    while remaining:
                        block = stream.read(min(4*MIB,remaining))
                        if not block:
                            raise ValueError("Transferência local interrompida.")
                        destination.write(block)
                        remaining -= len(block)
                except BaseException:
                    destination.close()
                    path.unlink(missing_ok=True)
                    raise
            if self.pending_input:
                self.pending_input.unlink(missing_ok=True)
            self.pending_input = path

    def upload_chunk(self, stream, length, transfer, offset, total):
        if (not re.fullmatch(r"[a-zA-Z0-9-]{16,64}", transfer) or not 0 < length <= 4*MIB
                or offset < 0 or offset+length > total):
            raise ValueError("Bloco do CSV inválido.")
        with self.lock:
            if self.job["estado"] == "executando":
                raise ValueError("Aguarde a execução atual.")
            current = self.upload_transfer
            if current is None or current[0] != transfer:
                if offset != 0:
                    raise ValueError("O envio do CSV expirou. Selecione o arquivo novamente.")
                if total + 64*MIB > shutil.disk_usage(self.output).free:
                    raise ValueError("Espaço livre insuficiente para receber o CSV.")
                with tempfile.NamedTemporaryFile(prefix="blocos-", suffix=".csv",
                                                 dir=self.output, delete=False) as destination:
                    path = Path(destination.name)
                if current and current[1] != self.pending_input:
                    current[1].unlink(missing_ok=True)
                self.upload_transfer = current = (transfer, path, total)
            _, path, expected = current
            received = path.stat().st_size
            if expected != total or offset > received or offset < received < offset+length:
                raise ValueError("Sequência de blocos do CSV inválida.")
            block = stream.read(length)
            if len(block) != length:
                raise ValueError("Transferência local interrompida.")
            if offset == received:
                with path.open("r+b") as destination:
                    destination.seek(received)
                    try:
                        destination.write(block)
                        destination.flush()
                    except OSError:
                        destination.truncate(received)
                        raise
                received += length
            if received == total:
                if self.pending_input and self.pending_input != path:
                    self.pending_input.unlink(missing_ok=True)
                self.pending_input = path
            return received

    def start(self, options):
        with self.lock:
            request = options.get("solicitacao")
            if request and self.last_request == request:
                return self.job["id"]
            if self.job["estado"] == "executando":
                raise ValueError("Já existe uma execução em andamento.")
            if not self.pending_input:
                raise ValueError("O CSV ainda não foi carregado.")
            transfer = options.get("transferencia")
            if transfer and (not self.upload_transfer or
                             self.upload_transfer[:2] != (transfer, self.pending_input)):
                raise ValueError("O CSV desta solicitação foi substituído. Envie o arquivo novamente.")
            source = options["ntsl"]
            if not isinstance(source,str) or not source.strip():
                raise ValueError("Carregue ou cole uma estratégia NTSL.")
            name = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            path = self.pending_input
            self.pending_input = None
            if self.upload_transfer and self.upload_transfer[1] == path:
                self.upload_transfer = None
            self.started_at = monotonic()
            self.job = {"estado": "executando", "id": name, "parcial": {"etapa":"preparacao"}}
            self.last_request = request
            Thread(target=self.run,args=(path,name,options),daemon=True).start()
            return name

    def run(self, csv, name, options):
        destination = self.output/name
        try:
            if options["modo"] == "estrategia":
                def replay_progress(snapshot):
                    self.job = self.job | {"parcial": snapshot}
                run_strategy(csv,options["ntsl"], destination,int(options["segundos"]),
                             options["formato"],float(options["tick"]),options["opcoes"],float(options.get("valor_ponto",1)), on_progress=replay_progress)
            elif options["modo"] == "otimizar":
                requested = options["formato"]
                config = options["opcoes"]
                config["segundos_por_candle"] = int(options["segundos"])
                config["versao"] = VERSION
                seconds = config["segundos_por_candle"]
                if config.get("motor") == "ntsl":
                    replay = strategy_replay(csv, options["ntsl"], seconds, requested, config,
                                             float(options["tick"]), float(options.get("valor_ponto",1)))
                else:
                    if csv_format(csv, requested) != "profit":
                        raise ValueError("A otimização do ensemble requer CSV de indicador Profit.")
                    with tempfile.TemporaryDirectory() as tmp:
                        path = Path(tmp)/"estrategia.ntsl"
                        path.write_text(options["ntsl"],encoding="utf-8")
                        model = NTSLModel(path)
                    frame = read_export(csv,seconds)
                    validate_ohlc(frame)
                    replay = Replay(frame, model, seconds, config.get("classe_alvo", "1C"),
                                    config.get("alvo"), config.get("campos_excluidos", ()))
                destination.mkdir()
                def resources(plan):
                    self.job = self.job | {"recursos": plan}

                def progress(history, names):
                    self.job = self.job | {"graficos": charts(history[-100:], names,
                                                    financial=replay.specification.get("modo") == "resultado")}

                def partial(snapshot):
                    self.job = self.job | {"parcial": snapshot}

                optimize(replay, config, destination, progress, resources, partial)
            else:
                raise ValueError("Modo de execução desconhecido.")
        except Exception as error:
            self.job = self.job | {"estado":"erro","mensagem":str(error),"segundos":round(monotonic()-self.started_at)}
        else:
            self.job = self.job | {"estado":"concluido","pasta":str(destination),"segundos":round(monotonic()-self.started_at)}
        finally:
            csv.unlink(missing_ok=True)


def build_handler(workspace):
    prefix = "/" + workspace.token
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass

        def route(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                return None
            if self.command == "POST" and self.headers.get("Origin") != f"http://127.0.0.1:{self.server.server_port}":
                return None
            path = urlsplit(self.path).path
            return path[len(prefix):] if path.startswith(prefix+"/") else None

        def send_bytes(self,body,mime,status=200):
            self.send_response(status)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("Referrer-Policy","no-referrer")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            self.wfile.write(body)

        def json(self,item,status=200):
            self.send_bytes(json.dumps(item,ensure_ascii=False).encode(),"application/json; charset=utf-8",status)

        def do_GET(self):
            path = self.route()
            if path == "/":
                self.send_bytes((APP/"interface.html").read_bytes(),"text/html; charset=utf-8")
            elif path == "/estado":
                job = workspace.job
                if job["estado"] == "executando":
                    job = job | {"segundos": round(monotonic()-workspace.started_at)}
                self.json(job)
            elif path == "/modelo-exemplo":
                self.send_bytes((APP/"modelo_profit.ntsl").read_bytes(),"text/plain; charset=utf-8")
            elif path == "/config-exemplo":
                self.send_bytes((APP/"config_v7.json").read_bytes(),"application/json; charset=utf-8")
            elif path and path.startswith("/resultados/"):
                pieces = path.split("/")
                if (len(pieces)!=4 or not re.fullmatch(r'\d{8}-\d{6}-\d{6}',pieces[2])
                        or pieces[3] not in REPORTS):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                file = workspace.output.joinpath(*pieces[2:])
                if not file.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type",mime)
                self.send_header("Content-Length",str(file.stat().st_size))
                self.send_header("X-Content-Type-Options","nosniff")
                self.send_header("Referrer-Policy","no-referrer")
                if file.suffix != ".html":
                    self.send_header("Content-Disposition",f'attachment; filename="{file.name}"')
                self.end_headers()
                with file.open("rb") as stream:
                    shutil.copyfileobj(stream,self.wfile,length=MIB)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            path = self.route()
            if path not in {"/csv","/csv-bloco","/executar","/encerrar"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                if path == "/encerrar":
                    if workspace.job["estado"] == "executando":
                        raise ValueError("Aguarde a execução antes de encerrar.")
                    self.json({"ok":True})
                    Thread(target=self.server.shutdown, daemon=True).start()
                    return
                length = int(self.headers.get("Content-Length","0"))
                if path == "/csv":
                    workspace.upload(self.rfile,length)
                elif path == "/csv-bloco":
                    self.connection.settimeout(35)
                    offset = workspace.upload_chunk(
                        self.rfile, length, self.headers.get("X-Upload-Id",""),
                        int(self.headers.get("X-Upload-Offset","-1")),
                        int(self.headers.get("X-Upload-Size","-1")))
                    self.json({"recebido": offset})
                    return
                elif 0 < length <= 8*MIB:
                    options = json.loads(self.rfile.read(length))
                    if not isinstance(options.get("opcoes"),dict):
                        raise ValueError("As opções precisam ser um objeto JSON.")
                    job = workspace.start(options)
                    self.json({"ok":True,"id":job})
                    return
                else:
                    raise ValueError("O código e a configuração excedem 8 MiB ou estão vazios.")
                self.json({"ok":True})
            except (BrokenPipeError, ConnectionResetError):
                return
            except TimeoutError:
                self.json({"erro":"O envio do bloco expirou."},408)
            except (ValueError,OSError,KeyError,TypeError) as error:
                self.json({"erro":str(error)},400)
    return Handler


def serve(output,open_browser):
    output.mkdir(parents=True,exist_ok=True)
    workspace = Workspace(output)
    with ThreadingHTTPServer(("127.0.0.1",0),build_handler(workspace)) as server:
        url = f"http://127.0.0.1:{server.server_port}/{workspace.token}/"
        print(url,flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        finally:
            if workspace.pending_input:
                workspace.pending_input.unlink(missing_ok=True)
            if workspace.upload_transfer:
                workspace.upload_transfer[1].unlink(missing_ok=True)


def main():
    if sys.stdout is None:
        import os
        sys.stdout = open(os.devnull,"w",encoding="utf-8")
        sys.stderr = sys.stdout
    if len(sys.argv)>1 and sys.argv[1]=="--cli":
        launcher_cli(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sem-navegador",action="store_true")
    parser.add_argument("--resultados",type=Path,default=Path.home()/"simuladorCotacao"/"resultados")
    args = parser.parse_args()
    try:
        serve(args.resultados,not args.sem_navegador)
    except OSError as error:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(error),"Simulador de Cotação",0x10)
        raise


if __name__=="__main__":
    main()
