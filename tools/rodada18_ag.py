"""Rodada 18: inventário, baselines e AG existente por grupo WINZ26."""
from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256, file_digest
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import Event, Thread
from time import monotonic

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
import pandas as pd
import psutil

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from controle import ProcessingControl
from estrategia import Engine, ExecutionRules, StrategyReplay, load_bars, source_text
from ntsl import NTSLError, compile_ntsl
from sessao import Session, load_session
from simulador import optimize, read_export
from tools.preparar_paridade_profit_barras import read_profit


EVID = Path("docs/colaboracao/evidencias")
EA = "estrategias/execucao/"
PB20 = EVID / "estrategia_pullback_20_pregoes_v1"
ADAPT = EVID / "estrategia_pullback_adaptativo_v1"
SHORT = EVID / "estrategia_pullback_busca_curta_v1"
DYNAMIC = EVID / "estrategia_pullback_alvo_dinamico_v1"
PB16 = EVID / "estrategia_pullback_falha_rompimento_v1"
SOURCES = ("profit_WINZ26_20261021_barras_1min.csv",
           "profit_WINZ26_20261021_indicadores_v5_7.csv", "indicadorv7_claude.csv",
           "indicadorv6_claude.csv", "barras_v58.csv")
HEADS = ("d2429a4549b497fcdbdb0cfef04e02c01d6be997", "3e2720016e83436c7a648eac51f134de4e68393a")
RULES = asdict(ExecutionRules(custo_por_contrato_lado=0.50, slippage_ticks=1))
MARKET = ("bidprice", "askprice", "bidsize", "asksize", "totalbuyqtd", "totalsellqtd",
          "agressionvolbuy", "agressionvolsell", "agressionvolbalance", "trades", "volume", "vwap")
V_FAST = ["v_bid", "v_ask", "v_qtd_bid", "v_qtd_ask", "v_qtd_compra_book", "v_qtd_venda_book",
          "v_agressao_compra", "v_agressao_venda", "v_trades_atual"]
POP = 24
GENERATIONS = 3
FAST_GENERATIONS = 2
FAST_POP = 8
SEED = 18024
MUTATION = 0.28
TICK = 5
POINT = 0.20


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def normal(inputs):
    return {k.lower(): v for k, v in inputs.items()}


def sources(research):
    base = load_json(research / PB20 / "resultado.json")["baseline"]
    conf = load_json(research / PB16 / "protocolo.json")
    profiles = {
        1: base, 2: base,
        3: base | load_json(research / SHORT / "resultado.json")["perfis"]["maior_liquido"]["parametros"],
        4: base | load_json(research / DYNAMIC / "resultado.json")["perfis"]["dinamico"]["parametros"],
        5: conf["referencia"],
        6: base | load_json(research / ADAPT / "v1_6.json")["perfis"]["dinamico"]["parametros"],
        7: conf["referencia"] | {"p_AtivarSaidaFalha": 0},
    }
    paths = ["estrategias/pesquisa"] * 2 + [PB20] * 2 + [DYNAMIC, ADAPT, ADAPT, "estrategias/execucao"]
    selected = {}
    for version, parent in enumerate(paths):
        group = "win_60s_1c" if version < 4 else "win_60s_2c"
        relative = str(Path(parent) / f"pullback_tendencia_v1_{version}.ntsl").replace("\\", "/")
        selected[relative] = (group, profiles.get(version, {}), "pesquisa")
    strategies = {
        "Modelo_Unificado_Refatorado_v5_7": ("win_60s_2c", {"p_lote": 2}),
        "Modelo_Unificado_v5_8": ("win_60s_2c", {"p_exec_tick": 0, "p_lote": 2}),
        "modelo_scalper_v1_1": ("win_60s_2c", {"p_lote": 2}),
        "modelo_scalper_micro_hft_v3_0": ("win_1s_2c", {"p_lote": 2}),
        "modelo_micro_scalper_v4_2_5s": ("win_5s_2c", {"p_lote": 2}),
        "modelo_micro_scalper_v4_3_ranges_5s": ("win_5s_2c", {"p_lote": 2}),
        "modelo_1c_antecipado_profit_v1_0": ("win_1s_2c", {"p_lote": 2}),
        "modelo_1c_antecipado_profit_v1_1": ("win_1s_2c", {"p_lote": 2}),
    }
    strategies.update({f"modelo_scalper_v2_{i}": ("win_5s_2c", {"p_lote": 2}) for i in range(4)})
    for name, (group, profile) in strategies.items():
        selected[EA + name + ".ntsl"] = (group, profile, "pr2")
    return selected, conf


