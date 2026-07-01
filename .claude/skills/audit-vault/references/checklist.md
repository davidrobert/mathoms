# Checklist de auditoria de vault

> Referência da skill [`audit-vault`](../SKILL.md). Desdobra os 4 critérios
> (**completude, corretude, consistência, precisão**) por tipo de arquivo, com a
> coluna **"coberto por gate"** — o julgamento LLM (camada 3) **nunca**
> re-verifica o que um gate determinístico (camada 1) já pega. Regra canônica:
> [[ADR-302]].

---

## 1. Mapa critério × cobertura (o que é gate vs. o que é julgamento)

| Critério | Gate cobre (determinístico, camada 1) | Gap de julgamento (LLM, camada 3) |
|---|---|---|
| **Completude** | frontmatter obrigatório presente (`validate_frontmatter`), filename↔id (`check_doc_filename_id`), índices `_MOC/_generated` sincronizados (`build_doc_index --check`) | ADR `Proposto` esquecido sem flip para `Decidido`; plano sem critério de aceite; MOC não indexa nota nova; glossário sem termo que a ADR introduziu; runbook sem seção de rollback |
| **Corretude** | wikilink resolve (`check_doc_links`), anchor existe (`check_adr_anchors`), formato Status/Data (`validate_adr_format`), markdown link relativo (`check_doc_markdown_links`) | conteúdo factualmente errado (path de teste inexistente); regra de domínio que contradiz `config/`; ADR descreve API que mudou |
| **Consistência** | link bidirecional existe como wikilink | **supersedure unidirecional** (Y supersede X, X não declara `superseded_by`); dois ADRs decidindo o mesmo em direções opostas; CLAUDE.md ↔ ADR drift; tag folksonomy vs. vocabulário controlado |
| **Precisão** | — (gates não veem semântica) | número/threshold desatualizado (ex.: "156 ADRs" quando são 292); data de revisão parada; exemplo cujo valor não bate a fórmula atual; prosa↔código divergentes |

**Coração da skill:** as células vazias/direita — sobretudo **precisão factual**
(doc↔realidade) e **supersedure semântica**. É onde o LLM ganha; o resto o gate
faz de graça.

---

## 2. Roteamento por `type:` do frontmatter (não por path)

| `type:` / arquivo | Especialista (§Subagentes do CLAUDE.md) | Foco de julgamento |
|---|---|---|
| `adr` (forma) | `information-architect` | atomicidade, size_lines, supersedure bidirecional, tags |
| `adr` (conteúdo técnico) | `senior-cto` | decisão contradiz arquitetura/invariante vigente |
| `adr` (conteúdo de domínio) | `financial-planner` | regra financeira contra o enforcer/metodologia |
| `plan` / `lane` | `product-manager` + `information-architect` | KR/ondas/critério (PM); forma/frontmatter/MOC (IA) |
| `track` | `information-architect` | forma de lane operacional (schema `note-track`) |
| `config/prompts/*.yaml` | `prompt-engineer` | eval, determinismo, versão (conteúdo do prompt) |
| `domain-rule` | `financial-planner` | rule-as-code (ADR-143) contra `config/` |
| reference / CLAUDE.md (doc↔código) | **loop principal** (diff textual) | maioria dos DOC-BLOCK não precisa de especialista |

> A skill **não** carrega tabela própria de "quando chamar quem" — isto é só o
> mapa de foco. A autoridade de gatilho é o §Subagentes do CLAUDE.md.

---

## 3. Severidade → ação (ancorada em consequência)

| Severidade | Definição | Ação |
|---|---|---|
| **DOC-BLOCK** | Doc contradiz código/ADR vigente ⇒ um agente decidiria errado. | Fix agora: commit `docs(...)` imediato (docs-only) ou lane XS se toca código. |
| **DOC-DRIFT** | Desatualizado/inconsistente mas **não** indutor de erro imediato. | Batch em **uma** lane P2 no BACKLOG (estilo W6-T04). A skill propõe o batch. |
| **DOC-POLISH** | Cosmético (TOC, frontmatter incompleto, prosa). | Wontfix por default em dogfood ou batch pré-beta. |

Só **DOC-BLOCK interrompe**. Findings ≥ DOC-BLOCK passam pelo **verify**
(camada 4) antes de entrar no relatório.

---

## 4. Estrutura de finding (deduplicável + acionável)

```yaml
id: vault-<YYYY-MM-DD>-rN-NNN   # sequencial p/ citação humana/anchor
criterio: completude|corretude|consistencia|precisao
dimensao: forma|plano|prompt|dominio|arquitetura   # → roteia p/ dono
path: docs/adr/247-vault-md.md   # SEM :linha na chave de dedup (linha muda)
regra: <gate ou princípio violado>
severidade: DOC-BLOCK|DOC-DRIFT|DOC-POLISH
dono: information-architect|product-manager|prompt-engineer|financial-planner|senior-cto|loop
disposicao: procede-aberto        # DEFAULT; humano rebaixa. Nunca auto-refutar.
evidencia: <trecho do doc + trecho da fonte-de-verdade (obrigatório p/ DOC-BLOCK)>
```

**Dedup entre runs:** chave semântica **`(path, regra)`** — não o `id`
sequencial. Ao abrir run novo, cruze contra o `procede-aberto` da seção anterior
de [`AUDITS-active.md`](../../../docs/_MOC/AUDITS-active.md) (cadência §4).

---

## 5. Armadilhas (não gerar falso-positivo)

1. **`archive/` + sprint fechada** — fora do julgamento de precisão (gates
   ainda rodam via pre-commit). Auditar snapshot congelado = falso-drift.
2. **Shims** (`DECISIONS.md`, `BACKLOG.md`, `CHANGELOG.md`) — âncoras
   históricas "órfãs" são intencionais; `check_adr_anchors` já isenta.
3. **HTML derivado** ([[ADR-247]]) — `docs/plan/<X>/assets/*.html` e afins são
   legítimos. Só HTML **substituindo** `.md` canônico é DOC-BLOCK.
4. **Wikilink-stub futuro** — `[[ADR-XXX]]` planejado (link-as-you-go). Cheque
   se é TODO explícito antes de flaggar.
5. **`config/prompts/*.yaml`** — a skill roteia a **forma**; o **conteúdo**
   (determinismo/eval) é do `prompt-engineer`.
6. **Busca** — nunca `rg --no-ignore` (puxa `.claude/worktrees/`); varra por
   bucket lendo `CONTEXT_INDEX.md` primeiro.
