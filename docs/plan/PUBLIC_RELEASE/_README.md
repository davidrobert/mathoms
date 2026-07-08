---
id: PLAN-public-release
type: plan
title: "PUBLIC_RELEASE — tornar o repo público in-place com segurança e qualidade de referência"
status: draft
sprint_origem: A34
sprint_atual: null
sprints_envolvidas: [A34]
created_at: 2026-07-08
last_review: 2026-07-08
adrs_canonical:
  - "[[ADR-313]]"
  - "[[ADR-314]]"
  - "[[ADR-315]]"
  - "[[ADR-316]]"
  - "[[ADR-317]]"
  - "[[ADR-318]]"
  - "[[ADR-319]]"
  - "[[ADR-320]]"
tags:
  - type/plan
  - status/draft
  - area/seguranca
  - area/ci
---

# PUBLIC_RELEASE — tornar o repo público in-place com segurança e qualidade de referência

> **Origem:** co-design multi-agente 2026-07-08 (orquestrador + 5 especialistas em
> paralelo — `product-manager`, `information-architect`, `sre-devops`, `senior-cto`,
> `gtm-strategist` — + síntese de fechamento `senior-cto`, protocolo anti-loop do
> CLAUDE.md). Semente: auditoria de PII/segredos de 2026-07-08 (4 agentes: histórico
> git · working tree · apresentação · sre-devops). Inventário mascarado dos achados:
> [audit-2026-07-08.md](audit-2026-07-08.md) (**anexo — fonte das lanes de saneamento**).
>
> **Restrição do owner:** flip **in-place** do repo `davidrobert/mathoms` (NÃO criar
> repo novo). Duas objeções foram registradas contra essa restrição (ver §"Objeções
> registradas") — o owner está ciente e o plano trabalha dentro da restrição.
>
> **Status:** `draft` — nenhuma lane abre antes do **gate G0** (Onda 0, decisões
> owner-gated em 8 ADRs `Proposto`). Este plano é o formato canônico multi-fase
> ([[ADR-182]]); runbooks das operações destrutivas (rewrite de histórico, flip) são
> tracks self-contained em `docs/agent_prompts/`.

---

## Tese

Tornar o Mathoms público expõe **três camadas de contaminação simultâneas** e uma
**superfície de apresentação/negócio** que precisa de decisão consciente. A auditoria
provou que a disciplina recente funcionou (zero API key viva, fixtures golden
sintéticas, prompts sem PII) — o passivo é histórico e de escopo:

1. **HEAD atual** — dados financeiros reais em arquivos tracked: `_archive/` (58 PDFs
   bancários reais), endereço residencial em ~27 arquivos (incluindo código e testes),
   CPFs, o `EXEMPLO_DE_RELATORIO.html` real, migration de seed com nomes de terceiros,
   ~15 ADRs/docs de sprint com valores/placas/contrato reais.
2. **Histórico git** — recuperável de `origin/main` mesmo após limpar o HEAD:
   `config/family_members.json` (CPFs, filho menor), `members/` (holerite), `processed/`
   (transações reais), patrimônio nominal em ~100 mensagens de commit, Gmail pessoal em
   813 commits. Escopo real: **1.862 commits + 85 branches `agent/*` + 75 worktrees**.
3. **Metadados GitHub** — **855 PRs/issues/logs de CI**, imutáveis por git.

Além da PII, há **IP e negócio** que não devem ser públicos por default: prompts de
produto que citam **Perini/Cerbasi/AUVP nominalmente** (violação de sigilo metodológico
que a auditoria de *PII* não mediu), o playbook competitivo (`COMPETITIVE_PIERRE`),
pricing concreto. E a apresentação mínima que, ausente, causa dano ativo: **não existe
`LICENSE`** (repo público sem licença = *all-rights-reserved* hostil).

**O MLP do flip é "público SEGURO", não "projeto de referência".** O must-have bloqueia
o flip só quando sua ausência causa vazamento de PII, dano legal ou exposição de
segurança. Polish de percepção (badges, diagrama, CODE_OF_CONDUCT, docs-EN) é *should*
pós-flip. Confundir os dois infla o escopo e atrasa o marco de segurança.

---

## Objeções registradas (owner ciente — decisão em [[ADR-316]] / G0)

O protocolo de co-design registra objeções uma vez; o plano trabalha dentro da
restrição. Duas objeções materiais foram levantadas por 4 dos 5 especialistas e
**devem ser lidas antes de aprovar G0**:

1. **In-place é arquiteturalmente inferior a repo novo para a Camada 3.** Os metadados
   GitHub (855 PRs/issues/logs de CI) são **matematicamente inapagáveis por git** — o
   rewrite de histórico (Onda 3) não os alcança. Um repo público novo, com push do HEAD
   já saneado, zeraria as **3 camadas de uma vez**, sem rewrite/bypass de Ruleset/triagem
   de metadados. Como o repo privado nunca teve tráfego/stars externos, o custo-benefício
   do in-place é fraco. **Se o owner exigir zero-risco em metadados, o flip in-place é
   logicamente incompatível** (cláusula em [[ADR-316]]) e a restrição reabre para repo
   novo. Vale ~30min do owner reconsiderar antes de G0.
2. **"Ser referência open-source" não é alavanca GTM validada para o ICP** (HENRY
   brasileiro que compra seriedade metodológica, não GitHub stars). Público que admira ≠
   público que paga. Antes do flip, articular **qual objetivo de negócio** o repo público
   serve (recrutamento? investidores? contribuidores?). Se o objetivo real é
   *transparência metodológica para confiança do cliente*, isso se resolve com um
   **whitepaper público**, não expondo o motor competitivo inteiro (ver [[ADR-314]]).

---

## O que já existe (reusar/reconciliar, não inventar)

- **Auditoria + inventário** ([audit-2026-07-08.md](audit-2026-07-08.md)): mapa mascarado
  de paths/hashes/ADRs por camada. Cada lane de saneamento referencia a subseção
  correspondente **por referência** (path:linha + tipo), NUNCA reproduzindo valor real —
  senão o anexo vira nova camada de contaminação.
- **Gates de PII/sigilo já existem, mas com cobertura incompleta:** `tests/utils/lint_no_real_pii.py`
  (só `tests/`, só CPF) e `dev/check_sigilo_terms.py` (só `frontend/` + `docs/_marketing/`).
  A Onda 2 os estende ao superset público — não cria do zero.
- **[[PLAN-i18n]]** (ADR-130, `paused` com gate de demanda): governa i18n de
  **produto** (locales do app). **Este plano não toca produto-i18n.** O escopo de
  idioma do PUBLIC_RELEASE é **exclusivamente EN de apresentação** (docs de repo);
  a Onda 7 ativa apenas a cláusula já escrita em [[PLAN-i18n]] §11 (Pós-launch)
  — "docs em EN se open-source". **es e pt-PT não são necessários para executar
  este plano** (locales de produto — ficam no PLAN-i18n, `paused` e intacto).
  Fronteira formalizada em [[ADR-318]].
- **[[PLAN-launch-trust]]**: suas `adrs_canonical` incluem [[ADR-246]]/[[ADR-255]]/[[ADR-267]]/[[ADR-271]]
  — ADRs que a Onda 1 anonimiza. Anonimização é **in-body apenas**; `id`/filename/wikilink
  permanecem intactos (invariante `filename ≡ id ≡ wikilink-target`), então o grafo do
  LAUNCH_TRUST não quebra.
- **`SECURITY.md`** (LGPD, SLAs) e **`.github/CONTRIBUTING.md`** já existem e são de bom
  padrão. CONTRIBUTING assume fluxo de agentes internos — adaptar é *should* (Onda 6 polish).
- **Backup / rotação:** `rotate_fernet_secrets.py` ([[ADR-171]], runbook `fernet_rotation.md`)
  é a ferramenta de confirmação da Fernet (Onda 0).

---

## Ondas, lanes e dependências (sprint A34)

Ordem de execução **serial com um único gate irreversível adjacente ao flip**. Correção
central do co-design (senior-cto vence): **os gates anti-regressão (W2) vêm ANTES do
saneamento (W1)** — gate-after-clean é anti-padrão (não verifica o próprio commit de
saneamento nem trava regressão durante as edições). Mesmo princípio "substrato antes de
tocar" do [[PLAN-data-lineage]].

```
W0(G0 gate decisões) ──► W2(G2 gates) ──► W1(G1 saneia HEAD) ──► W6-min(G6) ──► W3(G3 rewrite) ──► W8(G8 flip)
                                              │                        │            ▲
                         W5(G5 hardening) ────┘ (∥ com W1/W6)          │        W4(G4 metadados, ∥ com W3)
                                                                        │
                    W7 docs-EN + W6-polish + W4-ampla ── should, pós-flip (P2)
```

> **Convenção de sequenciamento (ler antes de orquestrar):** o **gate de onda** é o
> mecanismo de bloqueio primário, NÃO o campo `depends_on` das lanes. `depends_on`
> captura só dependências **específicas entre lanes** (ex.: `l22` flip depende de
> `l20`+`l21`+`l15`+`l16`). As barreiras de onda — **G0** (nenhuma lane W1+ abre antes
> das 8 ADRs decididas) e **G2** (nenhuma lane W1 de saneamento roda antes dos 3 gates
> de W2 verdes) — são invariantes do plano e **não** estão replicadas em cada
> `depends_on` (seria ruído em 23 lanes). Um orquestrador deve tratar G0 e G2 como
> pré-condições de onda, lidas aqui, e usar `depends_on` só para a ordem fina intra/inter-lane.

| Onda | Objetivo | Lanes | P | Gate |
|------|----------|-------|---|------|
| **W0 — Gate de decisões** (owner) | Travar política/negócio/IP/risco em 8 ADRs `Proposto`. Nenhuma lane W1+ abre antes de G0. | [[A34.l1]] ADRs do gate · [[A34.l2]] backup mirror off-site + tag · [[A34.l3]] confirmar rotação Fernet em prod | P0 | **G0:** 8 ADRs (313–320) mergeadas com decisão do owner; aceite de risco de metadados assinado **OU** restrição in-place reaberta; backup restaurável + tag `pre-public-flip-backup`; Fernet `old_key_decryptable=0` |
| **W2 — Gates anti-regressão** | Instalar+provar gates PII + sigilo + secrets ANTES do saneamento. | [[A34.l4]] estender `lint_no_real_pii` a `docs/`+domínio · [[A34.l5]] estender `check_sigilo_terms` ao superset · [[A34.l6]] bloquear `_archive/` + gitleaks bloqueante | P0 | **G2:** os 4 gates rodam **VERMELHO** no HEAD contaminado (critério de detecção) e um commit-teste sintético é BARRADO |
| **W1 — Saneamento do HEAD** | Zerar PII camada-1 + redigir/split IP público, sob gates verdes de W2. | [[A34.l7]] deletar `_archive/` · [[A34.l8]] regenerar `EXEMPLO_DE_RELATORIO` sintético · [[A34.l9]] anonimizar ~15 ADRs+docs (in-body) · [[A34.l10]] purgar CPFs+endereço · [[A34.l11]] neutralizar seed+paths · [[A34.l12]] redigir/split `COMPETITIVE_PIERRE`+prompts+pricing (owner) | P0 | **G1:** gates W2 verdes no HEAD; `git ls-files` sem `_archive/`; EXEMPLO regenerado com cobertura estrutural completa; `check_doc_links`+`check_adr_anchors` verdes; suíte completa verde |
| **W5 — Hardening CI/CD** (∥ W1) | Fechar superfície que só existe em repo público. Config no HEAD, independe do histórico. | [[A34.l13]] `permissions: read-all` default + require-approval · [[A34.l14]] SHA-pin das 4 actions de terceiros · [[A34.l15]] GHAS + Fernet dummy → secret | P0/P1 | **G5:** permissions mínimas em todos os workflows; 4 actions SHA-pinned + Dependabot; GHAS + push protection; CODEOWNERS em `.github/workflows/**` |
| **W6 — Apresentação (mín.)** | Só o que, ausente no flip, causa dano legal (LICENSE) ou expectativa falsa (disclaimer). | [[A34.l16]] LICENSE + README EN com disclaimer + fronteira de idioma · [[A34.l17]] polish (P2, pós-flip) | P0/P2 | **G6-min:** LICENSE coerente com [[ADR-313]]; README EN com disclaimer de dogfood + fronteira EN/PT-BR + narrativa [[ADR-183]] sem atribuição nominal; passa no gate de sigilo |
| **W3 — Rewrite de histórico** (IRREVERSÍVEL, owner) | Reescrever git (blobs + mensagens + mailmap) via `git-filter-repo`. Penúltima operação, adjacente ao flip. | [[A34.l18]] runbook `git-filter-repo` (track) · [[A34.l19]] freeze de merges + deletar 85 branches `agent/*` · [[A34.l20]] bypass do Ruleset + atualizar hash-refs | P0 | **G3:** filter-repo em clone `--mirror` (paths→replace-text→replace-message→mailmap); validação DUPLA (gitleaks árvore+histórico = 0); 85 branches deletadas; hash-refs em ~10 ADRs atualizadas; Ruleset **reativado e verificado**; backup íntegro; FREEZE ativo até W8 |
| **W4 — Metadados GitHub** (∥ W3, owner) | Mitigar parcialmente a camada-3. Aceite de risco em [[ADR-316]]. | [[A34.l21]] triagem T1 de PRs/issues/CI logs sensíveis | P0 | **G4-min:** itens T1 (PII direta/dogfood/competitivo) editados/deletados; logs de CI de dogfood expirados; risco residual T3 aceito em [[ADR-316]] |
| **W8 — Flip + verificação** (owner) | Flip para público + critério de aceite global. Smoke de clone anônimo ANTES do flip. | [[A34.l22]] flip + verificação pós-flip (track) | P0 | **G8:** critério de aceite global (ver §Verificação) |
| **W7 — i18n docs-EN** (should, pós-flip) | Só **EN de apresentação**; não toca produto-i18n. | [[A34.l23]] docs EN de apresentação + cross-link PLAN-i18n | P2 | **G7:** README/CONTRIBUTING/COC/SECURITY em EN; vault permanece PT-BR ([[ADR-318]]); produto-i18n PAUSED intacto; **es e pt-PT fora do escopo deste plano** |

**Escopo A34 (caminho crítico → público-seguro):** W0→W2→W1/W5→W6-min→W3/W4→W8.
**Should pós-flip (janela A35):** W6-polish ([[A34.l17]]), W7 ([[A34.l23]]), varredura
ampla dos 855 metadados — marcadas P2, não bloqueiam o marco de segurança.

---

## ADRs `Proposto` (gate G0 — a partir de ADR-313)

Uma ADR atômica por decisão ([[ADR-182]]), NÃO uma ADR-monstro. Verificar ID livre
antes do push (sessão longa criando ADR pode colidir).

| ADR | Owner? | Decisão | Recomendação (leading) |
|-----|--------|---------|------------------------|
| [[ADR-313]] | 🔒 | Licença open-source | **BSL 1.1** source-available (Change License Apache-2.0, 4 anos) — preserva o moat sob COMPETITIVE_PIERRE. Alt.: AGPL-3.0; fallback MIT/Apache |
| [[ADR-314]] | 🔒 | Escopo público (allowlist/blocklist de paths + IP) | Split privado dos prompts de produto; redigir/mover COMPETITIVE_PIERRE; genericizar pricing |
| [[ADR-315]] | 🔒 | Estratégia de rewrite de histórico | `git-filter-repo` (rejeita BFG/squash-to-genesis/shallow); backup antes; validação dupla; bypass owner do Ruleset |
| [[ADR-316]] | 🔒 | Aceite de risco de metadados GitHub imutáveis | Triagem em tiers T1/T2/T3 + **cláusula de incompatibilidade lógica** (zero-risco ⇒ reabrir in-place) |
| [[ADR-317]] | 🔒 | Identidade de autoria no mailmap público | Owner decide identidade pública (Gmail 813 commits); tratamento de co-authors |
| [[ADR-318]] | 🔒 | Fronteira EN-apresentação vs PT-BR-vault | Ativa cláusula §11 (Pós-launch) do [[PLAN-i18n]] (sem emenda de ADR-130); es e pt-PT fora do escopo deste plano |
| [[ADR-319]] | — | Contrato de gates anti-regressão PII + sigilo | Contrato negativo permanente + enforcement (lint/sigilo/forbidden-paths/gitleaks) |
| [[ADR-320]] | — | Hardening CI/CD + paridade estrutural do EXEMPLO sintético | permissions/SHA-pin/GHAS + invariante "zero seção removida, só dados sintéticos" |

---

## KRs

| # | Key Result | Baseline | Meta |
|---|---|---|---|
| **KR1** | PII zero em HEAD e histórico | 3 camadas contaminadas | gitleaks árvore+histórico verde + `lint_no_real_pii` estendido verde + **smoke de clone anônimo** com grep de padrões PII/atribuição = zero |
| **KR2** | Cobertura dos gates sobre o superset público | lint só `tests/`+CPF; sigilo só `frontend/`; gitleaks informativo | lint cobre `docs/`+raiz+domínio; sigilo cobre `docs/**`+prompts+README+migrations; gitleaks bloqueante+full-history; commit-teste BARRADO |
| **KR3** | Zero atribuição nominal metodológica no público | prompts citam Perini/Cerbasi/AUVP; ~200 arquivos internos | grep `(perini\|cerbasi\|auvp\|raul sena\|viver de renda)` no superset público = vazio; vocabulário canônico [[ADR-183]] |
| **KR4** | Superfície CI/CD hardenizada | só job `changes` declara permissions; 4 actions tag-flutuante; GHAS off | permissions read-all default; 4 actions SHA-pinned; GHAS+push protection; first-time approval; Fernet dummy em secret |
| **KR5** | Ruleset `main-protection` intacto pós-flip | Ruleset ativo colide com force-push | bypass na janela W3 → force-push → **reativado e verificado**; zero janela aberta |
| **KR6** | Apresentação mínima presente no flip | sem LICENSE/COC; README interno | LICENSE + README EN com disclaimer + fronteira de idioma, passando no gate de sigilo |
| **KR7** | Metadados de alto risco triados | ~15 itens T1 em 855 | 100% dos T1 editados/deletados + logs de dogfood expirados; residual T3 aceito em [[ADR-316]] |

---

## Registro de decisões (co-design 2026-07-08)

Decisões owner-gated migram para ADR; as demais são fechadas pela síntese senior-cto.

- **[G0/ADR-316]** Aceite de risco de metadados é gate **G0** com cláusula de
  incompatibilidade lógica — falhar cedo (W0), não tarde (W8) após desperdiçar W1–W3.
- **[ordem W2→W1]** Gates anti-regressão ANTES do saneamento (CTO vence PM/IA/SRE):
  o gate rodando vermelho no HEAD contaminado é o critério de detecção, e trava regressão
  durante as ~15 edições de anonimização.
- **[EXEMPLO_DE_RELATORIO]** Regeneração sintética com cobertura estrutural completa, **sem
  onda de re-paridade** (nenhum golden/teste carrega o `.html` em runtime; única ref é uma
  docstring em `tests/unit/pipeline/test_financial_score_calculator.py:402` que cita linhas
  físicas do HTML — `L1809-1811` — como nota humana; atualizar path+citação no mesmo PR, de
  preferência de-acoplando da linha física — ver [[A34.l8]]).
- **[sigilo/prompts]** Prompts de produto citam Perini/Cerbasi/AUVP e `check_sigilo_terms`
  NÃO os cobre — bloqueador de flip que 4/5 agentes não capturaram (só GTM). Fecha em W2
  ([[ADR-319]]) + W1 ([[A34.l12]]).
- **[licença/ADR-313]** BSL 1.1 leading (moat competitivo), AGPL-3.0 alternativa, MIT/Apache
  fallback de máxima adoção. Owner + gtm-strategist + legal.
- **[escopo de idioma deste plano]** O PUBLIC_RELEASE adiciona **só EN de apresentação**
  (docs de repo). **es e pt-PT não são necessários para executar este plano** (simplificação
  do owner, 2026-07-08): são locales de **produto** e ficam no [[PLAN-i18n]] (`paused`,
  intacto) — não são dependência nem deliverable aqui. "Referência global" = audiência-de-repo,
  que EN resolve; produto fiscal-BR não muda de mercado por causa do flip. Se o owner quiser
  dropar es do roadmap de **produto**, é mudança separada no PLAN-i18n (não neste plano).
- **[escopo git]** 1.862 commits (não 2.729 — diferença são refs de branches), 85 branches
  `agent/*`, 75 worktrees.
- **[backup/Fernet]** Backup off-site + tag + confirmação de rotação Fernet são
  pré-condições de **W0**, não de W3 (o rewrite é irreversível; sem rede antes, force-push
  mal-sequenciado = perda permanente).
- **[_archive/ delete]** Checar referências vivas antes: `manual_operacao_v6.1.md` é citado
  em CLAUDE.md/ARCHITECTURE — mover conteúdo não-PII sanitizado OU atualizar refs no mesmo PR.
- **[anonimização in-body]** Nunca tocar `id`/filename/`aliases`/`supersedes`/`superseded_by`/`relates_to`
  — só texto de exemplo no corpo. Onde a PII é exemplo pedagógico (ADR-246/271), reescrever
  com `Titular`/`Cônjuge` sintéticos preservando a mecânica.

**Decisões abertas do owner (bloqueiam G0):** [[ADR-313]] licença · [[ADR-314]] escopo
público · [[ADR-316]] aceite de metadados (ou reabrir in-place) · [[ADR-317]] identidade
mailmap · [[ADR-318]] confirmar que docs-EN não sinaliza mercado PT · confirmação
operacional da rotação Fernet · aprovação da janela de FREEZE (W3→W8).

---

## Verificação (por onda)

- **G0:** 8 ADRs mergeadas com decisão textual; backup mirror clonável de teste; tag
  `pre-public-flip-backup` no HEAD de `main`; `rotate_fernet_secrets.py` com
  `old_key_decryptable=0`.
- **G2:** cada gate roda VERMELHO no HEAD atual (prova que detecta); commit-teste com
  PII/atribuição sintética-conhecida é BARRADO pelos 4 gates.
- **G1:** `git grep` no HEAD = zero para CPF/endereço/placa/nome-de-terceiro/patrimônio-nominal;
  `git ls-files _archive/` vazio; EXEMPLO com todas as seções/cards/charts/IDs; suíte completa
  verde (código neutralizado não quebrou); `check_doc_links`+`check_adr_anchors` verdes.
- **G5:** `git grep -n "uses:.*@v[0-9]" .github/workflows/` = zero para actions de terceiros;
  permissions read-all no topo de todos os workflows; GHAS verde num PR de teste.
- **G6-min:** LICENSE presente; README EN passa no gate de sigilo estendido.
- **G3:** gitleaks árvore+histórico = 0 (dupla); 85 branches `agent/*` deletadas; Ruleset
  reativado e verificado; FREEZE ativo; backup íntegro.
- **G4-min:** hits T1 tratados; risco residual T3 em [[ADR-316]].
- **G8 (aceite global):** (1) gitleaks árvore+histórico verde; (2) gates W2 verdes; (3) 85
  branches zeradas; (4) Ruleset reativado; (5) GHAS+push protection ativos; (6) 4 actions
  SHA-pinned; (7) LICENSE+README EN presentes; (8) T1 de metadados tratados; (9) Fernet
  inócua; (10) backup íntegro por ≥30d; (11) **SMOKE FINAL:** clone anônimo + grep dos
  padrões PII/atribuição = zero. O smoke roda **ANTES** do flip (o flip é irreversível na prática).

---

## Riscos & invariantes

- **W3 é a fase de maior blast-radius e a única irreversível.** Mitigação: backup off-site
  (W0) é a única rede; validação dupla; FREEZE de merges; janela curta e anunciada.
- **Camada 3 é irredutível por git.** [[ADR-316]] força o aceite de risco ou reabre in-place.
- **Anonimização preserva `filename ≡ id ≡ wikilink`** — link rot só ocorreria por rename/mudança
  de id (desnecessário para remover PII).
- **Fernet:** o rewrite remove o blob, mas a key só é inócua se a rotação ([[ADR-171]]) rodou
  em prod — não verificável do repo.
- **FREEZE de merges (W3→W8)** tem custo de error-budget de feature parado — aprovação do owner.
- **Sigilo metodológico:** publicar prompt que cita "AUVP/Perini/Cerbasi" = exposição de marca
  de terceiros sem licença — bloqueante e mecanizável.

---

## Referências

- Anexo de auditoria: [audit-2026-07-08.md](audit-2026-07-08.md).
- ADRs canônicas: [[ADR-313]]–[[ADR-320]].
- Reconciliação: [[PLAN-i18n]] ([[ADR-130]]) · [[PLAN-launch-trust]] · [[PLAN-report-premium]].
- Formato exemplar: [[PLAN-data-lineage]].
- Sprint de execução: [sprint/A34/_README.md](../../sprint/A34/_README.md).
- Runbooks (tracks self-contained): [[TRACK-public-release-history-rewrite]] ([[A34.l18]]) ·
  [[TRACK-public-release-flip]] ([[A34.l22]]).
