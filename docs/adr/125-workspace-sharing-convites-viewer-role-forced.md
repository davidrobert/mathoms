---
id: ADR-125
type: adr
title: "Workspace sharing: convites, viewer role, forced logout"
status: Decidido
phase: "F9"
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 125"]
tags:
  - area/multitenancy
  - status/decidido
  - type/adr
size_lines: 52
---

# ADR-125 — Workspace sharing: convites, viewer role, forced logout

> Renumerado de ADR-078 (duplicata) em 2026-04-24 para resolver colisão com
> ADR-078 "Render Nativo React + E6 como Exportador Standalone" (linha ~1396).
> O conteúdo abaixo é o original; referências externas ao antigo "ADR-078
> (workspace sharing)" devem migrar para ADR-125.

**Status:** Decidido (F9) • **Data:** 2026-04-15

**Contexto:** Dados financeiros familiares precisam ser compartilhados entre
membros da mesma família (casal, filhos adultos) e, no futuro, com
consultores financeiros. ADR-072 criou a infraestrutura de multi-tenancy
(`WorkspaceMember` com roles owner/member), mas não cobria o fluxo de
convite, o papel read-only, nem a invalidação de sessão ao remover um
membro. F9 endereça esses 3 gaps.

**Decisão:**

1. **3 roles fixos** (`owner`, `member`, `viewer`) com sets de conveniência
   (`WRITE_ROLES`, `MEMBER_ADMIN_ROLES`). Roles customizadas e escopos
   parciais (ex: "contador vê transações mas não metas") ficam como débito
   explícito.
2. **Convite por link copiável** (sem provider de email no V1). Backend gera
   token aleatório 256-bit, armazena `SHA-256(token)`, retorna token cru uma
   vez. Owner envia o link manualmente.
3. **`WorkspaceInvitation`** como entidade separada de `WorkspaceMember` —
   token + TTL 72h + uso único + revogável. Convite aceito cria membership.
4. **`require_role(allowed)` factory** em `tenancy.py` como dependency FastAPI.
   Reutiliza `workspace_member` já carregado por `get_current_workspace` (zero
   query extra). Pré-instanciados: `require_write_role`, `require_member_admin_role`.
5. **`User.token_version`** — claim `tv` no JWT. Incrementado ao remover membro.
   `get_current_user` rejeita tokens stale com `code: "token_revoked"` → frontend
   detecta e redireciona para login.
6. **Reuso de `AuditLog`** existente — sem tabela nova. Ações de membership usam
   convenção de naming (`workspace.member.invite`, `.accept`, `.remove`, etc).
7. **Default de role no convite: `viewer`** — upgrade para `member` é explícito.
   Convite como `owner` é bloqueado. Transferência de ownership é débito.
8. **Nomenclatura UI em PT-BR** — "Responsável" / "Coadministrador" / "Acompanha"
   (não "Owner/Admin/Viewer").

**Consequências:**

- ✅ Fluxo completo convite → aceite → membership funcional sem provider externo.
- ✅ Viewer read-only com enforcement duplo (backend 403 + frontend UI guards).
- ✅ Forced logout imediato ao remover membro — sem janela de exposição.
- ✅ 39 testes + tenancy lint cobrem a feature end-to-end.
- ⚠️ Convite manual (copiar link) é friction — email automático é F9.8.
- ⚠️ `token_version` bump invalida TODAS as sessões do user, não só a do workspace removido. Aceitável porque o user faz login de novo e acessa seus outros workspaces normalmente.
- ❌ Sem escopos parciais — um viewer vê tudo (metas, transações, patrimônio). Primeiro cliente consultor vai pedir isso.
- ❌ Sem transferência de ownership — bloqueado explicitamente nos services com mensagem clara.
