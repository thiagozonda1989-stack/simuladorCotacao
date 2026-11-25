"""Compara o contador da v5.8 apenas na base conhecida da rodada 19."""
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path
import subprocess

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl
from tools.inventario_rodada19 import save
from tools.rodada19 import (
    DiagnosticEngine, EVIDENCE, digest, operations, read_json, totals,
)

RESET = "  if Date <> Date[1] then\n    v_Entradas_Dia := 0;"
CONTROL = """  if Date <> v_DataContagem then
  begin
    v_Entradas_Dia := 0;
    v_DataContagem := Date;
  end;"""


def counter_control(source):
    declaration = "  v_Qtd                : Integer;"
    if source.count(RESET) != 1 or source.count(declaration) != 1:
        raise ValueError("A fonte da v5.8 não corresponde à hipótese registrada.")
    return source.replace(RESET, CONTROL).replace(
        declaration, declaration + "\n  v_DataContagem : Integer;"
    )


class GapDiagnostic(DiagnosticEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gaps = []
        self.early_rows = 0
        self.early_requests = 0

    def evaluate_strategy(self, event="avaliacao_ntsl"):
        count_before = self.value("v_entradas_dia")
        position = self.position
        previous_date = self.series("date", 1)
        segments = int(self.frame["barras_no_segmento"].iat[self.row])
        warmup = sum(self.value(name) for name in
                     ("p_periodo_atr", "p_periodo_regime_atr", "p_periodo_desvio")) + 2
        super().evaluate_strategy(event)
        warmed = bool(self.value("v_aquecido"))
        request = bool(self.entry_intentions)
        if self.segment_starts[self.row] > self.session_start and segments <= warmup and warmed:
            self.early_rows += 1
            self.early_requests += request
        if self.gap[self.row]:
            self.gaps.append(dict(
                pregao=self.days[self.row],
                antes=int(count_before), depois=int(self.value("v_entradas_dia")),
                date_1=int(previous_date), barra=int(self.series("currentbar")),
                barras_no_segmento=segments, aquecido=warmed, posicao=int(position),
                atr=float(self.value("v_atr")), media_atr=float(self.value("v_media_atr")),
                solicitacao=request,
            ))


def replay(source, parameters, frame, frozen):
    args = (compile_ntsl(source), frame, frozen["tick_pontos"], parameters,
            frozen["segundos"], frozen["reais_por_ponto_contrato"])
    engine = GapDiagnostic(*args, regras=frozen["regras_execucao"])
    engine.run(record_trace=False)
    trades = operations(engine, frame, frozen["lote"])
    return engine, trades, args


def report_for(profile, frame, days, frozen):
    code = source_text(Path(profile["arquivo"]))
    if digest(Path(profile["arquivo"])) != profile["sha256"]:
        raise ValueError("A fonte publicada da v5.8 mudou.")
    base, original, args = replay(code, profile["parametros"], frame, frozen)
    plain = Engine(*args, regras=frozen["regras_execucao"])
    plain.run(record_trace=False)
    if plain.fills != base.fills or plain.ambiguities != base.ambiguities:
        raise ValueError("O diagnóstico não pode alterar o perfil original.")
    alternative, counter, _ = replay(counter_control(code), profile["parametros"], frame, frozen)
    baseline = totals(original)
    expected = profile["referencia_rodada18"]
    if any(baseline[k] != expected[k] for k in ("operacoes", "acertos", "liquido", "drawdown_max")):
        raise ValueError("O baseline conhecido diverge da referência.")
    per_day = {}
    for day in days:
        per_day[day] = {name: totals([t for t in trades if t["pregao"] == day])
                        for name, trades in (("congelado", original), ("contador_escalar", counter))}
    return dict(
        congelado=baseline, contador_escalar=totals(counter), pregoes=per_day,
        fills_identicos=base.fills == alternative.fills,
        ambiguidades=dict(congelado=base.ambiguities, contador_escalar=alternative.ambiguities),
        lacunas_por_pregao=dict(Counter(x["pregao"] for x in base.gaps)),
        estados_lacunas=dict(congelado=base.gaps, contador_escalar=alternative.gaps),
        barras_aquecido_antes_de_janela_completa=base.early_rows,
        entradas_solicitadas_nessas_barras=base.early_requests,
    )


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--base-conhecida", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    frozen = read_json(EVIDENCE / "perfis.json")
    if digest(args.base_conhecida) != frozen["base_sha256"]:
        raise ValueError("Use somente a base conhecida e congelada da rodada anterior.")
    days = frozen["pregoes_conhecidos"]
    frame = load_bars(args.base_conhecida, frozen["segundos"], "ohlc")
    frame = frame.loc[frame.pregao.isin(days)].reset_index(drop=True)
    if frame.pregao.unique().tolist() != days or len(days) != 20:
        raise ValueError("O diagnóstico exige os mesmos 20 pregões.")
    report = {}
    for name in ("v58_original", "v58_otimizada_diagnostico"):
        report[name] = report_for(frozen["perfis"][name], frame, days, frozen)
    save(args.saida, dict(
        sha_executado=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        barras=len(frame), replays_na_reserva=0, perfis=report,
    ))


if __name__ == "__main__":
    main()