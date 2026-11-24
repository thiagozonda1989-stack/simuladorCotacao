"""Busca exploratória no desenvolvimento e reavalia três perfis na janela conhecida."""
import argparse
import itertools
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from validar_pullback_20 import BASE, PROTOCOL, preparar
from avaliar_fora_amostra import compile_ntsl, executar, load_bars, operacoes, source_text

ROOT = Path(__file__).resolve().parents[1]
ESTRATEGIA = ROOT / 'docs/colaboracao/evidencias/estrategia_pullback_adaptativo_v1/pullback_tendencia_v1_5.ntsl'


def metricas(programa, quadro, dias, parametros, protocolo):
    motor = executar(programa, quadro, parametros, protocolo)
    if any(f['quantidade'] != 2 for f in motor.fills):
        raise AssertionError('Preenchimento diferente de dois contratos.')
    ops = operacoes(motor)
    if len(ops) * 2 != len(motor.fills):
        raise AssertionError('Há preenchimentos sem pareamento.')
    alvos = [float(motor.trace[i]['plot3']) for i in ops.barra_sinal]
    return_metrics = dict(alvo_medio=sum(alvos)/len(alvos), alvos_distintos=len(set(alvos)),
                          alvo_minimo=min(alvos), alvo_maximo=max(alvos))
    valor = ops.liquido_reais
    curva = valor.cumsum()
    drawdown = (curva.cummax().clip(lower=0) - curva).max()
    horas = quadro.timestamp
    entrada = horas.iloc[ops.barra_entrada].reset_index(drop=True)
    saida = horas.iloc[ops.barra_saida].reset_index(drop=True)
    resumo = valor.groupby(ops.pregao).sum().reindex(dias, fill_value=0)
    return dict(**return_metrics, operacoes=len(ops), por_dia=len(ops)/len(dias),
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
        comum = dict(p_Stop=110, p_TempoMax=5, p_MaxEntradasDia=24, p_Espera=1,
                     p_JanelaAmplitude=5)
        for fator, stop in itertools.product((0.8, 1.2, 1.6), (0.55, 0.8)):
            p = comum | dict(p_FatorAmplitude=fator, p_FatorStop=stop)
            linhas.append(dict(parametros=p, **metricas(programa, dev, treino, BASE | p, protocolo)))
        top = max(linhas, key=lambda x: x['liquido'])
        validacao = quadro(teste)
        perfis = {'dinamico':top['parametros']}
        resultado = {k:dict(parametros=p, desenvolvimento=metricas(programa,dev,treino,BASE|p,protocolo),
                           reavaliacao=metricas(programa,validacao,teste,BASE|p,protocolo))
                     for k,p in perfis.items()}
        print(json.dumps(dict(desenvolvimento=treino,reavaliacao=teste,grade=linhas,perfis=resultado),
                         ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
