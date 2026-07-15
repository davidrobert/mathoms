---
id: ADR-338
type: adr
title: "Contrato role-keyed no view-model — nome do membro só em valores, nunca em chaves"
status: Proposto
date: "2026-07-15"
relates_to:
  - "[[ADR-176]]"
  - "[[ADR-166]]"
  - "[[ADR-143]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
  - area/report
---

# ADR-338 — Contrato role-keyed no view-model

> Cluster **CTO-02** (P0) da onda R2 do [[PLAN-dogfood-report-fix]]. Fecha o follow-up explícito
> deixado em [[ADR-176]] §Consequências. Co-desenho `codesign-review-wave` (senior-cto + IA +
> red-team, 2026-07-15).

## Contexto

O view-model deriva **chaves de dict do nome legal completo** do membro:
`patrimonio.investimentos_<nome>`, `goals.idade_<nome>_if`, `cenarios.salario_<nome>_clt_brl`,
`reserva_emergencia.composicao_liquida.investimentos_<nome>`
(`patrimonio_calculator.py:217`, `patrimonio_types.py:132-137`, `narrativas/context.py:59-65`,
`if_projector.py:180-188`). Três defeitos:

- **PII estrutural** — o nome legal fica na **chave**, não no valor; scrubbers que redigem
  valores não pegam a chave → vaza em log/snapshot/lineage.
- **Shape não-determinístico** — o key-set do JSON varia por workspace → golden/snapshot frágil,
  TS não-tipável.
- **Contrato TS morto** — `report-analysis.ts:72-73,129-130` declara `investimentos_titular/_conjuge`
  (short-name) que **nunca** casa com o slug de nome completo; nenhum componente lê (a UI usa
  `patrimonio.composicao`). Drift silencioso: leitura sempre `undefined`.

É o anti-padrão que [[ADR-143]] combate; [[ADR-176]] deixou os `_KEY_*_CONJUGE` residuais como
follow-up.

## Decisão

Chaves **role-keyed estáveis** — o nome do membro vive **só em VALORES**:

- `investimentos_titular` / `investimentos_conjuge` (não `investimentos_<nome>`)
- `idade_titular_if` / `idade_conjuge_if`
- `salario_conjuge_clt_brl`
- `reserva_emergencia.composicao_liquida.investimentos_titular/_conjuge`

O nome de exibição fica em um campo `nome` por membro (valor). Consumidores de narrativa
(`perfil_familia_narrator.py`, `summaries_narrator.py`, `charts_narrator.py`) leem via `ctx.key_*`
e seguem sozinhos. `report-analysis.ts` declara exatamente essas role-keys.

**Alavanca — teste de contrato view-model↔card** (irmão de `test_report_view_model_snapshot.py`,
fixture PII-zero): (1) roda o view-model com **dois** conjuntos de nomes → afirma **key-set
idêntico** (determinismo de shape); (2) walk de todas as chaves → **zero** chave contendo token de
nome de membro (gate estrutural de PII); (3) presença das role-keys obrigatórias; (4) keys
declaradas em `report-analysis.ts` ⊆ keys emitidas. Red-antes-de-green sobre o shape atual; vira
regressão permanente.

## Rationale

Identidade estável por papel (titular/cônjuge) é o contrato correto para um payload consumido por
TS tipado + goldens. Tira PII da estrutura (onde scrubbers não alcançam) e torna o shape
determinístico. Fecha [[ADR-176]] sem emendá-la: a 176 é Decidida/atômica (1 chave); carregar uma
decisão P0 de contrato+PII estouraria o cap de 150 linhas ([[ADR-182]]) — "ADR nova fecha
follow-up" é o padrão do vault.

## Alternativas consideradas

- **Emendar [[ADR-176]].** Rejeitada: 176 atômica/Decidida; violaria o cap de tamanho.
- **Manter as chaves + scrubber que redige a chave.** Rejeitada: scrubbing de chave é frágil e não
  resolve o shape não-determinístico nem o TS morto.
- **Só corrigir o TS (short-name → slug).** Rejeitada: cimentaria PII na chave + shape variável.

## Consequências

- Bump: `schema_e5` — CTO-02 é a **âncora** do bump único aditivo da onda R2.1 (role-keys entram
  no schema; `patternProperties` de idade/salário viram chaves fixas). Último a tocar o schema.
- Golden `dogfood_view_model.json` rebaselinado via `dev/golden_diff.py` — só **rename de chave**,
  zero delta de cents.
- **Prova** (não grep) de que role-keys **não** são projetadas no `exec_context` do distiller do
  parecer (whitelist de campos), garantindo `manifest` sem bump / eval.

## Critério de aceite (4 lentes)

- **Completude** — `rg`/walk zero-hit de chave com token de nome nos 3 blocos (patrimonio,
  reserva.composicao_liquida, goals/cenarios).
- **Corretude** — role-keys presentes com valores em cents idênticos ao pré-fix (Decimal exato).
- **Consistência** — 2 conjuntos de nomes → key-set idêntico; TS declara exatamente essas keys.
- **Precisão** — golden rebaselinado mostra só rename de chave, 0 delta de valor.
