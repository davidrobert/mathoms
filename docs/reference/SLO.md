# Mathoms AI — Objetivos de nível de serviço (SLO)

> Referência para beta e GA. Alertas (ex.: Sentry) devem respeitar margem em relação a estes alvos. Ver [RUNBOOK.md](RUNBOOK.md).

## Disponibilidade

| Período | Alvo de uptime (API + app web servindo HTTP 2xx) |
| --- | --- |
| Beta | ≥ 99,0% mensal |
| GA | ≥ 99,5% mensal |

Medição recomendada: monitor externo (ex.: health checks a cada 1–5 min) + status page.

## Latência API

| Métrica | Alvo |
| --- | --- |
| p95 em endpoints autenticados típicos | menos de 1 s (excluindo upload pesado e jobs longos) |

## Pipeline

| Modo | Alvo p95 (tempo até conclusão ou falha terminal) |
| --- | --- |
| Free (sem LLM) | menos de 5 min para workspace de referência (dogfood) |
| Premium (LLM) | menos de 15 min para workspace de referência |

## Incidentes — comunicação (7E.9)

| Compromisso | Alvo |
| --- | --- |
| Primeira publicação na status page após **detecção interna** do incidente user-facing | **menos de 15 minutos** |
| Atualizações durante incidente aberto | A cada **30–60 min** ou ao mudar o impacto |

RPO/RTO de dados: ver [RUNBOOK.md](RUNBOOK.md) (secção *Disaster recovery*) e tarefas 7E.2–7E.4 no [BACKLOG.md](../BACKLOG.md).
