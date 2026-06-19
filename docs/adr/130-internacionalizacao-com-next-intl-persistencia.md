---
id: ADR-130
type: adr
title: "Internacionalização com `next-intl` + persistência em `users.locale`"
status: Decidido
phase: "F12"
date: "2026-04-25"
relates_to: ["[[ADR-108]]", "[[ADR-109]]", "[[ADR-111]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 130"]
tags:
  - area/auth
  - area/frontend
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 175
---

# ADR-130 — Internacionalização com `next-intl` + persistência em `users.locale`

**Status:** Decidido (F12) • **Data:** 2026-04-25 • **Revisões:**
2026-04-26 (escopo 11 → 10 locales; troca hi/ar/bn/id por de/ja/ko) ·
2026-05-15 (escopo 10 → 3 locales; ICP confirmado nômade BR; plano
permanece pausado com gatilho de reentrada).

**Contexto:** Plataforma é hoje 100% pt-BR. Pedido inicial foi
"suporte a múltiplos idiomas" sem ICP definido — primeira ronda
desenhou 10 locales (top 7 globais + pt-PT + de/ja/ko APAC/EU/DACH)
e a fundação F12.1 foi mergeada contra essa lista (commit `94cf939`,
2026-04-26).

Em **2026-05-15** o fundador delimitou o ICP da frente i18n: *"o
foco de inglês e espanhol são brasileiros nômades digitais morando
fora do Brasil"*. Análise GTM (briefing `gtm-strategist`, 2026-05-15)
concluiu que:

- Mathoms está pré-PMF (10 beta, R$ 0 MRR, meta 100 users em 12m). O
  gargalo de growth é converter os primeiros 100 **BR-residentes**.
- JTBD do nômade BR é o **mesmo** do ICP core (organizar IRPF/PGBL/
  patrimônio BR sem virar planilha); a diferença é cosmética (idioma
  da UI).
- **ES é marginal** para nômade BR: usuário em Madrid/Buenos Aires/
  CDMX lê pt-BR sem fricção real. Se entrar, apenas EN se justifica
  isoladamente.
- i18n é **débito permanente** (cada string nova exige tradução;
  revisão MT periódica). Em time pequeno pré-PMF, esse custo
  contínuo compete com PLATFORM_REVIEW, PLANNER_REVIEW, COMPETITIVE_PIERRE.

Análise de domínio (briefing `financial-planner`, 2026-05-15)
confirmou que a metodologia (Perini/Cerbasi/AUVP) e os instrumentos
financeiros (IRPF, PGBL, VGBL, CDB, LCI, LCA, Tesouro Direto, FII,
JCP, INSS, FGTS, Selic/CDI/IPCA) **não se traduzem** sem induzir
erro — Política C híbrida com glossário canônico é o caminho.

Decisões a tomar (esta ADR): biblioteca, estratégia de URL,
persistência, política de tradução de termos BR-específicos, e
**critério objetivo para destravar a execução**.

Alternativas consideradas:

- **Escopo de locales:** 10 (APAC/EU/DACH inclusos) vs 3 (pt-BR +
  en + es) vs 2 (pt-BR + en) vs adiar sem reduzir escopo.
- **Quando executar:** abrir lanes F12.2–F12.8 agora vs aguardar
  gatilho objetivo de demanda.
- **Política de tradução:** literal (A) vs preservar BR com
  glossário inline (B) vs híbrida com regra por nível de risco (C).
- **Biblioteca, URL, persistência, MT:** mantidas das revisões
  anteriores (sem mudança).

**Decisão:**

1. **`next-intl@^4`** como biblioteca i18n no frontend (Next 16 exige
   v4; v3 incompatível).
2. **Cookie `NEXT_LOCALE`** sem prefixo de URL (preserva ADR-108,
   `app.mathoms.ai`).
3. **Coluna `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'`** no
   DB + claim `locale` em JWT (cobre cross-device).
4. **3 locales** suportados, alinhados ao ICP nômade BR:

   `pt-BR` (default), `en`, `es`.

   - `pt-BR` cobre o ICP core (BR residente) e nômade BR que
     consome em PT sem fricção (Portugal, LatAm).
   - `en` cobre nômade BR em hubs anglófonos (US/UK/CA/AU/IE/SG/HK/
     MENA) onde compartilha relatório com contador/cônjuge não-BR.
   - `es` cobre nômade BR em Espanha/LatAm hispanófona em casos onde
     pt-BR causa atrito (compartilhar com cônjuge/contador local).
