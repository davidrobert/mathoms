---
id: ADR-238
type: adr
title: "Ingestão de Informes de Rendimentos anuais avulsos (PGBL/VGBL, financeiro PF/PJ, proventos) — fonte fiscal primária paralela ao E1.6"
status: Decidido
phase: A17.informes-avulsos
date: "2026-05-21"
amended_at: ["2026-05-29"]
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-216]]"
  - "[[ADR-189]]"
  - "[[ADR-236]]"
  - "[[ADR-093]]"
  - "[[ADR-212]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
  - "[[ADR-199]]"
  - "[[ADR-231]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 238"
  - "Informes de Rendimentos"
  - "Informes anuais avulsos"
  - "extract_informes_anuais"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/methodology
  - area/persistence
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - phase/a17
---

> **Correção (2026-05-29):** `data_adesao` deixou de ser hard-fail em regime
> regressivo — ver §"Correção — `data_adesao` não é hard-fail em regressivo".

## Contexto

ICP wealth-tech BR coleciona, todo ano, um **conjunto heterogêneo de Informes de Rendimentos anuais** emitidos por cada instituição financeira (banco PF, banco/adquirente PJ, corretora, seguradora de previdência privada, holding pagadora de dividendos, imobiliária). Esses informes alimentam a declaração IRPF, mas têm valor próprio: são **fontes primárias granulares** (por produto, por ticker, por plano) que a declaração agrega ou arredonda; são entregues entre janeiro e março, antes da declaração ser fechada; e existem para o ano corrente mesmo quando a declaração do ano-base anterior ainda é a única disponível.

Sessão de validação 2026-05-21 (workspace dogfood) com 15 PDFs reais — BrasilPrev 2025 (PGBL), Itaú/Santander/Caixa/Nubank/C6 PF, XP Investimentos + XP Proventos, Itaúsa (holding), C6 PJ + Stone PJ, Wise (conta multi-moeda no exterior), e o Informe de Rendimento (Einstein) genérico — revelou três problemas em produção:

1. **Cobertura quase nula.** O único informe anual modelado end-to-end hoje é o de aluguel QuintoAndar ([[ADR-216]] D9, sufixo `-2_informe_aluguel.json`). O classifier ([backend/app/services/classification/type_classifier.py](../../backend/app/services/classification/type_classifier.py)) tem regex genérico `informerendimentos` extremamente restrito (exige literal "Informe de Rendimentos Financeiros" ou "Informe Anual de Rendimentos"). Dos 15 PDFs do batch, ~13 caem em `.other` silencioso ou são mal-classificados.

2. **Mapping semanticamente errado.** [`map_e0_doc_type_to_document_type`](../../backend/app/services/document_classification.py) traduz qualquer `informerendimento*` para `DocumentType.irpf`, rota que dispara o stage [[ADR-157]] `extract_irpf_full` (esperando declaração IRPF completa, não informe avulso). Falsos positivos quebram o pipeline silenciosamente.

3. **Gap de produto pré-IR.** S8 Previdência ([[ADR-189]]) só calcula `PgblStatus.capacidade_disponivel` quando E1.6 existe. ICP que adota Mathoms em janeiro-fevereiro (antes de declarar) fica sem o KPI mais valioso da seção, mesmo tendo o informe da seguradora em mãos. Mesmo problema afeta ADR-236 cascata fiscal PJ ([[ADR-236]] D2 leitor IRPF base PGBL) — depende exclusivamente de E1.6, sem fallback por informe PJ.

Co-design `financial-planner` + `data-engineer` em paralelo (2026-05-21, registrado em A17 §Origem) consolidou 5 tipos canônicos, padrão arquitetural unificado, ordem de rampup e guardrails de produto.

## Decisão

Adotar **stage único `extract_informes_anuais` paralelo ao `extract_irpf_full`, com 5 tipos canônicos discriminados por `tipo_informe`, schema-base polimórfico + sub-schemas por tipo, e cascade de fontes onde declaração entregue vence informe**. Rampup em 4 ondas (Sprint A17, L1-L4) com sinergia explícita com [[ADR-236]] em construção na A16 L2.

### D1 — Cinco tipos canônicos de informe

