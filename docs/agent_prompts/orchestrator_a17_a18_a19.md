# Orquestração — Roadmap A17 → A18 → A19 (ingestão fiscal + bens + proteção)

> Instância do [_TEMPLATE_orchestrator.md](_TEMPLATE_orchestrator.md) para o
> roadmap desenhado em 2026-05-21. 3 sprints encadeadas com ADRs `Proposto`
> já mergeadas em `main`: A17 ([[ADR-238]] informes anuais), A18
> ([[ADR-239]] CRLV + apólices + FIPE), A19 ([[ADR-240]] card S_PROTECAO).
>
> **Uso:** copie o bloco abaixo no início da sessão. O orquestrador assume
> o perfil [`senior-cto`](../../.claude/agents/senior-cto.md) e respeita as
> convenções de [CLAUDE.md](../../CLAUDE.md).
>
> **Quando arquivar:** quando A17 + A18 + A19 estiverem inteiramente em
> `main` (todas as lanes `shipped`, ADRs `Decidido`). Mover para
> [`archive/`](archive/) com data.

---

```
# Orquestração — Roadmap A17 → A18 → A19 (ingestão fiscal + bens + proteção)

Atue como **orquestrador** com o perfil do agente `senior-cto`
(`.claude/agents/senior-cto.md`). Você decide, delega, integra
resultados e responde pelo trabalho — não executa pessoalmente o que
um especialista deve revisar/decidir.

## Permissões
- Instanciar **quantos agentes** julgar necessário, em paralelo quando
  independentes (1 mensagem, N `Agent` calls).
- **Abrir PR contra `main` com auto-merge** (`gh pr merge <N> --squash --auto`)
  após CI verde, respeitando o Repository Ruleset (sem `--admin`,
  sem `--no-verify`, sem push direto em `main`).
- Criar branch `agent/<slug>/<yyyyMMdd-HHmm>` e commitar em cadência
  (CLAUDE.md §Cadência de commit).

## Comunicação obrigatória
1. **Início de cada agente** — anunciar em 1-2 linhas: nome do agente,
   escopo do brief, por que foi escolhido.
2. **Fim de cada agente** — anunciar em 1-2 linhas: veredito
   (aprovou / aprovou-com-ressalvas / rejeitou), 1-3 bullets do que
   mudou na sua decisão.
3. **Cada operação git** — commit, push, PR aberto, PR mergeado
   (CLAUDE.md §Git).
4. **Bloqueios** — se ficar parado >10min aguardando algo (CI, decisão
   ambígua, conflito entre agentes), reportar imediatamente.

## Regras de gate (PR)
- **Co-design > review** (CLAUDE.md §Protocolo de delegação): consulte
  os especialistas **antes** de codar, com premissas + opções +
  recomendação inicial — não no final pra carimbar.
- **Gate triplo obrigatório antes de abrir PR**: aprovação explícita de
  `financial-planner`, `product-designer` e `data-engineer`.
  - Invoque os 3 em **paralelo** com brief mínimo idêntico (contexto +
    premissas + opções + recomendação + pergunta clara).
  - **NÃO peça código** ao especialista — peça decisão/revisão.
- **Anti-loop**: objeção de especialista → **1 rodada** de ajuste no
  plano. Se persistir, **você (senior-cto) decide e fecha**, registrando
  no PR a divergência + justificativa do call. Sem ping-pong.
- **ADR `Proposto` antes do PR** se a mudança for P0/P1 com escopo
  arquitetural (modelo de DB, contrato API, fornecedor externo, política
  de segurança, invariante crítico). Veja CLAUDE.md §Política operacional.
  **Atenção:** ADR-238 (A17), ADR-239 (A18) e ADR-240 (A19) já estão
  `Proposto` em `main`. PR de implementação **referencia** e flippa para
  `Decidido (Sprint <X> L<n>)` apenas no último PR da lane (cutover).
- **Gates locais antes do push** (não confiar só no CI):
  `pre-commit run --all-files` + suíte relevante
  (`pytest backend/tests -q`, `pytest tests -q`, `cd frontend && npm test -- --run`,
  E2E `@critical` se tocou fluxos críticos). Diff docs-only pula pytest.
- **Rebase + drift check** antes de pushar/abrir PR (CLAUDE.md §Pre-push).
- **Squash-merge** é o único método. Auto-merge habilitado; aguardar
  `All checks green`.

## Documentação
- Após **cada PR aberto** (não apenas no merge), avaliar se exige update
  em: `CLAUDE.md` (regras timeless), `docs/CHANGELOG.md`, `docs/adr/`
  (nova ADR ou flip `Proposto → Decidido`), `docs/_MOC/SPRINTS-active.md`,
  lane do sprint, plano canônico.
- Após **cada lane completa**: changelog entry em
  `docs/sprint/<X>/changelog/CHG-YYYY-MM-DD-<scope>.md`; lane
  `status: shipped` + `ship_pr` + `ship_date`; MOC `_README.md` da
  sprint atualizado §Lanes com checkmark.
- Se mudar **hotspot** (CLAUDE.md, CHANGELOG, BACKLOG, DECISIONS shim),
  rodar pre-flight (`git fetch && git log -5 --oneline origin/main -- <arquivo>`)
  e commitar **separado do código**, no fim da sessão (CLAUDE.md §Hotspots).
- "Concluído" = **PR mergeado em `main` (squash) com CI verde**. Não
  marcar tarefa como done antes disso.

## Ao final (quando todos os agentes encerrarem)
Devolva um único bloco com:
1. **Entregue** — lista de PRs (`#N · título · commit-merge`), com link
   da branch e ADRs flippadas.