5. **`<html lang>`** dinâmico; `dir="ltr"` fixo (sem locales RTL).
   `RTL_LOCALES` permanece exportado como `Set` vazio para extensão
   futura sem refactor. CSS logical properties continuam
   **recomendadas** (não obrigatórias) em código novo.
6. **Sem fontes secundárias** — Plus Jakarta Sans + Inter +
   JetBrains Mono cobrem os 3 locales (Latin Extended-A). Infra de
   carregamento condicional (`localeFontHrefs`) permanece tipada
   para reentrada futura (mapping vazio).
7. **ICU MessageFormat** para plurais e seleção mantido (plurais
   2-form em pt-BR/en/es; infra preservada para casos futuros).
8. **Tradução: pipeline MT (DeepL Pro) → glossário fintech →
   revisão humana por nativo**. Locales com MT ratio > 5%
   permanecem em "beta" com banner explícito.
9. **Política C — híbrido por risco** para termos BR-específicos
   (decisão 2026-05-15, briefing `financial-planner`):
   - **`do_not_translate` (~25 termos):** IRPF, IRRF, IRPJ, INSS,
     FGTS, PIS/PASEP, DARF, DIRPF, CPF, CNPJ, simples nacional,
     lucro presumido, lucro real, DSDP, CDB, LCI, LCA, LF, LFT,
     LTN, NTN-B, CRA, CRI, COE, debênture, FII, FIDC, FIP, BDR,
     JCP, "tag along", Selic, CDI, IPCA, IGP-M, TR, Tesouro
     Direto/Selic/IPCA+/Prefixado, PGBL, VGBL, 13º salário, férias,
     abono pecuniário, FGC.
   - **`inline_glossary` (~12 termos):** IRPF, PGBL, VGBL, FII, JCP,
     Tesouro Selic, Tesouro IPCA+, CDB, LCI/LCA, INSS, FGTS, DSDP —
     tooltip/abbr na primeira ocorrência por seção, com texto em
     EN e ES.
   - **`translate` (universais):** ativos, passivos, patrimônio
     líquido, receitas, despesas, fluxo de caixa, reserva de
     emergência, aporte mensal, dividendo, rentabilidade,
     independência financeira, meta, alocação, rebalanceamento.
   - Lista canônica e governance em
     [config/i18n_glossary.yaml](../../config/i18n_glossary.yaml).
   - **INSS exige glossário inline obrigatório** com disclaimer
     "not equivalent to US Social Security" — risco de confusão
     mais alto da lista.
   - Banner discreto "Reports assume Brazilian fiscal residency"
     em EN/ES nas seções tributárias do relatório, para sinalizar
     edge case do nômade que fez **DSDP** (modo não-residente
     fiscal é frente separada, fora do escopo F12).
10. **Codegen do `report_layout.yaml`** muda para emitir apenas
    `i18n_key`s (sem strings inline) — labels migram para
    `frontend/src/i18n/messages/<locale>.json`. Teste de paridade
    bloqueia merge se faltar entrada nos 3 locales.
11. **Strings dinâmicas concatenadas proibidas** em JSX — ESLint
    rule custom força ICU MessageFormat.
12. **Gate de execução (novo, 2026-05-15; revisado pós-briefing PM
    no mesmo dia):** F12.2–F12.8 **não iniciam** até atingir 1 dos
    4 gatilhos abaixo. Plano fica em `status: paused` com
    `pause_reason` rastreando o gate:
    - **Gatilho A:** ≥30 leads qualificados via formulário "notify
      me / preview" em EN ou ES na landing pública (janela 90 dias).
    - **Gatilho B:** ≥3 churns/feedback de beta com motivo declarado
      relacionado a idioma (cônjuge não-BR, partilha com contador
      local, fricção de leitura).
    - **Gatilho C:** decisão estratégica de tier de pricing
      internacional (USD/EUR) que exija UI EN como pré-requisito
      — abrir ADR separada de pricing antes.
    - **Gatilho D (qualitativo, n=1):** ≥1 pedido formal documentado
      de **user pagante ativo** solicitando EN ou ES para uso
      específico (cônjuge não-BR, contador local, partilha com
      terceiro). Em produto pré-PMF, n=1 de pagante engajado é sinal
      mais forte que n=30 de leads anônimos.
    - **Checkpoint mensal lightweight** (em cada retro de sprint):
      ler dashboard de sinal (A+B+D) em ≤5min. Sem ação default —
      apenas leitura. Mitiga o risco "instrumentou e esqueceu".
    - **Revisão do gate:** retro Q3 2026 (3 meses pós-A12). Sem
      atingir threshold, manter `paused` e re-avaliar com novo gate
      ou desativar a frente.

