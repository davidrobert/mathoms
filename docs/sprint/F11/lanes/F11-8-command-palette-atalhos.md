---
id: F11.8
type: lane
title: "Command palette / atalhos"
sprint: F11
status: shipped
priority: P2
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f11
  - status/shipped
  - priority/p2
---


# F11.8 — Command palette / atalhos


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.8a | **Command palette** (`cmdk` ou lib alinhada ao DS): buscar páginas, ir para Documentos, Pipeline, Relatórios, Config, Plano. | P2 | 10h | ✅ `CommandPalette.tsx` + `cmdk` |
| F11.8b | **Atalhos globais** documentados (modal `?` ou página ajuda): ex. `G` + letra para navegação, evitando conflito com inputs. | P2 | 6h | ✅ Modal **?** (fora de inputs) + **⌘K** / Ctrl+K |
| F11.8c | **A11y:** palette focável por teclado, `aria` em resultados. | P2 | 3h | ✅ `Command` label + lista cmdk (refinar com auditoria dedicada) |

**Checkpoint F11:** usuário entende **de onde vem** o número; sabe quando **confiar** no dado vs revisar; relatório **impresso/PDF** passa checklist de consultoria; navegação separa **plano de vida** de **fechamento do mês**; hierarquia tipográfica consistente; command palette opcional para power users.

---
