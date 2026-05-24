# Contribuindo com Mathoms AI

Obrigado pelo interesse. Este guia cobre o **fluxo prático**.
Convenções de código, regras de domínio e arquitetura vivem em
[`CLAUDE.md`](../CLAUDE.md) (raiz) e [`docs/`](../docs/).

---

## Setup rápido

Ver [`docs/reference/SETUP.md`](../docs/reference/SETUP.md) para instalação completa
(Python 3.11+, Node 18+, Redis 7+, pre-commit hooks). DB em dev é SQLite por
default; Postgres é opcional (necessário só para CI/produção).

```bash
git clone https://github.com/davidrobert/mathoms.git
cd mathoms
pip install pre-commit
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
pre-commit install --hook-type pre-push
```

---

## Fluxo de PR (quem pode mergear)

1. **Crie uma branch** descritiva: `<tipo>/<slug-curto>` para humanos
   (`fix/saldo-inicial-nan`) ou `agent/<slug>/<yyyyMMdd-HHmm>` para
   agentes LLM (ver [CLAUDE.md §Git e commits](../CLAUDE.md)).
2. **Commits coesos** seguindo Conventional Commits — uma mudança lógica
   por commit. Validado por `dev/validate_commit_msg.py` no `commit-msg`
   hook. Exemplos:
   - `feat(api): adiciona endpoint /v1/reports/export`
   - `fix(pipeline): aborta E3 quando saldo inicial vem como NaN`
   - `refactor(frontend): extrai ReportSection de Report.tsx`
3. **Rode os gates locais antes do push**:
   ```bash
   pre-commit run --all-files
   pytest tests -q
   pytest backend/tests -q
   cd frontend && npm test -- --run
   ```
   Se mexeu em fluxos `@critical`: `npm run test:e2e`.

   Exceção: PR exclusivamente em `docs/**` ou `*.md` pode pular pytest/npm
   (mas pre-commit segue obrigatório).
4. **Abra o PR** contra `main`. O título do PR vira commit message no
   squash-merge — siga Conventional Commits aqui também (job
   `Title (Conventional Commits)` valida).
5. **Preencha o template** — checklist + ADR + breaking change quando
   aplicável.
6. **CI tem que ficar verde** — job `All checks green` é gate obrigatório.
7. **Auto-merge** (`gh pr merge <N> --squash --auto` ou botão na UI) é o
   caminho default. Habilitar auto-merge ainda **opt-in por você** quando
   achar que o PR está pronto — esse gesto também serve de sinal para o
   workflow `auto-update-prs.yml` (ver seção abaixo) manter a branch
   sincronizada com `main` automaticamente.

---

## Auto-update de branches de PR

O repo usa o workflow `.github/workflows/auto-update-prs.yml` para evitar
o ciclo manual `rebase → push → esperar CI → repetir porque outro PR
mergeou` em picos com múltiplos PRs paralelos.

**Mecânica:**

1. Você (ou um agente) abre PR, deixa verde, roda
   `gh pr merge <N> --squash --auto`.
2. Outro PR mergea em `main`.
3. O workflow `Auto-update PR branches` dispara em `push: main`, lista
   todos os PRs **com auto-merge habilitado**, e chama o endpoint
   `update-branch` da GitHub API em cada um.
4. GitHub atualiza a branch da PR (merge de `main` na branch — o
   squash-merge final em `main` continua produzindo histórico linear).
5. Novo CI run dispara automaticamente; quando fica verde, auto-merge
   faz o squash em `main`.

**Filtro:** o workflow usa `PR_FILTER: "auto_merge"` — só PRs com
auto-merge habilitado entram. PRs em draft, sem `--auto`, ou marcados
com label `wip` / `do-not-merge` / `blocked` são ignorados. Não precisa
label manual; o gesto de "habilitar auto-merge" já é o sinal de intent.

**Por que não Merge Queue?** Merge Queue do GitHub exige repo em
**Organization com Enterprise Cloud**. Este repo é privado em conta
pessoal (User), tier que não destrava a feature. Os triggers
`merge_group:` em `ci.yml` e `pr-quality.yml` ficam **dormentes** —
inofensivos hoje, e prontos caso o repo migre para Organization no
futuro.

**Implicações operacionais:**

- Em conflito de merge, o workflow `Auto-update PR branches` falha o
  step (visível em Actions). Resolução é manual no PR específico.
- Forçar rodada sem aguardar próximo `push: main`: botão "Run workflow"
  em Actions → `Auto-update PR branches` → `workflow_dispatch`.

---

## Boas práticas

- **PRs pequenos > grandes.** PR > 600 linhas (`size:XL`) deve ter
  justificativa. Ver CLAUDE.md §Git e commits sobre split de commits.
- **Bug fix vem com teste de regressão escrito ANTES do fix.** TDD para
  bugs é defesa contra regressão.
- **Sem dado sensível** em diff/logs/fixtures — CPF, valores reais,
  conteúdo de extrato/fatura. Hooks de pre-commit bloqueiam, mas
  responsabilidade primária é sua.
- **ADR para decisão arquitetural não-trivial.** Ver
  [`docs/_MOC/_generated/ADR_INDEX.md`](../docs/_MOC/_generated/ADR_INDEX.md) —
  notas atômicas em `docs/adr/NNN-slug.md` (ADR-182). Gates rodados via pre-commit.
- **Endpoint JSON novo/alterado** → `make update-openapi-snapshot` e
  comite o snapshot.

---

## Issues

- **Bug**: use o template `🐛 Bug report`. Anonimize CPF/valores reais.
- **Feature**: use o template `✨ Feature / melhoria`. Antes, veja se já
  está em [`docs/_MOC/SPRINTS-active.md`](../docs/_MOC/SPRINTS-active.md).
- **Vulnerabilidade de segurança**: **não abra issue pública**. Siga
  [`SECURITY.md`](../SECURITY.md).

---

## Para agentes LLM

[`CLAUDE.md`](../CLAUDE.md) é o briefing canônico. Respeite:

- Branches `agent/<slug>/<yyyyMMdd-HHmm>` (timestamp evita colisão).
- Pre-flight obrigatório antes de pegar lane: `git fetch origin` +
  `git worktree list` + `git for-each-ref refs/remotes/origin/agent/`.
- Commits WIP antes de devolver turno (regra defensiva contra resets).
- Hotspots de doc (`CLAUDE.md`, `CHANGELOG.md`, `BACKLOG.md`,
  `DECISIONS.md`) — anuncie antes de editar; commit + push no mesmo turno.

---

## Estrutura útil

| Para...                                     | Veja                                            |
| ------------------------------------------- | ----------------------------------------------- |
| Stack, modelo de dados, stages do pipeline  | `docs/reference/ARCHITECTURE.md`                |
| Sprint atual + lanes ready                  | `docs/_MOC/SPRINTS-active.md`                   |
| Roadmap macro (fases)                       | `docs/reference/PHASES.md`                      |
| Decisões arquiteturais (ADRs)               | `docs/_MOC/_generated/ADR_INDEX.md`             |
| Setup dev local                             | `docs/reference/SETUP.md`                       |
| Operações em prod (runbook)                 | `docs/reference/RUNBOOK.md`                     |
| Entregas últimos 14 dias                    | `docs/_MOC/_generated/CHANGELOG_RECENT.md`      |
| Convenções de código + domínio              | `CLAUDE.md`                                     |
