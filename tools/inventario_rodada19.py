"""Inventaria cobertura de exportações Profit por hash, sem executar estratégias."""
import argparse
import json
from pathlib import Path

import pandas as pd

from tools.preparar_paridade_profit_barras import read_profit
from tools.rodada19 import digest

OHLC = ("Abertura", "Máxima", "Mínima", "Fechamento")


def inventory(path):
    data = read_profit(path)
    stamp = pd.to_datetime(data["Data"], format="%d/%m/%Y %H:%M")
    minute = stamp.dt.hour * 60 + stamp.dt.minute
    if stamp.isna().any():
        raise ValueError("Timestamp ausente no exportador Profit.")
    prices = data[list(OHLC)]
    bad = (prices.isna().any(axis=1)
           | prices["Máxima"].lt(prices[["Abertura", "Fechamento", "Mínima"]].max(axis=1))
           | prices["Mínima"].gt(prices[["Abertura", "Fechamento"]].min(axis=1)))
    coverage = {}
    for day, positions in stamp.groupby(stamp.dt.strftime("%Y-%m-%d")).groups.items():
        seen = minute.loc[positions]
        width = int(seen.max() - seen.min() + 1)
        coverage[day] = dict(
            barras=int(seen.size),
            primeiro_rotulo=stamp.loc[positions].min().strftime("%H:%M"),
            ultimo_rotulo=stamp.loc[positions].max().strftime("%H:%M"),
            duplicatas_timestamp=int(seen.duplicated().sum()),
            minutos_ausentes_no_intervalo=width - int(seen.nunique()),
            ohlc_invalidos=int(bad.loc[positions].sum()),
            por_campo_nao_nulo={name: int(data[name].loc[positions].count())
                               for name in ("Trades", "Quantity", "Volume", "v_Saldo_Agressao")
                               if name in data},
        )
    return dict(bytes=path.stat().st_size, campos=list(data),
                ordem_fisica_descendente=bool(stamp.is_monotonic_decreasing),
                cobertura=coverage)


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("fontes", nargs="+", type=Path)
    args = parser.parse_args()
    cache = json.loads(args.cache.read_text(encoding="utf-8")) if args.cache.is_file() else {}
    results = {}
    for source in args.fontes:
        if source.name in results:
            raise ValueError("Use nomes de fonte distintos no manifesto.")
        sha = digest(source)
        if sha not in cache:
            cache[sha] = inventory(source)
        result = cache[sha]
        coverage = result["cobertura"]
        dates = sorted(coverage)
        results[source.name] = dict(
            sha256=sha, **{key: value for key, value in result.items() if key != "cobertura"},
            pregoes=len(dates), primeiro_pregao=dates[0], ultimo_pregao=dates[-1],
            barras=sum(day["barras"] for day in coverage.values()),
            cobertura_recente={day: coverage[day] for day in dates if day >= "2026-11-19"},
        )
    save(args.cache, cache)
    save(args.saida, dict(janela="WINZ26, 1 minuto, America/Sao_Paulo",
                         fontes=results, replays_na_reserva=0))


if __name__ == "__main__":
    main()
