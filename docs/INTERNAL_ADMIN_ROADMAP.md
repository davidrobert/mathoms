# Fin — Console interno (operadores)

> Interface administrativa para **quem opera o produto** (CEO, Operações, Atendimento, Financeiro, Legal/LGPD), distinta do app do cliente (`/config` do workspace).
>
> **Última atualização:** 2026-04-16
>
> **Backlog executável:** [BACKLOG.md — F7F](BACKLOG.md#f7f--console-interno-operadores)

---

## 1. Objetivo

Oferecer uma superfície **autenticada, separada do usuário final**, com **least privilege** e **auditoria**, para diagnosticar a plataforma, apoiar clientes e cumprir obrigações (LGPD, financeiro) sem depender apenas de SQL, SSH e ferramentas externas.

**Não é:** substituir Stripe Dashboard, Sentry ou Grafana na totalidade; substituir o `/config` do workspace (governança do cliente).

---

## 2. Princípios de arquitetura

| # | Princípio |
|---|-----------|
| P1 | **Host e credenciais separados** do login do cliente (ex.: subdomínio `ops.*`, SSO da empresa, 2FA quando aplicável). |
| P2 | **RBAC interno** (papéis como operador, suporte, financeiro, superadmin raro) com permissões explícitas na API. |
| P3 | Ação que altera estado do cliente ou expõe dado sensível: **motivo obrigatório** + registro em **audit log** (alinha a 7B.5). |
| P4 | APIs dedicadas sob prefixo controlado (ex.: `/api/internal/...`) com guard por **ambiente**, **allowlist** (IP/VPN) e testes de autorização. |
| P5 | **Minimização de dados:** visão padrão = metadados e agregados; PII/valores apenas em fluxos explícitos (“break glass”) com política documentada. |

---

## 3. Fases (IA-0 … IA-3)

### IA-0 — Fundação (paralelo a F7A–F7C)

**Meta:** trilhas e dados existirem antes de investir em UI rica.

- Runbook de deploy/recuperação (**7C.7**).
- **Structured logging** + correlação request/Celery (**7C.5**).
- **Audit log** para writes sensíveis (**7B.5**).
- Decisão documentada: **sem impersonation** do cliente ou fluxo “break glass” com TTL, notificação e ADR (**7F.1** no backlog).

**Saída:** operação sobrevive com documentação + logs; console pode ainda não existir.

### IA-1 — MVP Ops + Executivo (F7D–F7E)

**Meta:** CEO e Operações respondem “o sistema está saudável?” e “piorou na última semana?” sem abrir o banco.

- **Business metrics dashboard** — tarefa **7E.7** (`/admin/metrics` ou rota equivalente): runs/dia, taxa de sucesso, p95, workspaces ativos, uploads/dia, custo médio LLM por run (quando métricas existirem).
- Fonte de dados agregados privacy-first — **7D.9** (`UsageMetric`).
- Links para health, Sentry, uptime (**7C.4**, **7C.6**, **7E.6**).
- Lista/filtro de **pipeline runs** problemáticos (integra **7E.1** stuck detector).
- **Versão de release** visível (alinha a tracking Sentry).

**Critério de pronto:** incidente de pipeline triado em tempo interno alvo (ex.: &lt; 15 min) usando console + runbook.

### IA-2 — CS Lite (pré-beta / beta)

**Meta:** Atendimento resolve a maior parte dos tickets sem engenharia.

- Busca por **email / id de usuário** → workspaces, roles, convites (metadados).
- **Timeline operacional** por workspace (últimos runs, estágio falho, contagens `needs_review`).
- Ações de **baixo risco** auditadas (ex.: desbloqueio manual alinhado a **7B.13**, se API existir).
- **Support bundle** JSON com redaction (preferível a tela cheia de dados do cliente).
- Links para **7E.10** `SUPPORT.md` e templates **7E.9**.

### IA-3 — Financeiro + Legal (pós-billing ou volume LGPD)

**Meta:** Financeiro e Legal não dependem de exports ad hoc à engenharia.

- Visão read-only de **billing** (Stripe ou equivalente) + export CSV para contabilidade — depende de **billing real** (ver [ROADMAP.md](ROADMAP.md) F10).
- **Fila DSAR** com estados, SLA 15 dias, evidência em audit (**7B.18**).
- Fluxos guiados de exclusão/anonimização com confirmação dupla onde necessário.

---

## 4. Personas × fase (resumo)

| Persona | IA-0 | IA-1 | IA-2 | IA-3 |
|---------|------|------|------|------|
| CEO / fundador | — | Métricas agregadas | + tendências | + receita agregada (billing) |
| Operações | Runbook + logs | Health + runs + stuck | Drill-down + bundles | + checks compliance |
| Atendimento | SUPPORT.md | Links úteis | Busca + timeline | Triage DSAR |
| Financeiro | — | — | Export uso (se aplicável) | Stripe + CSV |
| Legal / LGPD | — | — | Metadados pedidos | Fila DSAR + conclusão auditada |

---

## 5. Mapa de dependências (backlog existente)

| Item | Papel |
|------|--------|
| **7E.7** | Núcleo visual da **IA-1** (dashboard de negócio). |
| **7D.9** | Telemetria agregada privacy-first. |
| **7E.1** | Runs presos → widgets/listas no console. |
| **7E.11–7E.12** | Custos LLM no contexto operacional. |
| **7B.5** | Audit para ações internas. |
| **7B.13** | Unlock manual → candidato a ação **IA-2**. |
| **7B.18** | DSAR → **IA-3** (ou visão read-only antes). |
| **7C.5 / 7C.4** | Correlação e erros sem UI nova pesada. |
| **7F.\*** | Tarefas transversais do console (ver [BACKLOG.md](BACKLOG.md)). |

---

## 6. Métricas de sucesso

- Tempo médio até **diagnóstico** de falha de pipeline (definir alvo interno após IA-1).
- **% tickets** de CS escalados para eng (meta: queda após IA-2).
- **100%** das ações internas mutadoras com registro auditável (amostragem trimestral).
- **DSAR:** percentual concluído dentro do SLA após IA-3.

---

## 7. Diagrama de contexto

```text
[ Usuário final ] → App Fin (workspace, pipeline, relatório, /config )
                         ↑
[ Operadores ] → Console interno (RBAC, audit, agregados)
                        ↔ Stripe · Zendesk/Linear · Grafana/Sentry
```

---

## 8. Governança do documento

- **Escopo macro** e fases: este arquivo.
- **Tasks estimáveis:** [BACKLOG.md — F7F](BACKLOG.md#f7f--console-interno-operadores).
- **Decisões técnicas** (auth staff, break-glass): [DECISIONS.md](DECISIONS.md) quando implementadas.
