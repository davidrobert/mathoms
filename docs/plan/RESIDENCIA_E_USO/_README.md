---
id: PLAN-residencia-e-uso
type: plan
title: "Residência e uso econômico de imóveis — override DB substitui keyword"
status: draft
sprint_origem: A12
sprint_atual: A12
sprints_envolvidas: ["A12"]
created_at: "2026-05-15"
last_review: "2026-05-15"
adrs_canonical:
  - "[[ADR-215]]"
tags:
  - type/plan
  - area/methodology
  - area/pipeline
  - area/persistence
  - area/report
  - sprint/a12
  - status/draft
---

# Plano canônico — Residência e uso econômico de imóveis

> Plano multi-fase para substituir `family_members.<titular>.extra.residencia_principal_keyword` por **classificação por imóvel** (`enum classification`) materializada em `workspace_property_overrides` (DB-first), com extração de endereço do contribuinte no IRPF como signal de pré-seleção heurística. Decisão arquitetural em [[ADR-215]].

## Origem

Sessão 2026-05-15 — usuário (CEO, workspace dogfood `5@5.com`) abriu o relatório e identificou linha "Residência" zerada na "Composição Patrimonial", apesar do IRPF dele declarar 1 casa código 12 (RUA TASSO DA SILVEIRA, 61 — R$ 996.821) + 4 apartamentos código 11. Investigação revelou:

1. **Sem UI** para `residencia_principal_keyword` — só Import/Export JSON ou SQL direto.
2. **Acoplamento errado** — keyword fica em `family_members.<titular>.extra` mas residência é da família.
3. **Modelo binário insuficiente** — não cobre terreno improdutivo, imóvel ocupado por familiar, sala comercial vaga.

Co-design 2026-05-15 com `financial-planner` (taxonomia metodológica + invariante anti-dupla-contagem em IF), `product-designer` (UX pós-upload IRPF + estado tripartite `owned|rented|undeclared`) e `data-engineer` (schema DB + property identity + lazy split) produziu modelo consolidado em [[ADR-215]] com invariantes não-negociáveis:

1. **Override é sticky** — sobrevive a reprocessamento E1.5c (padrão [[ADR-186]]).
2. **Heurística nunca decide sozinha** — pré-seleção sempre exige confirmação humana.
3. **Endereço IRPF é signal, não verdade** — pode ser PJ, casa dos pais, corretora.
4. **`property_id` é UUID estável** com matching humano-no-loop em caso de ambiguidade, não hash determinístico.

## Objetivo

Após este plano, ao subir IRPF novo (ou abrir MembersTab em workspace dogfood), o usuário:

- Vê lista dos imóveis extraídos com **pré-seleção heurística** justificada (badge "sugerida pelo seu endereço no IRPF").
- Marca explicitamente residência principal **e** classificação econômica de cada imóvel (`residencia_principal | uso_pessoal | locado | comercial | especulacao`).
- Pode declarar "Moro alugado / não tenho residência própria" (estado `rented`).
- Override sobrevive a re-upload de IRPF subsequente — escolha sticky.
- Relatório "Composição Patrimonial" passa a separar cat_1 ("Residência") de cat_2 ("Imóveis de Renda" — rebatizada) com critério econômico verdadeiro.
- `imoveis_no_if=true` ([[ADR-142]]) deixa de contaminar `investivel_efetivo` com terreno improdutivo / imóvel de uso pessoal.

## Não-objetivos (MVP V1)

- **Imóvel financiado com saldo devedor:** modelagem de `valor_mercado` separado de `valor_irpf` + linkagem `saldo_financiamento` ao passivo correspondente. Follow-up em ADR futura ([[ADR-215]] §Follow-ups).
- **`imoveis_no_if` por workspace:** hoje global em `pipeline.json`; débito já catalogado em [[ADR-142]].
- **Sub-bucket "Patrimônio de uso (não-gerador)"** agregando uso_pessoal + especulacao + veículos no relatório. Decisão de UX a refinar pós-MVP.
- **ML/LLM para classificação automática:** heurística determinística (regex + token_set_ratio) + confirmação humana é suficiente.
- **CEP/IBGE geocoding** do endereço IRPF: gold standard fora do MVP; só se o feeling humano + fuzzy match não resolver os casos da base atual.

## Status executivo

