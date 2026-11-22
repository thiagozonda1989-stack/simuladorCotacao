# S1 com uma proteção e toque na terceira barra elegível

## Aceitação da opção experimental

`--entrada-mercado-atraves-lacuna` fica **aceita como experimental** no replay OHLC. A opção é desativada por padrão e exige `--historico-continuo-lacunas`. A evidência cobre entradas a mercado elegíveis com posição zerada. O caso 1 da V3 reproduziu a solicitação no contexto 09:29, o preenchimento às 09:39, a avaliação extra em contexto 09:29 e a saída às 09:42, com +125 pontos. **O caso 2, com posição aberta e proteções pendentes na lacuna, permanece fora da paridade demonstrada.** [Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7071858509) · [Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7071942061) · [Matriz da opção](../WINZ26_v5_8_entrada_mercado_lacuna_20261026_v1/controles_v3.csv)

- Motor executado e revisado `142dbe882ae2a0436c4273a6e5bfa1268222e5d3`.
- Evidências da opção `5166699dabb51b787db977fbc8028d8e2474437a`.
- Evidências S1/S2 e base desta rodada `a1f693e8c73e4fce272d2c8b213a743b568a5f32`.

## Configuração das duas sondas

Use **Profit Backtest OHLC**, WINZ26, barras de 1 minuto, pregão de **26/10/2026**, fuso America/Sao_Paulo, um contrato, quantidade máxima um, slippage e custos zero e **Executar nos Limites** ativo. Comece cada execução com posição zerada e sem ordens. Mantenha a janela de teste sem filtros de horário ou zeragem externa entre 10:51 e 10:58. Compile cada NTSL como estratégia de execução e rode separadamente com os parâmetros padrão. A compilação e a execução nativas desta rodada estão pendentes.

| Parâmetro | S1-Alvo | S1-Stop |
|---|---:|---:|
| `p_Data` | 1261026 | 1261026 |
| `p_Entrada` | 1051 | 1051 |
| `p_Protecao` (t) | 1052 | 1052 |
| `p_Cancela` | 1056 | 1056 |
| `p_Zera` | 1057 | 1057 |
| `p_Fim` | 1058 | 1058 |
| `p_Distancia`, pontos | 430 acima da entrada | 795 abaixo da entrada |
| `p_Folga`, pontos | — | 100 abaixo do gatilho |

A compra é solicitada no contexto 10:51. Em 10:52 (t), com a posição comprada, **S1-Alvo** solicita somente `SellToCoverLimit` a +430 pontos. **S1-Stop** solicita somente `SellToCoverStop`, com gatilho a −795 pontos e limite a −895. Cada proteção é enviada uma única vez. O cancelamento de limpeza, se ainda houver pendências, é solicitado às 10:56. Se a posição continuar aberta, a zeragem a mercado é solicitada às 10:57. A janela de log termina às 10:58. [NTSL S1-Alvo](sonda_s1_alvo_toque_tardio_profit_v1_0.ntsl) · [NTSL S1-Stop](sonda_s1_stop_toque_tardio_profit_v1_0.ntsl) · [Lista de exportações](exportacoes_profit.md)

### Geometria conferida das barras

A janela de 10:51–10:58 tem oito barras consecutivas. Os quatro campos OHLC coincidiram nas oito barras entre a exportação privada do Profit da v5.8 e as barras preparadas do replay. Os valores abaixo estão em pontos relativos à abertura de 10:52, preço de entrada no simulador. Confirme a geometria com as **barras e o preço de entrada das novas execuções do Profit** antes de classificar o resultado.

| Barra | Abertura | Máxima | Mínima | Fechamento |
|---|---:|---:|---:|---:|
| 10:52 · t | 0 | +175 | −425 | −290 |
| 10:53 · t+1 | −285 | +225 | −355 | +35 |
| 10:54 · t+2 | +35 | +405 | −85 | +220 |
| 10:55 · t+3 | +220 | +445 | −875 | −260 |
| 10:56 · t+4 | −260 | −70 | −705 | −90 |

A máxima de 10:55 excede o alvo em 15 pontos. A abertura fica abaixo do alvo, acima do gatilho do stop e coincide com o fechamento anterior. A mínima de 10:55 passa 80 pontos abaixo do gatilho e fica 20 pontos acima do limite do stop. Nenhuma barra anterior desde o envio toca a respectiva proteção. Às 10:56, os dois níveis voltam a ficar fora da faixa, o que permite observar eventual pendência antes da limpeza. Cada execução tem uma única proteção. [OHLC relativo completo](barras_relativas.csv) · [Insumos e hashes](insumos_privados.csv)

