"""Seleciona no desenvolvimento e compara um único candidato em 20 pregões."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from comparar_pullback_v1_1 import ROOT, PROTOCOL
from avaliar_fora_amostra import medir, rotular
from avaliar_fora_amostra import (
    bootstrap_media, compile_ntsl, executar, load_bars, operacoes, source_text,
)

BASE = dict(p_Rapida=20, p_Lenta=21, p_Alvo=200, p_Stop=300, p_TempoMax=15,
            p_MaxEntradasDia=2, p_Espera=3, p_HoraInicio=1000)
EXCLUIDOS = {'2026-10-21', '2026-10-26'}


def preparar(origem):
    dado = pd.read_csv(origem, sep=';', encoding='cp1252', decimal=',')
    tempo = pd.to_datetime(dado['Data'], format='%d/%m/%Y %H:%M')
    if tempo.duplicated().any():
        raise ValueError('Há timestamps duplicados no CSV.')
    barras = dado[['Abertura', 'Máxima', 'Mínima', 'Fechamento']].copy()
    barras.columns = ['abertura', 'maxima', 'minima', 'fechamento']
    barras['timestamp'] = tempo.dt.strftime('%Y-%m-%dT%H:%M:%S')
    barras['dia'] = tempo.dt.strftime('%Y-%m-%d')
    grupo = barras.groupby('dia')['timestamp'].agg(['size', 'max'])
    completos = grupo['max'].str.endswith('18:24:00')
    confirmacao = sorted(set(grupo.index[completos & (grupo['size'] >= 550)]) - EXCLUIDOS)[-20:]
    if len(confirmacao) != 20:
        raise ValueError('São necessários 20 pregões elegíveis para confirmação.')
    treino = sorted(d for d in grupo.index[completos & (grupo['size'] >= 500)]
                    if d < confirmacao[0] and d not in EXCLUIDOS)
    if len(treino) < 10:
        raise ValueError('São necessários pelo menos 10 pregões de desenvolvimento.')
    return barras.sort_values('timestamp'), treino, confirmacao


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    args = parser.parse_args()
    barras, treino, teste = preparar(args.csv)
    protocolo = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    programas = {
        v: compile_ntsl(source_text(ROOT / (f'estrategias/pesquisa/pullback_tendencia_v1_{v}.ntsl' if v == 1 else f'docs/colaboracao/evidencias/estrategia_pullback_20_pregoes_v1/pullback_tendencia_v1_{v}.ntsl')))
        for v in (1, 2, 3)
    }
    with TemporaryDirectory() as tmp:
        csv = Path(tmp) / 'ohlc.csv'

        def quadro(dias):
            barras[barras['dia'].isin(dias)].drop(columns='dia').to_csv(csv, sep=';', index=False, decimal=',')
            return load_bars(csv, 60, 'ohlc')

        desenvolvimento = quadro(treino)
        grade = [(200, 300, 15), (150, 150, 10), (100, 150, 10),
                 (200, 150, 10), (150, 250, 10), (250, 200, 15)]
        ranking = []
        for v, programa in programas.items():
            for alvo, stop, tempo in grade:
                parametros = dict(p_Alvo=alvo, p_Stop=stop, p_TempoMax=tempo)
                ops = operacoes(executar(programa, desenvolvimento, BASE | parametros, protocolo))
                ranking.append(dict(versao=v, parametros=parametros, operacoes=len(ops),
                                    acertos=int((ops.liquido_reais > 0).sum()),
                                    liquido=float(ops.liquido_reais.sum())))
        elegiveis = [r for r in ranking if r['operacoes'] >= len(treino)
                     and 100 * r['acertos'] >= 45 * r['operacoes']]
        if not elegiveis:
            elegiveis = [r for r in ranking if r['operacoes'] >= len(treino)]
        escolhida = max(elegiveis, key=lambda r: r['liquido'])
        confirmacao = quadro(teste)
        modelo = programas[escolhida['versao']]
        parametros = BASE | escolhida['parametros']
        # Os dois motores recebem a mesma série, com parâmetros congelados por versão.
        rotulos = rotular(confirmacao, 150, 30)
        motores = {
            'baseline': executar(programas[1], confirmacao, BASE, protocolo),
            'candidata': executar(modelo, confirmacao, parametros, protocolo),
        }
        r = {nome: medir(confirmacao, motor, teste, rotulos, protocolo)
             for nome, motor in motores.items()}
        diarios = {
            nome: operacoes(motor).groupby('pregao')['liquido_reais'].sum().reindex(teste, fill_value=0)
            for nome, motor in motores.items()
        }
        r['delta_por_pregao'] = (diarios['candidata'] - diarios['baseline']).tolist()
        r['liquido_por_pregao'] = {nome: serie.tolist() for nome, serie in diarios.items()}
        r['ic95_delta_diario'] = bootstrap_media(r['delta_por_pregao'], 2000, 11)
        print(json.dumps(dict(treino=treino, teste=teste, ranking=ranking,
                              escolhida=escolhida, baseline=BASE, confirmacao=r),
                         ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