| `tipo_informe` | Cobre (instituições no batch 2026-05-21) | Schema principal |
|---|---|---|
| `previdencia_privada` | BrasilPrev (Bradesco Vida, Caixa Vida, Icatu por extensão) | PGBL/VGBL, regime tributação progressivo vs regressivo, contribuições + saldo 31/12 |
| `financeiro_pj` | C6 PJ, Stone PJ (Cielo, Rede por extensão) | Receita bruta + retenções IR/CSLL/PIS/COFINS/ISS por regime tributário |
| `financeiro_pf` | Itaú, Santander, Caixa, Nubank, PicPay, C6 PF, XP Investimentos, **Wise (multi-moeda, conta no exterior)** | 4 quadros RFB (tributáveis, isentos, exclusiva, bens/direitos) + snapshot 31/12 por produto; suporta `moeda` (BRL default, USD/EUR/GBP etc) para Wise/contas no exterior |
| `proventos_acoes` | XP Proventos, Itaúsa (corretora multi-ativo + holding pagadora direta) | Eventos por ativo: dividendo, JCP, rendimento FII, bonificação; CNPJ pagador ≠ CNPJ fonte que emite |
| `aluguel_imobiliaria` | QuintoAndar (já modelado — [[ADR-216]] D9) | Receitas + retenções por imóvel/locatário |

Itaúsa (holding) é caso de `proventos_acoes` com 1 ativo, não tipo separado. Bancos PF e XP Investimentos compartilham o mesmo layout RFB de 4 quadros, não vale fragmentar por instituição.

**Wise (multi-moeda no exterior)** é caso de `financeiro_pf` com nuances específicas — não justifica tipo novo, mas exige que o sub-schema `informe_pf` modele `moeda` em saldos e rendimentos (default `BRL`, aceita `USD`/`EUR`/`GBP`/`...`). Pegadinhas fiscais que o calculator/analyzer precisa tratar:

- **Saldo em conta-corrente no exterior em moeda estrangeira** → código RFB 62 em `bens_direitos[]` (distinto de código 41 doméstico). Valor convertido por PTAX 31/12 ([[ADR-135]] `market_rates`).
- **Variação cambial sobre saldo** **não é "rendimento"** — é ganho de capital em moeda estrangeira (Lei 9.250/1995, alíquota 15% via DARF GCAP). Não cair no bucket `rendimentos_isentos[]`.
- **Juros pagos sobre saldo em moeda estrangeira** vão em rendimentos tributáveis recebidos do exterior (carnê-leão, código 13) — IR retido na fonte se houver tratado de bitributação, raro para PF.
- **CBE (Capital Brasileiro no Exterior, BACEN)** acima de USD 1MM em ativos no exterior é **fora do escopo** — Mathoms não emite CBE, só sinaliza a obrigação no warning de E5 quando saldo Wise + outros exteriores cruza o threshold.

### D2 — Schema-base polimórfico com Discriminated Union

`InformeRendimentosBase` (Pydantic abstract) com campos comuns + payload tipado discriminado por `tipo_informe`. Sub-schemas JSON dedicados em `config/schemas/informe_<tipo>.schema.json`. Padrão de [[ADR-216]] `informe_aluguel.py`: top-level lenient (`additionalProperties: true`), sub-models strict.

```python
class InformeRendimentosBase(BaseModel):
    workspace_id: str
    ano_base: int  # ex.: 2024
    tipo_informe: Literal["previdencia_privada", "financeiro_pj", "financeiro_pf",
                          "proventos_acoes", "aluguel_imobiliaria"]
    fonte_pagadora_cnpj: str  # CNPJ emissor do informe
    fonte_pagadora_nome: str
    titular_cpf_masked: str  # ex.: "***.456.789-**"
    confidence: float = Field(ge=0.0, le=1.0)
    source_artifact_id: str  # FK pipeline_artifacts E0
    prompt_version: str  # ex.: "informe-anual-v1.0.0"
    needs_review: bool = False
    # Polimorfismo: 1 dos 5 abaixo populado conforme tipo_informe
    previdencia: Optional[InformePrevidenciaPayload] = None
    financeiro_pj: Optional[InformeFinanceiroPjPayload] = None
    financeiro_pf: Optional[InformeFinanceiroPfPayload] = None
    proventos: Optional[InformeProventosPayload] = None
    aluguel: Optional[InformeAluguelPayload] = None
```

Wire monetário: string decimal ([[ADR-090]]). Enums `CodigoRendimentoIsento` e `CodigoRendimentoTribExclusiva` de E1.6 são **reaproveitados sem alteração** (codigo_rfb é invariante imutável — não fazer upgrade in-place).

### D3 — Stage único `extract_informes_anuais` em `STAGE_REGISTRY`

