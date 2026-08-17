---
id: A40.l58
type: lane
title: "schema_validation warn → strict: o PR5 que a l5 declarou como outra lane"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l58-flip-do-schema-para-strict
owner: sre-devops
depends_on:
  - "[[A40.l5]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/pipeline
---

# A40.l58 — `flip-do-schema-para-strict`

> 🔓 **Desbloqueada em 2026-08-17 — o bloqueador morreu em 2026-08-14 e ninguém
> viu.** A condição escrita abaixo era *"os PRs 2–4 da l5"*: **#1440** (PR2,
> 08-13), **#1441** (PR4, 08-14) e **#1450** (PR3, 08-14) estão **todos
> mergeados**. A lane ficou `blocked` por **3 dias** sobre dep satisfeita.
>
> `depends_on: [[A40.l5]]` **permanece** — a dep é real e agora está terminal
> (`shipped`, 2026-08-17). O que estava errado era o `status`, não o grafo.
>
> **O instrumento funcionou; o insumo é que estava podre.** O
> [`_sprint_current_renderer`](../../../../dev/_sprint_current_renderer.py) **já**
> dá seção própria ao `blocked` — exatamente para que lane bloqueada não suma no
> instante em que vira pegável (comentário no `:44`) — e ainda imprime a dep
> pendente. O que ele imprimia era **`⛔ dep pendente: A40.l5 (in_progress)`**:
> uma frase que lê como bloqueio legítimo, porque o `status` da l5 também estava
> stale.
>
> **Dois status stale se mascararam mutuamente.** Nenhum leitor humano tinha
> como suspeitar: a linha do painel era coerente consigo mesma. Só cruzar o
> frontmatter com os PRs mergeados em `main` desfaz — que é a checagem que
> nenhum gate fazia.
>
> **Classe, não incidente.** O merge da dep não tem escritor no `status` da lane
> dependente: quem fecha a dep não sabe quem depende dela. É a mesma classe que a
> [[A40.l59]] gateia na transição — registrada lá como caso de origem.
>
> **Motivo original do bloqueio (preservado — era correto quando escrito):**
>
> > **`blocked` por [[A40.l5]]** — o flip exige *"o drift medido em mãos"*
> > (§Forma da l5), e o drift só existe depois que os PRs 2–4 da l5 tiparem os
> > blocos restantes do `e5_analysis.schema.json`. Flipar antes é converter
> > lacuna de tipagem em run de cliente abortado.
>
> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Origem: [[A40.l5]] §Forma, PR5 — *"Proposta `warn → strict` …
> **Outra lane.** ADR própria + gatilho `sre-devops` (blast radius = run de
> cliente)"*. Esta lane materializa a rota que a l5 prometeu; "outra lane" que
> não existe é rota que aponta para o nada.

## Problema

A validação de schema do pipeline roda em modo `warn` em produção
(`pipeline.json → schema_validation.mode`, override
`MATHOMS_PIPELINE_SCHEMA_MODE`): payload que viola o contrato **loga e passa**.
O gate real de schema é o golden de execução — que a l5 descobriu ter ficado
**anos sem validar nada** (o `pipeline.json` de teste era `{}`, `enabled`
defaultava `False`). A l5 ligou a validação `strict` **fixa** na suíte; falta o
flip em produção, onde o blast radius é run de cliente.

## Escopo

1. **ADR `Proposto` antes do PR** (exigência registrada na l5) — decide o modo
   de rollout: strict direto, ou observação → strict com kill-switch.
2. Medição do drift real: com os PRs da l5 mergeados, quantos payloads de
   produção violariam `strict` hoje? (Zero é hipótese, não premissa.)
3. Flip com kill-switch documentado (`MATHOMS_PIPELINE_SCHEMA_MODE=warn` como
   rollback de 1 env var, sem deploy).
4. Re-adoção do "flip órfão" que a l5 registrou: a suíte valida com `strict`
   fixo, não dependente de CI lembrar de setar env.

## Coordenação declarada — RV6-06 (escrita em 2026-08-17, Onda 0 do [[PLAN-deterministic-authority]])

Esta lane **permanece dona do `mode_overrides` e do kill-switch como infra**. O
que mudou de mãos é o *consumo* dessa infra para dois schemas específicos: o item
1e do [[PLAN-deterministic-authority]], materializado na [[A40.l67]], flippa
`baseline_patrimonial` e o schema irmão do E1.5a **per-schema**, via
`mode_overrides`, com drift medido por ≥7 dias de dogfood. A [[A42.l6]] cedeu o
mesmo eixo e mantém retenção/`SCHEMA_BY_STAGE`.

**Tensão que o dono desta lane precisa resolver — não a resolvo aqui.** O §Escopo
acima trata do flip **global** (`pipeline.json → schema_validation.mode`), e o
plano carrega anti-decisão explícita em sentido contrário: *"NÃO subir
`schema_validation.mode` global — só per-schema com janela medida."* As duas
posições não são compatíveis como escritas. Três encaminhamentos possíveis, todos
do `sre-devops`:

1. a ADR desta lane decide o rollout global e **supera** a anti-decisão do plano,
   que então é emendada;
2. esta lane se re-escopa para "entregar e provar a infra per-schema", e o global
   vira deferimento datado;
3. as duas convivem com o global **depois** de N schemas flipados per-schema, com
   o N declarado.

Enquanto não houver decisão, vale a regra operacional da fila (§0d do plano):
esta lane e a [[A40.l67]] **não podem estar abertas na mesma janela de
rebaseline** — J2 é da l67.

## Critério de aceite

- ADR mergeada antes do PR de flip, com a decisão de rollout e o rollback
  declarados.
- O drift pré-flip está **medido e citado** na ADR (não "acreditamos que zero").
- Kill-switch provado: com a env de rollback setada, payload inválido volta a
  logar-e-passar — teste, não prosa.
- Runbook de incidente: o que fazer quando um run de cliente aborta por schema
  (gatilho `sre-devops`).
