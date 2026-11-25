"""Mede o poder preditivo das variáveis físicas da estratégia Física do Mercado.

As variáveis são lidas do próprio motor (histórico das variáveis NTSL), então o
estudo mede exatamente o que a estratégia calcula. Só agregados são gravados,
o que permite rodar sobre CSV privado no computador local e publicar o JSON.

Para cada variável, em cada barra elegível do recorte:
- direcao: Spearman com o retorno futuro de h barras (mesmo pregão).
- continuacao: Spearman com o retorno futuro multiplicado pelo sinal do
  deslocamento passado de N barras (> 0 favorece seguir a tendência).
- amplitude: Spearman com |retorno futuro| (prevê movimento, sem direção).
Intervalos de 95% por bootstrap de pregões inteiros.

Controle negativo: fase da Lua (fenômeno natural externo, calculado pela data).
Ela é constante no pregão, então não deveria prever nada intradiário. Se aparecer
"significativa", o método está gerando falsos positivos.
"""
from argparse import ArgumentParser
import json
from pathlib import Path

import numpy as np
import pandas as pd

from estrategia import Engine, load_bars, source_text
from ntsl import compile_ntsl

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "estrategias/pesquisa/fisica_mercado_v1_0.ntsl"
VARIAVEIS = {
    "massa": "v_massa", "momento": "v_momento", "energia_cinetica": "v_cinetica",
    "temperatura": "v_templonga", "aquecimento": "v_aquecimento", "entropia": "v_entropia",
    "razao_variancia": "v_vr", "hurst": "v_hurst", "eficiencia": "v_eficiencia",
    "deslocamento_mola": "v_x", "velocidade_mola": "v_v", "energia_potencial": "v_potencial",
    "pressao": "v_pressao",
}
LUA_NOVA_REFERENCIA = pd.Timestamp("2000-01-06 18:14", tz="UTC")
MES_SINODICO = 29.530588853


def fase_lunar(datas):
    """Fração do ciclo sinódico (0 = lua nova, 0,5 = cheia); erro de algumas horas."""
    t = pd.to_datetime(datas).dt.tz_localize("America/Sao_Paulo").dt.tz_convert("UTC")
    dias = (t - LUA_NOVA_REFERENCIA).dt.total_seconds() / 86400.0
    return (dias / MES_SINODICO) % 1.0


def series_do_motor(frame, parametros=None):
    programa = compile_ntsl(source_text(FONTE))
    motor = Engine(programa, frame, 5, parametros or {}, 60, 0.2,
                   regras={"custo_por_contrato_lado": 0.5, "slippage_ticks": 1})
    motor.run(record_trace=False)
    dados = {nome: motor.history[:, programa.symbols[s].slot] for nome, s in VARIAVEIS.items()}
    entrada = {**programa.inputs, **{k.lower(): v for k, v in (parametros or {}).items()}}
    aquecimento = int(entrada["p_janelamola"] + entrada["p_janela"] + entrada["p_q"] + 2)
    janela = int(entrada["p_janela"])
    return pd.DataFrame(dados), aquecimento, janela


def montar(frame, horizonte, parametros=None):
    variaveis, aquecimento, janela = series_do_motor(frame, parametros)
    base = pd.DataFrame({"pregao": frame["pregao"].values, "fechamento": frame["fechamento"].values})
    grupo = base.groupby("pregao")["fechamento"]
    base["futuro"] = grupo.shift(-horizonte) - base["fechamento"]
    base["passado"] = base["fechamento"] - grupo.shift(janela)
    base["lua_fase"] = fase_lunar(frame["timestamp"]).values
    base["lua_iluminacao"] = (1 - np.cos(2 * np.pi * base["lua_fase"])) / 2
    tabela = pd.concat([base, variaveis], axis=1)
    tabela = tabela.iloc[aquecimento:]
    return tabela.dropna(subset=["futuro", "passado"]).reset_index(drop=True)


def spearman(x, y):
    if len(x) < 30 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(pd.Series(x).rank().corr(pd.Series(y).rank()))


def medir(tabela, nomes, reamostragens=500, semente=11):
    alvos = {
        "direcao": tabela["futuro"].to_numpy(),
        "continuacao": (tabela["futuro"] * np.sign(tabela["passado"])).to_numpy(),
        "amplitude": tabela["futuro"].abs().to_numpy(),
    }
    pregoes = tabela["pregao"].to_numpy()
    unicos = np.unique(pregoes)
    indices = {p: np.flatnonzero(pregoes == p) for p in unicos}
    rng = np.random.default_rng(semente)
    amostras = [np.concatenate([indices[p] for p in rng.choice(unicos, len(unicos))])
                for _ in range(reamostragens)]
    saida = {}
    for nome in nomes:
        x = tabela[nome].to_numpy()
        saida[nome] = {}
        for alvo, y in alvos.items():
            pontos = [spearman(x[i], y[i]) for i in amostras]
            baixo, alto = np.nanpercentile(pontos, [2.5, 97.5])
            saida[nome][alvo] = dict(rho=round(spearman(x, y), 4), ic95=[round(float(baixo), 4), round(float(alto), 4)],
                                     significativo=bool(baixo > 0 or alto < 0))
    return saida


def estudar(caminho_csv, horizonte=10, pregoes_estudo=None, reamostragens=500):
    frame = load_bars(caminho_csv, 60, "ohlc")
    tabela = montar(frame, horizonte)
    if pregoes_estudo is not None:
        tabela = tabela[tabela["pregao"].isin(pregoes_estudo)].reset_index(drop=True)
    nomes = list(VARIAVEIS) + ["lua_fase", "lua_iluminacao"]
    return dict(
        horizonte_barras=horizonte, barras=int(len(tabela)), pregoes=int(tabela["pregao"].nunique()),
        intervalo=[str(tabela["pregao"].iloc[0]), str(tabela["pregao"].iloc[-1])],
        reamostragens_bootstrap_pregao=reamostragens,
        resultados=medir(tabela, nomes, reamostragens),
        quantis={n: [round(float(q), 4) for q in np.nanpercentile(tabela[n], [5, 25, 50, 75, 95])]
                 for n in VARIAVEIS},
    )


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("--csv", required=True)
    p.add_argument("--saida", required=True)
    p.add_argument("--horizonte", type=int, default=10)
    p.add_argument("--primeiros-pregoes", type=int, help="estuda só os N primeiros pregões (treino)")
    p.add_argument("--reamostragens", type=int, default=500)
    a = p.parse_args()
    pregoes = None
    if a.primeiros_pregoes:
        todos = sorted(load_bars(a.csv, 60, "ohlc")["pregao"].unique())
        pregoes = todos[:a.primeiros_pregoes]
    resultado = estudar(a.csv, a.horizonte, pregoes, a.reamostragens)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in resultado.items() if k not in ("resultados", "quantis")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
