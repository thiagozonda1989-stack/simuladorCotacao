# Rodadas 14 e 15 · Dois contratos e proteções adaptativas

Todos os replays usam WINZ26 de um minuto, dois contratos por posição, R$ 0,50 de custo por contrato e lado e slippage de 1 tick no motor. Os preços são alinhados à grade de 5 pontos. Seleção em 19 pregões. Os 20 pregões de reavaliação já foram usados em rodadas anteriores e são evidência exploratória. Os originais ficam privados.

## Rodada 14

A v1.4 calcula a amplitude média de High − Low no fechamento do sinal, multiplica por um fator e limita o alvo entre 50 e 220 pontos. O alvo é mantido durante a operação a partir do preço de entrada. Das 24 configurações, a selecionada usa fator 0,8 e janela de 5 barras, stop de 75 pontos, prazo de 5 barras, limite de 24 entradas e espera de 1 barra. Comparação nos 20 pregões: alvo fixo de 150 pontos com esses mesmos filtros, 249 operações, 38,2% de acerto, −R$ 590, drawdown R$ 944. Alvo dinâmico, 240 operações, 41,3%, −R$ 1.284 e drawdown R$ 1.504. A variante foi mantida como pesquisa.

## Rodada 15

A v1.5 fixa também o stop no sinal, como múltiplo da amplitude média limitado a 50–110 pontos. A v1.6 acrescenta uma separação mínima entre médias de 10% da amplitude média. Foram testados seis pares de fatores por versão. Em cada versão, a configuração de maior líquido no desenvolvimento foi reavaliada. A janela foi de 5 barras, com prazo de 5 barras, até 24 entradas e espera de 1 barra.

| Versão | Fatores alvo / stop | Líquido desenvolvimento | Operações/dia | Acerto | Duração média | Líquido nos 20 pregões | Drawdown |
|---|---|---:|---:|---:|---:|---:|---:|
| v1.4 | 0,8 / fixo | R$ 520 | 12,00 | 41,3% | 1 min 33 s | −R$ 1.284 | R$ 1.504 |
| v1.5 | 1,6 / 0,8 | R$ 698 | 11,50 | 36,5% | 2 min 11 s | −R$ 480 | R$ 1.238 |
| v1.6 | 1,6 / 0,55 | −R$ 230 | 2,25 | 26,7% | 1 min 31 s | −R$ 504 | R$ 556 |

A v1.5 reduziu a perda da v1.4 em R$ 804, porém ficou abaixo do objetivo de lucro e do acerto da v1.4. A v1.6 perdeu frequência e piorou o acerto. Nenhuma sessão atingiu R$ 3 mil. A frente permanece em 35/100.

## Reprodução

Na raiz do repositório, configure PYTHONPATH para a raiz e execute `python tools/buscar_pullback_adaptativo.py CSV_PRIVADO --estrategia CAMINHO_NTSL` para cada versão. O runner verifica dois contratos em todos os preenchimentos e o pareamento das entradas e saídas. Os JSONs contêm parâmetros e resultados agregados. A avaliação ocorreu no simulador OHLC.