Stage descritivo único ([[ADR-093]] F9.2) com sufixo `-2_informe_anual.json` em `_STAGE_TO_SUFFIX` ([[ADR-212]]). `artifact_key` codifica `tipo_informe` + instituição + ano: `previdencia_brasilprev_2024`, `proventos_xp_2024`, `financeiro_pf_itau_2024`.

**Por quê stage único e não 5 stages:** 5 stages da mesma família semântica em `FULL_ORDER` polui `STAGE_REGISTRY` e quebra reasoning sobre execução do workspace. Stage é unidade de **orquestração** (1 invocação despacha N artifacts por kind); tipo é unidade de **conteúdo**. ADR-093 exige descritividade, não 1:1 stage/tipo.

**Aluguel migra para dentro em L1.6 ou Sprint A18:** `extract_informe_aluguel` standalone ([[ADR-216]]) é depreciado em favor de `extract_informes_anuais` com `tipo_informe="aluguel_imobiliaria"`. PR de cutover separado, fora de A17.

### D4 — Cascade de fontes: declaração vence quando entregue

Quando E1.6 (`extract_irpf_full`) **e** informe avulso existem para o mesmo `(ano_base, fonte_pagadora_cnpj)`:

- **Declaração entregue vence.** Justificativa: é o que o usuário assumiu formalmente perante a RFB; mathoms não pode silenciosamente contradizer formalização legal.
- **Informe preenche gaps** onde declaração não tem aquela instituição/ano (pré-IR, histórico, instituições omitidas).
- **Divergência sempre gera warning estruturado** em E5 (não bloqueia pipeline, não persiste o diff por LGPD — alinhado a [[ADR-231]] PII encryption). Linguagem fact-checking: "divergência R$ X entre informe Y e sua declaração. Revise se foi pré-preenchimento da RFB ou omissão a corrigir." Nunca afirmar intencionalidade.

Encode via campo `source_priority` no `InformeRendimentosBase` consumido por `FiscalSource` adapter (D5). Default: `informe.source_priority = 2` quando declaração existe; `1` quando declaração ausente.

### D5 — `FiscalAnalyzer` polimórfico sobre `FiscalSource`

[`IRPFAnalyzer`](../../pipeline/domain/services/irpf_analyzer.py) é renomeado para `FiscalAnalyzer` e passa a consumir uma camada `FiscalSource` que aceita `IRPFFullOutput` (declaração) **e** lista de informes do mesmo ano-base. Ordem de precedência: D4. Snapshot 31/12 dos informes financeiros alimenta `consolidate_baseline` (E1.5c) — "informe 31/12 vence extrato D+1" quando há divergência (informe é fonte fiscal certificada).

`previdencia_analyzer.py` e `tributario/irpf_renda_tributavel.py` (ADR-236 D2) consomem `FiscalAnalyzer`, não E1.6 direto — destrava S8 PGBL e cascata fiscal PJ para workspaces sem E1.6 mas com informes correspondentes.

### D6 — Rampup em 4 ondas paralelas à conclusão de A16 L2

| Onda | Foco | Sinergia | PDFs do batch destravados |
|---|---|---|---|
| **L1** | `previdencia_privada` (BrasilPrev) | Destrava S8 PGBL pré-IR ([[ADR-189]]) | BrasilPrev → 1 |
| **L2** | `financeiro_pj` (C6 PJ, Stone PJ) | **Sinergia com [[ADR-236]] em construção** — alimenta cascata fiscal PJ sem esperar declaração | C6 PJ, Stone PJ → 2 |
| **L3** | `financeiro_pf` (6 bancos + XP Investimentos) | Snapshot 31/12 alimenta E1.5c baseline; AUVP ganha granularidade por classe | Itaú, Santander, Caixa, Nubank, PicPay, C6 PF, XP Inv → 7 |
| **L4** | `proventos_acoes` (XP Proventos, Itaúsa) | Yield-on-cost por ativo (S3) — Perini "viver de renda" | XP Prov, Itaúsa → 2 |

L1 valida o padrão arquitetural completo (classifier + schema-base + parser LLM + analyzer + UI integration). L2-L4 replicam. Cada onda é 1 lane independente em A17; L2 pode ser puxada em paralelo a A16 L2 (ADR-236) por agentes distintos para maximizar sinergia.

### D7 — Catálogo institucional: migration Alembic

Migration curta ([[ADR-137]]):

