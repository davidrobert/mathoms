# Orquestrador — Sprint A33 (autonomia total: zero ações do owner)

> Prompt operacional para executar a [[MOC-sprint-a33]] de ponta a ponta.
> **Uso:** cole o bloco abaixo no início de uma sessão nova (ou invoque
> este arquivo). Fonte de verdade do escopo: [`docs/sprint/A33/_README.md`](../sprint/A33/_README.md)
> + lanes em [`docs/sprint/A33/lanes/`](../sprint/A33/lanes/) — este
> prompt orquestra, não duplica.
>
> Sprint aberta em 2026-07-07 (PR #822) com revisão de kickoff
> `product-manager` + `information-architect` + `data-engineer` já
> incorporada (l3 cortada; l1/l4 re-escopadas; gates de l6/l9
> explícitos). **Não re-invoque os mesmos especialistas para carimbar o
> mesmo escopo** — só para decisão nova dentro de uma lane.

---

```
# Orquestração — Sprint A33 (autonomous-debt)

Atue como orquestrador com o perfil `senior-cto`
(`.claude/agents/senior-cto.md`), executando a Sprint A33 até o
fechamento. Regras de CLAUDE.md valem integralmente (branch naming,
PR-flow squash, gates locais, cadência de commit, anti-loop).

## Missão

Shippar as 8 lanes de `docs/sprint/A33/` — todo o trabalho é executável
SEM nenhuma ação do owner. Essa restrição é o contrato da sprint (KR1):
se qualquer lane revelar gate escondido de owner (token, key, assinatura,
decisão, tráfego de dogfood), flipe a lane para `blocked` com nota
nomeando o gate NO MESMO DIA e siga para a próxima — descobrir gate não
é falha; esperar em silêncio é.

## Protocolo de início (antes de qualquer edit)

1. `git fetch origin && git status` + pickup checks de CLAUDE.md
   (`git worktree list` + branches `agent/*` recentes). Lane com slug em
   uso (worktree OU branch <24h) está tomada — não duplique.
2. Leia `docs/sprint/A33/_README.md` e as lanes que vai atacar. O
   frontmatter das lanes é a fonte de verdade de status/prioridade.
3. Cheque o estado da A32 (`docs/sprint/A32/_README.md`):
   - A32 `done` → flip A33 `candidate → current` (edite os dois
     `_README.md` ANTES de `python3 dev/build_doc_index.py --inline`;
     commit docs-only separado).
   - A32 ainda `current` → NÃO flipe a A33. Execute as lanes mesmo
     assim (precedente A27: Must executado durante a janela A26) e
     anuncie isso no primeiro PR. A onda A não colide com os arquivos
     da A32 (verificado no kickoff); l6/l9 têm gates próprios.
4. **Passo-0 de reconciliação POR LANE (obrigatório, lição do kickoff):**
   o escopo herdou planos de mai/2026 e o drift já foi pego 3× (e15 já
   era Decimal; W2 inteira já havia shipado; proventos já tinham
   schema/prompt/classifier). Antes de estimar qualquer lane:
   `git log --oneline --since=2026-07-07 -- <paths do escopo>` + grep
   dirigido. Item já entregue → risque do escopo e registre no PR.

## Ordem de execução

**Onda A (paralela, 2 agentes):**
- `A33.l1` (P0, branch `a33-l1-adr090-llm-boundary`) — ADR-090 no
  `e2_llm_extract` + gate float no pacote LLM + rebaseline offenders
  stale. Item 4 da lane (float deliberado do parecer) exige decisão
  co-design com `data-engineer` — decisão, não código.
- `A33.l2` (P1, branch `a33-l2-a17l3-financeiro-pf`) — fechar A17.l3
  P3-P5. Co-design ANTES de codar: `financial-planner` (PTAX/ganho
  cambial/CBE, P5) + `product-designer` (UI S4, P4) em paralelo.

**Onda B (dispare conforme capacidade, l4 pode antecipar):**
- `A33.l4` (P1) — integração proventos→S3 (lane pequena; schema/prompt/
  classifier prontos). Fecha A17 → `done` junto com l2 (flip do
  `_README.md` da A17 + SPRINTS-active no PR final).
- `A33.l5` (P2) — nightly drift extractLLM (ADR-307 F2). Aceite exige
  resultado do drift-check persistido consultável, não só linha de
  custo; custo declarado na janela mês-calendário do cap ADR-173.
- `A33.l6` (P2) — retenção de artifacts. **GATE DURO: só abre após
  A32.l5 mergeada E ADR-311 `Decidido`.** Predicado de prune (versão
  corrente + tombstone sobrevivem) é parte do aceite. Ordem dos PRs:
  migration → write-path → backfill → prune dry-run → flip efetivo.
  Co-design `data-engineer` na calibração da política.

**Onda C (cauda):**
- `A33.l7` (P2) — OTLP `mathoms.llm.*` (labels {prompt_name,
  prompt_version}); persistência SQL já existe (A20.l12/l13).
- `A33.l8` (P2) — catálogo via `InstitutionCatalogProvider` (protocol no
  consumer — pipeline não importa backend) + RFB YAML + runbook anual
  (forma do runbook: co-design `information-architect`).
- `A33.l9` (P2) — services taxonomy (ADR-285). **GATE DURO: ≤1 PR ativo
  tocando `backend/app/services/`** — verifique com
  `gh pr list --search "backend/app/services"` e registre a checagem no
  corpo do PR. Flip ADR-285 → `Decidido` no 1º PR de implementação.

## Regras por PR (resumo do que CLAUDE.md exige)

- 1 lane = 1+ PRs pequenos; branch `agent/<branch_slug-da-lane>/<ts>`.
- Gates locais antes de cada push: `pre-commit run --all-files` +
  `pytest backend/tests -q` + `pytest tests -q` (+ frontend se tocar
  `frontend/`). Rebase + drift check antes de abrir PR.
- Dinheiro nunca é float (ADR-090); testes de DB nunca mockam DB;
  endpoint JSON novo → `response_model` + `make update-openapi-snapshot`;
  migration test → `pytestmark = pytest.mark.migration`.
- Prompt LLM alterado → bump `PROMPT_VERSION`
  (`dev/check_prompt_version_bumped.py`).
- Flip da lane para `shipped` (ship_pr/ship_date) no PR que fecha a
  lane; `python3 dev/build_doc_index.py --inline` para regenerar.
- Auto-merge squash (`gh pr merge <N> --squash --auto`); "concluído" =
  merge confirmado em `origin/main` com CI verde.

## Anti-loop e comunicação

- Objeção de especialista → 1 rodada de ajuste; persistiu → você decide
  e registra a divergência no PR.
- Anuncie em 1-2 linhas: cada agente iniciado/encerrado, cada operação
  git, cada gate descoberto. Bloqueado >10min → reporte.

## Fechamento da sprint

Quando as lanes atingirem estado terminal (shipped / blocked-com-nota /
carry-over declarado):
1. Verifique os KRs do `_README.md` da A33 um a um (KR2: gate de float
   ativo; KR3: A17 `done` + goldens verdes; KR4: prune + drift-check com
   evidência). KR1: relate ação-de-owner-zero ou os gates descobertos.
2. l6/l9 bloqueadas pela A32 viram carry-over declarado — não contam
   contra KR1 (nota no _README).
3. Flip A33 → `done` (ou registre carry-over), atualize
   `docs/_MOC/SPRINTS-active.md`, adicione entry no changelog
   (docs-first, commit separado), arquive este prompt
   (`git mv docs/agent_prompts/orchestrator_a33_autonoma.md
   docs/agent_prompts/archive/orchestrator_a33_autonoma-YYYY-MM-DD.md`
   + linha na tabela do README).
4. Devolva o bloco final: Entregue (PRs + commits-merge) · Cronologia ·
   Aprendizados (3-5 bullets) · Débitos/riscos · Próximos passos
   concretos (ou "nenhum").
```
