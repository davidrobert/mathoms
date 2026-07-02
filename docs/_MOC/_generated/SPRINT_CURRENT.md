> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A26

Volta para [`00-INDEX`](../00-INDEX.md).

Nenhuma lane prontidão atual.

## Todas as lanes da sprint (para inspeção)

### blocked (3)

- [[A26.l2]] — Flip evidencia_path warn→strict (gate de segurança binário + budget de needs_review) · priority P1 · branch `evidencia-flip-strict`
- [[A26.l4]] — Override v2 ON no default + instrumentação do gate (v2_match_count + query agendada) · priority P2 · branch `override-v2-on-instrumentacao`
- [[A26.l5]] — M2-B — drop destrutivo do estado legado de identidade do override (Fase E) · priority P2 · branch `m2-override-drop`

### shipped (6)

- [[A26.l1]] — Fix de citação do evidencia_path — catálogo de paths disponíveis + eval golden LLM · priority P1 · branch `evidencia-prompt-catalogo`
- [[A26.l3]] — M2-A — drop do shim v1 do dedup (compute_transaction_hash) · priority P2 · branch `drop-dedup-v1-shim`
- [[A26.l6]] — Telemetria de citação: cobertura (missing_path) vs. correção (value_mismatch) + drift · priority P1 · branch `evidencia-coverage-kpi`
- [[A26.l7]] — Catálogo de citação cobre folhas de LISTA (fonte única forward↔reverse) · priority P1 · branch `evidencia-catalog-listas`
- [[A26.l8]] — value_mismatch residual: enforcement per-item no strict (path válido, número errado) · priority P1 · branch `evidencia-value-mismatch`
- [[A26.l9]] — citação determinística: renderizar valor R$ da folha (path) — value_mismatch → 0 estrutural · priority P1 · branch `citacao-deterministica`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
