---
name: unified-certify-review
description: >-
  Roda as três skills numa rodada só — `ledger-certify` (razão) + `pipeline-review`
  (dispara o run) + `report-review` (produto) — e produz UM entregável priorizado
  cujas linhas são roteadas para três registros. Use SEMPRE que o dono pedir "roda a
  rodada unificada", "certifica e revisa tudo de uma vez", "roda as três skills
  juntas", "faz um U novo", ou pedir as três em sequência sobre o mesmo workspace —
  mesmo sem a palavra "skill". Dispara run completo (~25–66 min, ~US$1–3 de API) e
  custa um painel de 5 lentes. NÃO use quando uma skill sozinha responde: se o pedido
  é só sobre o razão, é `ledger-certify`; só sobre a execução, `pipeline-review`; só
  sobre o relatório já existente, `report-review`. Recebe o workspace por email OU uuid.
---

# unified-certify-review

Procedimento do **loop principal** para executar a rodada unificada. **Esta skill é
fina de propósito** — ela não repete o procedimento, ela aponta para ele. A fonte é
uma só:

> **[`docs/reference/runbooks/unified_certify_review.md`](../../../docs/reference/runbooks/unified_certify_review.md)**

Canônica da composição: [[ADR-416]]. Disciplina de estado durável: [[ADR-343]].
Classe: [[ADR-302]].

## Por que a fonte é o runbook, e não este arquivo

O procedimento **re-executa a cada rodada e nunca é consumido**, e carrega um
§Débito de método append-only que cresce a cada execução — é a peça mais reusável
que a rodada produz. Duplicá-lo aqui criaria duas fontes de verdade sobre a mesma
condição de parada, que é exatamente o defeito que a rodada existe para caçar.

**Regra:** ao mudar o procedimento, edite o runbook. Este arquivo só muda se a
**fronteira** mudar (quando invocar, o que não fazer).

## O que a skill faz, em uma frase por fase

Leia o runbook para o detalhe; isto é o mapa, não o território.

| Fase | O quê |
|---|---|
| **F0** | Preflight — `dev/preflight_unified_review.py <ws>`; `FAIL` bloqueia |
| **F1** | Aloca o `U<n>`, cria o diretório cru, tira o snapshot de seleção E2 |
| **F2** | Grava `fired_at` **antes** de disparar; poll até terminal; coleta |
| **F3** | Cross-checks determinísticos → painel de 5 lentes → braço cego → céticos → crítico de completude |
| **F4** | Clusteriza; **gate de cobertura em matriz dimensão × registro** |
| **F5** | Três appends num commit só — a **única** fase que toca o git |
| **F6** | Débito de método do encadeamento |
| **F7** | Fecho e baseline |

## Fronteira vs as skills vizinhas

| Pedido | Skill |
|---|---|
| "o razão perdeu ou dobrou transação?" | [[ledger-certify]] |
| "roda o pipeline e analisa a execução" | [[pipeline-review]] |
| "revisa o relatório que já existe" | [[report-review]] |
| "cada documento virou artefato correto?" | [[parse-certify]] |
| **as três juntas, um entregável, três registros** | **esta** |

**Não use esta skill para economizar decisão.** Ela custa um run pago e um painel;
se a pergunta cabe numa vizinha, a vizinha é mais barata e mais precisa.

## O que ler antes de disparar

Duas seções do runbook, e nenhuma é opcional:

- **§2 Retomada** — se `fired_at` está preenchido, o run **já foi disparado**, mesmo
  com `run_id` nulo. Nunca dispare de novo; adote o run pelo `started_at`.
- **§10 Débito de método** — os furos que as execuções anteriores acharam em si
  mesmas. Os dois que mais custam: a tabela de condicionamento tem de ser chaveada
  nos blocos do **consumidor**, não nos baldes do produtor; e particionar por lente
  cria costura, então a varredura *"nenhuma lente reivindicou isto"* sobre a
  superfície renderizada é obrigatória antes de fechar a matriz.

## Critério de aceite

O do runbook (§5 F7), sem duplicação aqui. Em resumo: run `completed` — **nunca**
`partial_failure` — · matriz sem célula silenciosa · toda linha com registro de
destino de cardinalidade 1 · taxa de `REFUTADO` > 0 · ≥1 claim pivotal fechado por
medição · zero PII nas três seções git · débito de método registrado.
