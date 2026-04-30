# Track IRPF Full Schema Cutover — flag `MATHOMS_E16_SUPERSEDES_E15_BENS`

> **Lane ID:** irpf-full-schema-cutover
> **Branch prefix:** `agent/irpf-full-schema-cutover/*`
> **Depende de:** [track_irpf_full_schema.md](track_irpf_full_schema.md) ✅ (backend + analyzer + E5 wire em `main`) **+** [track_irpf_full_schema_goldens.md](track_irpf_full_schema_goldens.md) ✅ (goldens byte-byte cobrindo paridade) **+** ≥3 declarações reais processadas com paridade `bens_direitos[]` E1.5↔E1.6 byte-byte tolerância 0,01 BRL ([ADR-157](../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full) sub-decisão 8).
> **Conflita com:** `pipeline/stages/consolidate_baseline.py`, `pipeline/stages/extract_baseline.py`, `pipeline/domain/services/baseline_normalizer.py`, `scripts/e5_analyze.py` (consumidor de baseline), `tests/test_e5_golden_execution.py` (golden de paridade — pode mudar). **Se alterar `pipeline/stage_spec.STAGE_RENAME_MAP`** (e.g., novo alias, marcar E1.5 deprecated): também `frontend/src/lib/pipelineStageNames.ts::LEGACY_TO_DESCRIPTIVE` (mirror, gate em `tests/test_frontend_stage_rename_parity.py` — pre-commit **não** detecta).
> **Onda:** **bloqueante** — todas as outras tracks IRPF (UI, goldens) precisam estar mergeadas antes.
> **ADR:** **OBRIGATÓRIA** — nova ADR registra a decisão de virar default + impacto em paridade legado/novo. Provavelmente `ADR-NNN — Cutover E1.5 → E1.6 (Bens & Direitos)`.
> **Supervisão:** **G1 (`senior-cto`)** ADR + estratégia de cutover + rollback plan · **G2 (`data-engineer`)** schema/contract migration · **CTO sign-off** antes de virar default global · **G0 (`financial-planner`)** se houver mudança de classificação de Bens & Direitos no relatório.

> **Objetivo (1 frase):** virar `MATHOMS_E16_SUPERSEDES_E15_BENS` default `true` para workspaces que tenham declarações IRPF processadas via E1.6 — eliminando a duplicação E1.5/E1.6 sem regredir o relatório de quem ainda não rodou E1.6.

---

## Por que esta lane

### Sintoma

Hoje (pós lane `irpf-full-schema`) o pipeline produz **dois artefatos** com Bens & Direitos:

1. **E1.5** (`baseline_patrimonial-1.5_consolidated.json`) — formato legado, `valor_brl: float`, é input canônico do E5 hoje.
2. **E1.6** (`*-1.6_irpf_full.json`) — formato novo, `valor_brl: Decimal`, contém `bens_direitos[]` paridade + todo o resto do IRPF.

Custo: **2 chamadas LLM por declaração** (E1.5 + E1.6), bens & direitos extraídos em duplicata, golden de paridade legado tem que continuar passando para os dois caminhos.

ADR-157 sub-decisão 8 deixou explícito: **cutover é fora da lane backend** e fica para sprint futura. Esta é essa sprint.

### O que falta

1. **Implementar a flag `MATHOMS_E16_SUPERSEDES_E15_BENS`** por workspace — coluna `workspaces.use_e16_supersedes_e15_bens_override: bool | None` (ou via `feature_flags_service` se já houver pattern). Default global `False` durante a fase de validação; quando virar `True`, E1.5 vira no-op e E5 lê só E1.6.
2. **Lógica de short-circuit no orquestrador**: quando flag `True` e `extract_irpf_full` produziu artefato com `bens_direitos[]` não-vazio para o ano-base esperado, **pular** `extract_baseline` e `consolidate_baseline` (ou rodar mas marcar como skipped — cada opção tem trade-off; G1 decide).
3. **Adapter no consumidor** (E5): quando flag `True`, `_e5_load_irpf_kpis` também produz `baseline_patrimonial` consumível pelos analyzers existentes (patrimônio, ratios, score) — conversão Decimal→float **no ponto único do consumer** (ADR-157 sub-decisão 10).
4. **Test de paridade golden**: rerun do golden E5 ([tests/test_e5_golden_execution.py](../../tests/test_e5_golden_execution.py)) com workspace flag `True` deve produzir output **byte-byte idêntico** ao com flag `False` para a parte de `patrimonio` — exceto pequenas diferenças aceitas (Decimal arredondamento). Fail = aborta cutover.
5. **Critério de saída para virar default global**: ADR-157 sub-decisão 8 já especifica — ≥3 declarações reais validadas com paridade byte-byte (tolerância 0,01 BRL). Esta lane **implementa a flag**; virar default é PR separado depois.
6. **Plano de rollback**: documentado na ADR. Se cutover quebrar relatório em produção, virar flag `False` e investigar.
7. **Deprecation path para E1.5**: depois que flag global virar `True` e estabilizar (≥4 semanas em produção), abrir lane `track_e15_baseline_removal.md` que remove `extract_baseline`/`consolidate_baseline` do `STAGE_REGISTRY`. **Fora desta lane.**