def ranges(program, profile, group):
    template = {
        "p_rapida": [5, 9, 15, 20], "p_lenta": [21, 27, 34, 48],
        "p_alvo": [60, 100, 150, 200, 250], "p_stop": [75, 110, 150, 200, 300],
        "p_folgastop": [25, 50, 100], "p_tempomax": [5, 10, 15, 30],
        "p_espera": [1, 3, 5], "p_horainicio": [930, 1000, 1030],
        "p_horafimentradas": [1530, 1630, 1700], "p_maxentradasdia": [4, 8, 12, 24],
        "p_janelaamplitude": [5, 10, 15], "p_fatoramplitude": [0.8, 1.0, 1.2, 1.6],
        "p_fatorstop": [0.55, 0.65, 0.8], "p_separacao": [0.05, 0.10, 0.20],
        "p_usaralvodinamico": [0, 1], "p_rompimento": [0, 1],
        "p_ativarsaidafalha": [0],  # Rejeitado na rodada 16, exige consenso próprio.
        "p_periodo_atr": [10, 14, 20], "p_periodo_regime_atr": [35, 50, 65],
        "p_desvio_vwap": [1.6, 2.1, 2.6], "p_zscore_vol": [1.0, 1.5, 2.0],
        "p_stop_pontos": [200, 275, 350, 450], "p_alvo_pontos": [250, 350, 400, 450, 550],
        "p_minimotrades": [50, 100, 150, 250], "p_offset_limite_stop": [5, 25, 50, 100],
        "p_periodo_desvio": [15, 20, 30], "p_modo_banda": [0, 1],
        "p_barras_espera": [1, 3, 5], "p_max_entradas_dia": [5, 10, 15],
        "p_hora_inicio": [915, 930, 1000], "p_hora_fim_entradas": [1550, 1615, 1645],
        "p_alvopontos": [20, 35, 50, 100, 150, 200], "p_stoppontos": [15, 25, 40, 75, 150],
        "p_offsetstop": [5, 10, 20, 50], "p_cooldownbarras": [0, 1, 3, 5],
        "p_periodomedia": [5, 9, 15], "p_periodomediapreco": [5, 9, 15],
        "p_periodomediafluxo": [12, 20, 30], "p_thresholdfluxo": [1.3, 1.8, 2.3],
        "p_cortescoremodelo": [0.0, 0.5, 0.847298, 1.1],
        "p_minvelocidade": [1, 2, 5, 10], "p_minaceleracao": [0.2, 0.5, 1, 5],
        "p_minforcacontratos": [5, 10, 25, 50], "p_razaodesbalanco": [1.0, 1.15, 1.5, 2.5],
        "p_maxbarrasposicao": [2, 4, 6], "p_cooldownminutos": [5, 10, 15],
        "p_minrazaoagressaoentrada": [1.0, 1.2, 1.5],
        "p_mindeltaagressao": [2, 5, 10], "p_minimpulsobook": [0.5, 1, 2],
        "p_mintradesbarra": [1, 3, 5, 10] if "60s" not in group else [100, 200, 300, 400],
        "p_tempomaxsegundos": [2, 5, 8, 12] if "1s" in group else [15, 25, 45, 90],
        "p_horarioinicio": [915, 945, 1015],
    }
    result = {}
    for key in program.used_inputs:
        if key in template:
            default = profile[key]
            result[key] = {"valores": sorted(set(template[key]) | {default})}
    for key, value in profile.items():
        if key not in result and (program.inputs[key] != value or key in {"p_exec_tick", "p_lote"}):
            result[key] = {"valores": [value]}
    return dict(sorted(result.items()))


def mode_rules(group, problem):
    rules = RULES.copy()
    if "60s" in group:
        rules.update(volume_financeiro_ntsl=True, agressao_referencia_injetada=True,
                     vwap_continuo_lacunas=True)
    if problem == "diagnostico_winz26_native":
        rules.update(avaliacao_pos_preenchimento=True)
    return rules


