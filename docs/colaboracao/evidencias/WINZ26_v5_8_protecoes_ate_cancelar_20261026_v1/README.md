# Persistência experimental de proteções no replay OHLC

Motor executado `d67a8731bfa1597b0bdfe4cc4064e6502822f81a`. Motor de referência `142dbe882ae2a0436c4273a6e5bfa1268222e5d3`. Evidência nativa das sondas S1 `2a180c3c437cbb2bb8c3824ebb0f7275ad4f1e7a`. [S1 nativa](../WINZ26_v5_8_s1_toque_tardio_profit_20261026_v1/README.md) · [Parecer Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7115147308) · [Parecer Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7115175173)

## Regra do simulador

- `--protecoes-ate-cancelar` vem desligada e é exclusiva do OHLC. Com a validade normal de uma barra, a opção conserva saídas limite e stop-limit do lado da posição aberta, em barras consecutivas. A elegibilidade continua valendo, inclusive com latência. As entradas, os stops sem limite e as ordens genéricas limite/stop por `SendOrder` seguem a validade normal.
- `CancelPendingOrders`, zeragem, mudança de pregão e lacunas mantêm o descarte de proteções e os contadores existentes. O teste combinado preserva apenas a entrada a mercado elegível através da lacuna. A avaliação extra usa a barra anterior e pode criar proteção para a posição recém-aberta. Renovação idêntica usa a mesma chave e conserva a elegibilidade e o estado de disparo.
- Quando uma saída a mercado elegível encerra a posição na abertura e há proteção elegível, o simulador preenche a mercado, pelo preço de abertura com o slippage configurado, e remove as saídas da posição. Em seguida o NTSL avalia o fechamento com posição zerada. Os toques posteriores da barra não registram disparo, preenchimento adicional ou ambiguidade. A regra também reconhece a ordem genérica a mercado exatamente redutora via `SendOrder`. Duplo toque de proteções sem zeragem na abertura continua sujeito à regra adversa de OHLC.
- `--no-ordem-so-proxima-barra` tem precedência quando as duas flags são usadas juntas. O diagnóstico global mantém sua validade geral e sua política de ambiguidade anterior.
- A evidência nativa confirma as duas proteções isoladas em posição comprada. A prioridade da saída a mercado é uma regra do simulador com sonda Profit à espera de execução. OCO nativo, preenchimento parcial, renovação com preço alterado e persistência isolada em posição vendida são validações próprias.

## S1 · toque tardio em WINZ26

WINZ26 em 26/10/2026, barras de 1 minuto, fuso America/Sao_Paulo, tick 5, um contrato, R$ 0,20 por ponto, zero custo e slippage. A proteção é enviada uma vez no contexto 10:52. A primeira barra que pode tocar o nível é 10:55 (t+3). O rótulo 10:51 da avaliação extra e a hora 10:52 da entrada pertencem a campos distintos.

| Motor e modo | Pendentes em t+1 / t+2 / t+3 | Alvo | Stop-limit |
|---|---|---|---|
| Profit Backtest OHLC | 1 / 1 / 0 | 10:55, +430 pontos | 10:55, −795 pontos |
| Simulador padrão | 1 / 0 / 0 | 10:58, limpeza, −375 pontos | 10:58, limpeza, −375 pontos |
| Simulador com persistência | 1 / 1 / 0 | 10:55, +430 pontos | 10:55, −795 pontos |
| Simulador com diagnóstico global, com ou sem persistência | 1 / 1 / 0 | 10:55, +430 pontos | 10:55, −795 pontos |

Nos quatro arquivos de execução, o padrão ficou idêntico à rodada S1 anterior. A opção ativa igualou os quatro arquivos do diagnóstico global nas duas pernas. A primeira divergência do padrão antes da saída é a pendência às 10:54. [Matriz S1](sondas_s1.csv) · [Matriz Profit nativa](../WINZ26_v5_8_s1_toque_tardio_profit_20261026_v1/matriz_profit_simulador.csv)

## Sonda de prioridade na abertura

