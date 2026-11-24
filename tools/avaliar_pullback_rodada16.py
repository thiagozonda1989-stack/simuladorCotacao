"""Roda uma fase da comparação v1.5/v1.7 da rodada 16."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from estrategia import Engine, load_bars
from ntsl import compile_ntsl
from tools.avaliar_fora_amostra import bootstrap_media, regras_execucao
from tools.metricas_pullback_rodada16 import diagnosticar, metricas


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/colaboracao/evidencias/estrategia_pullback_falha_rompimento_v1"
BASE_DIR = ROOT / "docs/colaboracao/evidencias/estrategia_pullback_adaptativo_v1"
REFERENCE = BASE_DIR / "pullback_tendencia_v1_5.ntsl"
CANDIDATE = ROOT / "estrategias/execucao/pullback_tendencia_v1_7.ntsl"
COLUMNS = ["pregao", "barra_entrada", "barra_saida", "lado", "quantidade", "preco_entrada",
           "liquido_reais", "duracao_min", "saida_antecipada", "distancia_nivel_pts"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def frame_for(path, days, minimum):
    raw = pd.read_csv(path, sep=";", encoding="cp1252", decimal=",",
                      usecols=["Data", "Abertura", "Máxima", "Mínima", "Fechamento"])
    stamps = pd.to_datetime(raw.pop("Data"), format="%d/%m/%Y %H:%M")
    bars = raw.loc[stamps.dt.strftime("%Y-%m-%d").isin(days)].copy()
    bars.columns = ["abertura", "maxima", "minima", "fechamento"]
    bars["timestamp"] = stamps.loc[bars.index]
    if bars["timestamp"].duplicated().any():
        raise ValueError("Há carimbos duplicados nos pregões escolhidos.")
    coverage = bars.groupby(bars["timestamp"].dt.strftime("%Y-%m-%d"))["timestamp"].agg(["size", "max"])
    valid = coverage.index[(coverage["size"] >= minimum) & coverage["max"].dt.strftime("%H:%M").eq("18:24")]
    if set(valid) != set(days):
        raise ValueError(f"Pregões ausentes ou sem cobertura: {sorted(set(days) - set(valid))}.")
    with TemporaryDirectory() as tmp:
        prepared = Path(tmp) / "ohlc.csv"
        bars.sort_values("timestamp").to_csv(prepared, sep=";", index=False, decimal=",",
                                              date_format="%Y-%m-%dT%H:%M:%S")
        return load_bars(prepared, 60, "ohlc")


def replay(program, frame, parameters, protocol):
    data = protocol["dados"]
    engine = Engine(program, frame, data["tick"], parameters, data["intervalo_segundos"],
                    data["valor_ponto_reais"], regras=regras_execucao(protocol) | {"rastrear_ordens": True})
    engine.run()
    return engine


def operations(engine):
    rows = []
    for entry, closing in zip(engine.fills[::2], engine.fills[1::2], strict=True):
        mode = entry["acao"]
        assert mode in {"long", "short"} and closing["acao"] == f"exit_{mode}"
        assert entry["quantidade"] == closing["quantidade"] == 2
        assert entry["pregao"] == closing["pregao"] and closing["posicao"] == 0
        start, end = entry["barra"] - 1, closing["barra"] - 1
        early = (closing["ordem"] in {"selltocoveratmarket", "buytocoveratmarket"}
                 and end > 0 and engine.trace[end - 1].get("plot4") == 1)
        level = engine.trace[start - 1].get("plot5") if start else None
        duration = (engine.frame["timestamp"].iat[end] - engine.frame["timestamp"].iat[start])
        rows.append((entry["pregao"], start, end, mode, entry["quantidade"], entry["preco"],
                     entry["liquido_reais"] + closing["liquido_reais"], duration.total_seconds() / 60,
                     early, abs(entry["preco"] - level) if level else None))
    return pd.DataFrame(rows, columns=COLUMNS)


def summarize(engine, ops, days):
    result = metricas(ops, days)
    early = int(ops["saida_antecipada"].eq(True).sum())
    distance = ops["distancia_nivel_pts"].dropna()
    return result | {
        "preenchimentos_saida_antecipada": early,
        "solicitacoes_saida_antecipada": sum(row.get("plot4") == 1 for row in engine.trace),
        "entradas_com_nivel_congelado": len(distance),
        "distancia_entrada_nivel_mediana_pts": float(distance.median()) if len(distance) else None,
        "distancia_entrada_nivel_p90_pts": float(distance.quantile(0.9)) if len(distance) else None,
        "sinais_no_primeiro_candle_de_segmento": sum(
            bool(engine.gap[i]) for i, row in enumerate(engine.trace) if row["sinal_compra"] or row["sinal_venda"]),
        "barras_ambiguas": engine.ambiguities,
        "ordens_canceladas_lacuna": engine.orders_cancelled_at_gaps,
        "lacunas_com_posicao": engine.gaps_with_exposure,
        "custos_ida_volta_das_antecipadas_reais": early * 2,
    }


def ab_diagnostic(ref, cand, days, uncertainty):
    paired = diagnosticar(ref, cand)
    per_day = {day: diagnosticar(ref[ref["pregao"].eq(day)], cand[cand["pregao"].eq(day)]) for day in days}
    delta = cand["liquido_reais"].sum() - ref["liquido_reais"].sum()
    assert abs(paired["delta_pareadas_reais"] + paired["delta_sem_par_reais"] - delta) < 1e-8
    return paired | {
        "por_pregao": per_day,
        "ic95_media_diaria_delta_antecipadas_pareadas_reais": bootstrap_media(
            [v["delta_antecipadas_pareadas_reais"] for v in per_day.values()],
            uncertainty["reamostragens"], uncertainty["semente"]),
        "delta_liquido_total_reais": float(delta),
    }


def evaluate(path, phase, days, protocol, variants):
    frame = frame_for(path, days, 500 if phase == "desenvolvimento" else 550)
    reference, candidate = [compile_ntsl(source.read_text(encoding="utf-8-sig"))
                            for source in (REFERENCE, CANDIDATE)]
    parameters = protocol["referencia"]
    original = replay(reference, frame, parameters, protocol)
    disabled = replay(candidate, frame, parameters | {"p_AtivarSaidaFalha": 0}, protocol)
    for key in ("fills", "order_events", "trace", "logs", "ambiguities", "orders_cancelled_at_gaps", "gaps_with_exposure"):
        if getattr(original, key) != getattr(disabled, key):
            raise AssertionError(f"Adendo desligado diverge da referência em {key}.")
    ref_ops = operations(original)
    base = summarize(original, ref_ops, days)
    if phase != "inedito":
        label = "desenvolvimento" if phase == "desenvolvimento" else "reavaliacao"
        previous = read_json(BASE_DIR / "v1_5.json")["perfis"]["dinamico"][label]
        for field, aggregate in (("liquido", "liquido_reais"), ("acerto", "acerto"),
                                 ("drawdown", "drawdown_reais"), ("operacoes", "operacoes")):
            if abs(base[aggregate] - previous[field]) > 1e-8:
                raise AssertionError(f"Referência {label} diverge em {field}: {base[aggregate]} versus {previous[field]}.")
    scenarios = []
    for variant in variants:
        engine = replay(candidate, frame, parameters | variant, protocol)
        ops = operations(engine)
        metrics = summarize(engine, ops, days)
        ab = ab_diagnostic(ref_ops, ops, days, protocol["incerteza"])
        cutoff = ab["resultado_medio_referencia_nas_antecipadas_pareadas_reais"]
        gates = {
            "delta_total_positivo": ab["delta_liquido_total_reais"] > 0,
            "delta_pareado_positivo": ab["delta_pareadas_reais"] > 0,
            "delta_antecipadas_pareadas_positivo": ab["delta_antecipadas_pareadas_reais"] > 0,
            "referencia_negativa_nas_antecipadas_pareadas": cutoff is not None and cutoff < 0,
            "drawdown_nao_aumenta": metrics["drawdown_reais"] <= base["drawdown_reais"],
        }
        scenarios.append({"variante": variant, "metricas": metrics, "diagnostico": ab, "criterios": gates})
    return {
        "fase": phase, "pregoes": days, "barras": len(frame), "insumo_sha256": digest(path),
        "paridade_adendo_desligado": True, "referencia": base, "cenarios": scenarios,
    }


def selected(scenarios):
    approved = [r for r in scenarios if all(r["criterios"].values())]
    if not approved:
        return None
    choice = min(approved, key=lambda r: (
        -r["diagnostico"]["delta_liquido_total_reais"], r["metricas"]["drawdown_reais"],
        r["variante"]["p_JanelaFalha"], r["variante"]["p_ToleranciaFalhaTicks"],
    ))
    return choice["variante"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fase", choices=["desenvolvimento", "exploratorio", "inedito"], required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--congelamento", type=Path, help="Artefato da fase de desenvolvimento.")
    parser.add_argument("--dia-inedito", action="append")
    args = parser.parse_args()
    protocol_path = EVIDENCE / "protocolo.json"
    protocol = read_json(protocol_path)
    identity = {"protocolo_sha256": digest(protocol_path), "enunciado_sha256": digest(EVIDENCE / protocol["enunciado"]),
                "candidata_sha256": digest(CANDIDATE), "referencia_sha256": digest(REFERENCE)}
    phase = args.fase
    if phase == "desenvolvimento":
        days, variants = protocol[phase], protocol["variantes"]
        frozen = None
    else:
        frozen = read_json(args.congelamento) if args.congelamento else {}
        if frozen.get("fase") != "desenvolvimento" or frozen.get("identidade") != identity:
            parser.error("Informe o congelamento de desenvolvimento correspondente a este código e protocolo.")
        choice = frozen.get("variante_escolhida")
        if phase == "inedito":
            days = sorted(set(args.dia_inedito or ()))
            if not choice or not days or min(days) <= max(protocol["exploratorio"]):
                parser.error("Reserva exige candidata congelada e pregões inéditos posteriores aos conhecidos.")
        else:
            days = protocol[phase]
        variants = [choice] if choice else []
    result = evaluate(args.csv, phase, days, protocol, variants) | {"identidade": identity}
    result["variante_escolhida"] = selected(result["cenarios"]) if frozen is None else frozen["variante_escolhida"]
    if frozen is not None:
        result["congelamento_sha256"] = digest(args.congelamento)
    with args.saida.open("x", encoding="utf-8", newline="\n") as file:
        json.dump(result, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")


if __name__ == "__main__":
    main()
