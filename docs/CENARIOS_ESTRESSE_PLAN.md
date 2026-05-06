# Cenários de Estresse — plano canônico

> **Status:** 🚧 Em execução · **Iniciado:** 2026-05-06 · **Sprint host:** A8 (segue pós-Onda 7/8/9)
>
> **Owner:** principal + 4 especialistas (financial-planner · product-designer · senior-cto · data-engineer)
>
> **Branches alvo:** `agent/cenarios-estresse-{docs,pr1,pr2,pr3,pr4,pr5}/<timestamp>`
>
> **Resumo executivo:** remover do produto **toda referência família-específica** (Mariana, NCLEX, Green Card, EB2-NIW, F1/F2) que entrou na fase de prototipagem; preservar como feature **universal** apenas o cenário "Cônjuge sem trabalhar", generalizado, com **gate de elegibilidade no domain service** e **APP_C "Cenários de Estresse"** que **só aparece quando há cenário elegível** (numeração A/B/C/D/E permanece estável).

---

## Sumário

- [1. Motivação](#1-motivação)
- [2. Decisões fixadas](#2-decisões-fixadas)
- [3. Especialistas consultados](#3-especialistas-consultados)
- [4. Escopo](#4-escopo)
  - [4.1. Sai do produto](#41-sai-do-produto)
  - [4.2. Fica como feature universal](#42-fica-como-feature-universal)
- [5. Mapa de superfície](#5-mapa-de-superfície)
- [6. Plano de PRs](#6-plano-de-prs)
  - [PR0 · docs + plano](#pr0--docs--plano)
  - [PR1 · rename schema](#pr1--rename-schema-cenarios_mariana--cenarios_conjuge)
  - [PR2 · gate de elegibilidade + analyzer 1-cenário](#pr2--gate-de-elegibilidade--analyzer-1-cenário)
  - [PR3 · frontend + APP_C "Cenários de Estresse"](#pr3--frontend--app_c-cenários-de-estresse)
  - [PR4 · deletar Modo USA](#pr4--deletar-modo-usa-u1u4)
  - [PR5 · limpeza](#pr5--limpeza-final)
- [7. ADRs novas](#7-adrs-novas)
- [8. Backlog futuro](#8-backlog-futuro--cenários-2-e-3)
- [9. Critério de aceite global](#9-critério-de-aceite-global)
- [10. Glossário](#10-glossário)

---

## 1. Motivação

O Mathoms entrou em fase de produto com um **cliente piloto** (família do owner) que tem características muito específicas: cônjuge enfermeira buscando licença NCLEX nos EUA, processo de Green Card via EB2-NIW, mudança internacional planejada. Durante a prototipagem, esses contextos viraram **estruturas hardcoded no código**:

- Modo USA inteiro do relatório (U1-U4) — Mudança EUA F1/F2, Green Card EB2-NIW, NCLEX Roadmap, Simulação Mariana Sem Trabalhar
- 3 cenários hardcoded em `cenarios_conjuge_analyzer.py`: `("Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card")`
- Charts/cards: `mariana_cenarios`, `mariana_cenarios_usa`, `simulacao_mariana`, `nclex_roadmap`, `custos_f1f2`, `cenarios_cambiais`
- Chave de payload `cenarios_mariana` (workspace-dependent: vem de `f"cenarios_{_CONJUGE_KEY}"`)
- Strings em `config/methodology.md`, `config/report_spec.md`, `config/prompts/*.yaml`, copy de UI

ADR-151 já estabeleceu doutrina: **modos opcionais sem cliente real são lastro**. Modo Tático foi removido em 2026-04-26; modo USA tem o mesmo perfil de risco e idade similar de uso.

A regra de domínio "cenário cônjuge sem trabalhar" é, no entanto, **universal e útil** — corresponde ao "stress test de renda familiar / planejamento de contingência conjugal" (Cerbasi) e "stress test de aporte sobre regra dos 300" (Perini). Será preservada como capability genérica, ativada por gate de elegibilidade.

---

## 2. Decisões fixadas

### D1 · Escopo MVP — apenas cenário "Cônjuge sem trabalhar"

**Decisão:** **Opção A** — entrega só "cônjuge sem trabalhar" generalizado.

Cenários "Perda de renda do titular" e "Aposentadoria antecipada" propostos pelo financial-planner ficam **documentados como backlog futuro** (§8) com regra de gatilho pronta, mas não entram nesta entrega. Justificativa: pedido literal do owner foi "remover prototipagem"; expandir para 3 cenários é escopo creep que dilui a entrega e aumenta risco de regressão.

### D2 · Título — "Cenários de Estresse"

**Decisão:** seção APP_C renomeada para **"Cenários de Estresse"** (no YAML SOT e na UI).

Trade-offs avaliados:
- "Cenários de Sensibilidade" (atual no YAML) — jargão DCF/valuation, confunde HNW
- "Cenários Alternativos" (atual na UI) — vago, não comunica gravidade
- "Stress Tests" — destoa do PT-BR
- "Cenários de Contingência" — empático mas burocrático
- ✅ **"Cenários de Estresse"** — termo CVM/Susep; formal, traduzido, reconhecível por leitor HNW que vê em previdência/seguros; dá peso sem alarmismo

### D3 · Visualização comparativa lado-a-lado

**Decisão:** abandonar tabela 1-linha; renderizar **cenário base vs. cenário de estresse** com delta explícito + parágrafo "Leitura:" explicando o impacto.

```
Premissa testada: Cônjuge sem renda do trabalho

Cenário base                 →  Cenário de estresse
Aporte mensal  R$ 12.000          R$ 18.500   (+54%)
Prazo até IF   14a 3m             19a 8m      (+5a 5m)
Ano IF         2040               2046        (+6 anos)

Leitura: a ausência da segunda renda exige aporte 54% maior
ou estende a IF em 6 anos. Margem de segurança recomendada:
reserva específica de XX meses de despesa do cônjuge.
```

Threshold para futuro: ≥3 cenários → tabela com coluna delta; ≤2 → cards comparativos.

### D4 · Comportamento da seção quando vazia

**Decisão:** **hide-when-empty com numeração estável** — se gate retorna `False` para o workspace, APP_C **não aparece no TOC nem no corpo**, mas **APP_D continua rotulado "D"** (numeração A/B/C/D/E é literal no YAML, não recomputada). Cliente que compara dois ciclos consecutivos do mesmo planner vê numeração estável; quem ligou/desligou o gate é responsabilidade do planner explicar.

Regra: `report_layout.yaml` mantém APP_C declarada com flag `optional: true`; codegen emite a seção sempre, mas o componente retorna `null` quando `cenarios_conjuge` ausente, **e** o TOC consulta a mesma condição.

### D5 · Onde mora o gate de elegibilidade

**Decisão:** **pipeline E5 emite ou omite o bloco** (uma camada decide). Frontend só checa presença (`if (!data.cenarios_conjuge) return null`). Ancora em ADR-143 (rules-as-code).

---

## 3. Especialistas consultados

| Agente | Sessão | Contribuição principal |
|---|---|---|
| `financial-planner` | 2026-05-06 | Regra de elegibilidade (≥2 rendas + secundária ≥15% do total + meta IF presente); validação universal sob Cerbasi/Perini; output esperado (Δ vs base, ponte com reserva); cenários 2 e 3 como backlog |
| `product-designer` | 2026-05-06 | Padrão de hide-when-empty com numeração estável; título "Cenários de Estresse"; copy do subtítulo; visualização comparativa; critério de a11y (delta com sinal+cor) |
| `senior-cto` | 2026-05-06 | Decisão de **deletar modo USA inteiro** (ancorando em ADR-151); rename de chave universal `cenarios_conjuge`; sequência rígida de 5 PRs com fallback dual-key transitório; 3 ADRs |
| `data-engineer` | 2026-05-06 | **5 sites do producer** (não 1); sem schema migration de DB; LLM cache invalida sozinho; OpenAPI snapshot inalterado; aviso sobre 2 chaves distintas (`cenarios_{conjuge_key}` ≠ `{conjuge_key}_cenarios` — segundo fora de escopo); script de backfill operacional em vez de dual-key permanente; test de regressão a inverter (`test_e5_serialization.py:258-265`) |

---

## 4. Escopo

### 4.1. Sai do produto

#### 4.1.1. Modo USA inteiro (U1-U4)

**Decisão de senior-cto:** `caminho (a)` — deletar inteiro. Não generalizar para "Modo Internacional" sem segundo cliente real. ADR-151 já estabeleceu doutrina; modo USA é o que sobrou de não-Estratégico desde a remoção do Tático (2026-04-26).

**Arquivos:**
- `config/report_layout.yaml:101-106` (nav `usa:`), `:477-545` (bloco `usa:` completo: U1/U2/U3/U4 + comentários), `:631-681` (chart maps USA-only `mariana_cenarios_usa`, etc.)
- `frontend/src/components/report/sections/UsaSections.tsx` (todo o arquivo: U1MudancaEuaSection, U2GreenCardSection, U3NclexSection, U4SimulacaoMarianaSection)
- `frontend/src/components/report/MigratedSection.tsx:22-25,72-79` (imports + roteamento U1/U2/U3/U4)
- `frontend/src/components/report/ReportShell.tsx:74-117` (`selectSections('usa')` + `nav.usa`)
- `frontend/src/components/report/ReportModeContext.tsx` (mode `'usa'`)
- `frontend/src/components/report/ReportModeProvider.tsx:19-24` (`?mode=usa` deep-link, comentário "Estratégico + USA")
- `frontend/src/components/report/ReportSection.tsx:10` (mode prop `"estrategico" | "usa"`)
- `frontend/src/components/report/shell/ReportTopNav.tsx`, `shell/ModeToggle.tsx`, `shell/ReportActions.tsx` (toggles USA)
- `frontend/tests/components/report/usaSections.test.tsx` (todo)
- `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts` (snapshots USA)
- `frontend/tests/e2e/reports/a11y.@critical.spec.ts` (asserts USA)

#### 4.1.2. Cenários família-específicos

- Labels `"Com NCLEX"` e `"Com NCLEX + Green Card"` no `cenarios_conjuge_analyzer._LABELS`
- Defaults `renda_rn_minima_usd`, `renda_rn_maxima_usd`, `cambio_usd_brl`, `from_configs(... cambio_usd_brl=...)` (analyzer fica BRL-only)
- Helpers `_resumo_s2`, `_resumo_s3` em `cenarios_conjuge_analyzer.py`
- Premissas `renda_nclex_usd`, `renda_nclex_brl`, `renda_gc_usd`, `renda_gc_brl`, `recovery_nclex_pct`, `recovery_gc_pct` (saem do output do analyzer)
- `tests/unit/pipeline/test_cenarios_conjuge_analyzer.py` — reduzir testes para 1 cenário

#### 4.1.3. Charts/cards família-específicos órfãos pós-USA

- `mariana_cenarios` (chart S3) — substituído por chart genérico `cenarios_conjuge` em PR3
- `mariana_cenarios_usa` (chart U4) — deletado em PR4 (vai com modo USA)
- `simulacao_mariana` (card U4) — deletado em PR4
- `nclex_roadmap` (card U3) — deletado em PR4
- `custos_f1f2` (chart U1) — deletado em PR4
- `cenarios_cambiais` (chart U2/APP_C — `enabled: false`) — deletado em PR4

#### 4.1.4. Strings em copy/docs

- `config/methodology.md:97-100` (E5.6 Plano EUA → menciona F1/F2, Green Card, NCLEX)
- `config/report_spec.md` (várias linhas: 191, 200, 312, 454, 574, 924, 964-1132, 1187, 1336, 1468-1644, 1612-1701, 1763) — mencionar Green Card, NCLEX, Mariana, F1/F2 em texto exemplificativo
- `config/prompts/section_summaries.yaml:470-480` (prompt U2 Green Card)
- `config/prompts/chart_conclusions.yaml:80-84` (`mariana_cenarios`, `mariana_cenarios_usa`)
- Comentários em `config/report_layout.yaml:478-581,631-681`
- Comentários em `frontend/src/components/report/sections/ApendicesSections.tsx:155-158`

**Excluídas do escopo de remoção (ficam):**
- `_archive/` — manual histórico
- `tests/_llm_stage_fixtures.py:80-82` ("Mariana Ferreira Campos") — fixture de teste, não produto
- Workspace `members.json` real do owner — é dado pessoal, não código
- `tests/test_e5n_builder_decomposition.py:76-215` (referencias `Green Card holder`, `cm_renda_nclex_brl`) — **avaliar PR2/3:** se mock do E5.N, atualizar para fixtures genéricas; se golden, manter

### 4.2. Fica como feature universal

#### 4.2.1. Cenário "Cônjuge sem trabalhar" generalizado

- Analyzer reduzido a **1 cenário**: `_LABELS = ("Sem Trabalhar",)` (ou nome equivalente em PT mais limpo — discussão em PR2)
- Premissas mantidas: `meta_if`, `investivel_atual`, `retorno_real_anual_pct`, `aporte_base`, `fator_reduzido`, `salario_{conjuge_key}_clt_brl`
- Saída legacy preserva keys: `labels`, `aportes`, `prazos_if`, `anos_if`, `idade_{titular_key}_if`, `premissas`, `cenarios`

#### 4.2.2. Chave de payload estável `cenarios_conjuge`

- `pipeline/domain/services/e5_serialization.py:266` — chave passa de `inputs.cenarios_conjuge_key` (dinâmica) para literal `"cenarios_conjuge"` (PR1)
- `pipeline/domain/services/narrativas/context.py:30,59,67` — `key_cenarios_conjuge`/`key_cenarios_section` viram constantes (PR1)
- `pipeline/stages/review_finances.py:59` — atualizar para `"cenarios_conjuge"` (PR1)
- `backend/app/services/section_summary_orchestrator.py:239,245` — `S7`/`T5` keys (PR1)
- Frontend: dual-key fallback em PR1 (`data.cenarios_conjuge ?? data.cenarios_mariana`); fallback removido em PR3
- E2E fixture `frontend/tests/e2e/fixtures/reports/medium.json:117` — atualizar (PR1)

#### 4.2.3. Gate de elegibilidade

Função pura no domain service (PR2):

```python
# pipeline/domain/services/cenarios_conjuge_analyzer.py
def should_render_conjuge_scenarios(*, family_members, fluxo, goals) -> bool:
    """Cenário 'cônjuge sem trabalhar' é elegível para o workspace?

    Critérios universais (Cerbasi/Perini):
    - meta IF presente (>0)
    - ≥2 membros com renda recorrente
    - renda do cônjuge ≥15% da renda familiar total
      (abaixo disso, pausa não muda materialmente o plano)
    """
```

Decisões de domínio (financial-planner):
- Solteiro / 1 renda → `False` (sem o que stressar)
- Casal sem meta IF → `False` (não há âncora de impacto)
- Casal 95/5 → `False` (impacto < 15%, não vale o ruído na seção)
- Casal 70/30 ou 60/40 → `True` (cenário relevante)

#### 4.2.4. Apêndice C "Cenários de Estresse"

- YAML: `id: APP_C`, `title: "Cenários de Estresse"`, flag `optional: true`
- Componente: retorna `null` quando `data.cenarios_conjuge` ausente; quando presente, renderiza visualização comparativa (D3)
- TOC dinâmico: lê mesma condição; quando ausente, omite linha (mas `D` continua "D")
- Subtítulo: `"Como o seu plano se comporta se uma premissa central mudar. Não são previsões — são testes de resiliência para validar a margem de segurança do plano atual."`

---

## 5. Mapa de superfície

### 5.1. Pipeline (Python)

⚠️ **Aviso do data-engineer:** **5 sites do producer**, não 1. E **2 chaves distintas** que parecem similares mas são diferentes:
- `cenarios_{conjuge_key}` (top-level do payload, alvo deste rename) ✅
- `{conjuge_key}_cenarios` (chave de seção de narrativas, `key_cenarios_section` em `context.py:67`) — **OUTRO rename, FORA de escopo desta entrega**

| Arquivo | Mudança | PR |
|---|---|---|
| `pipeline/domain/services/cenarios_conjuge_analyzer.py` | Reduzir `_LABELS` para 1 cenário; remover defaults USD/cambio; remover `_resumo_s2/_s3`; adicionar `should_render_conjuge_scenarios()` | PR2 |
| `pipeline/domain/services/e5_serialization.py` | Remover campo `cenarios_conjuge_key` do `E5SerializationInputs` (default já era `"cenarios_conjuge"`); chave vira literal no dict | PR1 |
| `scripts/e5_analyze.py:147` | Remover `_KEY_CENARIOS_CONJUGE = f"cenarios_{_CONJUGE_KEY}"` global | PR1 |
| `scripts/e5_analyze.py:3105` | Remover kwarg `cenarios_conjuge_key=_KEY_CENARIOS_CONJUGE` | PR1 |
| `scripts/e5n_narrativas.py:68` | Remover `_KEY_CENARIOS_CONJUGE` (paralelo ao acima) | PR1 |
| `pipeline/domain/services/narrativas/context.py:30,59` | `key_cenarios_conjuge: str` → fixar literal `"cenarios_conjuge"` | PR1 |
| `pipeline/domain/services/narrativas/context.py:38,67` | `key_cenarios_section=f"{conjuge_key}_cenarios"` — **NÃO mexer** (rename diferente) | — |
| `pipeline/stages/review_finances.py:59` | `"cenarios_mariana"` → `"cenarios_conjuge"` em `_E5_SUBKEYS` | PR1 |
| `scripts/e5_analyze.py:2574-2992,3076-3204` | Caller adaptado a 1 cenário; gate aplicado antes de chamar analyzer | PR2 |

### 5.2. Backend (Python)

| Arquivo | Mudança | PR |
|---|---|---|
| `backend/app/services/section_summary_orchestrator.py:239,245` | `cenarios_mariana` → `cenarios_conjuge` em `_SECTION_KEYS["S7"]` e `["T5"]` (verificar se T5 ainda está em uso pós-ADR-151) | PR1 |
| `backend/app/generated/report_layout.py` | Regenerado via codegen pós-YAML | PR4 |

### 5.3. Frontend

| Arquivo | Mudança | PR |
|---|---|---|
| `frontend/src/components/report/sections/ApendicesSections.tsx:155-253` | APP_C: hide-when-empty + título "Cenários de Estresse" + visualização comparativa + remover `programa_milhas` opcional (sai junto se for família-specific — confirmar) | PR3 |
| `frontend/src/components/report/sections/S3InvestimentosSection.tsx:33,69-72` | Lê `data.cenarios_conjuge`; chart id passa de `mariana_cenarios` para `cenarios_conjuge` | PR3 |
| `frontend/src/components/report/sections/UsaSections.tsx` | **Deletar arquivo inteiro** | PR4 |
| `frontend/src/components/report/MigratedSection.tsx:22-25,72-79` | Remover imports U2/U3/U4 + cases | PR4 |
| `frontend/src/components/report/ReportShell.tsx:74-117` | Remover `selectSections('usa')`, `nav.usa` | PR4 |
| `frontend/src/components/report/ReportModeContext.tsx`, `ReportModeProvider.tsx`, `ReportSection.tsx`, `shell/ModeToggle.tsx`, `shell/ReportTopNav.tsx`, `shell/ReportActions.tsx` | Remover mode `'usa'` | PR4 |
| `frontend/src/types/report-analysis.ts` | Adicionar `cenarios_conjuge?: ContingencyScenario` (tipado); `cenarios_mariana` removido em PR3 | PR1 (adicionar) + PR3 (remover legado) |
| `frontend/src/lib/api/reports.ts` | Refletir tipos | PR1+PR3 |
| `frontend/src/generated/report-layout.ts` | Regenerado via codegen | PR3 (rename chart id) + PR4 (remove USA) |

### 5.4. Config

| Arquivo | Mudança | PR |
|---|---|---|
| `config/report_layout.yaml:101-106` | Remover bloco `nav.usa` | PR4 |
| `config/report_layout.yaml:241,457-460,477-545,631-681` | Renomear `mariana_cenarios` → `cenarios_conjuge` (chart S3); APP_C title `"Cenários de Sensibilidade"` → `"Cenários de Estresse"` + flag `optional: true`; deletar bloco USA inteiro; deletar charts USA-only do map | PR3 (S3 chart + APP_C) + PR4 (USA delete) |
| `config/schemas/report_layout.schema.json` | Verificar se enum de chart_ids/section_ids precisa atualizar (codegen-driven?) | PR3+PR4 |
| `config/methodology.md:97-100` | Reescrever §E5.6 sem F1/F2/Green Card/NCLEX (ou remover seção se inteiramente USA-specific) | PR5 |
| `config/report_spec.md` | Reescrever 12+ linhas de exemplo família-específico → exemplos genéricos | PR5 |
| `config/prompts/section_summaries.yaml:470-480` | Remover prompt U2 (vai com modo USA) | PR4 |
| `config/prompts/chart_conclusions.yaml:80-84` | Remover/renomear `mariana_cenarios`, `mariana_cenarios_usa` | PR3+PR4 |

### 5.5. Tests

| Arquivo | Mudança | PR |
|---|---|---|
| `tests/unit/pipeline/test_cenarios_conjuge_analyzer.py` | Reduzir para 1 cenário; adicionar 4 casos de `should_render`: (a) 1 renda, (b) 2 rendas casal, (c) 2 rendas solteiro, (d) casal sem renda do cônjuge | PR2 |
| `tests/test_e5n_builder_decomposition.py:76-215` | Limpar fixtures família-específicas (Green Card holder, cm_renda_nclex_brl); manter testes da estrutura | PR2 |
| `tests/_llm_stage_fixtures.py:80-82` | **Manter** (fixture de teste, não produto) | — |
| `frontend/tests/components/report/apendices.test.tsx:71-73` | Atualizar fixture `cenarios_mariana` → `cenarios_conjuge` (PR1) e mover testes para nova visualização comparativa (PR3) | PR1+PR3 |
| `frontend/tests/components/report/usaSections.test.tsx` | **Deletar arquivo inteiro** | PR4 |
| `frontend/tests/components/report/dataAdapters.test.ts` | Remover refs USA | PR4 |
| `frontend/tests/e2e/fixtures/reports/medium.json:117` | `cenarios_mariana` → `cenarios_conjuge` (e popular com payload de exemplo) | PR1 |
| `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts` | Remover snapshots USA; adicionar snapshot APP_C "Cenários de Estresse" | PR3 (novo) + PR4 (delete USA) |
| `frontend/tests/e2e/reports/a11y.@critical.spec.ts` | Remover asserts USA; verificar APP_C contraste delta | PR3+PR4 |

### 5.6. Docs

| Arquivo | Mudança | PR |
|---|---|---|
| `docs/CENARIOS_ESTRESSE_PLAN.md` | **Este arquivo** — fonte canônica do plano | PR0 |
| `docs/BACKLOG.md` | Adicionar lane "Cenários de Estresse" no Sprint A8 (ou onda equivalente) | PR0 |
| `docs/CHANGELOG.md` | Entradas por PR | PR1-PR5 (cada um) |
| `docs/DECISIONS.md` | ADR-168, ADR-166, ADR-167 + ToC | PR1, PR2, PR4 |
| `docs/ARCHITECTURE.md §4.1 Domain glossary` | Adicionar `cenarios_conjuge` ao glossário | PR1 |
| `docs/REPORT_PREMIUM_PLAN.md` | Verificar referências a APP_C; atualizar se mencionar título antigo | PR3 |
| `_archive/` (manual histórico) | **Não tocar** | — |

---

## 6. Plano de PRs

> **Ordem rígida.** Cada PR mergeia com `gh pr merge --squash --auto`, suite verde, antes do próximo abrir. Branches `agent/cenarios-estresse-{slug}/<yyyyMMdd-HHmm>`.

### PR0 · docs + plano

**Branch:** `agent/cenarios-estresse-docs/20260506-1430` · **Tipo:** docs-only · **Risco:** baixo

**Escopo:**
- Adiciona `docs/CENARIOS_ESTRESSE_PLAN.md` (este arquivo)
- Adiciona lane no `docs/BACKLOG.md`
- Adiciona entrada no `docs/CHANGELOG.md`

**Critério de aceite:**
- `pre-commit run --all-files` verde
- `python3 dev/check_adr_anchors.py` verde (ADR-168/166/167 ainda não criadas; sem-âncora aceito)
- Auto-merge habilitado (docs-only não exige CI)

### PR1 · rename schema `cenarios_mariana` → `cenarios_conjuge`

**Branch:** `agent/cenarios-estresse-pr1/<ts>` · **Tipo:** schema rename + ADR · **Risco:** médio

**Escopo (atômico — 5 sites do producer + consumers + dual-read frontend):**
- `pipeline/domain/services/e5_serialization.py` — remover campo `cenarios_conjuge_key` do `E5SerializationInputs`; chave literal no dict
- `scripts/e5_analyze.py:147,3105` — remover `_KEY_CENARIOS_CONJUGE` global e kwarg
- `scripts/e5n_narrativas.py:68` — remover `_KEY_CENARIOS_CONJUGE`
- `pipeline/domain/services/narrativas/context.py:30,59` — `key_cenarios_conjuge` literal `"cenarios_conjuge"` (linha 67 `key_cenarios_section` **não tocar**)
- `pipeline/stages/review_finances.py:59` — atualizar `_E5_SUBKEYS`
- `backend/app/services/section_summary_orchestrator.py:239,245` — atualizar `_SECTION_KEYS["S7"]` e `["T5"]`
- `frontend/src/types/report-analysis.ts` — adicionar `cenarios_conjuge?: ...`; `cenarios_mariana` mantido com `@deprecated`
- `frontend/src/components/report/sections/{Apendices,S3Investimentos,Usa}Sections.tsx` — fallback dual-key transitório (`data.cenarios_conjuge ?? data.cenarios_mariana`)
- `frontend/tests/components/report/apendices.test.tsx`, `usaSections.test.tsx`, `e2e/fixtures/reports/medium.json:117` — atualizar fixtures para `cenarios_conjuge`
- Tests Python:
  - `tests/unit/pipeline/test_e5_serialization.py:237` — já alinhado, validar
  - `tests/unit/pipeline/test_e5_serialization.py:258-265` — **inverter** o `test_cenarios_conjuge_usa_key_configuravel` (era prova de que key era variável; vira prova de que é fixa)
  - `tests/test_e5n_builder_decomposition.py:211-215` — atualizar fixtures
- Logging: adicionar `INFO` em `e5_serialization.build_e5_output` (`logger.info("e5.cenarios_key", extra={...})`) — útil para confirmar via Loki/Cloudwatch que prod migrou
- ADR-166: schema estável `cenarios_conjuge` no payload E5
- `docs/CHANGELOG.md` entrada

**Sem mudanças necessárias:**
- ❌ Nenhum schema em `config/schemas/*.schema.json` referencia `cenarios_mariana` (validado por grep direto)
- ❌ Nenhum `MATHOMS_SCHEMA_VERSION` aplicável — payload E5 é dict aberto (`/reports/{id}/data` retorna `JSONResponse` com schema `{type: object}`)
- ❌ `make update-openapi-snapshot` desnecessário
- ❌ Nenhum golden binário em `tests/pipeline/goldens/` prende a chave (apenas unit tests)
- ❌ Sem migration Alembic — `pipeline_artifacts.content_json` é JSON cru sem index sobre a chave

**Política de pipeline_artifacts (operacional, pós-PR1):**
- Workspaces ativos têm artifacts E5 com `cenarios_mariana` no `content_json`. Frontend tem fallback dual-key durante PR1→PR3.
- **Pós-merge PR1 (operação manual):** rodar script `dev/backfill_e5_universal_keys.py` (criado no PR1) que itera workspaces com `last_report_at < PR1_merge_time` e dispara `analyze_finances`. Idempotente.
- LLM cache (ADR-144) **invalida automaticamente** quando key muda (hash de `section_payload`) — re-narração de S7/T5 acontece naturalmente; custo: ~2 chamadas LLM por workspace × N workspaces.
- Após backfill, query de validação:
  ```sql
  SELECT COUNT(*) FROM pipeline_artifacts
  WHERE stage IN ('E5','analyze_finances')
    AND content_json::text LIKE '%cenarios_mariana%';
  -- esperado: 0 antes de mergear PR3 (que remove fallback)
  ```

**Critério de aceite:**
- `pytest tests -q` verde
- `pytest backend/tests -q` verde
- `pytest tests/unit/pipeline/test_e5_serialization.py tests/unit/pipeline/test_e5n_builder_decomposition.py tests/unit/pipeline/test_e5_config_overrides_parity.py -q` verde
- `pre-commit run --all-files` verde
- `cd frontend && npm test -- --run` verde
- Re-run E5 manual em workspace de teste produz `cenarios_conjuge` no JSON
- Frontend lê tanto chave nova (preferida) quanto legada (fallback) sem regressão visual
- Snapshot OpenAPI inalterado (esperado) OU diff esperado committed

### PR2 · gate de elegibilidade + analyzer 1-cenário

**Branch:** `agent/cenarios-estresse-pr2/<ts>` · **Tipo:** domain logic + ADR · **Risco:** baixo (analyzer já é domain service tipado)

**Escopo:**
- `pipeline/domain/services/cenarios_conjuge_analyzer.py`:
  - `_LABELS = ("Sem renda do cônjuge",)` ou label equivalente (TBD em review)
  - Remover `renda_rn_minima_usd`, `renda_rn_maxima_usd`, `cambio_usd_brl` de `CenariosConjugeConfig` defaults e `from_configs`
  - Remover `_resumo_s2`, `_resumo_s3`
  - Reescrever `analyze()` para 1 cenário (mantém forma `CenariosConjugeResult` com `cenarios=(s1,)`)
  - Adicionar `should_render_conjuge_scenarios(*, family_members, fluxo, goals) -> bool` (regra do financial-planner)
  - Atualizar `to_legacy_dict()` para nova shape
- `scripts/e5_analyze.py:2574-2992,3076-3204` — caller aplicar gate antes de chamar analyzer; quando `False`, omitir bloco (`{}` no payload — frontend filtra)
- `pipeline/domain/services/e5_analyzer_adapter.py` — propagar gate
- `tests/unit/pipeline/test_cenarios_conjuge_analyzer.py` — adicionar 4 casos de `should_render` (1 renda, 2 rendas casal, 2 rendas solteiro, casal sem renda do cônjuge)
- `tests/test_e5n_builder_decomposition.py` — limpar fixtures família-específicas
- ADR-167: eligibility gate de cenário do cônjuge no domain service
- `docs/ARCHITECTURE.md §4.1 Domain glossary` — entrada `should_render_conjuge_scenarios()`

**Critério de aceite:**
- `pytest tests -q` verde
- `pytest backend/tests -q` verde
- 4 casos do gate cobertos com fixture mínimo
- Workspace de teste com 1 renda → payload sem `cenarios_conjuge`
- Workspace de teste com 2 rendas 70/30 + meta IF → payload com `cenarios_conjuge` (1 cenário)

### PR3 · frontend + APP_C "Cenários de Estresse"

**Branch:** `agent/cenarios-estresse-pr3/<ts>` · **Tipo:** UI + codegen · **Risco:** baixo

**Escopo:**
- `config/report_layout.yaml`:
  - APP_C: title `"Cenários de Sensibilidade"` → `"Cenários de Estresse"`; flag `optional: true`; subtitle key apontando para copy nova
  - Chart S3: `mariana_cenarios` → `cenarios_conjuge` (chart_canvas_map, chart_titles_map)
  - `enabled: false` no chart `cenarios_cambiais` em APP_C — manter (vai junto em PR4)
- Codegen: `python3 dev/codegen_report_layout.py` regenera `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py`
- `frontend/src/components/report/sections/ApendicesSections.tsx`:
  - Renomear comentário ADR-117/122 (referência a docstring antigo OK)
  - Remover fallback dual-key (lê só `data.cenarios_conjuge`)
  - Implementar **hide-when-empty:** `if (!cenarios) return null;`
  - Título: "Apêndice C — Cenários de Estresse"
  - Subtítulo: copy nova (D2/D3 acima)
  - Visualização: cards comparativos lado-a-lado base vs estresse + parágrafo "Leitura:" (D3)
  - Delta: sinal+cor (a11y AA)
- `frontend/src/components/report/sections/S3InvestimentosSection.tsx:33,69-72` — chart id `cenarios_conjuge`; lê `data.cenarios_conjuge`
- `frontend/src/components/report/UsaSections.tsx` — atualizar `cenarios_mariana` → `cenarios_conjuge` (mesmo que vai morrer em PR4, mantém consistência)
- `frontend/src/components/report/ReportToc.tsx` ou equivalente — TOC dinâmico (omite APP_C quando ausente, APP_D fica "D")
- `frontend/src/types/report-analysis.ts` — remover `cenarios_mariana` legado; tipar `cenarios_conjuge` corretamente
- `frontend/src/lib/api/reports.ts` — remover refs legadas
- `config/prompts/chart_conclusions.yaml:80` — `mariana_cenarios` → `cenarios_conjuge` (PR3); `mariana_cenarios_usa` removido em PR4
- `frontend/tests/components/report/apendices.test.tsx` — testes da nova visualização comparativa
- `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts` — adicionar snapshot APP_C com cenário e sem
- `frontend/tests/e2e/reports/a11y.@critical.spec.ts` — assert contraste delta

**Critério de aceite:**
- `cd frontend && npm test -- --run` verde
- `cd frontend && npm run test:e2e` verde
- Snapshot visual: workspace elegível mostra APP_C; workspace inelegível omite APP_C **e APP_D continua "D"**
- A11y: delta `+5a 5m` em vermelho passa contraste AA (sinal+cor juntos)
- Codegen sem drift (`git diff` em `generated/` consistente)

### PR4 · deletar Modo USA (U1-U4)

**Branch:** `agent/cenarios-estresse-pr4/<ts>` · **Tipo:** delete + ADR · **Risco:** médio (big-bang isolado)

**Escopo:**
- `config/report_layout.yaml`:
  - Remover bloco `nav.usa:` (linhas 101-106)
  - Remover bloco `usa:` inteiro (linhas 477-545)
  - Remover charts USA-only de chart_canvas_map / chart_titles_map / per-section maps (`mariana_cenarios_usa`, `simulacao_mariana`, `nclex_roadmap`, `custos_f1f2`, `cenarios_cambiais`)
- Codegen: `python3 dev/codegen_report_layout.py`
- `frontend/src/components/report/sections/UsaSections.tsx` — **deletar arquivo**
- `frontend/src/components/report/MigratedSection.tsx:22-25,72-79` — remover imports U2/U3/U4 + cases
- `frontend/src/components/report/ReportShell.tsx:74-117` — remover branches USA (`selectSections('usa')`, `nav.usa`, `mode === 'usa'`)
- `frontend/src/components/report/ReportModeContext.tsx` — `ReportMode = 'estrategico'` (modo único)
- `frontend/src/components/report/ReportModeProvider.tsx:19-24` — remover deep-link `?mode=usa`
- `frontend/src/components/report/ReportSection.tsx:10` — `mode?: 'estrategico'`
- `frontend/src/components/report/shell/{ModeToggle,ReportTopNav,ReportActions}.tsx` — remover toggles
- `frontend/tests/components/report/usaSections.test.tsx` — **deletar**
- `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts` — remover snapshots USA
- `frontend/tests/e2e/reports/a11y.@critical.spec.ts` — remover asserts USA
- `frontend/tests/components/report/dataAdapters.test.ts` — remover refs USA
- `config/prompts/section_summaries.yaml:470-480` — remover bloco U2
- `config/prompts/chart_conclusions.yaml:84` — remover `mariana_cenarios_usa`
- ADR-168: Remoção do Modo USA do relatório (supersede parcial ADR-117/123 + conclui agenda ADR-151)
- `docs/CHANGELOG.md` entrada
- Atualizar `docs/REPORT_PREMIUM_PLAN.md` se referencia U1-U4

**Critério de aceite:**
- `pytest backend/tests -q` verde
- `cd frontend && npm test -- --run` verde
- `cd frontend && npm run test:e2e` verde
- `grep -ri "U1MudancaEua\|U2GreenCard\|U3Nclex\|U4Simulacao\|selectSections('usa')\|mode === 'usa'" frontend/src/` → 0 hits
- Codegen sem drift
- ReportMode reduzido a 1 valor

### PR5 · limpeza final

**Branch:** `agent/cenarios-estresse-pr5/<ts>` · **Tipo:** docs/copy cleanup · **Risco:** baixo

**Escopo:**
- `config/methodology.md:97-100` — reescrever §E5.6 sem família-específico (ou remover se inteiramente USA-only)
- `config/report_spec.md` — reescrever exemplos família-específicos (linhas listadas em §4.1.4) com nomes genéricos / placeholders abstratos
- Comentários em `frontend/src/components/report/sections/ApendicesSections.tsx:155-158` — atualizar refs ADR
- Verificar `_archive/` — não tocar; só checar que `grep -ri "Mariana\|NCLEX\|Green Card\|EB2-NIW\|F1/F2"` produtivo está zerado fora de:
  - `_archive/`
  - `tests/_llm_stage_fixtures.py:80-82` (fixture de teste)
  - workspace data (não-rastreado)
- `docs/CHANGELOG.md` entrada de fechamento

**Critério de aceite:**
- `pre-commit run --all-files` verde
- `grep -ri "Mariana\|NCLEX\|Green Card\|EB2-NIW\|F1/F2\|EB2 NIW" config/ pipeline/ scripts/ backend/ frontend/src/ docs/` → 0 hits (excluindo `_archive/`, `tests/_llm_stage_fixtures.py`, este plano e ADRs históricas que mencionam por contexto)
- `grep -ri "cenarios_mariana\|mariana_cenarios" config/ pipeline/ scripts/ backend/ frontend/` → 0 hits

---

## 7. ADRs novas

### ADR-168 — Remoção do Modo USA do relatório

**Sprint host:** A8 (post-Onda 7/8/9) · **Status:** Decidido (PR4) · **Supersedes:** parcial ADR-117/ADR-123 (modos opcionais) · **Relacionada:** ADR-151 (modo Tático removido por mesma rationale)

**Decisão:** Modo USA (U1-U4: Mudança EUA F1/F2, Green Card EB2-NIW, NCLEX Roadmap, Simulação Mariana) removido do produto. Cliente piloto (família do owner) era o único caso real; sem segundo cliente USA, manter abstração custou em superfície de teste, layout YAML, components React, e branches de roteamento.

**Alternativas avaliadas:**
- (a) Generalizar para "Modo Internacional" — `YAGNI` premium; sem segundo cliente real para validar (Portugal D7? EB-5? Bali nômade?), abstração prematura
- (b) Manter U1 ("custos F1/F2") generalizado, deletar U2-U4 — caminho do meio, ainda especulativo
- (c) **Deletar tudo** ✅ — replicar quando cliente real aparecer (~2-3 dias)

**Consequências:**
- ReportMode: `'estrategico' | 'usa'` → `'estrategico'` (modo único)
- `~600 LOC` removidos (UsaSections.tsx, tests, snapshots, refs)
- Cenário "cônjuge sem trabalhar" sobrevive como capability genérica em APP_C (ADR-167)
- Recriar Modo Internacional quando segundo cliente justificar custa ~1 sprint

### ADR-166 — Schema estável `cenarios_conjuge` no payload E5

**Sprint host:** A8 · **Status:** Decidido (PR1) · **Ancora:** ADR-143 (rules-as-code), ADR-076 (codegen layout SOT)

**Decisão:** Chave de payload no E5 passa de `cenarios_{_CONJUGE_KEY}` (workspace-dependent) para literal estável `cenarios_conjuge`. Pipeline interno já usa `cenarios_conjuge` (ver `cenarios_conjuge_analyzer.py`); divergência era só na serialização (`e5_serialization.py:266` usava chave dinâmica).

**Alternativas avaliadas:**
- (a) Manter dual-key permanente — viola ADR-143; chave de produto não pode acoplar a workspace config
- (b) **Migrar para chave fixa, fallback transitório no frontend, deprecar** ✅
- (c) Forçar invalidação de artifacts antigos — desnecessário (cache de execução; re-run E5 reescreve)

**Consequências:**
- Payloads E5 antigos em `pipeline_artifacts.content_json` ficam com chave velha; frontend tem fallback dual-key durante PR1→PR3
- Frontend types ganham `cenarios_conjuge: ContingencyScenario`; `cenarios_mariana` removido em PR3
- Goldens atualizados atomicamente em PR1 (apenas unit tests; sem golden binário)
- **LLM cache invalida automaticamente** (hash de payload muda) — re-narração de S7/T5 acontece naturalmente
- Sem schema migration de DB (`pipeline_artifacts.content_json` é JSON cru sem index)
- Sem bump de `MATHOMS_SCHEMA_VERSION` (payload E5 é dict aberto; endpoint `/reports/{id}/data` retorna `{type: object}`)
- **Backfill operacional pós-PR1:** script `dev/backfill_e5_universal_keys.py` re-roda `analyze_finances` em workspaces com `last_report_at < PR1_merge_time`. Idempotente. Confirmar com query: `SELECT COUNT(*) FROM pipeline_artifacts WHERE content_json::text LIKE '%cenarios_mariana%'` = 0 antes de PR3

### ADR-167 — Eligibility gate de cenário do cônjuge no domain service

**Sprint host:** A8 · **Status:** Decidido (PR2) · **Ancora:** ADR-143 (rules-as-code, regra co-localizada com enforcer)

**Decisão:** Função pura `should_render_conjuge_scenarios()` em `pipeline/domain/services/cenarios_conjuge_analyzer.py` decide se o cenário "cônjuge sem trabalhar" entra no payload do workspace. Pipeline E5 omite o bloco quando `False`; frontend só checa presença.

**Critérios de elegibilidade (universal, Cerbasi/Perini):**
- Meta IF presente (`if_meta > 0`)
- ≥2 membros com renda recorrente
- Renda do cônjuge ≥15% da renda familiar total

**Alternativas avaliadas:**
- (a) Frontend decide (mostra `null` quando vazio mas backend sempre emite) — duplica regra em TS; risco de drift que ADR-143 combate
- (b) `section_summary_orchestrator` decide quais seções listar — mistura granularidade (orchestrator é seção-level, não chart-level)
- (c) **Pipeline E5 emite ou omite o bloco** ✅ — uma camada decide; frontend confia no payload

**Consequências:**
- Solteiro / 1 renda → APP_C oculto
- Casal sem meta IF → APP_C oculto
- Casal 95/5 → APP_C oculto (impacto < 15%)
- Casal 70/30 + meta IF → APP_C visível com cenário "Sem renda do cônjuge"
- TOC dinâmico no frontend reflete: APP_C ausente, APP_D continua "D"

---

## 8. Backlog futuro — Cenários 2 e 3

financial-planner propôs 2 cenários adicionais universalmente úteis. Não entram no MVP (D1=A) mas ficam documentados aqui para entrega futura — provavelmente Sprint A9+ via track `track_contingency_scenarios_v2.md`.

### Cenário B: Perda de renda do titular (12 meses)

**Gatilho universal:** sempre que titular tem renda recorrente E há meta IF.

**Output esperado:**
- Aporte mensal sob choque (zero, durante 12m)
- Reserva de emergência consumida
- Δ meses até IF
- Gap de cobertura: meta IF − investivel atual − reserva

**Cross-link:** ponte com reserva de emergência (Score Financeiro / cobertura de despesas).

### Cenário C: Aposentadoria antecipada (-5 anos da meta)

**Gatilho:** titular ≥45 anos OU progresso IF ≥60%.

**Output esperado:**
- Δ aporte necessário para antecipar IF em 5 anos
- Custo financeiro de antecipar (R$/mês adicional)
- Avaliação Perini: dolarização recomendada para hedge cambial pós-IF

### Threshold de visualização

- ≥3 cenários ativos (B + C ligados além do A) → tabela com coluna delta (formato atual revisado)
- ≤2 cenários → cards comparativos lado-a-lado (formato D3 atual)

### Sugestão estrutural (não bloqueante)

Renomear `cenarios_conjuge_analyzer.py` → `contingency_scenarios_analyzer.py` quando os 3 cenários estiverem ativos. Não fazer agora — escopo creep no MVP.

---

## 9. Critério de aceite global

Após PR5 mergeado:

- [ ] `grep -ri "Mariana\|NCLEX\|Green Card\|EB2-NIW\|F1/F2\|EB2 NIW"` em `config/`, `pipeline/`, `scripts/`, `backend/`, `frontend/src/`, `docs/` → **0 hits** (exceto `_archive/`, fixture LLM, este plano e ADRs históricas)
- [ ] `grep -ri "cenarios_mariana\|mariana_cenarios"` em `config/`, `pipeline/`, `scripts/`, `backend/`, `frontend/` → **0 hits**
- [ ] `grep -ri "U1MudancaEua\|U2GreenCard\|U3Nclex\|U4Simulacao\|selectSections('usa')\|mode === 'usa'" frontend/src/` → **0 hits**
- [ ] `frontend/src/components/report/ReportModeContext.tsx` reduzido a 1 modo
- [ ] `cd frontend && npm test -- --run` verde
- [ ] `cd frontend && npm run test:e2e` verde
- [ ] `pytest tests -q` verde
- [ ] `pytest backend/tests -q` verde
- [ ] `pre-commit run --all-files` verde
- [ ] `python3 dev/check_adr_anchors.py && python3 dev/build_adr_toc.py --check && python3 dev/validate_adr_format.py` verde
- [ ] Workspace solteiro: APP_C ausente; APP_D continua "D"
- [ ] Workspace casal 70/30 + meta IF: APP_C visível com cenário "Sem renda do cônjuge" + delta vs. base + parágrafo "Leitura:"
- [ ] Snapshot visual APP_C (com e sem) commitado
- [ ] OpenAPI snapshot inalterado (chave não exposta em response_model) OU diff esperado committed

---

## 10. Glossário

| Termo | Definição | Localização canônica |
|---|---|---|
| `cenarios_conjuge` | Bloco do payload E5 com cenário "cônjuge sem trabalhar" generalizado. Universal, não acoplado a workspace key | `pipeline/domain/services/e5_serialization.py:266` |
| `should_render_conjuge_scenarios()` | Função pura de elegibilidade; gate no domain service | `pipeline/domain/services/cenarios_conjuge_analyzer.py` |
| Cenários de Estresse | Apêndice C do relatório premium; condicional ao gate de elegibilidade | `frontend/src/components/report/sections/ApendicesSections.tsx`, `config/report_layout.yaml` (APP_C) |
| Hide-when-empty + numeração estável | Padrão UX: APP_C ausente quando inelegível, mas APP_D continua rotulado "D" (numeração A/B/C/D/E literal, não recomputada) | `config/report_layout.yaml`, `frontend/src/components/report/ReportToc.tsx` |
| Modo USA | Antiga modalidade do relatório (U1-U4) — removida em PR4 | (deletado em ADR-168) |

---

## Histórico

- **2026-05-06:** plano criado (PR0). Especialistas consultados: financial-planner, product-designer, senior-cto, data-engineer.
- **2026-05-06:** PR0 mergeado em `main` (commit `a4d956e`).
- **2026-05-06:** PR1 mergeado em `main` (#80, commit `a8c2666`) — schema rename `cenarios_conjuge` + ADR-166 Decidido.
- **2026-05-06:** ADR-168 alvo do PR4 ("Remoção do Modo USA") **renumerada para ADR-168** — slot 165 foi tomado por outro PR (#79, ValidationIssue) durante a janela de execução desta iniciativa.
- **2026-05-06:** PR2 mergeado em `main` (#81, commit `1d33411`) — analyzer reduzido a 1 cenário + gate de elegibilidade ADR-167 Decidido.
- **2026-05-06:** PR3 implementado — APP_C "Cenários de Estresse" com hide-when-empty + visualização comparativa lado-a-lado base vs estresse + `StressScenarioCard` extraído.
- **2026-05-06:** PR5 mergeado em `main` (#85, commit `bed2975`) — limpeza editorial em `config/methodology.md` e `config/report_spec.md` (mergeou antes de PR3/PR4 porque conteúdo não conflitava).
