# Histórico de versões

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
