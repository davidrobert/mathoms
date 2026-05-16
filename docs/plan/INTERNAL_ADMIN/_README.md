---
id: PLAN-internal-admin
type: plan
title: Console interno (operadores) — IA-0 a IA-4
status: in_progress
sprint_origem: F7
sprint_atual: A11
sprints_envolvidas: [F7, A11]
created_at: "2026-04-22"
last_review: "2026-05-07"
paused_at: null
pause_reason: null
adrs_canonical: ["[[ADR-116]]"]
tags:
  - type/plan
  - status/in-progress
  - area/ops
---

# PLAN-INTERNAL-ADMIN — Console interno (operadores)

> Interface administrativa para **quem opera o produto** (CEO, Operações, Atendimento, Financeiro, Legal/LGPD), distinta do app do cliente (`/config` do workspace).
>
> **Última atualização:** 2026-04-22 — fase dividida em **F7F-Local** (pré-produção, UI web em `127.0.0.1`, sem OAuth) e **F7F-Remote** (produção, OAuth staff em `ops.mathoms.ai`). IA-0 passa a ter **UI web como superfície principal**; CLI é atalho secundário/futuro.
>
> **Backlog executável:** [BACKLOG.md — F7F](../../BACKLOG.md#f7f--console-interno-operadores)

---

## 1. Objetivo

Oferecer uma superfície **separada do usuário final**, com **least privilege** e **auditoria**, para diagnosticar a plataforma, apoiar clientes e cumprir obrigações (LGPD, financeiro) sem depender apenas de SQL, SSH e ferramentas externas.

**A fase é dividida em duas partes:**

- **F7F-Local (IA-0) — pré-produção:** **UI web local** (bind em `127.0.0.1`, habilitada por flag de env) é a **superfície principal**, consumindo uma camada de serviço compartilhada. **CLI** vira **atalho secundário/futuro** para automação/batch, reutilizando a mesma camada sem duplicar regra. Não há deploy; opera contra backend + DB + storage locais (ou túnel/VPN para staging). Não depende de F7A (Docker/Deploy) nem F7B (auth prod).
- **F7F-Remote (IA-1…IA-4) — produção:** console hospedado em `ops.mathoms.ai` com OAuth staff (Google Workspace restrito ao domínio da empresa), RBAC interno, prefixo `/api/internal/`, telemetria de negócio (**7E.7**), CS/Financeiro/Legal. Depende de F7A–F7C estabilizados.

**Motivação da inversão UI-first em IA-0:** tarefas de LGPD e suporte (exclusão de conta, purge, reset senha) são baixa frequência e alto impacto — confirmação visual e onboarding rápido de operadores não-engenheiros (CS, Legal) valem mais que a ergonomia de scripting. A camada de serviço compartilhada garante que o CLI entre depois sem retrabalho.

**Não é:** substituir Stripe Dashboard, Sentry ou Grafana na totalidade; substituir o `/config` do workspace (governança do cliente).

---

## 2. Princípios de arquitetura

| # | Princípio |
|---|-----------|
| P1 | **Host e credenciais separados** do login do cliente — **`ops.mathoms.ai`** (ADR-108), session cookie com scope exclusivo, SSO da empresa, MFA (TOTP mínimo; WebAuthn em F7E). **Nunca** compartilhar cookies com `app.mathoms.ai`. |
| P2 | **RBAC interno** (papéis como operador, suporte, financeiro, superadmin raro) com permissões explícitas na API. |
| P3 | Ação que altera estado do cliente ou expõe dado sensível: **motivo obrigatório** + registro em **audit log** (alinha a 7B.5). |
| P4 | APIs dedicadas sob **`api.mathoms.ai/v1/internal/*`** com guard por **ambiente**, **IP allowlist** (Traefik `ipAllowList` middleware) e testes de autorização. Middleware de auth **distinto** de `get_current_user` do produto. |
| P5 | **Minimização de dados:** visão padrão = metadados e agregados; PII/valores apenas em fluxos explícitos (“break glass”) com política documentada. |

---

## 3. Fases (IA-0 … IA-4)

A **primeira etapa executável** é **local** (máquina do operador com repo, `DATABASE_URL` e storage apontando para o mesmo ambiente que se deseja administrar — em geral **dev/staging**; produção só com runbook e flags explícitas). Entrega com **UI web como superfície principal**, consumindo uma **camada de serviço compartilhada**; **CLI** fica como atalho **secundário/futuro** para automação/batch. **Não** há deploy de console na internet nesta etapa.

### IA-0 — Operações locais (primeira etapa — executável já)

**Meta:** com backend + DB + storage configurados localmente (ou túnel/VPN para staging), o operador executa tarefas de suporte e LGPD **sem depender** de um console **hospedado** na internet, pela **UI web em `127.0.0.1`**.

**Estratégia de entrega (UI-first):**

1. **Camada de serviço compartilhada** (`backend/app/services/internal_ops/`) — funções puras que recebem DB session + args e retornam resultado + audit record. Fonte de verdade única; UI e CLI futuro apenas a consomem.
2. **UI web local (principal)** — rotas FastAPI+HTMX ou Next em dev, **bind em 127.0.0.1**, habilitada por `INTERNAL_OPS_UI_ENABLED=1`, login mínimo com token/senha de `.env.local` (separado do JWT cliente). Tela por área (contas, credenciais, documentos, métricas, relatórios).
3. **CLI (secundário, pós-UI)** — entrypoint para automação/batch (ex.: purge agendado, exclusão em massa), reutilizando a camada de serviço. Não duplica regra; entrega quando houver demanda clara.

**Escopo mínimo (checklist de pronto — expostos pela UI web):**

| Área | O que entregar |
|------|----------------|
| **Contas** | Excluir conta de usuário com cascata coerente: memberships, convites, vínculos a workspaces; política **hard delete** vs **anonimização** documentada; tela com confirmação dupla (`TYPE "delete"`). |
| **Credenciais** | Alterar senha manualmente (hash no mesmo algoritmo do app — ex.: bcrypt/Argon2 conforme modelo `User`) via tela com campo de nova senha + geração de senha temporária copiável; nunca logar senha em claro ou mascarada. |
| **Documentos** | Apagar documentos de um **usuário** ou **workspace** deletando registros no BD **e** objetos no **storage** (`stored_path` / camadas em [storage](../../../backend/app/services/storage.py)); modo **"prévia"** lista o que seria removido antes de confirmar. |
| **Métricas** | Dashboard agregado (uploads por período, runs de pipeline sucesso/falha, contagem de workspaces/documentos, volume storage) em cards + tabela; export CSV como ação secundária; evolução para `UsageMetric` (**7D.9**) e dashboard **7E.7** nas fases seguintes. |
| **Relatórios** | Tela **somente leitura** com filtro por email / `user_id` / `workspace_id`; lista `Report` (ou runs) recentes; link abre JSON ou HTML exportado em aba separada — **sem** edição nem reexecução de pipeline pelo mesmo canal. |
| **CLI (secundário)** | Entrypoint opcional (`python -m app.scripts.internal_ops` ou `Makefile`) para automação; `--dry-run` + confirmação explícita em deletes; mesmo audit em `logs/` da UI. Entregue pós-UI estabilizada. |

**Guardrails locais (obrigatórios no desenho):**

- **Bind em `127.0.0.1`** (nunca `0.0.0.0`) — garante que o console não vaza em rede local.
- **Flag de env explícita** (`INTERNAL_OPS_UI_ENABLED=1`) — sem ela, rotas/páginas internas não sobem; default em prod é `0`.
- **Confirmação dupla** (`TYPE "delete"` ou similar) em mutações destrutivas; modo "prévia" como default em deletes de volume (ex.: purge de documentos por workspace).
- **Bloqueio se `ENVIRONMENT=production`** salvo flag `--i-accept-production-risk` + variável de ambiente explícita — evita apagar dados reais por engano.
- **Sessão isolada** — não reutilizar cookie/sessão do app do cliente; token de dev em `.env.local` não vaza para `app.mathoms.ai`.
- **Trilha mínima** — append em `logs/internal_ops_audit.log` (JSON: operador, ação, alvo, timestamp, resultado) alinhada ao espírito de **7B.5** + masking de ADR-110; quando o audit persistido existir, a camada de serviço passa a gravar na tabela sem mudar UI/CLI (troca só do sink).

**Saída:** operador usa a **UI web local** como superfície principal, conforme documentação / runbook. CLI é entregue depois, quando houver demanda de automação. **7F.2–7F.4** não são obrigatórios para fechar IA-0: são a evolução para **auth staff + exposição controlada na rede** em F7F-Remote. Rotas sob prefixo interno **só em dev** (localhost) podem existir antes do pacote completo **7F.4** em produção.

### IA-1 — Fundação remota (paralelo a F7A–F7C)

**Meta:** trilhas e dados existirem antes de investir em UI rica **e** preparar o mesmo comportamento de IA-0 atrás de API autenticada.

- Runbook de deploy/recuperação (**7C.7**).
- **Structured logging** + correlação request/Celery (**7C.5**).
- **Audit log** para writes sensíveis (**7B.5**) — obrigatório para mutações via CLI **e** via UI local; antes de expor o console na rede, reforçar política e testes (**7F.4**).
- Decisão documentada: **sem impersonation** do cliente ou fluxo “break glass” com TTL, notificação e ADR (**7F.1** no backlog).

**Saída:** operação remota sobrevive com documentação + logs; console web pode ainda não existir.

### IA-2 — MVP Ops + Executivo (F7D–F7E)

**Meta:** CEO e Operações respondem “o sistema está saudável?” e “piorou na última semana?” sem abrir o banco.

- **Business metrics dashboard** — tarefa **7E.7** (`/admin/metrics` ou rota equivalente): runs/dia, taxa de sucesso, p95, workspaces ativos, uploads/dia, custo médio LLM por run (quando métricas existirem).
- Fonte de dados agregados privacy-first — **7D.9** (`UsageMetric`).
- Links para health, Sentry, uptime (**7C.4**, **7C.6**, **7E.6**).
- Lista/filtro de **pipeline runs** problemáticos (integra **7E.1** stuck detector).
- **Versão de release** visível (alinha a tracking Sentry).

**Critério de pronto:** incidente de pipeline triado em tempo interno alvo (ex.: &lt; 15 min) usando console + runbook.

### IA-3 — CS Lite (pré-beta / beta)

**Meta:** Atendimento resolve a maior parte dos tickets sem engenharia.

- Busca por **email / id de usuário** → workspaces, roles, convites (metadados).
- **Timeline operacional** por workspace (últimos runs, estágio falho, contagens `needs_review`).
- Ações de **baixo risco** auditadas (ex.: desbloqueio manual alinhado a **7B.13**, se API existir).
- **Support bundle** JSON com redaction (preferível a tela cheia de dados do cliente).
- Links para **7E.10** `SUPPORT.md` e templates **7E.9**.

### IA-4 — Financeiro + Legal (pós-billing ou volume LGPD)

**Meta:** Financeiro e Legal não dependem de exports ad hoc à engenharia.

- Visão read-only de **billing** (Stripe ou equivalente) + export CSV para contabilidade — depende de **billing real** (ver [ROADMAP.md](../../_MOC/_generated/ROADMAP.md) F10).
- **Fila DSAR** com estados, SLA 15 dias, evidência em audit (**7B.18**).
- Fluxos guiados de exclusão/anonimização com confirmação dupla onde necessário — podem espelhar os fluxos já validados em **IA-0**.

---

## 4. Personas × fase (resumo)

| Persona | IA-0 (UI local) | IA-1 | IA-2 | IA-3 | IA-4 |
|---------|-----------------|------|------|------|------|
| CEO / fundador | Dashboard de métricas na UI local | — | Métricas agregadas UI remota | + tendências | + receita (billing) |
| Operações | Purge, métricas, leitura relatórios pela UI web em `127.0.0.1` | Runbook + logs | Health + runs + stuck | Drill-down + bundles | + checks compliance |
| Atendimento | Reset senha, exclusão conta/doc pela UI (com confirmação dupla) | SUPPORT.md | Links úteis | Busca + timeline | Triage DSAR |
| Financeiro | Export CSV de uso pela UI | — | — | Export uso (se aplicável) | Stripe + CSV |
| Legal / LGPD | Exclusão/limpeza pela UI com evidência em audit log | — | — | Metadados pedidos | Fila DSAR + conclusão auditada |

---

## 5. Mapa de dependências (backlog existente)

| Item | Papel |
|------|--------|
| **7F.L1 + 7F.L2 + 7F.10–7F.14** | Implementação da **IA-0** no [BACKLOG F7F-Local](../../BACKLOG.md#f7f-local--pré-produção-ia-0-sem-oauth): camada de serviço + UI web localhost (principal) + exclusão de conta, senha, purge, métricas, relatórios read-only. |
| **7F.9** | CLI interno **secundário**, entregue após UI estabilizada; reutiliza a camada de 7F.L1 sem duplicar regra. |
| **F7F-Local (IA-0)** | **Pode anteceder** F7A/B/C inteiros e **7F.1–7F.4**. UI só em **localhost** até haver auth staff. Ao expor na rede, obedecer prefixo `/api/internal/`, RBAC **7F.3** e **7F.4**. |
| **7E.7** | Núcleo visual da **IA-2** (dashboard de negócio) — reaproveita o layout de 7F.13 com telemetria mais rica. |
| **7D.9** | Telemetria agregada privacy-first — evolução das métricas já calculadas em **IA-0** (7F.13). |
| **7E.1** | Runs presos → widgets/listas no console. |
| **7E.11–7E.12** | Custos LLM no contexto operacional. |
| **7B.5** | Audit para ações internas; a camada de serviço (7F.L1) grava em `logs/internal_ops_audit.log` em IA-0 e passa a gravar em tabela quando 7B.5 persistir, sem mudar UI. |
| **7B.13** | Unlock manual → candidato a ação **IA-3**. |
| **7B.18** | DSAR → **IA-4** (ou visão read-only antes). |
| **7C.5 / 7C.4** | Correlação e erros sem UI nova pesada. |
| **F7F-Remote (7F.1–7F.8)** | Tarefas de produção do console (auth staff, RBAC, `/api/internal/`, CS, Financeiro); **7F.1** (ADR) pode iniciar em paralelo à IA-0. |

---

## 6. Métricas de sucesso

- **IA-0:** operador conclui em &lt; 30 min (alvo inicial) exclusão de conta, purge de documentos ou leitura de últimos relatórios **pela UI web local + documentação no runbook**, sem SQL ad hoc e sem precisar de shell — ajustar alvo após primeiros runs.
- Tempo médio até **diagnóstico** de falha de pipeline (definir alvo interno após IA-2).
- **% tickets** de CS escalados para eng (meta: queda após IA-3).
- **100%** das ações internas mutadoras com registro auditável (amostragem trimestral).
- **DSAR:** percentual concluído dentro do SLA após IA-4.

---

## 7. Diagrama de contexto

```text
[ Usuário final ] → App Mathoms AI (workspace, pipeline, relatório, /config )
                         ↑
[ Operadores ] → F7F-Local (IA-0): UI web em 127.0.0.1 (principal) + CLI (secundário)
                 └─ camada de serviço compartilhada + audit em logs/
                 ↓
                 F7F-Remote (IA-1…IA-4): Console em ops.mathoms.ai
                 └─ OAuth staff · RBAC · /api/internal/* · dashboard 7E.7
                        ↔ Stripe · Zendesk/Linear · Grafana/Sentry
```

---

## 8. Governança do documento

- **Escopo macro** e fases: este arquivo.
- **Tasks estimáveis:** [BACKLOG.md — F7F](../../BACKLOG.md#f7f--console-interno-operadores) — **F7F-Local (IA-0):** `7F.L1` camada de serviço, `7F.L2` UI web localhost, `7F.10`–`7F.14` business logic (exclusão, senha, purge, métricas, relatórios), `7F.9` CLI secundário. **F7F-Remote (IA-1…IA-4):** `7F.1`–`7F.8`.
- **Decisões técnicas** (auth staff, break-glass): [DECISIONS.md](../../DECISIONS.md) quando implementadas.
