---
id: ADR-240
type: adr
title: "Card S_PROTECAO no relatório — 4º pilar AUVP entre Reserva e Patrimônio (Sprint A19)"
status: Decidido
phase: A19.l1
date: "2026-05-21"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-127]]"
  - "[[ADR-129]]"
  - "[[ADR-143]]"
  - "[[ADR-145]]"
  - "[[ADR-189]]"
  - "[[ADR-199]]"
  - "[[ADR-216]]"
  - "[[ADR-238]]"
  - "[[ADR-239]]"
supersedes: []
superseded_by: []
amended_at: ["2026-08-08"]
aliases:
  - "ADR 240"
  - "S_PROTECAO"
  - "Proteção Patrimonial"
  - "Pilar AUVP Proteção"
  - "Seguros — Cobertura Contratada"
tags:
  - type/adr
  - status/decidido
  - area/report
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - phase/a19
---

> **Emenda de copy (2026-08-08, PR #1286):** o **título user-facing** da seção
> passou a ser **"Seguros — Cobertura Contratada"**. Os esboços de layout abaixo
> ainda escrevem "Proteção Patrimonial" — leia-os como o **nome de domínio
> interno** (id `S_PROTECAO`, payload `protecao_patrimonial`, analyzer
> homônimo), que permanece. Detalhe em §Emenda no fim.

## Contexto

Sprint A18 ([[ADR-239]]) entrega ingestão de **CRLV + Apólices de seguro + FIPE refresh**. Sem card no relatório, a ingestão fica invisível — owner sobe 6 PDFs e nada aparece na narrativa de planejamento.

Mathoms hoje **não tem categoria "proteção patrimonial"** como pilar formal no relatório. Há bucket de despesa "seguros" em [`config/scoring.json`](../../config/scoring.json) dentro de `custo_essencial_mensal`, mas nenhum KPI, gap, ou recomendação ancorada em proteção.

**AUVP (Raul Sena) tem 4 pilares formais — Reserva → Proteção → Patrimônio → Renda.** Mathoms cobre 3 (S2 Reserva, S4 Patrimônio, S3 Renda) e omite o segundo. Cerbasi posiciona seguro como gestão de risco familiar (3-5% da renda em proteção total quando há dependentes). Perini é mais lateral mas reconhece seguro de vida como capital protetor de renda projetada.

**Esta ADR formaliza S_PROTECAO como 4º pilar do relatório**, posicionado **entre S2 (Reserva) e S4 (Patrimônio)** seguindo ordem AUVP — não como anexo informativo.

Co-design `financial-planner` (2026-05-21) consolidou KPIs, faixas de sinal, copy CRC, e estratégia de gap qualitativo (seguros ausentes).

## Decisão

Adotar **card S_PROTECAO no relatório nativo React com 4 KPIs V1, 3 subgrupos visuais (Bens / Pessoas / PJ), posicionamento AUVP-coerente, linguagem CRC, e gap qualitativo de seguros ausentes**.

### D1 — Posicionamento AUVP-coerente

Ordem visual do relatório passa a ser:

```
S1  Capa / executive summary
S2  Reserva de Emergência (AUVP pilar 1)
S_PROTECAO  Proteção Patrimonial (AUVP pilar 2) ← NOVO
S4  Patrimônio (AUVP pilar 3)
S3  Renda (AUVP pilar 4)
S5  Orçamento / Fluxo de Caixa
S6  Dívidas
S7  Independência Financeira
S8  Previdência (com cross-link para S_PROTECAO — componente de proteção)
```

Mudança em [`config/report_layout.yaml`](../../config/report_layout.yaml) (codegen [[ADR-076]] regenera TS + Python).

S_PROTECAO tem **mesma hierarquia tipográfica** dos outros pilares — não é "extras", é pilar.

### D2 — 4 KPIs canônicos V1

| KPI | Função | Cálculo |
|---|---|---|
| **G — Prêmio total anual + decomposição** (hero KPI) | "Quanto pago de seguro no total?" | Σ(`premio_total_brl`) de apólices vigentes em `data_referencia`; pizza por tipo (auto / residencial / vida V2 / saúde V2) |
| **B — % renda anual em prêmios** | "Estou gastando muito/pouco?" | Σ(prêmios) / `renda_anual_liquida` (ancorado Cerbasi 1-5%) |
| **F — Seguros ausentes** (qualitativo) | "Que pilar de proteção está descoberto?" | Heurística por categoria — vida, saúde, RC familiar (V2). Sem score numérico; flag binária com copy CRC |
| **C — Gap de cobertura por bem** (auto V1, residencial V2) | "Onde estou sub-segurado?" | Por veículo: `(valor_fipe - lmi_brl) / valor_fipe`. Residencial V2 quando integrar valor de reconstrução via CUB regional |

**Descartados em V1 (movidos para V2 condicional):**

- **A — % patrimônio coberto** — denominador problemático (investimentos financeiros não são "seguráveis"); vira ratio enganoso. Reavaliar V2.
- **D — Multi-corretor warning** — vira nota neutra (Q5 abaixo), não KPI.
- **E — Bônus em risco** — exige modelar histórico de renovação + classe bônus por seguradora. V2.

### D3 — Faixas de sinal + copy CRC

Toda copy é **CRC** (considere / vale avaliar / verifique) — zero verbo prescritivo ("deve", "precisa", "recomendamos"). [[ADR-199]] persona Perini/Cerbasi/AUVP em E6-parecer aplica regra paralela.

#### KPI G (Prêmio total anual) — descritivo

Sem faixa. Pizza decomposta + total mensal equivalente. Copy:

> "Você investe R$ {total_anual} por ano em proteção patrimonial, distribuído entre {decomp_top_3}."

#### KPI B (% renda em prêmios) — ancorado Cerbasi

| Faixa | Sinal | Copy |
|---|---|---|
| `< 1%` | atenção | "Investimento em proteção abaixo do típico para perfil com patrimônio diversificado — vale avaliar se há pilares descobertos." |
| `1% – 3%` | ok | "Investimento em proteção dentro da faixa observada para o perfil." |
| `3% – 5%` | ok-forte | "Pilar de proteção bem dimensionado." |
| `> 5%` | atenção | "Investimento elevado — vale revisar sobreposições de cobertura entre apólices." |

Referência metodológica: Cerbasi recomenda 1-5% conforme estrutura familiar (dependentes + dívida + patrimônio).

#### KPI C (gap de cobertura por bem auto V1)

| Gap | Sinal | Copy |
|---|---|---|
| `< 10%` | ok | "Cobertura próxima ao valor de mercado." |
| `10% – 25%` | atenção branda | "LMI R$ {lmi} está {gap}% abaixo do valor FIPE R$ {fipe} — considere revisar na renovação." |
| `> 25%` | atenção | "LMI R$ {lmi} está significativamente abaixo do valor FIPE R$ {fipe} — vale conversar com seu corretor sobre ajuste." |

#### KPI F (seguros ausentes) — binário com gating heurístico

Gating heurístico (V1 implementa **só Vida e Saúde**):

- **Vida** flag se:
  - `(há dependentes em family_members com idade < 18)` **OU**
  - `(há cônjuge sem renda própria identificada)` **OU**
  - `(passivo / patrimônio_líquido > 30%)`
  - **E** ausência de `apolice` com `bens_segurados[*].tipo == "pessoa"` e `cobertura.tipo == "vida"`

  Copy: "AUVP e Cerbasi recomendam avaliar seguro de vida quando há dependentes financeiros ou dívida significativa. Não identificamos apólice de vida ativa — vale considerar."

- **Saúde** flag se:
  - `(sem dedução de saúde em E1.6 IRPF rendimentos_dedutiveis[])` **E**
  - `(sem categoria 'saude' significativa em E4 por 3+ meses)`

  Copy mais branda: "Não identificamos cobertura de saúde nos documentos analisados. Verifique se está coberto via PJ/empresa, ou se vale ativar plano individual."

- **RC familiar, RD profissional, AP** — V2 (exige perfil profissional via [[ADR-236]] BusinessProfile).

### D4 — 3 subgrupos visuais dentro do card único

Card **único** S_PROTECAO com 3 subgrupos:

```
S_PROTECAO — Proteção Patrimonial
├─ KPIs (G hero + B faixa + F gap qualitativo)
├─ Subgrupo Bens
│   ├─ Auto (tabela com LMI + FIPE + gap C por veículo)
│   └─ Residencial (tabela LMI nominal incêndio V1; valor reconstrução V2)
├─ Subgrupo Pessoas (V2)
│   ├─ Vida (capital segurado + beneficiários)
│   ├─ Saúde (rede + carências)
│   └─ Acidentes Pessoais (capital morte/invalidez)
└─ Subgrupo PJ (V2)
    └─ Empresarial (patrimônio PJ + RD)
```

V1 ativa Bens (Auto + Residencial); Pessoas e PJ renderizam **placeholder** "Não há apólices identificadas neste subgrupo. Vale considerar — ver gap em KPI F."

### D5 — Status de vigência por apólice

Cada linha de apólice tem **status visual**:

| Status | Critério | Tom visual |
|---|---|---|
| **vigente** | `vigencia_fim > hoje + 30d` | neutro |
| **vencendo** | `hoje < vigencia_fim ≤ hoje + 30d` | atenção (amarelo) |
| **vencida** | `vigencia_fim < hoje` | crítico (vermelho) — copy: "Apólice vencida em {data}. Atualize com a nova vigência para manter cobertura no relatório." |

Não é KPI numérico — é estado de dados que afeta confiança no card.

### D6 — Multi-corretor neutro com nota (não warning)

Mostrar lista de corretoras como **metadata** ("3 corretoras: Corretora Exemplo 1, Corretora Exemplo 2, Corretor PF Exemplo"), **sem warning**. Multi-corretor pode ser bom (concorrência, melhores prêmios por especialidade) ou ruim (fragmenta poder de negociação) — depende do contexto.

V2 condicional: detectar **mesma seguradora em múltiplas corretoras** (perde bônus consolidado por CPF) → flag.

### D7 — Cross-link com S8 Previdência

S8 (Previdência) já existe e cobre PGBL/VGBL ([[ADR-189]]). Previdência tem **componente de proteção** (capital para beneficiários em caso de morte do titular) que não é elegível como apólice de vida tradicional.

Card S_PROTECAO inclui nota textual:

> "Sua previdência privada (S8) também tem componente de proteção patrimonial — capital para beneficiários em sinistro. Considere ao avaliar cobertura total de vida."

Sem duplicar KPIs entre cards.

### D8 — Schema do payload em E5

Adicionar bloco `protecao_patrimonial` em `analise_financeira` (E5):

```python
class ProtecaoPatrimonial(BaseModel):
    premio_total_anual_brl: Decimal
    premio_decomposicao: dict[Literal["auto", "residencial", "vida", "saude", "ap"], Decimal]
    pct_renda_anual: Decimal  # B
    bens_com_gap_cobertura: list[BemGapCobertura]  # C
    gap_qualitativo: list[GapQualitativo]  # F
    apolices_vigentes: list[ApoliceResumo]
    apolices_vencendo: list[ApoliceResumo]
    apolices_vencidas: list[ApoliceResumo]
    corretoras_count: int
    seguradoras_count: int
```

Schema JSON novo em `config/schemas/protecao_patrimonial.schema.json`. Validação via hook pós-write em `DBArtifactStore` ([[ADR-212]]).

### D9 — Fórmulas registradas em FORMULAS.md

Adicionar entradas em [`docs/reference/FORMULAS.md`](../reference/FORMULAS.md):

- `protecao.pct_renda` = `Σ(premio_total_brl apolice vigente) / renda_anual_liquida`
- `protecao.gap_bem_auto` = `(valor_fipe_dezembro_atual - lmi_brl_casco) / valor_fipe_dezembro_atual`
- `protecao.flag_vida` = expressão booleana D3 KPI F
- `protecao.flag_saude` = expressão booleana D3 KPI F

Registrar fórmulas **antes** de implementar — gate G2 abaixo.

## Gates

- **G1** — [[ADR-239]] entregue ([`vehicles` table + `apolice` schema + FIPE refresh]) antes do PR1 desta lane.
- **G2** — Fórmulas registradas em `FORMULAS.md` antes de implementar card.
- **G3** — `report_layout.yaml` atualizado + codegen TS/Pydantic ([[ADR-076]]) verde.
- **G4** — `protecao_patrimonial.schema.json` validado pelo hook pós-write [[ADR-212]].
- **G5** — `family_members.json` referenciado para gating do KPI F vida — sem dados, flag não dispara (degrada gracioso).
- **G6** — Goldens E2E: 3 cenários — (a) workspace só com seguros de bens (caso owner), (b) workspace sem nenhuma apólice (placeholder + gap F flag), (c) workspace com apólice combinada (subgrupo Bens com 2 linhas).
- **G7** — UI review (manual): linguagem CRC validada (zero "deve/precisa"), hierarquia tipográfica idêntica aos outros pilares S2/S3/S4, status de vigência visível.
- **G8** — E6-parecer ([[ADR-199]]) ganha narrativa de proteção quando há gap qualitativo significativo (KPI F flag) — extensão do prompt persona AUVP/Cerbasi.

## Implementação

Detalhe em [[TRACK-a19-l1-card-protecao]] (~6-8d eng, 4 PRs sequenciais).

PR de Proposto desta ADR inclui apenas: este arquivo + [[ADR-239]] + estrutura de Sprints A18/A19 + changelogs. **Nenhum código de runtime.**

## Não-objetivos

- **Card de Vida / Saúde funcional V1** — schema e placeholder existem; tabelas e KPIs viram quando V2 (Sprint A20+ condicional).
- **Card PJ proteção empresarial** — V2 com [[ADR-236]] integração BusinessProfile.
- **Valor de reconstrução residencial via CUB regional** — V2; V1 mostra LMI nominal incêndio.
- **Franquia / LMI ratio (proteção efetiva real)** — V1 mostra apenas LMI; V2 calcula `franquia/LMI` como sinal.
- **Bônus em risco ao renovar** — V2 com modelagem de histórico de renovação inter-seguradora.
- **Sinistro / indenização recebida** — placeholder no schema [[ADR-239]] D2; UI V2 quando integrar com [[ADR-238]] (IR sobre indenização).
- **Mesma seguradora em múltiplas corretoras** (gap bônus) — V2.
- **Recomendação de produto específico** — Mathoms **nunca** recomenda "compre seguro X da seguradora Y". Linguagem CRC só sinaliza categoria ausente.

## Riscos

- **R1 — Owner perceived "vendedor de seguros".** Mitigado por D3 (linguagem CRC estrita + D8 E6-parecer prompt instrui a não recomendar produto específico).
- **R2 — Reposicionamento de cards quebra layout existente.** Mitigado por G3 (codegen + visual review antes de mergear).
- **R3 — `family_members.json` ausente para alguns workspaces.** Mitigado por G5: sem dados, flag F vida não dispara silenciosamente.
- **R4 — V2 (vida/saúde) sem schema preparado.** Mitigado por [[ADR-239]] D2 — discriminated union antecipa em V1.
- **R5 — Status "vencida" gera ruído permanente para apólices arquivadas.** Mitigado por filtro `archived_at IS NULL` + retenção temporal [[ADR-239]] D7 (5 anos pós-vigência).

## Alternativas consideradas

- **A1 — Tratar proteção como anexo informativo (não pilar).** Rejeitado: incoerência metodológica AUVP — Proteção é pilar formal, não anexo. Owner adota AUVP como referência produto.
- **A2 — 3 cards separados (S_PROTECAO_BENS / S_PROTECAO_PESSOAS / S_PROTECAO_PJ).** Rejeitado: fragmenta sinal narrativo; AUVP é "pilar Proteção" indivisível. Subgrupos visuais (D4) resolvem diferença de KPIs sem fragmentar seção.
- **A3 — KPI "% patrimônio coberto" como hero.** Rejeitado: denominador problemático (investimentos não são "seguráveis"), vira ratio enganoso.
- **A4 — Flagar agressivamente (recomenda produto).** Rejeitado: viola CRC, parece vendedor.
- **A5 — Não flagar ausência (sem KPI F).** Rejeitado: omite pilar AUVP; vira catálogo, não diagnóstico.
- **A6 — Multi-corretor warning ativo em V1.** Rejeitado: contexto-dependente; vira nota neutra. V2 detecta caso real de gap de bônus.
- **A7 — Manter ordem visual atual (S_PROTECAO depois de S4/S3).** Rejeitado: contradiz hierarquia AUVP que Mathoms usa como argumento de produto.

## Entrega — L1 (S_PROTECAO V1)

Lane [[A19.l1]] entregue em 4 PRs squash-mergeados em `main` (todos CI verde):

- **P1** [#430](https://github.com/davidrobert/mathoms/pull/430) — `protecao_patrimonial.schema.json` (wire string decimal, validado via hook DBArtifactStore.write) + 4 fórmulas em `docs/reference/FORMULAS.md` (G2 gate atendido) + `ProtecaoAnalyzer` puro (sem DB) + 20 testes em `tests/test_protecao_analyzer.py` cobrindo 3 cenários G6.
- **P2** [#432](https://github.com/davidrobert/mathoms/pull/432) — `config/report_layout.yaml` ganha seção `S_PROTECAO` entre S2 e S3 (`enabled: false` até P3 ligar — evita break visual) + codegen TS/Pydantic regenerado.
- **P3** [#435](https://github.com/davidrobert/mathoms/pull/435) — componente React `S_ProtecaoSection.tsx` + 4 sub-componentes (`ProtecaoKpiHero`, `ProtecaoGapVeiculos`, `ProtecaoGapQualitativo`, `ProtecaoApolices`) + tipos TS + 17 testes Vitest cobrindo 3 cenários G6 + edge cases + faixas Cerbasi parametrizadas.
- **P4** (este PR) — extensão E6-parecer (instrução D10 — proteção patrimonial com regras CRC ADR-240 D3) + bump `PROMPT_VERSION` 1.1.0→1.2.0 + telemetria `mathoms.relatorio.protecao_rendered` (kpis_status, has_gap_vida/saude, has_apolice_vencida — sem PII) + flip ADR-240 → `Decidido (Sprint A19 L1)` + lane shipped.

**Padrão arquitetural validado (replicar em V2):**

- **Domain analyzer puro** + **schema JSON validado** + **codegen TS/Pydantic** (ADR-076) + **componente React modular** (1 section + 4 sub-componentes) + **telemetria emitida no analyzer** (não no React — facilita métricas server-side).
- **Discriminated Union no payload** (`gap_qualitativo[].categoria`) antecipa V2 (vida, saúde + rc_familiar, rd_profissional, ap como placeholders V2) sem migration breaking.
- **Empty states** em cada sub-componente + degradação graceful no nível da section (retorna `null` quando `protecao_patrimonial=null`).
- **CRC strict** em copy de UI + instrução D10 no parecer LLM (sem prescritivo; sem recomendação de produto).

**Débito conhecido (V2 candidates):**

- **P3.1** — E2E `@critical` Playwright (`frontend/e2e/protecao.spec.ts`) — 3 cenários G6 com interação real no relatório. Não bloqueia V1 (Vitest cobre componente; E2E garante integração shell).
- **P2.1** — Reorderação S3↔S4 para ordem AUVP completa (`S2 → S_PROTECAO → S4 → S3 → S8`). Requer visual review explícito de snapshots PDF. Sub-task isolada.
- **Card vida/saúde funcional V1** — schema + chips placeholder existem; tabela com capital segurado + beneficiários + rede credenciada fica em V2 (Sprint A20+ condicional a apólices reais de vida/saúde).
- **`flag_vida` heurístico** — gating depende de `family_members` populado (gate G5 garante degradação graceful quando ausente). V2 pode integrar dependentes IRPF via E1.6.

## Emenda 2026-08-08 — título user-facing deixa de atribuir metodologia

**O que muda:** só o título renderizado da seção 2.5.

| | Antes | Depois |
| --- | --- | --- |
| `config/report_layout.yaml` → TOC | "Proteção Patrimonial — Pilar AUVP" | **"Seguros — Cobertura Contratada"** |
| `S_ProtecaoSection.tsx` → heading | "Proteção Patrimonial — 4º Pilar" | **"Seguros — Cobertura Contratada"** |

**O que NÃO muda:** id `S_PROTECAO`, chave de payload `protecao_patrimonial`,
`protecao_analyzer.py`, os KPIs G/B/F, o posicionamento entre S2 e S4, e toda a
atribuição interna deste documento — §13.4 do
[COPY_GUIDELINES](../reference/COPY_GUIDELINES.md) permite, e os esboços de
layout acima seguem válidos como nome de domínio.

**Por quê.** "Pilar AUVP" é marca de curso sem licença e chegava ao cliente pela
entrada de índice do relatório — §13.1, bloqueante. O gate `sigilo-terms` não
pegava: o título nasce em config e chega à UI por codegen ([[ADR-076]]), fora das
duas surfaces que o hook cobria. O PR fecha o furo com surface própria
(`dev/_sigilo_copy_yaml.py`).

**Por que não "Proteção Patrimonial" nu** (recusado por `product-designer` +
`financial-planner`): em PT-BR o termo lê primeiro como *blindagem patrimonial*
(holding, sucessão, credores) e, no jargão SUSEP, como *ramo patrimonial* = bens
**em oposição a** pessoas. Sucessão/ITCMD mora na S9 ([[ADR-192]]), então o termo
apontaria para a seção que ele não titula; e a V2 desta ADR (D4: vida/saúde/AP)
o tornaria ainda menos exato. Registro da substituição em COPY_GUIDELINES §13.2.

**Não fecha D3.** Continua aberto que o KPI F (`gap_qualitativo`) afirma ausência
de cobertura lendo **apenas** apólice extraída de documento, enquanto a S9 lê o
aggregate `Protection` ([[ADR-192]] D1/D2) — workspace que cadastra apólice sem
subir PDF vê "coberto" na S9 e "não identificamos" aqui. A correção de domínio
(afirmação de ausência sobre a **união** das evidências) é emenda futura a D3,
com dono `financial-planner` + `senior-cto`, e deve preceder o flip de
`enabled: true` decidido na [[A40.l7]].
