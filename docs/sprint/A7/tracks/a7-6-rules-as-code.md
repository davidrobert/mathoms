---
id: TRACK-a7-6-rules-as-code
type: track
title: "Track A7.6 — Rules-as-code: dissolver `docs/methodology/`"
sprint: A7
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a7
  - status/consumed
---

# Track A7.6 — Rules-as-code: dissolver `docs/methodology/`

> **Lane ID:** A7.6
> **Branch prefix:** `agent/a7-6-rules-as-code/*`
> **Depende de:** A7.4 ✅ mergeada (arquivos atualmente em `docs/methodology/`).
> **Coordena com:** A7.2a (Decision aggregate), A7.2b (fiscal/market), A7.3 (catalog/override). Nenhum overlap de arquivos esperado, mas conceitualmente A7.3 redefine taxonomia de categorias e A7.2a captura algumas "decisões" hoje em `definitions.md`.
> **Conflita com:** qualquer commit ativo em `docs/methodology/**`, `pipeline/domain/services/{cash_flow_builder,income_origin_resolver}.py`, `scripts/e5_analyze.py::parse_milhas_md`.
> **Onda:** 2.5 (paralelo a Onda 2 mas com gate G1 pendente — ADRs precisam ser mergeadas antes de codar).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.6](../../../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md#§56-a76--rules-as-code-dissolver-docsmethodology).
> **ADRs novas (gate G1):** ADR-143 (`docs/methodology/` é rules-as-code), ADR-145 (composição patrimonial canonical 7-bucket), ADR-146 (E3 source hierarchy), ADR-147 (milhas valuation + storage workspace-scoped).
> **Supervisão CTO:** G1 (ADR draft) **antes** de tocar código · G2 (schema review p/ migrator de milhas) · G3 (PR pré-merge).

> **Objetivo (1 frase):** eliminar o diretório `docs/methodology/` movendo regras universais de produto para docstrings + ADRs no código que enforce, e dados cliente-específicos para DB ou `storage/<workspace_id>/notes/` (gitignored).

---

## Por que esta lane

A A7.4 (mergeada) moveu 4 arquivos de `config/` → `docs/methodology/` mas a movimentação preservou um vício do CLI mono-cliente: cada arquivo mistura **regras universais de produto** (as 7 categorias da composição patrimonial, hierarquia de fontes, método de valuation de milhas) com **instâncias cliente-específicas do workspace piloto** (David, Mariana, Rua Exemplo, Hashdex, valores BRL reais, contas Itaú/BTG).

**Auditoria pós-A7.4** confirmou:

| Arquivo | Linhas | Hits cliente-específicos | Onde a regra universal vive (ou viveria) |
|---|---|---|---|
| `definitions.md` | 505 | 59 | DB schema (`FamilyMember`, `BankAccount`, `Category`) + glossário em `docs/reference/ARCHITECTURE.md` |
| `regras_composicao_patrimonial.md` | 234 | 19 + valores BRL | Função classificadora em `pipeline/domain/services/cash_flow_builder.py` (ou similar) |
| `source_hierarchy.md` | 150 | 19 | `pipeline/domain/services/income_origin_resolver.py` |
| `milhas.md` | 95 | 5 | `scripts/e5_analyze.py::parse_milhas_md` (lê o markdown em runtime — anti-padrão) |

**Problemas concretos:**
- **CLAUDE.md §Regras críticas violado:** "nunca expor valores monetários reais" + "nomes de família" em commit público.
- **Drift garantido:** quando a regra muda no código, o markdown fica desatualizado.
- **`milhas.md` é DUAS COISAS ao mesmo tempo:** doc humano + fonte de dados runtime parseada por `parse_milhas_md`. Anti-padrão clássico.
- **Não generaliza:** o produto Mathoms vai ter N clientes; cada um exige seu próprio "definitions" e "regras". O modelo "1 markdown global" não escala.

**Princípio adotado (conforme decisão David, 2026-04-27):** product methodology IS the code. Documentar separadamente cria drift. Eliminar `docs/methodology/` força a referência única (código + ADR para o "porquê").

---

## Regras inegociáveis

1. **CLAUDE.md §Regras críticas (PII):** nenhum dado cliente-específico vai para `docs/`. Nomes/valores BRL/contas migram para DB ou `storage/<ws>/notes/` (gitignored).
2. **Pipeline não importa SQLAlchemy/FastAPI:** se uma regra precisa de DB read em runtime, o caminho é via `ConfigStore` Protocol (já existe pós A7.0).
3. **Stateless rigoroso (ADR-111):** sem `@lru_cache` para regras hot-path; cache via Redis se necessário.
4. **Money nunca é float (ADR-090):** valores em `int64` cents OR `Money` Pydantic.
5. **Funções 4-20 linhas, módulos ≤500 linhas.**
6. **Smoke E2E verde após cada commit** — não merge intermediário com pipeline quebrado.
7. **Bridges com prazo:** se for necessário ler `docs/methodology/` durante a transição (pouco provável), a leitura emite `DeprecationWarning` + log estruturado e tem data de remoção.
8. **G1 obrigatório:** as 4 ADRs (139–142) devem estar em status **Decidido** em `docs/DECISIONS.md` antes de qualquer commit de código. Lane sem ADR mergeada = lane bloqueada.

---

## Sub-tasks (1 ADR + 1 commit por arquivo)

### Sub-task 0 — ADRs (gate G1, **antes** de qualquer código)

Drafts em `docs/DECISIONS.md` (status: Proposto → Decidido após CTO sign-off):

- **ADR-143 — `docs/methodology/` é rules-as-code:** justifica eliminação do diretório, regra geral "product methodology IS the code".
- **ADR-145 — 7 categorias canonical da composição patrimonial:** Residência própria, Imóveis investimento, Investimentos Titular, Investimentos Cônjuge, Criptoativos, Caixa + Moeda Estrangeira, Veículos. Regras de classificação (Hashdex é fundo FIC FIM ⇒ Investimentos, não Crypto). Premissa "exatamente 2 membros (titular + cônjuge)" é assumption do produto — documentar; expansão para N membros é tema futuro.
- **ADR-146 — E3 source hierarchy:** prioridade canônica (LLM extraction > extrato > fatura > dedução). Workspace-specific banco→tier vai para DB (`BankAccount.source_tier` ou similar — confirmar com schema review G2).
- **ADR-147 — Milhas: valuation methodology + storage workspace-scoped:** método de valuation (universal, ADR) + dados workspace-specific migrados de `docs/methodology/milhas.md` para `storage/<workspace_id>/notes/milhas.md` (gitignored). `parse_milhas_md` migra para ler do novo path. Migrator one-shot copia o conteúdo atual para o workspace piloto. Modelagem de `MileageProgram` como entidade DB fica fora deste escopo (potencial Sprint A8+).

**CTO sign-off** em cada ADR antes de prosseguir. Use `Agent(subagent_type="senior-cto", ...)` se humano não disponível.

### Sub-task 1 — `definitions.md` → DB schema reference + ARCHITECTURE.md glossary

Status: a maior parte do conteúdo **duplica DB schema** (membros, instituições, categorias, contas bancárias). A migração é principalmente de exclusão.

1. Mapear cada seção de `definitions.md` para uma das fontes:
   - DB models (`FamilyMember`, `BankAccount`, `Institution*`, `Category*`, etc.) — referenciar via `docs/reference/DB_SCHEMA_REFERENCE.md`.
   - Enum docstrings (papéis: titular/conjuge/dependente/etc.) — docstring na coluna `FamilyMember.role`.
   - Convenções de naming/path do pipeline — já estão em CLAUDE.md §Convenções.
   - **Conteúdo cliente-específico** (David's Itaú, valores) — descartar (já está em DB/BankAccount rows).
2. Adicionar seção curta em `docs/reference/ARCHITECTURE.md` (e.g., §"Domain glossary") com 1 parágrafo + links para DB schema + link para ADR-143 (regra geral) e ADR-145/146 (especificidades).
3. `git rm docs/methodology/definitions.md`.
4. Atualizar referências em `CLAUDE.md §Fontes de verdade` e `docs/agent_prompts/*` (A7.4 já atualizou alguns; reauditar com grep).
5. Tests: nenhum runtime impacto (definitions.md não é parseada). Confirmar via `grep -rn 'definitions\.md' pipeline/ scripts/ backend/` retorna zero hits após cleanup.

Commit: `docs(a7.6): definitions.md → DB schema ref + ARCHITECTURE glossary (ADR-143/145)`.

### Sub-task 2 — `regras_composicao_patrimonial.md` → docstring no classifier + ADR-145

Status: as 7 categorias são enforced em algum ponto do pipeline E4/E5. Identificar e migrar.

1. **Mapeamento:** localizar a função/classe que classifica ativos em buckets de composição patrimonial. Candidatos:
   - `pipeline/domain/services/cash_flow_builder.py` (provavelmente sim — `CashFlow.composicao` ou similar).
   - `pipeline/domain/services/investments_consolidator.py` (categoriza investimentos).
   - `scripts/e5_analyze.py::analyze_patrimonio` (compõe o output S1 do relatório).
   - Use `Agent(subagent_type="Explore", ...)` para mapear precisamente.
2. **Migração de regras:** docstring na função classificadora documenta as 7 categorias + tabela "tipo X → bucket Y" (sem valores BRL, sem nomes). Referência ADR-145 ("ver ADR-145 para o porquê dessas 7 categorias").
3. **Casos especiais (Hashdex, contas bancárias com `Aplicacao RDB/CDP`, etc.):** essas regras de matching ficam no docstring da função + cobertas por testes unitários com fixtures. **Nomes/valores reais NÃO entram nos testes** — usar fixtures genéricas (`FundoExemplo`, `BancoExemplo`).
4. `git rm docs/methodology/regras_composicao_patrimonial.md`.
5. Tests: golden de paridade E4/E5 (se houver) deve regenerar **idêntico** ao baseline pré-cutover (regra é a mesma, só mudou de lugar).
6. Atualizar referências em comentários `# Source: docs/methodology/regras_composicao...` → `# Source: ADR-145`.

Commit: `refactor(pipeline): regras composição patrimonial → docstring + ADR-145`.

### Sub-task 3 — `source_hierarchy.md` → docstring no resolver + ADR-146

Status: similar à anterior. A regra é universal (LLM > extrato > fatura > dedução); workspace-specific banco→tier vai para DB.

1. **Mapeamento:** localizar `pipeline/domain/services/income_origin_resolver.py` (mencionado em mapping anterior). Confirmar é o consumidor.
2. **Migração:**
   - Docstring na função/classe documentando a hierarquia universal (lista priorizada de fontes).
   - Workspace-specific (banco X é tier 1 para reconciliação) — verificar se já está em `BankAccount.source_tier` (column nova) ou se precisa schema migration. **Schema review G2 com CTO antes de migration.**
3. `git rm docs/methodology/source_hierarchy.md`.
4. Tests: golden E3 deve continuar verde.
5. Atualizar referências em scripts/e3_reconcile.py + tests.

Commit: `refactor(pipeline): source hierarchy → docstring + ADR-146 (+ workspace tier em BankAccount)`.

### Sub-task 4 — `milhas.md` → `storage/<ws>/notes/milhas.md` + docstring + ADR-147

Status: **mais complexa** das 4 porque envolve runtime migration de path.

1. **Migrar `parse_milhas_md(workspace_root)`** em `scripts/e5_analyze.py`:
   - Antes: lê de `<workspace>/docs/methodology/milhas.md` (path atual pós-A7.4).
   - Depois: lê de `<workspace>/storage/<ws_id>/notes/milhas.md` (workspace-scoped) — ou via `ctx.load_config("milhas.md")` se usar overrides A7.1.
   - Bridge transitório: se path novo não existe, fallback para path antigo + `DeprecationWarning`. Bridge removido em A7.5 cleanup.
2. **Migrator one-shot** (`dev/migrate_milhas_to_workspace_storage.py`):
   - Copia `docs/methodology/milhas.md` (ou `_archive/` se já moved) para `storage/<workspace_id>/notes/milhas.md` no workspace piloto.
   - Idempotente: skip se path destino já existe.
   - CLI flag `--workspace-id`.
   - Não generalizar — script descartável.
3. **Docstring + ADR-147:**
   - Universal valuation methodology (como avaliar 1 ponto de cada programa) → docstring em `parse_milhas_md` + ADR-147.
   - Notas culturais ("Smiles tem valor X em campanhas Y") → ADR-147 ou descartar (são timing-bound, não invariantes de produto).
4. **Forbidden paths:** `dev/check_forbidden_paths.py` ganha bloqueio para `storage/` em git (já tem provavelmente — confirmar) e para `docs/methodology/milhas.md` (já tem após A7.4).
5. **Sanity:** `gitignore` cobre `storage/<ws>/notes/`? Confirmar.
6. Após verificação visual no workspace piloto: `git rm docs/methodology/milhas.md`.

Commit: `feat(pipeline): milhas migra para storage/<ws>/notes/ + docstring + ADR-147`.

### Sub-task 5 — `README.md` + delete dir + forbidden paths

1. `git rm docs/methodology/README.md` (após sub-tasks 1-4 todos mergeados).
2. `rmdir docs/methodology/` se vazio.
3. **`dev/check_forbidden_paths.py`:** adiciona `docs/methodology/` à lista de paths proibidos (não pode ser recriado por engano).
4. **`CLAUDE.md`:** atualizar §Fontes de verdade — remover qualquer referência a `docs/methodology/`. Adicionar parágrafo curto em §Regras críticas: "Methodology = code. Nada em `docs/methodology/` (path proibido). Regras universais vivem em docstrings + ADRs; dados cliente em DB ou `storage/<ws>/notes/`."
5. **`docs/agent_prompts/`:** grep por `methodology` e atualizar referências (A7.4 fez parcial; reauditar).

Commit: `chore: remove docs/methodology/ + bloqueia path em forbidden_paths (A7.6 final)`.

### Sub-task 6 — Documentação Sprint A7

1. `docs/CONFIG_CUTOVER_PLAN.md`:
   - §1 sumário executivo: tabela ganha coluna refletindo destino real (3 dos 4 mds dissolvem em rules-as-code; milhas vai workspace-scoped).
   - §5.4: nota retrospectiva — A7.4 movimentou, A7.6 dissolveu.
   - §5.6 (esta lane): marcar ✅ entregue + commits + ADRs.
   - §10 checklist: A7.6 ✅.
2. `docs/CHANGELOG.md`: entrada A7.6 ✅ no estilo das anteriores (commits + ADRs + acceptance gates batidos).
3. `docs/BACKLOG.md`: A7.6 ✅; status global atualizado.

Commit: `docs(a7.6): ✅ entregue — rules-as-code dissolve docs/methodology/`.

---

## Sequência de commits sugerida (após G1)

1. `docs(adr): ADR-143 + 140 + 141 + 142 (Decidido) — gate G1 A7.6` (CTO sign-off em PR review).
2. `refactor(pipeline): regras composição patrimonial → docstring + ADR-145` (Sub-task 2).
3. `refactor(pipeline): source hierarchy → docstring + ADR-146` (Sub-task 3).
4. `feat(pipeline): milhas migra para storage/<ws>/notes/ + ADR-147` (Sub-task 4) — inclui migrator + bridge + tests.
5. `docs(a7.6): definitions.md → DB schema ref + ARCHITECTURE glossary (ADR-143/140)` (Sub-task 1, depois das outras pq referencia ADRs já mergeadas).
6. `chore: remove docs/methodology/ + bloqueia path em forbidden_paths` (Sub-task 5).
7. `docs(a7.6): ✅ entregue — rules-as-code dissolve docs/methodology/` (Sub-task 6).

Após cada commit: rebase em `origin/main`, `pytest backend/tests` + `pytest tests` verdes, push.

---

## Acceptance gates ([CONFIG_CUTOVER_PLAN.md §5.6](../../../archive/CONFIG_CUTOVER_PLAN-2026-04-27.md))

- [ ] ADRs 139-142 status **Decidido** em `docs/DECISIONS.md`.
- [ ] `find docs/methodology/ -type f` → empty (ou diretório deletado).
- [ ] `dev/check_forbidden_paths.py` bloqueia `docs/methodology/**`.
- [ ] `grep -rn "David\|Mariana\|Rua Exemplo\|Praça Exemplo\|Itaú Personnalité\|Hashdex" docs/` → zero hits (fora de git history).
- [ ] `grep -rn "docs/methodology/" .` → zero hits (excluindo `_archive/`, git history, esta track file, e CHANGELOG retrospectivo).
- [ ] `pytest tests -q` 1495+ passed (E3/E4/E5/E5.N goldens paridade preservada).
- [ ] `pytest backend/tests -q` 1350+ passed.
- [ ] `dev/check_pipeline_boundaries.py` verde.
- [ ] `dev/check_code_style_regression.py` sem regressão (P1/P7/P8/P9).
- [ ] CLAUDE.md atualizado (Fontes de verdade + Regras críticas).
- [ ] Workspace piloto: relatório gera identicamente (smoke shadow se F7 prod).
- [ ] CTO G3 ✅ pré-merge.

---

## Riscos

- **`parse_milhas_md` runtime breakage:** se path novo não popula antes do path antigo deletar, card de milhas no relatório fica vazio. Mitigação: bridge com fallback warned + migrator roda **antes** do `git rm`.
- **Schema migration para `BankAccount.source_tier`:** se ADR-146 exigir column nova, requer Alembic migration backwards-compat (add nullable + populate + flip — nunca DROP no mesmo PR).
- **Goldens drift silencioso:** se mudança de docstring/ADR alterar comportamento sutilmente (improvável; é só doc), goldens E4/E5 detectam.
- **Outros agentes paralelos (A7.2a, A7.2b, A7.3):** podem tocar tabelas/services adjacentes. Coordenar via `docs/CHANGELOG.md` `[Unreleased]` antes de mexer em hot files.
- **`milhas.md` storage workspace-scoped:** primeiro arquivo "notes" workspace-scoped do produto. Se ainda não há padrão, ADR-147 estabelece o padrão para futuros arquivos similares.

---

## O que NÃO entrega

- Modelagem de `MileageProgram` como entidade DB (potencial Sprint A8+).
- N membros (>2): premissa "titular + cônjuge" é product invariant aqui; expansão é tema futuro.
- Migração para Sprint A7 de `parametros_fiscais.json` / `taxas.json` — A7.2b.
- `decisions.md` — A7.2a.

---

## Coordenação

- **A7.2a (paralela):** toca `backend/app/{models/decision,application/decisions}` + frontend `PlanoDeAcao`. Você toca pipeline domain services + ADRs + docs. Zero overlap de arquivos.
- **A7.2b (paralela):** toca `backend/app/{models/fiscal_parameter,models/market_rate}` + `pipeline/domain/services/{previdencia,cenarios}_*`. Você toca cash_flow_builder/income_origin_resolver/parse_milhas. Zero overlap esperado.
- **A7.3 (Onda 3 — destravada por A7.1):** toca categorization/institutions split. Coordenar conceitualmente: definitions.md tem seções sobre categorias/instituições que A7.3 vai substituir via DB. Possivelmente `definitions.md` cleanup (sub-task 1) deveria esperar A7.3 mergear primeiro. **Decisão recomendada:** dependência soft de A7.3 — sub-task 1 deste lane fica por último, depois de A7.3.
- **Hotspots cross-lane:** `docs/{BACKLOG.md, CHANGELOG.md, DECISIONS.md, CONFIG_CUTOVER_PLAN.md, ARCHITECTURE.md}`. Aplicar protocolo CLAUDE.md §Hotspots (anunciar, ≤5min commit+push).

---

## Estimativa

~3-4 sessões de 2h. Maior que A7.4 porque:
- 4 ADRs draft + CTO sign-off (G1) consomem ~1 sessão sozinhas.
- Mapeamento "qual função enforce qual regra" requer Explore.
- `milhas.md` migration runtime + migrator one-shot + bridge.
- Re-auditoria de referências em scripts/agents/docs.

---

## Rollback

`git revert` por sub-task. Cada sub-task é commit atômico com seu próprio escopo. Bridge transitório (especialmente em sub-task 4) facilita rollback parcial.