- Enum `institutions.category` ganha `insurance`, `broker`, `holding` (já tem `bank`, `exchange`, `government`, `real_estate`, `employer`, `fintech`).
- Nova coluna `tax_regime: Literal["pf", "pj", "both"]` default `both` (não explode entries de instituições que servem PF + PJ como C6 ou Stone).
- Seeds: `brasilprev` (insurance, both), `xp` (broker, both), `itausa` (holding, pf).

### D8 — Guardrails de produto: Mathoms consolida, não substitui contador

Linha vermelha: Mathoms **consolida** (snapshot patrimonial, capacidade PGBL, alíquota efetiva, comparativo metodológico Perini/Cerbasi/AUVP) e **diagnostica** (divergência, gap, oportunidade). **Não** pré-preenche declaração, não calcula DARF, não emite Carnê-Leão, não simula imposto a pagar para entrega à RFB. Implementado em 3 lugares:

1. **Inline** em todo KPI fiscal derivado de informe — footnote: "Cálculo informativo. Confira com seu contador antes de declarar. Mathoms não substitui orientação tributária."
2. **No upload do informe** — badge "Documento fiscal — usado para análise patrimonial, não para preencher declaração."
3. **No E6-parecer** ([[ADR-199]]) — system prompt instrui persona a não recomendar aporte específico ("aporte R$ X em PGBL antes de 31/12"). Padrão Cerbasi: "você tem capacidade dedutível disponível; vale conversar com contador."

### D9 — Goldens sintéticos versionados + eval real fora do git

Replicar padrão [[ADR-216]]: `tests/fixtures/informes/<tipo>/sample_<tipo>_anonymized.pdf` (CPF `000.000.000-00`, CNPJ fake, valores arredondados, nomes fictícios) + golden JSON pareado. Não usar PDFs reais em fixture — risco LGPD direto. Eval de acurácia LLM é **débito separado** com dataset privado em `_scratch/` fora do git.

## Gates

- **G1** — Migration Alembic do catálogo (D7) mergeada antes do PR1 de L1.
- **G2** — `extract_informes_anuais` em `STAGE_REGISTRY` desde o PR1 da L1; aluguel migra para dentro só após L4 (cutover de [[ADR-216]] sufixo standalone para `tipo_informe="aluguel_imobiliaria"`).
- **G3** — Coordenação síncrona com responsável [[ADR-236]] antes do PR de L2 — `InformeQuery` service deve estar pronto e validado pelo agente que tocou `irpf_renda_tributavel.py`.
- **G4** — `dev/codigo_rfb_invariant_check.py` (já em CI) continua verde após adição dos novos schemas — codigo_rfb não muda in-place.
- **G5** — 14 PDFs do batch de validação (workspace dogfood) classificam corretamente com `confidence ≥ 0.7` ao final de cada onda; PDFs fora do escopo da onda continuam em `.other` (não regridem).
- **G6** — `pytest backend/tests tests -q` verde + `cd frontend && npm test -- --run` verde + `pre-commit run --all-files` verde por PR.
- **G7** — Disclaimer "não substitui contador" visível em todo KPI fiscal derivado (D8) — validado em UI review de cada onda.

## Implementação

Detalhe operacional por onda em [[TRACK-a17-l1-previdencia-privada]], [[TRACK-a17-l2-financeiro-pj]], [[TRACK-a17-l3-financeiro-pf]], [[TRACK-a17-l4-proventos-acoes]]. Lanes em [docs/sprint/A17/lanes/](../sprint/A17/lanes/). Plano canônico cross-onda em A17 quando justificar (>2 ondas em paralelo).

PR de Proposto desta ADR inclui apenas: este arquivo + estrutura de Sprint A17 (`_README.md` + 4 lanes + 4 tracks ready) + entrada changelog. **Nenhum código de implementação** — implementação começa quando L1 (previdência) for puxada por agente.

## Não-objetivos

- **VGBL como capacidade PGBL** — VGBL não deduz IRPF (vai em isentos/exclusiva no resgate). Schema modela `plano_tipo` para distinguir, mas calculator nunca conta VGBL como capacidade PGBL.
- **Tabela regressiva PGBL com precisão por aporte** — exige data de cada aporte, informe só dá média anual. V1 usa média declarada; precisão por aporte é V2 condicionada a demanda.
- **Aporte do empregador (patrocinador) em PGBL** — vem em informe separado do empregador (não da seguradora). V1 documenta o gap; V2 adiciona `tipo_informe="patrocinador_pgbl"` se ICP materializar.
- **Histórico retroativo > 2 anos** — onboarding aceita até 2 anos retrospectivos de informes; expansão para 5 anos só com sinal de demanda do beta.
- **Lucro Real PJ** — fora do escopo da L2 (consistente com [[ADR-236]] V1).
- **Reforma tributária / PEC dividendos** — ADR de schema evolution quando aprovar.
- **Seção S_FISCAL_AVULSO dedicada no relatório** — enriquecimento inline em S3 (proventos) / S4 (patrimônio) / S8 (previdência) + warnings de divergência em E5. Seção nova dilui narrativa.
- **Pré-preenchimento de declaração / DARF / Carnê-Leão** — D8 linha vermelha.

