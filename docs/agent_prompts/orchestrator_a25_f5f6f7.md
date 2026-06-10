# Orquestração — A25 Data Lineage · F5 (reverso) + F6 (produto N1/N2) + F7 (debug LLM) + herdados

> Instância do [_TEMPLATE_orchestrator.md](_TEMPLATE_orchestrator.md) para o
> **fast-follow** do plano [DATA_LINEAGE](../plan/DATA_LINEAGE/_README.md). Sucede a
> A24 (`done` 2026-06-10 — G3 atingido, KR2 4/6, de-leak cirúrgico confirmado no dado
> real via G-f). A A25 **colhe o valor** do substrato: query reversa, UI cliente e o
> agente de debug LLM — mais dois herdados (cutover K4→E4 e a **decisão** do flip
> strict do `evidencia_path`).
>
> **Pré-revisado** por `product-manager` (ondas/KR/corte) + `senior-cto`
> (dependências/boundary) em 2026-06-10 — ajustes incorporados: split do flip dedup
> E4→v2 em lane própria, F6 independente da edge table, gate da decisão-strict com
> piso de amostra + carry-over, eval LLM em nightly, precedência de corte F7>F6.
>
> **Uso:** copie o bloco abaixo no início da sessão. Respeita [CLAUDE.md](../../CLAUDE.md)
> e delega aos especialistas de [`.claude/agents/`](../../.claude/agents/).
>
> **Quando arquivar:** sprint A25 `done` (KR1/KR3 verdes + decisão do flip registrada).
> Mover para [`archive/`](archive/) com data.

---

