# Sondas G3, G4 e 03 de ajuste à grade no Profit

WINZ26, **26/10/2026**, 1 minuto, America/Sao_Paulo. Foram conferidos três Backtests OHLC nativos, um por sonda, e oito replays no simulador. **G3 e G4 encerram a confirmação nativa dos exemplos de recompra testados.** A sonda 03 confirma seu preenchimento. O registro nativo dos níveis aceitos no stop-limit segue pendente. [Passo a passo para a captura](captura_pendente_03.md)

O motor executado foi `db9ace693c9396d87198e0973d9708ddeb7668d4`, conferido no head inicial do PR `ca1b602481e25802d0d5369afa159c677dc5316e`. As estratégias e o motor são os mesmos desses SHAs. A opção `--ajuste-tick-saidas-venda` continua experimental e limitada a `exit_long`. [Protocolo, opções e regressões anteriores](../WINZ26_ajuste_tick_saidas_venda_20261026_v1/README.md)

## Inventário local e evidências no GitHub

| Fonte | Inventário e conferência |
|---|---|
| 3 consoles TXT | 22 eventos estruturados por arquivo, 11 por bloco e 2 blocos idênticos. O primeiro bloco inteiro foi lido na ordem física. São 33 eventos no derivado, dos quais 27 avaliações e 6 solicitações. Nenhum aviso adicional nos blocos. [Console sanitizado](console_profit.csv) |
| 3 CSVs de operações | 19 colunas por exportação e 1 operação completa por sonda. Cada operação contém 1 contrato na entrada e 1 na saída. Cabeçalho do operador e cotações absolutas ficaram no Windows. [Matriz por sonda](matriz_profit_simulador.csv) |
| 3 relatórios PDF | 1 página por relatório. Os totais, custos de R$ 0,00 e número de operações conferem com os CSVs. |
| 3 capturas PNG | Os painéis correspondem aos consoles. WINZ26, OHLC selecionado, 1 minuto, período de 26/10 a 26/10, quantidade e máxima 1, slippage zero, Executar nos Limites ligado. |
| Barras de referência no Windows | 8/8 barras na janela de 10:51 a 10:58, sem lacuna. OHLC idêntico nos três consoles, em `SONDA_S1_ALVO_barras.csv`, `SONDA_S1_STOP_barras.csv`, `barras_v58.csv` e na base preparada do simulador. S1 Alvo e v5.8 têm o mesmo SHA-256. [Fontes e cobertura](fontes_barras.csv) · [Barras relativas à entrada](barras_referencia.csv) |

O [inventário dos 12 anexos](inventario_anexos.csv) contém os nomes, tamanhos, SHA-256, pregão e campos conferidos. O CSV nativo relaciona as operações ao console por sonda, data, direção, quantidade, sequência e preços. A hora de contexto do NTSL e a hora de execução exportada aparecem em campos próprios.

