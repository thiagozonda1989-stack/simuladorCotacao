# Fechamento da v5.8 e controles na retomada de lacuna

Motor executado em `0d2f19a47307d5390f5d89bb53d70e6c87a37856`. Head de evidências que fundamenta o fechamento `10ba1e979bebfe18a27e0322a47ee55092a265ab`. Os controles desta rodada usam esse motor. [Revisão Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7054792922) · [Revisão Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7054828827)

## Fechamento da amostra v5.8

| WINZ26, 1 minuto, com pregão anterior | Reinício | Continuidade histórica |
|---|---:|---:|
| 21/10/2026 | 7/7 | **7/7** |
| 26/10/2026 | 8/10 | **9/10** |

Com continuidade, coincidiram as 17 entradas, as 306 e 62 solicitações e as 509 e 472 avaliações comparáveis nos respectivos pregões. A paridade observada nas retomadas cobre **posição zerada e ausência de ordens pendentes**. O replay de 21/10 com histórico anterior não tem lacunas intradiárias. O de 26/10 tem a retomada às 09:39 e também uma no histórico de 23/10 às 17:55. As duas ficaram sem exposição e sem cancelamentos no replay. As duas políticas de continuidade são independentes. `--historico-continuo-lacunas` conserva janelas e referências históricas `[n]`. `--vwap-continuo-lacunas` controla o acumulador da VWAP e também foi usado nessa matriz. A sonda v2 já publicada mantém arrays e `estado[n]` como pendências gerais do motor. [Relatório da rodada fechada](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/README.md) · [Matriz v5.8](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/matriz_v5_8.csv)

## Controles de execução

As sondas se concentram em WINZ26, 26/10/2026, candles de 1 minuto. A barra rotulada **09:29** precede diretamente a **09:39**. O controle usa um contrato. O log nativo mostra rótulo de contexto, `CurrentBar`, sequência da sonda, posição e `HasPendingOrders` antes de cada ação. O log do simulador também distingue a barra física do replay, o rótulo de contexto NTSL e o tipo de avaliação.

| Caso | Condição que precisa existir antes da lacuna | O que observar na retomada |
|---|---|---|
| 1 · entrada pendente | A compra a mercado é solicitada em 09:29 com posição zerada. A ordem precisa permanecer pendente até a fronteira. | Preenchimento ou cancelamento da solicitação, posição e pendentes na primeira avaliação regular e eventual avaliação extra com posição alterada. |
| 2 · posição protegida | A compra é solicitada em 09:27. A sonda solicita alvo e stop em 09:28 e renova ambos em 09:29. A avaliação de 09:29 precisa ver a posição comprada e proteções já pendentes, ou o histórico de ordens precisa comprová-las antes da renovação. | Sobrevivência e execução das proteções, eventual cancelamento, posição e pendentes na primeira avaliação regular e eventual avaliação adicional por mudança de posição. |

No caso 2, alvo +100, gatilho −10.000 e limite −10.500 pontos são níveis deliberadamente escolhidos para isolar o stop. A abertura de 09:39 fica dentro da faixa do stop-limit e a máxima fica abaixo do alvo. O controle usa o mesmo perfil em uma série sintética com oito candles e no replay das barras privadas preparadas a partir do Profit. A sonda só volta a enviar uma ação às 09:41, quando solicita a zeragem ou o cancelamento de limpeza necessário para encerrar a execução. Essa limpeza fica fora da observação da primeira barra da retomada.

### Resultado no simulador

Os oito replays locais, quatro por fonte, produziram os mesmos estados em ambos os modos:

| Caso | Posição antes da lacuna | Ordens canceladas | Preenchimentos às 09:39 | Extra às 09:39 | Posição na avaliação regular às 09:39 | Pendentes na avaliação regular |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 1 | 0 | 0 | 0 | 0 |
| 2 | 1 | 2 | 0 | 0 | 1 | 0 |

No caso 2, a compra e a avaliação extra ocorreram normalmente na barra de replay das 09:28, com contexto NTSL das 09:27 na extra. Alvo e stop ficaram pendentes antes da avaliação regular de 09:29 e foram renovados. O motor atual cancela pendências na retomada e a extra de entrada a mercado tem uma guarda para lacunas. A hipótese do parecer Claude sobre a sobrevivência da ordem pendente e das proteções no Profit fica para validação nativa. Nenhuma regra do motor foi alterada. [Resumo dos oito replays](resumo_controles.csv) · [Rastreio em ordem de emissão](rastreio_simulador.csv)

## Execução manual no Profit