2. **Cronologia** — quem rodou, quando, veredito, decisão tomada em caso
   de divergência (referenciando o anti-loop).
3. **Aprendizados** — 3-5 bullets do que foi não-óbvio nesta sessão
   (trade-offs reais, premissas que caíram, surpresas no domínio/stack).
4. **Recomendações** — débito gerado, refactors sugeridos, riscos a
   monitorar.
5. **Próximos passos** — apenas se concretos e atribuíveis (lane do
   BACKLOG / nova ADR `Proposto` / follow-up de produto). Se não houver,
   diga "nenhum".

Mantenha o resumo objetivo: bullets, sem floreio, sem repetir o que já
está nos PRs/ADRs — focar no **valor agregado** desta orquestração.

## Objetivo

Implementar o **roadmap A17 → A18 → A19** desenhado em 2026-05-21 — 3 sprints sequenciais com ADRs `Proposto` mergeadas em `main` cobrindo (a) ingestão de informes anuais avulsos como fonte fiscal paralela ao E1.6, (b) comprovantes de bem (CRLV) + apólices de seguro polimórficas + FIPE refresh, (c) card S_PROTECAO no relatório como 4º pilar AUVP.

### Contexto

Sessão dogfood do owner anexou **24 PDFs reais** que hoje caem em `.other` silencioso ou são mal-classificados:

- **15 informes fiscais** anuais (Sprint A17 — `docs/adr/238-ingestao-informes-rendimentos-anuais-avulsos.md`): BrasilPrev PGBL, 7 bancos PF (Itaú, Santander, Caixa, Nubank, PicPay, C6 PF, XP Investimentos), Wise multi-moeda no exterior, C6 PJ + Stone PJ, XP Proventos, Itaúsa holding, Einstein, mais um informe genérico.
- **3 CRLV-e + 3 apólices** (Sprint A18 — `docs/adr/239-comprovantes-bens-apolices-fipe.md`): Yamaha NMAX 160 STH2C88 2024, Yamaha NMAX DAV0351 2018, Fiat Toro GDK6A27 2022; apólice Tokio Marine Moto, Porto Moto, **Porto Proteção Combinada** (multi-bem: Toro + residência R Tasso Silveira 61).

Co-design `data-engineer` + `financial-planner` rodou em 2026-05-21 — decisões fechadas em "Decisões já fechadas (não reabrir)" de cada track. **Não reabra.** Se encontrar ambigüidade, escale ao owner; não improvise.

### Premissas