- **ADR-215 Proposto** ✅ shipped 2026-05-15 (#278)
- **Plano draft** ✅ shipped 2026-05-15 (#278)
- **P1 Schema (E1.6 + DB)** ✅ shipped 2026-05-15 (#281, d63ecbe)
- **P2 Property Identity (E1.5c)** ✅ shipped 2026-05-15 (#286, f3a7748)
- **P3 Domain (lazy split + classifier)** ✅ shipped 2026-05-15 (#289, 73f590d)
- **P4 Backend API (overrides + heurística)** ✅ shipped 2026-05-15 (#291, ad7215e)
- **P5 UX MembersTab + esconde Residência R$ 0,00** ✅ shipped 2026-05-15 (#292)
- **P6 Cutover legado + pre-commit gate** 🚧 este PR
- **Quick fix paralelo:** descartado pelo usuário em favor da solução completa.

## Fases (MVP V1)

| Fase | Status | Entrega | Owner | Dependências | Esforço |
|---|---|---|---|---|---|
| **P1** | ⏳ | Schema E1.6 (`contribuinte.endereco`) + DB (tabelas `workspace_property_overrides` + `property_identity` + coluna `workspaces.residencia_status`) + migrations Alembic | data-engineer + senior-cto | ADR-215 ✅ | 3d eng |
| **P2** | ⏳ | Consolidador E1.5c emite `property_id` estável + dedup endereço normalizado em casal/comunhão + low-confidence flag | data-engineer | P1 ✅ | 2d eng |
| **P3** | ⏳ | `patrimonio_calculator.split_imoveis` puro/read-time + payload E5 com `property_id` + goldens E5 atualizados (paridade) + label cat_2 → "Imóveis de Renda" | senior-cto + data-engineer | P2 ✅ | 3d eng |
| **P4** | ⏳ | Endpoints: `GET /workspaces/{ws}/properties` (lista classificável com sugestão fuzzy) + `PUT /workspaces/{ws}/properties/{id}/classification` + `PUT /workspaces/{ws}/residencia-status` + telemetria mínima | senior-cto | P3 ✅ | 2d eng |
| **P5** | ⏳ | UX pós-upload do 1º IRPF (inline, não modal) + seção em MembersTab + tabela densa com radio + badge de sugestão + opção "Moro alugado" | frontend + product-designer | P4 ✅ | 3d eng |
| **P6** | ⏳ | Migration de cutover: matching de `residencia_principal_keyword` legado → override DB; deprecation + delete do campo legado; pre-commit gate impedindo re-uso | data-engineer + sre-devops | P5 ✅ + 1 sprint deprecation | 1d eng + 7d wall-clock |

**Total estimado MVP V1:** ~14d eng + 7d wall-clock cutover. Workspace dogfood `5@5.com` usado para validar P5 antes de habilitar feature flag globalmente.

### P1 — Schema E1.6 + DB

**Track:** `residencia-uso-p1-schema.md` (criar quando lane abrir)

Entrega:

- Pipeline:
  - `config/schemas/e16_irpf_full.schema.json` — campo aditivo opcional `contribuinte.endereco: string|null`.
  - `pipeline/llm/schemas/e16_irpf_full.py` — `Contribuinte.endereco: Optional[str] = None`.
  - `pipeline/llm/prompts/e16_irpf_full.py` — prompt pede extração de "Dados do Contribuinte → endereço" explicitamente.
  - Goldens: `tests/fixtures/llm_golden/e16_irpf_full_completo.json` (com endereço) + novo `e16_irpf_full_sem_endereco.json` (lazy fallback).
- DB (Alembic):
  - Tabela `workspace_property_overrides` (id, workspace_id, property_id, classification, override_source, created_at, updated_at, created_by_user_id) com unique `(workspace_id, property_id)` e partial unique `(workspace_id) WHERE classification='residencia_principal'`.
  - Tabela `property_identity` (id, workspace_id, titular_key, codigo_rfb, endereco_canonical, first_seen_year, descricao_sample, created_at).
  - Coluna `workspaces.residencia_status VARCHAR(20) NOT NULL DEFAULT 'undeclared'` com CHECK constraint.
  - Models SQLAlchemy + repos.

**Gate de saída:** Alembic up/down testado; golden duplo E1.6 verde; `make update-openapi-snapshot` rodado para DTOs novos; modo `warn` no schema validator do pipeline ([[ADR-212]]).

### P2 — Property identity (consolidador E1.5c)

**Track:** `residencia-uso-p2-property-identity.md`

Entrega:

- `scripts/e1_5c_consolidate.py` (ou consolidador equivalente): emite imóveis com `property_id` UUID.
- Função `match_property_identity(titular_key, codigo, descricao, descricao_normalizada) -> (property_id, confidence)`:
  - Normaliza descrição (lowercase, sem acento, expande `av/avenida` `r/rua`, remove `apto/ap`).
  - Regex extrai `(via, numero)` quando possível.
  - Busca match em `property_identity` por `(workspace_id, titular_key, codigo_rfb, endereco_canonical)`.
  - Match → reusa `property_id`. Sem match ou ambíguo → cria nova row + marca `low_confidence` para UI.
- Dedup em casal/comunhão: mesmo endereço canonicalizado em 2 titulares vira 1 `property_id` com `owner='familia'` (não-titular).
- Testes:
  - Golden de identidade cross-IRPF (2 IRPFs do mesmo workspace, mesmo imóvel descrito diferente em cada ano → mesmo `property_id`).
  - Golden de dedup casal (mesma residência declarada por ambos titulares).

**Gate de saída:** golden de paridade verde; audit em workspace dogfood mostra 100% dos imóveis com `property_id` estável após 2 reprocessamentos consecutivos.

### P3 — Domain (lazy split + classifier rename)

**Track:** `residencia-uso-p3-domain.md`

Entrega:

- `pipeline/domain/services/patrimonio_calculator.py`:
  - `split_imoveis(imoveis, overrides) -> CompositionSplit` torna-se função pura.
  - Calculator deixa de ler `residencia_principal_keyword`.
  - Cat_2 passa a filtrar por `classification ∈ {locado, comercial}` quando `imoveis_no_if=true` ([[ADR-142]]); `especulacao` e `uso_pessoal` nunca contaminam `investivel_efetivo`.
- Payload E5 (`analyze_finances`):
  - Itens em `composicao_patrimonial.imoveis[]` ganham `property_id` + `classification`.
  - Campos materializados antigos (`composicao_patrimonial.imoveis.residencia/investimento`) deprecated; lane operacional decide se mantém em paralelo via feature flag até cutover.
- Renderer/relatório (`frontend/src/components/report/cards/PatrimonioCategoriasCard.tsx`):
  - Cat_2 label: "Imóveis Investimento" → "Imóveis de Renda" (`template_key` interno `imoveis_investimento` estável).
- Goldens E5 atualizados (paridade contratual).

**Gate de saída:** goldens E5 verdes; paridade legado↔novo em workspace de fixture (snapshot diff documentado); CI verde.

### P4 — Backend API

**Track:** `residencia-uso-p4-api.md`

Entrega:

- `GET /workspaces/{ws}/properties` — lista todos os imóveis classificáveis + classificação atual + score fuzzy de sugestão para `residencia_principal` (quando `contribuinte.endereco` disponível).
- `PUT /workspaces/{ws}/properties/{id}/classification` — body `{classification, override_source}`. Idempotente.
- `PUT /workspaces/{ws}/residencia-status` — body `{status: 'owned'|'rented'|'undeclared'}`. Se `rented` ou `undeclared`, qualquer override `residencia_principal` é deletado.
- `POST /workspaces/{ws}/properties/{id}/merge` — para resolver `low_confidence` do P2 (usuário marca 2 entries como "mesmo imóvel").
- Heurística fuzzy: `rapidfuzz.fuzz.token_set_ratio` com pré-processamento regex (`(via, numero)`); thresholds 80 (sugere) / 92 (pré-marca) — eval set parametrizado trava regressão.
- Telemetria mínima inline (`mathoms.properties.*`): `classifications_set_total{classification, override_source}`, `properties_merged_total`, `fuzzy_match_accepted_total`.
- Snapshot OpenAPI atualizado ([[ADR-109]]).

**Gate de saída:** test integration com 3 cenários (owned + 1 imóvel; owned + N imóveis com sugestão fuzzy; rented com imóveis no IRPF → override `residencia_principal` proibido); eval set fuzzy com ≥20 pares TP/FP travado em CI.

### P5 — UX pós-upload + MembersTab

**Track:** `residencia-uso-p5-ux.md`

Entrega:

- **Inline pós-upload do 1º IRPF** (não modal interruptivo): após sucesso do upload, exibe seção "Identificamos N imóveis no seu IRPF. Qual é sua residência principal?" com:
  - Tabela densa: `[radio] | Tipo (Casa/Apto) | Descrição completa | Valor`.
  - Pré-seleção do candidato fuzzy (score ≥80) com badge cinza "sugerida pelo seu endereço no IRPF".
  - Opção final "○ Moro de aluguel ou em imóvel de terceiros" (seteia `residencia_status='rented'`).
  - Botão "Decidir depois" → mantém `residencia_status='undeclared'` + badge "pendente" em MembersTab.
- **Seção "Residência principal" em MembersTab.tsx**: editor permanente com estado atual (`Residência: Casa Tasso da Silveira` | `Aluguel` | `Não definida`) + botão trocar.
- **Renderer do relatório:**
  - `residencia_status='rented'` → esconder linha "Residência" da Composição Patrimonial + footnote "Aluguel não compõe patrimônio (despesa em fluxo de caixa)".
  - `residencia_status='undeclared'` → mostrar linha com `—` + CTA "definir residência".
- **Re-upload de IRPF:** só repergunta se `property_id` da escolha anterior sumiu do novo IRPF (não interrompe fluxo nominal).
- Acessibilidade: `aria-describedby` na pré-seleção + screen reader anuncia justificativa.

**Gate de saída:** dogfood no `5@5.com` (CEO confirma em <30s na primeira vez); usabilidade verificada com Playwright `@critical` em fluxo pós-upload.

### P6 — Cutover legado

**Track:** `residencia-uso-p6-cutover.md`

Entrega:

- Script idempotente `dev/migrate_residencia_keyword_to_override.py`:
  - Para cada workspace com `residencia_principal_keyword` setado:
    - Roda matching de keyword contra `descricao` dos imóveis do baseline consolidado mais recente.
    - Match → cria row em `workspace_property_overrides` com `classification='residencia_principal'`, `override_source='migration_keyword'`.
    - Sem match → seta `residencia_status='undeclared'` + log warning para audit.
  - Dry-run mode (default) + apply explícito; output JSON com workspaces afetados.
- Deprecation:
  - 1 sprint com keyword + override coexistindo (override vence).
  - Sprint seguinte: remove leitura de `residencia_principal_keyword` em `_extract_residencia_keyword` ([`pipeline/domain/services/e5_analyzer_adapter.py`](../../../pipeline/domain/services/e5_analyzer_adapter.py)).
  - Hook pre-commit (`dev/check_forbidden_paths.py` ou novo `dev/check_residencia_keyword.py`) impede re-introdução do campo em `family_members.<titular>.extra`.

**Gate de saída:** audit de workspaces zerado (todos migrados ou `undeclared`); 0 leitura de `residencia_principal_keyword` em code search; pre-commit gate ativo em CI.

## Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Migration legado não encontra match em workspace com keyword exótica | Dry-run obrigatório; workspaces sem match viram `undeclared` (não-destrutivo); audit pré-merge no PR de cutover. |
| Heurística fuzzy mal-calibrada | Eval set ≥20 pares com TP/FP documentado; threshold travado em CI; auto-aplica **só** com `override_source='fuzzy_match_accepted'` após confirmação humana. |
| Payload E5 muda contrato e quebra renderer | P3 entrega payload novo em paralelo via feature flag; cutover quando goldens E5 e snapshot E2E passam. |
| Casal em comunhão com 2 IRPFs declarando mesmo imóvel duplica | Dedup determinístico em P2 (`endereco_canonical` + `codigo_rfb`); golden de paridade trava. |
| Workspace sem IRPF processado fica sem pré-seleção heurística | UX em P5 degrada para "lista todos sem destaque"; usuário marca manualmente em MembersTab. |
| ADR-215 ainda Proposto e alguém PR fora dela | Plano só executa após ADR Decidida; gate operacional (sprint planning) bloqueia P1 sem ADR Decidida. |

## Métricas de sucesso (pós-MVP V1)

- **Cobertura:** % de workspaces com `residencia_status ∈ {owned, rented}` (não `undeclared`) ≥ 80% após 2 semanas do rollout.
- **Acurácia heurística:** ratio de overrides com `override_source='fuzzy_match_accepted'` ÷ total ≥ 60% (pré-seleção útil).
- **Stickiness:** 0 caso de override sobrescrito acidentalmente após re-upload de IRPF (gate empírico em CI).
- **Bug rate:** 0 relato de "linha Residência zerada" pós-cutover.

## Referências

- [[ADR-215]] — decisão arquitetural canônica (este plano executa)
- [[ADR-145]] — 7 categorias canonical (cat_2 rebatizado, key estável)
- [[ADR-142]] — `imoveis_no_if` (passa a respeitar enum, não cat_2 inteira)
- [[ADR-186]] — override sticky pattern (mesmo princípio)
- [[ADR-137]] — catalog + override resolver (modelo espelhado)
- [[ADR-157]] — schema E1.6 (campo aditivo)
- [docs/reference/ARCHITECTURE.md §4.1](../../reference/ARCHITECTURE.md) — domain glossary (atualizar após cutover)
- Co-design 2026-05-15: `financial-planner` + `product-designer` + `data-engineer`
