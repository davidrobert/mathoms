# `goals.json` Cutover Final — Plano Canônico (Sprint A10)

> Plano canônico multi-fase para fechar o último frente da migração
> `config/*.json` → DB-first iniciada em Sprint A7. Substitui débito
> tácito de [ADR-077 §Contrato de cutover](DECISIONS.md#adr-077--ponte-pipelinedb-via-pipeline_adapter--implementação-de-adr-075)
> ("100% dos campos lidos pelo E5/E5.N/E6") que ficou aberto após A7.
>
> Origem do escopo: review 2026-05-06 — narrativa "Top 5 Decisões de
> Impacto" (S10) renderiza string hardcoded de
> `_archive/pre-f8-cutover-2026-04-15/config/goals.json` mesmo após
> Sprint A7 deletar 5 outros JSONs e migrar `decisions.md` para o
> `Decision` aggregate (ADR-136).
>
> **Sprint:** A10 (próxima após A8.4 fechar).
> **Owner:** orquestrador + supervisão CTO (gates G1-G4, padrão ADR-138).
> **Especialistas consultados (G0):** `senior-cto` + `financial-planner`.

---

## 1. Contexto

### 1.1 Por que existe esse débito

Sprint A7 (entregue 2026-04-27) era "config cutover" e atacou:

- ✅ `categorization.json`, `family_members.json`, `institutions.json`,
  `parametros_fiscais.json`, `taxas.json` → DB-first via
  ConfigStore/aggregates/tabelas globais.
- ✅ `decisions.md` (editorial Plano de Ação D01–D15) →
  `Decision` aggregate event-sourced (ADR-136).
- ✅ 4 docs em `docs/methodology/` → rules-as-code (ADR-143/145/146/147).
- ❌ **`config/goals.json` foi bypassado.** F8.4 (2026-04-15) arquivou
  o arquivo em `_archive/pre-f8-cutover-2026-04-15/config/goals.json`
  e [pipeline_task.py:78-86](../backend/app/tasks/pipeline_task.py:78)
  passou a **materializar `goals.json` em runtime** dentro do
  `tenant_root/config/` para os scripts E5/E5.N continuarem lendo via
  filesystem. O DB virou bridge, não fonte primária.

### 1.2 Estado atual (factual, 2026-05-06)

**4 chaves do legado** viraram Goal types dedicados em DB com DTO
Pydantic + endpoint + UI:

- `aportes` → `APORTE_MENSAL` (DTO `AporteGoalInputs`)
- `independencia_financeira` → `INDEPENDENCIA_FINANCEIRA`
  (DTO `IFGoalInputs`)
- `dolarizacao` → `DOLARIZACAO`
- `alocacao_alvo` → `ALOCACAO_ALVO`

**18 chaves restantes** são empilhadas em
`PLANNING_CONTEXT.params_json.inputs` como **bag tipada-em-runtime**
(sem schema, sem DTO, sem UI), seguindo
[backend/app/scripts/seed_goals_full_ferreira_campos.py](../backend/app/scripts/seed_goals_full_ferreira_campos.py)
— único caminho de seed. Hardcoded para `family_surname == "Ferreira Campos"`
(precondição de tenancy violada).

A leitura em pipeline ainda passa por:

1. [`pipeline_task.py::_materialize_adapter_configs`](../backend/app/tasks/pipeline_task.py:56)
   gera `tenant_root/config/goals.json` por run.
2. [`scripts/e5_analyze.py:166`](../scripts/e5_analyze.py:166) e
   [`scripts/e5n_narrativas.py:105`](../scripts/e5n_narrativas.py:105) leem
   esse arquivo via `_load_goals()`.
3. Domain services (`if_projector.py`, `cenarios_conjuge_analyzer.py`,
   `consumo_consciente_calculator.py`) recebem sub-dicts do `goals_cfg`
   como parâmetro.
4. Narradores (`charts_narrator`, `summaries_narrator`,
   `perfil_familia_narrator`, `builder`) consomem métricas derivadas.

**Card visível ao usuário** que motivou esta sprint:
[S10SinteseSection.tsx:38](../frontend/src/components/report/sections/S10SinteseSection.tsx:38)
"Top 5 Decisões de Impacto" — texto vem de
[charts_narrator.py:382-393](../pipeline/domain/services/narrativas/charts_narrator.py:382),
template f-string que concatena `decisoes[1:5]` da bag PLANNING_CONTEXT
(5 strings hardcoded Ferreira-Campos).

### 1.3 Por que importa

- **Tenancy quebrada:** mesmo após F8.4, qualquer workspace novo (não
  Ferreira-Campos) recebe seed copiando dados pessoais alheios; ou
  fica sem `decisoes_prioritarias`/`riscos_prioritarios` e o
  relatório quebra silenciosamente em narrativas que assumem essas
  chaves preenchidas.
- **Decision aggregate desperdiçado:** ADR-136 entregou aggregate
  event-sourced com tela `/plano`, mas o card "Top 5 Decisões" do
  relatório lê string editorial paralela. Duas fontes de verdade
  para o mesmo conceito.
- **`Risk` não existe:** `riscos_prioritarios` (8 dicts hardcoded
  prob×impacto) renderiza no chart `bubble_riscos` (S9) sem aggregate
  por trás — usuário não pode editar; consultor não pode parametrizar
  por workspace.
- **Dead data ressuscitada:** ADR-168 (A8.4 PR4, 2026-05-06) removeu
  Modo USA do relatório, mas o seed continua povoando `fase_f1f2`,
  `mariana_eua`, `nclex_roadmap` no PLANNING_CONTEXT — código de
  narrativa zumbi em [`e5n_narrativas.py:351-352`](../scripts/e5n_narrativas.py:351),
  [`summaries_narrator.py:80-82`](../pipeline/domain/services/narrativas/summaries_narrator.py:80),
  [`charts_narrator.py:332-335`](../pipeline/domain/services/narrativas/charts_narrator.py:332).
- **ADR-077 com checkbox aberto** há 7 meses; cleanup técnico
  travado.

---

## 2. Inventário decisional (22 chaves)

Cada chave do legado classificada em **destino canônico** baseado em
revisão CTO + financial-planner. Tipo metodológico (FP):
**[U]**niversal · **[C]**liente · **[D]**erivada · **[H]**istórica/dead ·
**[M]**etodológica · **[O]**peracional.

### 2.1 Goal types existentes (manter como estão)

| Chave | Tipo | Goal type | Status |
|---|---|---|---|
| `aportes` | C | `APORTE_MENSAL` | ✅ entregue F8.4 |
| `independencia_financeira` | C | `INDEPENDENCIA_FINANCEIRA` | ✅ entregue F8.1 |
| `dolarizacao` | C | `DOLARIZACAO` | ✅ entregue F8.4 |
| `alocacao_alvo` | C | `ALOCACAO_ALVO` | ✅ entregue F8.4 |

### 2.2 Chaves a migrar / consolidar / deletar

| Chave | Tipo | Destino | Justificativa | Lane |
|---|---|---|---|---|
| `decisoes_prioritarias` | D | **Projeção de `Decision`** | Já existe aggregate (ADR-136); narrativa S10 consulta `Decision` ordenado por `impact_score DESC` filtrado por `horizon=short` e `status IN (Decidido, Pendente)`. AUVP: Plano de Ação por aporte. | A10.5 |
| `top5_decisoes` | D | **Projeção de `Decision` + extensão schema** | Mesmo aggregate; `impact_1y_brl_cents`/`impact_10y_brl_cents` adicionados ao `Decision` (Alembic). Cliente quantifica direto na UI `/plano`. | A10.3 + A10.5 |
| `riscos_prioritarios` | C+U mix | **Novo aggregate `Risk`** (ADR-178) | Estrutura `{name, probability, impact, mitigations: Decision[]}` distinta de Decision. Seed com 5 riscos universais Cerbasi (morte/invalidez/doença/longevidade/desemprego) como template; cliente edita. Bubble chart S9 vira projeção. | A10.4 |
| `seguros` (vida_term_min/max) | U+C híbrido | **Goal type `SEGUROS`** + heurística rules-as-code | Fórmula "10× renda anual" (Cerbasi) é universal — vai docstring + ADR-177; valor-alvo R$ é cliente-específico — Goal type leve. | A10.6 |
| `tetos_orcamentarios` | C | **Deletar agora; ressurreita em sprint dedicada quando houver UI** | Zero leitor vivo (E6 morto, ADR-129; nenhum frontend novo lê). Conceito Cerbasi sobrevive, mas criar Goal type sem feature definida viola "no premature abstraction" (CLAUDE.md §Code style). | A10.1 |
| `viagens.teto_anual` | C | **Deletar com `tetos_orcamentarios`** | Mesmo destino futuro (categoria de orçamento), mesmo princípio. | A10.1 |
| `tributario` (contador, regime, holding_prazo) | C | **Campo em `Workspace.business_profile_json` (JSON simples)** | Cliente PJ específico; aggregate dedicado é overkill. JSON livre no Workspace é suficiente até demanda concreta. Holding prazo vira campo de Decision opcional. | A10.7 |
| `imoveis` (yield_potencial_pct_min/max) | U | **Rules-as-code** (constante em módulo + ADR-177) | Yield bruto FII/imóvel BR (4-6%) é referência de mercado. Não varia por cliente. | A10.2 |
| `thresholds.imovel_pct_patrimonio_ideal: 50` | U | **Rules-as-code** (ADR-177) | Concentração imobiliária >50% = bandeira. Convergente Perini (passivo) + AUVP (concentração). | A10.2 |
| `thresholds.equity_pct_alvo_min/max` | U/C | **Rules-as-code (default) + override em `ALOCACAO_ALVO`** | Range default por perfil em rules-as-code; override por cliente já cabe em Goal `ALOCACAO_ALVO` existente (extensão `target_min_pct`/`target_max_pct` opcional). | A10.2 |
| `simulacao.aporte_reduzido_fator: 0.66` | U | **Rules-as-code** (constante em `cenarios_conjuge_analyzer.py` + ADR-177) | Heurística "cônjuge 66%" — sem ancoragem direta em livro mas convergente com Cerbasi (renda dupla). Já tem default no código. | A10.2 |
| `stress_test_imovel_queda_pct: 20` | U | **Rules-as-code** (constante em stress test service + ADR-177) | Threshold metodológico de stress test imobiliário. | A10.2 |
| `referencias.livros` | M | **Conteúdo estático no frontend** (página Sobre/Metodologia) | Bibliografia Perini/Cerbasi/Nigro/Clason/Kiyosaki — não muda por cliente. | A10.2 |
| `referencias.ferramentas` | M | **Conteúdo estático no frontend** | 9 sites/apps de mercado — idem. | A10.2 |
| `referencias.contatos_templates` | M+C | **Template estático no frontend** | Perfis profissionais (advogado, CPA, corretor) são templates. Contato real do cliente fica em `notes/<ws>/contatos.md` (bridge tipo ADR-147 milhas) até demanda de aggregate `Contact`. | A10.2 |
| `calendario_fallback[]` | O+M | **Rules-as-code** (template estático em módulo + ADR-177) | Itens-template por horizonte ("Imediato"/"Próximo mês"/etc). Filtrar entries USA-only após ADR-168. | A10.2 |
| `dashboard.aporte_match_keywords` | O | **Constante em módulo backend** | **VIVO** em [`task_progress_service.py:63`](../backend/app/services/task_progress_service.py:63). Migrar para constante imutável `_APORTE_MATCH_KEYWORDS` no módulo. | A10.2 |
| `dashboard.category_labels` | O | **i18n no frontend** | Labels PT-BR — fica no codegen ou em `frontend/src/i18n/`. | A10.2 |
| `dashboard.{thresholds,cycle_thresholds,...}` | O | **Rules-as-code** (constantes no módulo onde o threshold vive) | Operacional do dashboard E6 morto. Migrar **só** o que `task_progress_service` usa; resto deleta. | A10.2 |
| `investimentos_blocos` | D | **Derivar de `FamilyMember.first_name`** | Zero leitor vivo (`inv_david` em e5_analyze é variável local, não a chave). Deletar. | A10.1 |
| `aportes_destinos_detalhados` | D | **Derivar de `APORTE_MENSAL.distribuicao` + `ALOCACAO_ALVO`** | Duplica `aportes.distribuicao` com metadata derivável (objetivo/liquidez/moeda). Deletar. | A10.1 |

### 2.3 Dead data confirmada (ADR-168 cleanup débito)

ADR-168 removeu Modo USA do relatório mas as narrativas que usam essas
chaves continuaram pendurar — verificável em
[`summaries_narrator.py:80-82`](../pipeline/domain/services/narrativas/summaries_narrator.py:80),
[`charts_narrator.py:332-335`](../pipeline/domain/services/narrativas/charts_narrator.py:332),
[`perfil_familia_narrator.py:108`](../pipeline/domain/services/narrativas/perfil_familia_narrator.py:108).

| Chave | Tipo | Destino | Bloqueador |
|---|---|---|---|
| `fase_f1f2` | H | **Deletar + remover narrativas órfãs** em E5/E5.N | `custo_fase_f1f2`/`sobra_mensal_f1f2` consumidos por 4 narradores. Cada site exige cirurgia. |
| `mariana_eua` / parte EUA de `cenarios_conjuge` | H | **Deletar** | `cenarios_conjuge_analyzer.py` continua mas só lê `simulacao.aporte_reduzido_fator` (que vira rules-as-code). |
| `nclex_roadmap` | H | **Deletar** | Sem leitor vivo. |
| `nclex_estimativa_meses` | H | **Deletar** | Sem leitor vivo. |

**Lane:** A10.1 (combina dead-data deletion + ADR-168 cleanup débito).

---

## 3. Estratégia técnica

### 3.1 Injeção via `StageConfig.config_store` (estende A7.0)

**Decisão:** estender `ConfigStore` Protocol existente com método
`get_goals_bundle(workspace_id) -> GoalsBundle`, **NÃO** criar
`AnalyzerInputs` por stage.

**Por quê:**

- A7.0 já entregou `WorkspaceContext.config_overrides` lendo via
  `DBConfigStore`. Consistência > novo padrão paralelo.
- `AnalyzerInputs` por stage exige refatorar 11 sites em E5 + 2 em E5.N
  + 4 em domain services (alto custo, ganho marginal).
- `GoalsBundle: TypedDict` montado pelo adapter resolve com mínima
  cirurgia, mantendo `pipeline/**` sem import de `fastapi`/`celery`/
  `sqlalchemy` (boundary check ADR continua verde).

**Shape proposto** (a refinar em ADR-180):

```python
class GoalsBundle(TypedDict):
    aporte: AporteGoalInputs
    if_meta: IFGoalInputs
    dolarizacao: DolarizacaoGoalInputs
    alocacao: AlocacaoGoalInputs
    seguros: SegurosGoalInputs            # A10.6
    decisoes_top5: list[DecisionProjection]  # A10.5
    riscos_top: list[RiskProjection]      # A10.5
```

`pipeline_adapter.build_goals_payload_sync` (existente) é refatorado
para retornar `GoalsBundle` ao invés de dict legacy-shaped.

### 3.2 Cutover do filesystem

`_materialize_adapter_configs` em
[`pipeline_task.py:56-99`](../backend/app/tasks/pipeline_task.py:56)
**deletado**. E5/E5.N param de chamar `_load_goals()`; recebem
`GoalsBundle` via `StageConfig`. Consequência: `goals.json` físico
**nunca mais escrito em filesystem**.

### 3.3 Decision aggregate — extensão de schema (ADR-179)

[backend/app/models/decision.py](../backend/app/models/decision.py)
hoje tem: `code, title, rationale, amount_brl_cents, status, supersedes_id,
decided_at, executed_at, target_field, target_value, target_value_type,
context_snapshot`.

**Adicionar** (Alembic + DTO + UI form):

- `impact_1y_brl_cents: BIGINT NULL` — impacto financeiro projetado em 1
  ano (ADR-090: cents).
- `impact_10y_brl_cents: BIGINT NULL` — idem 10 anos.
- `horizon: VARCHAR(16)` — enum `{short_6_12m, medium_1_3y, long_5y_plus}`,
  default `short_6_12m`. Default permite query do card S10 sem migrator
  pesado para Decisions existentes.
- `priority: SMALLINT NULL` — ordenação manual do consultor; nulo
  ordena por `impact_1y_brl_cents DESC NULLS LAST`.

Migrator preenche `impact_1y_brl_cents` a partir de
`amount_brl_cents` quando aplicável (heurística: aporte mensal × 12;
seguro = cobertura; etc.) — **PR separado de paridade goldens** se
narrativa S10 mudar.

### 3.4 Risk aggregate (ADR-178)

Modelo paralelo a `Decision`:

```python
class Risk(Base):
    __tablename__ = "risks"
    id, workspace_id, code, name, rationale: str
    probability: Enum["baixa", "média", "alta"]
    impact_level: Enum["baixo", "médio", "alto", "crítico"]  # qualitativo
    impact_brl_cents: BigInteger | None  # quantitativo opcional (ADR-090)
    status: Enum["Ativo", "Mitigado", "Aceito", "Descartado"]
    mitigations_decision_ids: JSON  # array de Decision.id (link semântico)
    created_at, updated_at
```

**Seed template** (universal Cerbasi, não-cliente-específico): 5 riscos
do provedor — morte, invalidez, doença grave, desemprego, longevidade.
Workspace novo recebe os 5 com `status="Ativo"` e `probability=null`
(cliente preenche). Riscos cliente-específicos (concentração PJ,
cambial, sucessório, iliquidez) são **adicionados pelo consultor/cliente
via UI**, não seedados.

Bubble chart S9 lê `Risk` aggregate ordenado por (`impact_level`,
`probability`).

### 3.5 Seed refactor — `seed_goals_workspace.py`

[`seed_goals_full_ferreira_campos.py`](../backend/app/scripts/seed_goals_full_ferreira_campos.py)
renomeado, perdendo:

- Hardcode `family_surname == "Ferreira Campos"` → recebe `--workspace-id`
  obrigatório.
- Leitura de `_archive/.../goals.json` → seed agora é **declarativo no
  código**, não consome arquivo.
- Bag `PLANNING_CONTEXT` → tipo deletado (sem chaves residuais a
  empilhar após cleanup).

Cliente Ferreira-Campos perde os dados do `goals.json` arquivado que
não couberam em aggregates novos. Aceito — esses dados eram
demonstração interna; produção usa wizard de onboarding.

---

## 4. ADRs propostos

Próxima ADR livre: **ADR-177** (última = ADR-175).

| ADR | Título | Escopo | Supersedes |
|---|---|---|---|
| **ADR-177** | Thresholds e referências metodológicas como código (rules-as-code consolidation goals.json) | 7 chaves U/M/O do goals.json viram docstrings + constantes em módulo. Aplica ADR-143. | — |
| **ADR-178** | `Risk` aggregate workspace-scoped | Novo aggregate paralelo a `Decision`. Estrutura prob×impacto + link via `mitigations_decision_ids`. Seed Cerbasi 5 riscos universais. | — |
| **ADR-179** | Decision aggregate — extensão de schema (impact_1y/10y, horizon, priority) | Alembic adiciona 4 colunas; DTO + UI form; backfill heurístico em migrator dedicado. Estende ADR-136. | — |
| **ADR-180** | `goals.json` cutover final via `StageConfig.config_store` extendido | `GoalsBundle: TypedDict` montado pelo adapter; pipeline para de materializar `goals.json`; `_load_goals()` deletado. **Fecha checkbox** ADR-077. | (parcial) ADR-077 |
| **ADR-181** | `goals.json` removido de `_archive/` e adicionado a `dev/check_forbidden_paths.py` | Cleanup final. Substitui arquivo arquivado por `goals.json.MIGRATED.md` documentando destino de cada chave. | — |

**Decisão sobre ADR para `SEGUROS` Goal type:** dispensável (sub-1h,
padrão estabelecido pelos 4 Goal types existentes). PR direto sem ADR.

**Decisão sobre `BUDGET_CEILING` Goal type:** **não criar**.
`tetos_orcamentarios` deletado em A10.1; ressurreita em ADR + Goal type
quando UI de orçamento entrar no roadmap.

**Total:** 5 ADRs `Proposto` em batch antes do PR1.

---

## 5. Lanes e ondas

### 5.1 Tabela de lanes (9 lanes em 4 ondas)

| Lane | Slug | Wave | Depende de | Paralelo com | Esforço | Owner |
|---|---|---|---|---|---|---|
| **A10.0** ADRs Proposto batch (ADR-177 a ADR-181) | `a10-0-adrs` | W0 | — | — | 0.5d | senior-cto |
| **A10.1** Dead-data + ADR-168 cleanup débito | `a10-1-dead-data` | W1 | A10.0 ✅ | A10.2 | 1d | engenheiro |
| **A10.2** Rules-as-code consolidation (ADR-177) | `a10-2-rules-as-code` | W1 | A10.0 ✅ | A10.1 | 1d | engenheiro |
| **A10.3** Decision schema extension (ADR-179) | `a10-3-decision-extension` | W2 | A10.0 ✅ | A10.4, A10.7 | 1.5d | engenheiro |
| **A10.4** `Risk` aggregate (ADR-178) | `a10-4-risk-aggregate` | W2 | A10.0 ✅ | A10.3, A10.7 | 2d | engenheiro |
| **A10.7** Seed refactor + tributario migration | `a10-7-seed-refactor` | W2 | A10.1 + A10.2 ✅ | A10.3, A10.4 | 1d | engenheiro |
| **A10.5** Top5 + Bubble como projeção (charts_narrator switch) | `a10-5-projections` | W3 | A10.3 + A10.4 ✅ | A10.6 | 1d | engenheiro |
| **A10.6** Pipeline cutover (StageConfig bundle, ADR-180) | `a10-6-stage-config-bundle` | W3 | A10.1 + A10.2 + A10.3 + A10.4 ✅ | A10.5 | 1.5d | engenheiro |
| **A10.8** Final cutover + forbidden_paths (ADR-181) | `a10-8-cutover-final` | W4 | TODAS ✅ | — | 0.5d | engenheiro |

**Esforço estimado total:** ~10 dias de trabalho ativo. Wall-clock
~5-7 dias com paralelismo de 2-3 agentes.

### 5.2 Diagrama de ondas

```
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 0 — ADRs Propostos (1 lane, BLOQUEANTE)                       ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.0  Batch ADR-177..180 em status "Proposto"                    ║
║         Reusa esqueleto + ToC + gates dev/check_adr_*               ║
╚════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 1 — Cleanup paralelo (2 lanes simultâneas)                    ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.1  Dead-data deletion + ADR-168 narrativas órfãs              ║
║          (scripts/e5n_narrativas.py, narradores E5.N,              ║
║           seed_goals_full_ferreira_campos.py — chaves H)           ║
║  A10.2  Rules-as-code consolidation (ADR-177)                      ║
║          (constantes em módulos + docstrings + frontend estático)  ║
║                                                                    ║
║  Hotspot: backend/app/services/task_progress_service.py            ║
║   (A10.2 migra aporte_match_keywords → constante)                  ║
╚════════════════════════════════════════════════════════════════════╝
                              │ A10.1 + A10.2 mergeadas
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 2 — Aggregate work (3 lanes simultâneas)                      ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.3  Decision schema extension (ADR-179)                        ║
║          Alembic + DTO + UI form 4 campos novos                    ║
║  A10.4  Risk aggregate (ADR-178)                                   ║
║          Model + repo + 6 use cases + UI mínima + seed Cerbasi     ║
║  A10.7  Seed refactor + Workspace.business_profile_json            ║
║          seed_goals_workspace.py + tributario migration            ║
║                                                                    ║
║  Hotspot: backend/alembic/versions/ — 3 migrations simultâneas     ║
║   (resolver heads collision via merge migration ou serial deps)    ║
╚════════════════════════════════════════════════════════════════════╝
                              │ A10.3 + A10.4 + A10.7 mergeadas
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 3 — Pipeline cutover (2 lanes simultâneas)                    ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.5  Top5/Bubble projections                                    ║
║          charts_narrator.py:382 lê Decision/Risk aggregates        ║
║          remove decisoes_prioritarias/top5_decisoes/riscos da bag  ║
║  A10.6  StageConfig bundle (ADR-180)                               ║
║          GoalsBundle TypedDict + adapter retorno tipado            ║
║          E5/E5.N/conjuge_analyzer leem do bundle                   ║
║          _materialize_adapter_configs deletado                     ║
║                                                                    ║
║  Cross-cutting goldens E5/E5.N — paridade rigorosa byte-a-byte     ║
║  (PR de reset com diff humanamente revisado se quebrar)            ║
╚════════════════════════════════════════════════════════════════════╝
                              │ A10.5 + A10.6 mergeadas
                              ▼
╔════════════════════════════════════════════════════════════════════╗
║ ONDA 4 — Cutover final (1 lane, BLOQUEANTE)                        ║
╠════════════════════════════════════════════════════════════════════╣
║  A10.8  config/goals.json adicionado a check_forbidden_paths.py    ║
║          _archive/.../goals.json deletado                          ║
║          ADR-077 checkbox marcado; ADR-180 → Decidido               ║
║          Substituir arquivo por goals.json.MIGRATED.md             ║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 6. Critério de aceite global

Sprint A10 só fecha quando **todos** os itens abaixo são verde:

### 6.1 Código

- [ ] `_materialize_adapter_configs` em `pipeline_task.py` deletado.
- [ ] `_load_goals()` em `scripts/e5_analyze.py` e
  `scripts/e5n_narrativas.py` deletados.
- [ ] `goals.json` físico nunca mais escrito em filesystem (verificável
  por `grep -r "goals.json" backend/app/tasks/` retornar zero).
- [ ] `pipeline_adapter.build_goals_payload_sync` retorna `GoalsBundle`
  tipado, não dict legacy-shaped.
- [ ] `Decision` model tem `impact_1y_brl_cents`, `impact_10y_brl_cents`,
  `horizon`, `priority`. Migration aplicada.
- [ ] `Risk` model criado, repo + 6 use cases + endpoints + UI lista
  básica.
- [ ] `seed_goals_full_ferreira_campos.py` renomeado para
  `seed_goals_workspace.py`, sem hardcode de surname.
- [ ] `PLANNING_CONTEXT` Goal type **deletado** do `VALID_GOAL_TYPES`
  (sem chaves residuais após cleanup).

### 6.2 Conteúdo

- [ ] `config/goals.json` em `dev/check_forbidden_paths.py`.
- [ ] `_archive/pre-f8-cutover-2026-04-15/config/goals.json` deletado;
  substituído por `goals.json.MIGRATED.md` com mapa chave→destino.
- [ ] Card S10 ("Top 5 Decisões de Impacto") renderiza top 5 do
  `Decision` aggregate via projeção, com fallback gracioso para
  workspaces sem decisões.
- [ ] Bubble chart S9 ("Riscos Prioritários") renderiza `Risk`
  aggregate; workspaces novos têm seed dos 5 riscos universais
  Cerbasi.
- [ ] Narrativas órfãs ADR-168 (`custo_fase_f1f2`, `f1f2_visto`,
  `sobra_mensal_f1f2`) removidas dos 4 narradores.

### 6.3 ADRs e governança

- [ ] ADR-177 a ADR-181 todos `Decidido` (saíram de `Proposto`).
- [ ] ADR-077 com checkbox ✅ marcado e referência cruzada para
  ADR-180 ("Fechado por").
- [ ] CHANGELOG `[Unreleased]` com entrada Sprint A10 + ADRs.
- [ ] BACKLOG Sprint A10 com todas as 9 lanes ✅.

### 6.4 Testes

- [ ] Goldens E5/E5.N verdes byte-a-byte em A10.1, A10.2, A10.6, A10.7,
  A10.8.
- [ ] Goldens com diff humanamente revisado e PR de reset dedicado em
  A10.3 + A10.5 (extensão de Decision pode mudar ordenação do top 5).
- [ ] Backend tests + pipeline tests verdes em todas as lanes.
- [ ] Boundary check `dev/check_pipeline_boundaries.py` verde
  (pipeline não importa novo código backend).
- [ ] OpenAPI snapshot regenerado em A10.3 + A10.4 (`make
  update-openapi-snapshot`).
- [ ] Specs novos: `backend/tests/test_decision_extension.py` (~10),
  `backend/tests/test_risk_aggregate.py` (~30), `backend/tests/test_goals_bundle.py`
  (~15), `tests/test_e5_pipeline_no_filesystem_goals.py` (gate empírico).

---

## 7. Riscos e mitigações

### 7.1 Paridade de goldens E5/E5.N (alto)

A10.5 troca fonte do narrador S10 de string hardcoded para query do
Decision aggregate. Para Ferreira-Campos, ordenação editorial
(`decisoes_prioritarias` legado) pode não bater 1:1 com ordenação
por `impact_score DESC` do aggregate.

**Mitigação:**

1. Migrator do A10.3 popula `impact_1y_brl_cents` a partir de
   `amount_brl_cents` ou heurística (aporte mensal × 12; seguro = cobertura).
2. Backfill manual de `impact_1y_brl_cents` para Ferreira-Campos
   replicando os valores de `top5_decisoes` legado.
3. Se ainda divergir após backfill, **PR de reset de goldens dedicado
   em A10.5** com diff humanamente revisado.

### 7.2 ADR-168 narrativas órfãs (médio)

`custo_fase_f1f2` consumido por 4 narradores
([`summaries_narrator.py:80-82`](../pipeline/domain/services/narrativas/summaries_narrator.py:80),
[`charts_narrator.py:332-335`](../pipeline/domain/services/narrativas/charts_narrator.py:332),
[`perfil_familia_narrator.py:108`](../pipeline/domain/services/narrativas/perfil_familia_narrator.py:108)).
Deletar a chave sem remover os usos quebra a renderização.

**Mitigação:** A10.1 obrigatoriamente trata os 4 sites; teste de
regressão verifica narrativa não menciona "fase F1/F2" ou "EUA"
quando workspace não tem flag USA (que não existe pós-ADR-168).

### 7.3 Schema evolution Decision aggregate (médio)

Decision em produção tem registros com `amount_brl_cents` populado mas
sem `impact_1y_brl_cents`/`impact_10y_brl_cents`/`horizon`/`priority`.

**Mitigação:**

- Alembic faz migration **non-breaking**: 4 colunas nullable; default
  `horizon='short_6_12m'`.
- Migrator dedicado backfill heurístico
  (`backend/app/scripts/backfill_decision_impact.py`) com `--dry-run`.
- Endpoint `/decisions/{id}` aceita ausência dos campos (DTO opcionais)
  até backfill aplicado.

### 7.4 Risk aggregate vs Decision sobreposição (baixo)

Confusão semântica: "decisão de contratar seguro" vs "risco de não
ter seguro" são conceitos relacionados.

**Mitigação:** ADR-178 explicita: Decision = ação a tomar; Risk =
evento incerto. Link via `Risk.mitigations_decision_ids: list[str]`.
Documentação no aggregate.

### 7.5 Tenancy do `tributario` (baixo)

`Workspace.business_profile_json` é JSON livre — não tem schema.

**Mitigação:** Pydantic model em `backend/app/schemas/business_profile.py`
valida shape ao entrar/sair do DB; campo no Workspace, não aggregate
separado. Se virar feature plena, promove a aggregate em sprint
futura.

### 7.6 Seed Ferreira-Campos perde dados (baixo)

Ao deletar `_archive/.../goals.json` e refatorar seed, dados
demonstração de Ferreira-Campos somem.

**Mitigação:** `seed_goals_workspace.py` declara fixtures de
demonstração inline (apenas para `--demo` flag); produção real usa
wizard de onboarding. PR final A10.8 inclui `seed_demo_workspace.py`
opcional para reproduzir Ferreira-Campos como demo.

---

## 8. Definition of Done — Sprint A10

```bash
# 1. Verificar arquivo arquivado deletado
test ! -f _archive/pre-f8-cutover-2026-04-15/config/goals.json

# 2. Verificar forbidden_paths bloqueia recriação
grep "config/goals.json" dev/check_forbidden_paths.py

# 3. Verificar pipeline não materializa goals.json
grep -r "_materialize_adapter_configs" backend/app/ | wc -l   # = 0
grep -r "goals.json" backend/app/tasks/ | wc -l              # = 0

# 4. Verificar ADRs Decididos
grep -A 2 "^## ADR-177" docs/DECISIONS.md | grep "Decidido"
grep -A 2 "^## ADR-178" docs/DECISIONS.md | grep "Decidido"
grep -A 2 "^## ADR-179" docs/DECISIONS.md | grep "Decidido"
grep -A 2 "^## ADR-180" docs/DECISIONS.md | grep "Decidido"
grep -A 2 "^## ADR-181" docs/DECISIONS.md | grep "Decidido"

# 5. Verificar ADR-077 fechada
grep "Fechado por.*ADR-180" docs/DECISIONS.md

# 6. Verificar testes
pytest tests -q                                  # pipeline
pytest backend/tests -q                          # backend
pre-commit run --all-files                       # hooks

# 7. Verificar PLANNING_CONTEXT goal type sumiu
grep "PLANNING_CONTEXT" backend/app/models/goal.py | wc -l    # = 0

# 8. Verificar Risk aggregate registrado
grep "class Risk" backend/app/models/risk.py
```

---

## 9. Pós-cutover (followups esperados)

Não fazem parte da Sprint A10 mas devem ser registrados como débitos
em BACKLOG (Sprint A11+):

- **`tetos_orcamentarios` UI:** quando dashboard nativo recolocar
  orçamento por categoria, criar Goal type `BUDGET_CEILING` (não
  ressurreitar bag).
- **`Contact` aggregate:** se demanda concreta de gerenciar contatos
  profissionais (advogado/CPA/corretor) aparecer, promover de
  `notes/<ws>/contatos.md` para aggregate.
- **`MileageProgram` aggregate:** já tracked em A8.1.
- **`top5_decisoes` UX:** após A10.5, validar com financial-planner se
  ordenação `impact_1y_brl_cents DESC` é a mais útil ou se `priority`
  manual + `horizon` filter dá melhor experiência.

---

## 10. Histórico e supersedes

- **Supersedes parcial** ADR-077 (checkbox aberto sobre 100% cobertura
  de campos lidos pelo E5/E5.N/E6).
- **Estende** ADR-136 (Decision aggregate — extensão de schema em
  ADR-179).
- **Aplica** ADR-143 (rules-as-code) em ADR-177.
- **Cleanup débito de** ADR-168 (Modo USA removido — narrativas órfãs
  em A10.1).
- **Padrão herdado de** ADR-138 (supervisão CTO Sprint A7) — gates
  G1/G2/G3/G4 reutilizados.

---

**Última atualização:** 2026-05-06
**Status:** Proposto — aguardando aprovação para criação dos ADRs
176-180 e abertura das lanes A10.0 a A10.8.
