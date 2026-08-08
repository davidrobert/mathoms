---
id: ADR-370
type: adr
title: "Inventário estrutural do relatório: a fixture canônica é superfície completa e card que sai exige linha apagada à mão"
status: Decidido
phase: "A40"
date: "2026-08-08"
relates_to:
  - "[[ADR-141]]"
  - "[[ADR-167]]"
  - "[[ADR-076]]"
  - "[[ADR-210]]"
tags:
  - type/adr
  - status/decidido
  - area/frontend
  - area/testing
  - phase/a40
---

## Contexto

O gate visual do relatório compara **pixels**. Quando um card desaparece, a
baseline apenas encolhe, e o diff de um PNG não é revisável em PR — a saída
natural do revisor é rebaselinar.

Aconteceu duas vezes, medido:

- **Card "Alocação · Atual vs Alvo"**: a A12 PR7 (`d25bfab1`, #906) o fez
  consumir `goals.alocacao_alvo.derived` e ocultar-se sem o bloco (intencional,
  [[ADR-141]] §Emenda). A fixture `medium` nunca teve a chave `goals`. A
  baseline da S3 caiu de `976x1457` para `976x929` e o #1290 **congelou a
  perda**. ~3 meses invisível.
- **`report.print.pdf.png`**: congelou um error boundary do React como baseline
  por 3,5 meses (desde 2026-04-27). O gate comparava crash com crash.

A causa comum não é falta de atenção: é que **a única prova de que um componente
existe era um binário que ninguém consegue ler em review**.

## Decisão

**1.** Um gate estrutural (`frontend/tests/e2e/reports/report-inventory.@critical.spec.ts`)
compara o conjunto de cards renderizados por seção contra um inventário
commitado em texto (`report-inventory.expected.json`). Ele falha **nomeando** o
card ausente. O inventário é varrido da estrutura do DOM
(`section[class*="card-variant-"]` + `h3` filho direto), não de uma lista de
títulos: card novo entra sozinho.

**2. Assimetria de regeneração.** `MATHOMS_UPDATE_INVENTORY=1` **só acrescenta**;
nunca remove. Card novo é regenerável; **card que sai exige apagar a linha à
mão**, e a linha apagada aparece no diff do PR. Sem isso o arquivo vira a
baseline PNG em texto — um comando que lava a perda de cobertura. O modo update
continua reprovando remoções, para não dar verde local e vermelho no CI.

**3. A fixture `medium` é superfície completa.** *"A fixture não tem o dado"*
**não** é justificativa aceitável para card ausente — é precisamente o defeito
do #906. Ausência legítima é remoção de produto, e sai como linha apagada com
justificativa no PR.

**4. O gate roda sem label, em todo PR de frontend.** Entra no step
`Report render gate` de `frontend-checks`, que está em `all-green.needs`. Esse
step perde o `if: needs.changes.outputs.report` — o filtro `report` é allowlist
positiva e falha aberta: medido em 400 commits de `main`, 8 de 57 commits de
frontend (14%) tocam a closure do relatório sem acioná-lo, incluindo
`lib/goalPremissas.ts`. Pôr o gate atrás de label repetiria o mecanismo que
manteve o PDF quebrado 3,5 meses ([[ADR-210]] §camada 1 mantém os jobs de pixel
opt-in por custo; isso não se estende a gate estrutural).

## Consequências

- Card que some falha por **nome**, em texto, em todo PR de frontend.
- O inventário passa a ser o artefato de atribuição de rebaseline: se ele não
  mudou, uma mudança de pixel é estilo/layout, não conteúdo.
- Custo medido: ~+15s no step; ~1,6 min nos ~90 runs/mês de frontend que hoje
  pulam estes steps.
- Quatro seções (`V0`, `S_parecer`, `plano_de_acao`, `APP_E`) entram com lista
  vazia: nelas o gate assere apenas que a **seção** ainda renderiza.

## Descoberta registrada: `cards[].enabled` do layout é decorativo

`config/report_layout.yaml` declara `cards[].id` + `enabled` e o cabeçalho do
arquivo afirma controlar "quais seções, cards e charts aparecem no relatório".
**Para o relatório inteiro, isso não é verdade hoje.** `MIGRATED_SECTIONS`
([`MigratedSection.tsx:26`](../../frontend/src/components/report/MigratedSection.tsx))
contém as 18 seções, e `ReportShell` só repassa `section.cards` para o
`ReportSectionStub` — o ramo não-migrado, hoje inalcançável. Nenhum componente
referencia id de card do layout (`rg` por `proventos_yield`,
`hero_gap_protecao`, `contrafluxo`… não retorna nada em `frontend/src`).

Consequência: pôr `alocacao_atual_vs_alvo: enabled: false` não removeria o card.
Por isso o gate v1 é chaveado por **título renderizado**, não por id do layout:
assertar contra ids seria assertar contra config que não governa nada, e exigiria
inventar ~10 mapeamentos ambíguos.

### Deferimento — tornar o layout load-bearing (2026-08-08)

**Dono:** próxima lane que tocar a estrutura de cards do relatório.
**Escopo:** `cardId?: string` em `ReportCard` emitindo `data-card-id`, aplicado
aos `ReportCard` de topo dos cards declarados (~36 sítios, não os 76 call sites
— o resto são variantes de loading/empty e sub-cards), com obrigatoriedade
enforçada por registry ou lint, nunca por convenção. Feito isso, o inventário
troca a chave de título por id e o acoplamento com copy de produto some.
**Condição de retomada:** quando as lanes concorrentes em
`frontend/src/components/report/**` drenarem — hoje um diff cross-cutting em ~30
arquivos é ímã de conflito.
**Por que não agora:** o valor marginal sobre o gate v1 é a robustez a mudança
de copy; o custo é o conflito. Não justifica bloquear o fechamento da classe.
