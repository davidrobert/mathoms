---
id: CHG-2026-05-29-ADR-238-DATA-ADESAO-NAO-HARDFAIL
type: changelog-entry
date: "2026-05-29"
sprint: A20
adrs: ["[[ADR-238]]"]
prs: [512]
commits: ["1c4fbe0d"]
breaking: false
summary: |
  fix(adr-238): data_adesao deixa de ser hard-fail em previdência regressiva.
  Incidente dogfood — stage extract_informes_anuais abortava (193.5s, 4 retries)
  em informe regressivo real porque um model_validator exigia data_adesao,
  insumo de cálculo PEPS que é V2 e não existe no código. Removido o hard-fail;
  regressivo sem data → needs_review + nota (saldo preservado); prompt bumpado
  v1.0.0 → v1.1.0.
tags:
  - type/changelog-entry
  - sprint/a20
  - status/shipped
  - status/decidido
  - area/pipeline
  - area/methodology
---

# fix(adr-238): data_adesao não é hard-fail em previdência regressiva

## Sumário

[[ADR-238]] corrigida em 1 PR squash-mergeado em `main` (CI verde — "All checks green" + Backend tests):

- [#512](https://github.com/davidrobert/mathoms/pull/512) (`1c4fbe0d`) — remoção do `model_validator` de hard-fail em `InformePrevidenciaPayload` + degradação graciosa `_flag_regressivo_sem_adesao` em `extract_informes_anuais.py` + prompt `informe-prev-v1.0.0 → v1.1.0` + seção de correção na ADR-238 + 5 testes (3 stage + conversão do teste de schema).

## Problema (incidente dogfood 2026-05-29)

A etapa `extract_informes_anuais` rodou **193.5s** e abortou em um informe real de previdência regressivo:

```
Output validation failed after 4 attempts:
regime_tributacao=regressivo exige data_adesao (alíquota PEPS depende de anos_desde_adesao)
```

Um `model_validator` fazia **hard-fail** quando `regime_tributacao=regressivo` sem `data_adesao`. O informe não imprimia a data (comum em regressivos), o LLM retornava `null` corretamente, e o validator transformava o erro Pydantic em **retry** — o harness LLM tratou a falha como retentável e queimou **4 chamadas (~193s)** numa restrição insatisfazível, perdendo o informe inteiro (`saldo_31_12` = patrimônio + IRPF código 97).

## Decisão (resumo)

O guard protegia um consumidor **inexistente**: o cálculo de alíquota regressiva PEPS (`anos_desde_adesao`) é **V2** (ver Não-objetivos da ADR-238). Falso-positivo (patrimônio que some, silencioso) é pior que falso-negativo (alíquota imprecisa, visível e deferida).

- Removido o `model_validator` de hard-fail. `data_adesao` permanece `Optional[str]`.
- Regressivo sem `data_adesao` → **degradação graciosa**: `needs_review=true` + nota; saldo preservado.
- Prompt `v1.0.0 → v1.1.0`: removido "OBRIGATÓRIO quando regressivo" (induzia alucinação); reforçado anti-alucinação ("`null` + `needs_review` é a resposta CORRETA"). Bump invalida cache idempotente ([[ADR-144]]).
- Follow-up: eval golden live-LLM Classe A (com data → recall) / Classe B (sem data → precision), 100% sintético, fora do gate determinístico de CI.

Endossado por `financial-planner` + `prompt-engineer`.

## Nota de operação

Auto-merge do GitHub mergeou main na branch via GITHUB_TOKEN, cujo commit **não dispara workflows** (proteção anti-recursão) — o novo head ficava sem checks e `BLOCKED` permanentemente. Resolvido com rebase sobre `origin/main` + force-push, que re-disparou o CI normalmente.
