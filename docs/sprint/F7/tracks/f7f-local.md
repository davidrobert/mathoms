---
id: TRACK-f7f-local
type: track
title: "Track F7F-Local — Console interno pré-produção (IA-0)"
sprint: F7
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/f7
  - status/consumed
---

# Track F7F-Local — Console interno pré-produção (IA-0)

> **Lane ID:** F7F-Local
> **Branch prefix:** `agent/f7f-local/*`
> **Depende de:** nada (greenfield; independente de F7A/B/C)
> **Paralelo com:** qualquer lane da Onda 2 e Onda 3 — zero overlap de arquivos se respeitar escopo abaixo
> **Conflita com:** qualquer commit ativo em `backend/app/services/internal_ops/`, `backend/app/api/admin/`, `backend/app/core/internal_ops_auth.py`, `frontend-ops/`, `config/internal_operators*.yaml`, `scripts/hash_ops_pw.py`
> **Onda:** 3 (Lane C6 — INDEPENDENTE de 7A/B/C)
> **Objetivo (1 frase):** entregar console interno local (UI web em `127.0.0.1`) para operador executar exclusão de conta (anonimização), purge de documentos, reset de senha, leitura de relatórios e métricas antes do produto estar em produção, sem OAuth staff.
> **Fonte de verdade:** [CLAUDE.md §Code style](../../../../CLAUDE.md#code-style), [ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local), [INTERNAL_ADMIN_ROADMAP.md §IA-0](../../../plan/INTERNAL_ADMIN/_README.md)

---

## Por que este slice agora

F7F-Local (IA-0) é **ferramenta que o operador precisa antes do produto estar no ar** — exclusão de conta para testes, purge de documentos indevidos, reset de senha em dev/staging. Sem ela, operador vira dependente de SQL ad hoc (risco alto, sem audit).

**Não espera F7A/B/C.** Roda em dev/staging, consome backend + DB local. Quando F7A estabilizar, a mesma UI vira base de `ops.mathoms.ai` (F7F-Remote) com troca de ~20 linhas de middleware (localhost → OAuth).

**UI-first, CLI secundário.** Decisão em [ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local): superfície principal é Next separada em `frontend-ops/` (agnóstica a Python/Go no futuro, blast radius isolado, 90% reaproveitado em F7F-Remote). CLI (`7F.9`) entra **depois** da UI estabilizada, reutilizando a mesma camada de serviço.

---

## Regras inegociáveis

Do CLAUDE.md + ADRs:

1. **Camada de serviço é fonte de verdade** ([ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local) Decisão 1): `backend/app/services/internal_ops/` tem funções puras; UI e CLI futuro **consomem** — nunca duplicam regra de negócio.
2. **Anonimização é default** ([ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local) Decisão 2): `delete_user(user_id, mode="anonymize")`. `mode="hard_delete"` existe mas **nunca é default**, exige confirmação extra. Integridade de FKs preservada (ADR-115 domain events dependem de `aggregate_id` estável).
3. **Auth por yaml + bcrypt + JWT httpOnly** ([ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local) Decisão 3): `config/internal_operators.yaml` (gitignored) + `POST /admin/login` emite JWT assinado com `INTERNAL_OPS_SESSION_SECRET` (distinto do `SECRET_KEY` cliente) + cookie `ops_session` com `Path=/admin`. Zero reuso de sessão do cliente.
4. **Bind em `127.0.0.1`** (nunca `0.0.0.0`). Habilitado por `INTERNAL_OPS_UI_ENABLED=1` (default off). Bloqueia se `ENVIRONMENT=production` sem `--i-accept-production-risk`.
5. **Stateless rigoroso** ([ADR-111](../../../DECISIONS.md#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6)): `internal_ops` service sem cache in-memory mutável, sem counter global. Audit vai para `logs/internal_ops_audit.log` (sink trocável para `AuditEntry` quando 7B.5 persistir).
6. **Dinheiro nunca é `float`** ([ADR-090](../../../DECISIONS.md)): métricas de cobrança usam `Decimal`/`Money`. Agregações monetárias no dashboard também.
7. **Funções 4-20 linhas, arquivos ≤500, nomes específicos** (§Code style). Nomes: `AnonymizeUserCommand`, `PurgeDocumentsService`, não `UserHandler`/`DocUtils`.
8. **TypeScript sem `any`** ([ADR-102 R14](../../../DECISIONS.md)): `frontend-ops/` segue mesmas regras do `frontend/` cliente — zero `any`, tipos do codegen como fonte de verdade.
9. **Endpoint JSON novo → `response_model` + `make update-openapi-snapshot`** ([ADR-102 R18](../../../DECISIONS.md)). Rotas `/admin/*` entram no snapshot normalmente (não há motivo para esconder contrato interno).
10. **Preserve comentários existentes** em qualquer arquivo refatorado.
11. **Paths proibidos** — `config/internal_operators.yaml` entra no `.gitignore` + ALLOWLIST de `dev/check_forbidden_paths.py` (o arquivo **não** pode ser commitado; só `.example`).
12. **Idioma:** código/APIs/vars em inglês; UI texto em pt-BR (operadores são internos, time fala português).
13. **Dados sensíveis:** nunca logue senha (nem mascarada), CPF, ou valor monetário total em logs INFO. ADR-110 masking aplica.

---

## Estado atual — arquivos que este slice introduz

Todos greenfield, zero conflito com outras lanes se o escopo for respeitado:

| Arquivo | Propósito |
|---|---|
| `backend/app/services/internal_ops/__init__.py` | Expõe funções públicas do serviço |
| `backend/app/services/internal_ops/anonymize_user.py` | `anonymize_user(db, user_id) -> OpResult` |
| `backend/app/services/internal_ops/hard_delete_user.py` | `hard_delete_user(db, user_id) -> OpResult` (não-default) |
| `backend/app/services/internal_ops/reset_password.py` | `reset_password(db, user_id, new_pw) -> OpResult` |
| `backend/app/services/internal_ops/purge_documents.py` | `purge_documents(db, scope) -> OpResult` |
| `backend/app/services/internal_ops/metrics.py` | `get_metrics(db, period) -> MetricsSnapshot` |
| `backend/app/services/internal_ops/list_reports.py` | `list_reports(db, filter) -> list[ReportSummary]` |
| `backend/app/services/internal_ops/audit.py` | `AuditRecord`, `append_audit(record)` (sink: file/DB) |
| `backend/app/core/internal_ops_auth.py` | Load yaml, bcrypt verify, JWT emit/verify, `require_internal_operator` middleware |
| `backend/app/api/admin/__init__.py` | Router agregador `/admin/*` |
| `backend/app/api/admin/login.py` | `POST /admin/login`, `POST /admin/logout` |
| `backend/app/api/admin/users.py` | `GET /admin/users`, `POST /admin/users/{id}/anonymize`, `POST /admin/users/{id}/reset-password` |
| `backend/app/api/admin/documents.py` | `POST /admin/documents/purge` (preview + confirm) |
| `backend/app/api/admin/metrics.py` | `GET /admin/metrics` (MVP; 7E.7 expande depois) |
| `backend/app/api/admin/reports.py` | `GET /admin/reports?user_id=&workspace_id=` |
| `backend/app/schemas/admin.py` | DTOs `AdminLoginRequest`, `AnonymizeUserRequest`, `MetricsSnapshot`, etc. |
| `backend/tests/internal_ops/` | Unit tests + integration tests para cada serviço |
| `backend/tests/api/admin/` | Tests 401/403 + happy path por rota |
| `frontend-ops/package.json` | App Next separada, deps mínimas |
| `frontend-ops/next.config.ts` | Config Next, standalone output, bind `127.0.0.1:3100` |
| `frontend-ops/src/app/login/page.tsx` | Tela de login |
| `frontend-ops/src/app/(admin)/layout.tsx` | Layout autenticado + nav |
| `frontend-ops/src/app/(admin)/users/page.tsx` | Lista + busca + ações (anonimizar, reset senha) |
| `frontend-ops/src/app/(admin)/documents/page.tsx` | Purge com preview |
| `frontend-ops/src/app/(admin)/metrics/page.tsx` | Dashboard simples |
| `frontend-ops/src/app/(admin)/reports/page.tsx` | Lista read-only |
| `frontend-ops/src/lib/api.ts` | Client HTTP tipado para `/admin/*` |
| `frontend-ops/Dockerfile` | Multi-stage Next standalone |
| `config/internal_operators.example.yaml` | Template commitável |
| `scripts/hash_ops_pw.py` | Gera bcrypt interativo |
| `docker-compose.dev.yml` | Service `frontend-ops` bind 127.0.0.1:3100 (se já existir; senão adicionar em F7A.3) |

**Total estimado:** ~2500 linhas de código novo. 3-4 sessões longas se seguir a sequência abaixo.

---

## Sequência de commits sugerida

### Slice 1 — Camada de serviço + auth backend (7F.L1 + parte de 7F.L2)

**Meta:** backend expõe `/admin/login` + CRUD mínimo de ops; testes verdes antes de qualquer UI.

1. **S1.a** `backend/app/services/internal_ops/` com `anonymize_user` + `hard_delete_user` + `audit` module (audit vai para `logs/internal_ops_audit.log` em JSON). Unit tests em `backend/tests/internal_ops/`.
2. **S1.b** `backend/app/services/internal_ops/` completo (`reset_password`, `purge_documents`, `delete_document`, `set_developer_flag`, `update_user_email`, `update_user_profile`, `metrics`, `list_reports`). Mutações sensíveis (email, flag dev) bumpam `User.token_version` para invalidar JWTs. Unit tests cobrindo colisão de email + invalidação de sessão.
3. **S1.c** `backend/app/core/internal_ops_auth.py` — carrega yaml, bcrypt verify, emite/valida JWT com `INTERNAL_OPS_SESSION_SECRET`, middleware `require_internal_operator`. Unit tests.
4. **S1.d** `scripts/hash_ops_pw.py` (bcrypt interativo, sem echo) + `config/internal_operators.example.yaml` + entrada em `.gitignore` + ALLOWLIST em `dev/check_forbidden_paths.py`.
5. **S1.e** `backend/app/api/admin/login.py` + `users.py` + `documents.py` + `metrics.py` + `reports.py`. Tests de 401/403 + happy path. `make update-openapi-snapshot`.
6. **S1.f** Flag `INTERNAL_OPS_UI_ENABLED` em `backend/app/core/config.py` — rotas `/admin/*` só montam se flag é `True`; senão retornam 404. Bloqueio se `ENVIRONMENT=production` sem `INTERNAL_OPS_ACCEPT_PRODUCTION_RISK=1`.

**Gate S1:** `pytest backend/tests/internal_ops/ backend/tests/api/admin/ -q` verde; `make update-openapi-snapshot` sem diff não-intencional; `dev/check_forbidden_paths.py` passa.

### Slice 2 — Frontend-ops app Next (parte de 7F.L2)

**Meta:** app Next separada consumindo APIs do Slice 1.

1. **S2.a** Bootstrap `frontend-ops/` — `package.json`, `next.config.ts` (standalone + bind `127.0.0.1:3100`), `tsconfig.json`, Tailwind config reusando `design-tokens/` (symlink ou relative import; **zero import** de `frontend/src/`). `Dockerfile` multi-stage.
2. **S2.b** Login page + layout autenticado — chama `POST /admin/login`, armazena cookie via Set-Cookie, redireciona. Middleware Next protege rotas `(admin)/*`.
3. **S2.c** Tela **Usuários** — lista + filtro por email, ações "Anonimizar" (confirmação dupla com `TYPE "delete"`), "Reset senha" (gera senha temporária copiável), "Editar cadastro" (email/full_name/is_active), toggle `is_developer`.
4. **S2.d** Tela **Documentos** — purge com modo "prévia" (lista arquivos/linhas) antes de confirmar; exclusão individual por linha na listagem de documentos do usuário/workspace.
5. **S2.e** Tela **Métricas** — cards + tabela (uploads/runs/workspaces/volume storage); export CSV como botão secundário.
6. **S2.f** Tela **Relatórios** — lista read-only filtrada por email/`user_id`; link abre JSON/HTML em aba separada.
7. **S2.g** `docker-compose.dev.yml` — service `frontend-ops` em `127.0.0.1:3100` (se já existir compose; senão documenta que F7A.3 vai incluir).

**Gate S2:** `cd frontend-ops && npm run lint && npm run build` verde; smoke manual local (iniciar backend + frontend-ops, logar, executar uma anonimização em usuário de fixture); `docs/reference/RUNBOOK.md` atualizado com URL/flag/rotação.

### Slice 3 — 7F.10–7F.17 (refino das telas por área)

Slice 2 entrega shell + tela por área; Slice 3 refina business logic específica (hard delete gate, ownership órfão, edge cases de purge). Este slice **só começa após S1+S2 mergeados** — reduz área de conflito.

1. **S3.a — 7F.10:** polimento de anonimização + modal para `mode="hard_delete"` com confirmação reforçada (motivo obrigatório registrado no audit).
2. **S3.b — 7F.11:** reset de senha com geração de senha forte (16 chars), display one-time copiável, invalidação de refresh_tokens.
3. **S3.c — 7F.12:** purge de documentos com scope switch (user vs workspace), preview paginada, rollback se qualquer blob falhar no storage.
4. **S3.d — 7F.13:** dashboard de métricas com filtro de período (7d/30d/90d); cache in-process **proibido** (ADR-111), usa query direto.
5. **S3.e — 7F.14:** lista de relatórios com paginação + filtro `needs_review`.
6. **S3.f — 7F.15:** toggle `is_developer` na tela de edição do usuário; confirmação simples (ação reversível); substitui [set_developer_flag.py](../../../../backend/app/scripts/set_developer_flag.py) manual.
7. **S3.g — 7F.16:** form de edição de cadastro (email/full_name/is_active); validação de unicidade de email; bump de `token_version` em mudança de email + audit separado para campo sensível.
8. **S3.h — 7F.17:** exclusão individual de documento a partir da lista (separado do purge bulk de 7F.12); confirmação simples; audit inclui hash/nome do arquivo.

**Gate S3:** tests Playwright `@internal-ops` básicos (login + 1 operação por área); checkpoint F7F-Local fechado.

### Slice 4 — 7F.9 CLI secundário (opcional, pós-UI)

**Só comece** se demanda concreta de automação aparecer (purge agendado, exclusão em lote via script). CLI reutiliza `backend/app/services/internal_ops/` **sem** duplicar regra.

1. `backend/app/scripts/internal_ops.py` — Click ou Typer, comandos `anonymize-user`, `purge-documents`, `metrics-dump`.
2. Mesma audit trail que a UI (`logs/internal_ops_audit.log`).
3. `--dry-run` default em ações destrutivas.

---

## Gates de push

Antes de push para `main` (CLAUDE.md §Git):

```bash
# 1. Hooks
pre-commit run --all-files

# 2. Backend tests
pytest backend/tests/internal_ops/ backend/tests/api/admin/ -q
pytest backend/tests -q              # zero regressão em outros módulos

# 3. Pipeline tests (não deve quebrar — internal_ops não toca pipeline/)
pytest tests -q

# 4. Frontend-ops (quando Slice 2 fechar)
cd frontend-ops && npm run lint && npm run build && cd ..

# 5. OpenAPI sync
make update-openapi-snapshot
git diff backend/tests/api/openapi_snapshot.json  # verificar intencional

# 6. Pre-push drift check
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main)
[ "$BEHIND" -eq 0 ] || { git rebase origin/main; pytest backend/tests -q; }

# 7. Boundaries
python3 dev/check_pipeline_boundaries.py
python3 dev/check_forbidden_paths.py
python3 dev/check_forbidden_names.py
```

**Qualquer falha → não faz push.** Fix-forward antes.

---

## Checklist de pronto (F7F-Local MVP)

- [ ] `7F.L1` — `backend/app/services/internal_ops/` com módulos para anonymize/hard_delete/reset_password/purge_documents/delete_document/set_developer_flag/update_user_email/update_user_profile/metrics/list_reports + tests verdes (cobertura ≥85% em internal_ops/).
- [ ] `7F.L2` parte backend — `/admin/*` routes + auth yaml+bcrypt+JWT + flag `INTERNAL_OPS_UI_ENABLED` + smoke manual verde.
- [ ] `7F.L2` parte frontend — `frontend-ops/` app Next separada, build limpo, login + 1 ação por área funciona localmente.
- [ ] `7F.10` — anonimização default testada (user anonymized não consegue logar, FKs preservadas, audit gravado); hard delete exige mode explícito.
- [ ] `7F.11` — reset senha via UI, invalidação de refresh_tokens testada.
- [ ] `7F.12` — purge com preview funcionando; blob storage + DB em sync após confirm.
- [ ] `7F.13` — dashboard mostra métricas reais; export CSV funciona.
- [ ] `7F.14` — lista de relatórios read-only acessível, sem mutação.
- [ ] `7F.15` — toggle `is_developer` funcional via UI; audit gravado.
- [ ] `7F.16` — editar email/full_name/is_active; mudança de email bumpa `token_version` e invalida JWTs existentes; colisão de email retorna 409.
- [ ] `7F.17` — exclusão individual de documento funciona; blob + DB em sync; audit grava hash/nome do arquivo.
- [ ] `docker-compose.dev.yml` ou `README.md` documenta como subir `frontend-ops` em `127.0.0.1:3100`.
- [ ] `docs/reference/RUNBOOK.md` seção "Console interno local" — como adicionar operador (gerar bcrypt + editar yaml), rotação de credenciais, bloqueio em produção.
- [ ] `config/internal_operators.yaml` no `.gitignore` + ALLOWLIST de `dev/check_forbidden_paths.py` + `.example` commitado.
- [ ] `.env.local.example` ganha `INTERNAL_OPS_UI_ENABLED`, `INTERNAL_OPS_SESSION_SECRET`, `INTERNAL_OPS_UI_PORT`.
- [ ] OpenAPI snapshot atualizado.
- [ ] 0 regressão em `pytest backend/tests -q` e `pytest tests -q`.
- [ ] Checkpoint F7F-Local fechado no BACKLOG; CHANGELOG atualizado.
- [ ] 7F.9 (CLI) fica em ☐ aberto — não bloqueia encerramento da fase.

---

## Rollback criteria — ABORTE se

- `pytest backend/tests -q` baseline cai em qualquer módulo fora de `internal_ops/api/admin/`.
- `dev/check_pipeline_boundaries.py` quebra (você importou algo errado).
- `dev/check_forbidden_paths.py` bloqueia — `internal_operators.yaml` foi commitado por engano ou `.env.local` vazou.
- `dev/check_forbidden_names.py` falha — arquivo genérico (`user_utils.py`, `DocumentHandler.ts`).
- Rotas `/admin/*` aparecem quando `INTERNAL_OPS_UI_ENABLED=0` (falha de gate).
- `anonymize_user` apaga `user.id` ou quebra FK em `audit_entries`/`pipeline_artifacts`.
- JWT `ops_session` é aceito pelo middleware de auth do **cliente** (`get_current_user`) — breach de isolamento.
- Cookie `ops_session` sem `HttpOnly` ou sem `SameSite=Strict` em resposta de login.
- Qualquer campo de senha aparece em log (nem mascarado).

Em rollback: commitar tudo em branch, anunciar, abrir issue e voltar para `origin/main` limpo.

---

## Anti-patterns a evitar

- **Duplicar regra de anonimização** na UI ou no CLI. `anonymize_user()` vive em `internal_ops/`, pontos de consumo **chamam**, nunca reimplementam.
- **Cookie de sessão sem Path=/admin.** Se vazar para `/`, pode confundir com sessão do cliente em dev multi-domain.
- **Reutilizar `SECRET_KEY` do JWT cliente.** `INTERNAL_OPS_SESSION_SECRET` é variável separada, obrigatória, sem fallback para `SECRET_KEY`.
- **Hard delete como default** em qualquer ponto do código. `mode="hard_delete"` é **sempre** explícito, nunca inferido.
- **Importar componentes de `frontend/src/`** em `frontend-ops/src/`. Só compartilhamento é `design-tokens/` (paleta gerada). Componentes duplicados se necessário.
- **`any` em `frontend-ops/`** — mesma regra do cliente (ADR-102 R14).
- **Cache in-memory** no backend `/admin/*` — stateless rigoroso (ADR-111). Se precisar cache de métricas, use Redis (mas em IA-0 query direto é suficiente).
- **`float` em agregados de valor monetário** no dashboard — `Decimal`/`Money` (ADR-090).
- **Smoke test "clique e vê"** sem teste automatizado de 401/403 nas rotas. Cada rota `/admin/*` tem teste de: (a) sem cookie → 401; (b) com cookie inválido → 401; (c) com cookie expirado → 401; (d) com role insuficiente (se for o caso) → 403.
- **Commits misturando slices.** Cada S1.a/S1.b/... é commit separado; PR pode agregar mas o histórico mantém granularidade para rollback cirúrgico.

---

## Coordenação com outros agentes

F7F-Local é **greenfield** — arquivos novos em paths não tocados por outras lanes. Riscos:

- **A6e.4 thin routers** — pode renomear arquivos em `backend/app/api/`. Coordene: se A6e.4 tiver edit ativo em `backend/app/api/__init__.py` (agregador de routers), espere seu commit mergear antes de registrar o router `admin` lá.
- **A6g.6 enforcement** — pode apertar regras de ruff/ESLint. Se escopo ficar mais strict durante seu trabalho, aplique na próxima PR, não durante.
- **F7A Docker** — se rodar em paralelo, F7A.3 (`docker-compose.dev.yml`) pode entrar em conflito com sua adição do service `frontend-ops`. Coordene no commit de `docker-compose.dev.yml`: se F7A.3 já commitou, rebase e adicione service; senão, seu commit adiciona o service e F7A.3 herda.

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- docs/CHANGELOG.md docs/BACKLOG.md docs/DECISIONS.md
```

Se agente mergeou hotspot <30min, espere 2min, anuncie, commite docs no **mesmo turno** (≤5min).

**Sync periódico (sessão >1h):** rode `git fetch origin && git log HEAD..origin/main` a cada 30min. Se `CLAUDE.md` ou `ADR-116` mudarem, releia antes de continuar.

---

## O que NÃO entrega (fora de escopo)

- **OAuth Google Workspace** — é F7F-Remote (`7F.2`), não IA-0.
- **RBAC múltiplos papéis** granular — IA-0 usa só `role: superadmin` e `role: ops` como string livre no yaml; matriz de permissões fica para `7F.3`.
- **`/api/internal/*` prefix** — é F7F-Remote (`7F.4`); IA-0 usa `/admin/*` simples sob flag.
- **Dashboard de custo LLM por run** — é `7E.12`; IA-0 `7F.13` só mostra métricas básicas.
- **Support bundle JSON redigido** — é `7F.7`; IA-0 não precisa, operadores têm acesso direto ao DB local.
- **Persistir audit em tabela** — sink inicial é `logs/internal_ops_audit.log`; troca para `AuditEntry` quando `7B.5` fechar.
- **Traefik `ipAllowList`** — é F7F-Remote (`7A.7b`); IA-0 só precisa bind 127.0.0.1.
- **Teste cookie leakage** — é F7F-Remote (`7A.11b`); IA-0 testa isolamento de cookie via unit test de middleware.
- **CLI** — é `7F.9`, opcional pós-UI. Se não entregar, não bloqueia fechamento da fase.

---

## Referências

- [ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local) — decisões de design F7F-Local (stack, anonimização, auth)
- [ADR-111](../../../DECISIONS.md#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6) — stateless rigoroso
- [ADR-110](../../../DECISIONS.md#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3) — structured logs + masking
- [ADR-109](../../../DECISIONS.md#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a) — auth portability + OpenAPI snapshot
- [ADR-102](../../../DECISIONS.md#adr-102--princípios-r18-r20-language-neutral-boundaries-a6f) — language-neutral boundaries (R18 `response_model`, R14 no `any`)
- [ADR-090](../../../DECISIONS.md) — Dinheiro nunca é `float`
- [ADR-076](../../../DECISIONS.md) — Design tokens (compartilhados entre `frontend/` e `frontend-ops/`)
- [ADR-115](../../../DECISIONS.md#adr-115--domain-events-tipados-arquitetura-e-boundaries-a6eevents) — Domain events (FKs preservadas em anonimização)
- [INTERNAL_ADMIN_ROADMAP.md §IA-0](../../../plan/INTERNAL_ADMIN/_README.md) — narrativa da fase
- [BACKLOG §F7F-Local](../../../BACKLOG.md#f7f-local--pré-produção-ia-0-sem-oauth) — tasks estimáveis
- [CLAUDE.md §Code style](../../../../CLAUDE.md#code-style) — regras de código
- [CLAUDE.md §Git](../../../../CLAUDE.md#git-e-commits) — protocolo de commits/push