```
Continue o plano DATA_LINEAGE — **Sprint A25: F5 (lineage reverso) + F6 (produto N1/N2)
+ F7 (debug substrate LLM) + herdados (cutover K4→E4 · decisão do flip strict do
evidencia_path)**. Fatie em branches/PRs próprios. Perfil da sprint: DIFERENTE da A24 —
pouco risco de número (lineage é aditivo), muito risco de UI/UX (F6 é a 1ª superfície
cliente do lineage) e de eval LLM (F7 define KR1/KR3).

## Onde estamos (em origin/main — NÃO refazer)
Sprint A24 done (docs/sprint/A24/_README.md): extração pura, substrato de rebaseline
endurecido (manifesto ref/adr/rationale + check_golden_rebaseline_isolation por commit
+ invariantes por categoria), `_lineage` field-level em patrimonio.liquido/bruto +
reserva_emergencia.total_liquida + fluxo_caixa.despesa_total + investimentos.total,
LineageResolver + lineage_registry + dev/explain_number.py + check_lineage_refs/
check_lineage_sum, evidencia_path E5→E6 em modo warn (telemetria ativa desde
2026-06-10). A23.l4 slices 1–3: 1–2 em main, **slice 3 (backfill) em PR — GATE da l1**.

## Leia primeiro (canônico)
1. CLAUDE.md — code style, git/PR, delegação, "Concluído".
2. docs/plan/DATA_LINEAGE/_README.md — §Arquitetura D (edge table/B6) + F (produto) +
   G (debug LLM), §Verificação F5/F6/F7, §Guard-rails G-d/G-g/G-h, §KRs, §Deferido
   (NÃO construir: MCP prod, índice reverso por rule_ref, adapter feed).
3. docs/sprint/A25/_README.md (MOC, promover candidate→current no kickoff) +
   docs/sprint/A24/lanes/A24-l5-*.md §Decisões (padrão _lineage — vale p/ tudo) +
   A24-l6-*.md §Resultado (K4 0% em E4) + A24-l4-*.md (evidencia_path warn).
4. docs/adr/279 (edge table DDL + B6/B8) · 281 (renderer/diff/tools/eval/KRs) ·
   282 (**§7 é GATE de sequenciamento, não o desenho do flip dedup**) · 045 (tooltip
   que a F6 substitui) · docs/sprint/A23/lanes/A23-l4-*.md (slices 4–5).
5. COPY_GUIDELINES §6.3 (zero jargão de pipeline na UI cliente) — régua da F6.

## Kickoff (antes de qualquer lane)
- Promover A25 candidate→current (MOC + SPRINTS-active, PR docs-only) — par
  product-manager (ondas) + information-architect (forma) se houver dúvida de formato.
- **Reconciliar o denominador do KR2** com product-manager: A24 reporta "4/6" mas
  lista 5 dot-paths (liquido+bruto contam como 1 agregado?). Fechar a lista canônica
  dos 6 e registrá-la no plano §KRs. Candidatos default p/ os restantes:
  **fluxo_caixa.fluxo_liquido** (decisão de capacidade de poupança; invariante G-b já
  existe) + **dividas.total** (prioridade de quitação; Σ passivos direta). Se
  "patrimônio investível efetivo" voltar à mesa → gatilho financial-planner.
- **Acumular telemetria do evidencia_path DESDE O DIA 1**: gerar parecer sobre goldens
  + dogfood na abertura (a decisão da l7 precisa de amostra; não deixar p/ o fim).

## As lanes (crie docs/sprint/A25/lanes/A25-l{1..}-*.md; IDs livres)
ORDEM/DEPENDÊNCIAS — l3 + l4 + destrave da l1 abrem JÁ (independentes); l5 após
decisão de exposição do collapsed_count; l2 após l1; l6 após l2; l7 por último.

- a23l4-cutover-override (A25.l1 — GATE DE ABERTURA: A23.l4 slice 3 mergeado; se não
  estiver, FECHE o slice 3 primeiro): slices 4–5 da A23.l4 (cutover do override p/
  identidade v2 + M2 destrutiva no FIM, janela PITR + runbook G-e). ⚠️ NÃO inclui o
  flip dedup E4→v2 (é a l2 — blast radius distinto). Critério: zero override órfão
  novo; gate dogfood de reancoragem ≥ limiar (ADR-282 §7) ANTES de declarar shipped.
  Co-design: data-engineer + senior-cto.

- dedup-e4-flip-v2 (A25.l2, após l1 — LANE PRÓPRIA por blast radius): flip do consumo
  E4 para identidade v2 (passo 2 da B4, ADR-278/282 §7). Muda como E4 chaveia/colapsa
  → REBASELINE esperado de goldens E3/E4/E5 + view-model snapshot, manifestado
  valor-a-valor (ref/adr/rationale) em commit isolado + label golden-rebaseline + 2º
  revisor (G-c). ⚠️ o DESENHO do flip (algoritmo/rollout/rollback) NÃO está em ADR —
  abrir seção na lane ou nota ADR antes de codar. Invariantes de conservação são a 2ª
  testemunha. Co-design: data-engineer + senior-cto.

- dl-f5-reverso (A25.l3, ∥ INDEPENDENTE — abre já): tabela `artifact_lineage_edge`
  (DDL ADR-279 §D; CONCURRENTLY fora de transação; runbook data_lineage_migrations.md)
  + derivação/materialização com BOUNDARY CRAVADO: **deriver PURO em
  pipeline/domain/services/ (lineage_edge_deriver — _lineage inline → edges) + writer
  backend em backend/app/services/ (SQLAlchemy, espelha DBArtifactStore)** — pipeline/
  não importa sqlalchemy. Se vira stage no FULL_ORDER ou hook pós-run no backend →
  decidir no co-design (stage que não produz artefato tensiona ADR-093). **B6: DELETE
  cross-run, retenção N=1.** Verificação: query reversa "números que dependem da fonte
  X" num run canônico; cadeia P0 reconstruída; teste de retenção (2 runs não acumulam).
  NOTA anti-armadilha: edge table N=1 NÃO é fonte de auditoria de citação do parecer —
  auditoria histórica usa o _lineage inline do E5 daquele run (pipeline_artifacts).
  Co-design: data-engineer + senior-cto.

- dl-f7-debug-llm (A25.l4, ∥ — só precisa do _lineage forward que JÁ existe): renderer
  LLM de trace linearizada (passos numerados raiz→folha, inputs como #N, ~30-60
  tok/nó, teto 1.5k tokens inline, colapsa subárvore sem anomalia, anomaly-first) +
  `lineage_diff(tree_a, tree_b)` (puro: nós mudados + first-divergent-leaf +
  propagação) + tools explain_number/expand_node/trace_source (cap
  max_expand_iterations:6, whitelist de field, audit em _meta.tool_trace) + eval de
  injeção determinística (20-30 casos PII-sintético sobre goldens; temp=0, seed
  pinado, **model por VERSION-ID literal commitado, nunca alias**). **Eval LLM roda no
  NIGHTLY (G-g), não em PR** — PR roda só os goldens determinísticos (renderer,
  lineage_diff, check_lineage_refs); teto de tokens/custo por execução + skip sem
  ANTHROPIC_API_KEY (degrada p/ determinístico). KR1 ≥85% (regressão >2% bloqueia);
  KR3 p95 ≤6. MCP prod DEFERIDO. Co-design: prompt-engineer + senior-cto.

- dl-f6-produto-n1n2 (A25.l5 — **INDEPENDENTE da edge table**: N2 é forward
  single-number, LineageResolver sobre _lineage inline + _report_lineage coarse
  bastam): flag de feature (registrar em DEFAULTS de feature_flags_service no MESMO
  PR) + exposição no view-model + selo N1 no <MonetaryValue/> (prop provenance?,
  underline pontilhado + aria-label) + popover N2 "Como chegamos a esse número"
  (4 verbos 1ª pessoa com contagens: Li → Conferi → Classifiquei → Calculei; dedup
  como trabalho A FAVOR). ⚠️ Dependência REAL do "Conferi": `dedup_report.collapsed_count`
  hoje só existe em LOG (e4_categorizer_adapter.py:232) — expor no payload E4 ou em
  `_lineage.signals` é micro-trabalho de pipeline DESTA lane (rebaseline não-monetário
  do view-model snapshot, label golden-rebaseline). ⚠️ Definir comportamento do selo/
  popover no EXPORT PDF (Playwright renderiza a mesma rota — selo suprimido ou
  estático no print?). N3 drawer NÃO é desta lane (fast-follow). ~6 elegíveis em
  report_layout.yaml. Critérios (lista completa no plano §Verificação F6): flag off ⇒
  relatório === atual E flag-ON === flag-off exceto máscara do selo (G-h); snapshot
  isolado do affordance light+dark; **G-d: snapshot textual pt-BR dos valores
  expostos**; **G-g: re-armar visual+@critical no filtro lineage|report + canary
  nightly verde**; copy gate (4 verbos + zero jargão §6.3); a11y completo (teclado,
  Escape, foco, prefers-reduced-motion, badge needs_review); mobile <md degrada p/
  drawer; **teste de confiança 5s dogfood** (dogfooder responde "de onde veio?" em 1
  frase sem abrir nada técnico) — é o único teste de VALOR da F6, não pule.
  Co-design: product-designer + senior-cto (exposição view-model).

- kr2-resto (A25.l6, **P2/stretch — cortável sem culpa**, após l2): fecha KR2 6/6 —
  _lineage nos 2 agregados definidos no kickoff (padrão A24.l5) + member_hashes REAIS
  no nó de despesa (⚠️ depende do FLIP DEDUP da l2, não só do cutover l1): trocar
  signals.k4_coverage="partial" → cobertura total + check_lineage_sum
  Σ amount[member_hashes] == value (cents int, run_id — B8) + teto inline 200 (acima →
  edge table da l3, decisão registrada) + G-d nos agregados novos. Se l1/l2
  escorregarem, esta lane cai — e tudo bem. Co-design: herda A24.l5.

- evidencia-strict-decision (A25.l7, ÚLTIMA — requisito de done = **DECISÃO INFORMADA,
  não flip incondicional**): analisar telemetria do evidencia_path
  (pipeline_stage_logs.output_summary: evidencia_failed/verified + failures_by_layer).
  GATE: **taxa de violação <5% sobre ≥20 gerações** → flipa (1 linha:
  evidencia_verification_mode strict em config/prompts/parecer_planejador.yaml, PR
  com a análise no corpo). Taxa ≥5% → NÃO flipa: ajustar regex/prompt (co-design
  prompt-engineer) e re-medir. **Amostra <20 gerações ao fim da sprint → registrar
  decisão "carry-over A26 com gate idêntico" e a sprint fecha done mesmo assim** —
  o flip não sequestra o fechamento.

## Precedência de corte (se houver squeeze)
**F7 > F6** — F7 ancora KR1/KR3 e ataca a dor-raiz do plano (arqueologia de bug);
F6 não move KR e o público hoje é dogfood. MLP da sprint = l3+l4+l5 + decisão l7;
l1 must-condicional ao slice 3; l2 must-se-l1; l6 é stretch.

## Inegociáveis
- Padrão _lineage da A24.l5 para TODO bloco novo (value string .2f do payload, inputs
  sort canônico, zero timestamp, topologia honesta, member_hashes só onde K4 existe).
  Rebaseline via golden_diff + manifesto + commit isolado + label golden-rebaseline.
  Invariantes de conservação NÃO quebram.
- F6: número final soberano; lineage opt-in; linguagem de "conferência", não
  "estimativa"; zero jargão de pipeline na UI.
- F7: determinismo total no eval; custo/latência são features.
- F5: edge table DERIVADA (rebuildável), nunca fonte primária; retenção N=1 (B6).
- Dinheiro nunca float (ADR-090); stateless (ADR-111); pipeline/** não importa
  fastapi/celery/sqlalchemy. CI verde antes do merge. Concluído = PR squashed em main.
- Co-design ANTES de codar; múltiplos gatilhos → especialistas em PARALELO.
- ⚠️ Operacional: auto-merge + main movimentado = deadlock de update-branch
  (GITHUB_TOKEN não dispara CI). Padrão: NÃO habilitar auto-merge; monitor que mergeia
  --squash quando CI verde; rebase+force-push próprio se BEHIND; "Title" falhando com
  timeout de Docker Hub = infra, re-rodar.

## Antes de começar
- git fetch origin && git worktree list && git for-each-ref --sort=-committerdate
  refs/remotes/origin/agent/ | head (confirme ninguém em dl-f5-*/dl-f6-*/dl-f7-*/
  a23l4-*/dedup-e4-*). Confirme A23.l4 slice 3 (gate l1) e gere parecer p/ telemetria
  (gate l7).
- Crie UMA branch por lane (agent/<slug>/<yyyyMMdd-HHmm>) a partir de origin/main.
- Comece por l3 (dl-f5-reverso) + l4 (dl-f7-debug-llm) + l5 (dl-f6-produto) em
  paralelo + destrave da l1. Anuncie cada operação git. Comece lendo as fontes e
  propondo plano + co-design por lane.
```
