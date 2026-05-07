# Report a11y gate — prova empírica (lane `report-a11y-finalize` item 6)

> Documento curto. **Não é um runbook.** É a evidência arquivada de que
> os gates entregues em itens 1+2+4 da lane realmente bloqueiam regressões
> reais — pré-requisito do item 6 do
> [track](agent_prompts/track_report_a11y_finalize.md#gate-de-saída-commit-final-em-main-ci-verde).

## Hipótese

Se um colaborador (humano ou agente) introduzir um `<button>` sem
accessible name dentro do escopo do relatório (`[data-report-scope]`),
o CI **deve falhar antes do merge** em pelo menos um dos gates ativos:

- `frontend/tests/e2e/reports/a11y.@critical.spec.ts` (axe-core, gate
  `critical+serious` — D1).
- `frontend/tests/e2e/reports/tab-order.@critical.spec.ts` (asserções
  escopadas a `[data-report-scope]`).
- `frontend-lighthouse` job (Lighthouse CI, threshold a11y ≥ 0.95 — D2).

## Procedimento

Em vez de abrir um PR descartável remoto (que poluiria o histórico do
GitHub), a regressão foi exercitada **localmente** no worktree
`agent/report-a11y-finalize/20260425-1200`, na rota `/reports/[id]`
via mock helper, em 25/04/2026.

Patch temporário aplicado em
[`frontend/src/components/report/sections/S10SinteseSection.tsx`](../frontend/src/components/report/sections/S10SinteseSection.tsx):

```tsx
return (
  <ReportSection id="S10" title="Síntese Estratégica — Tarefas e Score">
    {/* TEMPORARY REGRESSION — gate empírico item 6 — REMOVE ME */}
    <button type="button" className="md:col-span-2">
      <svg width="16" height="16" viewBox="0 0 16 16">
        <circle cx="8" cy="8" r="4" />
      </svg>
    </button>
    <SectionSummary narrativas={narrativas} sectionId="S10" />
    ...
```

`<button>` com `<svg>` e sem texto, sem `aria-label`, sem
`aria-labelledby`. Accessible name = vazio.

## Resultado observado (25/04/2026, chromium local)

### axe-core (a11y.@critical.spec.ts)

```
2 failed
  · [chromium] › Report a11y @critical › relatório completo (modo
    estratégico) sem violações critical+serious
  · [chromium] › Report a11y @critical › seção S10 sem violações
    critical+serious

Error: axe-core encontrou 1 violação(ões) em [data-report-scope]:
  · [critical] button-name: Ensure buttons have discernible text
    help: https://dequeuniversity.com/rules/axe/4.11/button-name?application=playwright
    - .gap-6.md\:grid-cols-2.grid > button[type="button"]
```

✅ Gate dispara em **critical**, conforme esperado.

### tab-order (tab-order.@critical.spec.ts)

```
1 failed
  · [chromium] › Report tab-order @critical › nenhum focável dentro de
    [data-report-scope] sem accessible name
3 passed
```

✅ Gate dispara via fallback comportamental (mesmo que axe não corra).

### Reverter + re-rodar

Após `git checkout` do arquivo:

```
28 passed (39.9s)
```

✅ Tudo verde — confirma que os 3 falhas vieram exclusivamente da
regressão.

## Conclusão

Os gates do item 1, 2 e 4 da lane são **empiricamente eficazes** contra
o cenário-alvo descrito no track. Itens 3 (snapshots por seção) e 5
(checklist WCAG operacional) continuam abertos — não foram exercitados
neste experimento porque snapshots por seção não estão entregues e
checklist é doc.

Esta evidência fica arquivada aqui (não em commit message, que rota com
o tempo) para qualquer pessoa que queira reproduzir o experimento ou
auditar a lane.
