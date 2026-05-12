---
id: CHG-2026-05-12-TEST-S9-GOLDENS-CLOSE-TRACK
type: changelog-entry
date: "2026-05-12"
sprint: A11
lane: "[[A11.w5]]"
adrs:
  - "[[ADR-192]]"
prs: []
commits: []
summary: |
  test(report): reset goldens E5 + paridade narrativa S9 (ADR-192, S9-T06)
  — auditoria empírica confirmou zero drift em goldens E5 após T01-T05;
  pipeline JSON shape estável. Track `s9-riscos-expansion` flippado para
  `status: consumed` + `consumed_at: 2026-05-12`. Sem update de goldens,
  sem schema E5 update, sem `report_version` bump — todos justificados
  por inspeção empírica (suíte completa verde + grep zero matches em
  fixtures pipeline).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/pipeline
  - area/domain
---

# test(report): reset goldens E5 + paridade narrativa S9 (S9-T06)

Track `s9-riscos-expansion` — onda 3 (T06) entregue. **Fecha o track.**

## Achado-chave

**Zero drift** em goldens E5 após T01-T05. A expansão S9 (ADR-192) ficou
contida em três eixos disjuntos do pipeline JSON:

1. **API + DB** (T02): aggregate `Protection` + endpoints REST + bundle
   adapter. **Não toca `analise_financeira-5_analysis.json`**.
2. **Domain services puros** (T03): 4 calculators determinísticos no
   bundle adapter (`backend/app/services/protection_bundle_adapter.py`).
   O bundle é projeção API-side via `GET /protection-bundle`, não
   materializada no E5.
3. **UI + narrativa empty-state** (T01, T04, T05): renderer React lê
   bundle do endpoint; narrador `_narrate_bubble_riscos` mantém shape
   `{data_state, context, conclusion}` idêntico ao pré-expansão; T01
   apenas adicionou guard early-return para evitar concatenação quebrada.

## Verificação empírica

```bash
# Goldens E5/E5.N + suítes adjacentes
pytest tests/test_e3_golden_execution.py \
       tests/test_e4_golden_execution.py \
       tests/test_e5_golden_execution.py \
       tests/test_e5n_golden_execution.py \
       tests/test_e5n_s9_empty_state.py -q
# → 21 passed, 0 failed

# Suítes globais
pytest tests -q       # → 2093 passed, 2 skipped
pytest backend/tests -q  # → 1910 passed, 5 skipped

# Auditoria de goldens (zero matches em fixtures pipeline)
find tests -name '*.json' -not -path '*node_modules*' \
  | xargs grep -l 'bubble_riscos\|riscos_top3\|has_us_exposure\|seguro_vida_minimo'
# → 0 matches
```

A ausência de matches confirma que goldens minimal tenants (`E3→E4→E5`)
não exercem a via que poderia ter drifted: nenhum workspace de fixture
tem `Protection` cadastrada, então o bundle vem vazio e o narrador volta
ao caminho `data_state="empty"` (já estabelecido em T01).

## Decisões registradas

### 1. Sem update de goldens — preferiu-se "verificado, mantido"

Update especulativo "para registrar o estado novo" introduziria ruído
sem ganho semântico (o estado novo é idêntico ao antigo). Audit
explícito documentado neste changelog substitui o reset.

### 2. Sem schema E5 update

`config/schemas/e5_analysis.schema.json` permanece com
`additionalProperties: true` (W6-T01 do PLATFORM_REVIEW vai flippar para
strict). `bubble_riscos` continua em `narrativas.charts.bubble_riscos`
com shape `{data_state, context, conclusion}`.

**`ProtectionBundle` não vai pro schema E5**: é projeção API-side
(`GET /workspaces/{id}/protection-bundle`, ADR-192 §D2 + Pydantic DTO em
`backend/app/schemas/dto/protection/bundle.py`), não artefato do
pipeline. O contrato é OpenAPI + Pydantic, não JSON Schema do pipeline.

