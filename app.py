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
from urllib.parse import parse_qs, urlsplit
import webbrowser
from zipfile import BadZipFile
from execucoes import ExecutionArchive, ID, REPORTS, SCHEMA, history, utc_now
import github_execucoes

from cotacoes import Quotes, slice_csv
from ntsl import parameterized_ntsl
from sessao import Session, extract_csv, load_session
from controle import ProcessingCancelled, ProcessingControl
from diagnostico import charts
from estrategia import csv_format, main as strategy_cli, run_strategy, strategy_replay
from simulador import NTSLModel, Replay, main as simulator_cli, optimize, read_export, search_target, validate_ohlc

APP = Path(__file__).resolve().parent
VERSION = (APP/"VERSION").read_text().strip()
MIB = 1024**2


def launcher_cli(args):
    if args == ["--version"]:
        print(VERSION)
        return
    if not args or args[0] in {"-h", "--help"}:
        print("simuladorCotacao", VERSION)
        print("Comandos: estrategia | otimizar | candles | integrar")
        print("Use <comando> --help para consultar os argumentos.")
        return
    command = args[0]
    if command == "integrar":
        from integrar_profitrtd import main as integrate_cli
        sys.argv = [sys.argv[0], *args[1:]]
        integrate_cli()
        return
    sys.argv = [sys.argv[0], *args[1:]] if command == "estrategia" else [sys.argv[0], *args]
    (strategy_cli if command == "estrategia" else simulator_cli)()


