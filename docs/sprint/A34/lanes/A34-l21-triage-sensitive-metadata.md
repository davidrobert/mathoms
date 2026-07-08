---
id: A34.l21
type: lane
title: "Triagem T1 de PRs/issues/CI logs sensíveis"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: triage-sensitive-metadata
adrs: ["[[ADR-316]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/seguranca
---

# A34.l21 — `triage-sensitive-metadata` (W4 · Metadados)

## Problema

A **camada 3** de contaminação — títulos e corpos de PRs/issues + logs de CI
— é **matematicamente inapagável por git**. O rewrite de histórico (W3,
[[A34.l18]]) reescreve blobs e mensagens de commit, mas **não alcança** os
metadados do GitHub: 855 PRs/issues são objetos do banco do GitHub, editáveis
apenas via API individualmente ou deletáveis. Um clone anônimo pós-flip não vê
esses metadados, mas a **interface web pública** os expõe integralmente.

O risco não está uniformemente distribuído nos 855 itens: concentra-se em
**~15 itens T1** que carregam PII direta ou IP sensível. Exemplos de padrões
(referidos por tipo, nunca por valor):

- **CPF em corpo de PR** — discussão de bug de dedup por CPF (ex.: placeholder
  `123.456.789-09`).
- **Endereço residencial** — PRs que citam o dado de imóvel real usado em teste
  (ex.: "Rua Exemplo, 100").
- **Nomes de terceiros** — membros reais da seed (`Titular`/`Cônjuge` como
  substituto sintético).
- **Valores de dogfood** — patrimônio nominal em títulos/corpos de PR de
  reconciliação (ex.: "R$ X").
- **Discussão competitiva** — issues/PRs do playbook `COMPETITIVE_PIERRE` com
  posicionamento contra concorrente.
- **Issue "Security schedule failure"** — issue automática de CI que pode
  vazar caminhos/diagnóstico.
- **Logs de CI de runs com diagnóstico de dogfood** — output de eval do parecer
  com valores reais em artefatos de run.

Sem triagem, esses ~15 itens permanecem indexáveis (Google, GitHub search)
após o flip — anulando o saneamento das camadas 1 e 2.

## Escopo

1. **Script de varredura read-only** (`_scratch/`, descartável): usa `gh search
   issues`/`gh search prs` + `gh api` para varrer títulos e corpos dos 855 itens
   pelos padrões de PII/IP conhecidos (regex de CPF, tokens de endereço, nomes de
   terceiros da seed, faixas de valor de dogfood, termos competitivos). Produz
   **lista priorizada** por tier (T1 alto risco · T2 médio · T3 residual aceito).
   A lista de saída mora em `_scratch/` (gitignored) — **nunca commitar** a lista
   com os valores reais.
2. **Tratar 100% dos T1**:
   - Editar título/corpo via `gh api -X PATCH /repos/davidrobert/mathoms/issues/<N>`
     substituindo o dado real por placeholder sintético, **OU**
   - Deletar o item quando não houver valor histórico e a edição for inviável
     (incl. a issue automática "Security schedule failure").
3. **Logs de CI**: para runs com diagnóstico de dogfood, reduzir retenção
   (`retention→0-1d`) **ou** deletar via `gh api -X DELETE /repos/davidrobert/mathoms/actions/runs/<id>`.
4. **Registrar o aceite de risco residual** (T3) em [[ADR-316]] — a triagem é
   mitigação parcial declarada, não eliminação total.

## Critério de aceite (verificável)

- Script de varredura roda e classifica os 855 itens em T1/T2/T3; contagem de
  T1 registrada no PR (~15 esperado).
- **100% dos T1 tratados**: cada item T1 da lista ou tem título+corpo sem o
  padrão de PII/IP (re-varredura pós-edição = zero hits nesse item), ou foi
  deletado (`gh api` retorna 404).
- Issue "Security schedule failure" editada ou deletada.
- Logs de CI de runs com dogfood: retenção reduzida ou run deletado —
  `gh api /repos/davidrobert/mathoms/actions/runs/<id>` não retorna artefato
  com valor real.
- Risco residual **T3 explicitamente aceito** em [[ADR-316]] (cláusula de
  metadados imutáveis) — sem essa aceitação textual, G4-min não fecha.
- **Nenhum artefato desta lane commita PII**: a lista priorizada fica em
  `_scratch/`; o PR (se houver) contém apenas o script de varredura mascarado
  e a nota de fechamento.

## Rollback

Operação **destrutiva e irreversível** sobre metadados do GitHub (edição de
corpo perde a versão original; delete é permanente). Não há rollback via git —
metadados não vivem no repo.

Mitigação (não rollback):
- **Antes** de editar/deletar, o script exporta um **dump local** dos itens T1
  (`gh api /repos/.../issues/<N> > _scratch/metadata_t1_backup/<N>.json`) para
  `_scratch/` (gitignored) — arqueologia local, jamais commitada.
- Edição preferível a delete quando o item tem valor histórico (preserva o fio
  da discussão com o dado redigido).
- Executar **na janela FREEZE** (W3→W8) para evitar que novos PRs reintroduzam
  padrões durante a triagem.

## Notas

- **Owner-gated**: depende do aceite de [[ADR-316]] (G0) antes de executar; roda
  **em paralelo com W3** ([[A34.l18]]), ambas adjacentes ao flip.
- **Toca infraestrutura GitHub, não código do repo** — não há CI a rodar sobre
  esta lane. O único artefato versionável (script de varredura mascarado) é
  docs/tooling em `_scratch/`; se algo for para `dev/`, **CI obrigatório**.
- **ROI cirúrgico**: ~15 itens T1 concentram quase todo o risco vs. 855 totais.
  A varredura ampla dos 855 (T2 completo) é *should* pós-flip (P2, janela A35),
  não bloqueia o marco de segurança.

## Referências

- Plano canônico: [[PLAN-public-release]] §W4 (G4-min).
- Aceite de risco de metadados: [[ADR-316]].
- Par de execução (irreversíveis, adjacentes ao flip): [[A34.l18]] (rewrite de
  histórico) · [[A34.l22]] (flip + verificação).
- Anexo de auditoria (achados mascarados por camada): [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md).