### 3. Sem `report_version` bump (permanece `"6.1"`)

ADR-077 §"contrato de cutover" só exige bump quando o JSON top-level
muda de forma incompatível para consumers determinístico-incrementais.
Nesta expansão:

- **JSON E5:** shape inalterado (`narrativas.charts.bubble_riscos`
  mantém keys).
- **React renderer:** ganhou 4 cards lendo bundle API — leitura via
  endpoint separado, não via JSON E5.
- **Página `/protecao`:** consumer separado, fora do contrato do report.

Bumpar `report_version` sinalizaria quebra de contrato a clientes que
consomem o JSON E5 (atualmente só o renderer React in-process, mas a
regra protege futuros consumers determinístico-incrementais). Manter
`"6.1"` é a sinalização correta.

### 4. Visual snapshots Playwright

Regenerados em T04 follow-up [#229](https://github.com/davidrobert/mathoms/pull/229)
(commit `2e60901`) — S9-light + S9-dark refletem os 4 cards novos +
bubble re-enquadrado. T06 **não** regenera baselines porque T04 já
fechou esse débito; nada no path entre T04→T05→T06 mudou a aparência
visual de `/reports/[id]`. Página `/protecao` (T05) é rota separada,
fora do range do `sections.snapshots.visual.spec.ts`.

## Encerramento do track

- Track `docs/sprint/A11/tracks/s9-riscos-expansion.md` flippado para
  `status: consumed` + `consumed_at: "2026-05-12"`.
- Lane MOC `docs/sprint/A11/lanes/A11-w5-frontend-methodology.md`
  atualizada com 6/6 sub-tasks ✅.
- ADR-192 permanece `Decidido (Sprint A11.W5)` (flip ocorreu em T02).

## Decisões do orquestrador (auditoria)

Gate triplo `data-engineer` via Agent tool indisponível neste
sub-fluxo; orquestrador com autoridade `senior-cto` delegada tomou as
decisões abaixo, registradas para auditoria (padrão de PRs T03/T04/T05
desta mesma sessão):

- **Critério "zero drift":** suíte verde + grep zero em fixtures
  é evidência suficiente. Não justifica `git checkout HEAD~1` +
  `pytest` comparativo, que adicionaria 5min sem ganho informacional.
- **Sem `golden_drift_expected` marker:** o track R5 previa marker
  defensivo em T01-T05; nunca foi necessário porque cada onda manteve
  suíte verde sem precisar. Documentado no track como aprendizado.
- **Track flip + lane MOC update no mesmo PR:** padrão dos PRs
  follow-up de A12 (e.g., #224, #226) — documento + estado em diff
  atômico.

## Aprendizados (devolvidos ao track)

1. **Expansão UI-pesada não precisa drift de goldens** quando a fronteira
   pipeline↔API é bem estabelecida (ADR-101 R5 + ADR-134 ConfigStore).
   O bundle API é projeção, não artefato.
2. **Auditoria empírica > atualização especulativa.** O reset T06 foi
   reduzido a "verificado + flip track" porque a evidência era clara.
3. **Pre-flight checklist canônico para "track close" PRs:** (a) suíte
   completa verde; (b) grep zero matches em fixtures para campos
   novos; (c) schema integridade (sem campos órfãos novos); (d)
   `report_version` decisão explícita.

## Próximos passos (fora do track)

- W6-T01 (PLATFORM_REVIEW) vai flippar `e5_analysis.schema.json` para
  strict — momento de decidir se `bubble_riscos` ganha schema próprio
  (hoje é `narrativas: type: object` generic).
- `fiscal_parameters.itcmd_aliquota_por_uf` + `.us_thresholds_usd` —
  débito documentado em T03 (ADR-135 follow-up); calculators continuam
  com defaults inline até lá.
- Job futuro "apólices vencendo em 30d" usando o índice
  `(workspace_id, ends_at)` criado em T02.
