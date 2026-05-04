# Track — Real estate efficiency feature (ADR-160)

> **Self-contained.** Execute em branch `agent/real-estate-efficiency/<yyyyMMdd-HHmm>`. Sign-offs G0 (financial-planner) e G4 (product-designer) já feitos em ADR-160; este prompt traduz a ADR em passos.
>
> Lane única; evite começar se houver outro agente ativo em S4 / `report_layout.yaml` / `IRPFAnalyzer` (checar `git for-each-ref refs/remotes/origin/agent/real-estate*`).

## Contexto mínimo

- **ADR canônica:** [docs/DECISIONS.md §ADR-160](../DECISIONS.md#adr-160--eficiência-tributária-imóvel-direto-vs-fii-no-relatório-premium-roadmap). **Leia inteira antes de codar** — fórmulas, ações, copy e anti-patterns são load-bearing.
- **Mudar status ADR-160 de `Roadmap` para `Decidido (Sprint <X>)`** ao final, no mesmo PR.
- Aggregates consumidos: `Suggestion` ([ADR-153](../DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples)) + `Decision` ([ADR-136](../DECISIONS.md#adr-136--decisions-event-sourced-aggregate--projection-sobre-goals)). NÃO criar aggregate novo.
- Schema IRPF source-of-truth: [ADR-157](../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full).

## Pré-flight

1. `git fetch origin && git status` — clean. Branch `agent/real-estate-efficiency/<ts>` a partir de `origin/main`.
2. Confirmar que ADR-160 está em `main` (deve estar; este prompt só existe se ela mergeou).
3. Confirmar que S4 atual em `config/report_layout.yaml` tem `cards: []` e título `"Real Estate — Imóveis e Renda Passiva"`. Se mudou, abrir comment com a equipe antes de prosseguir.
4. Decidir **antes de começar:** A2 (anomaly de inadimplência) entra no MVP ou diferida? ADR diz "aceitável diferir iteração 2". Default: diferir, fica como follow-up. Se fizer, somar +2 dias.

## Estimativa total

**3-5 dias dev** (sem A2). 5-7 dias se incluir A2.

## Estrutura sugerida — 7 commits coesos

### Commit 1 — domain service `RealEstateEfficiencyAnalyzer`

`pipeline/domain/services/real_estate_efficiency_analyzer.py` — pure-Python, sem dependência de FastAPI/SQLAlchemy.

Inputs (via construtor):
- `imoveis: list[ImovelLocado]` (dataclass nova: `id`, `apelido`, `cidade`, `tipo`, `valor_mercado_brl`, `valor_aquisicao_brl`, `aluguel_anual_brl`)
- `aliquota_marginal_aluguel: Decimal` — derivada da faixa RFB sobre `imposto_apurado.base_calculo_brl + aluguel_anual` no IRPFAnalyzer
- `yield_fii_pct: Decimal` (default `Decimal("0.08")`)
- `custos_pct: Decimal` (default `Decimal("0.02")`, override via config)
- `corretagem_pct: Decimal` (default `Decimal("0.055")`)
- `ir_ganho_capital_pct: Decimal` (default `Decimal("0.15")`)

Outputs (dataclasses tipadas, ADR-097 D1 — não dict):
- `ImovelEfficiencySnapshot` por imóvel: yields bruto/líquido, custo de saída detalhado, renda FII equivalente, gap anual, payback (ou `None` se delta ≤ 0).
- `RealEstateEfficiencyReport`: agregação + threshold concentração 30% AUVP + lista de suggestions canônicas.

Fórmulas exatas em ADR-160 §Sub-decisão 2. **Atenção crítica:**
- Alíquota **marginal**, não efetiva.
- Custo de saída **NÃO inclui ITBI** quando destino é FII.
- Principal pós-saída em renda FII (não principal cheio).
- Disclaimer "rateio proporcional" se `aluguel_anual_brl` veio rateado.

Money sempre `Decimal`/`Money.brl` (ADR-090). Sem float.

**Tests** (`tests/test_real_estate_efficiency_analyzer.py`):
- 1 imóvel, yield 4% bruto, alíquota marginal 27,5%, custos 2% → líquido bate 0,9% (bruto 4% × 0,725 − 2%).
- 1 imóvel `valor_aquisicao_brl == valor_mercado_brl` → ir_ganho_capital = 0.
- 1 imóvel sem `valor_mercado_brl` (None) → analyzer falha-explícito com erro tipado.
- Multi-imóvel rateio proporcional quando aluguel agregado.
- Payback retorna `None` quando delta ≤ 0.
- Concentração >30% emite suggestion `concentracao_imobiliaria_alta`.

### Commit 2 — wire em `analyze_finances` (E5)

`scripts/e5_analyze.py` (ou módulo equivalente) lê:
- `baseline_patrimonial` itens type=imovel com aluguel registrado (filtro: matched em E4 categoria `aluguel_recebido` por imóvel-key OU rateio proporcional)
- `imposto_apurado.base_calculo_brl` do `extract_irpf_full` artifact (workspace-scoped, try-read padrão ADR-157)

Aliquota marginal: helper novo `pipeline/domain/services/aliquota_marginal.py` que dado `base_calculo_brl + adicional` retorna a faixa RFB. Tests com fixtures por faixa.

Output do analyzer entra em `analyze_finances-5_analysis.json` em chave nova `imoveis_eficiencia: { snapshots: [...], report: {...} }`. **Schema strict** — atualizar `config/schemas/e5.schema.json`.

### Commit 3 — Suggestion templates + use case

`backend/app/application/suggestion/generate_real_estate_suggestions.py` — converte `RealEstateEfficiencyReport.suggestions` em `Suggestion` rows via use case canônico (ADR-153). Disparado em `_persist_aggregate_suggestions` em `pipeline_task.py` (mesmo padrão das 5 regras Onda 5 + 6 da Onda 8).

3 templates ativos no MVP:
- `real_estate_avaliar_conversao_fii` (severity warn) — payload com payback e delta_anual.
- `real_estate_concentracao_acima_alvo_auvp` (severity info) — payload com pct atual + pct alvo 30%.
- `real_estate_inadimplencia_detectada` (severity alert) — **diferir para iteração 2** (anomaly detection sazonal não-trivial).

Templates A4 reajuste regional e janela R$440k **NÃO criar** (ADR-160 vetou).

### Commit 4 — `report_layout.yaml` + codegen

- Renomear S4 de `"Real Estate — Imóveis e Renda Passiva"` para `"Real Estate — Imóveis e Eficiência Tributária"`.
- Adicionar `cards: [{id: "imovel_eficiencia", enabled: true, variant: "feature", size: "full", repeat_per_imovel: true}]` (campo novo `repeat_per_imovel` se necessário ou deixar componente decidir como iterar).
- Threshold `enabled_if: "imoveis_locados_pct > 0.15"` (ou implementar lógica em `<RealEstateSection/>` lendo override admin).
- Rodar `python3 dev/codegen_report_layout.py` + commitar `frontend/src/generated/report-layout.ts` + `backend/app/generated/report_layout.py`.
- `make update-openapi-snapshot` se DTO/endpoint novo.

### Commit 5 — frontend `<RealEstateSection/>` + `<ImovelEfficiencyCard/>`

`frontend/src/components/report/sections/RealEstateSection.tsx`:
- Lê `data.imoveis_eficiencia` do snapshot E5.
- Filtro `imoveis_locados_pct > admin_threshold` (default 0.15).
- Renderiza top 5 cards individuais + 1 agregado se >6 (ADR-160 §Sub-decisão 5).
- `<SectionSummary/>` lê `narrativas.S4` (copy editorial canônica em ADR-160 §Sub-decisão 8).

`frontend/src/components/report/cards/ImovelEfficiencyCard.tsx`:
- Wireframe ADR-160 §Sub-decisão 7. Header → 4 KPIs grid (2×2 mobile) → tabela 2×4 → calculadora `<details>` → chips ações → disclaimer.
- `<MonetaryValue signed/>` em "Gap vs FII".
- Calculadora: slider+input acoplado, range 2-12% step 0,1%, persiste em `localStorage['mathoms:report:imovel:<id>:fii_yield']`. Reset IFIX visível ao lado.
- Chips de ação: máx 3 visíveis, "+N mais" inline. Click abre dialog com CTA "Marcar como decisão" → cria Decision via use case ADR-136.
- Tokens: `--brand-info`, `--semantic-alert`, `--semantic-loss`, `--badge-yellow-*`. **Zero hex literal.** **Zero token novo.**
- Mobile: chips empilham vertical em <md, calculadora vira input puro (sem slider).

`frontend/src/components/report/cards/ImoveisAggregadosCard.tsx`:
- Tabela inline (1 linha/imóvel: endereço, valor, yield líq, gap), variant `neutral`, sem calculadora, sem ações individuais.
- `sticky left-0` na primeira coluna em <md (scroll horizontal).

### Commit 6 — barrel + tests Vitest

- `frontend/src/components/report/cards/index.ts` — exportar `ImovelEfficiencyCard`, `ImoveisAggregadosCard`.
- `frontend/src/components/report/sections/index.ts` se existir.
- `frontend/tests/components/RealEstateSection.test.tsx`:
  - Renderiza nada quando `imoveis_locados_pct ≤ 0.15`.
  - Renderiza N cards + 0 agregados quando N ≤ 6.
  - Renderiza 5 cards + 1 agregado quando N > 6.
  - Cards aparecem ordenados por valor desc.
  - Calculadora muda yield → recalcula tabela em re-render.
  - Reset IFIX volta para default.
- `backend/tests/test_real_estate_suggestions_integration.py` — workspace fixture com 2 imóveis → roda E5 → assert que 2 suggestions criadas (1 conversão_fii + 1 concentração se aplicável).

### Commit 7 — copy editorial + status flip

- Atualizar `narrativas.S4` no fixture E5.N (template determinístico OU LLM prompt) com context+conclusion canônicos da ADR-160 §Sub-decisão 8.
- Em `docs/DECISIONS.md`: mudar `**Status:** Roadmap` para `**Status:** Decidido (Sprint <X>)` na ADR-160. Rodar `python3 dev/build_adr_toc.py --inline` + `python3 dev/validate_adr_format.py`.
- Atualizar [docs/CHANGELOG.md](../CHANGELOG.md) com entry da feature.
- Atualizar [docs/BACKLOG.md](../BACKLOG.md) marcando lane fechada.

## Gates obrigatórios antes do PR

- [ ] `pytest tests/test_real_estate_efficiency_analyzer.py -q` (analyzer + fórmulas)
- [ ] `pytest tests/test_e5n_golden_execution.py -q` (não regrediu)
- [ ] `pytest backend/tests/test_real_estate_suggestions_integration.py -q`
- [ ] `cd frontend && npm test -- --run` (Vitest)
- [ ] `cd frontend && npm run test:e2e` se houver fluxo `@critical` tocado
- [ ] `pre-commit run --all-files` — gates de ADR + style + tokens + codegen sync
- [ ] `make update-openapi-snapshot` se mudou DTO; `make update-db-schema-reference` se houve migration
- [ ] **Sem dado real cliente** em fixture; sem hex literal; sem `Mapped[float]` em campo monetário; sem token novo (G4 disse explícito)
- [ ] Visual baselines opt-in: `gh workflow run CI -f run_visual=true -f update_visual_baselines=true` para gerar S4 {light,dark} pós-renomeio

## Anti-patterns a vigiar (ADR-160 §Sub-decisão 9)

1. Comparar yield bruto FII com yield líquido imóvel — sempre líquido vs líquido visíveis.
2. Tratar yield FII como permanente — disclaimer "premissa em ciclo Selic intermediário".
3. Volatilidade de FII vs imóvel — frase "imóvel tem volatilidade equivalente porém invisível".
4. FII isento PF perde isenção se >10% das cotas / <50 cotistas / cotista PJ — disclaimer.
5. Vacância 8% histórica já no líquido — reforço no copy.

**Proibições editoriais absolutas:** sem "venda/perda/incrível/excelente/deveria/erro" em qualquer string emitida.

## Out of scope (não fazer neste PR)

- Cache Brapi em DB (ADR-160 Follow-up #2 — ADR irmã pendente). MVP usa fallback hard-coded 8%.
- Schema E1.5 separar `valor_mercado_brl` (Follow-up #3 — fallback `valor_brl` + warning suficiente).
- Subcategoria de aluguel por imóvel-key (Follow-up #4 — rateio proporcional + warning).
- Fatores de redução IR Lei 11.196 (Follow-up #6).
- Anomaly detection inadimplência (A2 difere se MVP).

## Critério de aceite final

- ADR-160 em `Decidido (Sprint X)` com data atual.
- 7 commits coesos squash-merge no main.
- 1 sample workspace com ≥1 imóvel locado renderiza S4 com KPIs corretos, calculadora funcional, ≥1 chip de ação.
- 0 regressão em snapshots OpenAPI/DB schema (ou snapshots regenerados e commitados).
- 0 hex literal novo, 0 token novo, 0 `: float` em campo monetário.

Após merge, atualizar este arquivo com `**Status:** ✅ Entregue (commit `<sha>`)` no topo (padrão dos demais `track_*.md`).