## Matriz Profit × simulador

| Proteção | Motor/modo | Pendências em t+1 / t+2 / t+3 | Preenchimento da proteção | Saída de limpeza | Classificação |
|---|---|---|---|---|---|
| Alvo | Profit OHLC | A coletar | A coletar | A coletar | Aguarda execução manual |
| Alvo | Simulador padrão | 1 / 0 / 0 | — | 10:58, −375 pontos | Expirada após 10:53 |
| Alvo | Simulador diagnóstico | 1 / 1 / 0 | 10:55, +430 pontos | — | Preenchida após espera |
| Stop | Profit OHLC | A coletar | A coletar | A coletar | Aguarda execução manual |
| Stop | Simulador padrão | 1 / 0 / 0 | — | 10:58, −375 pontos | Expirada após 10:53 |
| Stop | Simulador diagnóstico | 1 / 1 / 0 | 10:55, −795 pontos | — | Preenchida após espera |

O diagnóstico usa a flag existente `--no-ordem-so-proxima-barra` para confirmar que a geometria permite o preenchimento em t+3 quando a ordem se mantém ativa. Essa flag afeta a validade das ordens em geral. O padrão continua `ordem_so_proxima_barra=True`. Com a regra padrão, a ordem é vista em 10:53 e removida ao final dessa barra sem renovação. Nos quatro replays, a compra de 1 contrato ocorreu na abertura das 10:52. O histórico registra contexto NTSL e horário do preenchimento em campos distintos. A leitura de `HasPendingOrders` acontece no início da avaliação, após o processamento de ordens da barra pelo simulador. [Matriz CSV](matriz_profit_simulador.csv) · [Estados por avaliação](estados_simulador.csv) · [Solicitações e preenchimentos](eventos_simulador.csv)

### Classificação da captura nativa

Classifique **cada perna separadamente**, após conferir a janela e a solicitação única.

- **Preenchida após espera.** O CSV atribui a saída à proteção em 10:55 (t+3), antes da limpeza, com posição zerada na avaliação correspondente ou evidência nativa equivalente.
- **Pendente sem preenchimento observado.** A única proteção ainda aparece como pendente em 10:55 ou 10:56, com posição aberta e sem saída da proteção antes da limpeza.
- **Expirada.** O simulador permite confirmar pela própria regra. No Profit, use o estado nativo de expiração. Se a pendência sumir sem preenchimento ou cancelamento solicitado, registre a hora da primeira avaliação sem pendência e mantenha o motivo indeterminado até obter o evento nativo.

Use o log, o CSV de operações e o histórico nativo para confirmar a transição. Preserve diferenças de horário, preço ou estado antes de considerar uma opção específica de persistência de proteções. O caso 2 da lacuna (saída 09:40 no Profit e 09:42 no simulador) e a saída de 10:15, ambígua em OHLC, permanecem investigações separadas. Os resultados da S1 anterior confirmam presença de pelo menos uma pendência, e os da S2 cobrem abertura além do gatilho em barras consecutivas. [S1/S2 anteriores](../WINZ26_v5_8_sondas_s1_s2_profit_20261026_v1/README.md) · [Caso 2 da V3](../WINZ26_v5_8_sonda_profit_20261026_v3_teste2/README.md#caso-2) · [Ambiguidade às 10:15](../WINZ26_v5_8_entrada_mercado_lacuna_20261026_v1/README.md#regressões-e-testes)

## Reprodução no simulador

A cópia local do NTSL substitui `FloatToString(expr, 0)` por `(expr)` e remove o argumento de cor `clYellow` das chamadas a `ConsoleLog`. Use o CSV privado preparado de 26/10. Execute com destinos distintos para alvo e stop.

```powershell
# Para o diagnóstico de seleção da janela, use $flags = @('--no-ordem-so-proxima-barra').
$flags = @()
py -3.11 estrategia.py --csv $barrasPreparadas --ntsl $sondaLocal --saida $pastaReplay `
  --formato ohlc --segundos 60 --tick 5 --valor-ponto 0.2 `
  --avaliacao-pos-preenchimento --rastrear-ordens @flags
py -3.11 -m pytest -q
```

Os quatro replays locais foram executados e os **89 testes** passaram, com 12 avisos de timezone do pandas já conhecidos. O motor e a validade padrão foram preservados. Os originais privados seguem no Windows. [Fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto](SHA256SUMS.txt)
