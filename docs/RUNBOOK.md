# Mathoms AI — Runbook operacional

> Procedimentos para deploy, incidentes e recuperação. Complementa [SETUP.md](SETUP.md). **Sprint A (2026-04-17):** templates de incidente, status page no app, drill documentado.

---

## 1. Visão geral

| Recurso | Onde |
| --- | --- |
| API + OpenAPI | `MATHOMS_*` em `.env`, uvicorn, ver SETUP |
| Worker | Celery + Redis |
| Frontend | Next.js; variável opcional `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL` |
| Status page pública | Ferramenta externa (ex.: Uptime Kuma, Instatus) — URL configurada no frontend |

---

## 2. Status page (7E.6)

### 2.1 O que monitorar

Componentes sugeridos na ferramenta de status:

- **API** — `GET /health` (ou endpoint dedicado)
- **App web** — página pública mínima (ex.: `/login` retornando 200)
- **Worker / processamento** — health agregado (fila + worker respondendo) ou check sintético
- **Redis** — se expuser health, ou inferido via worker

Incidentes **manuais** na mesma ferramenta quando o problema for conhecido antes do monitor (ex.: degradação percebida internamente).

### 2.2 Link no aplicativo

Definir no build do frontend:

```bash
# frontend/.env.local (não commitar)
NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL=https://status.seudominio.com
```

Com isso, o rodapé de **login**, **cadastro** e **área logada** exibe **“Status e incidentes”** (abre em nova aba). Sem a variável, o link não aparece.

### 2.3 E-mail e suporte

Incluir a URL da status page nos templates de e-mail de boas-vindas quando existirem (tarefa futura).

---

## 3. Resposta a incidentes

### 3.1 Fluxo resumido

1. **Detectar** — alerta, cliente ou dogfood.
2. **Classificar** severidade (`minor` / `major` / `critical`) e áreas afetadas.
3. **Abrir** registro interno (mesmo que planilha) com `INCIDENT_ID`.
4. **Publicar** primeira comunicação na status page usando [initial_report.pt-BR.md](runbooks/incidents/initial_report.pt-BR.md) — alvo **menos de 15 minutos** após detecção interna (ver [SLO.md](SLO.md)).
5. **Atualizar** com [update_in_progress.pt-BR.md](runbooks/incidents/update_in_progress.pt-BR.md) até resolução.
6. **Encerrar** com [resolved_postmortem.pt-BR.md](runbooks/incidents/resolved_postmortem.pt-BR.md).
7. **Post-mortem** interno (opcional em beta; recomendado em GA) — ações de follow-up.

Índice dos templates: [runbooks/incidents/README.md](runbooks/incidents/README.md).

---

## 4. Drill de incidente (obrigatório antes do beta fechado)

Checklist **Sprint A** — execução pode ser em **staging** ou **produção** com incidente claramente marcado como teste.

| # | Passo | Feito |
| --- | --- | --- |
| 1 | Status page acessível e URL configurada em `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL` | ☐ |
| 2 | Criar incidente **fictício** (título ex.: `[DRILL] Teste de processo — ignorar`) | ☐ |
| 3 | Publicar texto baseado em **initial_report** (pode ser cópia do exemplo preenchido) | ☐ |
| 4 | Publicar **update** fictício com template **update_in_progress** | ☐ |
| 5 | Encerrar com **resolved** (template **resolved_postmortem**) | ☐ |
| 6 | Registrar **tempo** da primeira publicação desde o “start” do drill e notas de melhoria abaixo | ☐ |

**Registro do drill (preencher após execução):**

- Data: _______________
- Tempo até primeira publicação (min): _______________
- Notas / melhorias no processo: _______________

---

## 5. Disaster recovery (RPO / RTO)

