# Sonda nativa de prioridade entre saída a mercado e proteção

WINZ26 em 26/10/2026, barras de 1 minuto, fuso America/Sao_Paulo. Motor executado `d67a8731bfa1597b0bdfe4cc4064e6502822f81a`. Protocolo e referência do simulador publicados em `7fb2598546be3d1793b2cdf5f51106b228d7002e`. [Sonda e protocolo](../WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1/README.md) · [Matriz local anterior](../WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1/sonda_prioridade_simulador.csv)

Nas duas variantes com saída a mercado, o Profit registrou **uma única saída de 1 contrato às 10:55:00, no preço da abertura da barra**, a +220 pontos (R$ 44,00), sem segunda venda registrada e com posição e pendências zeradas até 10:58. O simulador reproduziu ambas com os parâmetros do painel. Nos controles, o Profit preencheu no tick de 5 pontos mais próximo do nível solicitado, enquanto o simulador executou no nível bruto. [Matriz Profit × simulador](matriz_profit_simulador.csv)

## Associação e configuração

| Rodada | `p_Perna` | `p_SaidaMercado` | Proteção no console | `SOLICITA_MERCADO` | Operação exportada |
|---|---:|---:|---|---|---:|
| 01 · alvo controle | 1 | 0 | Alvo, +428 pts | Ausente | +430 pts |
| 02 · alvo com mercado | 1 | 1 | Alvo, +428 pts | 10:54, seq. 5 | +220 pts |
| 03 · stop controle | 2 | 0 | Gatilho −793, limite −894 pts | Ausente | −795 pts |
| 04 · stop com mercado | 2 | 1 | Gatilho −793, limite −894 pts | 10:54, seq. 5 | +220 pts |

O print **`01_alvo_mercado_configuracao.png` pertence ao alvo controle**. O painel mostra `p_Perna=1` e `p_SaidaMercado=0`. No trecho visível, há solicitação de alvo e a avaliação de 10:54 segue diretamente para 10:55, como no TXT do controle. O CSV e o PDF desse conjunto confirmam +430 pontos e R$ 86,00, respectivamente. O arquivo original mantém seu nome. Os CSVs 02 e 04 têm o mesmo SHA-256 e a mesma operação. A associação entre essas duas variantes vem dos prints e dos eventos de proteção no console. Os PDFs confirmam os resultados e a contagem, e por si sós também não identificam a perna nessas duas variantes. [Inventário dos 16 originais](inventario_anexos.csv) · [Parâmetros por rodada](parametros_por_rodada.csv)

Os quatro prints registram Profit Ultra 5.0.4.33, a aba Backtest, WINZ26, 1 minuto, período de análise de 26/10 a 26/10/2026, quantidade e máxima 1, slippage de 0 ticks e **Executar nos Limites** ativo. O relógio inferior de Replay mostra outra data, enquanto a janela de análise, `p_Data`, console, CSV e PDF concordam em 26/10. Os quatro PDFs registram custo zero e uma operação, e os CSVs registram comissões zero e 1 compra/1 venda. **O seletor OHLC/Tick a Tick está fora da área visível nos prints.** O protocolo prescreve OHLC, e as observações são compatíveis com ele. Os anexos não certificam a posição do seletor em nenhuma das quatro rodadas.

Parâmetros comuns vistos no painel: `p_Data=1261026`, `p_Entrada=1051`, `p_Protecao=1052`, `p_EnvioMercado=1054`, `p_Limpeza=1056`, `p_Fim=1058`, `p_Alvo=428`, `p_Stop=793`, `p_Folga=101`. O editor exibe padrões 430/795/100, diferentes dos valores carregados no painel. Os níveis calculados nos consoles confirmam os parâmetros relevantes de cada perna.

## Sequência observada e preços

Todos os quatro consoles contêm dois blocos completos idênticos, comparados linha a linha incluindo o cabeçalho Debug. Foi retido o primeiro bloco na ordem física, com 11 eventos nos controles e 12 nas variantes com mercado. Não houve avisos de execução. O rótulo 10:51 aparece duas vezes para o mesmo `CurrentBar` (26.873), com posição 0 na sequência 1 e +1 na sequência 2. A compra é solicitada na sequência 1 e sua execução é registrada em outro arquivo, às **10:52:00**. [Console derivado e linhas de origem](console_profit.csv)

Na sequência 3 (rótulo 10:52) há uma única solicitação de proteção. A posição permanece +1 com `HasPendingOrders=1` nos rótulos 10:53 e 10:54. A solicitação a mercado aparece imediatamente após a avaliação 5 apenas nas rodadas 02 e 04. Nas quatro rodadas, a avaliação 6 (rótulo 10:55) já vê posição 0 e pendências 0. Esse estado segue até 10:58, sem solicitação de limpeza. O CSV registra a única saída às 10:55:00.

| Rodada | Preço solicitado (pts desde a entrada) | Abertura de 10:55 (pts) | Profit (pts e resultado) | Simulador com painel | Simulador com padrões |
|---|---|---:|---:|---:|---:|
| 01 · alvo controle | Limite +428 | +220 | +430 · R$ 86,00 | +428 · R$ 85,60 | +430 |
| 02 · alvo com mercado | Limite +428 | +220 | +220 · R$ 44,00 | +220 · R$ 44,00 | +220 |
| 03 · stop controle | Gatilho −793, limite −894 | +220 | −795 · −R$ 159,00 | −793 · −R$ 158,60 | −795 |
| 04 · stop com mercado | Gatilho −793, limite −894 | +220 | +220 · R$ 44,00 | +220 · R$ 44,00 | +220 |

