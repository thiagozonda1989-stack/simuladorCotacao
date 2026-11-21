# Fluxo de colaboração das IAs

O `AGENTS.md` e as diretrizes do projeto definem as regras comuns. A Issue concentra a tarefa e os critérios da etapa. O PR concentra a implementação, a evidência e os pareceres. O SHA da execução e o SHA revisado do PR podem ser diferentes e devem ser informados.

## Piloto ProfitRTD

1. Publique a branch `research/piloto-ias-etapa1`. Use o utilitário abaixo para criar ou reencontrar a Issue e o PR de rascunho. O destino é `main`. Esse PR inclui a linha local do simulador até a v0.14.0, que ainda não estava na referência remota quando o piloto foi preparado.
2. O Codex local executa os testes do baseline no Windows e completa `ETAPA1_EVIDENCIAS.md` com resultados agregados. Para reproduzir a v0.14.0, use o SHA da Issue. Para testar o PR, use o SHA do PR e registre essa distinção.
3. Compartilhe o link do PR e o SHA de revisão. Claude verifica lógica e implicações para o replay. Gemini verifica qualidade e interpretação das amostras. ChatGPT verifica método e rastreabilidade. Codex registra o que executou localmente.
4. Thiago decide se fecha a etapa. Se o código, os dados agregados ou a conclusão mudarem, renove os pareceres afetados no SHA novo.

## Evidências compartilhadas

Antes de solicitar parecer, siga a [diretriz de publicação de dados e logs do Profit](../../DIRETRIZES_PROJETO.md#publicação-de-dados-e-logs-do-profit). Forneça no PR os caminhos dos arquivos e o SHA de cada execução. Envie links fixos para os arquivos compartilháveis e confira que eles abrem antes do repasse.

## Parecer de revisão

```text
IA:
SHA do PR revisado:
Evidência ou comandos conferidos:
Achado e impacto:
Decisão: aprovado | aprovado com ressalva | bloqueado
```

## Publicação pelo Codex local

Com GitHub CLI autenticado com acesso de escrita ao repositório, abra a raiz do clone da branch piloto e execute:

```powershell
python tools/publicar_piloto_ias.py --publicar
```

Sem `--publicar`, o utilitário apenas valida o clone e apresenta os comandos de publicação. A publicação usa push sem força, cria ou reutiliza Issue e PR e imprime os links. O PR é criado como rascunho e não é mesclado pelo utilitário.

## Automação inicial

O workflow de testes existente roda em pushes e PRs quando o GitHub Actions está habilitado no repositório. A captura e os testes com dados reais permanecem no Windows. Para revisão automática no PR, comece com um revisor nativo conforme o acesso disponível. Uma revisão automática de código não substitui o parecer metodológico. Nunca ligue bots para responder aos próprios comentários ou publicar dados de mercado.

Registre número de repasses manuais, divergências de SHA e testes refeitos ao fechar a etapa. Compare esses números com o fluxo anterior antes de adicionar mais automações.
