---
id: MOC-sprint-a36
type: moc
title: "Sprint A36 — Follow-up da auditoria r4: itens de mérito sem rastreio"
aliases: ["A36", "Sprint A36"]
sprint_status: candidate
date: "2026-07-09"
theme: "audit-followup"
---

# Sprint A36 — Follow-up da auditoria r4

> **Status:** `candidate` — backlog de remediação **não-iniciado**, priorizável
> pelo owner. São os cinco achados de **mérito** da auditoria externa
> `repo-audit` r4 (2026-07-09) que **não tinham lane/plano** no repo. Os achados
> **gating/críticos** já vivem em [[A34]] (W3 rewrite de história), [[ADR-228]]
> (W4-T01 backup + drill) e [[ADR-085]] (materializer) — esta sprint **não** os
> duplica.
>
> **Origem:** auditoria de repositório r4 @ `c004742b` (confidencial, fora do
> repo). Cada lane referencia o ID do achado (ARQ-/SEC-/DAT-/QUAL-) e traz
> âncoras `arquivo:linha` do próprio código — nenhum dado sensível. Os IDs de
> achado são **rótulos de proveniência não-acionáveis** (o relatório é externo);
> a evidência que carrega peso é a âncora `arquivo:linha`, verificável in-repo
> sem acesso ao confidencial.

> **Revisão 2026-07-10 (painel de 6 especialistas — cto, sre, data, financial,
> pm, ia).** As âncoras `arquivo:linha` das 5 lanes foram **todas verificadas
> contra o código real** — são verdadeiras. Mas a revisão desfez o "tudo P1"
> original e corrigiu dois erros de mérito que só apareceram ao ler o código:
>
> 1. **L3 protegia o alvo errado.** Dos 14 checks CV, só **CV1/CV9/CV10** têm
>    `severity="error"`; o gate proposto dispara em `errors_count` (= só error).
>    Logo, como escrito, L3 **pausaria em narrativa/gráfico ausente (CV9/CV10,
>    cosmético)** e **não pausaria** em CV2/CV3/CV6/CV7 — justamente os "números
>    que não fecham". O fix load-bearing inclui **re-tagear CV2/CV3/CV6/CV7 de
>    `warning`→`error`** (ou um tier `conservation` próprio), não só o
>    encanamento de `validation.valid`. Detalhe na [[A36.l3]].
> 2. **L5/QUAL-02 estava mal descrito.** `baseline_validator` é consumido **só**
>    pela reconciliação E3 (extrato×IRPF) — **não** pela construção do patrimônio
>    líquido (E1.5/E1.5c não o importam). O `except` largo **não dropa conta do
>    patrimônio**; ele **cega o alarme de reconciliação** (o `BaselineDiffWarning`
>    não dispara). Severidade média, não "perda de net worth". Detalhe na [[A36.l5]].

## Por que esta sprint existe

A r4 observou que a org **captura os grandes achados conhecidos** (PII em
histórico, backup, BYOK) em sprints/ADRs, mas **os de mérito médio escapam do
backlog** (achado MAT-03). Estas cinco lanes fecham essa lacuna: são baratas
(~4-5 dias somados), sem dependência externa, e nenhuma bloqueia a nota gated —
são **dívida de qualidade/segurança que impede a nota de subir de "sólido" para
"maduro"**.

**A36 é um contêiner de proveniência, não uma sprint coesa.** As 5 lanes não
têm dependência compartilhada — não se movem juntas. O valor do wrapper é
tornar a dívida da r4 **visível e priorizável como unidade** (resposta ao
MAT-03), não executá-la em bloco. O owner promove o subconjunto de alto valor;
o resto fica como P2 "later" com a tag de proveniência.

## Lanes (repriorizadas — painel 2026-07-10, método WSJF)

O "tudo P1" original foi desfeito. Proveniência (mesma auditoria) não é eixo de
prioridade. Tiers por custo-de-atraso ÷ esforço:

