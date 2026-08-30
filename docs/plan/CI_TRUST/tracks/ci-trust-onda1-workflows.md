---
id: TRACK-ci-trust-onda1-workflows
type: track
title: "Track Onda 1 — leva única de .github/workflows/**: inertes, canal de falha 9/9, endgame do watchdog (heartbeat), security-green, nightly por job"
plan: PLAN-ci-trust
status: ready
created_at: "2026-08-25"
agent_role: sre-devops
tags:
  - type/track
  - area/ci
  - status/ready
  - priority/p1
---

# Track Onda 1 — `ci-trust-onda1-workflows`

> Executa a **Onda 1 do [[PLAN-ci-trust]]**. Pré-requisito: track
> [TRACK-ci-trust-onda0-governanca](ci-trust-onda0-governanca.md) mergeado — o PR 3
> daqui muda a função de veredito do gate, e o **rollback nomeado é o bypass
> sancionado + Issue do detector** (só existem após a Onda 0). PRs de
> `.github/workflows/**` na ordem de risco **1 → 2 → 3**; mudança de veredito
> do `all-green` viaja **sozinha**. Com o PR 0 da Onda 0 no ar, PR nesse path
> não starva mais a fila (403 vira skip daquele PR).

## PR 1 — inertes (nenhum muda veredito) ✅ **entregue 2026-08-27**

> Re-medição (n=8 runs success, 2026-08-27) que mudou dois números do plano:
> `lint-all` mediana **138s** — o teto de 4min estava **abaixo** de 2× a
> mediana, critério da [[ADR-210]] §Adendo 2026-08-03, e subiu para 5min;
> `pipeline-tests` mediana **202s** = **67%** do teto, acima do gatilho de 60%
> do §Adendo 2026-08-08(b), teto para 8min. `go-lint` (19s), `go-test` (66s) e
> `all-green` (4s) ganharam teto — rodavam com o default de 360min.

- `timeout-minutes`: go-lint 6 · go-test 8 · all-green 2 (hoje sem teto —
  default 360min; observados 58s / 1m41s / <1min).
- Teto do `pipeline-tests` 5→8min + comentário re-medido (mediana 3m15s =
  65% do teto atual; comentário afirma "54s"). Idem `lint-all` (comentário
  "44s" → mediana 2m06s). Regra: número citado se re-mede, não se relê —
  citar run ids.
- `concurrency` do nightly: cron pesado 06:00 cancela `main-smoke` 05:30 em
  voo (mesmo group + `cancel-in-progress: true`; cancelamento não abre Issue
  porque `if: failure()` não dispara). Diferenciar group por cron
  (`nightly-${{ github.event.schedule || github.ref }}`) ou
  `cancel-in-progress: false` para `schedule`. **Pré-req do religamento.**
- Encolher a legenda de sinais no `budget-alert.yml` (pós-#1613/#1625,
  `WAIVED` e `GH` não aparecem mais na Issue).
- Fecha os §Follow-ups menores de [[ADR-210]] §21b/§21c (blockquote de
  fechamento em cada um).

## PR 2 — canal de falha 9/9 (KR-F)

- Cada workflow do manifesto ganha step `if: failure()` → abre/atualiza Issue
  com label declarada em `alerts:` (hoje 2/9 têm; em 08-17 o
  `auto-update-prs` falhou 10× em ~5h e nada percebeu). `issues: write`
  revisado job a job (privilégio mínimo).
- Justificativa do `S2` no manifesto passa a dizer "9 de 9".
- Zumbis LLM: key-check **fail-closed em `schedule`** (substitui o waiver
  datado da Onda 0 OU convive até o owner criar os secrets).
- Aceite por **falha forçada**: quebrar `auto-update-prs` num branch de teste
  ⇒ Issue abre com a label declarada.

## PR 3 — endgame do watchdog (heartbeat-Issue), sozinho

Retoma [[ADR-210]] §Adendo 2026-08-21b (condição A34 G0 satisfeita — repo
público) com o desenho fechado no co-design `sre-devops` de 2026-08-25:

