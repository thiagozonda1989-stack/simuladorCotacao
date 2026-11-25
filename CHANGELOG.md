# Histórico de versões

## Não publicado — pesquisa de paridade da Etapa 2A

- Adiciona rastreamento opt-in do ciclo de ordens OHLC em `eventos_ordens.csv`.
- Adiciona modo opt-in para avaliar somente alvo e stop novos no candle em que uma entrada a mercado foi preenchida na abertura, sem antecipar saídas a mercado, entradas limite/stop ou ordens antigas e sem alterar o comportamento padrão.
- Cobre com regressão a elegibilidade da proteção no candle da entrada e a regra stop-limit quando a proteção já estava ativa.
- Experimenta a avaliação pós-preenchimento na abertura com dados da barra anterior e avaliação regular após o processamento das proteções.
- Preserva as atribuições escalares da avaliação pós-preenchimento até o fechamento no modo experimental, mantendo isolados arrays e janelas móveis.
- Permite comparar indicadores com aquecimento contado a partir de cada reinício do replay.
- Acrescenta `--historico-continuo-lacunas` ao replay OHLC para preservar janelas e referências históricas, mantendo cancelamento de pendentes e registro de lacunas com exposição.
- Acrescenta `--entrada-mercado-atraves-lacuna` como opção experimental do replay OHLC para entradas elegíveis com posição zerada e histórico contínuo em lacunas.
- Acrescenta `--protecoes-ate-cancelar` como opção experimental no OHLC, com proteção limitada à posição aberta e zeragem a mercado prioritária na abertura.
- Experimenta `--ajuste-tick-saidas-venda` para alvos limite e gatilhos de stop de posições compradas no replay OHLC, com empate explícito e rastreio de preço solicitado e efetivo.
- Versiona um indicador de coleta para exportar OHLC, negócios, volume, agressão nativa e VWAP da reserva WINZ26 em um CSV.

## 0.14.0

- Replay, validação e otimização NTSL tick a tick por negócios, com desempate por sequência, latência em milissegundos e cancelamento em lacunas.
- Preenchimentos parciais limitados pela quantidade observada, timestamps de execução e identificação da zeragem sintética final.
- Testes de causalidade, empate, latência, execução intrabar, preenchimento parcial e stop-limit.

## 0.13.0

- Incorpora o catálogo publicado do ProfitRTD com seus 23 NTSL intactos.
- Cancela ordens e reinicia indicadores após lacunas intradiárias, com rastreio de posição exposta.
- Integra Negócios, Preços e Ofertas normalizados em ordem causal, com idade dos snapshots e manifesto.
- Adiciona latência em barras, CalcTime, métricas de estabilidade, processos para replay paralelo e walk-forward pela CLI.
- Inclui testes de lacuna, causalidade, stop-limit, posição parcial, reversão, integridade e matriz de paridade.

## 0.12.0

- Modo Validar modelo para estratégias parametrizadas com dados de entrada selecionáveis, indicadores e gráficos de performance.
- CSV de conferência por execução e demonstrativo simulado em PDF com balanço por pregão.

## 0.11.0

- Vigência de ordens por barra com renovação no fechamento, e histórico contínuo entre pregões no Replay NTSL. Os modos anteriores continuam disponíveis.
- Resto com o mesmo sinal em `mod` e `Mod()`, suporte a `VWAP`, `StdDevs` e `AgressionVolBalance`, e diagnóstico para modo tick a tick.
- Testes pytest com o exemplo de replay e GitHub Actions para push e pull request.

## 0.10.0

- Taxa configurável por contrato e lado, slippage adverso em ticks e métricas financeiras líquidas no Replay NTSL.
- Preenchimento conservador opcional para ordens limite passivas, com ultrapassagem de um tick.
- Diagnósticos específicos para arrays multidimensionais e parâmetros por referência. Documentação sobre fila e sequência intrabar.

## 0.9.0