A máxima de 10:55 é +445 e a mínima −875. A barra abre abaixo do alvo e acima do gatilho, e alcança ambos os níveis em suas respectivas rodadas. A mínima fica acima do limite do stop enviado (−894) e também do tick mais próximo desse limite (−895). No controle do alvo, a execução fica 2 pontos acima do limite calculado. No controle do stop, a execução fica 2 pontos abaixo do gatilho calculado. Os dois preços correspondem ao tick de 5 pontos mais próximo e ao resultado anterior com os padrões do código. Isso evidencia a diferença de preços da execução nativa no controle, sem estabelecer um algoritmo geral de arredondamento. O preço limite aceito pelo Profit no stop-limit continua indeterminado. A saída no preço da abertura ocorre nas duas rodadas com solicitação a mercado, independentemente da perna pendente.

Os CSVs de operações e o console evidenciam a solicitação a mercado, o preço, o volume, os horários exportados e o estado que a estratégia observou. Sem histórico nativo de ordens da mesma execução, não há confirmação do tipo da venda preenchida, da ordem temporal subminuto de disparos e execuções, da causa da remoção da pendência ou de cancelamento OCO. Apenas as linhas do simulador têm tipo de saída e contagem de gatilhos atribuídos.

## Conferência de barras e reprodução

Não foi anexado um CSV de barras exportado na mesma rodada. Os quatro consoles concordam nos 32 valores OHLC da janela (quatro por barra). Esse recorte também coincide com três CSVs locais independentes de exportações anteriores do Profit (`SONDA_S1_ALVO_barras.csv`, `SONDA_S1_STOP_barras.csv`, `barras_v58.csv`) e com o arquivo de referência preparado para o simulador. A janela 10:51 a 10:58 contém oito barras consecutivas sem lacunas ou timestamps duplicados. A repetição no rótulo de 10:51 corresponde às duas avaliações. [Barras relativas](barras_conferencia.csv) · [Hashes das fontes de barras](fontes_barras.csv)

Foram reexecutadas as quatro combinações com os parâmetros do painel e com os padrões do código, no mesmo motor e com a mesma série preparada `WINZ26_20261026_profit_1min_privado.csv`. Os dois perfis reproduzem os horários, as quantidades, as solicitações e os estados observados. O perfil padrão reproduz as quatro linhas de `sonda_prioridade_simulador.csv` anterior. O perfil do painel reproduz os níveis solicitados nos quatro consoles, as saídas da abertura e a diferença de dois pontos nos controles. O motor e a sonda versionada permanecem intactos. Para rodar, use as pastas privadas indicadas pelas variáveis e crie um destino novo.

```powershell
# $ref é a pasta da rodada 7fb2598. $barras é a série privada preparada.
# $originais contém os 16 anexos mais os três CSVs de barras anteriores.
New-Item -ItemType Directory -Path $replays
$ntsl = Join-Path $replays 'sonda_prioridade_simulador.ntsl'
$codigo = [IO.File]::ReadAllText((Join-Path $ref 'sonda_prioridade_mercado_protecao_profit_v1_0.ntsl'))
$codigo = $codigo -creplace 'FloatToString\((\w+), 0\)', '($1)' -creplace ', clYellow\);', ');'
[IO.File]::WriteAllText($ntsl, $codigo)
foreach ($perfil in @('painel','padrao')) {
    $config = if ($perfil -eq 'painel') { @{p_Alvo=428; p_Stop=793; p_Folga=101} } else { @{p_Alvo=430; p_Stop=795; p_Folga=100} }
    foreach ($perna in @(1,2)) {
        foreach ($mercado in @(0,1)) {
            $nome = "$perfil-$perna-$mercado"
            $p = $config + @{p_Perna=$perna; p_SaidaMercado=$mercado; p_Data=1261026; p_Entrada=1051; p_Protecao=1052; p_EnvioMercado=1054; p_Limpeza=1056; p_Fim=1058}
            [IO.File]::WriteAllText("$replays/$nome.inputs.json", ($p | ConvertTo-Json))
            py -3.11 estrategia.py --csv $barras --ntsl $ntsl --inputs "$replays/$nome.inputs.json" `
              --saida "$replays/$nome" --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
              --avaliacao-pos-preenchimento --rastrear-ordens --protecoes-ate-cancelar
        }
    }
}
# O extrator lê os PDFs com PyMuPDF (disponível no PYTHONPATH da conferência).
py -3.11 -m tools.publicar_prioridade_protecao_profit --originais $originais --replays $replays `
  --referencia $ref --barras $barras --saida $saidaPublicavel
py -3.11 -m pytest -q
```

A suíte local passou com **108 testes** e 12 avisos de fuso do pandas já conhecidos. Nenhuma rodada precisa ser repetida para determinar preço, quantidade e número de saídas. Se a comprovação documental do modo for necessária, recapture o seletor nas quatro configurações ou repita as rodadas cuja configuração original não puder ser recuperada. Para comprovar o tipo de saída, a ordem temporal ou o ciclo das ordens, obtenha o histórico nativo das rodadas 02 e 04. Os originais e os preços absolutos ficam no Windows. [Manifesto dos derivados](SHA256SUMS.txt) · [Fontes para o Gemini](fontes_gemini.txt)
