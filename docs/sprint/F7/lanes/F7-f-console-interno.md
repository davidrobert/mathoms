---
id: F7.f
type: lane
title: "Console interno (operadores)"
sprint: F7
plan: PLAN-internal-admin
status: shipped
priority: P0
adrs: ["[[ADR-076]]", "[[ADR-110]]", "[[ADR-115]]", "[[ADR-116]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f7
  - status/shipped
  - priority/p0
---


# F7F — Console interno (operadores)


> Superfície para CEO, Ops, CS, Financeiro e Legal **operarem a plataforma** (não confundir com `/config` do workspace do cliente). Fases conceituais **IA-0 … IA-4** em [PLAN-internal-admin](../../../plan/INTERNAL_ADMIN/_README.md).
>
> **Dividida em duas partes independentes:**
>
> - **[F7F-Local — Pré-produção (IA-0, sem OAuth)](#f7f-local--pré-produção-ia-0-sem-oauth)** — **UI web em `127.0.0.1` é a superfície principal** (consumindo uma camada de serviço compartilhada); CLI vira atalho secundário/futuro. Roda na máquina de desenvolvimento (backend + DB local ou túnel para staging). **Pode ser feita antes de F7A Docker/Deploy** — é a ferramenta que o operador usa enquanto o produto ainda não está no ar. Segurança vem de bind `127.0.0.1` + flag de env + sessão isolada + audit em arquivo, sem auth staff.
> - **[F7F-Remote — Produção (IA-1…IA-4, com OAuth staff)](#f7f-remote--produção-ia-1ia-4-com-oauth-staff)** — console hospedado em `ops.mathoms.ai` com OAuth Google Workspace, RBAC interno, prefixo `/api/internal/`, dashboard de negócio (**7E.7**), CS bundle, financeiro. **Depende de F7A–F7C estabilizados.**
>
> **Ordem sugerida global:** F7F-Local P0 (7F.L1 serviço → 7F.L2 UI → 7F.10–7F.12 exclusão/senha/purge) → F7F-Local complementar (7F.13–7F.14 leituras → 7F.9 CLI secundário opcional) → F7F-Remote ADR (7F.1, pode iniciar em paralelo) → F7A/B/C → F7F-Remote auth + RBAC (7F.2–7F.4) → F7F-Remote CS/Financeiro (7F.5–7F.8).

#### F7F-Local — Pré-produção (IA-0, sem OAuth)

> **Meta:** operador executa tarefas de suporte e LGPD localmente (exclusão de conta, purge de documentos, reset de senha, leitura de relatórios, métricas agregadas) antes do produto estar no ar. Nenhuma dependência de F7A (deploy), F7B (auth prod) ou F7C (CI/CD). Guardrails locais: bind em `127.0.0.1`, flag de env explícita (`INTERNAL_OPS_UI_ENABLED=1`), bloqueio se `ENVIRONMENT=production` sem `--i-accept-production-risk`, audit em arquivo.
>
> **Decisão de superfície (atualizada 2026-04-22):** a **interface web local** é a **superfície principal** desta fase. A camada de serviço (business logic) é a fonte de verdade e fica escrita agnóstica a consumidor; **CLI entra como atalho secundário/futuro** para automação e operações batch, reutilizando a mesma camada de serviço da UI. Motivação: UI acelera onboarding de novos operadores (CS/Legal), dá confirmação visual para deletes (reduz risco de typo) e é base reaproveitada para `ops.mathoms.ai` na F7F-Remote.
>
> **Ordem sugerida:** 7F.L1 (camada de serviço) → 7F.L2 (UI web local — shell + auth mínimo) → 7F.10/7F.11/7F.12/7F.15/7F.16/7F.17 (business logic por área, consumidas pela UI) → 7F.13/7F.14 (leituras) → 7F.9 (CLI secundário, opcional, depois da UI estabilizada).

| #     | Tarefa | Prio | Est. | Status |
| ----- | ------ | ---- | ---- | ------ |
| 7F.L1 | **Camada de serviço interna** ([ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local)): módulo `backend/app/services/internal_ops/` com funções puras (recebem DB session + args, retornam `OpResult` + `AuditRecord`); consumida pela UI web (7F.L2) e pelo CLI futuro (7F.9); expõe `delete_user(user_id, mode="anonymize"\|"hard_delete")`, `reset_password(user_id, new_pw)`, `purge_documents(scope)`, `delete_document(document_id)`, `update_user_email(user_id, new_email)`, `update_user_profile(user_id, **fields)`, `set_developer_flag(user_id, enabled)`, `get_metrics()`, `list_reports(user_id\|workspace_id)`; mutações sensíveis (email, flags) bumpam `token_version` para invalidar JWTs; testes unitários com fixture SQLite | P0 | 6h | ✅ S1 mergeado 2026-04-23 (`cd46545..ef1a7ae`) |
| 7F.L2 | **UI web local — `frontend-ops/` app Next separada** ([ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local)): novo diretório raiz com `package.json`, `next.config.ts`, `Dockerfile`, bind em `127.0.0.1:3100` via flag `INTERNAL_OPS_UI_ENABLED=1` (default off); **auth** `config/internal_operators.yaml` (bcrypt hashes, gitignored) + `POST /admin/login` emite JWT assinado com `INTERNAL_OPS_SESSION_SECRET` (distinto do `SECRET_KEY` cliente); cookie `ops_session` httpOnly + SameSite=Strict + Path=/admin, TTL 8h; middleware FastAPI `require_internal_operator()` em todas rotas `/admin/*`; `scripts/hash_ops_pw.py` gera bcrypt interativo; design tokens reaproveitados via `design-tokens/` (ADR-076), zero import de componentes do frontend cliente; bloqueio se `ENVIRONMENT=production` sem `--i-accept-production-risk`; documentar URL/flag/rotação de credenciais no runbook | P0 | 10h | ✅ S2 mergeado 2026-04-23 (`e65126b..d7b5a18`) |
| 7F.10 | **Exclusão de usuário (UI + serviço)** ([ADR-116](../../../DECISIONS.md#adr-116--f7f-local-stack-next-separada--anonimização-default--auth-yamlbcryptjwt-f7f-local) default **anonimização**): `internal_ops.delete_user(user_id, mode="anonymize")` substitui `email` por `deleted_user_<id>@tombstone.mathoms.ai`, `display_name` por `"Conta removida"`, zera `password_hash` com sentinela, grava `anonymized_at`, remove `refresh_tokens`+`sessions`+`invitations` pendentes; preserva `id`/`created_at`/FKs para integridade de audit (ADR-115); workspaces órfãos ficam inativos (transferência manual documentada); `mode="hard_delete"` exige confirmação extra + audit específico + nunca é default; tela com confirmação dupla (`TYPE "delete"`); testes unitários + de anonimização com fixture SQLite | P0 | 6h | ✅ S3.a mergeado 2026-04-23 |
| 7F.11 | **Reset de senha manual (UI):** tela atualiza hash no modelo `User` (mesmo algoritmo do app); campo de nova senha com revelar opcional e geração de senha temporária copiável; não loga senha nem em claro nem mascarada | P0 | 2h | ✅ S3.b mergeado 2026-04-23 (16 chars + invalida JWT via token_version) |
| 7F.12 | **Purge de documentos (UI):** por `user_id` ou `workspace_id`, remove registros e blobs em storage (`stored_path` / [storage.py](../../../../backend/app/services/storage/__init__.py)); modo "prévia" lista arquivos/linhas antes de confirmar; mesma confirmação dupla de 7F.10 | P0 | 6h | ✅ S3.c mergeado 2026-04-23 (rollback em OSError + preview paginada) |
| 7F.13 | **Métricas de utilização (UI):** dashboard simples agrega uploads/runs/workspaces/volume storage; cards + tabela; export CSV como ação secundária; base para **7D.9** telemetria e **7E.7** dashboard remoto | P1 | 4h | ✅ S3.d mergeado 2026-04-23 (7d/30d/90d + novos cards uploads/users) |
| 7F.14 | **Relatórios read-only (UI):** lista dos últimos `Report` (ou pipeline runs) por conta com filtro por email/`user_id`; link abre JSON ou HTML exportado em aba separada; sem mutação nem reexecução de pipeline | P1 | 4h | ✅ S3.e mergeado 2026-04-23 (paginação offset/total) |
| 7F.15 | **Toggle `is_developer` (UI + serviço):** tela mostra flag atual do usuário e permite ligar/desligar com confirmação simples; `internal_ops.set_developer_flag(user_id, enabled)` atualiza `users.is_developer` ([user.py:21](../../../../backend/app/models/user.py:21)) e grava audit; substitui uso manual de [set_developer_flag.py](../../../../backend/app/scripts/set_developer_flag.py); sem confirmação dupla (ação reversível) | P0 | 2h | ✅ S3.f mergeado 2026-04-23 (confirm só ao ligar) |
| 7F.16 | **Editar cadastro do usuário (UI + serviço):** formulário edita `email`, `full_name`, `is_active` ([user.py:17-20](../../../../backend/app/models/user.py:17)); mudança de `email` valida unicidade, bumpa `token_version` para invalidar JWTs existentes e grava audit separado (campo sensível); `is_active=false` equivale a desativar login sem anonimizar; mudanças em `full_name` não bumpam token; testes cobrem colisão de email + invalidação de sessão | P0 | 4h | ✅ S3.g mergeado 2026-04-23 (audit `user.email_changed` + banner logout) |
| 7F.17 | **Exclusão de documento individual (UI + serviço):** complementa purge bulk (7F.12) permitindo deletar **um** upload específico por `document_id`; UI lista documentos por `user_id`/`workspace_id` com metadados (nome, data, tamanho, tipo) e ação "excluir" por linha; `internal_ops.delete_document(document_id)` remove registro + blob em storage ([storage.py](../../../../backend/app/services/storage/__init__.py)); confirmação simples (não dupla — escopo menor que purge); audit inclui hash/nome do arquivo removido | P0 | 4h | ✅ S3.h mergeado 2026-04-23 (audit filename+content_hash; excluir por linha na prévia de 7F.12) |
| 7F.9  | **CLI interno (secundário, pós-UI):** entrypoint documentado (ex.: `python -m app.scripts.internal_ops` ou target em `Makefile`) para automação/batch; **reutiliza a camada de serviço de 7F.L1** (zero duplicação de regra); `--dry-run` + confirmação explícita em deletes; mesmo audit em `logs/` que a UI | P1 | 3h | ☐ opcional (sem demanda concreta) |

**Audit (comum UI + CLI):** toda mutação escreve linha em `logs/internal_ops_audit.log` (JSON: operador, ação, alvo, timestamp, resultado) — ADR-110 masking aplica. Quando 7B.5 persistir, a camada de serviço passa a gravar na tabela de audit sem mudar UI/CLI (troca só do sink).

**Checkpoint F7F-Local (IA-0):** ✅ **MVP FECHADO em 2026-04-23** — S1 (services+auth backend, `cd46545..ef1a7ae`) + S2 (frontend-ops shell + 4 telas, `e65126b..d7b5a18`) + S3 (refino 7F.10–7F.17, `876d09f..8f1e0ca`) mergeados em `main`. Operador executa anonimização (default) / hard delete (superadmin + motivo) / reset pw (16 chars + invalida JWT) / purge bulk (com rollback em OSError de blob) / delete individual / toggle dev / editar email+nome+is_active pela UI local. Métricas 7d/30d/90d com cards de uploads/novos users; relatórios paginados. Harness Playwright `@internal-ops` scaffolded em `frontend-ops/tests/e2e/` (run em CI pendente; smoke curl validado manualmente). 7F.9 (CLI) fica aberto sem bloquear — só executar se demanda concreta.

#### F7F-Analyst — Superfície do especialista de planejamento financeiro/patrimonial (IA-0+, pós-P0 Ops)

> **Meta:** permitir que um especialista em planejamento financeiro (metodologias **Perini / Cerbasi / AUVP** — [CLAUDE.md §Papel do assistente](../../../../CLAUDE.md)) analise a saúde financeira de cada conta, tenha panorama agregado da base e registre feedback contínuo sobre produto/layout de relatório. Superfície **read-heavy e não-destrutiva** — distinta da Ops, mesmo app `frontend-ops/` com papel `analyst` separado no yaml (`role: analyst`) e rotas `/analyst/*` protegidas.
>
> **Fundamentos dos 5 indicadores de saúde** (todos derivados de artefatos E1.5/E5 — **zero recálculo na UI**):
> - **Reserva de emergência** (Cerbasi): `reserva_liquida / custo_fixo_mensal` → meses cobertos (meta 6-12m).
> - **Taxa de poupança** (Cerbasi/AUVP): `(receita − despesa) / receita` → savings rate (meta >20%).
> - **Alocação patrimonial** (AUVP/Perini): % em RF / RV / imóveis / caixa vs benchmark por faixa etária.
> - **Renda passiva** (Perini): `(dividendos + juros 12m) / custo_fixo_anual` → % de IF atingido.
> - **Endividamento** (Cerbasi): `divida_total / patrimonio_liquido` + `divida / renda` (meta <30%).
>
> **Ordem sugerida:** 7F.A1 (serviço de métricas, reutiliza `pipeline/domain/services/`) → 7F.A2 (modelo `analyst_notes` + ADR nova) → 7F.A3 (role analyst + rotas backend) → 7F.A4 (triage) → 7F.A5 (deep dive) → 7F.A6 (overview agregado) → 7F.A7 (feedback loop).
>
> **Fluxos de referência:** triage semanal (5), deep dive diário (6), panorama mensal (7), feedback contínuo (8) — desenhados com estética Stripe (single-scroll + detail panel) + Linear (⌘K, atalhos, cycle-picker).

| #      | Tarefa | Prio | Est. | Status |
| ------ | ------ | ---- | ---- | ------ |
| 7F.A1  | **AnalystMetrics service** — `backend/app/services/analyst_metrics/` com funções puras que agregam indicadores de saúde a partir de artefatos E1.5 (baseline patrimonial) e E5 (análise financeira) **sem recalcular** — reutiliza `pipeline/domain/services/` quando possível; expõe `compute_health_score(user_id)`, `list_users_ranked(filters, sort)`, `get_user_snapshot(user_id, period)`, `aggregate_base(segment_by)`; health score composto **transparente** (retorna breakdown por indicador com fórmula + meta aplicada); testes unitários com fixtures Alembic-aware (DB em memória, nunca mock — CLAUDE.md §Testes) | P0 | 8h | ☐ |
| 7F.A2  | **Modelo `analyst_notes` + ADR** — tabela nova (`id`, `author_operator`, `note_type` ∈ `user_insight\|product_suggestion\|report_suggestion`, `target_user_id` nullable, `target_report_section` nullable, `methodology` ∈ `perini\|cerbasi\|auvp`, `body`, `status` ∈ `aberto\|em_analise\|implementado\|descartado`, `created_at`, `updated_at`); migration Alembic; service `analyst_notes.py` (CRUD + filtros); **nova ADR** em [DECISIONS.md](../../../DECISIONS.md) justificando a tabela (separada de audit porque é conteúdo editorial, não imutável) | P0 | 4h | ☐ |
| 7F.A3  | **Backend `/admin/analyst/*` + role `analyst`** — extende `config/internal_operators.yaml` com campo `role` (`ops` \| `analyst`); middleware `require_analyst_role()` em FastAPI; rotas `GET /admin/analyst/users` (triage), `GET /admin/analyst/users/<id>` (deep dive), `GET /admin/analyst/overview` (agregado), `POST/GET/PATCH /admin/analyst/notes`; `make update-openapi-snapshot`; testes 403 (ops não acessa analyst e vice-versa) + 401 (sem auth); **antecipa RBAC de 7F.3** — mesmo yaml, granularidade mínima | P0 | 6h | ☐ |
| 7F.A4  | **Tela Triage `/analyst`** (Fluxo 5): tabela com 5 indicadores + health score composto, filtros-chip estilo Linear (`sem reserva`, `savings < 10%`, `endividado > 30%`, `alocação 100% RF`, `IF < 10%`), colunas ordenáveis, expansão inline por linha com sparkline de 6 meses, hover em score abre tooltip com breakdown de cálculo (zero opacidade); paginação server-side; ações contextuais por linha: "Abrir análise profunda" (7F.A5) e "Anotar" (7F.A7) | P0 | 8h | ☐ |
| 7F.A5  | **Tela Deep Dive `/analyst/users/[id]`** (Fluxo 6): 5 cards verticais (fluxo de caixa Cerbasi, reserva Cerbasi, alocação AUVP, renda passiva Perini, endividamento Cerbasi) — cada card é mini-relatório diagnóstico com valor atual + meta + gap; sidebar direita com timeline de evolução mensal (Linear activity feed); click em mês abre snapshot histórico; botão **export markdown/PDF** reusa renderer E6; link "Anotar sobre este usuário" (pré-preenche `target_user_id`); zero divergência com relatório cliente (mesma fonte E5) | P0 | 10h | ☐ |
| 7F.A6  | **Tela Overview `/analyst/overview`** (Fluxo 7): 6 histogramas de distribuição (meses reserva, savings rate, alocação 100% RF, endividado >30%, IF atingida, top 3 categorias de gasto); linha temporal de % base saudável em cada indicador mês a mês; seção de insights auto-gerados (copy dinâmico a partir dos dados); dropdown de segmentação (faixa etária, renda, tempo de uso); cada agregado drill-down → `/analyst` pré-filtrado; **não-acionável** (sem mutação nem botões) | P1 | 8h | ☐ |
| 7F.A7  | **Feedback loop `/analyst/feedback` + sheet `⌘K → nota`** (Fluxo 8): sheet lateral (não modal) abre por atalho global ⌘N (estilo Linear); 3 tipos de nota (`user_insight`, `product_suggestion`, `report_suggestion`); se tipo `report_suggestion`, dropdown lista seções de `config/report_layout.yaml` (gerado em build-time via [dev/codegen_report_layout.py](../../../../dev/codegen_report_layout.py)); metodologia de referência obrigatória (Perini/Cerbasi/AUVP); tabela `/analyst/feedback` filtrada por status + tipo (tabs Linear cycle-style); nota `user_insight` aparece no perfil do usuário em F7F-Local (ops vê o que analista anotou); fase 2 (opcional): botão "exportar pra BACKLOG.md" cria branch + PR com task — fora de escopo do MVP | P1 | 6h | ☐ |

**Checkpoint F7F-Analyst (IA-0+):** 7F.A1 + 7F.A2 + 7F.A3 concluídos (backend + DB + RBAC mínimo) • 7F.A4 + 7F.A5 cobrem triage + deep dive (analista resolve 80% do trabalho diário) • 7F.A6 entrega panorama mensal • 7F.A7 fecha o feedback loop • role `analyst` testado em isolamento (ops não acessa `/analyst/*`, analista não acessa mutations destrutivas de Ops) • cálculos de saúde consistentes com relatório cliente (teste de paridade sobre fixture compartilhada) • export markdown/PDF do deep dive funciona localmente.

**Dependências e notas:**
- **7F.A1 exige artefatos E1.5/E5** — só funciona para usuários com pipeline rodado ao menos 1x; UI mostra estado vazio "sem dados de análise" para contas novas.
- **Health score é heurística, não verdade absoluta** — documentar limitações em [docs/reference/CANONICAL_ENGINE_P0.md](../../../reference/CANONICAL_ENGINE_P0.md) ou ADR da 7F.A2; qualquer mudança de fórmula exige bump de versão + recomputação de histórico.
- **Comparação com peers** (fase 2 mencionada no Fluxo 6) exige base anonimizada — **fora do MVP**, entra depois de termos volume (>100 usuários com E5 rodado).
- **Quando F7F-Remote subir:** rotas `/admin/analyst/*` migram para `/api/internal/analyst/*` com OAuth staff (7F.2) e RBAC granular (7F.3) — superfície e UX ficam idênticas, só a auth muda.

#### F7F-Remote — Produção (IA-1…IA-4, com OAuth staff)

> **Meta:** console acessível em `ops.mathoms.ai` com auth staff separado do JWT cliente, RBAC, telemetria de negócio (IA-2), ferramentas de CS (IA-3) e financeiro/legal (IA-4). Exige deploy (F7A), hardening (F7B) e observability (F7C) estabilizados.
>
> **Ordem sugerida:** 7F.1 (ADR) pode iniciar em paralelo à F7F-Local — não bloqueia. 7F.2–7F.4 após F7A pronto (HTTPS + subdomain `ops.mathoms.ai`). 7F.5 junto com 7C.7 (RUNBOOK). 7F.6–7F.7 pós-F7B (audit log persistido). 7F.8 quando billing real existir (F10).

| #     | Tarefa | Prio | Est. | Status |
| ----- | ------ | ---- | ---- | ------ |
| 7F.1  | **ADR + política interna:** identidade staff vs `User` cliente; impersonation proibida por padrão ou "break glass" com TTL + audit + ADR em [DECISIONS.md](../../../DECISIONS.md) | P0 | 3h | ☐ |
| 7F.2  | **Auth interna MVP:** credencial separada do JWT cliente (ex.: allowlist email + senha/secret rotativo, ou OAuth Google Workspace restrito a domínio da empresa); sessão não reutiliza cookie do app | P0 | 8h | ☐ |
| 7F.3  | **RBAC interno** (`internal_ops`, `internal_support`, …) + dependency FastAPI + testes 403 entre papéis | P1 | 6h | ☐ |
| 7F.4  | **Prefixo `/api/internal/`** (ou equivalente) protegido por env + testes; nenhuma rota interna em build do cliente sem flag explícita | P0 | 4h | ☐ |
| 7F.5  | **Documentação:** ao concluir **7C.7** (`docs/reference/RUNBOOK.md`), incluir secção console interno — quem acessa, rotação de credenciais, revogação de acesso staff | P1 | 1h | ☐ |
| 7F.6  | **CS:** busca por email / `user_id` → workspaces, roles, convites (somente metadados); toda consulta auditada | P2 | 8h | ☐ |
| 7F.7  | **CS:** endpoint + UI para **support bundle** JSON (diagnóstico redigido, sem valores/PII por padrão) | P2 | 6h | ☐ |
| 7F.8  | **Financeiro (pós-billing):** links read-only Stripe + export CSV contábil — depende de billing real (F10 / roadmap) | P2 | TBD | ☐ |

**Dependências externas da F7F-Remote:**

- **7A.7b** — Traefik `ipAllowList` para `ops.mathoms.ai` (pré-requisito de rede).
- **7A.11b** — teste Playwright valida isolamento de cookie entre `app.` e `ops.`.
- **7B.5** — audit log persistido em tabela `AuditEntry` (mutations internas gravam em DB em vez do log de arquivo da IA-0).
- **7C.4** — Sentry tags (`environment=ops`) separando erros de staff vs cliente.
- **7E.7** — dashboard `/admin/metrics` é o **núcleo visual da IA-2**; evolui as métricas já calculadas em 7F.13; protegido por 7F.2–7F.4.

**Checkpoint F7F-Remote (MVP IA-1 + IA-2):** 7F.1–7F.4 concluídos • **7E.7** renderizando para papel `internal_ops` • **7A.7b + 7A.11b** passando • zero exposição de rotas internas em deploy sem config explícita • audit log persistido (7B.5) cobre mutações internas.

**Checkpoint F7F-Remote (IA-3 CS Lite, pré-beta):** 7F.6–7F.7 concluídos • support bundle redigido testado em incidente real • time de CS triado ≥1 ticket sem escalar para engenharia.

**Checkpoint F7F-Remote (IA-4 Financeiro/Legal, pós-billing):** 7F.8 + fila DSAR (7B.18) integrada no console • export CSV contábil validado com contador externo.

---