def gather_catalog(args, selected):
    seen, rows = {}, []
    names = selected.keys()
    for label, root, expected in (("pr2", REPO, HEADS[0]), ("pesquisa", args.pesquisa, HEADS[1])):
        files = subprocess.check_output(["git", "-C", root, "ls-tree", "-rz", "--name-only",
                                         expected], text=True, encoding="utf-8").split("\x00")
        for relative in sorted((x for x in files if x.endswith(".ntsl")),
                               key=lambda x: (x not in names, x)):
            path = root / relative
            kind = "github"
            add_source(rows, seen, selected, path, label, relative, kind, expected)
    if args.fontes_extras:
        roots = [(args.dados, "*.ntsl"), (args.fontes_extras, "WINZ26_Direcional*.txt")]
    else:
        roots = [(args.dados, "*.ntsl")]
    for root, pattern in roots:
        for path in sorted(root.rglob(pattern) if root == args.dados else root.glob(pattern)):
            add_source(rows, seen, selected, path, "windows", path.name, "windows", None)
    return rows


def add_source(rows, seen, selected, path, label, relative, kind, git_sha):
    raw = path.read_bytes()
    raw_sha = sha256(raw).hexdigest()
    code = source_text(path)
    semantics_sha = sha256(code.replace("\r\n", "\n").encode()).hexdigest()
    key = label + ":" + relative + ("@" + raw_sha[:12] if kind == "windows" else "")
    info = dict(id=key, local=kind, commit=git_sha, arquivo=relative,
                versao=re.search(r"v(\d+[._]\d+(?:[._]\d+)?)", path.name.lower()).group(1).replace("_", ".")
                if re.search(r"v(\d+[._]\d+(?:[._]\d+)?)", path.name.lower()) else None,
                sha256=raw_sha, sha256_texto_lf=semantics_sha, bytes=len(raw))
    if semantics_sha in seen and not (relative in selected and selected[relative][2] == label):
        rows.append(info | dict(status="duplicata", equivalente=seen[semantics_sha]))
        return
    seen.setdefault(semantics_sha, key)
    lower = relative.lower()
    if ("indicadores/" in lower or lower.startswith(("indicador", "monitor", "diagnostico"))
            or "/sonda_" in lower or "/g1_" in lower or "/g2_" in lower
            or "/g3_" in lower or "/g4_" in lower or "auditoria" in lower
            or "captura_paridade" in lower or lower.startswith("exemplo")
            or not re.search(r"\b(?:BuyAtMarket|SellShortAtMarket|BuyAtLimit|SellShortAtLimit|SendOrder)\s*\(", code, re.I)):
        info["tipo"] = "coleta, instrumentação ou exemplo"
    else:
        info["tipo"] = "estrategia"
    try:
        program = compile_ntsl(code)
    except NTSLError as error:
        status = "fora_ranking" if info["tipo"] != "estrategia" else "bloqueada"
        rows.append(info | dict(status=status, compilador=str(error)))
        return
    info.update(compilador="aceito", inputs=program.inputs, usados=sorted(program.used_inputs),
                dependencias=sorted(set(MARKET) & program.used))
    if relative in selected and selected[relative][2] == label:
        group, p, _ = selected[relative]
        published = program.inputs | {k: v for k, v in normal(p).items() if k in program.inputs}
        overrides = {"p_lote": 2} if "p_lote" in program.inputs else {}
        if "p_exec_tick" in program.inputs:
            overrides["p_exec_tick"] = 0
        info.update(grupo=group, status="apta", ranking_original=program.inputs | overrides,
                    modo_ohlc_original=program.inputs | {k: v for k,v in overrides.items() if k!="p_lote"},
                    perfil_publicado=published | overrides if p else None,
                    busca=ranges(program, published | overrides, group))
    elif info["tipo"] != "estrategia":
        info.update(status="fora_ranking")
    elif lower.endswith("modelo_micro_scalper_v4_1_5s.ntsl"):
        info.update(status="bloqueada", motivo="Volume ausente no indicador nativo de 5s; a estratégia o lê.")
    elif lower.endswith("modelo_micro_scalper_v4_0.ntsl"):
        info.update(status="bloqueada", motivo="Exige book profundo válido; 0 a 3,1% das barras de 1s têm profundidade válida nos dias elegíveis.")
    elif lower.endswith("modelo_profit.ntsl"):
        info.update(status="bloqueada", motivo="Ensemble com execução semelhante à v1.1, mas o SHA de execução independente será verificado antes de uso.")
    else:
        info.update(status="bloqueada", motivo="Sem contrato de fonte e granularidade aplicáveis comprovado para esta cópia.")
    rows.append(info)


