> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A40

Volta para [`00-INDEX`](../00-INDEX.md).

17 open · 5 in_progress · 3 blocked.

## Open (17)

- [[A40.l10]] — Ordem do plano com critério encodado + pendências acionáveis do dono · priority P1 · área produto · branch `a40-l10-pendencia-do-dono-e-ordem-do-plano`
- [[A40.l29]] — Editorial do ano de IF: dois anos concorrentes, eixo em quando em vez de quanto, e a faixa sem componente · priority P2 · área frontend/product-design/financial-planning · branch `a40-l29-editorial-do-ano-de-if`
- [[A40.l36]] — Double-count potencial na base da cascata fiscal da S8: pró-labore pode entrar duas vezes · priority P1 · área pipeline/financial-planning · branch `a40-l36-double-count-base-cascata-s8`
- [[A40.l37]] — A tabela de IR tem três fontes, e uma é hardcoded contra a ADR-135 · priority P2 · área pipeline · branch `a40-l37-tabela-de-ir-tres-fontes`
- [[A40.l46]] — Resíduos do bloco de identidade (perfil): baseline de print não provada + variant feature sem o DNA do mockup · priority P2 · área frontend · branch `a40-l46-residuos-perfil-identidade`
- [[A40.l48]] — Polaridade de comparação é fixa por métrica, mas cobertura de reserva não é monotônica no alvo · priority P2 · área pipeline · branch `a40-l48-polaridade-de-comparacao-nao-monotonica`
- [[A40.l49]] — Parecer: rótulo de evidência derivado do root do path, e dois guardrails que não podem disparar · priority P1 · área backend/llm · branch `a40-l49-parecer-rotulo-e-guardrails`
- [[A40.l50]] — Abertos da investigação de exposição cambial: inventário verificado do que não foi atacado · priority P1 · área report/pipeline/financial-planning · branch `a40-l50-abertos-exposicao-cambial`
- [[A40.l51]] — Follow-ups órfãos da A40.l43: o que o co-design achou na vizinhança e ninguém está atacando · priority P1 · área frontend/pipeline/financial-planning · branch `a40-l51-followups-orfaos`
- [[A40.l54]] — `hidden md:block` entrega ao papel a variante mobile: varredura dos call-sites e gate da classe (ADR-381 D1) · priority P2 · área frontend/report · branch `a40-l54-hidden-md-block-no-papel`
- [[A40.l55]] — Medida de linha no papel: prosa a 100–110 caracteres por linha no A4 · priority P3 · área frontend/report · branch `a40-l55-medida-de-linha-no-papel`
- [[A40.l56]] — A tabela fiscal de produção: a row é internamente inconsistente e nenhum golden a atravessa · priority P1 · área pipeline/db · branch `a40-l56-tabela-fiscal-de-producao`
- [[A40.l57]] — O parecer lê o contrato antigo do bloco PGBL: guardrail com predicado morto e âncora que resolve null · priority P2 · área llm/pipeline · branch `a40-l57-parecer-le-contrato-antigo-do-pgbl`
- [[A40.l59]] — A transição para `shipped` ganha gate: ship_pr no frontmatter e PR visível no _README · priority P2 · área docs · branch `a40-l59-gate-na-transicao-shipped`
- [[A40.l60]] — Conselho de seguro: cobertura recomendada sem ressalva fiduciária, e uma string que afirma invalidez sem fonte · priority P1 · área pipeline/frontend · branch `a40-l60-ressalva-e-separacao-do-conselho-de-seguro`
- [[A40.l62]] — ProtectionComputationSnapshotV1: fontes run-scoped e computabilidade por categoria · priority P1 · área backend/pipeline/persistence/financial-planning · branch `a40-l62-protection-computation-snapshot-v1`
- [[A40.l63]] — Conversão ME→BRL não registra proveniência: taxa hardcoded indistinguível de taxa real, e saldo BRL rotulado como USD · priority P1 · área pipeline/money · branch `a40-l63-conversao-me-brl-sem-proveniencia`

## In progress (5)

- [[A40.l25]] — Honestidade do cone de IF: precisão de exibição e sigma apresentado como premissa auditada · priority P1 · área pipeline/frontend/financial-planning · branch `a40-l25-honestidade-do-cone-if`
- [[A40.l33]] — Contraste de texto sobre tint da própria cor: fecha a classe e gateia por medição · priority P1 · área frontend/design-system/a11y · branch `a40-l33-contraste-texto-sobre-tint`
- [[A40.l39]] — Posição por instituição: o header '31/12' mente para 10 de 16 linhas — separar visão corrente da fiscal · priority P1 · área pipeline/frontend/financial-planning · branch `a40-l39-posicao-visoes-corrente-fiscal`
- [[A40.l41]] — Frescor cross-pool: posição stale de 2025-03 vale R$ 206k no bruto contra IRPF 31/12/2025 de R$ 2,4k · priority P1 · área pipeline/financial-planning · branch `a40-l41-frescor-cross-pool-fonte-inteira`
- [[A40.l5]] — Codegen do view-model + gate de contrato: mata a classe reader-lê-chave-que-ninguém-emite · priority P1 · área frontend/dx · branch `a40-l5-contrato-view-model-gate`

## Blocked (3)

_Não pegáveis. Listadas porque `blocked` que fica stale some daqui justamente quando a dependência ship e a lane vira pegável._

- [[A40.l35]] — Bundle de proteção sobre insumos reais: a S9 calcularia cobertura e ITCMD sobre zeros · priority P1 · área backend/frontend/financial-planning · ⛔ dep pendente: A40.l62 (open) · branch `a40-l35-bundle-de-protecao-sobre-insumos-reais`
- [[A40.l58]] — schema_validation warn → strict: o PR5 que a l5 declarou como outra lane · priority P2 · área pipeline · ⛔ dep pendente: A40.l5 (in_progress) · branch `a40-l58-flip-do-schema-para-strict`
- [[A40.l64]] — Redutor da Lei 15.270/2025 e IRPFM: a economia diferencial de PGBL está errada para AC2026 em diante · priority P1 · área pipeline/financial-planning · ⛔ dep pendente: A40.l56 (open) · branch `a40-l64-redutor-lei-15270-e-irpfm`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
>
> **Este arquivo não vê ocupação.** Ele deriva do frontmatter, que ninguém
> escreve no pickup: sessão que abriu worktree e ainda não commitou é
> invisível aqui, em `git for-each-ref` e em `gh pr list`. Antes de pegar
> qualquer lane abaixo, rode `python3 dev/lane_pickup.py <id>`.
