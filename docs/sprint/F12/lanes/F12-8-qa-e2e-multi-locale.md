---
id: F12.8
type: lane
title: "QA + E2E multi-locale"
sprint: F12
status: blocked
priority: P0
adrs: ["[[ADR-130]]"]
depends_on: ["[[F12.2]]", "[[F12.3]]", "[[F12.4]]", "[[F12.5]]", "[[F12.6]]"]
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/blocked
  - priority/p0
---


# F12.8 — QA + E2E multi-locale


> 🚧 **Blocked-by-gate.** Aguarda gatilho de §10 do
> [plan/I18N/_README.md](../../../plan/I18N/_README.md) E depende de
> F12.2/F12.3/F12.4/F12.5/F12.6 mergeadas. Escopo: 3 locales (pt-BR +
> en + es). (Frontmatter anterior `status: shipped` era incorreto —
> tasks nunca iniciaram; corrigido em 2026-05-15.)

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.8a | Playwright matrix: fluxos `@critical` (5) × 3 locales = 15 runs paralelos. CI < 10min. | P0 | 4h | ⏳ |
| F12.8b | Visual regression do relatório nos 3 locales; PDF export (`pdf_renderer.py`) renderiza locale correto via cookie. Regressão `do_not_translate`: teste E2E carrega relatório em EN/ES e confere que ~25 termos do bucket aparecem intactos no DOM. | P0 | 4h | ⏳ |
| F12.8c | Atualizar [SMOKE_TEST_HUMAN.md](../../../reference/SMOKE_TEST_HUMAN.md) com checklist troca de idioma (3 fluxos × 3 locales). | P1 | 2h | ⏳ |

**Checkpoint F12 (após gate destravar + lanes acima fecharem):**
usuário escolhe um dos 3 idiomas (pt-BR/en/es) em
`/settings/preferences`; preferência persiste após logout (DB + JWT
claim); relatório React/PDF renderiza corretamente nos 3 locales;
plurais corretos via ICU; locales não-revisados marcam banner "beta";
banner "Brazilian fiscal residency assumed" aparece em EN/ES nas
seções tributárias.

**Estimativa total** (após gate destravar): ~71h engenharia + ~10h
revisão humana externa ≈ **~81h** com 1 agente em série; **~2,5
semanas** com 2 agentes em paralelo nas fases independentes.

**Dependências:**
- F12.1 (a–e) ✅ — fundação completa contra lista revisada (commit
  `94cf939`).
- Cleanup 2026-05-15 ✅ — reduz fundação para 3 locales (este PR).
- **GATE §10** — bloqueia F12.2–F12.6 + F12.8 até demanda objetiva.
- F12.2/F12.3/F12.4/F12.5 paralelizáveis (próxima onda após gate).
- F12.6 depende de F12.2 + F12.4.
- F12.7 (RTL) cancelado — fora do escopo F12.
- F12.8 depende de tudo acima.
