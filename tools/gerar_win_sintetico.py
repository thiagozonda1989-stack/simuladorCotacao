"""Gera pregões sintéticos de WIN em barras de 1 minuto, de forma determinística.

Os dados servem para exercitar o protocolo de avaliação fora da amostra.
Eles não representam o mercado real e não medem desempenho de estratégia.

Parâmetros fixados antes de qualquer estratégia ser testada:
- 565 barras por pregão (09:00 a 18:24), tick de 5 pontos, preço inicial 125.000.
- Cada minuto tem 12 passos de 5 segundos; máxima e mínima vêm desses passos.
- Volatilidade intradiária em U, agrupamento de volatilidade (GARCH simples)
  e choques com cauda pesada (t de Student, 4 graus de liberdade).
- Regime diário sorteado: 40% tendência (deriva ±) e 60% lateral
  (reversão à abertura do dia). Gap de abertura com desvio de 300 pontos.

Versões do gerador:
- 1: deriva de 0,04 a 0,10 desvio por passo. Gerava dias de tendência de ~5%
  (cerca de 6.000 pontos), irreal para o WIN. Mantida só para reproduzir a rodada 1.
- 2: deriva de 0,01 a 0,025 desvio por passo (~1% a 2% num dia de tendência).
  Mesma semente e mesmos sorteios de regime da versão 1.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

TICK = 5
BARRAS_POR_PREGAO = 565
PASSOS_POR_BARRA = 12


def dias_uteis(inicio, quantidade):
    return pd.bdate_range(inicio, periods=quantidade)


def perfil_intradiario(n=BARRAS_POR_PREGAO):
    x = np.linspace(-1, 1, n)
    return 0.75 + 0.6 * x**2


DERIVA = {1: (0.04, 0.10), 2: (0.01, 0.025)}


def gerar(pregoes=60, semente=20261124, inicio="2026-07-01", preco_inicial=125_000.0, versao=2,
          com_regimes=False):
    if versao not in DERIVA:
        raise ValueError(f"Versão do gerador desconhecida: {versao}.")
    deriva_min, deriva_max = DERIVA[versao]
    rng = np.random.default_rng(semente)
    regimes = []
    perfil = perfil_intradiario()
    linhas = []
    preco = preco_inicial
    variancia = 1.0
    for dia in dias_uteis(inicio, pregoes):
        preco += rng.normal(0, 300)
        abertura_dia = preco
        tendencia = rng.random() < 0.4
        deriva = rng.choice([-1, 1]) * rng.uniform(deriva_min, deriva_max) if tendencia else 0.0
        regimes.append((dia.strftime("%Y-%m-%d"), "tendencia" if tendencia else "lateral", round(float(deriva), 4)))
        for barra in range(BARRAS_POR_PREGAO):
            choque_barra = rng.standard_t(4)
            variancia = 0.05 + 0.10 * choque_barra**2 / 2 + 0.85 * variancia
            sigma_passo = 14.0 * perfil[barra] * np.sqrt(variancia)
            abertura = preco
            passos = []
            for _ in range(PASSOS_POR_BARRA):
                reversao = 0.0 if tendencia else -0.002 * (preco - abertura_dia)
                preco += sigma_passo * (rng.standard_t(4) / np.sqrt(2) + deriva) + reversao
                passos.append(preco)
            valores = np.array([abertura, *passos])
            stamp = dia + pd.Timedelta(hours=9, minutes=barra)
            linhas.append((stamp, abertura, valores.max(), valores.min(), preco,
                           int(rng.lognormal(6.5, 0.4) * (1 + abs(preco - abertura) / 50))))
    frame = pd.DataFrame(linhas, columns=["timestamp", "abertura", "maxima", "minima", "fechamento", "volume"])
    for coluna in ("abertura", "maxima", "minima", "fechamento"):
        frame[coluna] = (frame[coluna] / TICK).round() * TICK
    frame["maxima"] = frame[["abertura", "maxima", "fechamento"]].max(axis=1)
    frame["minima"] = frame[["abertura", "minima", "fechamento"]].min(axis=1)
    frame["timestamp"] = frame["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    if com_regimes:
        return frame, pd.DataFrame(regimes, columns=["pregao", "regime", "deriva"])
    return frame


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--saida", required=True)
    p.add_argument("--pregoes", type=int, default=60)
    p.add_argument("--semente", type=int, default=20261124)
    p.add_argument("--versao", type=int, default=2)
    a = p.parse_args()
    frame = gerar(a.pregoes, a.semente, versao=a.versao)
    destino = Path(a.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destino, sep=";", index=False)
    print(f"{len(frame)} barras, {a.pregoes} pregões -> {destino}")


if __name__ == "__main__":
    main()