- ADR-238, ADR-239, ADR-240 já estão `Proposto` em `main`. Implementação **referencia** e flippa no cutover de cada lane.
- 4 sprints prévias (A11 platform review, A12 categorization learning loop, A16 cascata fiscal PJ) entregues — não interferem.
- ICP é wealth-tech BR alta renda (PJ/CLT mix), patrimônio diversificado, família com dependentes — perfil típico AUVP/Cerbasi/Perini.
- Stack: backend FastAPI + SQLAlchemy + Alembic + Celery + Redis; pipeline Python isolado de framework; frontend Next.js + Vitest + Playwright; LLM Anthropic SDK com cache de prompt.

### Restrições

- **Sem mudança em invariantes:** `codigo_rfb` imutável (ADR-225), pipeline não importa framework (ADR-097), dinheiro nunca é `float` (ADR-090), stateless rigoroso (ADR-111), ArtifactStore é DB-only (ADR-212).
- **Sem novos SaaS pagos:** FIPE via BrasilAPI (decidido). LLM segue Claude Anthropic (cache de prompt obrigatório).
- **LGPD/PII:** sem persistir diff informe vs declaração (efêmero em E5). Goldens com PDFs sintéticos anonimizados, eval real fora do git.
- **Linguagem CRC:** zero verbo prescritivo em qualquer copy de produto ("deve/precisa/recomendamos" proibido — só "considere/vale avaliar/verifique").
- **Não tocar A16/A11 entregues** sem co-design prévio com responsáveis (provável conflito de schema).

### Roadmap — ordem de pickup recomendada

| Ordem | Sprint | Lane | Track | Esforço | Status |
|---|---|---|---|---|---|
| 1 | **A17 L1** | previdência privada (BrasilPrev/PGBL) | `docs/sprint/A17/tracks/a17-l1-previdencia-privada.md` | ~7-9d, P1-P6 | `open` |
| 2 | **A18 L1** | CRLV-e (gateway) | `docs/sprint/A18/tracks/a18-l1-crlv-veiculos.md` | ~5d, P1-P5 | `open` |
| 3 | **A18 L2** ‖ **A18 L3** | apólice combinada V1 ‖ FIPE refresh | `docs/sprint/A18/tracks/a18-l2-apolice-seguro.md` · `docs/sprint/A18/tracks/a18-l3-fipe-refresh.md` | ~6d + 3d | esqueletos `ready` |
| 4 | **A17 L2** | financeiro PJ (C6 PJ, Stone) | `docs/sprint/A17/tracks/a17-l2-financeiro-pj.md` | esqueleto | `ready` |
| 5 | **A17 L3** ‖ **A17 L4** | financeiro PF + Wise ‖ proventos ações | `docs/sprint/A17/tracks/a17-l3-financeiro-pf.md` · `docs/sprint/A17/tracks/a17-l4-proventos-acoes.md` | esqueletos | `ready` |
| 6 | **A19 L1** | card S_PROTECAO (4º pilar AUVP) | `docs/sprint/A19/tracks/a19-l1-card-protecao.md` | ~6-8d, P1-P4 | `open` (depende A18 inteira) |

**Paralelismo permitido** (após L1 gateway de cada sprint estabelecer padrão arquitetural): L2/L3 do A18 podem rodar em paralelo por agentes distintos. A17 L3/L4 idem. A17 L2 (PJ) pode coexistir com qualquer A18 L*.

**Bloqueios rígidos:**
- A18 L2 e L3 **dependem** de A18 L1 (tabela `vehicles` + stage `extract_comprovantes_bens`).
- A19 L1 **depende** de A18 inteira em `main` (sem dado de apólice, card não tem o que renderizar).
- A17 L2-L4 **dependem** de A17 L1 (padrão de schema-base polimórfico).

### Pegadinhas críticas (do co-design 2026-05-21 — não reaprender)

**A17:**
- Declaração entregue **vence** informe quando ambos cobrem `(ano, fonte)` (ADR-238 D4). Divergência → warning E5 efêmero.
- VGBL nunca conta como capacidade PGBL.
- Wise: código RFB **62**, PTAX 31/12 via `market_rates` (ADR-135), variação cambial = GCAP **não** isento.
- `codigo_rfb` enums reaproveitados de E1.6 (ADR-157) sem alteração in-place.

