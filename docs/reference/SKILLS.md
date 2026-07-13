# Skills de projeto

> Procedimentos recorrentes empacotados como **skills** em `.claude/skills/`,
> invocáveis por `/<nome>`. Agentes as descobrem sozinhos (lista `available_skills`
> do harness); esta tabela existe para descoberta **humana**. A regra canônica de
> quando algo vira skill (vs. subagente `.claude/agents/` vs. prompt LLM em
> `config/prompts/`) é [[ADR-302]].

| Skill | O quê faz | Quando usar | Fonte | Canônica |
| --- | --- | --- | --- | --- |
| `audit-vault` | Auditoria recorrente do vault de docs (completude/corretude/consistência/precisão): gates determinísticos → delegação aos especialistas → síntese em `docs/_MOC/AUDITS-active.md`. | Dono pede para auditar documentação/ADRs/planos/prompts, ou ao fechar um plano canônico grande (drift recém-criado). | [.claude/skills/audit-vault/SKILL.md](../../.claude/skills/audit-vault/SKILL.md) | [[ADR-302]] |
| `pipeline-review` | Roda o pipeline COMPLETO de um workspace no ambiente local e produz revisão profunda priorizada (execução + relatório) com tabela prioridade/dificuldade/risco, delegando aos especialistas com verificação adversarial. | Rodar o pipeline de um workspace e analisar o relatório; revisar a saúde de um run; gerar relatório novo e criticá-lo. Recebe workspace por email ou uuid. | [.claude/skills/pipeline-review/SKILL.md](../../.claude/skills/pipeline-review/SKILL.md) | [[ADR-302]] (classe) |

Adicionar uma skill nova: crie `.claude/skills/<nome>/SKILL.md` (frontmatter `name` +
`description`), acrescente uma linha aqui, e — se for a **primeira** de uma classe
nova de procedimento — abra ADR; instâncias conformes à classe já decidida ([[ADR-302]])
não precisam de ADR própria (mesma disciplina dos subagentes catalogados no CLAUDE.md).
