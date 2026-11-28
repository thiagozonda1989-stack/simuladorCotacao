"""Prepara a amostra congelada da rodada 20 e reproduz o piloto OHLC local."""
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import subprocess

import pandas as pd

from estrategia import load_bars, source_text
from ntsl import compile_ntsl
from tools.auditar_reserva_rodada20 import audit_warmup_tail, coverage, parse, save
from tools.criterios_rodada20 import assess
from tools.preparar_paridade_profit_barras import prepare, read_profit
from tools.rodada19 import DiagnosticEngine, digest, operations, read_json, totals


DAY = "2026-11-24"
WARMUP = "2026-11-23"
PROFILES = ("v58_original", "scalper_v11_otimizada")
BASE = Path("docs/colaboracao/evidencias")
PROTOCOL = BASE / "WINZ26_decisao_elegibilidade_rodada20_v2/protocolo.json"
AUDIT = BASE / "WINZ26_decisao_elegibilidade_rodada20_v3/manifesto.json"
SAMPLE = BASE / "WINZ26_piloto_rodada20_v1/amostra.json"


def validate_coverage(warmup, pilot):
    # Sem candles artificiais. 09:03 e o primeiro rotulo de 1 minuto do dia 23.
    for day, data_day, start, count in ((WARMUP, warmup, "09:03", 562), (DAY, pilot, "09:00", 565)):
        stat = coverage(day, data_day)
        if (stat["primeiro"], stat["ultimo"], stat["barras"]) != (start, "18:24", count):
            raise ValueError(f"Cobertura esperada ausente em {day}.")
        if any(stat[key] for key in ("lacunas_internas_minutos", "timestamps_duplicados", "ohlc_invalidos")):
            raise ValueError(f"Lacuna, duplicata ou OHLC invalido em {day}.")
        if any(field["ausentes_ou_invalidos"] for field in stat["series"].values()):
            raise ValueError(f"Campo ausente ou invalido em {day}.")
    tail = audit_warmup_tail(warmup["Data"], f"{WARMUP} 18:24", 86)
    if not tail["continua"]:
        raise ValueError("Janela final de aquecimento incompleta.")
    return tail


def prepare_sample(source, prepared):
    sha = digest(source)
    published = read_json(AUDIT)
    if sha != next(m["sha256"] for m in published["fontes"] if m["papel"] == "coleta_1min"):
        raise ValueError("A captura nao e a fonte de 1 minuto auditada.")
    data = parse(source)
    day_labels = data["Data"].dt.strftime("%Y-%m-%d")
    prior = data.loc[day_labels.eq(WARMUP)]
    pilot = data.loc[day_labels.eq(DAY)]
    tail = validate_coverage(prior, pilot)
    raw = read_profit(source)
    prepared.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.concat([prepare(raw, day, raw)[0] for day in (WARMUP, DAY)], ignore_index=True)
    frame.to_csv(prepared, sep=";", decimal=",", index=False, encoding="utf-8-sig", lineterminator="\n")
    return dict(
        rodada=20, natureza="piloto_descritivo", fase="pre_replay", ativo="WINZ26", segundos=60,
        fonte_1min_sha256=sha, entrada_privada_preparada_sha256=digest(prepared),
        protocolo_sha256=digest(PROTOCOL), perfis=list(PROFILES),
        aquecimento=WARMUP, piloto=[DAY], barras={WARMUP: len(prior), DAY: len(pilot)},
        janela_final_aquecimento=tail, excluidos_da_futura_coorte_formal=[WARMUP, DAY],
        primeira_barra_replay_do_profit=f"{WARMUP}T09:03:30-03:00",
        fonte_horario="Captura visual WINZ26 1 segundo em Replay, cruzada com a exportacao subminuto.",
        replays_executados=0,
    )


class PilotEngine(DiagnosticEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ambiguities_by_day = Counter()

    def process_orders(self, *args, **kwargs):
        before = self.ambiguities
        super().process_orders(*args, **kwargs)
        self.ambiguities_by_day[self.days[self.row]] += self.ambiguities - before


def evaluate_profile(name, config, frame, first):
    profile = config["perfis"][name]
    path = Path(profile["arquivo"])
    if digest(path) != profile["sha256"]:
        raise ValueError(f"Fonte da estrategia alterada: {name}.")
    program = compile_ntsl(source_text(path))
    params = profile["parametros"]
    if set(params) != set(program.inputs) or params["p_lote"] != config["lote"]:
        raise ValueError(f"Parametros congelados invalidos: {name}.")
    engine = PilotEngine(program, frame, config["tick_pontos"], params, config["segundos"],
                         config["reais_por_ponto_contrato"], regras=config["regras_execucao"])
    engine.run(record_trace=False)
    engine.cursor = first
    prior_available = first - engine.history_start
    if prior_available < 86 or engine.series("date", 1) != int(frame["data_ntsl"].iat[first - 1]):
        raise ValueError("O motor nao recebeu o aquecimento anterior esperado.")
    trades = [trade for trade in operations(engine, frame, config["lote"]) if trade["pregao"] == DAY]
    max_exposure = max((abs(fill["posicao"]) for fill in engine.fills if fill["pregao"] == DAY), default=0)
    evaluated = assess({DAY: [trade["centavos"] / 100 for trade in trades]}, max_exposure, name,
                       config["validacao_inedita"])
    return dict(
        totais=totals(trades), exposicao_maxima=max_exposure,
        ambiguidades_ohlc=engine.ambiguities_by_day[DAY],
        operacoes_por_motivo_saida=dict(sorted(Counter(t["motivo_saida"] for t in trades).items())),
        no_inicio=dict(
            currentbar=int(engine.series("currentbar")), barras_previas_disponiveis=prior_available,
            barras_no_segmento=int(frame["barras_no_segmento"].iat[first]),
            lacuna_intradiaria=bool(engine.gap[first]),
        ),
        avaliacao=evaluated,
    )


def run_sample(prepared, output):
    sample = read_json(SAMPLE)
    config = read_json(PROTOCOL)
    if digest(prepared) != sample["entrada_privada_preparada_sha256"] or digest(PROTOCOL) != sample["protocolo_sha256"]:
        raise ValueError("A entrada ou o protocolo difere do congelamento publicado.")
    if output.exists():
        raise ValueError("O resultado ja existe.")
    frame = load_bars(prepared, config["segundos"], "ohlc")
    if (frame["pregao"].unique().tolist() != [WARMUP, DAY]
            or frame["pregao"].value_counts().to_dict() != sample["barras"]
            or frame["lacuna_intradiaria"].any()):
        raise ValueError("O replay exige os dois pregoes congelados, sem lacunas intradiarias.")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    first = sample["barras"][WARMUP]
    result = dict(
        sha_executado=head, amostra_sha256=digest(SAMPLE), datas_expostas=[WARMUP, DAY],
        pregao_relatorio=DAY, aquecimento=WARMUP, avaliacoes_por_perfil=1,
        perfis={name: evaluate_profile(name, config, frame, first) for name in PROFILES},
    )
    save(output, result)


def main():
    parser = ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preparar", type=Path, metavar="CSV_PROFIT")
    actions.add_argument("--executar", action="store_true")
    parser.add_argument("--entrada-privada", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    if args.preparar:
        if args.preparar.resolve() == args.entrada_privada.resolve() or args.entrada_privada.exists() or args.saida.exists():
            parser.error("Use caminhos novos para a entrada derivada e o manifesto.")
        save(args.saida, prepare_sample(args.preparar, args.entrada_privada))
    else:
        run_sample(args.entrada_privada, args.saida)


if __name__ == "__main__":
    main()