- **Cron mantém UMA Issue `ops-watchdog` que nunca fecha**; corpo
  máquina-legível: `violations`, `checked: M/N`, idade da violação mais
  antiga, **pré-vencimentos** (AUTOUPDATE_PAT, waivers — warning ≤14d; hoje
  waiver só tem 2 estados: válido / hard-fail repo-wide, e foi isso que
  produziu 7 bypasses em 08-14).
- **Gate de PR = sinais offline (S0 + waiver vencido) + 1 chamada** ao
  endpoint de **Issues** (fora do índice de runs, onde moram as 6/7 leituras
  obsoletas medidas). Reprova se: Issue ausente (**fail-closed** — hoje
  ausência é verde) · `updatedAt` > máx · `violations > 0` · `checked < N`.
- Job não-required roda S1/S2/S3 completos; tem `if: failure()` → Issue
  (senão é o 10º compensador invisível); **não** entra em `all-green.needs`.
- **Modos residuais R1–R5 declarados na emenda** (a fonte é o co-design
  registrado no plano): R1 verdito rebaixado ⇒ mitigação `checked: M/N`; R2
  latência = `max_age` (troca aceita); R3 Issue fechada à mão ⇒ fail-closed
  ruidoso (válvula = waiver offline); R4 corpo e gate consomem a **mesma**
  função `--report` + teste de mutação (violação sintética aparece no corpo e
  reprova o gate); R5 canal de falha do próprio job.
- **Supersedure**: a entrada `ops-watchdog` com `max_issue_age_days: 3`
  deferida no §21b é **incompatível** com Issue que nunca fecha (no 4º dia,
  idade>3 = hard-fail permanente). Fechar o deferimento **por supersedure**
  (precedente: §21c fez isso com o retry), com blockquote no §21b. "Rot"
  passa a ser idade da violação mais antiga **no corpo**, não idade da Issue.
- Emenda datada na [[ADR-210]] no mesmo PR (`amended_at` + blockquote de
  sinal; keyword `Emenda`, não `Adendo` — o gate não reconhece "Adendo").

## PR 4 — sweep agendado de bypass (herdado da Onda 0)

A Onda 0 entregou o braço `push: main` do `merge-audit` e **adiou este** por
bootstrap: workflow com `schedule:` precisa de entrada no manifesto (S0) e que
o Actions já conheça o arquivo (S1), e ele só o conhece após o merge. Com
`merge-audit.yml` já em `main`, a trava caiu. Escopo:

- `schedule:` diário no `merge-audit.yml` + entrada no
  `.github/scheduled-workflows.yml` (`max_age_days: 3`) com `alerts:` para a
  label `merge-protection` — o que também resolve o aceite 6 da Onda 0, hoje
  inalcançável (a label da Issue de auditoria não é vigiada por ninguém).
- Comparação de `rulesets/{id}/history`: desabilitar o ruleset, mergear e
  reabilitar é bypass que **não** aparece em `rule-suites`. Sem esse braço a
  auditoria fecha a porta e deixa a janela — e o **KR-B** fica contável por
  uma janela que ele mesmo declara cega ([[ADR-415]] D4).
- **Pré-requisito de token, e é bloqueante:** `rule-suites` exige
  `Administration: read`, que o `GITHUB_TOKEN` **não pode receber** (a chave
  `permissions:` do Actions não tem esse escopo). Sem um token de admin, o
  sweep aborta com `rc=2` por desenho — correto, mas inerte. Decidir junto ao
  item 2.0 (Organization): se o repo migrar, reavaliar a credencial ali.

Aceite: falha forçada (remover o token) ⇒ `rc=2` e nenhuma contagem impressa;
com token, o sweep lista os bypasses do período e a Issue acumula.

## PR 5 — gate visual obrigatório por paths-filter, sozinho

