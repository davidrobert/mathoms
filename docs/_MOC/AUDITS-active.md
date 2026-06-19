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
| **DAT-01, DAT-02, REL-02, DAT-05** | — | refutado (#671) | refutado · **não reverificado** | #671 §"NÃO incluídos" 🔎 |

**⚠️ SEC-03 — lição de processo.** A validação manual de #671 colocou SEC-03 no
balde "CVEs Python… refutados ou já endereçados (versões já patched)". Estava
**errado**: `pip-audit` (2026-06-19) confirmou 17 CVEs reais com fix acima da
versão pinada. Reaberto e fechado em #676 / [[ADR-299]]. Validar CVE **sempre**
com `pip-audit` contra o lock — leitura manual de "versão X já é segura" decai
conforme novas CVEs são divulgadas.

**🔎 DAT-01/02, REL-02, DAT-05 — candidatos a reverificação.** Foram refutados
**no mesmo passo de validação que errou o SEC-03** (#671 §"NÃO incluídos"). Como
o relatório original sumiu, não há detalhe para re-litigar aqui, mas a refutação
desse balde perdeu credibilidade. **Recomendação:** reverificar com a mesma
disciplina empírica (DAT-* → `data-engineer`; REL-02 → `sre-devops`). Sem owner
atribuído — decisão do owner do repo se vira `procede-aberto` (com gatilho de
BACKLOG) ou se confirma `refutado` com evidência.