- Histórico local com log JSONL, motivo de parada, indicadores e ZIP reutilizável de cada execução.
- Evolução por geração e avaliações individuais com parâmetros e métricas legíveis por ferramentas externas.
- Publicação opcional em pré-releases do GitHub, catálogo dos testes compartilhados e importação de pacotes.
- Logs de início e parada para os comandos CLI.

## 0.8.0

- Busca aleatória adaptativa com metas independentes de sensibilidade e especificidade e confirmação cronológica.
- Cadastro local de estratégias NTSL, com nome, observação, versões e carregamento no editor.

## 0.7.0

- Base local de cotações com importação de CSV, catálogo SQLite e recorte inclusivo por pregão.
- Finalização antecipada da busca genética com validação do melhor candidato disponível.
- Seleção pós-busca por critério e exportação de inputs JSON ou estratégia NTSL parametrizada.
- Taxas e contagens de verdadeiros positivos e negativos e resultado bruto em reais durante o replay NTSL.


## 0.6.0

- Sessão portátil em um único arquivo ZIP com o CSV, o código NTSL, a configuração e o progresso da execução.
- Salvamento manual durante a execução ou pausa e salvamento automático em intervalo configurável.
- Retomada do replay pela próxima barra e da otimização pelos candidatos pendentes. A sessão anterior é preservada se a próxima gravação falhar.

## 0.5.3

- Pausa, retomada e cancelamento cooperativos no replay e na otimização.
- Reuso em RAM das séries e do histórico entre candidatos NTSL no modo máximo.
- Cache do Ensemble dimensionado pela RAM disponível após a reserva do sistema e dos trabalhadores.

## 0.5.2

- Progresso durante cada geração com métricas e parâmetros do melhor candidato até o momento.
- Indicadores de preparação, validação e geração do relatório e progresso por barras no replay direto.

## 0.5.1

- Envio local de CSV em blocos de 4 MiB, com progresso e retomada de blocos em caso de falha transitória.
- A interface diferencia erros de envio, execução e consulta do andamento.

## 0.5.0

- Modo de recursos máximos com dimensionamento automático por CPU, RAM e população.
- Replay NTSL em processos isolados, com reuso da estratégia compilada e progresso preservado.

## 0.4.0

- Busca genética por execução NTSL com faixas para todos os inputs, incluindo listas booleanas e de texto, e objetivos de resultado e drawdown.
- Linguagem ampliada com laços, arrays, rotinas escalares, funções matemáticas e de volatilidade, SendOrder e ReversePosition.
- Relatórios com P&L e drawdown, exportação dos inputs e manutenção do classificador de abertura anterior.

## 0.3.0

- Tabela de inputs NTSL com seleção e faixas sugeridas.
- Alvos de classe, direção no fechamento de N barras e toque de pontos dentro de N barras.
- Seleção de colunas excluídas e filtro de árvores dependentes.
- Gráficos de busca ao vivo e no relatório e curva de resultado do replay.

## 0.2.1

- Detecção automática de CSV do Profit, negócios ou candles OHLC pelo cabeçalho.
- Mensagens orientam a corrigir o formato quando a seleção manual é incompatível.

## 0.2.0

- Aplicativo portátil Windows x64 com dois executáveis, interface local no navegador e CLI.
- Entrada por arquivo NTSL ou colagem de código e seleção de CSV.
- Compilador para um subconjunto do NTSL, com variáveis por barra, médias e simulação de ordens.
- Replay com ordens elegíveis na barra seguinte, relatório de preenchimentos e marcação de ambiguidades OHLC.
- Interface para executar o otimizador de classificação do ensemble existente.
- Código-fonte, runtime, dependências fixadas, build e exemplos incluídos.

## 0.1

- Reconstrução de candles de negócios e ordenação de candles do indicador Profit.
- Leitura das 150 árvores do ensemble, otimização genética paralela e avaliação cronológica.
- Exportação de relatórios de classificação e do NTSL com a parametrização selecionada.
