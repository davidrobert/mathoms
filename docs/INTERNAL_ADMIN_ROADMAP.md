# Mathoms AI — Console interno (operadores)

> Interface administrativa para **quem opera o produto** (CEO, Operações, Atendimento, Financeiro, Legal/LGPD), distinta do app do cliente (`/config` do workspace).
>
> **Última atualização:** 2026-04-16
>
> **Backlog executável:** [BACKLOG.md — F7F](BACKLOG.md#f7f--console-interno-operadores)

---

## 1. Objetivo

Oferecer uma superfície **separada do usuário final**, com **least privilege** e **auditoria**, para diagnosticar a plataforma, apoiar clientes e cumprir obrigações (LGPD, financeiro) sem depender apenas de SQL, SSH e ferramentas externas. A **primeira entrega** é **local e executável**: **CLI/scripts** e, se desejado, **interface web mínima em localhost** (mesmas operações e guardrails — ver **IA-0**). **Autenticação staff** para console acessível na rede e **UI hospedada** vêm nas fases seguintes (**7F.2–7F.4**).

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

## 3. Fases (IA-0 … IA-4)

A **primeira etapa executável** é **local** (máquina do operador com repo, `DATABASE_URL` e storage apontando para o mesmo ambiente que se deseja administrar — em geral **dev/staging**; produção só com runbook e flags explícitas). Pode ser **só CLI** ou **CLI + UI web** rodando no mesmo host: a UI não substitui o CLI para automação, mas é viável na v1 (**7F.15** no backlog). **Não** há deploy de console na internet nesta etapa.

### IA-0 — Operações locais (primeira etapa — executável já)

**Meta:** com backend + DB + storage configurados localmente (ou túnel/VPN para staging), o operador executa tarefas de suporte e LGPD **sem depender** de um console **hospedado** na internet.

**Escopo mínimo (checklist de pronto):**

| Área | O que entregar |
|------|----------------|
| **Contas** | Excluir conta de usuário com cascata coerente: memberships, convites, vínculos a workspaces; política **hard delete** vs **anonimização** documentada em uma linha no script/README interno. |
| **Credenciais** | Alterar senha manualmente (hash no mesmo algoritmo do app — ex.: bcrypt/Argon2 conforme modelo `User`) via CLI com confirmação interativa ou `--user-id` + `--password` (evitar echo em histórico; preferir prompt). |
| **Documentos** | Apagar documentos de um **usuário** ou **workspace** deletando registros no BD **e** objetos no **storage** (`stored_path` / camadas em [storage](../backend/app/services/storage.py)); suportar `--dry-run` listando o que seria removido. |
| **Métricas** | Métricas de utilização **agregadas** via queries ou script: uploads por período, runs de pipeline (sucesso/falha), contagem de workspaces/documentos, volume storage quando aplicável — suficiente para CSV/stdout; evolução para `UsageMetric` (**7D.9**) e dashboard **7E.7** nas fases seguintes. |
| **Relatórios** | Acesso **somente leitura** aos últimos relatórios de uma conta: identificar por `user_id` / `workspace_id`, listar `Report` (ou runs) recentes e permitir dump JSON/metadata ou abrir HTML exportado quando existir referência no modelo — **sem** edição nem reexecução de pipeline pelo mesmo canal. |
| **UI web local** | Página(s) mínima(s) servidas só em **localhost** (ex.: rota Next em dev ou painel FastAPI), chamando a **mesma camada de serviço** que o CLI — sem duplicar regra de negócio. Tarefa **7F.15**. |

**Guardrails locais (obrigatórios no desenho):**

- **Dry-run** como padrão ou confirmação explícita (`TYPE "delete"`) em qualquer exclusão.
- Bloqueio se `ENVIRONMENT=production` (ou equivalente) **salvo** flag `--i-accept-production-risk` + variável de ambiente explícita — evita apagar dados reais por engano.
- **UI em IA-0:** habilitar só com flag de env explícita (ex.: `INTERNAL_OPS_UI_ENABLED=1`); servidor escuta **apenas 127.0.0.1**; não reutilizar cookie/sessão do app do cliente; mutações na UI seguem o mesmo audit que o CLI.
- Trilha mínima: append em log em `logs/` (operador, ação, alvo, timestamp) alinhada ao espírito de **7B.5**; quando o audit persistido existir, os mesmos scripts passam a gravar na tabela de audit.

**Saída:** operador usa CLI e/ou UI local conforme documentação / runbook. **7F.2–7F.4** não são obrigatórios para fechar IA-0: são a evolução para **auth staff + exposição controlada na rede**. Rotas sob prefixo interno **só em dev** (localhost) podem existir antes do pacote completo **7F.4** em produção.

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

- Visão read-only de **billing** (Stripe ou equivalente) + export CSV para contabilidade — depende de **billing real** (ver [ROADMAP.md](ROADMAP.md) F10).
- **Fila DSAR** com estados, SLA 15 dias, evidência em audit (**7B.18**).
- Fluxos guiados de exclusão/anonimização com confirmação dupla onde necessário — podem espelhar os fluxos já validados em **IA-0**.

---

## 4. Personas × fase (resumo)

| Persona | IA-0 (local) | IA-1 | IA-2 | IA-3 | IA-4 |
|---------|--------------|------|------|------|------|
| CEO / fundador | Métricas via script/CSV | — | Métricas agregadas UI | + tendências | + receita (billing) |
| Operações | Purge, métricas, leitura relatórios (CLI e/ou UI localhost) | Runbook + logs | Health + runs + stuck | Drill-down + bundles | + checks compliance |
| Atendimento | Reset senha, exclusão conta/doc (com processo) | SUPPORT.md | Links úteis | Busca + timeline | Triage DSAR |
| Financeiro | Export uso bruto (queries) | — | — | Export uso (se aplicável) | Stripe + CSV |
| Legal / LGPD | Exclusão/limpeza com evidência em log | — | — | Metadados pedidos | Fila DSAR + conclusão auditada |

---

## 5. Mapa de dependências (backlog existente)

| Item | Papel |
|------|--------|
| **7F.9–7F.15** | Implementação da **IA-0** no [BACKLOG F7F](BACKLOG.md#f7f--console-interno-operadores) (CLI + opcional UI localhost **7F.15**; exclusão de conta, senha, purge, métricas, relatórios read-only). |
| **IA-0 (local)** | Pode anteceder **7F.2–7F.4**; UI só em **localhost** até haver auth staff. Ao expor na rede/internet, obedecer prefixo `/api/internal/`, RBAC **7F.3** e **7F.4**. |
| **7E.7** | Núcleo visual da **IA-2** (dashboard de negócio). |
| **7D.9** | Telemetria agregada privacy-first — evolução das métricas já calculadas em **IA-0**. |
| **7E.1** | Runs presos → widgets/listas no console. |
| **7E.11–7E.12** | Custos LLM no contexto operacional. |
| **7B.5** | Audit para ações internas; espelhar em tabela quando sair do log em arquivo. |
| **7B.13** | Unlock manual → candidato a ação **IA-3**. |
| **7B.18** | DSAR → **IA-4** (ou visão read-only antes). |
| **7C.5 / 7C.4** | Correlação e erros sem UI nova pesada. |
| **7F.\*** | Tarefas transversais do console (ver [BACKLOG.md](BACKLOG.md)); **7F.1** deve estar clara antes de expor **fora de localhost** o que **IA-0** faz em CLI/UI. |

---

## 6. Métricas de sucesso

- **IA-0:** operador conclui em &lt; 30 min (alvo inicial) exclusão de conta, purge de documentos ou leitura de últimos relatórios **com documentação + CLI e/ou UI local**, sem SQL ad hoc — ajustar alvo após primeiros runs.
- Tempo médio até **diagnóstico** de falha de pipeline (definir alvo interno após IA-2).
- **% tickets** de CS escalados para eng (meta: queda após IA-3).
- **100%** das ações internas mutadoras com registro auditável (amostragem trimestral).
- **DSAR:** percentual concluído dentro do SLA após IA-4.

---

## 7. Diagrama de contexto

```text
[ Usuário final ] → App Mathoms AI (workspace, pipeline, relatório, /config )
                         ↑
[ Operadores ] → IA-0: CLI + UI localhost opcional (DB + storage) → IA-1…: Console interno remoto (RBAC, audit, agregados)
                        ↔ Stripe · Zendesk/Linear · Grafana/Sentry
```

---

## 8. Governança do documento

- **Escopo macro** e fases: este arquivo.
- **Tasks estimáveis:** [BACKLOG.md — F7F](BACKLOG.md#f7f--console-interno-operadores) (**7F.9–7F.15** = IA-0; **7F.15** = UI web apenas em **localhost**, mesma regra de negócio que o CLI).
- **Decisões técnicas** (auth staff, break-glass): [DECISIONS.md](DECISIONS.md) quando implementadas.
