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
