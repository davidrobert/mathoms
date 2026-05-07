---
id: F12.8
type: lane
title: "QA + E2E multi-locale"
sprint: F12
status: shipped
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/shipped
  - priority/p0
---


# F12.8 — QA + E2E multi-locale


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.8a | Playwright matrix: fluxos `@critical` (5) × 10 locales = 50 runs paralelos. CI < 20min. | P0 | 4h | ⏳ |
| F12.8b | Visual regression do relatório nos 10 locales; PDF export (`pdf_renderer.py`) renderiza locale correto via cookie. | P0 | 4h | ⏳ |
| F12.8c | Atualizar [SMOKE_TEST.md](SMOKE_TEST.md) com checklist troca de idioma (3 fluxos × 10 locales). | P1 | 2h | ⏳ |

**Checkpoint F12:** usuário escolhe um dos 10 idiomas em
`/settings/preferences`; preferência persiste após logout (DB + JWT
claim); relatório React/PDF renderiza corretamente nos 10 locales;
CJK (zh-CN/ja/ko) carrega fonte secundária sob demanda; plurais
corretos via ICU; locales não-revisados marcam banner "beta".

**Estimativa total:** ~144h engenharia + ~45h revisão humana externa
≈ **~189h** com 1 agente em série (inclui F12.1e correção, 4h);
**~5 semanas** com 2 agentes em paralelo nas fases independentes.

**Dependências:**
- F12.1 (a–e) ✅ — fundação completa contra lista revisada de 10
  locales (commit `94cf939`).
- F12.2/F12.3/F12.4/F12.5 paralelizáveis (próxima onda).
- F12.6 depende de F12.2 + F12.4.
- F12.7 (RTL) fora do escopo F12 atual.
- F12.8 depende de tudo acima.

---
