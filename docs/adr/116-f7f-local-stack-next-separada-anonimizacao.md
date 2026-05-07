---
id: ADR-116
type: adr
title: "F7F-Local: stack Next separada + anonimização default + auth yaml+bcrypt+JWT (F7F-Local)"
status: Decidido
phase: "F7F-Local"
date: "2026-04-22"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 116"]
tags:
  - area/auth
  - area/ops
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 196
---

# ADR-116 — F7F-Local: stack Next separada + anonimização default + auth yaml+bcrypt+JWT (F7F-Local)

**Status:** Decidido (F7F-Local) • **Data:** 2026-04-22

**Contexto:** [BACKLOG §F7F](BACKLOG.md#f7f--console-interno-operadores) divide
console interno em **F7F-Local** (pré-produção, sem OAuth, roda em dev) e
**F7F-Remote** (produção, `ops.mathoms.ai` com OAuth staff + RBAC). Para
destravar F7F-Local, três decisões de design eram bloqueantes: (1) onde mora
a UI web em `127.0.0.1`; (2) o que "excluir usuário" faz por default; (3)
como o operador se autentica sem OAuth. Sem esses três pontos fechados, o
agente de IA-0 trava antes da primeira tela.

Três contextos adicionais importam aqui:

- **A6g.7 Go prep já destravada** ([ADR-113](DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7)): backend
  **pode** virar Go em algum ponto. Acoplar a UI interna ao processo Python
  cria dívida de migração.
- **F7F-Remote precisa consumir a mesma UI** (só troca o gate localhost →
  OAuth). Escolha da stack em F7F-Local reverbera no custo de F7F-Remote.
- **LGPD art. 16 vs art. 18**: esquecimento (art. 18) puxa hard delete;
  conservação para obrigação legal (art. 16) e integridade de audit
  (ADR-115 domain events) puxam anonimização. Precisa default claro + porta
  explícita para hard delete em DSAR.

### Decisão 1 — UI em app Next separada (`frontend-ops/`)

Três alternativas consideradas:

1. **FastAPI + Jinja2 + HTMX no processo backend** — rejeitada. Acopla UI
   à linguagem do backend; se A6g.7 virar migração Go completa, templates
   Jinja precisam ser reescritos (`html/template`). Mesmo com camada de
   serviço preservada, a UI-layer é dívida portável mas não gratuita.
   Blast radius de deploy maior: toda mudança no console pede deploy do
   backend Python.
2. **Rota `/admin/*` no app Next cliente existente** — rejeitada. Expande
   superfície de ataque do `app.mathoms.ai` (rotas admin viram parte do
   bundle JS do cliente); cookie e sessão do cliente dividem domínio com
   ops; gate fora de localhost precisa middleware Next custom. Na
   transição para F7F-Remote, refactor para `ops.mathoms.ai` implica mover
   rotas out-of-process.
3. **App Next separada em `frontend-ops/` consumindo API HTTP** —
   **escolhida**. Processo separado, agnóstico a Python ou Go, blast radius
   isolado, 90% reaproveitado em F7F-Remote (troca só o gate localhost →
   OAuth + RBAC, Traefik já nasce pronto para subdomain próprio). Custo
   inicial de bootstrap ~3-4h a mais.

`frontend-ops/` vive na raiz do repo ao lado de `frontend/` (cliente) e
`backend/`, com seu próprio `package.json`, `next.config.ts`, `Dockerfile`
e rota Traefik (em dev: `127.0.0.1:3100`; em prod F7F-Remote:
`ops.mathoms.ai`). Reusa **design tokens gerados** (`design-tokens/`, ADR-076)
via symlink ou import relativo para não duplicar paleta — mas nada mais.
**Não** importa componentes do `frontend/src/` do cliente (evita
contaminação).

### Decisão 2 — Anonimização como default em exclusão de usuário

Default da operação "excluir usuário" (tarefa `7F.10` no
[BACKLOG](BACKLOG.md#f7f-local--pré-produção-ia-0-sem-oauth)) é
**anonimização**, não hard delete.

Mecânica:

- `users.email` → `deleted_user_<id>@tombstone.mathoms.ai`
- `users.display_name` → `"Conta removida"`
- `users.password_hash` → valor sentinela inválido (bloqueia login em
  qualquer algoritmo)
- `users.anonymized_at` (coluna nova) → timestamp UTC
- Preserva `users.id`, `users.created_at`, e todas as FKs saindo de
  `user_id` (memberships, convites históricos, audit log de ações do
  usuário antes da anonimização)
- **Remove** `refresh_tokens`, `user_sessions` ativas, `invitations`
  pendentes
- **Não remove** `documents`, `pipeline_artifacts`, `reports` — pertencem
  a workspaces, não ao user diretamente. Purge de workspace (`7F.12`) é
  ação separada
- **Workspaces órfãos**: se user anonymized era owner sozinho, workspace
  fica com owner anonymized (estado inativo). Transferir ownership para
  outro admin é operação manual documentada — **não** automática

Hard delete completo (LGPD art. 18 DSAR) fica fora do escopo de IA-0; vive
em `7B.7` (DELETE `/workspace/{id}/artifacts` + cascata) e é invocado por
pedido formal. O serviço `internal_ops.delete_user()` aceita flag
`mode: "anonymize" | "hard_delete"`, default `"anonymize"`; `hard_delete`
exige confirmação extra + audit específico.

Alternativas consideradas:

1. **Hard delete default + flag opt-in para anonimização** — rejeitada.
   Hard delete é irreversível e quebra integridade referencial em audit
   log (ADR-115 domain events presumem `aggregate_id` estável). LGPD art.
   16 permite conservação para obrigação legal — default seguro é
   preservar trilha mínima.
2. **Sem operação na IA-0; delegar para DSAR formal** — rejeitada. CS e
   Legal precisam de ferramenta cotidiana para lidar com pedidos comuns
   (usuário que abandonou o produto, conta duplicada, teste); obrigar
   processo DSAR para cada caso vira fricção operacional.

### Decisão 3 — Auth via yaml + bcrypt + JWT cookie

Middleware `require_internal_operator()` em todas rotas `/admin/*` do
backend + frontend-ops consome cookie httpOnly.

Fluxo:

- `config/internal_operators.yaml` (gitignored; exemplo em
  `config/internal_operators.example.yaml`):
  ```yaml
  operators:
    - email: david@mathoms.ai
      password_hash: "$2b$12$..."   # bcrypt, gerado por scripts/hash_ops_pw.py
      role: superadmin
    - email: ops@mathoms.ai
      password_hash: "$2b$12$..."
      role: ops
  ```
- `POST /admin/login` (backend) com `{email, password}` → `bcrypt.checkpw`
  contra `password_hash` → emite JWT assinado com
  `INTERNAL_OPS_SESSION_SECRET` (env `.env.local`, **distinto** de
  `SECRET_KEY` do JWT cliente) com claims
  `{sub: email, role, exp: now+8h}` → responde com
  `Set-Cookie: ops_session=<jwt>; HttpOnly; Secure; SameSite=Strict; Path=/admin`
- Middleware FastAPI `require_internal_operator()` extrai cookie
  `ops_session`, valida assinatura e `exp`, injeta `operator: Operator`
  em handler. Audit record grava `operator_email` + `operator_role` do JWT
- `POST /admin/logout` limpa o cookie
- `scripts/hash_ops_pw.py` gera hash bcrypt de uma senha interativa
  (prompt, sem echo no shell history)

Alternativas consideradas:

1. **Basic Auth HTTP** — rejeitada. UX ruim (popup do browser, logout
   awkward), credenciais repetidas em cada request, não compõe bem com
   formulários HTMX/Next.
2. **Senha única em `.env.local`** — rejeitada. Não identifica operador
   individual; audit record fica "admin" genérico. Em IA-3 (CS entra),
   distinguir quem fez o quê deixa de ser opcional.
3. **Tabela `internal_operators` em DB + Alembic migration** — rejeitada
   **em IA-0** (adiciona migration a cada agente que entra/sai); adotada
   **em F7F-Remote** com OAuth Google Workspace substituindo
   `password_hash` por allowlist de emails contra payload OAuth. Middleware
   muda ~20 linhas entre IA-0 e F7F-Remote.

### Consequências

- ✅ **Portabilidade de backend**: Go futuro não reescreve a UI do console
  — frontend-ops consome HTTP. Camada de serviço (`backend/app/services/internal_ops/`)
  em Python hoje, migra junto com o resto do backend quando for.
- ✅ **Reaproveitamento IA-0 → F7F-Remote**: ~90% do código do
  `frontend-ops/` serve ops.mathoms.ai. Troca de gate localhost → OAuth
  em ~20 linhas de middleware; Traefik já nasce pronto para subdomain
  próprio.
- ✅ **Isolamento de blast radius**: deploy de `frontend-ops/` nunca
  arrisca `app.mathoms.ai`; superfície de ataque no app cliente não expande.
- ✅ **Trilha de auditoria preservada** (anonimização default)
  compatível com ADR-115 domain events (aggregate_id estável) e LGPD
  art. 16.
- ✅ **Identificação por operador** (yaml + JWT claims) cobre IA-0 e
  prepara IA-3 CS sem refactor.
- ⚠️ **Custo de bootstrap maior** em `7F.L2` (+3-4h: novo `package.json`,
  `next.config.ts`, Dockerfile, rota Traefik dev). Absorvido pela
  economia em F7F-Remote.
- ⚠️ **Duas aplicações Next** no repo (`frontend/` cliente + `frontend-ops/`
  interno). Riscos de drift de versão; política: `frontend-ops/` segue
  `frontend/` na major de Next; design tokens compartilhados via
  `design-tokens/` (ADR-076); zero import de componentes cliente.
- ⚠️ **Workspaces órfãos após anonimização** ficam no DB sem owner ativo.
  Manutenção manual (runbook documenta como transferir ou purgar);
  automação fica para F7F-Remote IA-4.
- ❌ **Hard delete em IA-0 é flag explícita, não default** — operador
  tem que conscientemente pedir `mode="hard_delete"`. Atrito aceito;
  LGPD art. 18 via DSAR formal (7B.7) cobre o caso real.

**Entregue em F7F-Local (7F.L1 + 7F.L2 + 7F.10–7F.14):**

- `backend/app/services/internal_ops/` — camada de serviço compartilhada
  (funções puras + audit record)
- `backend/app/api/admin/` — rotas `/admin/login`, `/admin/logout`,
  `/admin/users/*`, `/admin/workspaces/*`, `/admin/documents/*`,
  `/admin/metrics`, `/admin/reports`
- `backend/app/core/internal_ops_auth.py` — carrega yaml, valida bcrypt,
  emite/valida JWT, middleware `require_internal_operator`
- `frontend-ops/` — app Next separada (bind 127.0.0.1, flag `INTERNAL_OPS_UI_ENABLED`)
- `config/internal_operators.example.yaml` + `scripts/hash_ops_pw.py`
- `logs/internal_ops_audit.log` (sink inicial; quando 7B.5 persistir,
  troca para tabela sem mudar call-sites)

**Artefatos de config:**

- `.env.local.example` ganha `INTERNAL_OPS_UI_ENABLED=1`,
  `INTERNAL_OPS_SESSION_SECRET=<random>`, `INTERNAL_OPS_UI_PORT=3100`
- `config/internal_operators.yaml` no `.gitignore` +
  `dev/check_forbidden_paths.py` ALLOWLIST
- `docker-compose.dev.yml` (ADR-041 Traefik) ganha service `frontend-ops`
  bind em `127.0.0.1:3100`