def prepare_60(args):
    bars = read_profit(args.dados / SOURCES[0])
    ind = read_profit(args.dados / SOURCES[1])
    for df in (bars, ind):
        df["timestamp"] = pd.to_datetime(df.pop("Data"), format="%d/%m/%Y %H:%M")
        if df.timestamp.duplicated().any():
            raise ValueError("Timestamp duplicado em fonte nativa de 1 min.")
    ohlc = ["Abertura", "Máxima", "Mínima", "Fechamento"]
    ref = ind[["timestamp", *ohlc, "v_Saldo_Agressao"]]
    cmp = bars.merge(ref, on="timestamp", suffixes=("", "_ind"), how="left", validate="one_to_one")
    matched = np.logical_and.reduce([cmp[k].eq(cmp[k+"_ind"]) for k in ohlc])
    cmp["v_agressao_saldo_referencia"] = cmp["v_Saldo_Agressao"].where(matched)
    cmp["v_vwap_barra"] = cmp["Volume"] / (cmp["Quantity"] * POINT)
    frame = cmp.rename(columns=dict(zip([*ohlc, "Trades", "Quantity", "Volume"],
                                      ["abertura", "maxima", "minima", "fechamento", "v_trades_atual",
                                       "volume_contratos", "volume_financeiro"])))[
        ["timestamp", "abertura", "maxima", "minima", "fechamento", "v_trades_atual",
         "volume_contratos", "volume_financeiro", "v_agressao_saldo_referencia", "v_vwap_barra"]]
    frame["volume"] = frame["volume_contratos"]
    return frame.sort_values("timestamp"), list(bars.columns), list(ind.columns)


def cover_60(frame):
    entries = []
    for day, df in frame.groupby(frame.timestamp.dt.strftime("%Y-%m-%d")):
        missed = int(df.timestamp.diff().dt.total_seconds().div(60).sub(1).clip(lower=0).sum())
        entries.append(dict(pregao=day, segundos=60, barras=len(df),
                            hora_inicial=df.timestamp.min().strftime("%H:%M"),
                            hora_final=df.timestamp.max().strftime("%H:%M"),
                            lacunas_barras=missed, barras_sem_agressao=int(df.v_agressao_saldo_referencia.isna().sum()),
                            barras_com_trades=int((df.v_trades_atual>0).sum()),
                            barras_com_volume=int((df.volume_contratos>0).sum())))
    return entries


def prepare_fast(args, file, seconds):
    frames = read_export(args.dados / file, seconds)
    columns = ["data_minuto_origem", "v_barra_id", "abertura", "maxima", "minima", "fechamento", *V_FAST]
    rows = []
    for day,g in frames.groupby("pregao"):
        valid = (g.v_bid>0) & (g.v_ask>=g.v_bid) & (g.v_qtd_bid>0) & (g.v_qtd_ask>0)
        deep = valid & (g.v_qtd_compra_book>0) & (g.v_qtd_venda_book>0)
        rows.append(dict(pregao=day, segundos=seconds, barras=len(g), minutos=g.minuto.nunique(),
                         hora_inicial=g.minuto.min().strftime("%H:%M"), hora_final=g.minuto.max().strftime("%H:%M"),
                         lacunas_barras=int((g.minuto.max()-g.minuto.min()).total_seconds()/seconds+60/seconds-len(g)),
                         segmentos=int(g.segmento.nunique()), topo_valido=int(valid.sum()),
                         book_profundo_valido=int(deep.sum()), barras_com_trades=int((g.v_trades_atual>0).sum()),
                         barras_sem_agressao=int(g[["v_agressao_compra","v_agressao_venda"]].isna().any(axis=1).sum())))
    return frames[[*columns, "pregao"]], rows, [str(x) for x in frames.columns]


