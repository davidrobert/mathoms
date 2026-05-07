---
id: ADR-067
type: adr
title: "Test infrastructure em sub-fase 6.5F"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 067"]
tags:
  - type/adr
  - status/decidido
size_lines: 57
---

# ADR-067 — Test infrastructure em sub-fase 6.5F

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** Revisão de F6.5 após 6.5A-E definidas revelou que **fundamentos de teste estavam implícitos** e iam virar dor durante execução:

1. **Test DB isolation:** sem decisão entre transactions+rollback / truncate / recreate, tests vão leak state e ficar flaky
2. **Test data factories:** sem `make_user()`/`make_workspace()` etc., 250+ tests duplicam setup → manutenção dobra
3. **MSW sync com backend:** 50+ endpoints em `lib/api.ts` — se MSW handlers divergem do backend real, integration tests viram falsos positivos
4. **Parallelização + workspace isolation:** Playwright default = paralelo; múltiplos workers criando users no mesmo backend = race conditions
5. **Flaky test policy:** E2E vai flakear (natureza); sem política, ou CI vira ruído ou bloqueia tudo
6. **CI artifacts:** quando falha em CI, sem vídeo/trace = debug vira detective work
7. **Backend-real para E2E:** sobe via docker-compose? processo direto? que DB? que Redis? Sem spec, 6.5C.11 trava
8. **Long-running pipeline em E2E:** pipeline real = 5-15min; Playwright timeout = 30s → 6.5C.0 e 6.5C.3 dão timeout sem estratégia
9. **Premium tier LLM em E2E:** chama Anthropic real (caro, key em CI)? Mocka? Decisão pendente
10. **Synthetic PDF generator:** 6.5D.7 cita "PDFs sintéticos versionados" sem dizer **como gera**; cada banco tem layout próprio
11. **`docs/TESTING.md` ausente:** investimento de 4 semanas sem doc de onboarding = código que ninguém mantém

Esses não são "nice-to-have" — são pré-requisitos sem os quais 6.5A-E entregam testes que **viram débito técnico em 3 meses**.

**Alternativas consideradas:**
- (A) Distribuir entre 6.5A-E — fundamentos diluídos = nunca priorizados
- (B) Empurrar para F7D — aí 250+ testes já existem com infra ad-hoc, refactor caro
- (C) **[escolhida]** Sub-fase 6.5F dedicada (~1 semana), executada após 6.5E mas **antes** de F6.5 fechar; investe em fundamentos para sustentar o resto

**Decisão:** Criar sub-fase **6.5F — Test Infrastructure & Process** com 14 tasks organizadas em 4 grupos:
- **6.5F.A Backend test infrastructure:** DB isolation, factories backend, backend-real spec, long-running pipeline strategy
- **6.5F.B Frontend test infrastructure:** MSW sync strategy, parallelization + workspace isolation, factories frontend
- **6.5F.C CI/Process:** flaky policy, CI artifacts (vídeo+trace), snapshot review process, premium LLM E2E decision
- **6.5F.D Documentação + tooling:** synthetic PDF generator (11 bancos), `docs/TESTING.md`, pre-commit hooks

**Critérios de aceite adicionais em F6.5:**
- DB isolation green, factories adotadas em 100% novos tests
- Backend-real CI roda em <3min
- CI artifacts com vídeo+trace acessíveis em PR
- `TESTING.md` cobre 100% dos cenários de novo contributor
- Synthetic PDFs para 11 bancos versionados; zero PDFs reais em `tests/`
- Premium LLM E2E definido (mock default + nightly real opt-in)

**Consequências:**
- ✅ 250+ testes sustentáveis após launch (factories, doc, CI mature)
- ✅ Multi-tenant isolation testável de forma confiável (workspace pool)
- ✅ Custo de adicionar novo test cai drasticamente (factory pattern + docs)
- ✅ Falha em CI debugável em <5min via artifacts
- ✅ Zero PII leak risk em fixtures (synthetic PDF generator + lint 6.5D.7)
- ✅ Onboarding de novo contributor em horas, não dias (TESTING.md)
- ⚠️ Prazo de F6.5 +1 semana (3 → 4 semanas)
- ⚠️ Synthetic PDF generator exige manutenção quando bancos mudam layout (mas isso já é necessário para parsers de E2)
- ⚠️ Decisão D11/D13-D18 (decisões pendentes) precisa ser tomada antes de algumas tasks (premium LLM API key se opt-in real)
- ❌ Pre-commit hooks (6.5F.14) é P1 — pode cair se prazo apertar; aceito

**Trade-offs específicos:**
- Mock LiteLLM em CI default (não real Anthropic) → custo $0 mas perde validação real do provider; nightly opt-in mitiga
- Pipeline mock fixtures pré-computadas em 6.5C.0 → mais rápido mas cobre menos do código real; nightly `--real-pipeline` cobre
- Workspace pool vs worker_id-suffix → trade-off entre isolation e setup cost; ADR durante 6.5F.6 decide
