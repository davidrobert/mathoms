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

**Carve-out `docs/_MOC/*.md`:** para MOC, gate cobre **só** wikilink
(`check_doc_links`) e link markdown relativo — `validate_frontmatter` e
`check_doc_filename_id` **excluem** `_MOC` inteiro. Frontmatter, id e estado
de linha de MOC são julgamento (camada 3), não assuma cobertura que não
existe.

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
| `moc` — registro `*-active.md` com disposição (PIPELINE-REVIEWS/REPORT-REVIEWS/LEDGER-CERTIFY/PARSE-CERTIFY) | **loop principal** (estado da linha, mecânico e local-first — §6) + `information-architect` (forma da célula/ponteiro) | linha-zumbi; falso-fechado; prescrição refutada sem marcador na célula. **Nunca o mérito do achado** — mérito é da cadência da skill dona ([[ADR-343]]) |
| `moc` — navegacional e fila (00-INDEX/PLANS-active/OWNER-GATED) | `information-architect` | ponteiro para plano arquivado; narrativa ⟂ `sprint_status`; `last_review:` parado (OWNER-GATED) |
| `.claude/skills/*` | `information-architect` | forma da skill (SKILL.md + references), fronteira entre skills, sync com `docs/reference/SKILLS.md` |
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

**Finding sobre linha de registro** estende a chave para
**`(path, regra, âncora)`** com `âncora = <seção rN>/<código>` (ex.:
`docs/_MOC/AUDITS-active.md#r9/F01`) — código **sozinho não é identidade**:
`F01` reinicia a cada run do AUDITS-active, e a onda r7 da PIPELINE-REVIEWS
usa `DE-*`/`FP-*` sem prefixo de run. Essa chave é da **auditoria** e não
substitui nem conversa com a chave interna do registro
(`(dimensão, evidência-âncora, regra)`, propósito commit-safety/PII —
[[ADR-343]]).

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
7. **Medição-fantasma** — número citado sem comando que o reproduza não é
   evidência: **re-meça, não releia**. Finding de precisão numérica só entra
   no relatório com o comando na `evidencia` (lição da revisão de método da
   lane-closeout, 2026-08-21; corrigida em #1590 com o SQL anexado).
8. **Não importe regras lane-shaped (CLOSE-\*) para o corpus MOC** — foram
   calibradas noutro corpus; recall 0 medido no incidente 2026-08-21. E
   "prescrição contradiz medição" **não é gateável**: a medição não existe
   como artefato e o fix plausível (suavizar a prosa) cegaria o gate — fica
   como julgamento.
9. **Regra textual nova exige FP medido antes/depois** — baseline + teste de
   mutação, como a calibração do CLOSE-BLOCK-05 (64% → filtros → 30→4 hits).
   Check que só exige coabitação de linha over-fira por construção.
10. **Registro `*-active.md` acima de ~800 linhas** — gatilho para avaliar
    split de histórico (padrão `split_sprint_history`), **com co-design**: a
    forma "arquivo único, seções `## rN`" foi decidida em [[ADR-343]]; mudar
    exige emenda, não canetada.

---

## 6. Registros `*-active.md` — receitas e forma canônica da correção

> Candidatos `moc-linhas` do coletor (emenda 2026-08-21 da [[ADR-302]]). O
> coletor já entrega, por linha: `anchor`, `disposicao`, `viva`, `lanes`
> (status/`ship_pr` resolvidos **localmente** do frontmatter) e `prs`. A
> fronteira vale para tudo abaixo: **audita-se o registro, nunca o mérito do
> achado** ([[ADR-343]]) — "a lane cobriu mesmo o achado?" é da cadência da
> skill dona.

| Verificar | Como provar |
|---|---|
| **Linha-zumbi** — disposição viva com trilha morta | `lanes` do candidato já traz o status: viva + lane `shipped`/`cancelled` = reportar "reconciliar com a cadência da skill dona". Para `#NNNN` cru (minoria — 16 de 231 linhas medidas em 2026-08-21): `gh pr view <N> --json state,mergedAt`. **Local-first**: o frontmatter da lane resolve offline; `gh` é rede, não-hermético e rate-limited — declare no relatório quando um `403`/timeout deixar linha sem prova |
| **Falso-fechado** — linha terminal cujo fecho não se sustenta | Atestação **barata só**: o PR/SHA citado existe e mergeou; o fecho nomeia predicado (não "resolvido" seco). Sem re-adjudicar mérito. `remediado — fecha por medição no rN+1` **lê como fechado e é obrigação viva**: se o run seguinte não registrou a medição, é finding |
| **Prescrição refutada sem marcador na célula** | A linha prescreve X; medição posterior refutou X. A correção canônica edita **a própria célula**: marcador + `~~riscado~~` sobre a prescrição morta + ponteiro por **id nomeado** (`§Refutação R1`, `§Deferimento D2`) — nunca só nota datada abaixo (quem lê a tabela antes da nota executa a prescrição morta; ponteiro por data é ambíguo — 4 notas dividiam 2026-08-19) |
| **Ponteiro degradado** | Trilha aponta lane/ADR/§ que não existe mais, ou por data em vez de id nomeado |

**Limites medidos (2026-08-21, não afirme cobertura acima disso):** das 231
linhas vivas então medidas, só ~1/3 citava PR ou lane — o resto (`owner: X ·
lane a abrir`) é zumbi de outra natureza, sem nada mecânico a consultar; a
cobertura dele é a cadência anti-zumbi da skill dona, não esta receita. E o
**detector primário** da linha-zumbi é a `lane-closeout` no merge (a camada 2
dela relê os citadores, incluindo `docs/_MOC/*-active.md`); esta skill é a
rede de segurança.