| Lane | Achado | Tema | Tier | Esforço | Notas da revisão |
|---|---|---|---|---|---|
| [[A36.l3]] `e7-conservation-gate` | DAT-01 | Invariante de conservação pausa o run | **P0** | M | Client-facing; **re-tag CV2/CV3/CV6/CV7 warning→error** é parte do fix |
| [[A36.l1]] `boundary-gate` (Parte A) | ARQ-02 | Gate de fronteira + allowlist no CI | **P1** | S (~1h) | Fecha buraco de 4 auditorias; exige ADR Proposto |
| [[A36.l5]] QUAL-02 (baseline parse) | QUAL-02 | Saldo malformado escapa da reconciliação E3 | **P1** | S | `InvalidOperation` ⊄ `ValueError` — ver lane; log WARNING + ReviewReason |
| [[A36.l1]] `invert-sinks` (Parte B) | ARQ-01 | Inverter 3 escritas de domínio via port | **P2** | M | Raiz já mitigada ([[ADR-256]]); follow-up rastreado |
| [[A36.l5]] QUAL-01 (vault except) | QUAL-01 | Estreitar `except` cripto | **P2** | S | Baixa freq; toca feature BYOK paga (surfaçar ao usuário) |
| [[A36.l4]] `go-toolchain-cve-bump` | SEC-07 | **Gate `govulncheck` no CI** + toolchain floor | **P2** | S | CVE real (GO-2026-5856); CI provável já patcheado — entregável = o gate |
| [[A36.l2]] `stderr-pii-redaction` | SEC-09 | Spike confirma PII + backstop Go | **P2** | S | `candidate` não confirmado; defesa real = separar streams no Go |

## Ordem sugerida (valor-first — corrige a ordem original)

A ordem original (`l4→l5→l3→l2→l1`, "l1 por último") otimizava
esforço/isolamento, começando pelo item de **menor** valor. A ordem correta é
por valor:

**Rodar agora (subconjunto de alto valor):**
[[A36.l3]] (P0) → [[A36.l1]] Parte A (P1, ~1h, paralelo) → [[A36.l5]] QUAL-02
(P1) → [[A36.l2]] spike de confirmação (30min).

**Follow-up P2 (permanecem em A36 com tag de proveniência):**
[[A36.l5]] QUAL-01 → [[A36.l4]] gate `govulncheck` → [[A36.l1]] Parte B (inversão).

- [[A36.l3]] é o de maior **valor de correção** e client-facing (invariante de
  conservação violada chega ao cliente sem flag no exato gate dogfood→beta) —
  mas só entrega proteção real se a re-tag de severidade dos CV numéricos entrar
  junto. É o primeiro.
- [[A36.l1]] Parte A (gate) é ~1h e fecha causa-raiz que sobreviveu 4 auditorias
  — deveria ser dos primeiros commits, não o último. A inversão dos 3 sinks
  (Parte B) é o refactor M, follow-up.
- [[A36.l1]] Parte A + [[A36.l4]] gate `govulncheck` são os únicos itens com
  **valor de processo durável** — pegam a *classe* de achado por CI, não pela
  próxima auditoria externa (a resposta operacional ao MAT-03).

## Guarda pré-execução (entry-gates)

Fazer **antes de tocar código** — cada um decide *se/como* a lane prossegue.
Correções em *tempo de implementação* (não são entry-gate) vivem nos
`## Critérios de aceite` da lane, não aqui — para não duplicar/divergir.

| Lane | Entry-gate (antes do PR de implementação) | Remove o risco |
|---|---|---|
| [[A36.l3]] | Script **read-only** que mede a taxa-base retroativa: quantos runs de dogfood pausariam com CV2/CV3/CV6/CV7 promovidos a `error`. Só flipar a severidade se a taxa for tolerável. | Over-firing (único risco **alto** do sprint) |
| [[A36.l1]] | ADR `Proposto` mergeada (§ADR necessária) — política CLAUDE.md, não opcional. | Escopo arquitetural sem gate de sanidade |
| [[A36.l4]] | Passo-0: confirmar o patch Go efetivo do CI (`go version` no job) antes de assumir vuln aberta. **Sequenciar após [[A36.l1]]** — ambos tocam `.github/workflows/ci.yml`. | Esforço em near-no-op + conflito de merge em `ci.yml` |
| [[A36.l2]] | Spike de confirmação (~30min) decide o tier antes de qualquer fix. | Fix comprometido a vetor não-confirmado |

