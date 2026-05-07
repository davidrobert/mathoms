# Template — comunicação inicial de incidente

**Status sugerido na status page:** Investigating / Em análise

---

## Texto para usuários (copiar e ajustar)

**[Incidente {{INCIDENT_ID}}] — {{TÍTULO_CURTO}}**

Estamos investigando uma anomalia que pode afetar: **{{AFFECTED_AREAS}}**.

**O que você pode perceber:** {{SINTOMAS_USUARIO_EM_LINGUAGEM_SIMPLES}}

**O que já estamos fazendo:** equipe atuando na causa; próxima atualização em **{{ETA_NEXT_UPDATE}}**.

Gravidade interna: **{{SEVERITY}}**. Início (UTC): **{{STARTED_AT_UTC}}**.

---

## Exemplo preenchido (fictício)

**[INC-2026-04-17-001] — Lentidão ao processar documentos**

Estamos investigando uma anomalia que pode afetar: **processamento de pipeline (worker) e fila de tarefas**.

**O que você pode perceber:** o botão “Processar documentos” pode demorar mais que o habitual ou permanecer em processamento por vários minutos.

**O que já estamos fazendo:** equipe atuando na causa; próxima atualização em **30 minutos**.

Gravidade interna: **major**. Início (UTC): **2026-04-17T14:22:00Z**.
