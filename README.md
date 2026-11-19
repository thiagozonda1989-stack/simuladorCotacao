# simuladorCotacao 0.12.0

[Histórico de alterações](CHANGELOG.md) · [Manutenção e hashes dos pacotes](MANUTENCAO.md)


## Salvar e retomar uma execução

- Antes de iniciar, configure **Salvar sessão a cada N minutos**. Use `0` para desativar o salvamento automático.
- Durante a execução ou a pausa, clique em **Salvar sessão** e aguarde a confirmação. Use **Baixar última sessão salva** para copiar o arquivo antes de cancelar ou fechar o programa.
- O simulador também grava automaticamente a última sessão no subdiretório `sessoes` da pasta de saída do aplicativo. Cada execução tem seu próprio `.sessao.zip`.
- Em outra execução do aplicativo, clique em **Carregar sessão** e escolha o ZIP completo. O arquivo da sessão já contém o CSV e o código NTSL.
- No replay, a retomada começa na barra seguinte à salva. Na otimização, candidatos com resultados já gravados são reaproveitados. Avaliações em andamento e a validação final podem ser refeitas. O ZIP inclui os dados originais e deve ser tratado como o CSV de origem.

## Abrir no Windows

1. Extraia **todo o ZIP** para uma pasta gravável.
2. Execute **SimuladorCotacao.exe**. A interface abre no navegador padrão, em endereço local da própria máquina. O runtime acompanha o programa.
3. Selecione o CSV, mantenha a detecção automática de formato, informe o intervalo e carregue um arquivo NTSL ou cole o código do Profit.
4. Use **Replay da estratégia** e clique em **Executar**. Use **Abrir relatório** quando terminar.
5. Use **Encerrar aplicativo** para fechar o processo local. Os arquivos de saída ficam em `%USERPROFILE%\simuladorCotacao\resultados`.

Para testar a instalação com dados pequenos, selecione `exemplos/replay_minimo/candles.csv`, formato **Candles OHLC com timestamp**, e o `estrategia.ntsl` da mesma pasta. Com os valores padrão, o relatório deve mostrar dois preenchimentos e uma barra ambígua.

O campo **Substituição de inputs (JSON)** pode permanecer como `{}`. Por exemplo, `{"p_Lote": 2}` substitui um input do código. Os nomes de inputs são comparados sem distinção entre maiúsculas e minúsculas. O incremento de preço alimenta `MinPriceIncrement`. O **valor por ponto e contrato** converte pontos em reais. Com taxas configuradas, `DailyResult` devolve o resultado após os custos já cobrados no pregão. Configure esse valor para que os limites da estratégia usem a unidade desejada.

## Formatos do CSV

| Formato | Campos | Comportamento |
|---|---|---|
| Indicador exportado do Profit | `data_minuto_origem;v_barra_id;abertura;maxima;minima;fechamento` e campos adicionais conforme a estratégia | Ordena por minuto e identificador. Use 1 s para v6 e 5 s para v7. |
| Negócios | `timestamp;preco`, com `quantidade` e `sequencia` opcionais | Reconstrói OHLC por intervalo, conta negócios e soma quantidade quando disponível. |
| Candles OHLC | `timestamp;abertura;maxima;minima;fechamento` | Ordena o timestamp ISO 8601 de cada candle, com uma linha por timestamp. |

O separador é ponto e vírgula. Preços inteiros e decimais com vírgula são aceitos. Nos formatos com `timestamp`, use data e hora ISO 8601, por exemplo `2026-11-16T09:15:00.100`. A exportação v6/v7 registra a hora até o minuto. A saída preserva a ordem dentro do minuto sem atribuir segundos exatos.

### Colunas adicionais

| Recursos NTSL | CSV |
|---|---|
| `Trades`, `Volume`, `Quantity` | `v_trades_atual`, `volume`, `volume_contratos` |
| `AgressionVolBuy`, `AgressionVolSell` | `v_agressao_compra`, `v_agressao_venda` |
| `BidPrice`, `AskPrice`, `BidSize`, `AskSize` | `v_bid`, `v_ask`, `v_qtd_bid`, `v_qtd_ask` |
| `TotalBuyQtd`, `TotalSellQtd` | `v_qtd_compra_book`, `v_qtd_venda_book` |

