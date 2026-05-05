# Política de segurança — Mathoms AI

Obrigado por se preocupar com a segurança do Mathoms. Este documento
descreve como reportar vulnerabilidades responsavelmente.

---

## Versões suportadas

Mathoms é um produto em desenvolvimento ativo. **Apenas a versão atual
em `main`** recebe correções de segurança. Não há LTS de versões
anteriores neste momento.

---

## Reportando uma vulnerabilidade

### ❌ Não faça isso

- **Não abra issue pública** descrevendo a vulnerabilidade.
- **Não publique** detalhes em redes sociais, blogs ou fóruns antes do fix.
- **Não explore** dados de produção mesmo se acessíveis.

### ✅ Faça isso

**Opção A — GitHub Private Vulnerability Reporting (preferido):**

1. Acesse https://github.com/davidrobert/mathoms/security/advisories/new
2. Descreva a vulnerabilidade (impacto + repro + sugestão de fix se tiver)
3. Submeta — só o owner do repo recebe.

**Opção B — Email direto:** envie para `david@mathoms.ai` com:

- Tipo (auth bypass / SQLi / XSS / SSRF / RCE / data leak / etc.)
- Componente afetado (backend API / frontend / pipeline / DB / CI)
- Repro mínimo (dados sintéticos — não use dados reais de produção)
- Severidade percebida (CVSS opcional)
- Sugestão de mitigação se identificada

### Tempo de resposta

| Severidade  | Triagem inicial    | Fix em produção  |
| ----------- | ------------------ | ---------------- |
| Crítica     | <24h               | <72h             |
| Alta        | <72h               | <7d              |
| Média       | <7d                | <30d             |
| Baixa       | <14d               | próxima release  |

---

## Disclosure

Seguimos **coordinated disclosure**:

1. **Triagem** — confirmamos a vulnerabilidade e atribuímos severidade.
2. **Fix em desenvolvimento** — corrigimos em branch privada.
3. **Notificação preliminar** — avisamos o reporter com o cronograma.
4. **Deploy do fix** em produção.
5. **Disclosure pública** após o fix:
   - Advisory no GitHub Security tab
   - Crédito ao reporter (a menos que prefira anonimato)
   - CVE se aplicável

**Janela máxima padrão: 90 dias** entre report e disclosure pública,
estendíveis se o fix for genuinamente complexo.

---

## Escopo

### Em escopo

- Backend API (`api.mathoms.ai`)
- Frontend produto (`app.mathoms.ai`)
- Console interno (`ops.mathoms.ai`)
- Landing (`mathoms.ai`)
- Code repository (`github.com/davidrobert/mathoms`)
- CI/CD pipelines (`.github/workflows/`)
- Documentação publicamente acessível

### Fora de escopo

- Engenharia social / phishing contra colaboradores
- DoS / volumetric attacks
- Ataques físicos
- Vulnerabilidades em deps de terceiros já reportadas (use upstream)
- Issues que requerem acesso físico ao dispositivo do usuário
- Resultados de scanners automatizados sem PoC funcional
- Missing security headers em endpoints estáticos
- Self-XSS sem impacto cross-user

---

## Reconhecimento

Reporters de vulnerabilidades válidas serão creditados em:

- GitHub Security Advisory
- `docs/CHANGELOG.md` (notes da release com o fix)
- Hall of Fame (futuro, quando o produto for público)

Pedimos anonimato? Avise no report — respeitamos.

---

## Dados sensíveis no produto

Mathoms processa dados financeiros pessoais (CPF, extratos bancários,
faturas, valores patrimoniais). LGPD aplicável. Vulnerabilidades que
podem expor PII de produção são **automaticamente** classificadas como
**Críticas** ou **Altas**, com SLA correspondente.

Para dúvidas sobre tratamento de dados / LGPD: `david@mathoms.ai`.

---

## Direitos do titular LGPD (Art. 18)

Mathoms expõe self-service para os direitos garantidos pela LGPD —
qualquer usuário autenticado pode exercer sem precisar abrir ticket.

### Portabilidade (V) — `/api/v1/me/data-export`

- `POST /api/v1/me/data-export` (202): dispara empacotamento assíncrono.
  Cooldown de 1h evita storm; retorna 409 se já há request em andamento
  ou um `ready` recente.
- `GET /api/v1/me/data-export/{request_id}` (200): polling de status.
  Quando `status=ready`, retorna `download_url` com token assinado.
- `GET /api/v1/me/data-export/{request_id}/download?token=...` (200):
  streaming do tar.gz. **One-shot** — após servir, o arquivo é apagado
  e o token invalidado. TTL de 7 dias (cron `expire_data_exports`
  ativa retorno 410 e remove arquivos vencidos).

Conteúdo do arquivo: NDJSON tar.gz com `manifest.json` (schema), uma
linha por row em cada tabela vinculada ao usuário (User, Workspaces de
membership, documentos/reports/tasks/decisions/goals/notes/sugestões/
contas bancárias/categorias/pipeline_runs/notifications, audit logs).
**Excluído:** hash de senha (LGPD não obriga); ciphertext Fernet de
PasswordVault (chaves protegidas).

### Eliminação (VI) — `/api/v1/me/delete-request`

- `POST /api/v1/me/delete-request` (202): soft-delete imediato. `User`
  recebe `deletion_requested_at = now()` e `token_version` é incrementado
  (logout forçado em todas as sessões). Cron diário `process_user_deletions`
  finaliza hard-delete após **30 dias de grace**, cascateando para
  workspaces (ON DELETE CASCADE).
- `DELETE /api/v1/me/delete-request` (200): cancela enquanto ainda dentro
  do grace. User precisa re-logar (token bumped) para chamar este
  endpoint.

Após hard-delete, registros de `AuditLog` permanecem com
`actor_user_id=NULL` e `details.user_email_hash=<sha256[:16]>` —
anonimização compatível com LGPD §V (preserva trilha de auditoria sem
PII em claro).

### Auditoria

Toda transição (`requested`, `ready`, `downloaded`, `expired`, `failed`,
`deletion_*`) é registrada em `audit_logs` com IP/UA. Owner do workspace
pode consultar via `GET /api/v1/workspaces/{id}/audit?action=lgpd.*`.
