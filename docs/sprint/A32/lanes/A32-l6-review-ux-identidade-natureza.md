---
id: A32.l6
type: lane
title: "review UX: identidade legível + selo de natureza + copy sem contradição + agrupamento por documento"
sprint: A32
plan: null
status: shipped
ship_pr: 845
ship_date: "2026-07-08"
priority: P1
branch_slug: a32-l6-review-ux-provenance
adrs: []
depends_on: ["[[A32.l2]]", "[[A32.l3]]", "[[A32.l4]]", "[[A32.l5]]"]
parallel_with: []
tags:
  - type/lane
  - sprint/a32
  - status/shipped
  - priority/p1
  - area/frontend
  - area/ux
---

# A32.l6 — `review-ux-provenance` (a tela diz de quem é o erro)

## Problema

O owner não conseguiu distinguir "meu dado está errado" de "o produto leu
errado" — a função da tela. Cards atuais: título técnico + lista de
artifact_keys com prefixo hash (ilegível) + valor ofensor cru
(`banco=''`, datas ISO) ao lado de um filename que **contém** o banco —
contradição interna exposta ao usuário. Sem ação por item. Na run
dogfood, 100% dos 18 errors eram defeito do produto apresentados como
problema do dado do usuário.

## Escopo (3 PRs sequenciais, mergeáveis independentemente — PM)

**PR1 — projeção backend + identidade legível (núcleo; mata a
contradição-mor).** Premissa verificada (não condicional): `document_id`
NÃO chega hoje ao frontend —
`frontend/src/lib/api/pipeline.ts::ValidationIssue.context` e
`frontend/src/generated/` não o expõem, embora
`SaldoGapWarning.to_review_reason`
(`reconciliation_validators.py:118-135`) aceite o campo no domínio.
Threading: projeção `ReviewReason → ValidationIssueDTO.context` no
backend (`response_model` + `make update-openapi-snapshot` + commit do
diff, ADR-109) **vem primeiro**, senão os PRs de frontend ficam
bloqueados. No frontend: `document_id/content_hash →
documentDisplayLabel` (`frontend/src/lib/documentTypeLabels.ts:54`) no
topo de cada ocorrência em `ValidationErrorsPanel.tsx`, substituindo
`occurrenceLabel`; artifact_key/hash cru só sob "Detalhes técnicos";
fallback gracioso para reasons cross-doc com `artifact_key=''` (grupo
"Sequência de contas").

**PR2 — taxonomia de natureza + copy.** Mapa declarativo code→natureza
com 3 selos forma+ícone+rótulo (WCAG: nunca só cor; tokens semânticos
existentes, sem token novo): "Problema no seu documento" / "Falha na
nossa leitura" (hedge "provavelmente" quando incerto) / "Documento
faltando". Decisão Q4 do owner: selo na review principal, **sem aba
separada** — warnings não-bloqueantes ficam com selo rebaixando os
prováveis-nossos. Rewrite de `REVIEW_REASON_COPY`
(`frontend/src/lib/validation-copy.registry.ts:342-403`): nunca afirmar
desconhecer fato que o sistema tem no DB (caso `banco=''` ao lado do
nome do banco); quando o defeito é nosso (P1/P2), a copy assume;
`offending_value` cru sempre traduzido.

**PR3 — agrupamento por documento + ações MVP (pode deslizar para a
sprint seguinte sem invalidar o KR3 no eixo principal).** Agrupamento
por `document_id` como visão default (render-side em `review-groups.ts`
— NÃO muda granularidade de `StageReview`/contrato backend), colapsando
cascatas do mesmo doc em 1 card; visão por-code vira filtro. Ações MVP:
"Ver documento" + "Dispensar". Botão "Reprocessar" NÃO entra (dead UI
proibida) — a lane apenas ESPECIFICA o contrato do endpoint (doc anexo
ao plano, sem impl; decisão Q3).

Co-design: `product-designer` (visual/copy) já consultado no painel
2026-07-07; sem doc canônico novo (sem `information-architect`).

## Critérios de aceite

1. Zero hash sha256 cru no corpo visível de qualquer card; todo card com
   `document_id` mostra "Instituição · Tipo · Período" legível.
2. Cada um dos 6 codes E3 tem natureza atribuída; teste de contradição
   passa (nenhum card nega fato presente no DB).
3. Run de 49 itens colapsa para a contagem real de documentos-fonte;
   1 doc órfão com 3 codes = 1 card, 1 decisão.
4. Distinção de natureza legível sem cor (verificação
   daltônico/screen-reader); `npm test -- --run` + E2E `@critical`
   verdes; snapshot OpenAPI commitado (PR1).
5. Spec do contrato "reprocessar documento" anexada
   (`docs/sprint/A32/assets/` ou seção no plano da sprint seguinte).
6. PRs mergeados em `main` com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `frontend/src/app/(app)/pipeline/runs/[runId]/reviews/_components/ValidationErrorsPanel.tsx` | Card de review a redesenhar |
| `frontend/src/lib/validation-copy.registry.ts:342-403` | Copy registry a reescrever |
| `frontend/src/lib/documentTypeLabels.ts:54` | `documentDisplayLabel` existente a reusar |
| `frontend/src/lib/api/pipeline.ts` | `ValidationIssue.context` — onde falta `document_id` |
| `pipeline/domain/services/reconciliation_validators.py:118-135` | Origem do `document_id` no domínio |