JWT payload mudar (claim novo) é breaking segundo ADR-109; abre-se
**ADR-A6f.5b** dedicada antes do commit, com golden atualizado de
`backend/tests/test_auth_portability.py` — só quando F12.3 destravar
pelo gate.

A fundação F12.1 foi mergeada em 2026-04-25 (commit anterior) e
ressincronizada em 2026-04-26 (commit `94cf939`) contra a lista de
10 locales. **Cleanup 2026-05-15:** remove os 7 locales que saem
do escopo (`pt-PT`, `zh-CN`, `fr`, `ru`, `de`, `ja`, `ko`) +
fontes Noto SC/JP/KR + seletor CSS `html[lang=...]` para CJK. Custo
~2h. Infra de fontes condicionais e `RTL_LOCALES` permanecem
tipadas (mapping/set vazios) para reentrada futura sem refactor.

Detalhamento operacional, fases (F12.2–F12.8), critérios de aceite,
riscos e estimativas em [docs/plan/I18N/_README.md](../plan/I18N/_README.md).

**Consequências:**

- ✅ 3 locales cobrem o ICP delimitado (nômade BR) com pt-BR como
  default servindo também o ICP core. Custo de tradução cai de
  ~$4.050 + 45h para ~$800 + ~10h.
- ✅ URLs canônicas (ADR-108) intactas — sem redirect, sem prefixo.
- ✅ Persistência cross-device via JWT claim + DB (preservada do
  plano original).
- ✅ Stateless (ADR-111) preservado: locale resolve por contexto/JWT,
  não cache mutável.
- ✅ Política de tradução **previne erro regulatório** (INSS≠Social
  Security, FIDC≠ABS, FGC≠FDIC) via lista `do_not_translate`.
- ✅ Sem fontes secundárias — bundle reduz ~420kb (Noto SC/JP/KR
  saem) e simplifica `app/layout.tsx`.
- ⚠️ Frente fica `paused` aguardando gatilho — pode levar 3+ meses
  para destravar (ou nunca, se sinal de demanda não aparecer).
- ⚠️ Sunk cost da F12.1e (~4h em ajustes para 10 locales) aceito;
  cleanup atual descarta 7 JSONs vazios + fonts + CSS.
- ⚠️ Refactor de `format.ts` toca ~80 call sites quando F12.2
  iniciar; commit único facilitará revisão.
- ⚠️ Edge case "nômade fez DSDP" (não-residente fiscal BR) **não**
  é resolvido por i18n — sinalizado por banner; produto real fica
  para frente "modo não-residente fiscal" fora do escopo F12.
- ❌ Locales APAC/EU/DACH (zh-CN, ja, ko, ru, fr, de, pt-PT)
  saem do escopo. Reentram só se ICP mudar (mercado global) —
  exige nova ADR.
- ❌ SEO multilíngue não suportado (cookie-based). Aceito — app é
  autenticado; landing pública é frente F8 Growth.
- ❌ Conversão de moeda (BRL → USD/EUR) fora de escopo; símbolo R$
  mantém em todos os 3 locales (formatação muda).
- ❌ Tradução de narrativas LLM (E5, E7, parecer planejador E6) e
  de dados do usuário (categorias custom, nomes de instituições)
  ficam para fase 2 com ADR dedicada.

Relaciona-se a: ADR-053 (Intl nativo para datas — agora parametrizado
por locale), ADR-076 (design system), ADR-097 D1 (warnings tipados —
aplicado a `UserFacingError` no backend), ADR-102 R18 (response_model
explícito — aplicado ao endpoint `PATCH /users/me/preferences`),
ADR-108 (URLs canônicas — preservadas), ADR-109 (auth portability —
exige ADR-A6f.5b por mudança no JWT payload), ADR-111 (stateless —
locale via contexto, não cache), ADR-143 (methodology=code — política
de tradução BR-específica honra rules-as-code).
