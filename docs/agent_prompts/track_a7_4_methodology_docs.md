# Track A7.4 — Documentação metodológica → `docs/methodology/`

> **Lane ID:** A7.4
> **Branch prefix:** `agent/a7-4-methodology-docs/*`
> **Depende de:** — (independente; pode rodar em qualquer momento da Sprint A7).
> **Paralelo com:** qualquer lane (zero overlap de arquivos).
> **Conflita com:** qualquer commit ativo em `config/*.md`, `docs/methodology/` (novo), referências em `scripts/e5_analyze.py`/`e7_review.py` (somente comentários).
> **Onda:** 2 (livre — não depende de A7.0).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.4](../CONFIG_CUTOVER_PLAN.md#§54-a74--documentação-metodológica--docsmethodology)
> **ADR:** — (lane docs-only, sem ADR nova).
> **Supervisão CTO:** G3 pré-merge (curto — escopo trivial).

> **Objetivo (1 frase):** mover 4 arquivos de documentação humana de `config/` para `docs/methodology/` + atualizar comentários de scripts que apontam para os paths antigos.

---

## Por que esta lane

`config/definitions.md`, `config/regras_composicao_patrimonial.md`, `config/source_hierarchy.md`, `config/milhas.md` são documentação humana — não são lidos por nenhum parser. Vivem em `config/` por inércia do CLI legado. Mover para `docs/methodology/` esclarece a natureza (metodologia de produto, não config executável).

---

## Regras inegociáveis

1. **`git mv` (preserva histórico)** — não `git rm` + `Write`.
2. **Sem mudança de conteúdo** — apenas reorganização. Edits substantivos viram lane separada.
3. **Atualizar comentários** em scripts que citam paths antigos — efeito puramente cosmético.
4. **Lane docs-only** — pula `pytest`/`npm test` (CLAUDE.md §Git): `pre-commit run --all-files` continua obrigatório.
5. **CHANGELOG entry obrigatório** — ainda que seja docs-only.

---

## Entregáveis (CONFIG_CUTOVER_PLAN.md §5.4)

### Movimentação de arquivos

```bash
mkdir -p docs/methodology
git mv config/definitions.md                       docs/methodology/definitions.md
git mv config/regras_composicao_patrimonial.md     docs/methodology/regras_composicao_patrimonial.md
git mv config/source_hierarchy.md                  docs/methodology/source_hierarchy.md
git mv config/milhas.md                            docs/methodology/milhas.md
```

### Index

`docs/methodology/README.md` — uma linha por arquivo:

```markdown
# Mathoms — Methodology

Documentação humana de produto (regras editoriais, glossário, hierarquia
de fontes). **Não é configuração executável** — nenhum parser lê este
diretório.

- [definitions.md](definitions.md) — glossário de termos do método.
- [regras_composicao_patrimonial.md](regras_composicao_patrimonial.md) — regras determinísticas das 7 categorias do doughnut "Composição Patrimonial".
- [source_hierarchy.md](source_hierarchy.md) — hierarquia de fontes (extrato > config > relatório anterior > estimativa).
- [milhas.md](milhas.md) — método para tratamento de programas de milhagem.
```

### Atualização de comentários

Procurar e substituir referências `config/<arquivo>.md` em scripts (puramente cosmético — não muda runtime):

```bash
grep -rln "config/definitions\.md\|config/regras_composicao_patrimonial\.md\|config/source_hierarchy\.md\|config/milhas\.md" scripts/ pipeline/ backend/
```

Para cada hit, substituir por `docs/methodology/<arquivo>.md`. Tipicamente são 5-10 comentários em `scripts/e5_analyze.py`, `scripts/e7_review.py`, possivelmente `pipeline/domain/services/`.

### CLAUDE.md

Se `CLAUDE.md` cita esses 4 arquivos em `config/`, atualizar para apontar para `docs/methodology/`. Verificar em §Fontes de verdade.

### Limpeza

Após `git mv`, `config/` ainda terá os 7 arquivos restantes (até A7.5). Esta lane **não toca** os outros 7.

---

## Sequência de commits sugerida

```
1. docs(methodology): move definitions + regras + source_hierarchy + milhas to docs/methodology/ (A7.4)
2. docs(methodology): README.md index (A7.4)
3. docs(scripts): update comments referencing config/*.md → docs/methodology/*.md (A7.4)
4. docs(claude): update §Fontes de verdade if needed (A7.4)
5. docs(a7): A7.4 ✅ + CHANGELOG entry
```

---

## Gates de push

Lane docs-only — `pytest` opcional, mas `pre-commit` obrigatório:

```bash
pre-commit run --all-files
grep -rn "config/definitions\.md\|config/regras_composicao_patrimonial\.md\|config/source_hierarchy\.md\|config/milhas\.md" .
# ↑ deve retornar 0 hits fora de docs/methodology/, .git/, _archive/
```

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.4)

- [ ] 4 arquivos movidos com `git mv` (histórico preservado) ✓
- [ ] `docs/methodology/README.md` index criado ✓
- [ ] Comentários em scripts atualizados ✓
- [ ] CLAUDE.md atualizado se necessário ✓
- [ ] `grep -rn "config/<arquivo>.md"` = 0 hits em código produtivo ✓
- [ ] CTO G3 ✅ (revisão rápida — escopo trivial)

---

## O que NÃO entrega

- Edição de conteúdo dos 4 arquivos (vira lane separada se necessário).
- Modelagem de "milhas" como entidade `MileageProgram` (CONFIG_CUTOVER_PLAN.md §1 sugere; fica fora de A7).
- Movimentação de `decisions.md` (é A7.2a — cliente, não metodologia).
- Movimentação de outros `.md` em `config/` (não há outros — `methodology.md` e `report_spec.md` em `config/` são produto interno e ficam para A7.5).

---

## Coordenação com outros agentes

- **Pode rodar em qualquer momento.** Não bloqueia nem é bloqueada por nenhuma outra lane A7.
- **Pickup ideal:** sessão curta (≤30min), sem necessidade de contexto profundo.
- **Hotspot:** `CLAUDE.md` se §Fontes de verdade precisar editar — protocolo §Hotspots de documentação.

---

## Rollback

`git revert` reverte os movs. Histórico preservado em ambas as direções.

---

## Estimativa

~30 minutos – 1 sessão.
