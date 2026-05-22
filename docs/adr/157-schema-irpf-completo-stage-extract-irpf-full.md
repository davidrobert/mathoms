---
id: ADR-157
type: adr
title: "Schema IRPF completo (stage `extract_irpf_full`)"
status: Decidido
phase: "Sprint A8 · Lane irpf-full-schema"
date: "2026-04-30"
relates_to: ["[[ADR-090]]", "[[ADR-093]]", "[[ADR-097]]", "[[ADR-105]]", "[[ADR-111]]", "[[ADR-135]]", "[[ADR-143]]", "[[ADR-165]]", "[[ADR-231]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 157"]
tags:
  - area/llm
  - area/persistence
  - area/pipeline
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 103
---

# ADR-157 — Schema IRPF completo (stage `extract_irpf_full`)

**Status:** Decidido (Sprint A8 · Lane irpf-full-schema) • **Data:** 2026-04-30 • **Relaciona** [ADR-090](#adr-090--decimal-para-valores-monetários), [ADR-093](#adr-093--rename-completo-de-identificadores-de-stage-opção-a), [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy), [ADR-105](#adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a), [ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6), [ADR-135](#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio), [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76).

**Contexto:** O stage E1.5 (`extract_baseline`) extrai apenas Bens & Direitos do IRPF — ~30% do conteúdo financeiro útil da declaração. Restam fora: rendimentos tributáveis (PJ/PF/exterior), rendimentos isentos e exclusivos, pagamentos dedutíveis, imposto apurado, dependentes, dívidas e doações. Sem esses dados, o relatório premium não consegue calcular renda anual líquida real, capacidade PGBL não usada, alíquota efetiva, split renda do trabalho × capital (Perini), ou sinalizar otimizações tributárias (Cerbasi). Workspaces sem IRPF (free tier ou usuário que não declara) ficam invariavelmente sem essa camada — nada do que se decide aqui pode quebrá-los.

Alternativas avaliadas:
1. **Estender E1.5** com novos campos no `BaselinePatrimonialOutput` — quebra paridade com E1.5c/E5 atuais; obriga goldens a refletir explosão de campos vazios; mistura Bens & Direitos com renda em um único schema gigante.
2. **Stage novo paralelo (`extract_irpf_full`, sufixo `-1.6_irpf_full.json`)** — coexiste com E1.5; consumidores migram quando estiverem prontos; cutover futuro via flag (item 8 abaixo).
3. **Split em 2-3 chamadas LLM por declaração** (rendimentos / dedutíveis+IR / dependentes+bens) — reduz tokens por chamada mas adiciona reconciliação cross-call e custo de regression.

**Decisão:** Adotar (2). Stage `extract_irpf_full` (descritivo, sem alias legado conforme ADR-093), uma chamada LLM por declaração, prompt caching ativo desde v1, schema strict-by-default só para este stage. Sub-schemas tipados com Decimal-as-string no wire (ADR-090) e enums por contexto para `codigo_rfb`. E5 lê o artefato via try-read opcional — não declarado em `STAGE_REGISTRY[analyze_finances].reads` para que workspaces sem IRPF continuem rodando o pipeline determinístico inteiro. Cutover de Bens & Direitos (E1.5 → E1.6) é deliberadamente fora desta ADR e fica para Sprint futura via flag `MATHOMS_E16_SUPERSEDES_E15_BENS`.

**Sub-decisões:**

1. **Wire monetário:** `Decimal` no Pydantic + JSON Schema `"type":"string","pattern":"^-?\\d+(\\.\\d{1,2})?$"` (limita 2 casas, evita ruído LLM). Não cents, não float — segue ADR-090 e mantém paridade com `Money.brl`.
2. **Alíquotas calculadas em Python pós-extração**, não pelo LLM. LLM extrai apenas valores absolutos (`base_calculo`, `ir_devido`, `ir_pago`); `IRPFAnalyzer` deriva `aliquota_sobre_tributavel` (RFB-style) e `aliquota_sobre_total` (Cerbasi-style).
3. **Códigos RFB como enums por contexto** (`RendimentoIsentoCodigo`, `PagamentoDedutivelCodigo`, etc.) com fallback `"99_outro"` — evita string-matching frágil em E5 (G2 dealbreaker).
4. **`additionalProperties` mista**: `true` no top-level (com WARNING ao detectar campo desconhecido — mecanismo proativo para anos novos com shape novo); `false` em sub-models (rendimentos_pj item etc. validados strict). Destino do WARNING: `logger.warning("e16_unknown_field", extra={"field": k, "workspace_id": ws_id})` no namespace `mathoms.pipeline.e16`.
5. **PII enforcement:** validator emite `e16.pii.unmasked_cpf` (warning) quando string field livre — `notes`, `descricao`, `discriminacao`, `fonte` — bate `\d{3}\.\d{3}\.\d{3}-\d{2}` ou `\d{11}`. Visível no `StageReview` como sinal de data-quality; **não pausa o pipeline**. Classificação implícita PII-tier-2 por nome do stage; coluna `pii_tier` em `pipeline_artifact` é prematura e fica fora desta ADR. Defesa real de PII vem por encryption-at-rest dos campos livres (trajetória [[ADR-231]]). _Reclassificado de `error` para `warning` na errata 2026-05-22 — ver seção final._
6. **Reconciliação cross-field obrigatória** no validator: `imposto_apurado.ir_pago_brl ≈ sum(rendimentos_pj.ir_retido_brl) + sum(rendimentos_pf.ir_recolhido_brl)` com tolerância 0,02 BRL. Fora da janela → `confidence` cap em 0,7 + flag `needs_review`.
7. **`prompt_version: str`** no payload (constante por versão do prompt — `"e16-v1.0.0"` — golden-friendly). `extracted_at` **não** vai no payload (mudaria a cada rerun e quebraria golden byte-a-byte); auditoria temporal vive em `pipeline_artifact.created_at` (já existe).
8. **Cutover via flag** `MATHOMS_E16_SUPERSEDES_E15_BENS` (default `False`, por workspace). Quando `True`, E5 ignora `consolidate_baseline` e usa só `bens_direitos[]` do E1.6. **Critério de saída para virar default global:** ≥3 declarações reais validadas com paridade `bens_direitos[]` E1.5↔E1.6 byte-a-byte (tolerância 0,01 BRL — ADR-097/D5). Sem isso, coexistência permanece. Cutover real = sprint futura, fora desta ADR.
9. **Out of scope v1:** Ganho de Capital (DARF mensal), atividade rural, espólio, `ImpostoPagoMensal` granular (carnê-leão por mês), `doacoes[]` (uso marginal — desbloqueia conversa só com renda > R$ 500k/ano ou patrimônio > R$ 3M, suporta v2). `rendimentos_pf[]` permanece em v1 porque é o bucket canônico de aluguel recebido (carnê-leão), expressamente exigido pelo split trabalho×capital de Perini (G0 sign-off). Decisões registradas para v2 quando houver demanda.
10. **Coexistência float/Decimal:** E1.5 (`BaselinePatrimonialOutput`) mantém `float` legado nesta sprint para não quebrar goldens existentes. E1.6 usa `Decimal`. Conversão em ponto único no consumidor (E5/`IRPFAnalyzer`) durante coexistência. Não migrar E1.5 nesta lane.
11. **Custo aceitável:** rerun com prompt-cache hit ≤ $0,40/declaração; miss ≤ $0,80/declaração. Se exceder em ≥3 declarações reais consecutivas, abrir lane separada para split em 2-3 chamadas. Telemetry no log do stage inclui `metadata.ano_base` para breakdown por workspace+ano.

**KPIs derivados (IRPFAnalyzer, queries puras):**

- `renda_anual_familiar(ano)` — soma tributáveis + isentos + exclusiva (titular + cônjuge), com guard anti-13º duplo.
- `renda_liquida_familiar(ano)` — descontando IR pago, contribuição previdenciária e pensão alimentícia paga.
- `aliquota_sobre_tributavel(ano)` e `aliquota_sobre_total(ano)` — duas alíquotas por design (G0 sign-off).
- `pgbl_capacidade_dedutivel(ano)` — `0,12 × rendimento_tributavel - pgbl_aportado`. Zera quando `modelo == "simplificado"` (limitação metodológica do regime).
- `split_trabalho_vs_capital(ano)` — buckets via mapa de códigos RFB documentado em docstring (Perini puro).
- `evolucao_renda_anos()` — série temporal; degrada gracioso com 1 declaração.

**Consequências:**

- ✅ Destrava 6 KPIs novos no relatório premium (renda anual líquida, alíquota efetiva dupla, capacidade PGBL, split trabalho/capital, evolução temporal, sinalizações de otimização).
- ✅ Workspaces sem IRPF continuam rodando — try-read opcional + zero stages obrigatórios novos.
- ✅ Goldens cobrem regressão prompt + reconciliação cross-field cobre garbage-in silencioso.
- ✅ PII protegida em duas camadas (validator + classification convention) sem coluna nova no DB.
- ⚠️ Custo LLM ≈ $0,50–0,80 por declaração (Sonnet 4.6, ~80–120k tokens input + ~12–20k output). Aceitável dado que IRPF é processado raramente (1×/ano por contribuinte). Prompt caching reduz ~50% em rerun.
- ⚠️ Coexistência E1.5 + E1.6 por 1-2 sprints duplica artefato Bens & Direitos. Goldens existentes de E1.5 não devem mudar nesta sprint.
- ⚠️ `additionalProperties: true` no top-level relaxa garantia de schema — mitigado pelo WARNING obrigatório em telemetry.
- ❌ Schema strict global do pipeline (`pipeline.json → schema_validation.enabled`) **não** é alterado — E1.6 ganha override `schema_validation.stages.extract_irpf_full: "strict"` para não forçar rigor em stages onde dia-a-dia é warn.
- ❌ Ganho de Capital fica de fora — workspaces com venda de imóvel/ações verão lacuna até v2. Trade-off explícito em prol de prazo MVP.

**Referências de código (após implementação):**

- `pipeline/llm/schemas/e16_irpf_full.py` — Pydantic models.
- `config/schemas/e16_irpf_full.schema.json` — JSON Schema espelhado.
- `pipeline/llm/prompts/e16_irpf_full.py` — prompt + `PROMPT_VERSION`.
- `pipeline/llm/validators.py` → `validate_e16_output` — reconciliação cross-field, anti-PII em campos livres.
- `pipeline/stages/extract_irpf_full.py` — runner.
- `pipeline/domain/services/irpf_analyzer.py` — KPIs.
- `pipeline/stage_spec.py` — entrada `extract_irpf_full` em `STAGE_REGISTRY` + `FULL_ORDER` (paralela a `extract_baseline`, sem `reads` declarado).
- `pipeline/artifact_store.py` — mapeamento `extract_irpf_full → E2_extracts`, sufixo `-1.6_irpf_full.json`.

---

**Errata 2026-05-22 — D5 reclassificado de erro abortivo para warning**

A formulação original de D5 ("validator recusa payload se qualquer string field bate regex de CPF/CNPJ fora dos campos `*_masked`") modelou CPF não-mascarado em campo livre como leak de PII. Na prática, IRPF cita CPF de terceiros **por design**:

- `bens_direitos.descricao` — vendedor de imóvel ("Apto adquirido de CPF 123…")
- `dividas_onus.discriminacao` — credor PF de empréstimo
- `rendimentos_isentos.fonte/descricao` — fonte de aluguel, pensão, herança
- `rendimentos_tributacao_exclusiva.descricao` — sacado/contratante PF
- `notes` — anotações gerais que mencionam dependentes/cônjuge/herdeiros

O efeito operacional do tratamento como `severity="error"` era pausar **virtualmente todo IRPF real** em `needs_review` no stage `extract_irpf_full`. O gate em `backend/app/tasks/pipeline_task.py::_has_validation_errors` interpreta `validation.valid == False` (qualquer erro) como necessidade de revisão humana, e `ValidationResult.valid` retorna `len(errors) == 0`.

Reclassificação aplicada:

1. **`_emit_pii_cpf` agora emite `severity="warning"`** ([pipeline/llm/validators.py](../../pipeline/llm/validators.py)). Visibilidade no `StageReview` preservada (sinal de data-quality / hallucination); pipeline não pausa.
2. **Goldens E1.6** (`tests/test_llm_golden.py::test_no_unmasked_cpf_in_free_text`) continuam exigindo que fixtures não contenham CPF não-mascarado — se o LLM hallucinar CPF em campo livre, fica visível como warning + falha o golden em CI.
3. **Defesa real de PII** fica na trajetória [[ADR-231]] — encryption-at-rest dos campos livres em `pipeline_artifacts` via Fernet. Tratar exposição como problema de **persistência/transporte**, não de **rejeição de payload**.
4. **CNPJ permanece fora do escopo** do validator — a redação original mencionava CNPJ mas o regex nunca cobriu. Não é regressão; é correção da redação.

Testes atualizados: `tests/test_validation_issues_e16.py::TestLegacyMessageParity` (3 mensagens migraram de `r.errors` → `r.warnings`) + `TestIssuesStructure::test_pii_dividas_onus_issue` (severity assert) + `tests/test_irpf_full_schema_unit.py::TestValidatorAntiPii` (renomeado `_rejected` → `_warns` + assert `r.valid`).
