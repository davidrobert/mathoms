> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A38

Volta para [`00-INDEX`](../00-INDEX.md).

10 open.

## Open (10)

- [[A38.l1]] — Harness local de certificação de parse (classify→route→parse, métricas mascaradas) · priority P0 · branch `a38-l1-certify-parse-harness`
- [[A38.l10]] — TypeRules genéricas de fatura nunca cruzam linha (gaps `.{0,N}` sem re.DOTALL) · priority P2 · branch `a38-l10-typerule-fatura-dotall`
- [[A38.l11]] — Fuzzy-dupe cruza-flagga extratos de moedas distintas do mesmo período (Wise USD × BRL) · priority P2 · branch `a38-l11-fuzzy-dupe-moeda`
- [[A38.l2]] — parse_itau perde ~50% das transações do layout 2026 do extrato PDF · priority P0 · branch `a38-l2-parse-itau-layout-2026`
- [[A38.l3]] — Gate anti-silêncio no E2: 0 tx ou conservação quebrada nunca vira artefato 'ok' (ADR Proposto) · priority P0 · branch `a38-l3-gate-anti-silencio-e2`
- [[A38.l4]] — Colisão de instituição: pattern caixa `0800 726` casa SAC Santander com conf 1.0 · priority P1 · branch `a38-l4-colisao-instituicao-0800726`
- [[A38.l5]] — TypeRule cdbdetalhes rouba extrato de conta com `\bCDB\b` na descrição de transação · priority P1 · branch `a38-l5-typerule-cdbdetalhes`
- [[A38.l6]] — Wise: moeda decidida por filename (USD vira BRL sem LLM) + período range por extenso · priority P1 · branch `a38-l6-wise-moeda-conteudo`
- [[A38.l7]] — Fatura Santander Unique layout 2026: classificação conf 0.0 + parser sem total/vencimento · priority P1 · branch `a38-l7-faturaunique-layout-2026`
- [[A38.l9]] — Fatura Itaú Visa/Itaucard sem parser determinístico (100% E2-llm; 1 PDF com texto sem espaços) · priority P2 · branch `a38-l9-fatura-itau-visa-parser`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