Execute no **Profit Backtest OHLC**, WINZ26, 1 minuto, 26/10/2026, conta de simulação no backtest, quantidade e máximo 1, slippage e custos zero, “Executar nos Limites” ativo e nenhuma zeragem horária externa entre 10:51 e 10:58. Faça quatro rodadas independentes combinando `p_Perna=1` (alvo) ou `2` (stop-limit) com `p_SaidaMercado=0` (controle) ou `1` (envio a mercado). Os demais parâmetros ficam no padrão da sonda. Compile como estratégia de execução para o Backtest OHLC.

Na janela S1, a barra 10:55 abre a +220 pontos em relação à entrada, entre o alvo +430 e o gatilho −795. A máxima chega a +445 e a mínima a −875, dentro do limite de venda −895. Em 10:54 a sonda só envia a saída a mercado se observar posição comprada e a única proteção pendente. Ela não solicita cancelamento nesse ponto. Com a opção ativa, os controles locais reproduziram as S1. Nas duas variantes com mercado, houve **uma única saída a mercado às 10:55, a +220 pontos**, posição final zero, sem evento de gatilho nem barra ambígua. Para o Profit, o horário em minutos não separa as hipóteses. Use o preço e, se disponível, o tipo e o ciclo nativo de cada ordem. [Sonda NTSL](sonda_prioridade_mercado_protecao_profit_v1_0.ntsl) · [Resultados do simulador](sonda_prioridade_simulador.csv)

Para cada combinação, exporte:

1. Console Debug completo com os eventos `PRIORIDADE;`, da avaliação inicial à última, preservando a ordem física e eventuais avisos. Use um arquivo por execução.
2. CSV de operações com ativação, lado, horários de entrada e saída, preços, quantidades e resultado. Campos de ordem ausentes podem ser complementados com a exportação nativa.
3. CSV de barras de 26/10 com timestamp, abertura, máxima, mínima e fechamento, cobrindo pelo menos 10:51 a 10:58.
4. PDF do relatório e captura da configuração do ativo, período, modo OHLC, parâmetros, quantidade, slippage, custos e execução nos limites.
5. Se o Backtest oferecer histórico nativo da mesma execução, exporte IDs, tipo, preço, quantidade, timestamps subminuto de criação, disparo, execução e cancelamento, e vínculo OCO quando existir. Uma lista proveniente de Replay separado deve vir identificada como tal.

## Regressões privadas e controles de lacuna

| Estratégia | Configuração | 21/10 | 26/10 |
|---|---|---:|---:|
| v5.7 | Padrão | 10/10 | 8/12 |
| v5.7 | Proteção legada | 10/10 | 11/12 |
| v5.7 | Avaliação pós-preenchimento, incluindo os dois modos pareados | 10/10 | 12/12 |
| v5.8 | Reinício em lacunas | 7/7 | 8/10 |
| v5.8 | Continuidade, com ou sem entrada através de lacuna | 7/7 | 9/10 |

Resultados idênticos com a nova opção desligada e ligada. A operação #182 da v5.7 corresponde por entrada, saída, lado, quantidade e preços nos três modos com avaliação pós-preenchimento. Em 26/10, com continuidade, as 62 solicitações comparadas da v5.8 continuam exatas. A saída das **10:15** permanece ambígua em OHLC. O Profit registra alvo de +400 pontos e o simulador stop de −350. A proteção persistente também não atravessou o gap no caso 2 da V3. O simulador cancelou duas pendências, manteve a exposição na retomada e saiu na limpeza às 09:42. O Profit saiu às 09:40. No caso 1, a compra atravessou a lacuna às 09:39 sem cancelamento e saiu às 09:42 nas duas configurações. [Matriz v5.7](regressao_v57.csv) · [Matriz v5.8](regressao_v58.csv) · [Controle da lacuna](controle_lacuna.csv)

Foram 32 replays v5.7/v5.8 em 16 cenários. Para cada cenário foram comparados dois pares, referência × desligado e desligado × ligado. `candles.csv`, `execucoes.csv`, `console.csv`, `eventos_ordens.csv` e `estrategia.ntsl` foram idênticos byte a byte nas **160 comparações**. As outras 64 comparações apontam somente a inclusão da flag em `metricas.json` e em `relatorio.html`, e a mudança do valor entre ligado e desligado. Removendo esse campo, o JSON e o HTML correspondem nos dois pares de cada cenário. [Comparação por arquivo](comparacao_artefatos.csv)

