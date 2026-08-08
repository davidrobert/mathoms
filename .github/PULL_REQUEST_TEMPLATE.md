<!--
  Template de PR — Mathoms AI
  Não delete os comentários HTML; eles desaparecem do render mas
  documentam o template para quem editar no futuro.

  Título: deve seguir Conventional Commits (validado por job
  "Title (Conventional Commits)" no workflow PR Quality).
  Ex.: feat(api): adiciona endpoint /v1/reports/export
       fix(pipeline): aborta E3 quando saldo inicial vem como NaN
       refactor(frontend): extrai ReportSection de Report.tsx
-->

## Sumário
<!-- 1-3 bullets focados no PORQUÊ. O diff já mostra o QUE. -->
-

## Tipo de mudança
<!-- Marque o(s) que se aplica(m) -->
- [ ] feat (nova capacidade visível)
- [ ] fix (correção de bug)
- [ ] refactor (sem mudança de comportamento observável)
- [ ] perf (otimização)
- [ ] test (testes adicionados/modificados)
- [ ] chore (build, deps, tooling)
- [ ] docs (apenas documentação)
- [ ] **breaking change** ⚠️

## ADR / contexto
<!--
  Se introduz decisão arquitetural não-trivial: link para ADR-NNN ou
  justifique por que não precisa.
  Se executa um track plan: link para docs/agent_prompts/track_<slug>.md.
-->
N/A.

## Como testar manualmente
<!-- Golden path em 2-4 passos. Comandos exatos quando aplicável. -->
1.
2.

## Testes automatizados
<!-- Bug fix → teste de regressão obrigatório (escrito ANTES do fix). -->
- [ ] Pipeline: `pytest tests -q` verde
- [ ] Backend: `pytest backend/tests -q` verde
- [ ] Frontend unit: `cd frontend && npm test -- --run` verde
- [ ] Frontend E2E (se mexeu em fluxo `@critical`): `cd frontend && npm run test:e2e` verde
- [ ] Bug fix? Adicionei teste que falha sem o fix.

## Mexeu no relatório?
<!--
  Aplique se o diff toca `frontend/src/components/report/**`,
  `frontend/src/app/reports/**`, `config/report_layout.yaml`,
  `design-tokens/**`, ou fixtures/specs do relatório. Histórico de
  regressão pós-merge (#147, #148, #150, #151) levou a este gate.
  O pixel-diff **não roda sozinho**: a ADR-210 §camada 1 tirou o
  auto-trigger por path, e desde 2026-06-15 o nightly que compensava
  está `disabled_manually`. Sem o label, este checklist é a única
  cobertura do relatório neste PR.
-->
- [ ] Apliquei o label `visual` **na criação do PR** (posto depois, `labeled` não está em `on.pull_request.types`: o CI não redispara e o job fica `skipping` — verde por omissão).
- [ ] Job `frontend-visual` rodou e está verde. Falhou? Diff baixado em `report-visual-snapshots`, baseline atualizada via `gh workflow run CI -f run_visual=true -f update_visual_baselines=true` se a mudança é intencional.
- [ ] Mudança visível em UI? Invoquei o subagente `product-designer` para revisar copy / hierarquia / densidade / tokens (`Agent(subagent_type="product-designer", …)`). Justificativa caso N/A:
- [ ] Validei manualmente em **light + dark** com pelo menos uma das fixtures de variância: `medium`, `long-strings`, `large-values`, `sparse-data` (`frontend/tests/e2e/fixtures/reports/`).
- [ ] Não usei hex literal — toda cor via `var(--brand-*)` / `var(--surface-*)` / `var(--semantic-*)`.
- [ ] Valores monetários via `<MonetaryValue/>` (font-mono + tabular-nums).

## Breaking change
<!-- Marque ⚠️ acima se sim. Descreva: o que quebra, plano de migração, deprecation window. -->
N/A.

## Checklist obrigatório
- [ ] `pre-commit run --all-files` verde local
- [ ] Conventional Commit no **título do PR** (vira commit message no squash-merge)
- [ ] Commits coesos (1 mudança lógica por commit; refactor separado de feat)
- [ ] Sem dado sensível (CPF, valores reais, secrets, conteúdo de extrato/fatura) em diff/logs/fixtures
- [ ] Endpoint JSON novo/alterado? `make update-openapi-snapshot` rodado e snapshot commitado
- [ ] Migration Alembic nova? `alembic upgrade head` testado em DB limpo + downgrade funciona
- [ ] Mudou `config/report_layout.yaml`? Codegen rodado: `python3 dev/codegen_report_layout.py`
- [ ] Mudou `design-tokens/tokens.json`? Build rodado: `python3 design-tokens/build.py`
- [ ] Mudou `docs/DECISIONS.md`? Gates rodados: `python3 dev/check_adr_anchors.py && python3 dev/build_adr_toc.py --check && python3 dev/validate_adr_format.py`
- [ ] Feature visível ao usuário ou mudança operacional? `docs/CHANGELOG.md` atualizado

<!--
  Antes de mergear (responsabilidade de quem aprova):
  - [ ] Job "All checks green" verde
  - [ ] PR rebased em origin/main (botão "Update branch" se atrás)
  - [ ] Auto-merge habilitado se quiser merge automático ao verde
-->
