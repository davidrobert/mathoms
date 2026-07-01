---
type: moc
title: AUDITS-active — Rastreamento de auditorias de repositório
aliases: ["AUDITS", "AUDITS-active", "audit-tracking"]
---

# AUDITS-active — Rastreamento de auditorias

> **Editorial.** Curado manualmente — **não é gerado**. Um gerador baseado em
> frontmatter de ADR só veria itens que viraram ADR; o valor deste índice é
> capturar **todos** os achados — inclusive os que viraram só commit, os
> refutados e os não-acionáveis. Uma seção por auditoria; seções de auditorias
> 100% fechadas viram histórico aqui mesmo (não se arquiva linha a linha).

## Convenção de rastreamento (timeless)

Para que nenhum achado se perca entre auditorias:

1. **Cobertura 100%.** Toda auditoria gera uma seção abaixo cobrindo **todos**
   os achados — inclusive refutados e não-acionáveis. Triagem só é considerada
   completa quando todo item tem disposição registrada.
2. **ADR para o que tem peso de decisão.** Item que procede e altera
   decisão/invariante/dependência entra em ADR de veredito (1 ADR pode cobrir N
   itens correlatos — ex.: [[ADR-298]]). Refutado/não-acionável basta neste
   índice com 1-2 linhas de rationale + link à evidência. **Não** se exige "1 ADR
   por item".
3. **Aberto exige gatilho.** Item `procede-aberto` **deve** ter prioridade
   (P0-P2) + owner + link para linha de BACKLOG ou ADR `Proposto`. `procede-aberto`
   sem gatilho de execução é bug deste índice.
4. **Cadência.** Ao abrir auditoria nova, revise a seção da anterior: todo
   `procede-aberto` que persiste é re-priorizado ou rebaixado a `aceito-wontfix`
   com rationale. Sem zumbis silenciosos.

**Taxonomia de disposição:** `procede-fechado` · `procede-aberto` · `refutado`
· `não-acionável` · `aceito-wontfix`.

---

## r2 — `repo-audit-mathoms.ai-2026-06-11-r2`

> Relatório original efêmero (externo, não versionado). Esta seção foi
> **reconstruída** da trilha verificável: ADRs `phase: audit-r2`, corpo dos
> commits [#671](https://github.com/davidrobert/mathoms/pull/671) /
> [#676](https://github.com/davidrobert/mathoms/pull/676) e
> [#668](https://github.com/davidrobert/mathoms/pull/668). Códigos/severidades
> originais preservados onde recuperáveis.

| Código | Sev. orig. | Veredito | Disposição | Trilha |
|---|---|---|---|---|
| **SEC-03** | HIGH/CRIT | procede | procede-fechado | [[ADR-299]] · #676 (bump 4 deps; pip-audit 17→0) ⚠️ |
| **REL-03** | Médio→P1 | procede | procede-fechado | [[ADR-297]] · #671 (idempotência de Report) |
| **P0-4 / SEC-06** | P0 | procede | procede-fechado | #671 (fail-fast FERNET_KEY em prod; sem ADR) |
| **QUA-05** | Médio | procede | procede-fechado | #671 (detector P7 isenta docstring de módulo; sem ADR) |
| **QUA-04 / ARQ-01** | Baixo | procede | procede-fechado | #671 (slogan money do CLAUDE.md ↔ ADR-090; docs) |
| **MAT-01 / DAT-06** | — | procede | procede-fechado | #668 (flip ADR-241/242/243 → Decidido) |
| **item 6** — nota Qual. 4→3 | — | não-acionável | não-acionável | [[ADR-298]] D1 (recalibração de avaliador, não regressão) |
| **item 6** — "backend limpo, dívida no pipeline" | — | refutado | refutado | [[ADR-298]] D2 (medição: backend tem a maior fatia) |
| **item 6** — ratchet "sem metas decrescentes" | — | procede | procede-fechado | [[ADR-298]] D1 (política documentada; já decresce) |
| **DAT-01** (float monetário, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | data-engineer: ADR-283 shipou (Numeric(18,2), `check_float_money --scan-models`+hook, drop monthly_cap) |
| **DAT-02** (contrato schema warn/strict, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | data-engineer: e2 `additionalProperties:false`+gate; flip strict é lane de telemetria consciente (ADR-283) |
| **DAT-05** (PII/retenção/erasure, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | data-engineer: ADR-231 (crypto wired) + ADR-275 (retenção+erasure cascade FK fim-a-fim) Decididos |
| **REL-02** (idempotência pós-run, reconstr.) | — | refutado | refutado · **reverificado** 2026-06-30 | sre-devops: guarda terminal ADR-297 ([`pipeline_task.py:757,527`](../../backend/app/tasks/pipeline_task.py)) cobre TODO o pós-processamento, não só Report; demais tasks idempotentes |
| **REL-02b** (latente) — `TaskSuggestion.dedup_key` sem UC | P3 | procede | aceito-wontfix | sre-devops: inalcançável sob `reject_on_worker_lost`+`prefetch=1`; **gatilho:** reabrir P2 se `prefetch>1`/redelivery concorrente ([`task.py:242`](../../backend/app/models/task.py)) |
| **r2-new-1** — ADR-095 status stale | P2 | procede | procede-fechado | data-engineer: 095 `Proposto` mas D1/D2→ADR-231, D3/D4→ADR-275 shipados; banner + `relates_to [[ADR-231]]` adicionado nesta rodada |
| **r2-new-2** — LGPD export cobertura parcial | P2 | procede | **procede-aberto** (owner) | data-engineer: `lgpd_export_service.py` não exporta Debt/PropertyIdentity/Vehicle/Protection/Risk/TransactionOverride; **owner decide** se é escolha consciente de Art.18 → `aceito-wontfix`, senão P2 real |

**⚠️ SEC-03 — lição de processo.** A validação manual de #671 colocou SEC-03 no
balde "CVEs Python… refutados ou já endereçados (versões já patched)". Estava
**errado**: `pip-audit` (2026-06-19) confirmou 17 CVEs reais com fix acima da
versão pinada. Reaberto e fechado em #676 / [[ADR-299]]. Validar CVE **sempre**
com `pip-audit` contra o lock — leitura manual de "versão X já é segura" decai
conforme novas CVEs são divulgadas.

**✅ DAT-01/02, REL-02, DAT-05 — reverificação concluída (2026-06-30).** O balde
foi reverificado com disciplina empírica (`data-engineer` p/ DAT-*, `sre-devops` p/
REL-02), exatamente porque fora refutado no mesmo passo que errou o SEC-03. **Resultado:
diferente do SEC-03, a refutação RESISTIU** — cada decisão das ADRs correlatas foi
confirmada *shipada no código* (não só lida na ADR): float monetário (ADR-283 +
gate scan), `additionalProperties` (e2 + gate), criptografia/retenção/erasure
(ADR-231/275 + cascade FK fim-a-fim), e a guarda terminal da ADR-297 cobrindo todo
o pós-processamento. O relatório original é efêmero, então os códigos foram
*reconstruídos* (rótulos exatos perdidos) e a superfície re-auditada do zero. A
re-auditoria fresca levantou **2 achados novos** (r2-new-1 ADR-095 stale, fechado
nesta rodada; r2-new-2 LGPD export parcial, `procede-aberto` p/ decisão do owner)
+ 1 latente (REL-02b, aceito-wontfix com gatilho). Lição SEC-03 aplicada: nenhuma
refutação aceita sem evidência empírica de que o fix existe no código.