## Reprodução

Use os insumos privados da [rodada de referência](../WINZ26_v5_8_entrada_mercado_lacuna_20261026_v1/README.md#comandos-de-reprodução). A janela v5.7 usa o CSV preparado do respectivo pregão e `p_Lote=1`. A v5.8 usa o histórico preparado com o pregão anterior, o NTSL de auditoria do simulador, o JSON versionado (`p_Exec_Tick=0`, lote 5) e o corte de 63 barras por segmento no comparador. Os insumos estão verificados por hash, e a coleta de prioridade e S1 usa as barras preparadas de 26/10. Os originais, os relatórios HTML e as exportações inteiras dos replays ficam no Windows. [Inventário dos insumos](insumos_privados.csv)

```powershell
$base = @('--formato','ohlc','--segundos','60','--tick','5','--valor-ponto','0.2','--rastrear-ordens')
$paridade = @('--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas')
$extra = @('--avaliacao-pos-preenchimento')
$cont = @('--historico-continuo-lacunas')
$entrada = $cont + @('--entrada-mercado-atraves-lacuna')
$flag = @('--protecoes-ate-cancelar') # Repetir com $flag = @().
# v5.7: $modo = @(), @('--protecao-no-candle-entrada'), $extra, ($extra + $cont) ou ($extra + $entrada).
py -3.11 estrategia.py --csv $barrasV57 --ntsl $ntslV57 --inputs $jsonV57 --saida $saidaV57 @base @paridade @modo @flag
# v5.8: $modo = @(), $cont ou $entrada. $barrasV58 contém o pregão anterior.
py -3.11 estrategia.py --csv $barrasV58 --ntsl $auditoriaV58 --inputs $jsonV58 --saida $saidaV58 @base @paridade @extra @modo @flag
py -3.11 -m tools.comparar_v5_8 --data $dia --aquecimento 63 --barras-profit $barrasProfit `
  --operacoes-profit $operacoesProfit --console-profit $consoleProfit --barras-preparadas $barrasV58 `
  --candles-simulador "$saidaV58/candles.csv" --console-simulador "$saidaV58/console.csv" `
  --execucoes-simulador "$saidaV58/execucoes.csv" --saida "$saidaV58.comparacao.json"
# S1 e prioridade: na cópia de NTSL para o simulador, use (expr) no lugar de FloatToString(expr, 0)
# e remova o argumento de cor clYellow. Na sonda de prioridade passe o JSON de p_Perna e p_SaidaMercado.
py -3.11 estrategia.py --csv $barrasV57 --ntsl $sondaLocal --saida $saidaSonda @base @extra @flag
# V3: JSON do caso 1 ou 2.
py -3.11 estrategia.py --csv $barrasV57 --ntsl $sondaV3 --inputs $jsonCaso --saida $saidaV3 @base @extra @entrada @flag
py -3.11 -m tools.publicar_protecoes_ohlc --atuais $replays --referencia $referencia --referencia-s1 $referenciaS1 `
  --operacoes-v57 $operacoesV57 --saida $publicavel
py -3.11 -m pytest -q
```

O extrator lê uma pasta com saídas nomeadas `${dia}-v57-${modo}-${estado}`, `v58-${dia}-${modo}-${estado}`, `s1-${perna}-${estado}`, `prioridade-${p_Perna}-${p_SaidaMercado}` e `sonda-${caso}-entrada-${estado}`. O estado é `off` ou `on`; em S1, também `global` e `global-e-on`. Os modos estão nos CSVs. A execução com `--motor-ticks --protecoes-ate-cancelar` foi rejeitada pela CLI com código 2 antes de gravar os resultados.

A suíte passou com **108 testes**, incluindo 19 novos casos, e 12 avisos de timezone do pandas já conhecidos. [Fonte do extrator](../../../../tools/publicar_protecoes_ohlc.py) · [Testes](../../../../tests/test_protecoes_ohlc.py) · [Manifesto](SHA256SUMS.txt) · [Fontes para o Gemini](fontes_gemini.txt)