## Riscos

- **R1 — Acoplamento ruim com ADR-236.** Mitigado por G3 + abstração `InformeQuery` service em `backend/app/application/informes/` consumido por `irpf_renda_tributavel.py` antes de L2 mergear.
- **R2 — LGPD inferência identificável.** Comparar "BrasilPrev disse R$ X, sua declaração disse R$ Y" exige ambos descriptografados em memória. Mitigado por D4 (diff em E5 efêmero, não persistir) + alinhamento a [[ADR-231]].
- **R3 — Schema evolution PrevSocial (RPC/RPPS).** Pode entrar em informes ainda neste ciclo regulatório. Mitigado por campo `regime` no payload `previdencia` reservando espaço — V1 valida só `privado_complementar`; V2 abre sem breaking.
- **R4 — Layout LLM por instituição varia.** Mitigado por LLM-first (Claude Haiku para tipos simples, Sonnet para complexos), cache de prompt idempotente, e G5 (validação real com PDFs do batch).
- **R5 — Custo LLM.** ~$1-2/ano/workspace (Haiku majoritário). Aceitável dentro de premium tier; cache de prompt ([[ADR-144]]) corta 80% em re-runs.

## Alternativas consideradas

- **A1 — Schema unificado único com `kind` runtime.** Rejeitado: permissividade força runtime branching no consumer; perde garantia de tipo no boundary ([[ADR-097]] D2).
- **A2 — Stage por tipo (`extract_informe_previdencia`, `extract_informe_pj`, …).** Rejeitado: explode `STAGE_REGISTRY` com 5 stages da mesma família; ADR-093 exige descritividade, não 1:1 stage/tipo.
- **A3 — Informes substituem E1.6.** Rejeitado: declaração entregue tem precedência formal (D4); informes complementam, não substituem.
- **A4 — Build via SaaS de OCR fiscal BR (Serpro, Linker, Cuca).** Avaliado e rejeitado: Receita Federal API não cobre informes de bancos privados; SaaS B2B custa >LLM + adiciona dependência. LLM-first com Claude é mais barato e flexível.
- **A5 — Seção S_FISCAL_AVULSO dedicada.** Rejeitado: validação cruzada e snapshots enriquecem cards existentes (S3/S4/S8); seção nova dilui narrativa e cria fadiga em quem tem declaração consistente.

## Entrega — L1 previdência privada (Sprint A17 L1, 2026-05-21)

Lane [[A17.l1]] entregue em 5 PRs sequenciais (P1 → P5), todos squash-mergeados em `main` com CI verde:

