# Diretrizes do projeto ProfitRTD

## Objetivo

Desenvolver e validar estratégias automatizadas para operações curtas no mini-índice, integrando preço, volume, agressão, negócios e livro de ofertas, com implementação final no Profit Ultra/NTSL.

## Regras de pesquisa

- Identificar tendência, aceleração, persistência, exaustão, absorção e condições em que não se deve operar.
- Definir entrada, invalidação, saída, tempo máximo, exposição e perda diária antes da avaliação financeira.
- Avaliar spread, liquidez, custos, slippage e quantidade negociada.
- Não aumentar lote automaticamente para recuperar perdas.
- Separar ajuste retrospectivo de teste cronológico posterior.
- Medir lucro líquido, drawdown, perda média, pior perda, concentração do resultado e estabilidade entre pregões.
- O melhor parâmetro histórico não é evidência suficiente de desempenho futuro.

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
