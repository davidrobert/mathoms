# Comunicação de incidentes — templates

Templates em **pt-BR** para publicação na **status page** e, quando aplicável, e-mail ou post interno.

| Arquivo | Uso |
| --- | --- |
| [initial_report.pt-BR.md](initial_report.pt-BR.md) | Primeira comunicação após detecção |
| [update_in_progress.pt-BR.md](update_in_progress.pt-BR.md) | Atualizações durante investigação ou mitigação |
| [resolved_postmortem.pt-BR.md](resolved_postmortem.pt-BR.md) | Encerramento + causa raiz + follow-up |

## Placeholders

Substituir antes de publicar:

| Placeholder | Significado |
| --- | --- |
| `{{INCIDENT_ID}}` | ID curto (ex.: `INC-2026-04-17-001`) |
| `{{SEVERITY}}` | `minor` \| `major` \| `critical` |
| `{{AFFECTED_AREAS}}` | Lista: API, app web, pipeline, worker, Redis, etc. |
| `{{ETA_NEXT_UPDATE}}` | Horário ou duração (ex.: “em 30 minutos”) |
| `{{STARTED_AT_UTC}}` / `{{RESOLVED_AT_UTC}}` | ISO 8601 |

Ver processo completo em [RUNBOOK.md](../../RUNBOOK.md#resposta-a-incidentes).
