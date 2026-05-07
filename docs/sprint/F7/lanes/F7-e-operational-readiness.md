---
id: F7.e
type: lane
title: "Operational Readiness (semana 6-7, ~2 semanas)"
sprint: F7
status: shipped
priority: P0
adrs: ["[[ADR-065]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f7
  - status/shipped
  - priority/p0
---


# 7E — Operational Readiness (semana 6-7, ~2 semanas)


> Sub-fase dedicada à maturidade operacional além de "produto compila e sobe": runs órfãs, disaster recovery testado, observabilidade de negócio (não só erros), comunicação durante incidentes, e proteção contra runaway de custo LLM (BYOK não isenta de monitoring). Ver [ADR-065](DECISIONS.md#adr-065--sub-fase-7e-operational-readiness).

#### 7E.A — Pipeline operacional

| #     | Tarefa                                                                                                                                                                       | Prio | Est. | Status |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.1  | **Stuck pipeline run detector**: campo `last_heartbeat_at` em `PipelineRun`, atualizado a cada stage; Celery beat task roda a cada 5min e marca como `failed` runs sem heartbeat há >1h; notification automática | P0 | 4h | ☐ |

#### 7E.B — Disaster recovery

| #     | Tarefa                                                                                                                                       | Prio | Est. | Status |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.2  | **Restore drill quarterly**: documentado em RUNBOOK; executar pré-beta; gravar tempo real (RTO efetivo); checklist de validação pós-restore | P0 | 3h | ☐ |
| 7E.3  | **RPO/RTO declarados**: docs/SLO.md com targets (RPO=24h, RTO=4h propostos para dogfood; RPO=1h, RTO=1h para beta)                          | P0 | 1h | ☐ |
| 7E.4  | **Off-site backup** (S3 BR ou Backblaze B2): pg_dump diário replicado fora do Hetzner; rotação 30d off-site; restore testado de off-site    | P0 | 4h | ☐ |
| 7E.5  | **FERNET_KEY loss recovery**: procedure documentado em RUNBOOK; teste em ambiente staging que simula key perdida; backup criptografado da key em local separado (ex: 1Password vault) | P0 | 3h | ☐ |

#### 7E.C — Observabilidade de negócio

| #     | Tarefa                                                                                                                                                                                                          | Prio | Est. | Status |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.6  | **Status page público** (`uptime-kuma` self-hosted ou `instatus.com` free tier): incidentes manuais + uptime auto; link na footer do app                                                                       | P1 | 3h | ✅ Sprint A: `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL` + `StatusPageFooter` (login, register, invite, AppShell); provisão da ferramenta continua no deploy — ver [RUNBOOK.md](RUNBOOK.md#2-status-page-7e6) |
| 7E.7  | **Business metrics dashboard**: query simples + página interna `/admin/metrics`: runs/day, success rate trend (7d/30d), p95 duration, custo médio LLM por run, documents uploaded/day, active workspaces — integra **IA-2** do [INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md) (protegida por **7F.2–7F.4**) | P1 | 6h | ☐ |
| 7E.8  | **SLOs/SLAs declarados** em `docs/SLO.md`: uptime 99% beta / 99.5% GA; p95 API <1s; p95 pipeline free <5min, premium <15min; alertas Sentry quando burn rate >2x                                                | P0 | 1h | ✅ Sprint A: [SLO.md](SLO.md) (alvos + SLA comunicação incidente); burn rate Sentry continua em 7C |

#### 7E.D — Comunicação de incidentes

| #     | Tarefa                                                                                                                                                                  | Prio | Est. | Status |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.9  | **Incident comms templates** em RUNBOOK: 3 templates Markdown (`initial_report`, `update_in_progress`, `resolved_postmortem`) com placeholders e exemplos preenchidos; treinar uso na primeira incident drill | P0 | 2h | ✅ Sprint A: [runbooks/incidents/](runbooks/incidents/) + [RUNBOOK.md](RUNBOOK.md#3-resposta-a-incidentes); drill checklist em [RUNBOOK.md](RUNBOOK.md#4-drill-de-incidente-obrigatório-antes-do-beta-fechado) |
| 7E.10 | **Support runbook** (`docs/SUPPORT.md`): triagem por severidade, templates de resposta para 5 perguntas comuns, fluxo de escalação, tempo de resposta esperado por tier | P1 | 4h | ☐ |

**Detalhamento — status page (7E.6) e incidentes (7E.9)**

| Área | O quê incluir |
| --- | --- |
| **Status page (7E.6)** | Ferramenta (`uptime-kuma`, Instatus, etc.): componentes **API**, **frontend**, **worker/Celery**, **Redis** (ou agregado “processamento”); incidentes **manuais** com título, descrição curta, severidade, atualizações; link público na **footer** do app e no e-mail de boas-vindas / suporte. SLA de conteúdo: incidente “investigating” em **menos de 15 minutos** após detecção interna (alinhado a 7E.8). |
| **7E.9 — Templates** | Três arquivos em `docs/` ou `runbooks/incidents/`: (1) **initial** — o quê falhou, impacto usuário, escopo (região/tier), próximo update em X min; (2) **update** — mitigação em curso, workaround; (3) **resolved** — causa raiz (se conhecida), duração, follow-up. Idioma **pt-BR** para usuários; técnico pode ser bilíngue. Placeholders: `{{INCIDENT_ID}}`, `{{SEVERITY}}`, `{{AFFECTED_AREAS}}`, `{{ETA_NEXT_UPDATE}}`. |
| **Processo** | Primeiro drill **antes do beta**: publicar incidente fictício, linkar status page, postar update e resolved; registrar tempo e melhorias no RUNBOOK. Opcional **P2:** banner in-app não bloqueante quando `status` API reportar incidente ativo (depende de endpoint ou scraping seguro). |

#### 7E.E — LLM cost runaway protection

| #     | Tarefa                                                                                                                                                                                                            | Prio | Est. | Status |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.11 | **LLM cost cap por workspace/mês**: campo `monthly_token_cap` em `LLMConfig` (default 1M tokens premium); incrementa em `usage_metric`; toast 80%/95% cap; hard stop em 100% (próxima call retorna 429 com explicação) | P0 | 5h | ☐ |
| 7E.12 | **Dashboard de custo por run**: agregação de `token_tracking` existente; UI em `/pipeline/runs/{id}` mostra custo total estimado por modelo; export CSV de uso mensal                                              | P1 | 3h | ☐ |
| 7E.13 | **API key validation pré-pipeline**: ping rápido ao modelo (`messages.count_tokens` ou similar barato) antes de iniciar; falha clara em 400 vs crash mid-stage com 500                                            | P0 | 2h | ☐ |
| 7E.14 | **Fallback model** quando primary rate-limited (429/529): retry com modelo secundário configurável (ex: claude-haiku se opus indisponível); log explícito em `PipelineStageLog`                                   | P1 | 4h | ☐ |

**Checkpoint:** zero pipeline runs órfãs >1h • restore drill executado em <RTO declarado • off-site backup verificado • FERNET recovery testado • status page no ar (**7E.6:** link no app + RUNBOOK; provisão do serviço no deploy) • business metrics dashboard renderizando • 3 incident templates prontos (**7E.9** ✅) • LLM cost cap funcionando com toast e hard stop • API key validation antes de cada run.