def setup(args):
    selected, prior = sources(args.pesquisa)
    catalog = gather_catalog(args, selected)
    bars, headers_b, headers_i = prepare_60(args)
    fast = {secs: prepare_fast(args, file, secs) for file, secs in zip(SOURCES[2:4], [5, 1])}
    coverage = {60: cover_60(bars), 5: fast[5][1], 1: fast[1][1]}
    group60 = dict(segundos=60, formato="ohlc", desenvolvimento=prior["desenvolvimento"],
                   interno_ag=[], exploratorio=prior["exploratorio"],
                   validacao_inedita=[], drawdown_max_reais=1500)
    groups = {"win_60s_2c": group60 | {"lote":2}, "win_60s_1c": group60 | {"lote":1}}
    for secs in (5, 1):
        # Permit only sessions with the full operating window and at least 98% minute/bar coverage.
        threshold = 565*(60//secs)*0.98
        days = [r["pregao"] for r in coverage[secs] if r["barras"] >= threshold
                and r["hora_inicial"] <= "09:15" and r["hora_final"] >= "18:20" and r["barras_sem_agressao"] == 0]
        if len(days) < 2:
            raise ValueError(f"Cobertura insuficiente para o grupo {secs}s.")
        groups[f"win_{secs}s_2c"] = dict(segundos=secs, formato="profit", lote=2,
                                       desenvolvimento=days[:-1], interno_ag=[], exploratorio=days[-1:],
                                       validacao_inedita=[], drawdown_max_reais=1000)
    for group in groups.values():
        dates = set(group["desenvolvimento"]+group["interno_ag"]+group["exploratorio"])
        secs = group["segundos"]
        if secs == 60:
            part = bars[bars.timestamp.dt.strftime("%Y-%m-%d").isin(dates)].copy()
            numeric = part.drop(columns="timestamp")
            if not np.isfinite(numeric.to_numpy(dtype=float)).all() or (part.volume_contratos <= 0).any():
                raise ValueError("Série obrigatória ausente no recorte congelado de 1 min.")
            if set(part.timestamp.dt.strftime("%Y-%m-%d")) != dates:
                raise ValueError("Faltam pregões congelados de 1 min.")
        else:
            part = fast[secs][0]
            part = part[part.pregao.isin(dates)].drop(columns="pregao")
        dst = args.saida / "bases" / f"win_{secs}s.csv"
        dst.parent.mkdir(exist_ok=True, parents=True)
        if not dst.exists():
            part.to_csv(dst, sep=";", decimal=",", index=False, date_format="%Y-%m-%dT%H:%M:%S")
        group["base_sha256"] = digest(dst)
        group["minimo_operacoes_desenvolvimento"] = len(group["desenvolvimento"])
    public = dict(referencias=dict(pr2=HEADS[0], pesquisa=HEADS[1]),
                  regras_1min=mode_rules("win_60s", None), regras_subminuto=RULES,
                  win=dict(tick=TICK, valor_ponto=POINT), metas=dict(acerto=0.45, liquido_diario=3000),
                  ag=dict(populacao=POP, geracoes=GENERATIONS, orcamento_1s=dict(populacao=FAST_POP, geracoes=FAST_GENERATIONS), semente=SEED, mutacao=MUTATION,
                          objetivo="líquido após custos; mínimo de operações e teto de drawdown"),
                  grupos=groups, elegibilidade="1 min: recortes conhecidos da R16 com junção OHLC exata. Subminuto: 98% de 565 minutos e cobertura da janela operacional.",
                  validacao_inedita="sem pregão posterior elegível e ineditismo demonstrado; a reserva permanece fechada",
                  estrategias=[r for r in catalog if r["status"]=="apta"])
    headers = [headers_b, headers_i, fast[5][2], fast[1][2],
               ["Data", "Abertura", "Máxima", "Mínima", "Fechamento"]]
    files = [{"arquivo": name, "bytes": (args.dados/name).stat().st_size,
              "sha256": digest(args.dados/name), "campos": h} for name, h in zip(SOURCES, headers)]
    capture_headers = {}
    for path in sorted(args.dados.glob("win_*.csv")):
        if path.name.endswith(".lotes.csv"): continue
        import csv
        with path.open(encoding="utf-8-sig") as stream:
            cols = next(csv.reader(stream, delimiter=";"))
        capture_headers[path.name] = dict(bytes=path.stat().st_size, campos=cols)
    save(args.saida/"publico"/"protocolo.json", public)
    save(args.saida/"publico"/"cobertura.json", dict(ativo="WIN", contrato="WINZ26", fontes=files,
                                                  cobertura=coverage, ProfitRTD_brutos=capture_headers))
    save(args.saida/"publico"/"inventario_estrategias.json", catalog)


def frame_for(args, group, subset):
    filename = args.saida/"bases"/f'win_{group["segundos"]}s.csv'
    if digest(filename) != group["base_sha256"]:
        raise ValueError("A base preparada mudou depois do congelamento.")
    frame = load_bars(filename, group["segundos"], group["formato"])
    days = group[subset] if subset!="ag" else group["desenvolvimento"]
    return filename, frame.loc[frame.pregao.isin(days)].reset_index(drop=True)


def evaluate(program, frame, group, rules, parameters, lot):
    engine = Engine(program, frame, TICK, parameters, group["segundos"], POINT, regras=rules)
    engine.run(record_trace=False)
    opened = None
    pnls, durations = [], []
    by_day = {str(day): [0.0, 0] for day in sorted(set(frame.pregao))}
    if "timestamp" in frame:
        stamps = frame.timestamp
    else:
        stamps = frame.minuto + pd.to_timedelta((frame.ordem_no_minuto-1)*group["segundos"], unit="s")
    max_exposure = max((abs(fill["posicao"]) for fill in engine.fills), default=0)
    for fill in engine.fills:
        stamp = stamps.iloc[fill["barra"]-1]
        if fill["acao"] in {"long", "short"} and opened is None and abs(fill["posicao"])==fill["quantidade"]==lot:
            opened = (stamp, fill["liquido_reais"])
        elif fill["acao"].startswith("exit") and opened and fill["posicao"]==0 and fill["quantidade"]==lot:
            net = round(opened[1]+fill["liquido_reais"], 2)
            pnls.append(net)
            durations.append((stamp-opened[0]).total_seconds())
            day = by_day[fill["pregao"]]
            day[0] += net
            day[1] += 1
            opened = None
        else:
            raise ValueError("Preenchimento parcial, posição acumulada ou quantidade divergente do grupo.")
    if opened:
        raise ValueError("Posição residual no fim da amostra.")
    equity = np.r_[0, np.cumsum(pnls)]
    wins = sum(p>0 for p in pnls)
    gain = sum(p for p in pnls if p>0)
    loss = -sum(p for p in pnls if p<0)
    total, days = float(equity[-1]), len(by_day)
    return dict(pregoes=days, barras=len(frame), operacoes=len(pnls), operacoes_por_dia=len(pnls)/days,
                acertos=wins, acerto=wins/len(pnls) if pnls else None,
                delta_meta_acerto_pp=100*(wins/len(pnls)-0.45) if pnls else None,
                liquido=round(total,2), liquido_por_dia=round(total/days,2),
                delta_meta_diaria=round(total/days-3000,2), fator_lucro_liquido=round(gain/loss,5) if loss else None,
                drawdown_max=round(float((np.maximum.accumulate(equity)-equity).max()),2),
                pior_dia=round(min(day[0] for day in by_day.values()),2),
                duracao_mediana_s=float(np.median(durations)) if durations else None,
                duracao_p90_s=float(np.percentile(durations,90)) if durations else None,
                dias_meta=sum(day[0]>=3000 for day in by_day.values()), max_exposicao=max_exposure,
                ambiguidades=engine.ambiguities,
                por_pregao={k:{"liquido":round(v[0],2),"operacoes":v[1]} for k,v in by_day.items()})


def strategy_program(args, version):
    root = args.pesquisa if version["id"].startswith("pesquisa:") else REPO
    path = root / version["arquivo"]
    if digest(path) != version["sha256"]:
        raise ValueError("Fonte modificada após o congelamento.")
    return compile_ntsl(source_text(path))


def monitoring(done, samples):
    parent = psutil.Process()
    parent.cpu_percent()
    psutil.cpu_percent()
    while not done.is_set():
        family = [parent, *parent.children(recursive=True)]
        rss = 0
        for process in family:
            try:
                rss += process.memory_info().rss
            except psutil.Error:
                pass
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        samples.append((rss, memory.available, psutil.cpu_percent(), swap.used))
        done.wait(0.35)


def page_counters():
    script = ("Get-CimInstance Win32_PerfRawData_PerfOS_Memory | "
              "Select-Object PagesInputPersec,PagesOutputPersec,PageReadsPersec | ConvertTo-Json -Compress")
    try:
        raw = subprocess.check_output(["powershell", "-NoProfile", "-Command", script],
                                      text=True, timeout=8, stderr=subprocess.DEVNULL)
        return json.loads(raw) or {}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


def measured_optimize(program, data, subgroup, version, cfg, work, source_file, pilot=False):
    work.mkdir(exist_ok=True, parents=True)
    rules = cfg["regras_execucao"]
    replay = StrategyReplay(data, program, subgroup["segundos"], "1C", {"modo":"resultado"}, (),
                            TICK, POINT, regras=rules)
    replay.in_memory = True
    control = ProcessingControl()
    session_path = work/"sessoes"/"ag.sessao.zip"
    options = dict(salvar_minutos=1, modo="otimizar", ntsl=program.source, opcoes=cfg)
    state = None
    if session_path.exists() and not pilot:
        saved, state = load_session(session_path)
        if saved != options:
            raise ValueError("O checkpoint pertence a outra configuração.")
    session = Session(work, "ag", source_file, options, resume=state)
    paging_start = page_counters()
    start = monotonic()
    resources = {}
    monitor_done = Event()
    observations = []
    monitor = Thread(target=monitoring, args=(monitor_done, observations), daemon=True)
    monitor.start()

    def gate(stats):
        return (stats.get("saidas", 0)>=subgroup["minimo_operacoes_desenvolvimento"]
                and stats.get("drawdown_reais", float("inf"))<=subgroup["drawdown_max_reais"])

    def checkpoint(history, names):
        if not pilot:
            session.requested.set()
            session.service()

    try:
        metrics = optimize(replay, cfg, work, on_resources=resources.update, on_progress=checkpoint,
                           control=control, session=None if pilot else session, candidate_gate=None if pilot else gate, search_only=True)
    finally:
        monitor_done.set()
        monitor.join()
    spent = monotonic()-start
    paging_end = page_counters()
    pages = {key: int(paging_end[key])-int(value) for key,value in paging_start.items() if key in paging_end}
    log = dict(paginacao_contadores_sistema_delta=pages, trabalhadores=resources["trabalhadores"], nucleos_logicos=resources["nucleos_logicos"],
               modo=resources["modo_paralelo"], segundos=round(spent,3),
               avaliados=metrics["candidatos_avaliados"], segundos_ag=metrics["segundos_busca"],
               avaliacoes_minuto=round(metrics["candidatos_avaliados"]*60/max(metrics["segundos_busca"],0.01),2),
               rss_somado_pico_mib=round(max(s[0] for s in observations)/2**20,1),
               memoria_disponivel_min_mib=round(min(s[1] for s in observations)/2**20,1),
               cpu_total_media_pct=round(float(np.mean([s[2] for s in observations])),1),
               arquivo_paginacao_variacao_mib=round((max(s[3] for s in observations)-observations[0][3])/2**20,1),
               base_worker_mib=round(data.memory_usage(deep=True).sum()/2**20,2),
               atende_restricoes=metrics["atende_min_sinais"])
    return metrics, log


def settings(version, workers, pilot=False):
    pop, generations = (FAST_POP, FAST_GENERATIONS) if version["grupo"]=="win_1s_2c" else (POP, GENERATIONS)
    return dict(busca="genetica", classe_alvo="1C", pregoes_teste=0, cache_ram_mb=0, threads=workers,
                regras_execucao=mode_rules(version["grupo"], None),
                parametros=version["busca"], genetico=dict(populacao=pop,
                geracoes=1 if pilot else generations, semente=SEED, mutacao=MUTATION,
                min_sinais=0, paciencia=0, metrica="resultado"))


def run(args):
    public = args.saida/"publico"
    protocol = load_json(public/"protocolo.json")
    versions = protocol["estrategias"]
    if args.filtro:
        versions = [v for v in versions if any(key in v["arquivo"] for key in args.filtro)]
    resident, results = {}, {}
    for group_name, group in protocol["grupos"].items():
        if any(v["grupo"]==group_name for v in versions):
            source, data = frame_for(args, group, "ag")
            resident[group_name] = (source, data)
    for version in versions:
        name = Path(version["arquivo"]).stem
        print(f"{args.fase} {name}", flush=True)
        family = version["grupo"]
        group = protocol["grupos"][family]
        source, data = resident[family]
        program = strategy_program(args, version)
        work = args.saida/"execucoes"/name
        job = public/"resultados"/(name+".json")
        initial = public/"baselines"/(name+".json")
        rules = mode_rules(family, None)
        dev = data[data.pregao.isin(group["desenvolvimento"])].reset_index(drop=True)
        if args.fase=="baseline":
            if initial.exists() and not args.refazer_baseline:
                continue
            results = {}
            for label, p in (("original",version["ranking_original"]), ("publicado",version["perfil_publicado"])):
                if p is not None:
                    same = results.get("original")
                    m = same["metricas"] if same and same["parametros"]==p else evaluate(program,dev,group,rules,p,group["lote"])
                    results[label] = dict(parametros=p,metricas=m)
            if "p_lote" in program.inputs:
                p = version["modo_ohlc_original"]
                if p["p_lote"] != group["lote"]:
                    results["lote_original_separado"] = dict(parametros=p,metricas=evaluate(program,dev,group,rules,p,int(p["p_lote"])))
            if name=="Modelo_Unificado_Refatorado_v5_7":
                p = version["modo_ohlc_original"] | {"p_lote": 1}
                subset = mode_rules(family, "diagnostico_winz26_native")
                results["perfil_paridade_separado"] = dict(parametros=p,regras=subset,
                                                            metricas=evaluate(program,dev,group,subset,p,int(p["p_lote"])))
            save(initial,results)
        elif args.fase=="piloto":
            for workers in args.workers:
                _, log = measured_optimize(program,data,group,version,settings(version,workers,pilot=True),
                                          work/f"piloto-{workers}",source,pilot=True)
                save(public/"piloto"/f"{name}-{workers}.json",log)
        elif args.fase=="busca":
            if job.exists():
                continue
            if not initial.exists():
                raise ValueError(f"Baseline ausente para {name}.")
            workers = args.workers[0]
            cfg = settings(version, workers)
            results, log = measured_optimize(program,data,group,version,cfg,work/"ag",source)
            best = program.inputs | normal(results["parametros_otimizados"])
            acceptable = results["atende_min_sinais"]
            frozen = dict(parametros=best, apta=acceptable, semente=SEED, grupo=family,
                          sha256=version["sha256"], objetivo="resultado após custos",
                          referencia_exploratoria_sem_reselecao=group["exploratorio"])
            save(public/"congelados"/(name+".json"), frozen)
            baselines = load_json(initial)
            record = dict(grupo=family, identificacao=name, chave=version["id"], configuracao=cfg,
                          recursos=log, congelado=frozen, parada=results["parada"],
                          desenvolvimento=baselines.copy(), exploratorio={}, validacao_inedita=None)
            if acceptable:
                record["desenvolvimento"]["otimizado"] = dict(parametros=best, metricas=evaluate(program,dev,group,rules,best,group["lote"]))
            _, exploration = frame_for(args, group, "exploratorio")
            for k,r in baselines.items():
                if k in {"original","publicado"}:
                    raw = r["parametros"]
                    same = record["exploratorio"].get("original")
                    m = same["metricas"] if same and same["parametros"]==raw else evaluate(program,exploration,group,rules,raw,group["lote"])
                    record["exploratorio"][k] = dict(parametros=raw,metricas=m)
            if acceptable:
                final = evaluate(program,exploration,group,rules,best,group["lote"])
                record["exploratorio"]["otimizado"] = dict(parametros=best,metricas=final)
            for split in ("desenvolvimento","exploratorio"):
                rows = record[split]
                if "otimizado" in rows:
                    net = rows["otimizado"]["metricas"]["liquido"]
                    rows["otimizado"]["delta_original_reais"] = round(net-rows["original"]["metricas"]["liquido"],2)
                    if "publicado" in rows:
                        rows["otimizado"]["delta_publicado_reais"] = round(net-rows["publicado"]["metricas"]["liquido"],2)
            evolution = pd.read_csv(work/"ag"/"evolucao.csv")
            record["evolucao"] = json.loads(evolution[["geracao","avaliados","segundos","aptidao"]].to_json(orient="records"))
            pool = pd.read_csv(work/"ag"/"candidatos.csv")
            columns = [c for c in pool if c.startswith("input:") or c in {"aptidao","drawdown_reais","resultado_reais","saidas"}]
            record["avaliacoes"] = json.loads(pool[columns].replace([-np.inf,np.inf],np.nan).to_json(orient="records"))
            record["erros_ag"] = int(pool.erro.notna().sum()) if "erro" in pool else 0
            save(job,record)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("fase", choices=("preparar","baseline","piloto","busca"))
    for name in ("dados","pesquisa","saida"):
        parser.add_argument("--"+name, required=True, type=Path)
    parser.add_argument("--fontes-extras", type=Path)
    parser.add_argument("--filtro", nargs="+")
    parser.add_argument("--refazer-baseline", action="store_true")
    parser.add_argument("--workers", type=int, nargs="+", default=[12])
    args=parser.parse_args()
    if args.saida.resolve().is_relative_to(REPO):
        parser.error("Escreva bases e resultados privados fora do checkout.")
    if args.fase=="preparar":
        setup(args)
    else:
        run(args)


if __name__=="__main__":
    main()
