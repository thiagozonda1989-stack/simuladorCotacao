"""Compara o pullback original com confirmação no fechamento, sem reseleção."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from avaliar_fora_amostra import (
    bootstrap_media, compile_ntsl, executar, load_bars, medir, operacoes,
    rotular, sortear_variacoes, source_text,
)
from gerar_win_sintetico import gerar


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'docs/colaboracao/evidencias/estrategia_pullback_fora_amostra_sintetico_v1/protocolo.json'


def comparar(frame, dias, programas, parametros, protocolo):
    rotulos = rotular(frame, 150, 30)
    motores = [executar(p, frame, parametros, protocolo) for p in programas]
    metricas = [medir(frame, m, dias, rotulos, protocolo) for m in motores]
    diarios = [
        operacoes(m).groupby('pregao')['liquido_reais'].sum().reindex(dias, fill_value=0)
        for m in motores
    ]
    delta = (diarios[1] - diarios[0]).to_numpy()
    return {
        'original': metricas[0], 'candidata': metricas[1],
        'delta_por_pregao': delta.tolist(),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, help='Coorte OHLC elegível e congelada para teste')
    args = parser.parse_args()
    protocolo = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    caminho = ROOT / protocolo['estrategia']
    programas = [
        compile_ntsl(source_text(caminho)),
        compile_ntsl(source_text(caminho.with_name('pullback_tendencia_v1_1.ntsl'))),
    ]
    v = protocolo['variacoes']
    parametros = sortear_variacoes(v['espaco'], v['quantidade'], v['semente'], programas[0].inputs)[29]
    resultados = {}
    with TemporaryDirectory() as tmp:
        arquivo = Path(tmp) / 'win.csv'
        sementes = ['csv'] if args.csv else [20261124, 20261125, 20261126, 20261127]
        for semente in sementes:
            if args.csv:
                fonte = args.csv
            else:
                gerar(60 if semente == 20261124 else 18, semente=semente).to_csv(arquivo, sep=';', index=False)
                fonte = arquivo
            frame = load_bars(fonte, 60, 'ohlc')
            dias = sorted(frame['pregao'].unique())
            if semente == 20261124:
                dias = dias[-18:]
            resultados[str(semente)] = comparar(frame, dias, programas, parametros, protocolo)
    coortes = [r for s, r in resultados.items() if s != '20261124']
    delta = np.concatenate([r['delta_por_pregao'] for r in coortes])
    baseline = sum(r['original']['resultado_liquido_reais'] for r in coortes)
    print(json.dumps({
        'parametros': parametros, 'coortes': resultados,
        'confirmacao': {'baseline': baseline, 'liquido_candidata': baseline + float(delta.sum()),
                        'delta_reais': float(delta.sum()),
                        'meta_delta_reais': 0.1 * abs(baseline),
                        'delta_diario_ic95': None if args.csv else bootstrap_media(delta, 2000, 11)},
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
