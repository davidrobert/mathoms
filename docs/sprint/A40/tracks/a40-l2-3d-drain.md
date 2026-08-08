---
id: TRACK-a40-l2-3d-drain
type: track
title: "Track A40.l2 PR3d — o drain: re-ancorar os overrides condenados antes do enforce"
lane: "[[A40.l2]]"
sprint: A40
plan: PLAN-report-trust
status: ready
created_at: "2026-08-08"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a40
  - status/ready
  - priority/p0
  - area/backend
  - area/pipeline
---

# Track A40.l2 PR3d — o drain

> **Destravado em 2026-08-07** pelo merge do PR3b ([#1276](https://github.com/davidrobert/mathoms/pull/1276),
> `b3b8a74b`), que era sua única dependência. **É da onda desta sprint** — o §Gate de saída da
> [[A40.l2]] faz o contador de 2 re-runs consecutivos só iniciar quando a lane estiver
> terminal, e o 3d é pré-condição do 3e.

**Não começa por código.** Há uma decisão de desenho aberta (§1) que muda o produto; fechá-la
é o primeiro passo, e é co-design, não escolha do implementador.

## 1. 🔴 Primeiro passo: fechar de onde vêm os candidatos

A [[A40.l2]] diz *"o pipeline **emite**, o backend **decide**"* e **não diz por onde os
candidatos chegam ao drain**. Duas leituras, produtos diferentes:

| | **(a) o stage chama o drain** | **(b) o operador dispara, e o drain re-deriva** |
|---|---|---|
| candidatos | do próprio run, como o gate do 3b já faz | re-executa o colapsador (caminho `_rederive` do harness) |
| a favor | zero segunda derivação · re-ancora *enquanto as duas rows existem* (requisito temporal da lane) · reusa a fiação do 3b | preserva o **gesto humano** — a [[ADR-364]] §2 chama a re-ancoragem de *"mutar dado do usuário por heurística"* |
| contra | **automação destrutiva silenciosa** — muta categorização do usuário a cada run | **segunda derivação do colapsador**, a classe `keep_split` que esta lane pagou **2×** |

**Gatilho duplo obrigatório:** `senior-cto` (boundary + composition root) **e**
`financial-planner` (é mutação de dado categorizado pelo usuário). Em paralelo, 1 rodada de
objeção, `senior-cto` fecha se persistir. Precedente de que a rodada se paga: o co-design do
3c1 derrubou dois pontos do payload que já estavam cravados.

## 2. Restrições duras — verificadas no código, não presumidas

Todas em `backend/app/services/internal_ops/backfill_override_identity.py` (298 linhas):

- **`_fresh_legacy` NÃO pode ser reusado.** Ele revalida `natural_key_hash is not None ⇒
  return None`, e o override de colapso tem âncora **não-nula** por definição (é o hash da row
  removida). Reuso ⇒ **"0 aplicados" com a suíte inteira verde**. Precisa de revalidador irmão
  que confira `natural_key_hash == <esperado>`.
- **`_preflight` recusa com `cutover_already_active`** quando `override_natural_key_v2_enabled`
  está ligada — que é exatamente o estado desta lane. Entry point irmão, com preflight próprio.
- **`_apply` chama `_quarantine` + `_soft_delete_losers`.** Reuso integral **apagaria a
  categorização que o gate protege** — aprovação por destruição, contra a [[ADR-364]] §2.
  **Apply só do caso 1→1**; colisão e ambiguidade ficam **report-only**.

## 3. ⚠️ O apply path não tem dado real para exercitar

O PR3b mediu no dogfood: **0 overrides ancorados em row de candidato de colapso**
(4 `casou_corpus_fora_de_candidato`, 1 `casou_nada`, 0 em candidato). As travas do drain têm
de vir de **fixture sintética**, e o PR tem de **dizer isso** — senão alguém lê "verde no
dogfood" como prova de que o drain funciona. Mesma armadilha que a escapatória de absolvição
do 3b, já declarada uma vez; repeti-la seria a terceira instância nesta lane.

**Re-meça antes de fechar o desenho:** `python3 dev/probe_collapse_adjudication.py <ws>`.
"Vazio" é propriedade do corpus **e do tempo** ([[ADR-364]] §5) e override nasce
continuamente. O probe recusa emitir veredito com corpus/overrides vazios (`INDETERMINADO`,
exit 2) — **não contorne o guard**.

## Aceite

- **Trava anti-destruição, medida:** `COUNT(*) WHERE orphaned_at IS NOT NULL` e
  `WHERE deleted_at IS NOT NULL` em `transaction_overrides` **iguais** antes e depois. Se
  subir → abortar e restaurar.
- **Prova por mutação** em cada guarda: reusar `_fresh_legacy` deixa um teste vermelho;
  reusar `_preflight` idem; aplicar caso ≠1→1 idem. Guarda sem teste próprio é guarda que o
  próximo refactor remove.
- Fixture sintética cobrindo 1→1 (aplica), colisão N→1 (report-only) e âncora indecidível
  (report-only), **com a declaração de que o dogfood exercita zero delas**.
- Nenhuma resposta de API vaza hash cru nem descrição de transação.
- Resultado do probe **no corpo do PR**, mesmo que confirme o esperado.

## Não é escopo

- **Ligar o enforce** (3e) — exige os 9 eixos do §Critério de saída, incluindo **ensaio de
  rollback medido**; undo nunca executado é premissa, não propriedade.
- O **custo do gate por run**, aberto e já pagando em produção — é item próprio da lane
  (§"predicado FECHADO no PR3b; sobra o custo"), a medir antes do 3e.

## Referências

- Lane: [[A40.l2]] §3d · §"Restrições duras do 3d" · §D5
- ADRs: [[ADR-364]] (§2 quitação por re-ancoragem, §5 gate todo run) · [[ADR-282]] (a máquina
  que já existe: `ReanchorPlan`, `CollisionPlan`, TOCTOU plan→apply, `orphaned_at IS NULL`)
- Instrumento: `dev/probe_collapse_adjudication.py`
