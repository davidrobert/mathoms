---
id: TRACK-adr259-rule4-cpf-view
type: track
title: "ADR-259 rule 4 — UX decrypt de CPF em /reports/[id]: mascarado por default, 'ver completo' auditado"
plan: PLAN-llm-prompts-hardening
status: consumed
created_at: "2026-07-04"
consumed_at: "2026-07-06"
agent_role: general
tags:
  - type/track
  - area/security
  - area/backend
  - area/frontend
  - status/consumed
---

# Track — ADR-259 rule 4: CPF mascarado + "ver completo" auditado

> **Missão em 1 frase:** implementar a única regra pendente da [[ADR-259]]
> (flip `Decidido` em 2026-07-04, PR #775, com a rule 4 registrada como
> débito explícito): o dono do workspace vê o próprio CPF no relatório —
> mascarado por default, completo só mediante clique auditado — sem o CPF
> jamais tocar log, export ou job de background.

## Contexto (leia antes de codar — nesta ordem)

1. [[ADR-259]] §4 ("UX decrypt no boundary HTTP autenticado, mascarado por
   default") — a decisão está **tomada**; este track conforma, não reabre.
2. `backend/app/services/family_member_pii_service.py` — rules 1-3 vivas:
   CPF extraído por regex do documento original e cifrado em
   `FamilyMember.cpf_encrypted` via `backend/app/services/vault.py` (Fernet).
3. `backend/app/services/audit.py` (`AuditAction`) + model
   `backend/app/models/audit_log.py` — trilha de auditoria existente
   (precedente de uso: `override_v2_dualread_snapshot`).
4. `backend/app/services/_family_export_helpers.py:15` — decrypt existente
   no export LGPD (Art. 18, portabilidade). **Superfície sancionada
   distinta** — não tocar, não "unificar".
5. `backend/app/models/workspace_member.py:31-38` — `VALID_ROLES`
   (owner/member/viewer), `WRITE_ROLES`, `MEMBER_ADMIN_ROLES`.
6. Invariantes do CLAUDE.md: tenancy (`Depends(get_current_workspace)` +
   AST scan), `response_model` obrigatório (ADR-102/109), stateless
   (ADR-111), anti-PII em logs (ADR-273), gate `amended_at` (ADR-302 r6).

## Decisões já tomadas (conformar; mudar qualquer uma = emenda de ADR antes)

- **Máscara canônica:** `***.***.789-00` — últimos 3 dígitos do corpo +
  dígitos verificadores. Computada **server-side por request**
  (decrypt→mask→descarte); o plaintext nunca é persistido fora de
  `cpf_encrypted` nem enviado ao frontend no payload default.
- **Quem vê o quê:** máscara visível a qualquer role do workspace no
  relatório; **"ver completo" restrito a `owner`** (a ADR diz "JWT do owner
  do workspace" — ampliar para `member` é decisão nova, não tome).
- **Todo "ver completo" gera auditoria** — quem, quando, qual membro.
- **Export nunca decriptografa sozinho:** PDF server-side (Playwright sobre
  `/reports/[id]`) renderiza a máscara. Exceção única: export LGPD (item 4
  acima), que continua com CPF completo por ser portabilidade Art. 18.
- **Decrypt exclusivamente no boundary HTTP autenticado** — nunca em Celery,
  logs estruturados, `pipeline_artifacts` ou `LLMCallLog`.

## Decisão delegada pela ADR (resolver aqui, com critério)

A ADR deixou aberto "tabela nova `cpf_view_audit` ou extensão do event
log". **Default deste track: reusar `audit_log` + `AuditAction` nova
(ex.: `cpf_view_full`)** com `details` sem PII (member_id, workspace_id,
timestamp — **nunca** o CPF). Só crie tabela nova se `audit_log`
comprovadamente não comportar (retention/consulta) — e nesse caso o gatilho
`data-engineer` do CLAUDE.md é **obrigatório antes** (migration + schema).

## Gatilho de co-design obrigatório (antes de codar o frontend)

Componente novo no relatório ⇒ invoque **`product-designer`** com brief
mínimo: máscara canônica acima, estados (masked / revelado / loading /
erro / sem-CPF), copy do affordance ("ver completo", tooltip explicando a
auditoria), acessibilidade (não expor o CPF completo em `aria-label`
quando mascarado), e comportamento no print CSS (sempre mascarado). Peça
decisão de copy/estados, **não código**. 1 rodada; objeção persistente →
`senior-cto` decide e fecha.

## Escopo — 3 PRs pequenos e sequenciais

### PR1 — backend (service + endpoint + auditoria)

- Helper **único e canônico** de máscara (nome específico, ex.:
  `mask_cpf_last_digits`) colocado junto do serviço de PII — o frontend
  **nunca** mascara localmente (recebe a string pronta); `grep -r` do nome
  deve retornar <5 hits.
- Serviço de leitura: dado `member_id` do workspace, retorna
  `{cpf_masked}` (qualquer role) ou `{cpf_full}` (owner, com auditoria).
  Decrypt via `get_vault()` singleton (ADR-111 §b); plaintext morre no
  escopo do request.
- Endpoint(s) em router de workspace com `Depends(get_current_workspace)`,
  `response_model=` explícito, 404 para membro sem CPF, 403 para
  não-owner pedindo `full`. Rate limit modesto no "ver completo" usando o
  padrão Redis `INCR`+`EXPIRE` já existente (#720) — sem token bucket em
  memória.
- **Proibido logar o CPF** em qualquer nível — mensagens de log usam
  member_id; o hook anti-PII (ADR-273) e o lint de fixtures cobram.
- Testes: unit da máscara (CPF 11 dígitos, borda: `cpf_encrypted` NULL);
  endpoint masked por role; `full` cria exatamente 1 row de audit com
  action nova e `details` sem PII; cross-tenant 403/404 (o fuzz de tenancy
  pega sozinho, mas escreva o teste dedicado); rate limit excedido → 429.
  `make update-openapi-snapshot` + commit do diff (o snapshot test falha
  sem isso).
- LGPD: rode `backend/tests/test_lgpd_export_coverage.py` — se a action
  nova/estrutura tocar o perímetro de export/erasure, ajuste as listas
  **no mesmo PR** com rationale.

### PR2 — frontend (componente no relatório)

- Componente `CpfMasked` (ou nome fechado no co-design) em
  `frontend/src/components/report/ui/`, consumindo o endpoint via client
  gerado (`frontend/src/generated/` é fonte de verdade — regenerado do
  snapshot OpenAPI do PR1).
- Estados do co-design; botão "ver completo" só renderiza para owner
  (role já disponível no contexto de workspace do frontend); revelado
  volta a mascarado ao fechar/navegar (sem persistir plaintext em estado
  global/localStorage).
- **Sem `any`**; Vitest cobrindo: masked default, reveal owner, ausência
  de botão para viewer/member, erro de rede não quebra a seção.
- Print CSS: o componente imprime **sempre** a máscara (mesmo se revelado
  na tela) — teste de unit no render de print + verifique que o snapshot
  do PDF (`__snapshots__` do print) não contém CPF completo.

### PR3 — docs (fecho do débito)

- [[ADR-259]]: emenda datada curta ("rule 4 entregue, PRs #N/#M") +
  atualizar o banner do flip (o débito explícito sai; vira registro de
  entrega) + **`amended_at` no frontmatter** (gate
  `dev/check_adr_amendment_signal.py` falha sem isso).
- Este track: frontmatter `status: consumed` + `consumed_at`.
- Se o gate F7 R4 (PHASES §F7 / LGPD) tiver checklist referenciável,
  aponte a entrega nele.

## Varredura anti-débito (obrigatória antes do último PR)

1. `rg -i "cpf" frontend/src backend/app --glob '!*test*'` — TODA
   superfície que exiba CPF passa pelo helper canônico ou é a exceção LGPD
   sancionada. Atenção conhecida: `MembersTab.tsx` e
   `_IrpfSuggestionCard.tsx` (config) — se exibem CPF completo hoje,
   alinhe ao componente/máscara **ou** registre explicitamente no PR o
   porquê de ficar fora (com proposta de lane) — silêncio não é opção.
2. Zero `TODO`/`FIXME`/`XXX` novos no diff; zero código comentado.
3. Sem feature flag — e se durante o trabalho decidir que precisa de uma,
   a entrada em `DEFAULTS` (`feature_flags_service.py`) entra **no mesmo
   PR** (flag sem default é dead code silencioso).
4. Se substituir qualquer mascaramento ad-hoc existente, delete-o no mesmo
   PR (nada de dois caminhos de máscara convivendo).
5. Docstrings: 1 linha de intent no service/endpoint; comentário só onde o
   porquê é não-óbvio (ex.: por que o print força máscara), citando
   `(ADR-259 §4)`.

## Gates locais (antes de cada push)

```bash
pre-commit run --all-files
pytest backend/tests -q
pytest tests -q                      # pipeline não deve mudar; prove
cd frontend && npm test -- --run
make update-openapi-snapshot         # PR1
```

## Critérios de aceite (o track só fecha com todos)

- [ ] Relatório de workspace com CPF cifrado exibe `***.***.NNN-DD`.
- [ ] Owner clica "ver completo" → CPF completo na tela + 1 row de audit.
- [ ] `member`/`viewer` não têm o affordance; chamada direta ao endpoint
      `full` → 403.
- [ ] PDF exportado do mesmo relatório contém apenas a máscara.
- [ ] `rg` do CPF de teste nos logs capturados da suíte → 0 hits.
- [ ] Export LGPD continua entregando CPF completo (teste existente verde).
- [ ] ADR-259 emendada com `amended_at`; débito do banner encerrado.
- [ ] 3 PRs squash-merged em `main` com CI verde (regra "Concluído" do
      CLAUDE.md — doc-only do PR3 não exige aguardar CI, PR1/PR2 exigem).

## Anti-escopo

- Não reabrir decisões da ADR-259 (máscara, roles, boundary) — divergência
  fundamentada vira proposta de emenda ANTES de código.
- Não tocar rules 1-3 (extração, `cpf_present`, cifragem).
- Não generalizar para outros PII (RG, CNH) — se a necessidade aparecer,
  registre follow-up; este track é CPF em `/reports/[id]`.
- Não criar tela de administração de PII — só o componente do relatório.

## Git

Branch `agent/adr259-rule4-cpf-view/<yyyyMMdd-HHmm>` a partir de
`origin/main`; commits pequenos (1 mudança lógica); anuncie cada operação;
pre-push drift check; auto-merge squash quando CI verde.
