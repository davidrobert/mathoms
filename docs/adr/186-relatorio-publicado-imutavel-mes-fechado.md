---
id: ADR-186
type: adr
title: "Relatório publicado é imutável — conceito de mês fechado"
status: Decidido
phase: A11.report-publication
date: "2026-05-10"
relates_to:
  - "[[ADR-129]]"
  - "[[ADR-136]]"
  - "[[ADR-143]]"
supersedes: []
superseded_by: []
aliases: ["ADR 186", "Mês fechado", "Report publication immutability"]
tags:
  - area/report
  - area/methodology
  - phase/a11
  - status/decidido
  - type/adr
---

## Contexto

O Mathoms hoje **não tem** conceito formal de "relatório publicado" ou
"mês fechado". O artefato E7 é gerado on-demand no read-path; não há
flag de imutabilidade nem timestamp persistido de "entrega ao cliente".

ADR de learning loop (em rascunho — A12) (learning loop de categorização) introduz **re-categorização
retroativa** de transações sem override manual quando uma regra nova é
aprovada. Sem o conceito de mês fechado, regras criadas em maio podem
mudar gráficos de janeiro — quebrando o contrato implícito com o cliente
("o relatório que recebi não muda sozinho"). [[ADR-136]] (Decision
aggregate) tem necessidade análoga: evento "decisão fechada" não deve
ser re-escrito por mudança de input downstream.

**Por que isso importa metodologicamente:**

- **AUVP** fecha mês com diagnóstico consolidado + cadência de aporte +
  rebalanceamento. Se o diagnóstico do mês 01 muda no mês 06, a cadência
  fica revisionista.
- **Cerbasi** entrega relatório como "fotografia" do estado financeiro;
  fotografia que muda no álbum quebra a metáfora.
- **Perini** depende de série temporal estável de custo de vida pra
  calcular patrimônio-alvo; recalcular passado é aceitável **operacional­mente**
  mas precisa ser **explícito**, nunca silencioso.

## Decisão

Adotar **conceito de "report publication"** como evento explícito,
imutável e auditável, com 3 mudanças mínimas:

### D1. Tabela `report_publications` (nova)

```sql
CREATE TABLE report_publications (
  id              UUID PRIMARY KEY,
  workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  period_yyyymm   CHAR(6) NOT NULL,                 -- '202601'
  artifact_id     UUID NOT NULL REFERENCES pipeline_artifacts(id),
  published_at    TIMESTAMPTZ NOT NULL,
  published_by    VARCHAR(64) NOT NULL,             -- user_id ou 'system'
  immutable_hash  VARCHAR(64) NOT NULL,             -- SHA-256 do snapshot E7 publicado
  unpublished_at  TIMESTAMPTZ NULL,                 -- soft-delete: nunca apaga linha
  UNIQUE (workspace_id, period_yyyymm) WHERE unpublished_at IS NULL
);
```

**Semântica:** uma linha **viva** (`unpublished_at IS NULL`) significa
"este mês está fechado para este workspace". Despublicar é evento
explícito (escreve `unpublished_at`) — mantém o histórico para auditoria.

### D2. API: `is_month_closed(workspace_id, period_yyyymm) -> bool`

Helper canônico em `backend/app/services/report_publication.py`. Único
ponto de leitura. Re-categorização retroativa, edição de transação em
mês passado, qualquer ação que muda dado consolidado **consulta este
helper** e respeita a barreira.

### D3. Quem publica

V1 (escopo desta ADR): publicação **manual e explícita** via
`POST /workspaces/{ws}/reports/{period}/publish`. Sem auto-publish. Sem
deadline. Cliente/planejador decide quando o mês está fechado.

V2 (futuro, fora desta ADR): auto-publish após X dias do fim do mês,
com janela de "edição quente" antes.

## Alternativas consideradas

| # | Opção | Por que rejeitada |
|---|---|---|
| **A** | Coluna `published_at` em `pipeline_artifacts` direto. | Artefato E7 é regenerável; coluna no artefato confunde "existe artefato" com "foi publicado". Tabela separada é limpa. |
| **B** | Boolean `is_published` sem timestamp/hash. | Perde auditabilidade. Hash imutável detecta tentativa de "re-publicar com diferente". |
| **C** | Auto-publish após N dias. | Custo cognitivo: usuário recebe e-mail "seu mês foi fechado" em momento que ele não controla. V1 manual é mais previsível. |
| **D** | Não decidir agora; deixar ADR de learning loop (em rascunho — A12) re-categorizar tudo retroativo sem barreira. | Quebra confiança (lição Mint/Copilot). Não-negociável pra produto premium. |

## Consequências

**Positivas:**

- Habilita ADR de learning loop (em rascunho — A12) sem violar confiança do cliente.
- Snapshot fiel do mês entregue (PDF assinado) tem ancoragem em DB.
- Reusa pra outros invariantes futuros (Decision histórica, IRPF
  declarado, cenário comparativo).

**Negativas / custos:**

- Migration Alembic nova.
- API nova (publish/unpublish).
- UX nova mínima: indicador "mês fechado" no relatório + ação
  "publicar" em algum lugar (escopo `product-designer` separado).

**Riscos:**

- Workspace antigo sem publicações → comportamento default? **Default
  inclusive** — se não tem publicação, mês NÃO está fechado, regras
  re-categorizam livre. Backfill manual opcional pra clientes legados.

## Critério de aceite

- [ ] Tabela `report_publications` criada via Alembic.
- [ ] Endpoint `POST /workspaces/{ws}/reports/{period}/publish` +
      `DELETE` (unpublish) com `response_model` explícito ([[ADR-109]]).
- [ ] Helper `is_month_closed()` documentado + testes unitários.
- [ ] Indicador visual de "mês fechado" no relatório (badge cinza no
      header da seção mensal).
- [ ] Documentação `docs/reference/REPORT_PUBLICATION.md` explicando
      semântica + invariantes.

## Handoffs

- `senior-cto` revisa contrato API + API de leitura.
- `data-engineer` revisa migration + backfill (workspaces existentes
  ficam unpublished by default).
- `financial-planner` revisa **default policy** (workspace sem
  publicação = aberto) sob ótica AUVP.
- `product-designer` desenha indicador visual e fluxo de publicar.
- `product-manager` decide priorização vs ADR de learning loop (em rascunho — A12) (esta é
  pré-requisito).