Estratégias que dependem de alguma dessas séries exigem a respectiva coluna. No formato negócios, `Trades` é calculado e `Quantity` fica disponível quando há quantidade por negócio. O OHLC de negócios por si só deixa book e agressão indisponíveis.

## Módulo NTSL

Compila `input`, `const`, `var`, `begin/end`, `if/then/else`, `for to/downto`, `while`, `repeat until`, arrays estáticos escalares, funções e procedimentos definidos no código, atribuições e operadores aritméticos, relacionais e booleanos. Aceita referências históricas com `[n]`, OHLC, horário, posição, médias simples e exponenciais, máximas e mínimas de janela, soma móvel e funções matemáticas, incluindo `Mod`. A biblioteca inclui `TrueRange`, `AvgTrueRange` e acesso histórico em funções puras suportadas. Implementa entradas e saídas a mercado, limite e stop, `SendOrder` com constantes simbólicas, `ReversePosition`, cancelamento, zeragem, `Plot`, `PaintBar` e `ConsoleLog`. O arquivo `exemplo_cruzamento.ntsl` demonstra uma estratégia simples. A estratégia do pacote pode ser carregada pelo botão na tela.

- Rotinas aceitam parâmetros escalares por valor, variáveis locais escalares e retorno via `Result`. Histórico de séries locais em rotinas, múltiplos ativos, parâmetros por referência, arrays multidimensionais e o catálogo integral de indicadores permanecem fora do subconjunto. Identificadores incompatíveis geram erro com a linha do código. Laços compartilham um limite de 100 mil iterações por barra.
- A declaração `Asset(GetAsset, ...)` é reconhecida pelo compilador. As funções de book leem as colunas exportadas do CSV, como `v_bid`, `v_ask`, `v_qtd_compra_book` e `v_qtd_venda_book`. O replay usa os agregados fornecidos, sem reconstruir a profundidade ou carregar séries independentes por ativo e intervalo.
- No Replay NTSL, médias e referências históricas usam candles disponíveis de pregões anteriores por padrão, enquanto o saldo diário e as ordens encerram no pregão. Referências anteriores ao primeiro candle retornam zero para dados de mercado e o valor padrão para variáveis. Desmarque **Carregar histórico de candles entre pregões** para reproduzir o comportamento anterior. Nesse modo, implemente o aquecimento por pregão no código se necessário, pois `CurrentBar` conta desde o início da série.
- `Date` e `Time` usam a data do candle e a hora HHMM. O intervalo da interface organiza os dados e fica registrado no relatório. Altere explicitamente os inputs temporais do seu código quando forem diferentes do intervalo analisado.

## Preenchimentos e limitações do replay

O código é avaliado uma vez, no **fechamento**. Ordens emitidas no fechamento podem executar a partir da próxima barra disponível. Ordens a mercado usam a abertura seguinte. Limites e stops usam os extremos da barra com ajuste de gap. Por padrão, limites e stops não executados expiram no fim da barra seguinte ao envio, salvo se reenviados ou editados naquele fechamento. Desmarque **Expirar ordens** para manter a ordem até execução, cancelamento ou fim do pregão.

Se alvo e stop forem tocados na mesma barra, o relatório registra ambiguidade e aplica o preenchimento menos favorável entre as saídas tocadas. Uma ordem a mercado já pendente tem prioridade na abertura. O replay mantém uma posição líquida, substitui ordens pendentes da mesma função e limita saídas ao saldo da posição. Ao fim de cada pregão, cancela ordens pendentes e encerra a posição restante no último fechamento disponível.

