# Evidências — ProfitRTD Etapa 1

Data da execução local: 2026-11-19. Esta rodada não executou otimização nem abriu a reserva de validação final. Nenhum CSV bruto foi copiado para o repositório.

## Revisões e ambiente Windows

| Item | Valor |
|---|---|
| Branch do PR | `research/piloto-ias-etapa1` |
| SHA remoto observado antes do trabalho | `b36fca62086bc7ad2a2e9e772cf47ae0d64740d3` |
| Baseline v0.14.0 | `b4c18d86aac2ce4ffc352957e56a29ce30fe63f1` |
| Versão declarada nos dois checkouts | `0.14.0` |
| Python | `3.11.3`, MSC v.1934 64 bit |
| Windows | `Windows 10.0.19045` |

Os SHAs foram reproduzidos em worktrees separados e em estado detached antes dos testes. A árvore local preexistente `research/etapa1-inventario-20261119`, com o commit local `024330b`, foi preservada sem alteração.

### Comandos relevantes

```powershell
git fetch origin main research/piloto-ias-etapa1
git worktree add --detach <worktree-baseline> b4c18d86aac2ce4ffc352957e56a29ce30fe63f1
git worktree add --detach <worktree-pr> b36fca62086bc7ad2a2e9e772cf47ae0d64740d3
py -3.11 -m pip install --target <deps-temporarias> -r requirements.txt pytest

$env:PYTHONPATH='<deps-temporarias>'
$env:PYTHONUTF8='1'
py -3.11 -m pytest -q

py -3.11 estrategia.py --csv exemplos\replay_minimo\candles.csv `
  --ntsl exemplos\replay_minimo\estrategia.ntsl --saida <saida-candle> `
  --segundos 5 --formato ohlc --tick 5

py -3.11 estrategia.py --csv dados\exemplos\negocios_sintetico.csv `
  --ntsl exemplos\replay_minimo\estrategia.ntsl --saida <saida-tick> `
  --segundos 5 --formato negocios --tick 5 --motor-ticks

py -3.11 -m pytest `
  tests\test_replay_ticks.py::test_entrada_saida_no_mesmo_candle_com_parciais -q
