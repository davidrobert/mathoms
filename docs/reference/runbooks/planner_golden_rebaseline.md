# Runbook — Rebaseline do golden mensal do parecer

> **Workflow:** `.github/workflows/planner-golden-monthly.yml` (ADR-199 Ato 6 T-27 · [[ADR-201]], "hash + golden mensal detectam" persona drift).
> **Owner:** davidrobert, o humano que despacha e revisa o PR.
> **Severidade:** ticket, não page. Drift do parecer não derruba o produto.
> **Sinais de entrada:**
> - Issue `planner-drift-monthly`, aberta pelo run agendado quando o pytest falha.
> - Run agendado vermelho com `Sem baseline em tests/golden_baselines/`, que pede a semeadura.

---

## Modelo mental (30 segundos)

1. O run agendado (dia 1, 06:00 UTC) chama o parecer com LLM real.
2. Ele reduz a saída a métricas estruturais e compara com a última baseline em
   `tests/golden_baselines/parecer_monthly_<YYYY-MM>.json`.
3. Se não houver baseline, o run **falha**. Antes ele semeava em disco e pulava,
   e o drift nunca era comparado.

**Sem push em `main`.** O despacho com `update_baseline=true` termina numa
branch `agent/planner-golden-baseline/<yyyyMM>-<run_id>-<attempt>`. O PR é
aberto **por você**, pelo link do summary do run. São três os motivos:

- O Ruleset `main-protection` rejeita o push.
- O `GITHUB_TOKEN` não cria PR neste repo (`can_approve_pull_request_reviews: false`).
- PR de bot não dispara o CI ([[ADR-322]]).

**Sem auto-merge.** O despacho gera uma amostra **nova** do LLM. A que você
aceitou ao ler a issue de drift foi a do run que falhou, então quem revisa a
amostra nova é você, no PR.

## Pré-requisitos (owner-gated)

- Secret `ANTHROPIC_API_KEY_GOLDEN_MONTHLY` no repo. **Sem ele, o workflow pula e
  conclui `success`**. A pendência está no waiver do `.github/scheduled-workflows.yml`
  e no OWNER-GATED §0.
- A key é **dedicada**, num workspace Anthropic com teto de gasto (ordem de
  US$10/mês). Ela fica exposta ao job que executa deps de terceiros, e o teto
  limita exfiltração e loop de retry. O custo de um run é ≈ US$1, porque os 2
  testes chamam o LLM.
- O `model_id` default precisa estar disponível no dia. Se não estiver, a
  semeadura falha pelo motivo errado. Troca de modelo é com o `prompt-engineer`.

## Passos

1. **Despache a partir de `main`.** O link compara `main...<branch>`. Despachar de
   outra ref leva os commits dela para o PR.
   ```bash
   gh workflow run 'Planner Golden Monthly (LLM real)' --ref main -f update_baseline=true
   ```
2. Espere o run terminar e abra o **summary** dele. O job `baseline-branch` publica:
   - a tabela **anterior × nova** com a coluna `mudou`. O diff do PR não mostra o
     drift, porque cada mês é um arquivo novo;
   - o link **Abrir o PR pré-preenchido**, com título Conventional Commits e corpo
     com a tabela.
3. Abra o PR pelo link. O CI precisa reportar `All checks green`. Se o run ficar
   `action_required`, vá para *Falhas* abaixo.
4. Revise a tabela. Mudança em `p0_count` ou em `ancora_dominante_riscos`, ou
   variação acima de 50% em `riscos_count`, é exatamente o que o gate mede.
   Confirme que a amostra nova conta a mesma história que você aceitou.
5. Mergeie por squash, **sem `--auto`**.

## Falhas

| Sintoma | Causa | Ação |
|---|---|---|
| `baseline candidata rejeitada: ...` | O payload do job não confiável fugiu do shape fechado (`dev/ci_planner_baseline_branch.py`). | Leia a mensagem: ela nomeia o valor ofensor. Não afrouxe o validador para fazer passar. Métrica nova no teste exige ajuste deliberado. |
| `... não foi escrito pelo teste` | O pytest passou sem escrever a baseline do mês. | Confira o `MATHOMS_GOLDEN_UPDATE_BASELINE` no step e o mês UTC (corrida na virada do mês). |
| Push rejeitado (non-fast-forward) | A branch do mesmo run e tentativa já existe. | Abra o PR da branch existente ou despache de novo. Nunca force-push: com PR aberto, ele congela o CI ([[ADR-322]]). |
| PR com CI `action_required` ou exigindo aprovação | O commit é do `github-actions[bot]`. O campo `require_extra_approval_for_unattributed_changes` do Ruleset não foi medido em 2026-10-08. | Recrie o commit com a sua autoria numa branch nova (`git switch -c agent/planner-golden-baseline-manual/<ts> origin/<branch>`, `git commit --amend --reset-author --no-edit`, push) e abra o PR dela. Registre o resultado aqui; o primeiro despacho é o spike. |
| Issue `ops-llm-eval` aberta | O job `report-failure` viu `failure` ou `cancelled` (timeout do LLM incluído). | Triagem pelo log do run. Se o pytest falhou, é drift (issue `planner-drift-monthly`); se não, é infra. |

## Se o secret for recusado

O workflow não mede nada sem a key. Nesse caso, apague o workflow, o
`tests/test_parecer_golden_monthly_real.py` e a entrada do
`.github/scheduled-workflows.yml`, e registre emenda na [[ADR-201]]: "drift do
parecer não é medido". É o aceite por escrito que o OWNER-GATED pede.