Valores de referência estão em [SLO.md](SLO.md). Procedimentos de backup, restore e off-site: tarefas **7E.2–7E.4** e [BACKLOG.md](BACKLOG.md#f7--produção--lgpd).

### 5.1 Reset intencional (dev / staging)

Para apagar **toda** a base de utilizadores e ficheiros de tenant (cenário de teste “primeiro utilizador”, base descartável), usar o CLI documentado em [SETUP.md — Reset completo da plataforma](SETUP.md#reset-completo-da-plataforma-cli). **Não** usar em produção com dados reais.

---

## 6. Rotação de segredos e escalação

- **FERNET_KEY**, **JWT secret:** ver SETUP e tarefas F7.
- Escalação: definir contato on-call antes do beta (preencher aqui quando existir).

---

## 7. Console interno local (F7F-Local · IA-0)

Ferramenta web em `127.0.0.1:3100` para operador executar ações de suporte/LGPD
em **dev/staging** antes do produto estar em produção ([ADR-116](DECISIONS.md#adr-116)).
**Não** rodar em produção — bloqueado por flag + bind local.

### 7.1 Arquitetura resumida

| Componente | Local |
| --- | --- |
| UI | `frontend-ops/` (Next app separada, bind `127.0.0.1:3100`) |
| Rotas | `/admin/*` (FastAPI · só monta se `MATHOMS_INTERNAL_OPS_UI_ENABLED=1`) |
| Auth | `config/internal_operators.yaml` (bcrypt) + JWT cookie `ops_session` `httpOnly + SameSite=Strict + Path=/admin`, TTL 8h |
| Segredo de sessão | `MATHOMS_INTERNAL_OPS_SESSION_SECRET` (**distinto** de `MATHOMS_SECRET_KEY` do cliente) |
| Audit | `logs/internal_ops_audit.log` (JSONL, fora de git) |

### 7.2 Subir o stack local

1. **Gerar hash do operador** (senha ≥12 chars):

   ```bash
   python3 scripts/hash_ops_pw.py
   # cole o hash no próximo passo
   ```

2. **Criar `config/internal_operators.yaml`** (gitignored + bloqueado por `dev/check_forbidden_paths.py`):

   ```yaml
   operators:
     - username: superadmin
       hashed_password: "$2b$12$..."
       role: superadmin
   ```

3. **Exportar envs e subir backend** em **porta dedicada `:8001`** (o backend
   principal do dev roda em `:8000` — dois uvicorns convivem no mesmo
   processo/DB, mas só o de `:8001` monta `/admin/*`):

   ```bash
   export MATHOMS_FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   export MATHOMS_INTERNAL_OPS_UI_ENABLED=1
   export MATHOMS_INTERNAL_OPS_SESSION_SECRET="<secret distinto do SECRET_KEY>"
   export MATHOMS_SECRET_KEY="<secret do cliente>"
   export MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(pwd)/mathoms.db"
   uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
   ```

   **Nota:** todas as envs de settings usam prefixo `MATHOMS_` — `DATABASE_URL`
   sem prefixo é ignorado pelo BaseSettings. Se você prefere rodar na `:8000`
   (ex.: quando o backend principal não está ativo), pare o outro processo
   (`kill $(lsof -ti tcp:8000)`) e **remova** o `INTERNAL_OPS_API_BASE` do
   passo 4.

4. **Subir frontend-ops:**

   ```bash
   cd frontend-ops && npm run dev
   # UI em http://127.0.0.1:3100/login
   ```

   O rewrite `/admin/*` → `INTERNAL_OPS_API_BASE` aponta por default para
   `http://127.0.0.1:8001` (ver [`next.config.ts`](../frontend-ops/next.config.ts)).
   Se você rodou o backend de ops em outra porta, exporte
   `INTERNAL_OPS_API_BASE=http://127.0.0.1:<porta>` antes de `npm run dev`.
   Ou via compose: `docker compose -f docker-compose.dev.yml up frontend-ops`.

### 7.3 Operações disponíveis (UI)

Todas gravam linha em `logs/internal_ops_audit.log`:

| Tela | Ações | Audit action |
| --- | --- | --- |
| Usuários | Anonimizar (default, FKs preservadas), Hard delete (superadmin + motivo), Reset senha (16 chars one-time), Editar nome/ativo, **Alterar email** (invalida JWTs), Toggle `is_developer` | `user.anonymize` · `user.hard_delete` · `user.reset_password` · `user.update_profile` · `user.email_changed` · `user.set_developer_flag` |
| Documentos | Purge bulk (user\|workspace scope, preview paginada, rollback em OSError de blob), Delete individual | `document.purge` · `document.delete` |
| Métricas | Dashboard com filtro 7d/30d/90d + export CSV | leitura — sem audit |
| Relatórios | Lista read-only paginada (offset/total) | leitura — sem audit |

**Anonimização é default** — prefira sempre anonymize sobre hard delete. Hard
delete é irreversível e quebra FKs de audit/pipeline.

### 7.4 Rotação de credenciais

- **Senha do operador:** `python3 scripts/hash_ops_pw.py`, substituir hash no
  yaml e reiniciar backend. Sessões ativas continuam válidas até expirar (8h) —
  `/admin/logout` remove o cookie.
- **`MATHOMS_INTERNAL_OPS_SESSION_SECRET`:** rotacionar invalida **todas** as
  sessões de ops ativas (tokens deixam de verificar). Rotacionar pelo menos a
  cada 90d ou após qualquer suspeita de vazamento. **Nunca** reutilizar
  `MATHOMS_SECRET_KEY` (segredo do cliente) — se vazar, um lado compromete o
  outro.
- **Remover operador:** apagar a linha do yaml e reiniciar backend (não há
  soft-delete; o yaml é a fonte única).

### 7.5 Bloqueios de segurança (não bypasses)

- Rotas `/admin/*` só montam se `MATHOMS_INTERNAL_OPS_UI_ENABLED=1` — senão
  retornam 404.
- Backend refusa subir com `ENVIRONMENT=production` + UI habilitada sem a flag
  `--i-accept-production-risk` (ADR-116).
- Bind **deve** ser `127.0.0.1`, nunca `0.0.0.0`. Para expor remotamente é
  outra lane (F7F-Remote com OAuth + RBAC).
- YAML de operadores nunca commitado — bloqueado por `dev/check_forbidden_paths.py`.

### 7.6 Smoke manual

Depois de qualquer mudança em `backend/app/services/internal_ops/`,
`backend/app/api/admin/` ou `frontend-ops/`:

1. Seed user fixture: `python3 scripts/seed_internal_ops_smoke.py` (imprime
   user_id).
2. Subir backend + frontend-ops (passos 7.2).
3. Exercitar 1 fluxo por tela via UI; confirmar entrada no
   `logs/internal_ops_audit.log`.
4. Cleanup: `rm -f mathoms*.db config/internal_operators.yaml logs/internal_ops_audit.log`.

Harness Playwright scaffolded em `frontend-ops/tests/e2e/internal-ops.spec.ts`
(6 tests `@internal-ops`); execução em CI exige instalação do chromium +
global-setup para subir backend seeded.

---

## 8. Referências

- [SLO.md](SLO.md) — SLOs e SLAs de comunicação
- [BACKLOG.md](BACKLOG.md) — 7E (operational readiness) · F7F-Local
- [SMOKE_TEST.md](SMOKE_TEST.md) — verificações manuais pré-release
- [ADR-116](DECISIONS.md#adr-116) — decisões de design F7F-Local
