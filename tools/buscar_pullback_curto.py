"""Busca exploratória no desenvolvimento e reavalia três perfis na janela conhecida."""
import argparse
import itertools
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from validar_pullback_20 import BASE, PROTOCOL, preparar
from avaliar_fora_amostra import compile_ntsl, executar, load_bars, operacoes, source_text

ROOT = Path(__file__).resolve().parents[1]
ESTRATEGIA = ROOT / 'docs/colaboracao/evidencias/estrategia_pullback_20_pregoes_v1/pullback_tendencia_v1_3.ntsl'


def metricas(programa, quadro, dias, parametros, protocolo):
    ops = operacoes(executar(programa, quadro, parametros, protocolo))
    valor = ops.liquido_reais
    curva = valor.cumsum()
    drawdown = (curva.cummax().clip(lower=0) - curva).max()
    horas = quadro.timestamp
    entrada = horas.iloc[ops.barra_entrada].reset_index(drop=True)
    saida = horas.iloc[ops.barra_saida].reset_index(drop=True)
    resumo = valor.groupby(ops.pregao).sum().reindex(dias, fill_value=0)
    return dict(operacoes=len(ops), por_dia=len(ops)/len(dias),
                acerto=float((valor > 0).mean()), diario=float(resumo.mean()),
                liquido=float(valor.sum()), drawdown=float(drawdown),
                minutos=float((saida-entrada).dt.total_seconds().mean()/60),
                dias_meta=int((resumo >= 3000).sum()),
                melhor_dia=float(resumo.max()), pior_dia=float(resumo.min()),
                maior_frequencia=int(ops.groupby('pregao').size().max()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--estrategia', type=Path, default=ESTRATEGIA)
    args = parser.parse_args()
    b, treino, teste = preparar(args.csv)
    protocolo = json.loads(PROTOCOL.read_text(encoding='utf-8'))
    programa = compile_ntsl(source_text(args.estrategia))
    with TemporaryDirectory() as t:
        csv = Path(t)/'ohlc.csv'

        def quadro(dias):
            b[b.dia.isin(dias)].drop(columns='dia').to_csv(csv, sep=';', index=False, decimal=',')
            return load_bars(csv, 60, 'ohlc')

        dev = quadro(treino)
        linhas = []
        for alvo, stop, prazo, freq in itertools.product(
                (60, 100, 150, 200), (75, 100, 150), (2, 5), (12, 24)):
            p = dict(p_Alvo=alvo, p_Stop=stop, p_TempoMax=prazo, p_MaxEntradasDia=freq, p_Espera=1)
            linhas.append(dict(parametros=p, **metricas(programa, dev, treino, BASE | p, protocolo)))
        top = max(linhas, key=lambda x: x['liquido'])
        seguro = max((x for x in linhas if x['por_dia'] >= 8 and x['minutos'] <= 2),
                     key=lambda x: (x['liquido'] - x['drawdown'], x['liquido']))
        ativo = max((x for x in linhas if x['drawdown'] <= 500),
                    key=lambda x: (x['por_dia'], x['liquido']), default=None)
        ref = dict(p_Alvo=200,p_Stop=150,p_TempoMax=10)
        validacao = quadro(teste)
        perfis = {'referencia':ref, 'maior_liquido':top['parametros'], 'curto_risco':seguro['parametros']}
        if ativo:
            perfis['frequente_dd500'] = ativo['parametros']
        resultado = {k:dict(parametros=p, desenvolvimento=metricas(programa,dev,treino,BASE|p,protocolo),
                           reavaliacao=metricas(programa,validacao,teste,BASE|p,protocolo))
                     for k,p in perfis.items()}
        print(json.dumps(dict(desenvolvimento=treino,reavaliacao=teste,grade=linhas,perfis=resultado),
                         ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