**Correções em tempo de implementação (nos Critérios de aceite, não são
entry-gate):** `InvalidOperation ⊄ ValueError` ([[A36.l5]] QUAL-02), preservar
hooks de budget/telemetria [[ADR-173]] + session [[ADR-256]] ([[A36.l1]] Parte
B), auditar call-sites de `vault.decrypt` ([[A36.l5]] QUAL-01).

## ADR necessária

- [[A36.l1]] abre **ADR `Proposto`** (política CLAUDE.md — escopo arquitetural):
  mecanismo de allowlist do gate + critério reutilizável **"cabeia o boundary →
  allowlist; cruza de dentro do domínio → inverte"** + decisão sobre
  `parecer_orchestrator` (recomendação do painel: **inverter**, mesma família
  dos hooks `llm_*` no `WorkspaceContext`). É tightening de [[ADR-089]]. Flippa
  `Decidido` no PR de Parte B.
- [[A36.l3]] **emenda [[ADR-272]]** (mecanismo de pausa `needs_review`) — não
  abre ADR nova; a política de pausa já é regida lá.

## Fora de escopo (já rastreado)

- **SEC-01** (PII no histórico) → [[A34.l18]]–[[A34.l20]] (W3), [[ADR-315]].
- **REL-01** (backup + drill) → [[ADR-228]] W4-T01 + gate G2.
- **SEC-03** (BYOK plaintext) → [[ADR-085]] (decisão registrada, execução pendente).
- **DAT-03** (schema `warn`→`strict`) → PLATFORM_REVIEW W6-T01.
- **TEST-03** (paridade Go↔Py) → [[PLAN-go-shell]] F2 cutover ([[ADR-323]]).

## Follow-ups descobertos na execução (rever no fecho do sprint)

> **Ledger vivo.** Toda lane que descobrir um item fora do próprio escopo
> registra aqui (origem + descrição + tier), em vez de silenciar ou inchar a
> lane. **No fecho do A36**, revisar cada linha: promover a lane/backlog próprio,
> resolver inline se trivial, ou descartar com justificativa. Nenhum some sem
> decisão. `aberto` = pendente de decisão; `feito`/`descartado`/`promovido` = fechado.

| # | Origem | Follow-up | Tier | Estado |
|---|---|---|---|---|
| FU-1 | [[A36.l3]] | **Calibrar CV10** (feito) + render-gate dedicado. CV10 passou a checar completude só dos gráficos obrigatórios — opcionais legitimamente vazios (`impostos_pj`/`wise_fiscal_flags`) não são mais `warning` falso-positivo. CV9/CV10 já estão fora do gate de pausa (só conservação pausa), então o "render-gate" está funcionalmente atendido; formalizar uma estrutura própria fica opcional. | P2 | feito (calibração) |
| FU-2 | [[A36.l3]] | **Backfill retroativo.** Script read-only que reconstrói os 14 checks sobre o E5 persistido (`analyze_finances/analise_financeira`) e lista runs `completed` que teriam pausado — o E7 nunca persistiu verdict, então é reconstrução, não leitura. Zero migration. | P2 | aberto |
| FU-3 | [[A36.l3]] | **CV4 (taxa de poupança) falha em 25/28.** Advisory, fora do gate — provável drift de fórmula ou de campo. Investigar à parte; se for bug, entra como fix próprio. | P3 | aberto |
| FU-4 | forma | **`SPRINT_CURRENT` fallback.** Elege A36 como "corrente" via `max(dir)` quando nenhuma sprint é `current` — limitação de `dev/_sprint_current_renderer.py`. Follow-up: filtrar `sprint_status ∉ {done, paused, cancelled}` antes de eleger o max. | P3 | aberto |
| FU-5 | [[A36.l5]] | **Baseline parse → `needs_review`.** QUAL-02 tornou o drop observável (log WARNING), mas `from_baseline_dict` retorna `list[BaselineAccountSaldo]` — sem canal para emitir `ReviewReason`. Escalar a conta dropada para `needs_review` no boundary do E1.5 (via `ReviewReasonCode` novo, ex.: `domain_baseline_parse_failed`) exige threading no retorno + callers; gated por medição (ver se ocorre em prod). | P2 | aberto |

_(Adicione novas linhas conforme as lanes rodam — L1a, L5, L4, L2 tendem a
gerar itens de allowlist, calibração e cobertura.)_