class Workspace:
    def __init__(self, output):
        self.output = output.resolve()
        self.history = self.output / "historico"
        self.token = secrets.token_urlsafe(24)
        self.pending_input = None
        self.upload_transfer = None
        self.last_request = None
        self.started_at = None
        self.control = None
        self.job = {"estado": "pronto"}
        self.lock = Lock()
        self.quotes = Quotes(self.output.parent / "cotacoes")

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

    def save_quotes(self, data):
        with self.lock:
            if self.job["estado"] == "executando":
                raise ValueError("Aguarde a execução atual.")
            transfer = data.get("transferencia")
            if not self.pending_input or not self.upload_transfer or self.upload_transfer[:2] != (transfer, self.pending_input):
                raise ValueError("Envie o CSV antes de cadastrá-lo.")
            identifier = self.quotes.add(self.pending_input, data)
            self.pending_input.unlink(missing_ok=True)
            self.pending_input = self.upload_transfer = None
            return identifier

    def choose_parameters(self, data):
        name = data.get("id", "")
        criterion = data.get("criterio", "objetivo")
        if not re.fullmatch(r"\d{8}-\d{6}-\d{6}", name):
            raise ValueError("Execução inválida.")
        folder = self.output / name
        summary = json.loads((folder / "metricas.json").read_text(encoding="utf-8"))
        criterion = summary["metrica"] if criterion == "objetivo" else criterion
        if criterion not in {"f1", "accuracy", "balanced_accuracy", "precision", "recall",
                             "specificity", "npv", "resultado", "resultado_menos_drawdown", "resultado_estavel", "metas_classes"}:
            raise ValueError("Critério indisponível.")
        best = None
        with (folder / "selecionaveis.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                params, stats = json.loads(line)
                if criterion not in stats:
                    continue
                rank = (stats[criterion], stats[summary["metrica"]])
                if best is None or rank > best[0]:
                    best = rank, params, stats
        if best is None:
            raise ValueError("Nenhum candidato elegível para este critério.")
        _, params, stats = best
        result = dict(parametros=params, metricas=stats, criterio=criterion)
        if data.get("estrategia"):
            source = folder / "estrategia.ntsl"
            if summary["motor"] == "ntsl":
                result["ntsl"] = parameterized_ntsl(source.read_text(encoding="utf-8"), params)
            elif (folder / "modelo_parametrizado.ntsl").is_file():
                result["ntsl"] = NTSLModel(source).patched(params)
            else:
                raise ValueError("Este alvo ou ensemble modificado exige o motor Replay NTSL para exportar a estratégia.")
        return result

    def start(self, options, restore=False):
        with self.lock:
            request = options.get("solicitacao")
            if request and self.last_request == request:
                return self.job["id"]
            if self.job["estado"] == "executando":
                raise ValueError("Já existe uma execução em andamento.")
            selected = None if restore else options.get("serie")
            quote = None
            if selected:
                quote = self.quotes.select(selected, options.get("inicio"), options.get("fim"))
                meta, _, start, end = quote
                if meta["formato"] != "negocios" and int(options["segundos"]) != meta["segundos"]:
                    raise ValueError("Use a periodicidade cadastrada para candles prontos.")
                options = options | {"formato": meta["formato"], "csv": meta["arquivo"],
                                     "cotacao": meta | {"inicio_selecionado": start, "fim_selecionado": end}}
            reused = None
            if not restore and options.get("historico_id") and not quote:
                reused = ExecutionArchive(self.history, options["historico_id"])
                previous = reused.settings()
                if previous.get("cotacao"):
                    options = options | {"cotacao":previous["cotacao"]}
            if not self.pending_input and not quote and not reused:
                raise ValueError("O arquivo ainda não foi carregado.")
            transfer = options.get("transferencia")
            if transfer and (not self.upload_transfer or
                             self.upload_transfer[:2] != (transfer, self.pending_input)):
                raise ValueError("O arquivo desta solicitação foi substituído. Envie o arquivo novamente.")
            name = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            path = self.pending_input
            state = None
            if restore:
                share = options.get("publicar_github") is True
                options, state = load_session(path)
                options["publicar_github"] = share
            rules = (options.get("regras_execucao") if "regras_execucao" in options
                     else options.get("opcoes", {}).get("regras_execucao")) or {}
            options["regras_execucao"] = dict(ordem_so_proxima_barra=not restore,
                                              historico_continuo=not restore) | rules
            if options.get("modo") not in {"estrategia", "otimizar", "validar"}:
                raise ValueError("Modo de execução desconhecido.")
            if options["modo"] == "validar":
                asset = str(options.get("ativo") or (options.get("cotacao") or {}).get("papel") or "").strip().upper()
                if asset and asset != "NÃO INFORMADO" and not re.fullmatch(r"[A-Z0-9][A-Z0-9._ -]{0,39}", asset):
                    raise ValueError("Informe um código de ativo de até 40 caracteres.")
                options["ativo"] = asset or "NÃO INFORMADO"
            source = options["ntsl"]
            if not isinstance(source, str) or not source.strip():
                raise ValueError("Carregue ou cole uma estratégia NTSL.")
            archive = ExecutionArchive(self.history, name)
            archive.root.mkdir(parents=True)
            try:
                session = Session(self.output, name, path, options, state, self.saved_session)
            except Exception:
                archive.root.rmdir()
                raise
            if quote or reused:
                path = self.output / (name + "-entrada.csv")
                session.csv = path
            else:
                self.pending_input = None
            self.session = session
            if self.upload_transfer and self.upload_transfer[1] == path:
                self.upload_transfer = None
            self.control = ProcessingControl()
            self.started_at = monotonic()
            self.job = {"estado": "executando", "id": name, "parcial": {"etapa":"preparacao"},
                        "salvar_minutos": self.session.interval // 60, "modo": options["modo"]}
            self.last_request = request
            Thread(target=self.run, args=(path, name, options, restore, quote, reused, archive), daemon=True).start()
            return name

    def saved_session(self, status):
        with self.lock:
            self.job = self.job | {"sessao": status}

    def publish(self, **fields):
        with self.lock:
            self.job = self.job | fields

    def control_job(self, job_id, command):
        with self.lock:
            if self.job.get("id") != job_id or self.job["estado"] != "executando" or self.job.get("empacotando"):
                raise ValueError("Esta execução já terminou ou não está ativa.")
            ExecutionArchive(self.history, job_id).event("comando", comando=command)
            if command == "salvar-sessao":
                if self.control.cancelled.is_set():
                    raise ValueError("O processamento está sendo cancelado.")
                self.job = self.job | {"sessao": self.job.get("sessao", {}) |
                                       {"mensagem": "Salvamento solicitado. Aguardando um ponto seguro."}}
                self.session.requested.set()
            elif command == "finalizar":
                if (self.job["modo"] != "otimizar" or self.control.cancelled.is_set()
                        or self.job["parcial"]["etapa"] not in {"preparacao", "busca"}):
                    raise ValueError("A busca já terminou ou não está em andamento.")
                self.control.finish_requested.set()
                self.control.resume()
            elif command == "cancelar":
                self.control.cancel()
            elif not (self.control.cancelled.is_set() or self.control.finish_requested.is_set()):
                if command == "pausar":
                    self.control.pause()
                else:
                    self.control.resume()

    def run(self, path, name, options, restore, quote, reused, archive):
        destination = self.output/name
        control, session = self.control, self.session
        csv = None if restore else path
        resume_archive = path if restore else None
        summary = {}
        input_ready = not (quote or reused or restore)
        initial = dict(schema=SCHEMA, id=name, versao=VERSION, inicio=utc_now(), modo=options["modo"],
                       arquivo=Path(str(options.get("csv") or "dados.csv")).name, formato=options.get("formato"),
                       segundos_candle=options.get("segundos"), cotacao=options.get("cotacao"),
                       origem=options.get("historico_id"))
        last_stage = None
        def track(snapshot):
            nonlocal last_stage
            stage = snapshot["etapa"]
            if stage != last_stage:
                archive.event("etapa", etapa=stage)
                last_stage = stage
            self.publish(parcial=snapshot)

        try:
            archive.event("inicio", modo=initial["modo"], arquivo=initial["arquivo"],
                          formato=initial["formato"], segundos_candle=initial["segundos_candle"],
                          origem=initial["origem"], restaurado=restore,
                          github_solicitado=options.get("publicar_github") is True)
            archive.save_summary(initial | {"estado": "iniciada", "pacote": False})
            if reused:
                reused.extract_csv(csv, self.output)
            if quote:
                meta, original, start, end = quote
                if start == meta["inicio"] and end == meta["fim"]:
                    csv = original
                    session.csv = original
                else:
                    slice_csv(original, csv, meta["formato"], start, end, control.checkpoint)
            if restore:
                csv = extract_csv(path, self.output)
                session.csv = csv
            input_ready = True
            if control.cancelled.is_set():
                control.checkpoint()
            if options["modo"] in {"estrategia", "validar"}:
                def replay_progress(snapshot):
                    track(snapshot | {"valor_ponto": float(options.get("valor_ponto", 1))})
                run_strategy(csv,options["ntsl"], destination,int(options["segundos"]),
                             options["formato"],float(options["tick"]),options["opcoes"],float(options.get("valor_ponto",1)), on_progress=replay_progress, checkpoint=control.checkpoint,
                             session=session, resume_archive=resume_archive, safe_point=lambda: session.checkpoint(control), regras=options.get("regras_execucao"),
                             validacao=options.get("ativo", "NÃO INFORMADO") if options["modo"] == "validar" else None,
                             on_validation=lambda stats, graphs: self.publish(graficos=graphs, validacao=stats))
            elif options["modo"] == "otimizar":
                requested = options["formato"]
                config = options["opcoes"]
                config["segundos_por_candle"] = int(options["segundos"])
                config["versao"] = VERSION
                config["regras_execucao"] = options.get("regras_execucao") or config.get("regras_execucao", {})
                config.pop("cotacao", None)
                if config.get("walk_forward"):
                    raise ValueError("Execute walk_forward na CLI com o arquivo de configuração.")
                if options.get("cotacao"):
                    config["cotacao"] = options["cotacao"]
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
                                    search_target(config), config.get("campos_excluidos", ()))
                destination.mkdir()
                def resources(plan):
                    archive.event("recursos", **plan)
                    self.publish(recursos=plan)

                def progress(history, names):
                    archive.event("geracao", **history[-1])
                    self.publish(graficos=charts(history[-100:], names,
                                                 financial=replay.specification.get("modo") == "resultado"))

                optimize(replay, config, destination, progress, resources, track, control, session, archive.candidate)
            else:
                raise ValueError("Modo de execução desconhecido.")
            session.checkpoint(control)
            outcome = {"estado":"concluido", "pasta":str(destination), "parada":"fim dos dados"}
            summary = json.loads((destination / "metricas.json").read_text(encoding="utf-8"))
            if options["modo"] == "otimizar":
                outcome |= {"parada":summary["parada"], "exportavel":(destination/"modelo_parametrizado.ntsl").is_file(),
                            "tem_candidatos":summary["atende_min_sinais"], "motor":summary["motor"],
                            "financeiro":summary["alvo"].get("modo") == "resultado"}
        except ProcessingCancelled:
            outcome = {"estado":"cancelado", "parada":"cancelamento solicitado pelo usuário"}
        except Exception as error:
            outcome = {"estado":"erro", "parada":str(error), "mensagem":str(error)}
        finally:
            with self.lock:
                if control.cancelled.is_set():
                    outcome = {"estado":"cancelado", "parada":"cancelamento solicitado pelo usuário"}
                self.job = self.job | {"empacotando":True}
            if outcome["estado"] != "concluido" and destination.is_dir():
                shutil.rmtree(destination, ignore_errors=True)
            seconds = round(control.elapsed(self.started_at))
            indicators = {key: summary[key] for key in ("candidatos_avaliados", "metrica", "resultado_bruto_convertido", "resultado_liquido_reais", "custos_reais", "drawdown_liquido_reais",
                                                         "taxa_acerto", "fator_lucro", "operacoes", "ativo", "lacunas_intradiarias",
                                                         "lacunas_com_posicao", "ordens_canceladas_lacuna",
                                                         "parametros_otimizados", "resultados") if key in summary}
            finished = initial | {"fim":utc_now(), "segundos":seconds, "estado":outcome["estado"],
                                  "parada":outcome["parada"], "indicadores":indicators,
                                  "reutilizavel":bool(input_ready and csv and csv.is_file()), "pacote":True,
                                  "otimizada":(destination/"modelo_parametrizado.ntsl").is_file()}
            try:
                archive.event("parada", estado=outcome["estado"], motivo=outcome["parada"], segundos=seconds)
                archive.seal(finished, options, csv if input_ready else None, destination)
                if options.get("publicar_github") is True:
                    try:
                        finished["github"] = github_execucoes.publish(archive.package, finished)
                        archive.event("github_publicado", url=finished["github"])
                    except Exception as error:
                        finished["github_erro"] = str(error)
                        archive.event("github_erro", mensagem=str(error))
            except Exception as error:
                finished |= {"pacote":False, "reutilizavel":False, "erro_pacote":str(error)}
            finally:
                try:
                    archive.save_summary(finished)
                except OSError as error:
                    finished["erro_pacote"] = str(error)
                for temporary in (csv if not quote or csv != quote[1] else None, resume_archive):
                    if temporary:
                        try:
                            temporary.unlink(missing_ok=True)
                        except OSError:
                            pass
                self.publish(**outcome, segundos=seconds, empacotando=False, historico=finished)


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
                with workspace.lock:
                    job = workspace.job
                    if job["estado"] == "executando":
                        control = workspace.control
                        job = job | {"segundos": round(control.elapsed(workspace.started_at)),
                                     "pausado": control.paused_at is not None,
                                     "cancelando": control.cancelled.is_set(),
                                     "finalizando": control.finish_requested.is_set()}
                self.json(job)
            elif path == "/historico":
                self.json(history(workspace.history))
            elif path and (match := re.fullmatch(rf"/historico/({ID})/(execucao.zip|execucao.jsonl|configuracao|otimizada)", path)):
                archive = ExecutionArchive(workspace.history, match[1])
                action = match[2]
                try:
                    if action in {"configuracao", "otimizada"}:
                        self.json(archive.settings(action == "otimizada"))
                    else:
                        file = archive.package if action == "execucao.zip" else archive.log
                        with file.open("rb") as stream:
                            self.send_response(200)
                            self.send_header("Content-Type", "application/zip" if action == "execucao.zip" else "application/x-ndjson")
                            self.send_header("Content-Disposition", f'attachment; filename="{archive.key}-{action}"')
                            self.send_header("Content-Length", str(file.stat().st_size))
                            self.send_header("X-Content-Type-Options", "nosniff")
                            self.end_headers()
                            shutil.copyfileobj(stream, self.wfile, 4*MIB)
                except (ValueError, KeyError, OSError, BadZipFile) as error:
                    self.json({"erro":str(error)}, 404)
            elif path == "/github-execucoes":
                try:
                    query = parse_qs(urlsplit(self.path).query)
                    page = max(1, min(10000, int(query.get("pagina", ["1"])[0])))
                    self.json(github_execucoes.catalog(page))
                except (OSError, ValueError) as error:
                    self.json({"erro":str(error)}, 502)
            elif path == "/cotacoes":
                self.json(workspace.quotes.list())
            elif path == "/estrategias":
                self.json(workspace.quotes.list_strategies())
            elif path and re.fullmatch(r"/estrategias/[0-9a-f]{32}", path):
                item = workspace.quotes.get_strategy(path.rsplit("/",1)[1])
                if item is None:
                    self.json({"erro":"Estratégia não encontrada."}, 404)
                else:
                    self.json(item)
            elif path == "/modelo-exemplo":
                self.send_bytes((APP/"modelo_profit.ntsl").read_bytes(),"text/plain; charset=utf-8")
            elif path == "/config-exemplo":
                self.send_bytes((APP/"config_v7.json").read_bytes(),"application/json; charset=utf-8")
            elif path and path.startswith(("/resultados/", "/sessoes/")):
                pieces = path.split("/")
                if pieces[1] == "sessoes" and len(pieces) == 3 and re.fullmatch(
                        r"\d{8}-\d{6}-\d{6}\.sessao\.zip", pieces[2]):
                    file = workspace.output / "sessoes" / pieces[2]
                elif (len(pieces)!=4 or not re.fullmatch(r'\d{8}-\d{6}-\d{6}',pieces[2])
                        or pieces[3] not in REPORTS or pieces[1] != "resultados"):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                else:
                    file = workspace.output.joinpath(*pieces[2:])
                if not file.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                with file.open("rb") as stream:
                    self.send_response(200)
                    self.send_header("Content-Type",mime)
                    self.send_header("Content-Length",str(stream.seek(0, 2)))
                    stream.seek(0)
                    self.send_header("X-Content-Type-Options","nosniff")
                    self.send_header("Referrer-Policy","no-referrer")
                    if pieces[1] == "sessoes":
                        self.send_header("Cache-Control","no-store")
                    if file.suffix != ".html":
                        self.send_header("Content-Disposition",f'attachment; filename="{file.name}"')
                    self.end_headers()
                    shutil.copyfileobj(stream,self.wfile,length=MIB)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self):
            path = self.route()
            if path not in {"/csv","/csv-bloco","/executar","/encerrar","/carregar-sessao","/pausar","/retomar","/cancelar","/salvar-sessao","/finalizar","/cotacoes","/selecionar-parametros","/estrategias","/importar-execucao"}:
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
                if path in {"/pausar","/retomar","/cancelar","/salvar-sessao","/finalizar"}:
                    if not 0 < length <= 512:
                        raise ValueError("Identificação da execução inválida.")
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError("Identificação da execução inválida.")
                    workspace.control_job(data.get("id"), path[1:])
                elif path == "/importar-execucao":
                    data = json.loads(self.rfile.read(length)) if 0 < length <= 512 else {}
                    if not isinstance(data, dict):
                        raise ValueError("Dados de importação inválidos.")
                    with workspace.lock:
                        transfer = data.get("transferencia")
                        source = workspace.pending_input
                        if (workspace.job["estado"] == "executando" or not source or not workspace.upload_transfer
                                or workspace.upload_transfer[:2] != (transfer, source)):
                            raise ValueError("Envie o ZIP da execução antes de importá-lo.")
                        archive = ExecutionArchive.import_package(workspace.history, source)
                        source.unlink(missing_ok=True)
                        workspace.pending_input = workspace.upload_transfer = None
                    self.json(archive.summary())
                    return
                elif path == "/estrategias":
                    if not 0 < length <= 8*MIB:
                        raise ValueError("O cadastro excede 8 MiB ou está vazio.")
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError("Dados da estratégia inválidos.")
                    self.json({"id": workspace.quotes.save_strategy(data)})
                    return
                elif path in {"/cotacoes", "/selecionar-parametros"}:
                    if not 0 < length <= 16*1024:
                        raise ValueError("Dados da solicitação inválidos.")
                    data = json.loads(self.rfile.read(length))
                    if not isinstance(data, dict):
                        raise ValueError("Dados da solicitação inválidos.")
                    if path == "/cotacoes":
                        self.json({"id": workspace.save_quotes(data)})
                    else:
                        self.json(workspace.choose_parameters(data))
                    return
                elif path == "/csv":
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
                    restore = path == "/carregar-sessao"
                    if not isinstance(options, dict) or (not restore and not isinstance(options.get("opcoes"),dict)):
                        raise ValueError("As opções precisam ser um objeto JSON.")
                    job = workspace.start(options, restore)
                    self.json({"ok":True,"id":job})
                    return
                else:
                    raise ValueError("O código e a configuração excedem 8 MiB ou estão vazios.")
                self.json({"ok":True})
            except (BrokenPipeError, ConnectionResetError):
                return
            except TimeoutError:
                self.json({"erro":"O envio do bloco expirou."},408)
            except (ValueError,OSError,KeyError,TypeError,BadZipFile) as error:
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
