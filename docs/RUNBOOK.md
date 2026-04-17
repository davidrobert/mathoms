# Fin — Runbook operacional

> Procedimentos para deploy, incidentes e recuperação. Complementa [SETUP.md](SETUP.md). **Sprint A (2026-04-17):** templates de incidente, status page no app, drill documentado.

---

## 1. Visão geral

| Recurso | Onde |
| --- | --- |
| API + OpenAPI | `FIN_*` em `.env`, uvicorn, ver SETUP |
| Worker | Celery + Redis |
| Frontend | Next.js; variável opcional `NEXT_PUBLIC_FIN_STATUS_PAGE_URL` |
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
NEXT_PUBLIC_FIN_STATUS_PAGE_URL=https://status.seudominio.com
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
| 1 | Status page acessível e URL configurada em `NEXT_PUBLIC_FIN_STATUS_PAGE_URL` | ☐ |
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

Valores de referência estão em [SLO.md](SLO.md). Procedimentos de backup, restore e off-site: tarefas **7E.2–7E.4** e [BACKLOG.md](BACKLOG.md#f7--produção--lgpd).

---

## 6. Rotação de segredos e escalação

- **FERNET_KEY**, **JWT secret:** ver SETUP e tarefas F7.
- Escalação: definir contato on-call antes do beta (preencher aqui quando existir).

---

## 7. Referências

- [SLO.md](SLO.md) — SLOs e SLAs de comunicação
- [BACKLOG.md](BACKLOG.md) — 7E (operational readiness)
- [SMOKE_TEST.md](SMOKE_TEST.md) — verificações manuais pré-release
