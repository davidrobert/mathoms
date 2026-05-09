# `docs/_marketing/` — drafts de copy comercial gated

> Diretório materializado em PR-C da Fase 4.B do plano
> [[PLAN-competitive-pierre]]. Nasce gated pela auditoria automática
> §13.3 do [COPY_GUIDELINES](../reference/COPY_GUIDELINES.md).

## Propósito

Hospedar **rascunhos** de copy pública (landing `mathoms.ai`, e-mails
transacionais, comparativos competitivos, materiais de imprensa, pitch
decks em formato Markdown) **antes** da publicação. Cada draft fica aqui
até que um PR de publicação (ex.: PR-D da Fase 4.B) materialize o
conteúdo na surface real (componente React, template de e-mail, página
de landing) sob ADR de gate.

**Nada aqui é publicado automaticamente.** A presença do arquivo
sinaliza intenção e versiona a copy proposta — não dispara render para
o usuário final. A propagação para `frontend/src/app/`,
`backend/app/services/email/` ou para a infra da landing acontece em PR
separado, com revisão de `product-designer` e CEO sign-off.

## O que vive aqui

| Tipo de draft | Quando criar | Quem revisa |
| --- | --- | --- |
| Landing copy (hero + seções) | Fase 4.B / refresh narrativo | `product-designer` + `gtm-strategist` (sigilo) |
| Comparativo competitivo (factual, não-atacante) | Fase 4.E após Fase 2/3 beta | `gtm-strategist` + CEO |
| Templates de e-mail transacional | Quando `backend/app/services/email/` for materializado | `product-designer` + `financial-planner` |
| Pitch / one-pager para investidor ou parceiro | On-demand, mas anônimo público (sem menção a fontes metodológicas) | CEO + `gtm-strategist` |

Subdiretórios são bem-vindos quando o volume crescer (ex.:
`landing/`, `email/`, `comparatives/`). Mantenha um draft por arquivo
e use sufixo `-vN` para iterações (`landing-copy-draft-v2.md`).

## Política de sigilo (regra absoluta)

- Esta surface é **user-facing** para o §13 do
  [COPY_GUIDELINES](../reference/COPY_GUIDELINES.md). Atribuição direta a
  fontes metodológicas em copy renderizada é **proibida**.
- O hook `sigilo-terms`
  ([dev/check_sigilo_terms.py](../../dev/check_sigilo_terms.py)) cobre
  `docs/_marketing/**/*.md` desde PR-C da Fase 4.B (2026-05-09).
  Mesmo gate em CI via `Lint (pre-commit + …)`.
- Use o vocabulário canônico de §13.2 e — quando a copy referenciar
  posicionamento de marca — a tabela §"Decisão" de [[ADR-183]].
- Comentários HTML (`<!-- … -->`) e fenced code blocks (``` … ```)
  ficam fora do scan: atribuição interna em nota editorial é tolerada
  (§13.4). Inline code (`` `…` ``) **é escaneado** — não use para
  esconder atribuição.
- Este `_README.md` é **excluído** do hook (descritivo interno —
  registrado em `EXCLUDED_FILES` do script).

## Como contribuir

1. Crie o draft em `docs/_marketing/<slug>.md` seguindo formato dos
   drafts existentes (frontmatter mínimo opcional, `Out of scope`
   explícito ao final).
2. Rode `python3 dev/check_sigilo_terms.py docs/_marketing/<slug>.md`
   antes de commitar — exit 0 obrigatório.
3. Abra PR contra `main` referenciando a ADR de posicionamento que o
   draft ancora (ex.: [[ADR-183]] para landing).
4. PR de publicação (push para landing / e-mail / etc.) é separado e
   pode aguardar gates adicionais (Fase 2/3 beta, ADR de pricing
   etc.).

## Onde isso entra no plano canônico

Esta diretório é o entregável-suporte do PR-C da
[[PLAN-competitive-pierre]] §3 Fase 4.B. ADR pai:
[[ADR-183]] (pilares narrativos da landing). Track de execução:
[gtm-landing-copy-rewrite](../sprint/A11/tracks/gtm-landing-copy-rewrite.md).
