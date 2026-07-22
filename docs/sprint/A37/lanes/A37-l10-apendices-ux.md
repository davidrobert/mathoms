---
id: A37.l10
type: lane
title: "Apêndices: stress card com coluna base vazia + tabela de premissas 10× indisponível"
sprint: A37
status: shipped
priority: P2
branch_slug: a37-l10-apendices-ux
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/shipped
  - priority/p2
  - area/frontend
---

# A37.l10 — `apendices-ux` (PD-09 + PD-04)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **PD-09 — StressScenarioCard:** `ApendicesSections.tsx:250` casta
   `data.goals` como `{ if_prazo_anos?, if_ano? }`, mas o payload tem
   `prazo_anos_realista`/`ano_if` e **nenhum mapper existe no repo** → coluna
   do cenário base renderiza "—" com o dado presente. Com delta de aporte
   negativo (cenário reduz capacidade), o parágrafo vira "Leitura: . Reforce…"
   (`StressScenarioCard.tsx:142-154` só emite fragmentos quando `> 0`) e o
   copy nunca cobre redução de aporte.
2. **PD-04 — PremissasEconomicasCard:** com todas as classes
   `status="indisponivel"` (caso real do dogfood), o card emite 10 linhas
   idênticas "Premissa indisponível…" (`PremissasEconomicasCard.tsx:127-142`)
   + rodapé com jargão interno ("Override por workspace… fiduciária"). O sinal
   de degradação já existe no banner de qualidade de dados — a tabela repetida
   é redundante e parece quebrada.

## Escopo

- Mapear `prazo_anos_realista`→`if_prazo_anos` e `ano_if`→`if_ano` no ponto de
  montagem das props (ou ajustar o tipo do card); guard do parágrafo "Leitura:"
  (não emitir sem fragmento); copy para delta negativo de aporte.
- Premissas: `classes.every(indisponivel)` → empty-state único e digno;
  revisar rodapé sob COPY_GUIDELINES.

## Critério de aceite

- Unit: payload real → coluna base exibe prazo/ano; "Leitura:" nunca renderiza
  vazio; snapshot com delta negativo tem frase própria.
- Unit: todas indisponíveis → 1 empty-state, zero linhas repetidas.
- Testes de regressão dos dois comportamentos atuais antes do fix.

## Risco

Baixo — apresentação; consistência S3↔Apêndice C verificada por snapshot.