Roteado pela [[A40.l103]] (#1859), que mediu o custo e o achou **zero**. Hoje
`frontend-visual` é opt-in pela label `visual`: PR que toca o renderer e não
recebe a label mergeia sem nenhum gate de pixel — e a label é aplicada à mão.

- Trocar o gatilho de **label** por **paths-filter** nos mesmos paths que já
  disparam `Frontend checks` (`frontend/**`), mantendo a label como override
  para forçar o job fora desses paths.
- **Custo medido, não estimado:** PR de relatório já paga ~6 min de `Frontend
  checks` no mesmo filtro; o visual leva **1m31s–2m23s** e roda em paralelo,
  terminando antes. O delta de wall-clock no caminho crítico é **zero**.
- **Viaja sozinho:** entra em `all-green.needs`, logo muda a função de veredito
  do gate — mesma regra que isola o PR 3.
- **Exige emenda datada à [[ADR-210]] §Camada 1** no mesmo PR (`amended_at` +
  blockquote de sinal; keyword `Emenda`, não `Adendo`): a premissa de custo que
  sustenta o opt-in ali é "~$4/mês no overage", e ela **caducou com o repo
  público** — mesma caducidade que a Onda 1 já reconhece para o waiver do
  nightly.
- **Ordem:** depois da `A40.l102` (truncagem da trilha). Tornar o gate
  obrigatório antes daquele fix faz todo PR de frontend carregar um vermelho
  conhecido.

Aceite por detecção: PR que toca `frontend/src/components/report/**` **sem** a
label dispara o job; mutação estrutural no renderer reprova o `all-green`.

## security-green (junto do PR 2 ou próprio)

- Job agregador `security-green` em `security.yml` (`if: always()`, aceita
  `skipped` — espelho exato do `all-green`) → adicionado como required
  context no Ruleset. `all-green` **não pode** ter `needs:` de outro workflow
  — é por isso que o agregador mora no próprio security.yml.
- `pip-audit` + `npm-audit-prod` passam a gatear de fato (hoje o cabeçalho
  afirma "bloqueia merge" e nada consome o resultado — exposição medida de
  até 28d entre CVE e consequência, em repo público de fintech).
- Trade-off aceito e documentado: CVE publicada upstream trava o repo até
  bump/waiver (runbook "Ignorar CVE em npm audit" já existe).
- `security` no manifesto: `max_issue_age_days` 21 → 7.
- Aceite por detecção: CVE sintética em dep de teste reprova o agregador;
  commit com segredo falso conhecido é barrado (critério G2 de
  [[PLAN-public-release]]).

## Religar o nightly — POR JOB (ação owner + acompanhamento)

Ordem: `main-smoke` → **7 runs verdes** → `lineage-eval` → pesados
(lighthouse/cross-browser/visual-full/backup-drill). Religar tudo de uma vez
reativa o gate fail-open do `lineage-eval` (produtor morto desde 06-15) e
pode travar merges no mesmo dia — o loop que já reincidiu (#638/#647).
Depois: **remover** (não renovar) o waiver do nightly no manifesto — a Onda 1
tira o objeto dele e a razão FinOps caducou ("544% do orçamento" num repo
público). KR-C fecha aqui; KR-G fecha quando o lineage-eval religado provar
por mutação que produtor morto ⇒ gate ≠ 0.

## Aceite do track

1. PR 1/2/3 mergeados **sem bypass**, na ordem, com PR 3 sozinho.
2. KR-A: 7 dias sem falso-vermelho de instrumento **e** contagem pareada ≥
   baseline (19 sinais verdadeiros em 08-05→08-21).
3. KR-F: falha forçada abre Issue em 9/9.
4. KR-D: security-green required + prova por detecção.
5. KR-C: 7 noites de main-smoke verdes; waiver removido do manifesto.
6. Mediana open→merge não regrediu (KR-H) — medir antes/depois em janela 14d.
7. PR 5: `frontend-visual` dispara por paths-filter sem label, com emenda
   datada na [[ADR-210]] §Camada 1 no mesmo PR.