- **P1** [#402](https://github.com/davidrobert/mathoms/pull/402) `feat(adr-238): migration tax_regime + InformeRendimentosBase schema` — D2 (schema-base polimórfico) + D3 (stage) + D7 (catálogo institucional, seed BrasilPrev). Gate triplo `data-engineer` + `financial-planner` aplicado em 1 rodada: inverteu `source_priority` default (fail-safe), adicionou `saldo_31_12_ano_anterior` + `rendimentos_brutos/liquidos` + `ir_retido_natureza`, removeu `beneficiarios_count` (YAGNI — re-add em A19).
- **P2** [#403](https://github.com/davidrobert/mathoms/pull/403) `feat(adr-238): stage extract_informes_anuais + prompt LLM previdência` — stage runner polimórfico despachando por `tipo_informe` (P1 só `previdencia_privada`, L2-L4 expandem); cache key `content_hash[:16] + PROMPT_VERSION`; `source_artifact_id` via stem (lineage proxy); CPF mask em Python pós-LLM (LGPD).
- **P3** [#404](https://github.com/davidrobert/mathoms/pull/404) `feat(adr-238): classifier E0 content-based + DocumentType.informe_rendimentos_anuais` — corrigiu bug histórico §Contexto §2 (`informe*` caía em `.irpf` e quebrava o pipeline silenciosamente); migration `adr238informes2` cria valor no enum nativo (Postgres ALTER TYPE ADD VALUE IF NOT EXISTS).
- **P4** [#406](https://github.com/davidrobert/mathoms/pull/406) `feat(adr-238): FiscalSource adapter + InformeQuery service` — D4 (precedência declaração vence) + D5 (`FiscalAnalyzer` polimórfico via alias retrocompat); `divergencias_pgbl()` gera warning efêmero em E5 sem persistir (LGPD).
- **P5** [#407](https://github.com/davidrobert/mathoms/pull/407) `feat(adr-238): UI S8 footnote D8 + upload badge + parecer guardrail` — guardrails D8 nos 3 lugares prescritos: footnote CRC inline em S8, badge fiscal no upload zone, regra #9 no system prompt do parecer (PROMPT_VERSION bumpado 1.0.0 → 1.1.0).

**Padrão arquitetural validado** que L2-L4 replicam: classifier content-based → schema-base polimórfico + sub-schema strict por tipo → stage despachando por `tipo_informe` → `FiscalSource` consolidando IRPF + informes com precedência D4 → guardrails D8 em UI/upload/parecer.

**Débito explícito** (deferido para PR follow-up ou L2):
- Plumbing `analyze_finances` (E5) consumindo `FiscalSource` para popular `data.tributario.pgbl_*` quando há informe sem E1.6 — hoje a UI renderiza `RendaPfZeradaNotice` mesmo com informe processado.
- Eval golden update do parecer (reflexo da regra #9 prompt 1.1.0).
- `source_artifact_id` promovido de string-stem para FK UUID (P3 cobertura content-based metadata).

## Correção — `data_adesao` não é hard-fail em regressivo (incidente dogfood 2026-05-29)

**Sintoma.** Stage `extract_informes_anuais` rodou 193.5s e abortou em informe real de previdência regressivo: `Output validation failed after 4 attempts: regime_tributacao=regressivo exige data_adesao (alíquota PEPS depende de anos_desde_adesao)`. Um `model_validator` em `InformePrevidenciaPayload` exigia `data_adesao` quando `regime_tributacao=regressivo`. O informe não imprimia a data de adesão (comum em informes regressivos), o LLM corretamente retornava `null`, e o validator transformava o erro Pydantic em retry — o harness LLM (`litellm_client`) tratou a falha de validação como retentável e queimou 4 chamadas (~193s) numa restrição insatisfazível.

**Causa raiz.** O guard protegia um consumidor que **não existe**: o cálculo de alíquota regressiva PEPS (`anos_desde_adesao`) é V2 (ver Não-objetivos §"Tabela regressiva PGBL com precisão por aporte"). Exigir `data_adesao` destruía o informe inteiro — perdia `saldo_31_12` (patrimônio + IRPF código 97) por um insumo que ninguém consome em V1. Falso-positivo (patrimônio que some, silencioso) é pior que falso-negativo (alíquota imprecisa, visível e deferida).

**Decisão.** `data_adesao` é **opcional em V1, inclusive no regime regressivo**:
- Removido o `model_validator` que fazia hard-fail. `data_adesao` permanece `Optional[str]` com pattern `YYYY-MM(-DD)?`.
- Regressivo sem `data_adesao` → **degradação graciosa**: `extract_informes_anuais._flag_regressivo_sem_adesao` marca `needs_review=true` e anexa nota ("alíquota PEPS indeterminada; saldo registrado (ADR-238 V1)"). O saldo é preservado.
- Prompt LLM `informe-prev-v1.0.0 → v1.1.0`: removido "OBRIGATÓRIO quando regressivo" (induzia alucinação de data plausível); reforçado anti-alucinação ("se não está impressa, é `null`"; "`null` + `needs_review` é a resposta CORRETA"). Bump invalida cache idempotente ([[ADR-144]]).
- V2 (alíquota PEPS): quando regressivo sem data, alíquota deve ser **indeterminada/intervalo (10%–35%)**, nunca chutar 35% — endossado por `financial-planner`.

**Follow-up.** Eval golden live-LLM com duas classes — Classe A (informe com data → recall gate) e Classe B (informe sem data → precision gate: confirma `data_adesao=null` + `needs_review=true` sem alucinação). 100% sintético (sem PII). Fora do gate determinístico de CI; testes unitários determinísticos cobrem 100% da lógica de degradação (`tests/test_extract_informes_anuais_unit.py`, `tests/test_informe_previdencia_schema_unit.py`).
