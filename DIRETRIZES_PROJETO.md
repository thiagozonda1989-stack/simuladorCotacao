# Diretrizes do projeto ProfitRTD

## Objetivo

Desenvolver o simulador, pesquisar e validar estratégias NTSL para o Profit Ultra e ampliar a coleta e o suporte a dados e indicadores. O trabalho começa no mini-índice (WIN) e inclui o minidólar (WDO) quando houver dados elegíveis.

## Três frentes do projeto

1. **Dados e indicadores.** Inventariar o que já existe no ProfitRTD e no catálogo antes de criar novos coletores. Para cada variável, registrar fonte, fórmula, unidade, granularidade, instante em que fica disponível, cobertura, lacunas e disponibilidade no Profit e no simulador. Começar por negócios WIN elegíveis e candidatos calculáveis desses dados: taxa de negócios, volume por segundo, retorno em janelas passadas e amplitude realizada. Agressão depende da qualidade do campo de lado. Spread, desequilíbrio do livro e absorção com book exigem captura sincronizada e validação causal. WDO depende de dados próprios.
2. **Simulador.** Reproduzir o baseline v0.14.0 no Windows e completar a cobertura do WIN antes de congelar a Etapa 2. Usar casos sintéticos para distinguir avaliação a cada negócio de histórico NTSL por candle e testar lacunas, empates, ordens e custos. Comparar com o Profit primeiro em estratégias por candle e comparar sinais, ordens e execuções separadamente. Integrar cada nova variável com schema versionado e teste contra informação futura, incluindo comportamento diante de dado ausente ou vencido.
3. **Estratégias Profit Ultra.** Projetar modelos separados de COMPRA/NÃO COMPRA e VENDA/NÃO VENDA. Para começar, selecionar um baseline de 1 min do catálogo após conferir dependências NTSL e evidência de replay. Depois avaliar 5 s, 1 s, 5 min e outros intervalos conforme cobertura e paridade. Registrar separadamente duração do candle, frequência de avaliação e horizonte de saída. Gerar código NTSL versionado e validar compilação e execução no Profit para cada versão e configuração.

## Critérios comuns para as estratégias

- Antes de ajustar parâmetros, definir os rótulos por direção, o horizonte, a regra de entrada e saída e o tratamento de casos ambíguos. Congelar a divisão cronológica e manter a reserva final local e intacta durante o desenvolvimento.
- Tratar 95% por classe como meta de pesquisa. Reportar matriz de confusão, precisão por classe, sensibilidade, tamanho da amostra, incerteza e operações por pregão. Medir falsos positivos e seu custo em reais separadamente, considerando custos, slippage e preenchimentos. Reportar também lucro líquido e drawdown.
- Começar com 1 contrato, saídas rápidas, tempo máximo de posição e limites de exposição e perda diária definidos antes do teste. Avaliar 2 ou 3 contratos em testes separados após validar o baseline de 1 contrato. Avaliar frequência de operações junto com resultado líquido e estabilidade entre pregões.

## Revisão e avanço por etapas

Fechar primeiro as pendências da Etapa 1 na Issue #1 e no PR #2. O trabalho preparatório em hipóteses e testes sintéticos pode avançar enquanto o Windows e a cobertura são verificados. A otimização depende de dados elegíveis, regras de rotulagem congeladas e evidência de que o motor representa a estratégia selecionada.

Em cada etapa, Codex reproduz as evidências locais e implementa testes, Claude revisa a semântica do replay e o NTSL, Gemini revisa qualidade dos dados, indicadores e avaliação estatística, e ChatGPT consolida requisitos, evidências e divergências. As quatro IAs registram parecer no mesmo SHA. Se houver divergência material, a Issue registra a evidência necessária para resolvê-la. Thiago decide o avanço após a revisão. Use o [fluxo de colaboração](docs/colaboracao/FLUXO_IAS.md).

## Regras de pesquisa

- Identificar tendência, aceleração, persistência, exaustão, absorção e condições em que não se deve operar.
- Definir entrada, invalidação, saída, tempo máximo, exposição e perda diária antes da avaliação financeira.
- Avaliar spread, liquidez, custos, slippage e quantidade negociada.
- Não aumentar lote automaticamente para recuperar perdas.
- Separar ajuste retrospectivo de teste cronológico posterior.
- Medir lucro líquido, drawdown, perda média, pior perda, concentração do resultado e estabilidade entre pregões.
- O melhor parâmetro histórico não é evidência suficiente de desempenho futuro.

## Publicação de dados e logs do Profit

Para cada captura nova usada em teste, diagnóstico ou revisão, publique no GitHub, no PR da etapa, os CSVs, logs e recortes compartilháveis, acompanhados de um README. Use uma pasta por captura em `docs/colaboracao/evidencias`, com ativo, data e versão no nome ou no README. Preserve a ordem original dos eventos e mantenha separados o rótulo da barra e o horário da execução.

O README registra origem, ativo, pregão, janela, fuso, granularidade, parâmetros do Profit, versão da estratégia, SHA do simulador, comandos, contagens, lacunas, duplicatas, transformações e SHA-256 dos arquivos publicados. Quando houver sanitização ou recorte, descreva o que foi removido e quais verificações dependem do original. Publique uma nova versão quando os dados ou parâmetros mudarem.

Remova identificação de conta, titular, credenciais e caminhos privados. Dados de mercado sujeitos a restrição de redistribuição e a reserva final permanecem fora do GitHub. Para essas fontes, publique os recortes permitidos ou agregados, o manifesto e, quando útil, um caso sintético reproduzível. Identifique no README os resultados cuja reprodução exige acesso ao original.

Antes de encaminhar a revisão, confira se os arquivos abrem no SHA publicado e use links fixos no PR. Se o ambiente de revisão estiver dessincronizado, importe os arquivos publicados como fontes. Cada parecer informa o SHA e o que efetivamente leu ou reproduziu.

## Versionamento

- Estratégias de execução ficam em `estrategias/execucao`.
- Indicadores e diagnósticos ficam em `estrategias/indicadores`.
- O nome deve conter a versão: `nome_vMAJOR_MINOR[_PATCH].ntsl`.
- Código confirmado no Profit não é sobrescrito. Uma modificação gera nova versão.
- `estrategias/manifesto_estrategias.json` registra SHA-256, tamanho e origem de cada cópia.
- `estrategias/catalogo_estrategias.csv` separa compilação no Profit de compatibilidade com o simulador.

## Níveis de evidência

1. `rascunho`: revisão estática apenas.
2. `compila_profit`: compilação confirmada no Profit.
3. `replay_profit`: executou em Replay/Backtest do Profit.
4. `simulado`: executou em conta de simulação.
5. `validado_fora_amostra`: resultado em pregões posteriores ao ajuste.

Nenhum nível implica autorização para conta real.