| ARTEFATO NO GITHUB | SHA e conteúdo conferido |
|---|---|
| G1 e G2 nativas | `723838af659a8a1e3145ba22e00468dd8feae6d8`, matriz, console, barras relativas e manifesto. [Dossiê G1/G2](https://github.com/thiagozonda1989-stack/simuladorCotacao/tree/723838af659a8a1e3145ba22e00468dd8feae6d8/docs/colaboracao/evidencias/WINZ26_grade_precos_g1_g2_profit_20261026_v1) |
| Controles 01–04 de prioridade | `7fca12005a319a4feeb859054e7cfcffe3ec4926`, matriz e hashes para o controle 03 anterior. [Dossiê de prioridade](https://github.com/thiagozonda1989-stack/simuladorCotacao/tree/7fca12005a319a4feeb859054e7cfcffe3ec4926/docs/colaboracao/evidencias/WINZ26_v5_8_prioridade_protecao_profit_20261026_v1) |
| Protocolo G3/G4 e antes/depois da flag | `ca1b602481e25802d0d5369afa159c677dc5316e`, dois NTSLs, replays das sondas, checklist do Profit, regressões privadas agregadas e procedimento de captura da 03. [Dossiê da flag experimental](https://github.com/thiagozonda1989-stack/simuladorCotacao/tree/ca1b602481e25802d0d5369afa159c677dc5316e/docs/colaboracao/evidencias/WINZ26_ajuste_tick_saidas_venda_20261026_v1) |

A nova 03 tem console e operações **idênticos byte a byte** ao controle de 7fca120. PDF e print têm hashes próprios. O painel novo mostra `p_Alvo=430` e o anterior indicava 428. A sonda depende do gatilho e limite do stop, controlados por `p_Stop=793` e `p_Folga=101`. O alvo é inativo com `p_Perna=2`. [Comparação de hashes](comparacao_sonda_03.csv)

## Sequência e resultado

Em todas as sondas, a avaliação 1 de **10:51** começou zerada e solicitou a entrada a mercado. A avaliação 2 conservou o rótulo 10:51 e observou posição −1 em G3/G4 ou +1 na 03. A execução da entrada está registrada às **10:52:00**, pelo preço de abertura de 10:52. A avaliação 3, no contexto **10:52**, enviou uma única proteção. Em **10:53** e **10:54**, `HasPendingOrders=1` e a posição seguia aberta. Em **10:55**, a avaliação 6 observou posição e pendências zeradas, e o CSV registrou a saída às **10:55:00**. As avaliações até 10:58 ficaram zeradas, sem solicitações de limpeza ou de saída a mercado concorrente. O console registra a existência de pendências e a mudança de posição. O CSV informa uma operação por sonda, com horário ao segundo e preços de execução.

A barra de **10:55** tem abertura **+220**, máxima **+445**, mínima **−875** e fechamento **−260**, em pontos relativos à entrada. As barras de 10:53 e 10:54 ficam aquém dos níveis solicitados e dos candidatos na grade. Em 10:55, G3 exigia uma recompra abaixo da mínima pelo preço bruto e G4 exigia um gatilho acima da máxima pelo preço bruto. Os dois preenchimentos são compatíveis com o tick de 5 mais próximo. Como os dois ajustes de recompra aproximaram a ordem do preço, os exemplos também são compatíveis com arredondamento na direção do mercado. A rodada identifica nível efetivo no comportamento observado e deixa em aberto se o ajuste ocorre no cadastro ou na avaliação do toque. Sem histórico nativo da mesma execução, os campos de aceitação e de transição de estado ficam sem valor, assim como a ordem subminuto de disparo e preenchimento.

| Sonda | Níveis solicitados no console, relativos à entrada | Saída Profit | Resultado | Simulador com parâmetros brutos, flag OFF / ON | Controle simulador com nível na grade |
|---|---|---|---|---|---|
| G3 recompra limite | Limite −877 | 10:55:00, **−875** | **+875 pts, +R$ 175,00** | 10:58:00, −375, limpeza nos dois modos | −875 → 10:55:00, −875 |
| G4 stop de recompra | Gatilho +447, limite +1000 | 10:55:00, **+445** | **−445 pts, −R$ 89,00** | 10:58:00, −375, limpeza nos dois modos | +445 com limite +1000 → 10:55:00, +445 |
| 03 stop de venda | Gatilho −793, limite −894 | 10:55:00, **−795** | **−795 pts, −R$ 159,00** | 10:55:00, −793 / −795 | A flag de venda reproduz o preenchimento com o limite bruto |

Nos replays G3/G4, `execucoes.csv`, `console.csv` e `candles.csv` com parâmetros brutos ficaram idênticos byte a byte nos dois modos. Os controles na grade reproduziram hora, preço de saída e estado de 10:55. Os mesmos três arquivos também conferiram byte a byte com os replays correspondentes da rodada anterior. Na 03, `eventos_ordens.csv` e esses três arquivos conferiram com a rodada anterior em cada modo. A hipótese de limite bruto no simulador continua compatível com a observação nativa, porque −894 e os ticks vizinhos −895 e −890 ficam todos abaixo da mínima −875. O preço executado −795 deixa o limite aceito indeterminado. [Matriz completa de comparação](matriz_profit_simulador.csv)

## Reprodução e fontes

O extrator versionado confere os originais e os recortes independentes antes de executar novos replays. Use a raiz do repositório e destinos novos. `$originais` é a pasta local que contém os 12 anexos e os três CSVs de barras. `$barras` é a base preparada identificada em `fontes_barras.csv`. `$replays` deve ficar fora do Git. O script cria uma cópia local dos NTSLs para adaptar somente a formatação das mensagens e registra hashes dos insumos. O painel do Profit mostra `p_Alvo=877` em G3 e `p_Gatilho=447` com `p_Limite=1000` em G4. Em ambas, use `p_Data=1261026`, `p_Entrada=1051`, `p_Protecao=1052`, `p_Cancela=1056`, `p_Zera=1057` e `p_Fim=1058`. A configuração efetiva da 03 consta no passo a passo.

~~~powershell
py -3.11 -m pip install pymupdf
py -3.11 -m tools.publicar_grade_g3_g4_03_profit --originais $originais --barras $barras --replays $replays --saida $saida
py -3.11 -m pytest -q
~~~

Os oito replays usaram `--formato ohlc --segundos 60 --tick 5 --valor-ponto 0.2 --avaliacao-pos-preenchimento --protecoes-ate-cancelar --rastrear-ordens`. As variantes marcadas `flag_venda` também usaram `--ajuste-tick-saidas-venda`. A suíte local passou com **130 testes** e 12 avisos já conhecidos de fuso do pandas. As regressões privadas completas de v5.7/v5.8 são as da rodada anterior. O alcance desta rodada são as sondas G3/G4/03 com o mesmo motor. As capturas de Negócios, Preços e Ofertas têm outro nível de detalhe. A conferência aqui usa a sequência das avaliações, as barras exportadas e as operações de cada backtest. Esses arquivos não fornecem a aceitação da ordem stop-limit nem resolvem a sequência intrabar de 10:15. [Extrator](../../../../tools/publicar_grade_g3_g4_03_profit.py) · [Fontes para o Gemini](fontes_gemini.txt) · [SHA-256 dos derivados](SHA256SUMS.txt)
