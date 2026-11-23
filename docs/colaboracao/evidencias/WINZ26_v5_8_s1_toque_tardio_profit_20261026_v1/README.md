# Profit OHLC · toque tardio de alvo e stop isolados

No Backtest OHLC do Profit, tanto o alvo quanto o stop-limit foram **preenchidos após espera**. Cada execução enviou uma única proteção às 10:52. A proteção seguia pendente nas avaliações de 10:53 e 10:54 e encerrou a posição às 10:55, no primeiro toque elegível. A primeira divergência com o simulador padrão foi às **10:54**, quando este já mostrava a ordem expirada. O modo diagnóstico reproduziu as duas saídas. [Matriz completa](matriz_profit_simulador.csv)

## Configuração e versão

- Profit Ultra **5.0.4.33**, Backtest **OHLC**, WINZ26, 1 minuto, pregão de **26/10/2026**, fuso America/Sao_Paulo. Quantidade e quantidade máxima 1, slippage e custos zero, “Executar nos Limites” ativo.
- A captura do alvo usa o período “Tudo” (intervalo avaliado de 12/05 a 22/11/2026). A do stop usa “3 Meses” (23/08 a 23/11/2026). Ambas cobrem as oito barras da sonda e reproduzem a mesma entrada.
- Sondas V1.0 de `eba5fcfd37baf440eed22f648b406c33e0749ffb`, parâmetros `p_Data=1261026`, `p_Entrada=1051`, `p_Protecao=1052`, `p_Cancela=1056`, `p_Zera=1057`, `p_Fim=1058`. No alvo, `p_Distancia=430`; no stop, `p_Distancia=795` e `p_Folga=100`. [Sonda alvo](../WINZ26_v5_8_s1_toque_tardio_20261026_v1/sonda_s1_alvo_toque_tardio_profit_v1_0.ntsl) · [Sonda stop](../WINZ26_v5_8_s1_toque_tardio_20261026_v1/sonda_s1_stop_toque_tardio_profit_v1_0.ntsl)
- Motor executado `142dbe882ae2a0436c4273a6e5bfa1268222e5d3`, na revisão base `eba5fcfd37baf440eed22f648b406c33e0749ffb`. Os modos padrão e diagnóstico abaixo usam os quatro replays daquela revisão. [Configuração e comandos](../WINZ26_v5_8_s1_toque_tardio_20261026_v1/README.md#reprodução-no-simulador)

## Eventos do Backtest

| Rótulo do console | Seq. | Posição / pendência | Evento observado nas duas execuções |
|---|---:|---|---|
| 10:51 | 1 | 0 / 0 | Solicitação de compra a mercado |
| 10:51 | 2 | +1 / 0 | Avaliação adicional já comprada |
| 10:52 (t) | 3 | +1 / 0 | Envio único de alvo a +430 pontos ou stop a −795, limite a −895 |
| 10:53 (t+1) | 4 | +1 / 1 | Proteção pendente, faixa sem toque |
| 10:54 (t+2) | 5 | +1 / 1 | Proteção pendente, faixa sem toque |
| 10:55 (t+3) | 6 | 0 / 0 | Primeiro toque elegível, posição zerada |
| 10:56–10:58 | 7–9 | 0 / 0 | Nenhuma solicitação de limpeza |

O CSV de operações registra, em cada execução, **compra de 1 contrato às 10:52:00 e venda de 1 às 10:55:00**, com duração de três minutos. As saídas foram de +430 pontos (R$ 86) para o alvo e −795 pontos (−R$ 159) para o stop. Os PDFs confirmam uma operação, o resultado e o custo zero em cada sonda. O `10:51` da avaliação extra é o rótulo da barra observado no console. O preenchimento de entrada leva a hora da barra seguinte no CSV, às 10:52:00. [Console normalizado](console_profit.csv) · [Operações](operacoes_profit.csv)

O OHLC concorda entre console, exportações e preparo do simulador nas oito barras. Em t+1 e t+2, as máximas relativas (+225 e +405) ficam abaixo do alvo (+430) e as mínimas (−355 e −85) acima do gatilho (−795). Em t+3, a abertura de +220 coincide com o fechamento anterior e fica entre as duas proteções. A máxima de +445 supera o alvo. A mínima de −875 cruza o gatilho e fica 20 pontos acima do limite (−895). Cada estratégia estava exposta a apenas uma dessas pernas. [OHLC relativo](barras_conferencia.csv)

## Comparação com o simulador

| Perna | Modo | Pendentes t+1 / t+2 / t+3 | Saída | Classificação |
|---|---|---|---|---|
| Alvo | Profit OHLC | 1 / 1 / 0 | 10:55, +430 pts | Preenchida após espera |
| Alvo | Simulador padrão | 1 / 0 / 0 | 10:58, −375 pts, limpeza | Expirada após t+1 |
| Alvo | Simulador diagnóstico | 1 / 1 / 0 | 10:55, +430 pts | Preenchida após espera |
| Stop | Profit OHLC | 1 / 1 / 0 | 10:55, −795 pts | Preenchida após espera |
| Stop | Simulador padrão | 1 / 0 / 0 | 10:58, −375 pts, limpeza | Expirada após t+1 |
| Stop | Simulador diagnóstico | 1 / 1 / 0 | 10:55, −795 pts | Preenchida após espera |

O modo diagnóstico usa `--no-ordem-so-proxima-barra`, que altera a validade das ordens em geral. O padrão continua com `ordem_so_proxima_barra=True`. Nas duas pernas, a primeira diferença aparece na avaliação de t+2, com posição +1 nos dois motores e pendência 1 no Profit contra 0 no simulador padrão. [Estados do simulador](../WINZ26_v5_8_s1_toque_tardio_20261026_v1/estados_simulador.csv) · [Eventos do simulador](../WINZ26_v5_8_s1_toque_tardio_20261026_v1/eventos_simulador.csv)

## Listas de ordens do Replay

As listas de ordens são de **execuções separadas no Profit Replay**, com origem de automação. A coluna “Criação” preserva a data e a hora do Replay. “Última Atualização” traz a data de execução ou exportação (23/11/2026). A associação interna das linhas “Trade” com a ordem resumida do alvo foi preservada com identificadores locais `entrada` e `protecao`.

| Replay | Vínculo e horários observados | Comparação com Backtest |
|---|---|---|
| Alvo | Trade de compra às 10:52:00.265, criação da ordem de venda às 10:53:00.189 e Trade de venda vinculado às 10:55:08.155 | +430 pts, mesmo preço de entrada e saída |
| Stop | Compra “a Mercado”, criação às 10:52:02.143. Venda exibida como “Limite”, criação às 10:53:03.665. Ambas “Executada”, sem linhas Trade ou preço de stop informado | −795 pts, entrada e saída 25 pts acima das respectivas execuções do Backtest |

A lista do stop não permite identificar o instante exato de preenchimento, a ativação do gatilho ou eventual conversão da ordem. As duas listas não comprovam o ciclo nativo das ordens do mesmo Backtest, nem oferecem vínculo OCO. Cada sonda isolada usa somente uma perna. [Linhas relativas do Replay](ordens_replay_relativas.csv) · [Comparação de preços](comparacao_replay_backtest.csv)

## Cobertura, privacidade e reprodução

- Cada exportação de barras tem 20.001 registros e cinco campos (Data, Abertura, Máxima, Mínima, Fechamento), ordenados do mais novo ao mais antigo, sem duplicidade de timestamp. As 19.449 barras comuns têm OHLC idêntico. O workbook sem extensão `[Pasta1]SONDA_S1_ALVO_barras` repete integralmente o CSV do alvo após leitura de datas e valores. As séries completas têm 173 intervalos intradiários acima de 60 s no alvo e 137 no stop. A janela de **10:51 a 10:58 não tem lacunas**. [Cobertura](cobertura_barras.csv)
- Cada console contém dois blocos estruturados idênticos. O primeiro foi preservado em ordem física com 11 eventos (nove avaliações, uma compra e uma proteção). A avaliação extra repete o mesmo `CurrentBar`. As operações, as barras e os consoles do Backtest foram relacionados por pregão, ativo, janela, direção, quantidades e preços. As fontes são sondas OHLC, portanto o cruzamento não usa capturas RTD de Negócios ou Ofertas.
- Os 13 originais continuam no Windows. O inventário registra nomes, tamanhos e SHA-256. As tabelas publicam preços em pontos relativos, sem conta, titular ou identificadores nativos. A auditoria dos IDs e a recomputação desde as barras exportadas exigem os originais. [Inventário](inventario.csv) · [Manifesto](SHA256SUMS.txt) · [Fontes completas para o Gemini](fontes_gemini.txt)

```powershell
py -3.11 -m tools.publicar_s1_toque_tardio_profit --originais $pastaPrivada --referencia $pastaEvidenciasSondagem --saida $saidaNova
py -3.11 -m pytest -q
```

Use a pasta da sondagem inicial como referência. O extrator lê os originais e grava somente em um destino novo. A suíte passou com **89 testes e 12 avisos de fuso horário do pandas**.

As sondas sustentam a persistência das duas proteções isoladas nesta janela OHLC. O experimento não altera a validade padrão nem a regra de stop-limit. A opção experimental de entrada a mercado através de lacuna continua restrita a uma entrada elegível com posição zerada. Posição exposta com proteção pendente na lacuna (caso 2) permanece fora da paridade demonstrada. A saída de 10:15 continua ambígua em OHLC. [Aceitação e limites anteriores](../WINZ26_v5_8_s1_toque_tardio_20261026_v1/README.md)