---

## Regras inegociáveis

1. **Goldens existentes não regridem nesta lane** — `test_e5_golden_execution` continua passando para workspaces sem IRPF e para workspaces com flag `False`. Mudança de output só quando flag `True`.
2. **Decimal→float conversion em ponto único** ([ADR-157](../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full) sub-decisão 10): o consumer (E5 adapter) converte Decimal-string do E1.6 para o formato float legado de `baseline_patrimonial-1.5_consolidated.json` na borda. Pipeline E5 nunca recebe Decimal misturado com float.
3. **Tolerância 0,01 BRL** ([ADR-097/D5](../DECISIONS.md#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)) — paridade byte-byte de `bens_direitos[]` E1.5↔E1.6 com essa tolerância.
4. **Flag por workspace, não global** primeiro — gradual rollout. Ativar para workspaces de teste, depois canários, depois default.
5. **ADR antes de codar** — gate G1.
6. **Stateless** ([ADR-111](../DECISIONS.md#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)): a flag é lida por request/run via `WorkspaceContext`, sem cache em memória.
7. **Stage rename parity** — se mexer em `pipeline/stage_spec.STAGE_RENAME_MAP` (alias novo, deprecação), atualizar **no mesmo PR** `frontend/src/lib/pipelineStageNames.ts::LEGACY_TO_DESCRIPTIVE`. Pre-commit não cobre — só `pytest tests/test_frontend_stage_rename_parity.py` quebra. Caso real recente: lane `irpf-full-schema` adicionou `E1.6: extract_irpf_full` no backend e a parity ficou pendente até a UI lane fixar (commit `8f2e145`).

---

## Entregáveis

### A. ADR

`docs/DECISIONS.md` ganha `ADR-NNN — Cutover E1.5 → E1.6 (Bens & Direitos via flag)` cobrindo:
- Contexto: 2 fontes de verdade desde lane `irpf-full-schema`.
- Alternativas: (1) virar E1.6 default direto; (2) flag global on/off; (3) flag por workspace gradual; (4) coexistir indefinidamente.
- Decisão: (3) flag por workspace + critério de saída para virar default.
- Consequências: ✅ menos LLM cost por workspace; ⚠️ janela de coexistência mais longa; ❌ debt técnico até deprecation final.
- Rollback plan: virar flag `False` no workspace afetado, investigar via logs `mathoms.pipeline.e16`.
- Plano de deprecation E1.5 (sprint futura, fora desta ADR).

Rodar gates: `python3 dev/check_adr_anchors.py && python3 dev/build_adr_toc.py --check && python3 dev/validate_adr_format.py`.

### B. Flag por workspace

Decisão: usar pattern existente `feature_flags_service` (ADR-076-similar) ou seguir `use_db_artifacts_override` ([CLAUDE.md §Feature flag MATHOMS_USE_DB_ARTIFACTS](../../CLAUDE.md)).

Pattern provável (alinhar com G1):

```python
# backend/app/models/workspace.py
class Workspace(Base):
    ...
    use_e16_supersedes_e15_bens_override: Optional[bool] = mapped_column(Boolean, nullable=True)
```

```python
# backend/app/services/feature_flags_service.py
def use_e16_supersedes_e15_bens(workspace: Workspace) -> bool:
    if workspace.use_e16_supersedes_e15_bens_override is not None:
        return workspace.use_e16_supersedes_e15_bens_override
    return _global_default_e16_supersedes_e15_bens()  # False inicialmente
```

Alembic migration: `add_column workspaces.use_e16_supersedes_e15_bens_override Bool nullable`.

### C. Short-circuit no orquestrador

Decisão (G1): "skip" vs "execute mas no-op". Recomendação inicial:
- Quando flag `True` e workspace tem ≥1 declaração processada via E1.6 (`store.list_keys("extract_irpf_full")` não-vazio):
  - `extract_baseline` (E1.5) vira no-op (retorna `{"skipped": True, "reason": "E1.6 supersedes (flag MATHOMS_E16_SUPERSEDES_E15_BENS active)"}`)
  - `consolidate_baseline` (E1.5c) lê do E1.6 + converte Decimal→float em adapter

Alternativa: orquestrador pula a stage inteira via `STAGE_REGISTRY` modificado dinamicamente — mais arriscado.

### D. Adapter no consumer (E5)

```python
# scripts/e5_analyze.py ou pipeline/domain/services/baseline_normalizer.py
def _build_baseline_from_e16(payloads: list[dict]) -> dict:
    """Converte payloads E1.6 (Decimal-string) para formato baseline_patrimonial-1.5_consolidated (float).

    Aplica em ponto único conforme ADR-157 sub-decisão 10.
    """
    # ...
```

Quando flag `True`:
- `_e5_init_workspace`/equivalente lê `extract_irpf_full` artefatos.
- Constrói baseline equivalente.
- E5 segue rodando com o input baseline-shaped.

### E. Tests

```
tests/test_irpf_e15_e16_parity.py   # paridade byte-byte de bens_direitos[] entre E1.5 e E1.6
tests/test_e5_with_flag_on.py       # E5 produz output ~idêntico com flag True (modulo arredondamento)
tests/test_workspace_flag_irpf.py   # flag override per-workspace
backend/tests/test_workspaces_irpf_flag_endpoint.py  # admin endpoint para virar a flag
```

Goldens: rodar `tests/test_e5_golden_execution.py` com workspace flag `True` e comparar — deve produzir mesmo output (modulo Decimal arredondamento) quando E1.6 já tem `bens_direitos[]` equivalente.

### F. Telemetry + observability

- Log estruturado em `mathoms.pipeline.e16` quando flag dispara short-circuit: `logger.info("e15_skipped_due_e16_supersede", extra={"workspace_id": ws_id})`.
- Métrica de count: quantos workspaces estão na flag, quantas runs pulam E1.5 por mês.
- Alerta SRE: se >X% de workspaces rodam com flag `True` e algum tem `extract_irpf_full` com `confidence < 0.7`, **forçar fallback para E1.5** (não confiar em IRPF inseguro).

### G. Documentação

- ADR-NNN.
- `docs/CHANGELOG.md` entrada datada.
- `docs/ARCHITECTURE.md §Fluxo de runtime` atualizado se short-circuit altera diagrama.
- `docs/BACKLOG.md` A8.2 sub-lane `irpf-full-schema-cutover` ✅.
- `CLAUDE.md` §Feature flag — adicionar entrada `MATHOMS_E16_SUPERSEDES_E15_BENS` no padrão de `MATHOMS_USE_DB_ARTIFACTS`.

---

## Subagentes obrigatórios

| Gate | Quando | Subagente | O que aprovar |
|---|---|---|---|
| **G1** | Antes de codar | `senior-cto` | ADR aprovada, estratégia (skip vs no-op), rollback plan, decisão sobre Alembic. |
| **G2** | Antes de gravar adapter | `data-engineer` | Conversão Decimal→float no consumer, contrato compatível com E5 atual, paridade golden. |
| **G3** | Antes de PR | `senior-cto` (review) + `sre-devops` | Telemetria, alerta SRE, plano de rollback testado. |
| **G0** | Antes de virar default | `financial-planner` | Validar que classificação de bens não muda — se mudar, requer aviso ao usuário. |
| **CTO** | Antes de virar default global (PR separado pós-cutover) | `senior-cto` | Decisão final de promover. |

---

## Sequência de commits sugerida

```
1. docs(adr): ADR-NNN cutover E1.5 → E1.6 — Proposto
2. db(alembic): add column workspaces.use_e16_supersedes_e15_bens_override
3. feat(flag): feature_flags_service.use_e16_supersedes_e15_bens (per-workspace + global default False)
4. feat(pipeline): adapter Decimal→float no consumer E5 (baseline_normalizer ou helper E5)
5. feat(orchestrator): short-circuit extract_baseline + consolidate_baseline quando flag True + E1.6 OK
6. test(parity): bens_direitos[] E1.5 ↔ E1.6 byte-byte (tolerância 0,01 BRL) com fixtures sintéticas
7. test(e5): E5 golden execution com flag True — output equivalente
8. feat(observability): log estruturado + métrica + alerta SRE
9. docs(adr): ADR-NNN → Decidido + atualizar ARCHITECTURE/CHANGELOG/CLAUDE.md
10. (sprint futura, PR separado) chore: virar default global após critério de saída atendido
```

---

## Definition of Done

- [ ] ADR-NNN aprovada por `senior-cto` (G1) em `docs/DECISIONS.md`
- [ ] G2 (`data-engineer`) sign-off na ADR/PR
- [ ] G0 (`financial-planner`) revisou impacto em classificação de bens
- [ ] `pre-commit run --all-files` passa
- [ ] `pytest tests -q` + `pytest backend/tests -q` passam
- [ ] `pytest tests/test_frontend_stage_rename_parity.py` passa (verifica espelho `pipelineStageNames.ts` ↔ `STAGE_RENAME_MAP`)
- [ ] `cd frontend && npm test -- --run` passa
- [ ] Test de paridade `bens_direitos[]` E1.5↔E1.6 passa byte-byte (tolerância 0,01 BRL) em ≥3 fixtures sintéticas + ≥1 real anonimizada
- [ ] Test de E5 golden com flag `True` produz output equivalente ao golden atual (modulo arredondamento aceito)
- [ ] Alembic migration revisada por G2 + smoke test `alembic upgrade head` em DB de dev
- [ ] Telemetry + alerta SRE funcionando (logs aparecem em `mathoms.pipeline.e16`)
- [ ] Plano de rollback documentado e testado (virar flag `False` em workspace e ver E5 voltar a rodar com E1.5)
- [ ] PR mergeada em `main` com CI verde
- [ ] BACKLOG A8.2 sub-lane `irpf-full-schema-cutover` ✅
- [ ] **A flag NÃO é virada default global nesta PR** — ativar em workspaces de teste apenas (canary). Default global é PR separado após critério de saída ADR-157.

---

## Riscos / pontos de atenção

1. **Golden E5 quebra no flag True** — pode haver pequenas diferenças de arredondamento Decimal vs float. Decidir tolerância antes de bater golden (provavelmente 0,01 BRL como ADR-097/D5).
2. **Workspace tem E1.6 com bens_direitos[] vazio.** Se E1.6 rodou mas não extraiu bens (PDF corrompido, LLM truncou), short-circuit de E1.5 deixa o relatório sem patrimônio — **catastrófico**. Mitigação: short-circuit só quando E1.6 tem `bens_direitos[]` não-vazio E `confidence >= 0.7`.
3. **Migração de workspace existente** — workspace com baseline E1.5 já consolidado em DB precisa decidir: invalidar e recomputar, ou manter até próxima run?
4. **Duplicidade temporária consome cache LLM.** Antes de virar default, dois workspaces na flag pagam dobrado. Mitigação: prompt caching já em uso.
5. **Reversibilidade.** Quando virar flag `False` depois de já ter rodado com `True`, baseline_patrimonial original precisa estar ainda em DB ou reprocessar E1.5. Garantir não apagar artefato E1.5 antigo na coexistência.
6. **Adapter Decimal→float pode introduzir bug de arredondamento** — escrever testes especificamente para edge cases (valores como `1234.567` que arredondam diferente).
7. **Mudança comportamental imperceptível.** Cutover sem usuário perceber (relatório igual) é o ideal — qualquer diferença visível é bug ou requer aviso. G0 valida.

---

## Referências

- [ADR-157](../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full) sub-decisão 8 — critério de cutover
- [ADR-097/D5](../DECISIONS.md#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy) — tolerância 0,01 BRL
- [ADR-111](../DECISIONS.md#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6) — stateless
- Pattern de flag existente: `MATHOMS_USE_DB_ARTIFACTS` (ver [CLAUDE.md §Feature flag](../../CLAUDE.md)) e `workspaces.use_db_artifacts_override`
- E1.5 baseline normalizer: [pipeline/domain/services/baseline_normalizer.py](../../pipeline/domain/services/baseline_normalizer.py)
- E5 wire IRPF (lane irpf-full-schema): [scripts/e5_analyze.py::_e5_load_irpf_kpis](../../scripts/e5_analyze.py)
- Goldens existentes: [tests/test_e5_golden_execution.py](../../tests/test_e5_golden_execution.py)