1. Compile o [NTSL pronto para o Profit](sonda_lacuna_profit_v1_0.ntsl) como estratégia de execução no Editor. Use **Backtest OHLC**, WINZ26, 1 minuto, 26/10/2026, posição inicial zerada, quantidade padrão e máxima 1, slippage e custos zero, execução nos limites e sem zeragem horária externa na janela. Rode o pregão com a janela efetiva contendo 09:27–09:43. [Backtest OHLC da Nelogica](https://ajuda.nelogica.com.br/hc/pt-br/articles/12742147789851-Backtest-OHLC)
2. Faça duas execuções independentes. Use `p_Caso=1` na primeira e `p_Caso=2` na segunda. Mantenha os outros valores padrão. Confira antes de interpretar os resultados que as barras 09:29 e 09:39 são consecutivas no histórico efetivamente usado, sem barras de 09:30 a 09:38. Se esse requisito ou a condição inicial da tabela falhar, registre o controle como inconclusivo.
3. Guarde estes arquivos privados por execução, com `X` igual a 1 ou 2. Preserve a ordem e os cabeçalhos das exportações.

| Arquivo | Conteúdo |
|---|---|
| `lacuna_caso_X_console.txt` | Todas as linhas `LACUNA;` do Debug de uma execução, 09:27–09:43. Inclui avaliações repetidas no mesmo rótulo, solicitações, posição e pendentes. |
| `lacuna_caso_X_barras.csv` | Ativo, data/hora, abertura, máxima, mínima e fechamento das barras do backtest no intervalo 09:27–09:43, com fuso registrado. |
| `lacuna_caso_X_operacoes.csv` | Exportação da aba Operações do mesmo backtest, com ID ou número da operação, lado, quantidade, preços e horários de abertura e fechamento. Preserve o relatório vazio se o caso 1 ficar sem operação. |
| `lacuna_caso_X_config.txt` ou captura | Versão/build do Profit, ativo, resolução, dia, modo de execução, intervalo efetivo, quantidade, custos, regras de risco e valores dos inputs. |
| `lacuna_caso_X_ordens.csv` | Se o backtest disponibilizar o histórico de ordens, exporte 09:27–09:43 com ID, vínculo OCO, tipo, lado, quantidades, preços de gatilho/limite, status, motivos de cancelamento e timestamps de solicitação, ativação, disparo, preenchimento e cancelamento. Preserve resolução e sequência nativas. |

O console identifica solicitações e estados observados. Conte avaliações adicionais na ordem em que aparecem e preserve o rótulo da barra, mesmo quando ele se repetir. Use o relatório de operações para localizar o minuto da execução e o histórico nativo para atribuir eventos de ciclo de ordem. Se houver apenas uma avaliação ou se o histórico não identificar as ordens do backtest, registre o que ficou indeterminado. A Lista de Ordens de contas conectadas é uma fonte distinta do backtest. [Lista de Ordens da Nelogica](https://ajuda.nelogica.com.br/hc/pt-br/articles/360047168931-Lista-de-Ordens)

## Saída das 10:15

Permanece **ambígua em OHLC**. Nos negócios capturados, a faixa do alvo apareceu às 10:15:12.283 e a do stop às 10:15:43.810. A captura contém 64,84% dos negócios de referência do minuto. O histórico nativo com IDs, vínculo OCO e timestamps subminuto do mesmo backtest da v5.8 continua ausente dos arquivos disponíveis. Caso apareça, associe a compra de cinco contratos e as duas ordens de proteção ao mesmo backtest e preserve os tempos de ativação, disparo, preenchimento e cancelamento. A política conservadora do simulador permanece em uso. [Toques observados](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/toques_10h15.csv) · [Cobertura do minuto](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/cobertura_negocios_10h15.csv)

## Reprodução e testes

Os controles locais usam o mesmo perfil de ordens nos dois modos. Para rodar, escolha o caso, as barras e um destino novo. Use a flag de continuidade apenas na segunda execução. O fixture é sintético. A reprodução sobre o recorte histórico exige as barras privadas preparadas de 26/10 usadas na rodada de paridade.

```powershell
$evid = 'docs/colaboracao/evidencias/WINZ26_v5_8_controles_lacuna_20261026_v1'
$caso = 1
$barras = "$evid/barras_sinteticas.csv"
$flags = @()  # na segunda execução, @('--historico-continuo-lacunas')
py -3.11 estrategia.py --csv $barras --formato ohlc --segundos 60 --tick 5 `
  --valor-ponto 0.2 --ntsl "$evid/sonda_lacuna_simulador_v1_0.ntsl" `
  --inputs "$evid/inputs_caso_$caso.json" --saida $destinoNovo `
  --avaliacao-pos-preenchimento --rastrear-ordens @flags
py -3.11 -m pytest -q
```

A suíte local passou com **75 testes** e 12 avisos de timezone do pandas já presentes. Os resultados de regressão da v5.7 e da v5.8 vêm das execuções verificadas do motor revisado. Os oito replays acima são novos. A rodada só acrescenta sondas, controles e documentação no PR em rascunho. O rastreio histórico publica rótulos, contagens e preços em pontos relativos. Os originais continuam no Windows. [Regressão v5.7 verificada](../WINZ26_v5_8_continuidade_intrabar_20261026_v1/regressao_v5_7.csv) · [Fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto](SHA256SUMS.txt)