**A18:**
- **Tabela `vehicles` separada** (não array em `baseline_patrimonial`) com identidade `(workspace_id, placa, renavam)` imutável — padrão ADR-216 `real_estate_assets`.
- Schema apólice + cobertura **ambos Discriminated Union** já em V1 (antecipa vida/saúde/AP V2 sem migration breaking).
- LMI via `lmi_modo` discriminator + valores separados (não union de tipos no valor).
- FIPE lookup **sempre assíncrono** (Celery). Teste unitário deve travar regressão de sincronia.
- LLM Haiku → Sonnet cascade com gate (multi-bem OU confidence<0.7 OU strings "combinada"/"residencial+auto").
- Apólice combinada Porto (Toro + residência) é **caso V1 obrigatório**.
- `pagador_cpf ≠ segurado_cpf` (cônjuge paga) — FK opcional `family_members` (ADR-127) em ambos.
- Histórico de apólices imutável temporal (renovação = apólice nova, não update).

**A19:**
- Card posicionado **entre S2 (Reserva) e S4 (Patrimônio)** seguindo ordem AUVP. Reposicionar S3 (Renda) após S4 — mudança em `config/report_layout.yaml` + codegen (ADR-076).
- KPIs V1: G (prêmio total hero), B (% renda em prêmios faixas Cerbasi 1-5%), F (seguros ausentes qualitativo), C (gap cobertura por bem auto V1). KPI A (% patrimônio coberto) **descartado V1**.
- Vida/Saúde/PJ ficam como **placeholder visual** em V1 (schema preparado, ativar V2).
- KPI F vida usa `family_members.json` para gating; sem dados → flag não dispara (degrada gracioso).
- Cross-link textual S8 Previdência (componente de proteção para beneficiários) — sem duplicar KPIs.

### Critério de aceite por lane

Lane **só é concluída** quando:

1. PR mergeado em `main` via squash + CI verde (`gh pr view <N> --json mergeCommit,mergedAt`).
2. Changelog entry em `docs/sprint/<X>/changelog/`.
3. Lane (`docs/sprint/<X>/lanes/<id>.md`) → `status: shipped` + `ship_pr` + `ship_date`.
4. MOC `_README.md` da sprint atualizado §Lanes com checkmark.
5. Se for última lane da sprint: ADR pai flippa `Proposto → Decidido (Sprint <X>)`.
6. Workspace dogfood: PDFs reais do batch (15 informes A17 + 6 comprovantes A18) processam end-to-end com `confidence ≥ 0.7` para os escopos das lanes entregues; PDFs fora do escopo continuam em seu fluxo sem regressão.

### Entregável esperado

- **Múltiplos PRs** (1+ por fase de cada lane). Squash-merge. Conventional Commits validados.
- **Cronologia transparente** das decisões de orquestração — quando invocou cada especialista, veredito, divergência resolvida pelo senior-cto.
- **Bloco final estruturado** (Entregue / Cronologia / Aprendizados / Recomendações / Próximos passos) ao encerrar sessão ou ao fim de cada lane que for marco.

### Primeira ação

Antes de tocar qualquer código:

1. Leia `CLAUDE.md` seções "Concluído", "Code style", "Git e commits", "Antes de pegar uma task do BACKLOG".
2. Confirme o estado atual da sprint corrente: `docs/_MOC/_generated/SPRINT_CURRENT.md`.
3. Verifique concorrência:
   ```bash
   git worktree list
   git for-each-ref --sort=-committerdate \
     --format='%(committerdate:iso) %(refname:short)' \
     refs/remotes/origin/agent/ | head -15
   ```
4. Leia trinca canônica da próxima lane livre (ordem do roadmap): ADR pai + lane + track.
5. **Anuncie ao owner em 1-2 linhas:** qual lane vai puxar, esboço do P1, e qual especialista será invocado primeiro.

Se a lane que você quer puxar tem branch `agent/<mesmo-slug>/*` com commit <24h, escolha a próxima na ordem. Se 2+ lanes paralelas estão livres, escolha pela ordem do roadmap e anuncie ao owner.

**NÃO comece codando** sem o pre-flight (passos 1-5) e sem anúncio.
```
