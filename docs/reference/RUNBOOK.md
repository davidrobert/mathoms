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

Valores de referência estão em [SLO.md](SLO.md). Procedimentos de backup, restore e off-site: tarefas **7E.2–7E.4** e [BACKLOG.md](../BACKLOG.md#f7--produção--lgpd).

**Rollback do cutover [[ADR-212]] (pipeline DB-only):** procedimento dedicado em
[runbooks/pipeline_rollback.md](runbooks/pipeline_rollback.md) — janela ~30min
RTO via snapshot DB pré-deploy + revert PR + downgrade migration.

### 5.1 Reset intencional (dev / staging)

Para apagar **toda** a base de utilizadores e ficheiros de tenant (cenário de teste “primeiro utilizador”, base descartável), usar o CLI documentado em [SETUP.md — Reset completo da plataforma](SETUP.md#reset-completo-da-plataforma-cli). **Não** usar em produção com dados reais.

### 5.2 Rollback de seed de `category_template`

Ao reverter migration que inseriu nova `template_version` (`alembic downgrade <ver>`),
o `downgrade()` **DEVE** chamar `category_cache.invalidate_latest_template_version()`
explicitamente. Sem isso, cache Redis fica stale por até 15min (TTL) e a API
responde com `latest_template_version` apontando para a versão revertida.

```python
from backend.app.services.storage import category_cache

def downgrade():
    op.execute("DELETE FROM category_templates WHERE template_version = N")
    category_cache.invalidate_latest_template_version()
```

Verificar no `downgrade()` da migration alvo **antes** de aplicar.

### 5.3 Workspace cleanup (single-tenant cleanup)

Pré-produção, Mathoms roda single-tenant (apenas `5@5.com`). Workspaces
residuais de smoke runs / fixtures E2E / contas de teste antigas acumulam
no DB e geram drift em queries de admin/dashboard. Para zerar essa cauda
preservando apenas a keep list:

```bash
# 1. Dry-run (sem efeito) — confirma o que será deletado:
python3 dev/purge_test_workspaces.py

# 2. Backup do DB ANTES do apply (responsabilidade do operador):
cp mathoms.db mathoms.db.bak-$(date +%Y%m%d-%H%M)

# 3. Apply destrutivo — exige confirmação interativa "DELETE-ALL":
python3 dev/purge_test_workspaces.py --apply

# 4. Apply + remove storage/<workspace_id>/ em disco (uploads + inbox + audit files):
python3 dev/purge_test_workspaces.py --apply --include-blob-store

# 5. Customizar keep list (cumulativo; aceita múltiplos --keep):
python3 dev/purge_test_workspaces.py --keep 5@5.com --keep admin@mathoms.ai
```

Caveats:

- **Irreversível.** Backup do DB antes de `--apply` é responsabilidade do
  operador — o script não cria snapshot automático.
- Remove workspaces, pipeline_artifacts (onde vivem as transactions
  reconciliadas), overrides, rules, reports, audits, decisões (Plano de
  Ação · ADR-136), tasks, documentos, membros/convites, password vault,
  configs per-workspace, e usuários órfãos (owners cujos workspaces foram
  todos deletados E que não têm membership em workspace preservado).
- **Não** afeta config global: `category_template`, `institution_catalog`,
  `fiscal_parameters`, `market_rates`, `alembic_version`.
- **Não** dropa colunas/FKs/tabelas — schema permanece intacto.
- **Não** roda em CI; script ad-hoc para ops pré-produção.
- Defense in depth: `--apply` ativa `PRAGMA foreign_keys=ON` e exige
  confirmação digitada `DELETE-ALL` no prompt (impossível disparar
  acidentalmente em script automatizado sem TTY).

Quando o produto virar multi-tenant esse script deixa de fazer sentido —
neste ponto a operação canônica passa a ser soft-delete por workspace
(`Workspace.deleted_at` + janitor job de 30 dias · ADR-072). Marcar como
obsoleto e arquivar quando essa transição acontecer.

---

## 6. Rotação de segredos e escalação

- **FERNET_KEY**, **JWT secret:** ver SETUP e tarefas F7.
- Escalação: definir contato on-call antes do beta (preencher aqui quando existir).

---

## 7. Console interno local (F7F-Local · IA-0)

Ferramenta web em `127.0.0.1:3100` para operador executar ações de suporte/LGPD
em **dev/staging** antes do produto estar em produção ([ADR-116](../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local)).
**Não** rodar em produção — bloqueado por flag + bind local.

### 7.1 Arquitetura resumida

| Componente | Local |
| --- | --- |
| UI | `frontend-ops/` (Next app separada, bind `127.0.0.1:3100`) |
| Rotas | `/admin/*` (FastAPI · só monta se `MATHOMS_INTERNAL_OPS_UI_ENABLED=1`) |
| Auth | `config/internal_operators.yaml` (bcrypt) + JWT cookie `ops_session` `httpOnly + SameSite=Strict + Path=/admin`, TTL 8h |
| Segredo de sessão | `MATHOMS_INTERNAL_OPS_SESSION_SECRET` (**distinto** de `MATHOMS_SECRET_KEY` do cliente) |
| Audit | tabela `internal_ops_audit` (ADR-309 · A31.l1) — mesma transação da operação; `GET /admin/audit` lê |

### 7.2 Subir o stack local

1. **Gerar hash do operador** (senha ≥6 chars em dev; use ≥12 fora de localhost):

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
   `http://127.0.0.1:8001` (ver [`next.config.ts`](../../frontend-ops/next.config.ts)).
   Se você rodou o backend de ops em outra porta, exporte
   `INTERNAL_OPS_API_BASE=http://127.0.0.1:<porta>` antes de `npm run dev`.
   Ou via compose: `docker compose -f docker-compose.dev.yml up frontend-ops`.

### 7.3 Operações disponíveis (UI)

Todas gravam registro na tabela `internal_ops_audit` (ADR-309 — audit na
mesma transação da operação; rollback leva os dois; login/logout usam
escrita autônoma):

| Tela | Ações | Audit action |
| --- | --- | --- |
| Usuários | Anonimizar (default, FKs preservadas), Hard delete (superadmin + motivo), Reset senha (16 chars one-time), Editar nome/ativo, **Alterar email** (invalida JWTs), Toggle `is_developer` | `user.anonymize` · `user.hard_delete` · `user.reset_password` · `user.update_profile` · `user.email_changed` · `user.set_developer_flag` |
| Documentos | Purge bulk (user\|workspace scope, preview paginada, rollback em OSError de blob), Delete individual | `document.purge` · `document.delete` |
| Métricas | Dashboard com filtro 7d/30d/90d + export CSV; **Custo LLM por workspace** (mês-calendário UTC, mesma janela do hard-stop ADR-173) com **Editar cap** (mostra status resultante antes de confirmar) e **Remover cap** (confirmação dupla; NULL = sem teto); **Degradação de etapas** (ADR-357 — ver cadência abaixo) | `workspace.update_llm_budget` (edição) · leitura sem audit |
| Relatórios | Lista read-only paginada (offset/total) | leitura — sem audit |

**Anonimização é default** — prefira sempre anonymize sobre hard delete. Hard
delete é irreversível e quebra FKs de audit/pipeline.

**Desbloquear budget LLM (hard-stop ADR-173):** Métricas → Custo LLM por
workspace → Editar cap. O modal mostra gasto do mês + status resultante do
novo cap (com gasto $5.57, cap $6 ainda fica em warn). Não use SQL direto —
a edição via UI gera audit. A janela reseta na virada do mês-calendário UTC.

**Workspace órfão:** anonimizar o único owner deixa o workspace sem dono
ativo (estado inativo, dados preservados). Transferir ownership para outro
admin é operação **manual** (SQL/console) — não há automação em IA-0
(ADR-116; automação fica para F7F-Remote IA-4).

**Degradação de etapas — cadência semanal (ADR-357 · A40.l18).** Um add-on
advisory da cauda do pipeline (parecer, narrativas, cross-validation) pode não
entregar sem derrubar o run: o relatório é gerado e a lacuna fica declarada
(`partial_failure`). O card existe porque a alternativa — só log estruturado — é
o modo de falha que produziu o incidente de origem: **9 dias sem detecção**
(ADR-304 §Emenda). Card que ninguém abre tem o mesmo modo de falha, com sintaxe
melhor; esta casa já perdeu 45 dias de nightly desligado sem notar.

Olhe **1×/semana**, em Métricas → *Degradação de etapas* (30d), três números:

1. **Taxa sobre runs.** Contagem sozinha não sustenta threshold — 4 em 200 e 4 em
   5 são mundos diferentes. Acima de ~10% investigue.
2. **Por motivo.** `unknown` acima de ~20% do total significa que o mapeamento de
   `reason_class` não cobre os tipos reais — e toda a copy client-facing da
   A40.l20 fica construída em cima de moeda ao ar. Revise
   `backend/app/services/pipeline/stage_failure_reason.py`.
3. **Por etapa.** `review_finances_holistic` degradando é visível ao cliente
   premium e custa API; `validate_cross` é grátis e invisível. A etapa decide se o
   próximo passo é olhar o provider ou o código.

Não fecha com *Runs por desfecho*: um run pode degradar várias etapas, e run longo
cruza a janela. As duas âncoras são deliberadamente diferentes
(`PipelineStageLog.started_at` vs `PipelineRun.started_at`).

Alerta automático (burn-rate) depende do Sentry, que é OWNER-GATED (ADR-228 G4).
Até lá esta leitura semanal **é** o controle.

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
- Backend refusa subir com `ENVIRONMENT=production` + UI habilitada sem
  `MATHOMS_INTERNAL_OPS_ACCEPT_PRODUCTION_RISK=1` explícito (ADR-116;
  guard em [`backend/app/main.py`](../../backend/app/main.py)).
- Bind **deve** ser `127.0.0.1`, nunca `0.0.0.0`. Para expor remotamente é
  outra lane (F7F-Remote com OAuth + RBAC).
- YAML de operadores nunca commitado — bloqueado por `dev/check_forbidden_paths.py`.
- **Audit imutável (ADR-309):** em Postgres, o deploy que aplica a migration
  `a31l1opsaudit` deve rodar com `MATHOMS_DB_APP_ROLE=<role_da_app>` no env —
  a migration executa `REVOKE UPDATE, DELETE` (grant INSERT+SELECT). Sem o
  env, aplicar o REVOKE manualmente após o upgrade.
- **Log CRITICAL `mathoms.internal_ops.audit` ("audit sink failure")** =
  escrita autônoma de audit (login/logout) falhou e a operação abortou —
  tratar como page: ou o DB caiu (console inteiro afetado) ou há bug no path
  de audit bloqueando logins. O sink transacional não emite esse log — falha
  vira 500 + rollback da operação.
- Arquivo legado `logs/internal_ops_audit.log`: renomear para
  `internal_ops_audit.log.pre-7b5` e manter ≥30 dias como arquivo-morto
  (sem backfill — ADR-309 D6; linha `audit.migration` na tabela marca o corte).

### 7.6 Smoke manual

Depois de qualquer mudança em `backend/app/services/internal_ops/`,
`backend/app/api/admin/` ou `frontend-ops/`:

1. Seed user fixture: `python3 scripts/seed_internal_ops_smoke.py` (imprime
   user_id).
2. Subir backend + frontend-ops (passos 7.2).
3. Exercitar 1 fluxo por tela via UI; confirmar entrada em `GET /admin/audit`
   (tabela `internal_ops_audit`).
4. Cleanup: `rm -f mathoms*.db config/internal_operators.yaml`.

Harness Playwright scaffolded em `frontend-ops/tests/e2e/internal-ops.spec.ts`
(6 tests `@internal-ops`); execução em CI exige instalação do chromium +
global-setup para subir backend seeded.

---

## 8. Debug da rota `/reports/[id]` (Report Premium v1)

> Shell React `/reports/[id]` é o **único** renderer do relatório
> ([ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side));
> PDF server-side via Playwright é o único export. Renderer HTML
> standalone foi removido — não procure por `e6_render.py`, ele não
> existe mais.

### 8.1 Abrir o relatório em dev

```bash
# Backend + worker + Redis (se já não rodando)
docker compose up -d redis
uvicorn backend.app.main:app --reload --port 8000
# em outra aba:
celery -A backend.app.worker worker -l info
# em outra aba:
cd frontend && npm run dev   # http://localhost:3000
```

Login → seleciona workspace que tem ao menos 1 run completa (até E5).
`/reports` lista relatórios; click abre `/reports/<report_id>`.

Workspace seed sem runs reais: rodar fluxo do `docs/reference/SMOKE_TEST_HUMAN.md`
§2 (gera relatório a partir de fixtures).

### 8.2 localStorage do shell

O shell persiste estado de UI **localmente** no browser:

| Chave (prefixo `mathoms.report.`) | O que guarda |
| --- | --- |
| `theme`           | `light` \| `dark` (toggle do header) |
| `mode`            | `estrategico` \| `usa` (preferência do usuário; URL `?mode=` tem precedência). Modo `tatico` removido em ADR-151. |
| `font-scale`      | `0.85`–`1.15` (zoom relativo) |
| `notas:<report_id>:<section_id>` | Notas livres (legado pré-ADR-151; `report_notes` migrado para `workspace_notes` em ADR-154 M1; **endpoints REST retornam HTTP 410 Gone desde ADR-154 M2 (2026-04-29);** tabela renomeada para `_legacy_report_notes`, drop final em PR M3 sprint+2) |
| `kanban:<report_id>` | Colunas + ordem dos cards (legado pré-ADR-151; `kanban_items` migrado para `tasks` com `board_column`/`board_order`/`is_board_only` em ADR-154 M1; **endpoints REST retornam HTTP 410 Gone desde ADR-154 M2 (2026-04-29);** tabela renomeada para `_legacy_kanban_items`, drop final em PR M3 sprint+2) |

Inspecionar/limpar via DevTools → Application → Local Storage → host.
Reset completo do shell:

```js
Object.keys(localStorage)
  .filter(k => k.startsWith('mathoms.report.'))
  .forEach(k => localStorage.removeItem(k));
```

> **Nota persistida no servidor (ADR-123):** notas/kanban também sincronizam
> via `reports_collab` API — limpar localStorage **não apaga server-side**.
> Para reset completo, use endpoint `DELETE /v1/reports/<id>/collab/*`.

### 8.3 Regerar PDF via Playwright

Endpoint: `GET /v1/reports/<report_id>/download.pdf`. Backend chama
[backend/app/services/pdf_renderer.py](../../backend/app/services/pdf_renderer.py)
que usa Chromium headless para imprimir a rota
`/reports/<id>?print=1` em A4.

```bash
# Acionar manualmente (requer JWT válido):
curl -H "Authorization: Bearer $TOKEN" \
  https://api.mathoms.ai/v1/reports/<id>/download.pdf -o report.pdf
```

PDF é **gerado on-demand** (não cacheado). Para invalidar/forçar
regeneração: simplesmente refazer a chamada — não há cache HTTP no
endpoint. Se o PDF sai em branco ou sem charts: `chromium` do
Playwright não está instalado no container do backend (ver
[SETUP.md](SETUP.md) §Playwright).

### 8.4 Shell que não monta (página em branco / spinner eterno)

Diagnóstico em ordem:

1. **Console do browser** → erro de hidratação / bundle?
   `next dev` mostra stack trace; se erro é "module not found", roda
   `cd frontend && rm -rf .next node_modules && npm install`.
2. **Network tab** → `GET /v1/reports/<id>/data` retornando 200?
   Se 404: report_id não existe; se 403: workspace mismatch.
3. **`useReportData(id)` retornando `null`** → contrato
   `ReportAnalysisData` quebrado pós-pipeline. Confere shape em
   [frontend/src/types/](../../frontend/src/types/) vs payload real do
   endpoint. Mismatch comum: campo `score.formula` mudou de string
   para objeto, etc.
4. **`MIGRATED_SECTIONS` ausente** → seção referenciada no
   `report_layout.yaml` ainda é stub; layout muda mas seções não.
   Rodar `python3 dev/codegen_report_layout.py` e reiniciar dev server.

### 8.5 Modo errado na URL

`/reports/<id>?mode=foo` (modo inexistente) → `ReportModeProvider`
faz fallback para `estrategico` silenciosamente e loga warning. Toggle
do header sobrescreve a URL. Se quiser truncar `mode` da URL ao
mudar via toggle, é comportamento esperado — provider re-pusha sem
querystring.

### 8.6 Print não funciona / quebras feias

- `?print=1` na URL aciona estilos `@media print` + `data-print-route`
  no `<html>`.
- CSS de print mora em
  [frontend/src/components/report/report-print.css](../../frontend/src/components/report/report-print.css).
  Quebras explícitas por seção via `break-inside: avoid;` em
  `.report-section`.
- Se gráfico Chart.js sai cortado: provavelmente o canvas excede
  altura da página A4 — reduzir `aspectRatio` no wrapper específico
  em `frontend/src/components/report/charts/`.
- Se cabeçalho de família não aparece em todas as páginas: confere
  se `<ReportCover>` está fora de container com `transform`
  (transforms quebram `position: fixed` no print).

---

## 9. Dogfood Learning Loop (A12.P3 · ADR-186/188)

Gate dogfood do learning loop: CEO/sócio interno cria ≥5 regras em
janela de 7 dias, mede revert rate, valida caveats antes de cutover
global (default flip de `learning_loop_enabled`).

### 9.1 Pré-reqs

- **Feature flag** habilitada por workspace:

  ```python
  from backend.app.services.feature_flags_service import set_flag

  await set_flag(ws_id, "learning_loop_enabled", True, db=db)
  ```

  Default global continua `False` (ADR-186 §D6, gate dogfood).
- **Celery worker** rodando com `--concurrency=1` (race protection
  P2/P3: partial unique + ON CONFLICT + sort canônico). Em produção,
  >1 worker é válido — paridade testada em `test_multi_worker_concurrency`,
  mas para dogfood single-tenant `1` simplifica observabilidade.
- **Redis** disponível (`apply_status:*` hash + `apply_retroactive:*`
  idempotency keys; sem Redis o status async degrada para `unknown`).

### 9.2 CLI smoke (curl)

```bash
TOKEN=<JWT do dogfood user>
WS=<workspace_id>

# 1. Preview (não persiste)
curl -X POST "$API/v1/workspaces/$WS/categorization/rules/preview" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"keyword":"UBER","target_category":"Transporte · App"}'

# 2. Criar regra (sync se ≤500 matches → 201; async se >500 → 202)
curl -X POST "$API/v1/workspaces/$WS/categorization/rules" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"keyword":"UBER","target_category":"Transporte · App","priority":100}'

# 3. Status do apply async (se foi async)
curl "$API/v1/workspaces/$WS/categorization/rules/<rule_id>/apply-status" \
  -H "Authorization: Bearer $TOKEN"

# 4. Listar regras
curl "$API/v1/workspaces/$WS/categorization/rules?enabled=true" \
  -H "Authorization: Bearer $TOKEN"

# 5. Disable (toggle, sem cascade)
curl -X POST "$API/v1/workspaces/$WS/categorization/rules/<rule_id>/disable" \
  -H "Authorization: Bearer $TOKEN"

# 6. Delete (soft + cascade overrides source='rule')
curl -X DELETE "$API/v1/workspaces/$WS/categorization/rules/<rule_id>" \
  -H "Authorization: Bearer $TOKEN"
```

### 9.3 Critério de aceite (7 dias wall-clock)

- **≥5 regras persistentes** (não-deletadas) criadas pelo dogfood user.
- **`revert_rate ≤ 30%`** — numerador `revert_count_manual_edit` por regra,
  denominador `applied_count`. Disable não polui (ADR-188 §D3).
- **≥3 regras com ≥3 matches retroativos cada** — sinal de que regra
  pegou padrão real, não one-off.
- **Entrevista qualitativa** (3 perguntas):
  1. A regra apareceu na 1ª categoria certa do extrato?
  2. Se você revisse hoje, reverteria?
  3. Você criaria essa regra de novo?
- **Tempo de confirmação do dialog `requires_user_confirmation`**:
  se >70% dos preview com `requires_user_confirmation=true` confirmam
  em <2s, sinal-ruído errado — UI está pedindo confirmação demais.

Os 3 critérios quantitativos são computados por
[dev/dogfood_metrics_a12.py](../../dev/dogfood_metrics_a12.py) contra o
workspace real (fim da janela de 7 dias):

```bash
.venv/bin/python3 dev/dogfood_metrics_a12.py --workspace <workspace_id> [--days 7] [--json]
# Veredito: PASS | PARTIAL | FAIL (exit 0 só em PASS)
```

Entrevista qualitativa e tempo de dialog seguem manuais.

### 9.4 Caveats (financial-planner gate triple)

- **PIX cônjuge / split de conta** — detector de transferência interna
  falha se cônjuge não está em `family_members`. Adicionar cônjuge ao
  workspace **antes** de criar regras envolvendo categorias domésticas.
- **Sazonalidade** — keywords mensais (13º salário, IPVA, IPTU) só são
  testáveis 1×/ano. Dogfood de 7 dias **não vai cobrir** padrões anuais;
  esperar regressão silenciosa em mês X.
- **AUVP / contrafluxo / mês fechado** — `report_publications.published_at`
  bloqueia override retroativo (ADR-187). Preview deve explicar
  explicitamente: "3 matches em mês aberto, 47 em meses fechados — fechados
  **não serão alterados**". Se UI não mostra, é P4 follow-up.
- **Estorno blacklist** (deferred PR3+) — campo `transactions.is_reversed`
  ainda não existe; pares de estorno não são detectados. Acompanhar manualmente
  na lista de matches do preview. Track próprio quando dogfood pedir.

### 9.5 Falha do gate → product-designer

Se 4 dos 5 critérios falham, abrir track para `product-designer`
revisitar extração de keywords (UI + microcopy). Sucesso → P4 frontend
(react UI) entra na pilha.

### 9.6 Gate técnico (smoke E2E + invariantes)

[scripts/dogfood_gate_a12.py](../../scripts/dogfood_gate_a12.py) roda
gate **técnico** offline — independente do humano. Cria SQLite isolado
em `_scratch/dogfood_gate_a12.db`, gera fixture realista (~2880 txs /
24 meses), executa 5 regras (IFOOD / MERCADOLIVRE / UBER / PIX / "13"),
simula ~20% de reverts, exercita soft + hard cap.

```bash
.venv/bin/python3 scripts/dogfood_gate_a12.py
# Verdict: PASS | PARTIAL | FAIL
# Relatório: _scratch/dogfood_gate_a12_report.md (+ .json)
```

**Não substitui o gate humano UX** — cobre apenas invariantes
mensuráveis (ADR-186 §D2/§D6 + ADR-187 + ADR-188 §D3/§D5):

- sticky manual override (não sobrescreve correção do usuário)
- mês fechado enforce (ADR-187)
- transferência interna blacklist (PIX/TED não vira "Transferência")
- keyword warning (`keyword_too_short`)
- `revert_rate ≤ 30%` computável
- `applied_count - revert_count_manual_edit == COUNT(overrides ativos)`
- soft cap (50) warning + hard cap (200) bloqueio

Sinais qualitativos ("vou usar isso?", fadiga de dialog, expectativa
metodológica) e entrevista §9.3 continuam por conta do gate humano.

**Idempotente** — rodar 2× produz mesmo veredito (RNG seed fixo). Não
toca `mathoms.db` de produção.

---

## 10. Backfill de Debt (ADR-227 §D6 · Sprint A15 Onda 2)

Cutover one-shot que cria 1 row `Debt` por membro com `total_dividas > 0`
no `baseline_patrimonial-1.5_consolidated`. Substitui o agregado
in-memory por persistência (Onda 3 do calculator passa a consumir
`Debt` em vez de `baseline.total_dividas`).

### 10.1 Pré-requisitos

- Migration `adr227debt1` aplicada (`alembic upgrade head`). Tabelas
  `debt` + `property_market_value` existem.
- Workspace tem artifact `consolidate_baseline` / `E1.5c` com
  `dividas[]` em `pipeline_artifacts`.

### 10.2 Invocação

**Dogfood primeiro, prod 1 workspace por vez.**

```bash
# 1) Dry-run em workspace seed (default; não persiste)
python3 dev/backfill_debt_from_baseline.py --workspace-id <ws-id> > audit-dry.json

# 2) Inspecione audit-dry.json — `summary_by_status`, ações `would_create`
cat audit-dry.json | jq '.reports[].members'

# 3) Apply em workspace dogfood
python3 dev/backfill_debt_from_baseline.py --workspace-id <ws-id> --apply \
  --audit-out storage/<ws-id>/logs/debt_migration_audit.json

# 4) Re-run apply é no-op (uq_debt_migration_source partial unique)
python3 dev/backfill_debt_from_baseline.py --workspace-id <ws-id> --apply
# → audit reporta `skipped_already_migrated` em todos os membros
```

### 10.3 Audit log

- Path padrão: `storage/<ws-id>/logs/debt_migration_audit.json` (use
  `--audit-out`; default: stdout).
- Diretório `storage/` é **gitignored** — faça backup do audit log
  antes de cleanup destrutivo do workspace.
- Schema: `{summary_by_status, reports: [{workspace_id, status, members:
  [{key, total_dividas_brl, action, created_debt_id}]}]}`.
- `action ∈ {would_create, created, skipped_already_migrated, skipped_zero}`.

### 10.4 Rollback

Migration idempotente; reversão manual:

```sql
DELETE FROM debt
WHERE workspace_id = '<ws-id>' AND source = 'baseline_irpf_migration';
```

Rows com `source = 'user_declared'` ficam preservadas. Re-run do
backfill após DELETE volta a criar do baseline.

### 10.5 Troubleshooting

| Sintoma | Causa | Ação |
|---|---|---|
| `status: "skip", reason: "no_baseline"` | Workspace sem artifact `consolidate_baseline` | Rode pipeline E1.5c primeiro. |
| `status: "skip", reason: "no_members"` | Workspace sem `family_members` | Cadastre titular antes. |
| `action: "skipped_zero"` para todos | `total_dividas = 0` em `baseline.dividas[]` filtrado por member.key | Esperado em workspace sem dívidas. |
| 2ª run cria duplicatas | `migration_source_key` mudou entre runs | Não deveria ocorrer — chave é `{ws_id}_{member_key}`. Inspecione DB. |
| Test integration `test_backfill_debt_from_baseline.py` falha | Schema drift Onda 1 | Confirmar `alembic upgrade head` aplicado. |

---

## 11. Cutover do shell Go (F2 do GO_SHELL · [[ADR-150]] §7)

Procedimento e gatilhos de rollback vivem no track
[plan/GO_SHELL/tracks/f2-cutover.md](../plan/GO_SHELL/tracks/f2-cutover.md) —
esta seção é só o mapa operacional. **Fonte única do critério:** [[ADR-150]] §7 +
emendas 2026-07-08 (tiers de paridade) e 2026-07-31 (gate no dogfood local).

### 11.1 Ligar e desligar

```bash
make go-on  ENV=native     # shell Go :8002 + worker re-apontado
make go-off ENV=native     # rollback: worker volta ao executor InProcess
```

O flip **não é a quente**: `get_pipeline_client()` memoiza o singleton por
processo, então ambos os targets reiniciam o worker. RTO do rollback = 1 restart
(segundos). Runs em voo: drain SIGTERM (grace 30s) + re-run idempotente — a
escrita só commita no sucesso.

### 11.2 Gate de paridade

```bash
make go-parity WS=<workspace_uuid>            # Tier-1: 3 runs por braço, 0 LLM
```

Alterna o overlay sozinho e devolve o worker ao Python no fim. Relatórios em
`_scratch/go_parity/`.

**Pré-condição: inbox vazio.** O harness verifica e falha com o path — ele **não
move documento seu**. Com documento no inbox o E0 classificaria, e todo doc com
`classification_confidence < 0,8` dispara o fallback LLM (o `skip_llm` do
orquestrador filtra a lista de stages por `is_llm`; não alcança o E0). Isso gasta
LLM e quebra o determinismo do Tier-1.

Tier-2 (`--tier tier2`, via `dev/go_parity_run.py`) roda `FULL_ORDER` com
narrativas e **custa LLM** — owner-run, alimenta o gate humano.

Leitura dos exit codes:

| Exit | Significado | Ação |
|---|---|---|
| 0 | Controle Py↔Py limpo **e** nenhuma divergência Go↔Py | segue para o gate humano |
| 1 | Divergência Go↔Py com controle limpo | **bug de executor** — não flipa |
| 2 | Controle Py↔Py sujo, ou falha de pré-condição | o gate **não está pronto**; normalização incompleta ou não-determinismo fora da allowlist. Qualquer veredito Go↔Py aqui é ruído |

### 11.3 Ledger do soak (template)

O §8 da [[ADR-150]] exige o soak **documentado** — sem ledger não há como afirmar
os 14 dias. Copie para `_scratch/go_soak_ledger.md` (fora do git: carrega
`run_id` de dado real) e preencha **por run**, append-only.

```markdown
# Ledger do soak — shell Go (F2)
Início: YYYY-MM-DD · executor: Go · rollbacks: 0

| # | data | run_id | tier | status | duração | vs SLO | shell /health | falha (classe) |
|---|------|--------|------|--------|---------|--------|---------------|----------------|
| 1 | | | Free/Premium | completed | | ok | 200 | — |

## Parity check semanal (double-run)
| semana | data | cents diff | envelope diff | veredito |
|---|---|---|---|---|
| 1 | | 0 | 0 | ok |

## Incidentes
| data | gatilho | evidência | ação | zerou o relógio? |
|---|---|---|---|---|

## Fechamento (F3 abre quando TODOS verdes)
- [ ] 14 dias-calendário consecutivos em Go
- [ ] ≥10 runs E0→E5 reais · [ ] ≥3 com LLM
- [ ] parity checks semanais todos zero
- [ ] zero rollback · [ ] zero `database is locked` · [ ] zero zumbi
- [ ] shell saudável em 100% dos runs
- [ ] gate humano PASS
```

**Regras do relógio:** rollback por gatilho **zera** para dia 0. Janela em Python
por motivo não-Go (manutenção) **pausa**, não zera. 14 dias ociosos não provam
nada — a barra de atividade é que dá significado ao soak.

### 11.4 Sinais durante o soak

Logs em `_dev_pids/go.log` + `worker.log`. Não há monitor externo no dogfood —
`curl -sf localhost:8002/health` no início de cada run é o floor. Tabela completa
de gatilhos de rollback (7 herdados + o de contenção SQLite) no track. O que é
específico do dogfood e **não** existia sob `InProcess`:
`OperationalError: database is locked` — sob o shell Go o subprocess escreve
artefatos enquanto o worker escreve `pipeline_runs`/eventos, e SQLite WAL admite
um escritor por vez. **1 ocorrência = rollback.**

---

## 12. Referências

- [runbooks/f9_3_alembic_upgrade.md](runbooks/f9_3_alembic_upgrade.md) — F9.3 stage rename migration (pré-check + backup + rollback)
- [runbooks/schema_validation_strict_flip.md](runbooks/schema_validation_strict_flip.md) — flip warn→strict per-schema (gate por baseline 7d + rollback de 1 linha, ADR-284)
- [runbooks/override_legacy_drop.md](runbooks/override_legacy_drop.md) — ADR-282 Fase E: drop destrutivo do hash legado de override (gates G1/G2/G2b/G3 + backup/PITR + sign-off do owner; drafts da migration destrutiva e do sentinela G3 em apêndice — drop gated por go/no-go)
- [runbooks/vault_full_audit.md](runbooks/vault_full_audit.md) — auditoria full (100%) do vault: 3 fases ou one-shot `/audit-vault --scope all --full` (modo de evento, ADR-302)
- [SLO.md](SLO.md) — SLOs e SLAs de comunicação
- [BACKLOG.md](../BACKLOG.md) — 7E (operational readiness) · F7F-Local
- [SMOKE_TEST.md](SMOKE_TEST.md) — verificações manuais pré-release
- [SMOKE_TEST_HUMAN.md](SMOKE_TEST_HUMAN.md) — runbook de smoke humano
- [plan/REPORT_PREMIUM/_README.md](../plan/REPORT_PREMIUM/_README.md) — plano canônico do shell v1
- [ADR-116](../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local) — decisões de design F7F-Local
- [ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side) — descontinuação do renderer HTML server-side