```

### Resultados reproduzidos

| Revisão | `pytest` | Candle sintético, 5 s | Negócios sintéticos, tick a tick |
|---|---:|---|---|
| baseline `b4c18d8` | 25 passaram; 12 avisos | 3 barras, 2 preenchimentos, 1 saída, −10 pontos, 1 barra ambígua | 2 eventos, `motor_execucao=tick_a_tick`, 2 preenchimentos |
| PR `b36fca6` | 25 passaram; 12 avisos | resultado idêntico ao baseline | resultado idêntico ao baseline |

Sem `PYTHONUTF8=1`, ambos os checkouts tiveram `24 passed, 1 failed`: `test_validacao_com_extremos_ambiguos_e_taxas` tentou ler um HTML UTF-8 usando o CP1252 padrão do Windows. As asserções funcionais anteriores à leitura passaram; a repetição controlada em UTF-8 passou integralmente. Os 12 avisos são `Pandas4Warning` no tratamento de timezone em `integrar_profitrtd.py:30` e `replay_ticks.py:30`.

O teste tick adicional com seis negócios também passou isoladamente nos dois SHAs (`1 passed, 1 warning`). Ele validou ordem por sequência em timestamps empatados, execução somente em evento posterior, limite pela quantidade negociada, preenchimentos parciais e fechamento da posição. O caso simples de dois negócios pela CLI validou a seleção efetiva do motor, a leitura do formato e a geração do relatório; seu segundo preenchimento foi uma **zeragem sintética de fim de pregão**, não uma saída normal da estratégia, e o caso não é evidência suficiente de paridade NTSL.

Depois da inclusão do inventariador, a suíte completa do PR passou com `26 passed, 12 warnings`.

## Inventário local preservado

A raiz local contém 25 arquivos brutos WIN, cinco fontes por pregão em 16/09, 28/09, 21/10, 26/10 e 04/11 de 2026. Não foi encontrado arquivo bruto WDO.

| Fonte | Arquivos | Bytes | GiB | Linhas brutas inventariadas | Conteúdo útil |
|---|---:|---:|---:|---:|---|
| Negócios | 5 | 1.499.958.395 | 1,397 | 12.402.324 | horário do negócio em ms, preço, quantidade, participantes e agressor |
| Preços | 5 | 8.399.111.989 | 7,822 | 90.856.510 | níveis de compra/venda e quantidades, sem relógio causal comum aos negócios |
| Ofertas | 5 | 7.170.893.136 | 6,678 | 62.509.696 | horários por lado, agente, quantidade e preço |
| VAP financeiro | 5 | 1.683.627.026 | 1,568 | 19.462.010 | distribuição agregada por preço |
| VAP quantidade | 5 | 2.325.388.400 | 2,166 | 27.685.010 | distribuição agregada por preço |

Preços WIN estão em pontos inteiros e, nos negócios aceitos, todos respeitaram grade de 5 pontos. Quantidade e volumes foram tratados como contratos. `Data_Pregao` identifica o pregão. `DataHora_PC` é o horário local de recuperação/gravação retrospectiva; não é o horário do evento de mercado.

### Cobertura de negócios WIN

A janela nominal usada foi 09:00:00–18:31:59, total de 572 minutos. Cobertura significa minutos com pelo menos um negócio aceito. O critério agregado e pré-declarado de elegibilidade foi: cobertura mínima de 95%, densidade mínima de 10% da mediana entre pregões, sequência contínua e preço na grade. Pregões aprovados ainda precisam ser segmentados nas lacunas.

| Pregão | Negócios | Contratos | Cobertura | Minutos ausentes | Empates: grupos / negócios | Maior lacuna | Elegível |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-09-16 | 8.939 | 12.304 | 89,69% | 59 | 1.222 / 3.876 | 392,763 s | não: baixa cobertura e densidade |
| 2026-09-28 | 7.298 | 13.220 | 85,49% | 83 | 933 / 3.080 | 472,164 s | não: baixa cobertura e densidade |
| 2026-10-21 | 4.296.230 | 14.879.339 | 98,43% | 9 | 511.830 / 2.933.377 | 388,614 s | sim, com segmentação nas lacunas |
| 2026-10-26 | 4.676.480 | 9.458.490 | 96,33% | 21 | 703.250 / 3.525.730 | 607,998 s | sim, com segmentação nas lacunas |
| 2026-11-04 | 3.413.362 | 12.546.155 | 81,29% | 107 | 411.040 / 2.352.056 | 4.500,037 s | não: captura fragmentada |

As duas capturas de setembro têm somente 14–17 negócios por minuto coberto, contra 7.341–8.487 nos três pregões densos. A presença simultânea dos arquivos grandes de Preços e Ofertas e essa separação de três ordens de grandeza sustentam a classificação “captura de Negócios incompleta ou amostrada”, não a conclusão de ausência real de negócios. Nos pregões densos, minutos inteiros sem eventos em WIN são tratados como provável falha de captura; os minutos antes do primeiro ou depois do último evento são discriminados como borda parcial na tabela diária.

Os agregados completos estão em:

- `docs/colaboracao/ETAPA1_COBERTURA_WIN_PREGOES.csv`
- `docs/colaboracao/ETAPA1_COBERTURA_WIN_FAIXAS.csv`

O inventariador incremental é `tools/inventariar_cobertura_win.py`. Seu registro de tamanho, mtime e resultados permaneceu fora do repositório. Uma segunda execução sem alteração das fontes reutilizou os cinco resultados (`0 processados; 5 reutilizados`). O teste sintético cobre contagem de negócios e contratos, empate no mesmo milissegundo, lacuna superior a cinco segundos, continuidade da sequência e escrita dos dois agregados.

## Sequência, empates e relação entre fontes

`Sequencia` é uma sequência local da captura/exportação: ela começa nas linhas de identificação e cabeçalho, cresce em cada linha física e é contínua mesmo quando o horário de negócio volta no tempo. Portanto, não é evidência de sequência da bolsa. As inversões temporais na ordem física foram 3.238, 2.356, 1.831.170, 1.821.813 e 1.445.545, respectivamente nos cinco pregões em ordem cronológica.

Para uma reprodução determinística, eventos são ordenados por horário e `Sequencia` é usado apenas como desempate local. Quando vários negócios compartilham o mesmo milissegundo, essa escolha não prova a ordem real de bolsa. A Etapa 2 deve registrar a incerteza e executar análise de sensibilidade para estratégias cujo resultado muda com a permutação desses empates.

Negócios têm horário de mercado completo. Ofertas têm horários separados por lado, enquanto Preços não carregam um timestamp de mercado por nível. `DataHora_PC` indica o lote de recuperação posterior; `SessaoCompartilhada` apenas relaciona a mesma sessão de extração. Assim, não existe ainda uma chave demonstrada para uma junção causal ponto-no-tempo entre negócio e snapshot completo do book. Os arquivos mostram profundidade histórica, mas não permitem afirmar cobertura temporal do book nem reconstruir fila ou estado completo em cada negócio.

## Escopo proposto para a Etapa 2

1. Começar somente pelos Negócios WIN dos pregões elegíveis, 21/10 e 26/10, dividindo o replay nas lacunas e mantendo 16/09, 28/09 e 04/11 fora do conjunto inicial.
2. Manter a junção causal com book histórico pendente até existir evidência temporal de snapshots. Não usar `DataHora_PC` para preencher o passado nem fazer `merge_asof` retrospectivo sem essa prova.
3. Manter WDO pendente até haver dados próprios; não extrapolar parâmetros nem liquidez do WIN.
4. Manter otimização e validação final reservadas. A reserva final não foi aberta nesta rodada.

### Paridade: avaliação por negócio versus histórico NTSL por candle

O motor tick atual avalia a estratégia em cada negócio e representa cada negócio como uma observação da série: `CurrentBar`, OHLC, referências `[n]`, `Media`, `Trades` e demais janelas avançam por negócio. No Profit, uma estratégia configurada tick a tick em gráfico de 1 s ou 5 s pode ser reavaliada em cada negócio, mas o histórico NTSL continua indexado por candle; vários negócios atualizam o mesmo candle antes de ele fechar.

Logo, “avaliar em cada negócio” e “manter histórico por candle” são dimensões diferentes. A evidência de paridade da Etapa 2 precisa comparar explicitamente: instante do sinal, estado do candle em formação, valores das referências `[n]`, indicadores acumulados, ordens geradas e preenchimentos. Até essa comparação existir, o modo tick valida mecânica de eventos e execução, mas não equivalência semântica completa com o Profit.

## Bloqueios restantes

- Falta uma sequência de bolsa para resolver empates no mesmo milissegundo.
- Falta timestamp causal de snapshot completo para Preços/Ofertas e cobertura verificável do book.
- WDO não tem dados locais próprios.
- A leitura do HTML no teste foi corrigida para UTF-8 explícito na Etapa 2A. No SHA funcional `c534b575a027bc196743391a9674b7a9ed8c824d`, a suíte passou sem `PYTHONUTF8=1`: `27 passed, 12 warnings`.
- Os avisos de timezone do pandas devem ser corrigidos antes de uma atualização maior da biblioteca.
- A paridade NTSL por candle versus avaliação por negócio ainda precisa de uma matriz de evidências na Etapa 2.
