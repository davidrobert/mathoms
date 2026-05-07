# Agent Prompts — Arquivo

Prompts de lanes **concluídas e fora do contexto vigente** vivem aqui.
Critério para arquivar (W6-T04, CTO-007):

1. PR da lane mergeado em `main` há ≥30 dias.
2. Linha correspondente em [../../BACKLOG.md](../../BACKLOG.md) marcada
   ✅ ou removida.
3. Lane não é mais referenciada como contexto/dependência por nenhuma
   lane ativa.

## Como arquivar

```bash
git mv docs/agent_prompts/track_<slug>.md \
       docs/agent_prompts/archive/track_<slug>-YYYY-MM-DD.md
```

A data é a do merge da lane (não a do `git mv`). Em seguida, **remova
a entrada** da tabela em [../README.md](../README.md) — o índice deve
listar apenas prompts ativos ou ainda relevantes para pickup.

## Por que não deletar

Prompts arqueados são arqueologia operacional: contexto exato de
decisões, prompts efetivos vs. inefetivos, padrão de instruções que
funcionou bem. Útil para gerar prompts futuros com base em prior art.

Histórico permanece em `git log` mesmo se deletássemos, mas a busca
por nome ("como foi descrito o prompt da lane X?") fica mais cara.
Arquivo achatado em `archive/` resolve sem custo perceptível de espaço.
