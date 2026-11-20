"""Diagnóstico controlado da lacuna de 26/10/2026 às 09:39."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import estrategia
from tools.comparar_v5_8 import audit_by_label, console_lines, unique_native_capture


DAY = "2026-10-26"


def require_flat_boundary(group):
    for label in ("09:29", "09:39"):
        events = group.get(label, [])
        if len(events) != 1 or events[0][0] != "AVALIACAO":
            raise ValueError(f"Limite da lacuna {label}: esperada uma avaliação sem solicitação.")
        state = events[0][1]
        if state["posicao"] != 0 or state["pendentes"] != 0:
            raise ValueError(f"Limite da lacuna {label}: há posição ou ordem pendente.")


class DiagnosticEngine(estrategia.Engine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stamp = pd.to_datetime(self.frame["timestamp"])
        index = np.flatnonzero(stamp.dt.strftime("%Y-%m-%d %H:%M").eq(DAY + " 09:39"))
        if len(index) != 1 or not self.gap[index[0]]:
            raise ValueError("A barra de retomada precisa ser uma lacuna única em 26/10 às 09:39.")
        self.gap = self.gap.copy()
        self.gap[index[0]] = False
        self.segment_starts = np.maximum.accumulate(np.where(self.gap, np.arange(len(self.frame)), 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("barras", "ntsl", "inputs", "console-profit", "console-referencia", "saida"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    capture, _ = unique_native_capture(console_lines(args.console_profit, True))
    require_flat_boundary(audit_by_label(capture, DAY, True))
    require_flat_boundary(audit_by_label(console_lines(args.console_referencia, False), DAY, False))
    rules = dict(avaliacao_pos_preenchimento=True, rastrear_ordens=True,
                 volume_financeiro_ntsl=True, agressao_referencia_injetada=True, vwap_continuo_lacunas=True)
    engine = estrategia.Engine
    try:
        estrategia.Engine = DiagnosticEngine
        stats = estrategia.run_strategy(args.barras, estrategia.source_text(args.ntsl), args.saida,
                                        60, "ohlc", 5, json.loads(args.inputs.read_text(encoding="utf-8")),
                                        0.2, regras=rules)
    finally:
        estrategia.Engine = engine
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
