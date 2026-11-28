# G1 e G2 no Profit Backtest OHLC · WINZ26

Execuções nativas de **26/10/2026**, WINZ26, 1 minuto, fuso America/Sao_Paulo. Protocolo `d5b21f3c74749ce28058c58277ce9f7f4e124c96` e motor de comparação `d67a8731bfa1597b0bdfe4cc4064e6502822f81a`. [Protocolo e hipóteses](../WINZ26_grade_precos_g1_g2_20261026_v1/README.md)

**As duas proteções preencheram às 10:55 no extremo da barra, depois de permanecerem pendentes às 10:53 e 10:54.** Os níveis brutos de G1 e G2 estavam fora da faixa. No simulador, os mesmos parâmetros brutos resultaram em saída de limpeza às 10:58. Os controles com níveis na grade reproduziram os dois resultados nativos. [Matriz Profit × simulador](matriz_profit_simulador.csv)

| Sonda | Preços solicitados (pts desde a compra) | Extremo de 10:55 (pts) | Venda Profit | Resultado líquido | Replay com preços brutos |
|---|---|---:|---:|---:|---|
| G1 | Limite +447 | Máxima +445 | 10:55:00, +445 pts | R$ 89,00 | 10:58:00, −375 pts |
| G2 | Gatilho −877, limite −1000 | Mínima −875 | 10:55:00, −875 pts | −R$ 175,00 | 10:58:00, −375 pts |

## Parâmetros e fontes

Os dois prints exibem o seletor **OHLC/Tick a Tick**, com **OHLC** selecionado. A aba Backtest está ativa e o código aparece compilado no Profit Ultra 5.0.4.33. O painel registra WINZ26, período de 1 minuto, análise de 26/10 a 26/10/2026, quantidade e máxima 1, slippage 0 ticks e “Executar nos Limites” ativo. Os parâmetros comuns são `p_Data=1261026`, `p_Entrada=1051`, `p_Protecao=1052`, `p_Cancela=1056`, `p_Zera=1057`, `p_Fim=1058`. G1 mostra `p_Alvo=447`; G2 mostra `p_Gatilho=877` e `p_Limite=1000`. Os PDFs confirmam uma operação e custo zero em cada sonda, em concordância com os CSVs. [Inventário e SHA-256 dos oito anexos](inventario_anexos.csv)

Cada console contém dois blocos completos idênticos, sem avisos. O derivado conserva o primeiro bloco em ordem física com 11 eventos por sonda. Os dois registros do rótulo 10:51 correspondem a avaliações da mesma barra, sequências 1 e 2. A compra é solicitada na sequência 1, e a sequência 2 já mostra posição +1. A entrada de um contrato está registrada no CSV às **10:52:00**. A proteção é solicitada uma vez na avaliação 3, rótulo 10:52. As avaliações 4 e 5 (10:53 e 10:54) mostram posição +1 e pendência 1. A avaliação 6 (10:55) já mostra posição 0 e pendência 0. A venda de um contrato está registrada no CSV às **10:55:00**, com posição e pendências zeradas até 10:58 e sem solicitação de limpeza. [Console derivado](console_profit.csv)

A janela tem oito barras consecutivas de 10:51 a 10:58. Os 32 valores OHLC dos dois consoles coincidem com as exportações locais anteriores do Profit e a série preparada usada no simulador. A barra de 10:55 tem abertura +220, máxima +445, mínima −875 e fechamento −260 pontos. As máximas e mínimas de 10:52–10:54 ficam fora dos níveis em disputa. O lote recebido não traz um CSV de barras da própria execução. [Barras relativas](barras_referencia.csv) · [Hashes das fontes de barras](fontes_barras.csv)

## Interpretação e limite da evidência

G1 vendeu **2 pontos abaixo** do limite solicitado, no preço da máxima de 10:55. G2 vendeu **2 pontos acima** do gatilho solicitado, no preço da mínima. Os resultados demonstram comportamento efetivo de ajuste à grade de 5 pontos na execução dessas duas proteções. Os níveis brutos preservados e o ajuste para longe do mercado (+450 e −880) ficariam fora da faixa de 10:55. O ajuste direcional em direção ao mercado também produziria +445 e −875 nesta janela. Nos controles nativos anteriores, +428 e −793 resultaram em +430 e −795, respectivamente, na direção oposta. Em conjunto, as quatro observações sustentam o **tick mais próximo para as saídas de venda testadas**. [Controles nativos anteriores](../WINZ26_v5_8_prioridade_protecao_profit_20261026_v1/matriz_profit_simulador.csv)

A ordem de eventos subminuto, o preço aceito no cadastro da ordem e o momento interno da normalização exigem histórico nativo. A G2 usou limite −1000, que já estava na grade e ficou fora da faixa da barra. A rodada separada com limite −894 e exportação do limite aceito fica pendente. O escopo observado cobre essas duas saídas de venda em posição comprada com “Executar nos Limites” ativo. A regra para ordens de compra, outros tipos de ordens e o arredondamento do preço limite do stop-limit seguem em aberto.

## Reprodução e publicação

O motor foi preservado. Foram reexecutados quatro controles, usando o NTSL do protocolo e a série privada `WINZ26_20261026_profit_1min_privado.csv`. O perfil bruto usa os parâmetros do painel. O perfil na grade aplica diretamente +445 ou −875 no NTSL, com o limite −1000 preservado na G2. Não há ajuste de grade novo no simulador. Use destinos separados com os nomes `g1-bruto`, `g1-mais-proximo`, `g2-bruto` e `g2-mais-proximo`.

```powershell
$fonte = [IO.File]::ReadAllText($arquivoNtslProfit)
$fonte = $fonte -creplace 'FloatToString\((\w+), 0\)', '($1)' -creplace ', clYellow\);', ');'
[IO.File]::WriteAllText($arquivoNtslLocal, $fonte)
# G1: p_Alvo=447 ou 445. G2: p_Gatilho=877 ou 875, p_Limite=1000.
py -3.11 estrategia.py --csv $barrasPreparadas --ntsl $arquivoNtslLocal --inputs $inputs `
  --saida $saidaPerfil --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --avaliacao-pos-preenchimento --rastrear-ordens --protecoes-ate-cancelar
# O extrator usa PyMuPDF para conciliar os relatórios.
py -3.11 -m tools.publicar_grade_g1_g2_profit --originais $originais --barras $barrasPreparadas `
  --protocolo $pastaProtocolo --replays $pastaReplays --saida $saidaPublicavel
py -3.11 -m pytest -q
```

Todos os 108 testes locais passaram, com 12 avisos de fuso do pandas já conhecidos. Os originais e as cotações absolutas ficam no Windows. [Manifesto dos derivados](SHA256SUMS.txt) · [Fontes para o Gemini](fontes_gemini.txt)
