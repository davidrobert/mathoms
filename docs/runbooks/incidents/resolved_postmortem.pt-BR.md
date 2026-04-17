# Template — incidente resolvido / encerramento

**Status sugerido na status page:** Resolved

---

## Texto para usuários (copiar e ajustar)

**Resolvido — {{INCIDENT_ID}}**

**Resumo:** {{O_QUE_FOI_CORRIGIDO_EM_UMA_FRASE}}

**Duração aproximada:** de **{{STARTED_AT_UTC}}** a **{{RESOLVED_AT_UTC}}** (UTC).

**Causa (alto nível):** {{CAUSA_RAIZ_OU_INVESTIGACAO_EM_ANDAMENTO}}

**Próximos passos:** {{FOLLOW_UP_EX_POSTMORTEM_INTERNO}}

Agradecemos a paciência. Em caso de comportamento anômalo recorrente, contacte **{{CANAL_SUPORTE}}**.

---

## Exemplo preenchido (fictício)

**Resolvido — INC-2026-04-17-001**

**Resumo:** normalizamos a fila de processamento e reiniciamos os workers com a configuração correta; tempos de pipeline voltaram ao patamar habitual.

**Duração aproximada:** de **2026-04-17T14:22:00Z** a **2026-04-17T16:05:00Z** (UTC).

**Causa (alto nível):** acúmulo de mensagens na fila após restart não coordenado do broker; mitigado com drenagem e health check automatizado.

**Próximos passos:** revisão interna da ordem de deploy (documentado no post-mortem); nenhuma ação obrigatória para usuários.

Agradecemos a paciência. Em caso de comportamento anômalo recorrente, contacte o suporte pelo canal habitual do workspace.