O simulador usa hipóteses de preenchimento por OHLC, sem reconstruir posição na fila, latência ou a sequência intrabar. O código roda uma vez por candle, no fechamento. Ordens de saída geradas após a entrada ficam elegíveis na barra seguinte. As novas funções de ordens usam essas regras locais. A caixa de ferramentas foi conferida com o [manual NTSL da Nelogica](https://www.nelogica.com.br/manualntsl). A estratégia das 150 árvores pode ser analisada pelo classificador na abertura via modo **Otimização genética**, ou executada no fechamento via **Replay da estratégia**. Os dois modos têm unidades de avaliação e regras de execução próprias.

### Relatórios

- `relatorio.html` e `metricas.json` resumem preenchimentos, saídas, pontos × contratos, drawdown realizado, inputs, hash do código e ambiguidades.
- `execucoes.csv` lista preenchimentos. `candles.csv` contém OHLC, intenções de entrada, posição, pontos acumulados e chamadas de plot.
- `console.csv` contém as primeiras 10 mil mensagens de `ConsoleLog`.
- `estrategia.ntsl` guarda o código efetivamente executado. Os inputs aplicados ficam em `metricas.json`.

## Otimizador genético

Em **Otimização genética**, o motor padrão da interface é **Replay NTSL**. Todos os inputs reconhecidos do código podem receber mínimo, máximo e passo ou uma lista de valores. Cada candidato roda a estratégia com seus valores. A busca pelo objetivo financeiro usa as próprias ordens, incluindo alvo, stop, quantidade e filtros configurados no NTSL. Entradas sem uso no código podem ser selecionadas e naturalmente produzem o mesmo resultado.

- **Resultado** maximiza o saldo após taxas em pontos × contratos. **Resultado menos drawdown** subtrai a maior queda da curva líquida acumulada por barra. Ambos independem da coluna `classe`.
- **F1, precisão, recall e acurácia** usam o alvo escolhido, considerando preenchimentos de entrada a mercado na abertura da barra. Para ordens limite e stop, use o objetivo operacional para avaliar seus preenchimentos.
- O modo **Ensemble · avaliação na abertura** mantém a otimização anterior, específica para as features das árvores. Nele, somente os genes do classificador entram na busca. Configurações antigas de CLI sem `motor` continuam usando esse modo.
- Para usar o replay na CLI, acrescente `"motor": "ntsl"` ao JSON. Use `"valores": [false, true]` para booleanos e uma lista de textos para entradas de texto. As melhores entradas são gravadas em `inputs_otimizados.json`, pronto para carregar no replay.

Um exemplo sintético com laços, funções, `SendOrder` e três inputs configuráveis está em `exemplos/otimizacao_ntsl`.

### Usar recursos máximos

Ative **Usar recursos máximos** na tela de otimização genética ou defina `"recursos_maximos": true` no JSON. O simulador mede os núcleos lógicos disponíveis ao processo e a RAM livre no início da busca. A população e a estimativa de memória por trabalhador limitam o paralelismo. A reserva para o sistema é de pelo menos 512 MiB ou 20% da RAM que estava disponível, o que for maior.

No **Replay NTSL**, candidatos são avaliados em processos separados. Cada processo recebe os candles e compila a estratégia uma vez, enviando apenas métricas ao processo principal. No **Ensemble**, o programa continua usando threads para compartilhar a base em memória. A opção substitui os valores manuais de `threads` e `cache_ram_mb` durante a execução. Desmarcada, a configuração anterior segue aplicável.

A interface mostra o limite de trabalhadores selecionado e o relatório registra núcleos, RAM disponível, estimativa por trabalhador e modo de paralelismo. O uso pode cair quando há poucos candidatos, na geração do relatório ou quando o Ensemble compartilha o mesmo cálculo entre vários candidatos.

### Alvos e acompanhamento

| Alvo | Regra |
|---|---|
| Classe do CSV | Valor exato da coluna `classe` na barra de previsão |
| Direção após N barras | Compara o fechamento da N-ésima barra com a abertura da barra de previsão. Compra exige valorização e venda exige queda |
| Toque de pontos em N barras | Compra exige máxima pelo menos X pontos acima da abertura. Venda exige mínima pelo menos X pontos abaixo |

A contagem inclui a barra em cuja abertura o sinal é emitido. Mesmo em velas de 1 s, janelas sem N barras contíguas no mesmo pregão ficam fora da avaliação. Um toque é um rótulo de preço, sem pressupor preenchimento de ordem. No modo ensemble, o classificador existente é recalibrado para o alvo selecionado.

`classe`, `tipo_ordem` e `pts_maior_30` ficam protegidos como entradas. A coluna `classe` pode continuar sendo o rótulo. A seção **Campos excluídos** mostra as colunas do CSV. No ensemble, o programa remove as árvores que dependem do campo segundo o mapa de dependências. No Replay NTSL, o aplicativo bloqueia a execução se o código solicitar uma série excluída. O relatório informa a quantidade removida. OHLC e campos de identificação ainda podem ser usados para formar os rótulos, ordenar os candles ou filtrar o horário. Os rótulos futuros ficam fora dos preditores. Na abertura, as árvores usam features defasadas e o gap da abertura atual.

Os gráficos ao vivo mostram o melhor candidato da busca por geração. O relatório exportado inclui acurácia, precisão dos sinais, recall, F1, acurácia balanceada e os valores de cada gene selecionado. A tabela final compara busca e teste cronológico. O replay de estratégia ganhou curva de resultado realizado. O arquivo `evolucao.csv` guarda os dados dos gráficos genéticos.

## Linha de comando

No PowerShell, abra a pasta extraída:

```powershell
.\SimuladorCotacao-CLI.exe --version
.\SimuladorCotacao-CLI.exe estrategia --csv "C:\Dados\indicadorv7_claude.csv" --ntsl .\modelo_profit.ntsl --segundos 5 --formato profit --saida .\replay_v7
.\SimuladorCotacao-CLI.exe otimizar --config .\config_v7.json --csv "C:\Dados\indicadorv7_claude.csv" --saida .\otim_v7
.\SimuladorCotacao-CLI.exe candles "C:\Dados\negocios.csv" --formato negocios --segundos 5 --saida .\candles.csv
```

## Código e reconstrução do pacote

O motor e a interface estão em `ntsl.py`, `estrategia.py`, `app.py` e `interface.html`. A versão está em `VERSION`, nas propriedades dos executáveis e no [CHANGELOG.md](CHANGELOG.md). A pasta `windows` contém fonte dos launchers e dependências fixadas.

Em Linux, use Python 3.11+ e um toolchain MinGW-w64 x64. Baixe a distribuição embutida do Python **3.12.10 Windows x64** e as wheels correspondentes. Depois:

```bash
python -m pip download --only-binary=:all: --platform win_amd64 --python-version 312 -r windows/requirements.lock -d wheels
python windows/package.py --python-win python-3.12.10-embed-amd64.zip --wheels wheels --saida simuladorCotacao-v0.12.0-win64.zip
```

Para desenvolver ou testar com o seu Python local, instale `requirements.txt` e rode `python app.py`. Para um comando de terminal no código-fonte, use `python app.py --cli estrategia --help`.

### Conexão com a interface local

Se uma aba antiga perder a conexão, abra novamente o executável e use a nova aba que ele abrir. O CSV é enviado em blocos com indicação de progresso. A interface tenta novamente após uma interrupção transitória e identifica a etapa da falha.

### Acompanhamento durante a execução

Na busca genética, acompanhe a geração, os candidatos concluídos e os melhores parâmetros assim que termina cada avaliação. As métricas parciais usam o conjunto de busca. A validação cronológica tem uma etapa separada e seus resultados aparecem no relatório. No replay direto, acompanhe as barras processadas, as ordens executadas e o resultado bruto realizado.

### Pausar, retomar e cancelar

Durante a busca ou o replay, os controles ficam junto ao progresso. A pausa mantém a execução e os resultados parciais na memória e não conta para o limite de tempo da busca. Cancelar interrompe a execução e mantém as métricas parciais na tela. As ações são aplicadas no próximo ponto de parada do motor. Leitura de arquivos, cálculos vetorizados e escrita de relatórios podem levar alguns instantes para responder.

Em **Usar recursos máximos**, cada processo NTSL reaproveita as séries numéricas do CSV e a matriz de histórico entre candidatos. O Ensemble destina a RAM restante ao cache de scores, depois de calcular a reserva do sistema e a memória estimada dos trabalhadores. A RAM ocupada depende do tamanho do CSV, do modelo e da quantidade de avaliações úteis.

### Base de cotações

Em **Dados**, abra **Cadastrar CSV na base de cotações**. Informe o papel, a periodicidade e, se desejar, as datas e a observação. O simulador reconhece os formatos já aceitos pelo replay e detecta as datas do arquivo. A base SQLite e as cópias dos CSVs ficam na pasta `cotacoes`, ao lado de `resultados`. Faça backup dessa pasta inteira para levar a base a outro computador.

Selecione a série em **Origem dos dados** e ajuste o intervalo de pregões, se necessário. Os dois limites são inclusivos. A periodicidade de candles prontos é mantida. Para negócios com timestamp, você pode ajustar o intervalo de agregação dos candles no teste.

### Finalizar a busca e exportar

**Finalizar busca agora** deixa as avaliações em andamento terminarem, encerra a busca e valida o melhor candidato encontrado pelo objetivo original. O relatório indica quando a parada foi antecipada. No painel **Parâmetros otimizados**, escolha um critério, receba os parâmetros em JSON ou baixe o código NTSL com os valores aplicados às declarações de inputs. A escolha usa os candidatos já avaliados na amostra de busca que cumpriram o mínimo de sinais. A troca de critério não executa uma nova busca. O replay completo NTSL exporta o código parametrizado. No Ensemble, a exportação segue as condições indicadas no relatório.

### Classificação e resultado em reais

Em uma otimização de compra, escolha como alvo a classe positiva de compra ou uma regra de alta por barras ou pontos. A sensibilidade mede **VP ÷ (VP + FN)**. A especificidade mede **VN ÷ (VN + FP)**. O valor preditivo negativo mede **VN ÷ (VN + FN)**. A tela mostra as contagens e taxas durante a busca classificatória.

Informe o valor em reais por ponto e contrato. Para o WIN, o campo começa em R$ 0,20. No replay NTSL, o resultado bruto em reais é a soma realizada de pontos × contratos multiplicada por esse valor. O cálculo usa as quantidades executadas pela estratégia e aparece no progresso e no relatório. O líquido deduz as taxas configuradas e o bruto já incorpora o slippage nos preços executados. O Ensemble mede classificação. Use o motor Replay NTSL para obter resultado financeiro simulado.

### Busca aleatória adaptativa

Em **Otimização**, selecione **Aleatória adaptativa**. O CSV deve ter uma coluna `classe`. Informe a classe positiva, por exemplo `1C`, e as metas de sensibilidade e especificidade. O programa começa com combinações da faixa de inputs, sorteia novas combinações e explora variações próximas às que mais se aproximaram das duas metas. Cada combinação é avaliada uma vez. A busca termina ao cumprir simultaneamente as duas metas na amostra de busca, ao esgotar o espaço, ao atingir os limites de lotes ou tempo, ou por solicitação do usuário. O relatório mostra separadamente se as metas também foram atingidas nos pregões cronológicos reservados para teste.

### Base de estratégias

Carregue um arquivo NTSL ou cole o código no editor. Em **Base de estratégias NTSL**, informe o nome e clique em **Salvar estratégia na base**. Selecione uma estratégia cadastrada e clique em **Carregar no editor** para reutilizá-la. O mesmo nome com código diferente salva uma versão adicional. O mesmo nome com código idêntico atualiza a observação. A pasta de backup da base de cotações também contém o cadastro das estratégias.

### Histórico, reprodução e publicação de execuções

O aplicativo cria um registro em `resultados/historico/<id>/` ao aceitar uma execução. Ao terminar, registra o estado, a duração e o motivo da parada. Mostra controles, etapas e gerações no log, e guarda um ZIP local mesmo com a opção GitHub desmarcada. Após erro ou cancelamento, o pacote inclui os dados completos e as avaliações que já estiverem disponíveis. Uma interrupção abrupta do processo pode deixar apenas o registro de início e os eventos escritos até aquele momento. Na CLI, o log de início e parada fica ao lado da saída como `<nome-da-saida>.execucao.jsonl`.

Na tela **Histórico de execuções**, abra os indicadores, baixe o ZIP ou carregue os dados, estratégia e configuração no formulário. Quando houver NTSL parametrizado, também é possível usá-lo como ponto de partida. Ajuste as faixas de busca, o método ou a fonte dos dados e execute novamente. Para um pacote externo, use **Importar ZIP de execução**. Sessões de pausa continuam usando **Carregar sessão**.

O contrato para análise automatizada é identificado por `schema: simuladorCotacao.execucao/1` em `resumo.json`. O ZIP contém a configuração efetiva, estratégia original, entrada CSV usada, log em JSON Lines e os relatórios disponíveis. Em otimizações, `avaliacoes.csv` registra cada combinação concluída, com os inputs, a aptidão e as métricas em JSON. Geração 0 identifica avaliações trazidas de uma sessão restaurada. `evolucao.csv` registra a liderança de cada geração, `candidatos.csv` contém o ranking da execução concluída e `metricas.json` distingue busca e teste cronológico. Ferramentas externas podem ler esses arquivos para comparar execuções e sugerir parâmetros.

Para compartilhar um teste, configure a variável de ambiente `SIMULADOR_GITHUB_TOKEN` antes de abrir o aplicativo, usando um token com permissão **Contents: Read and write** no repositório oficial. Marque **Publicar esta execução no GitHub do projeto** antes de iniciar. O ZIP, limitado a menos de 2 GiB para envio, é anexado a uma pré-release. Em caso de falha, o pacote local e a mensagem no histórico ficam disponíveis. Em repositório público, estratégia, resultados e dados de entrada ficam acessíveis publicamente. Em repositório privado, o download pelo navegador exige acesso ao repositório. A tela **Consultar GitHub** mostra os resumos publicados e oferece os links para baixar e importar os pacotes.


### Custos e regras de preenchimento

Em **Custos e preenchimento no Replay NTSL**, informe a soma das taxas em reais por contrato e lado e o slippage adverso em ticks. Por exemplo, R$ 0,25 por lado resulta em R$ 0,50 por contrato para uma entrada e uma saída completas. O preço de ordens a mercado, stops recém-disparados e da zeragem de fim de pregão incorpora o slippage. Um stop com preço limite aguarda se o preço simulado violar esse limite. Ordens limite passivas podem exigir que o candle negocie pelo menos um tick além do limite. Essa regra reduz preenchimentos por simples toque e permanece uma aproximação sem posição de fila.

O replay apresenta bruto, taxas, líquido e drawdown líquido. A otimização financeira usa o líquido. Taxas e slippage vêm zerados. A ultrapassagem de limite começa desmarcada. Para configurar pela CLI de replay, use `--custo-por-contrato-lado`, `--slippage-ticks` e `--limite-exige-ultrapassar`. Na CLI de otimização NTSL, configure os campos correspondentes em `regras_execucao` no JSON.

O subconjunto NTSL aceita arrays unidimensionais e rotinas com parâmetros escalares por valor. Arrays multidimensionais, parâmetros por referência, histórico de variáveis locais e funções ausentes no compilador geram diagnóstico com a linha do código.


### Indicadores do Replay NTSL

- `VWAP(0..3)` calcula VWAP por barra, pregão, semana ou mês. Com negócios e quantidade, usa preço × quantidade. Em OHLC, usa `v_vwap_barra` se fornecido ou aproxima cada barra pelo preço típico (máxima + mínima + fechamento) ÷ 3, ponderado por `volume_contratos` ou `volume`.
- `StdDevs(Serie, Periodo)` usa desvio padrão populacional na janela de barras disponíveis. `AgressionVolBalance()` lê `v_agressao_saldo_acumulado` ou acumula, por pregão, a diferença entre `v_agressao_compra` e `v_agressao_venda`. Sem os dados exigidos, o replay informa quais colunas faltam.
- Para comparar o v5.8 no replay local, use `p_Exec_Tick = 0`. Mesmo com o CSV de negócios, a estratégia executa no fechamento dos candles agregados.

### Validar um modelo parametrizado

Selecione **Validar modelo**, carregue o NTSL com os parâmetros finais e escolha o CSV ou um recorte da base de cotações. Também é possível usar **Validar estratégia otimizada** no histórico para carregar o NTSL exportado e, em seguida, trocar os dados de entrada. Informe o ativo no demonstrativo, se desejado. O modo executa o modelo com os parâmetros informados, sem busca.

O resultado mostra operações, volume em contratos, acerto, fator de lucro, bruto, taxas, líquido, drawdown e gráficos da curva líquida, drawdown e resultado por pregão. Uma operação vai da primeira entrada até a zeragem. Aumentos de posição e saídas parciais ficam vinculados à mesma operação. O acerto e o fator de lucro são calculados por operação líquida, incluindo as taxas da entrada e da saída. O fator fica indefinido se não há perdas.

O **CSV de conferência** registra cada execução, com data e hora de referência, identificação da operação, lado, volume, preço, preço médio de entrada, posição, resultado, taxas e saldo acumulado. A **nota de corretagem simulada em PDF** traz o balanço por pregão e as execuções detalhadas. É um demonstrativo da simulação, sem validade fiscal. Os horários são do candle de referência, não de negócios reais. Se a origem Profit só contém a hora até o minuto, o exportador deixa a precisão em minutos. O ZIP do histórico inclui ambos os arquivos.
