---
id: PLAN-i18n
type: plan
title: Internacionalização (i18n)
status: paused
created_at: 2026-04-25
last_review: 2026-05-15
sprint_origem: null
sprint_atual: null
sprints_envolvidas: []
paused_at: 2026-04-26
pause_reason: |
  Aguarda gatilho objetivo de demanda (ver §10). ICP confirmado em
  2026-05-15: brasileiros nômades digitais morando fora do Brasil.
  Escopo reduzido para 3 locales (pt-BR + en + es). Frente não-iniciada
  por falta de evidência quantificada de demanda em pré-PMF; recomendação
  GTM 2026-05-15 mantém pausada até atingir um dos 3 gatilhos de §10.
adrs_canonical: ["[[ADR-130]]"]
tags:
  - type/plan
  - status/paused
---

# Plano canônico — Internacionalização (i18n)

> **Status:** `paused` (aguardando gatilho de reentrada — ver §10) ·
> **Última revisão:** 2026-05-15
> **ADR:** [[ADR-130]] — `docs/adr/130-internacionalizacao-com-next-intl-persistencia.md`
> **Sprint MOC:** [F12 lanes](../../sprint/F12/lanes/)
>
> **Locales suportados (3):** pt-BR (default) · en · es. Demais 7
> locales da revisão 2026-04-26 (pt-PT, zh-CN, fr, ru, de, ja, ko)
> saem do escopo F12 — reentram apenas se o ICP mudar (mercado global)
> via nova ADR.

Este documento é a fonte única do plano de i18n. ADR-130 contém o
resumo arquitetural; este plano detalha fases, arquivos afetados e
critérios de aceite. Mudanças de escopo atualizam este arquivo;
mudanças arquiteturais abrem nova ADR.

---

## 1. Premissas

- **ICP da frente:** brasileiros nômades digitais morando fora do
  Brasil — declaram IRPF no BR, mantêm corretora BR, têm renda
  parcial/total em moeda forte, querem ler relatório/UI em EN ou ES
  quando estão fora ou compartilhando com cônjuge/contador local.
- **Domínio continua estruturalmente BR:** IRPF, PGBL, VGBL, CDB,
  LCI/LCA, Tesouro Direto, FII, JCP, INSS, FGTS, Selic/CDI/IPCA. Não
  se traduzem (ver `config/i18n_glossary.yaml` + ADR-130 decisão 9).
- **Moeda primária BRL** em todos os locales. Símbolo R$ mantém;
  formatação muda por locale (`1.234,56` em pt-BR/es-ES vs `1,234.56`
  em en).
- **LGPD/legal permanece PT-BR** por compliance (termos de uso,
  política de privacidade, comunicações regulatórias).
- Nenhuma biblioteca de i18n instalada **em código de produto** —
  fundação F12.1 entregou `next-intl@^4` + `frontend/src/i18n/{config,
  request,plural,fonts}.ts` + middleware + `<NextIntlClientProvider>`
  no layout, mas **nenhuma string de produto foi extraída** ainda
  (apenas `header.title` como prova de fluxo).
- ~1.000–1.500 strings em PT hardcoded no frontend (relatório
  concentra a maior parte), 24 mensagens user-facing no backend,
  labels do `report_layout.yaml`, narrativas de E5/E7 em PT.
- `frontend/src/lib/format.ts` já cria `Intl.NumberFormat` por chamada
  em funções públicas (idempotente, ADR-111 ✅), mas o **locale está
  hardcoded** (`pt-BR`/`en-US`) em ~10 pontos.
- `<MonetaryValue/>` é o renderer único de moeda
  ([frontend/src/components/report/MonetaryValue.tsx](../../../frontend/src/components/report/MonetaryValue.tsx)),
  parametrizado por `currency` mas não por `locale`.
- Codegen `dev/codegen_report_layout.py` é fonte de verdade dos labels
  do relatório (`config/report_layout.yaml` →
  `frontend/src/generated/report-layout.ts` +
  `backend/app/generated/report_layout.py`).
- URLs canônicas (ADR-108): `app.mathoms.ai`, `api.mathoms.ai`. **Sem
  prefixo de locale na URL** — preserva contrato.
- Stateless rigoroso (ADR-111): preferência mora em DB ou cookie/JWT,
  não em cache global mutável.

### 1.1 Lista de locales suportados

| Prio | Locale (BCP-47)         | Idioma             | Script | Direção | Plurais | Cobertura ICP |
| ---- | ----------------------- | ------------------ | ------ | ------- | ------- | ------------- |
| 1    | `pt-BR` *(default)*     | Português (Brasil) | Latin  | LTR     | 2       | ICP core BR-residente + nômade BR em PT/LatAm sem fricção |
| 2    | `en`                    | English            | Latin  | LTR     | 2       | Nômade BR em US/UK/CA/AU/IE/SG/HK/MENA (hubs anglófonos) — share com contador/cônjuge não-BR |
| 3    | `es`                    | Español            | Latin  | LTR     | 2       | Nômade BR em Espanha/LatAm hispanófona em casos onde pt-BR causa atrito |

**Por que apenas 3:** ICP definido como nômade BR. Plus Jakarta + Inter
+ JetBrains Mono cobrem Latin Extended-A nos 3 locales; sem fontes
secundárias necessárias.

**Locales fora do escopo F12 (saída em 2026-05-15):** `pt-PT`,
`zh-CN`, `fr`, `ru`, `de`, `ja`, `ko`. Reentram apenas se ICP mudar
(mercado global) via nova ADR. Infra de carregamento condicional de
fontes e `RTL_LOCALES` permanecem tipadas (mapping/set vazios) — sem
custo de refactor para reentrada futura.

## 2. Escopo

**Dentro do escopo:**

- ✅ UI estática (botões, labels, status, mensagens user-facing).
- ✅ Formatação de números/datas (refactor de `format.ts`,
  `<MonetaryValue/>`).
- ✅ Labels do `report_layout.yaml` via codegen.
- ✅ Mensagens de erro user-facing do backend (24 ocorrências mapeadas).
- ✅ Persistência da escolha em `users.locale` + cookie `NEXT_LOCALE`.
- ✅ ICU MessageFormat para plurais 2-form (en/es alinhados a pt-BR).
- ✅ **Glossário canônico** `config/i18n_glossary.yaml` aplicado antes
  da MT (substituição literal de termos BR-específicos).
- ✅ **Banner "Brazilian fiscal residency assumed"** em EN/ES nas
  seções tributárias do relatório (sinaliza edge case do nômade que
  fez DSDP sem cobrir o produto real).
- ✅ **Tradução automática (MT) inicial via DeepL/Google + revisão
  humana por nativo antes de release não-beta** (ver §6 estratégia).

**Fora do escopo F12 (fase 2, abrir nova ADR se for fazer):**

- ❌ Tradução de **dados do usuário**: nomes de instituições configurados,
  categorias custom, conteúdo de extratos e faturas (são dados, não UI).
- ❌ Tradução de narrativas LLM (E5 análise, E7 cross-val, E6 parecer
  planejador). Risco em paridade dos goldens; quando feito, será via
  parâmetro `lang` no prompt + ADR dedicada.
- ❌ Logs internos (`mathoms.*` namespace JSON estruturado — locale-agnostic).
- ❌ Documentação técnica (`docs/**`, ADRs, CHANGELOG) permanece em PT-BR.
- ❌ Locale por URL (`/pt-BR/reports/...`). Cookie-based preserva ADR-108.
- ❌ Conversão de moeda (BRL → USD/EUR). Produto é fintech BR; mostra
  BRL formatado no idioma local (símbolo "R$" mantém em todos;
  separadores seguem locale). Multi-currency real é projeto separado.
- ❌ Locales APAC/EU/DACH (pt-PT, zh-CN, fr, ru, de, ja, ko) — fora do
  escopo F12. Reentram apenas se ICP mudar.
- ❌ RTL (`ar`/`he`) — fora do escopo F12. CSS logical properties
  continuam recomendadas em código novo, mas deixam de ser
  pré-requisito.
- ❌ Indic (`hi`/`bn`) e SE-Asia (`id`) — fora do escopo F12; reusam
  infra quando re-priorizados.
- ❌ **Modo não-residente fiscal BR** (usuário que fez DSDP): não é
  resolvido por i18n. Banner sinaliza no relatório; produto real
  (alíquota 25% retida, PGBL regime diferente, sem deduções) fica
  para frente separada de produto.

## 3. Decisões técnicas

| # | Decisão | Alternativa | Justificativa |
| --- | --- | --- | --- |
| 1 | `next-intl@^4` no frontend | `react-intl`, `i18next`, `lingui` | App Router-native, server components ok, bundle ~12kb, suporta ICU MessageFormat nativo. Next 16 exige v4 |
| 2 | Cookie `NEXT_LOCALE` (não prefixo URL) | `/pt-BR/...` | Preserva ADR-108; SEO não é objetivo (app autenticado) |
| 3 | Persistência em `users.locale` (DB) | Só cookie/localStorage | Sobrevive a logout/troca de device; sincroniza com cookie |
| 4 | `pt-BR` como default | `Accept-Language` detect | Userbase é BR; outros locales são opt-in; menos surpresa |
| 5 | Chaves flat (`report.overview.title`) | Nested objects | Grep-friendly, codegen mais simples, reduz colisão de merge |
| 6 | Dicionários JSON em `frontend/src/i18n/messages/<locale>.json` | YAML, TOML | JSON é nativo; lint+diff bons; codegen output já é JSON-friendly |
| 7 | Backend lê locale de JWT claim → fallback `Accept-Language` → fallback `pt-BR` | Sempre header | JWT claim segue usuário entre devices |
| 8 | Locale como **enum tipado** (Pydantic + TS literal) com lista whitelist | string livre | Fail-fast em boundaries; segue ISP/ADR-097 D1 |
| 9 | **ICU MessageFormat** para plurais e seleção (`{count, plural, ...}`) | Concatenação manual | Plurais 2-form nos 3 locales; infra preservada para futura extensão; next-intl suporta nativamente |
| 10 | CSS Logical Properties **recomendadas** em código novo | `margin-left/right` | Boa prática para preparar RTL futuro; sem ESLint rule custom enforcing nesta fase |
| 11 | **Sem fontes secundárias.** `localeFontHrefs()` retorna `[]` para os 3 locales | Carregar Noto Sans X | Latin Extended-A é coberto pelas fontes default; mapping tipado mantido vazio para extensão futura |
| 12 | Tradução: **MT (DeepL Pro) → glossário fintech → revisão humana** por locale antes de release não-beta | Tradução humana from-scratch | Custo: ~$200/locale via DeepL para 2 locales (en + es) ≈ $400; revisão humana ~5h/locale × 2 = 10h |
| 13 | **Política C híbrida** para termos BR-específicos: 3 buckets em `config/i18n_glossary.yaml` (`do_not_translate` · `inline_glossary` · `translate`). Default em dúvida = manter BR | Política A (literal) ou B (tudo com glossário inline) | Briefing `financial-planner` 2026-05-15: traduzir IRPF/PGBL/CDB literal induz erro regulatório (INSS≠Social Security, FGC≠FDIC). Híbrido preserva precisão sem poluir UI |

## 4. Arquitetura

### 4.1 Frontend

```
frontend/src/
├── i18n/
│   ├── config.ts              # LOCALES = ["pt-BR", "en", "es"] + default + RTL set vazio
│   ├── request.ts             # next-intl getRequestConfig
│   ├── plural.ts              # helper ICU MessageFormat
│   ├── fonts.ts               # FONT_HREFS = {} (extensão futura)
│   └── messages/
│       ├── pt-BR.json         # source-of-truth (escrita primeiro)
│       ├── en.json
│       └── es.json
├── middleware.ts              # next-intl middleware (cookie-based)
└── app/layout.tsx             # NextIntlClientProvider + lang attr
```

- **Server components** consomem `getTranslations()` (server-side, sem
  hydration cost).
- **Client components** consomem `useTranslations()` hook.
- **Middleware** detecta cookie `NEXT_LOCALE`; se ausente, default
  `pt-BR`. Nunca redireciona.
- **`<html lang="...">`** definido em `app/layout.tsx` baseado em
  `getLocale()`. `dir="ltr"` fixo; `RTL_LOCALES = new Set()` vazio.

### 4.2 Backend

- Migration Alembic: `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'`
  + CHECK constraint `locale IN ('pt-BR', 'en', 'es')`.
- Pydantic `Locale` enum em `backend/app/domain/locale.py` (whitelist 3).
- JWT payload ganha claim `locale` opcional. Mudança no payload é
  **breaking** segundo ADR-109 — abrir **ADR-A6f.5b** dedicada
  (parity test `backend/tests/test_auth_portability.py` precisa de
  golden atualizado).
- Módulo `backend/app/i18n/messages.py`: dataclass tipada com
  `.format(locale=..., **kwargs)`. Sem strings cruas em
  `HTTPException`.
- Endpoint `PATCH /users/me/preferences` aceita `{ "locale": "..." }`.
  `response_model` explícito (ADR-109); rodar
  `make update-openapi-snapshot`.

### 4.3 Codegen do report layout

- `config/report_layout.yaml`: cada label vira `i18n_key:
  "report.section.title"` (apontando para `messages/<locale>.json`).
- `dev/codegen_report_layout.py`: emite
  `frontend/src/generated/report-layout.ts` (+ Pydantic) com **apenas
  chaves i18n** (sem strings); valida que cada chave existe nos 3
  locales.
- Teste de paridade (`tests/test_i18n_parity.py`): para todas as chaves
  de `pt-BR.json`, deve existir entrada não-vazia em `en.json` e
  `es.json`. Falha CI se faltar.
- **Glossário canônico**: `config/i18n_glossary.yaml` é aplicado pelo
  script de MT antes da chamada DeepL — termos `do_not_translate`
  passam intactos; termos `inline_glossary` recebem tooltip/abbr na
  primeira ocorrência por seção (renderer React + Pydantic preservam
  a estrutura).
- **Marcadores `[MT]`** em entradas geradas por máquina ainda não
  revisadas por humano — banner "beta" no app desabilita locale para
  produção até MT ratio < 5%.

### 4.4 Persistência e propagação

```
[Login] → JWT inclui claim "locale" (do users.locale)
   ↓
[Middleware Next.js] lê cookie NEXT_LOCALE (sincronizado via PATCH /users/me/preferences)
   ↓
[Server Components] getRequestConfig() → carrega messages/<locale>.json
   ↓
[<html lang>] documento sempre LTR
   ↓
[Client Components] useTranslations() / useLocale()
   ↓
[API calls] Backend lê JWT.locale (ou Accept-Language como fallback)
```

## 5. Fases (mergeable independentemente)

> Cada fase é commitável e mergeable em `main` sem quebrar a anterior.
> Estimativas em horas de engenharia (frente única).
> **F12.2–F12.8 não iniciam até o gate de §10 ser atingido.**

### F12.1 — Fundação i18n no frontend ✅ (mergeada)

Detalhe histórico em [docs/sprint/F12/lanes/F12-1-fundacao-i18n-no-frontend.md](../../sprint/F12/lanes/F12-1-fundacao-i18n-no-frontend.md).
F12.1a-d entregues; F12.1e ressincronizou para 10 locales (commit
`94cf939`, 2026-04-26). **Cleanup 2026-05-15** descarta 7 locales
que saem do escopo (pt-PT, zh-CN, fr, ru, de, ja, ko) — mantém
fundação para 3 locales (pt-BR + en + es).

### F12.2 — Refactor de `format.ts` e `<MonetaryValue/>` (~8h)

- `format.ts`: aceitar `locale` como parâmetro em **todas** as funções
  públicas. Remover constantes top-level. Substituir por funções puras.
- `<MonetaryValue/>` consome `useLocale()` em vez de heurística
  `currency === "BRL"`. Mantém `currency` como prop.
- Mapas `STAGE_DISPLAY_NAMES`, `DOC_STATUS_MAP`, etc. →
  `messages/<locale>.json`.
- Helper `useFormat()` que injeta locale automaticamente.
- Testes Vitest snapshot por locale (números, datas, mês curto, plural
  count).
- **Validar formatação BRL nos 3 locales:** `Intl.NumberFormat` cobre
  todos via runtime; smoke test confirma.

**Critério de aceite:** `R$ 1.234,56` em pt-BR/es-ES, `R$ 1,234.56` em
en. Testes cobrem formatadores nos 3 locales.

**Commit:** `refactor(frontend): format.ts e MonetaryValue consomem locale via contexto (F12.2)`

### F12.3 — Persistência da escolha (~10h)

- Migration Alembic
  `backend/alembic/versions/<rev>_add_users_locale.py`:
  `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'` + CHECK
  constraint nos 3 valores.
- Pydantic `Locale` enum em `backend/app/domain/locale.py` (whitelist
  3).
- JWT claim `locale` (abrir **ADR-A6f.5b** dedicada antes do commit;
  atualizar golden `test_auth_portability.py`).
- Endpoint `PATCH /users/me/preferences` (Pydantic schema +
  `response_model`); rodar `make update-openapi-snapshot`.
- Frontend: `/settings/preferences` com seletor de **3 opções**.
  Dropdown ordenado por nome nativo do idioma.
- Teste integração: login em en → JWT carrega claim → navegação
  preserva idioma.

**Critério de aceite:** trocar idioma no settings persiste após logout.
Migration up/down testada local. Tabela CHECK constraint barra
locale inválido.

**Commits:**
1. `docs(adr): ADR-A6f.5b — JWT claim locale (extensão de auth payload) (F12.3)`
2. `feat(api): persiste user locale + endpoint preferences (F12.3 · ADR-130)`

### F12.4 — Codegen do report layout multilíngue (~10h)

- Estender schema de `config/report_layout.yaml`: labels migram
  para `i18n_key`.
- `dev/codegen_report_layout.py`: emite tipos sem strings.
- Traduzir labels existentes (≤30 strings) para os 2 locales
  não-pt-BR via DeepL + revisão (etapa MT delegada para F12.6).
- Teste `tests/test_i18n_parity.py`: paridade de chaves entre os 3
  locales.

**Critério de aceite:** alternar locale → labels do relatório React
mudam. Codegen idempotente. Teste de paridade roda em CI.

**Commit:** `feat(report): report_layout.yaml suporta multi-locale via codegen (F12.4)`

### F12.5 — Backend user-facing strings (~8h)

- Centralizar 24 mensagens em `backend/app/i18n/messages.py`
  (dataclass tipada por código; valor é dict `{Locale: str}`).
- Endpoints `documents.py`, `tasks.py`, `admin/users.py` consomem
  `error_message(code, locale)` em vez de strings cruas.
- Locale resolution no FastAPI: `Depends(get_current_locale)` → JWT
  claim → `Accept-Language` → default `pt-BR`.
- ICU plural: erros que mencionam contagem (ex.: "N documentos
  pendentes") usam helper próprio.
- Não traduzir logs internos (`mathoms.*`).

**Critério de aceite:** request com claim `locale=en` retorna
`{"detail":"Document not found"}` (após F12.6 fechar). Logs
permanecem em formato fixo.

**Commit:** `feat(api): mensagens user-facing localizadas via JWT claim/header (F12.5)`

### F12.6 — Tradução do relatório (~25h, paralelizável)

> **Maior frente do projeto.** Custo dominante.

#### 6a) Extração e marcação (10h)

- Migrar ~85 componentes de `frontend/src/components/report/` strings
  → `messages/pt-BR.json` (source-of-truth).
- Cada string ganha chave estável (`report.overview.title`,
  `report.kpi.patrimony.label`, etc.).
- Strings com pluralização migradas para ICU MessageFormat:
  `{count, plural, one {# documento} other {# documentos}}`.
- ESLint rule customizada bloqueia novas strings literais em JSX
  (forçar `t(...)`).
- **Banner "Brazilian fiscal residency assumed"** em EN/ES nas seções
  tributárias do relatório (string nova em `messages/{en,es}.json`).

#### 6b) Tradução automática (5h)

- Script `dev/translate_messages.py` consome DeepL Pro API:
  - Input: `messages/pt-BR.json`
  - Output: 2 arquivos preenchidos + marca `_meta.mt: true` por chave
- `config/i18n_glossary.yaml` aplicado **antes** do DeepL (override
  literal). Aplica buckets:
  - `do_not_translate`: passa intacto.
  - `inline_glossary`: insere tooltip/abbr na primeira ocorrência
    por seção, com texto EN/ES da entrada do glossário.
  - `translate`: termo segue para DeepL normalmente.
- Custo estimado: ~$400 (DeepL Pro $20/mo + chars de overage); ~3.000
  chars/locale × 2 ≈ 6k chars iniciais.

#### 6c) Revisão humana (10h)

- Por locale (~5h cada, 2 locales = 10h): revisor nativo passa por
  cada string MT, ratifica ou corrige. Marca `_meta.mt: false` quando
  ratificada.
- en: revisor verifica que nenhum termo do bucket `do_not_translate`
  foi traduzido (IRPF, PGBL, CDB, FII, JCP, INSS, FGTS, etc.) e que
  banner DSDP aparece nas seções tributárias.
- es: idem, com atenção a falsos cognatos ("renda" → "renta"? — depende
  de contexto; "patrimônio" → "patrimonio neto"). Glossário força
  forma canônica.
- Locales liberados para produção apenas com **ratio MT < 5%**. Acima
  disso, app exibe banner "beta — tradução automática".

#### 6d) Critério de aceite global

- Snapshot Playwright do relatório nos 3 locales sem strings PT
  vazando em en/es (CI regex: nenhum acento PT não-padrão em locales
  não-PT, exceto termos do `do_not_translate`).
- **Regressão `do_not_translate`**: snapshot de 1 relatório por locale
  EN/ES verifica que os ~25 termos da lista aparecem intactos.
- pt-BR continua sendo o único default; en/es podem ficar em beta na
  primeira release não bloqueia.

**Commit pattern:**
- `feat(frontend): extrai strings do relatório para i18n (F12.6a)`
- `chore(i18n): MT inicial via DeepL para 2 locales (F12.6b)`
- `feat(i18n): revisão humana para <locale> (F12.6c)`

### F12.7 — RTL polish (`ar`) — fora do escopo F12 atual

Removida do plano enquanto RTL e demais locales não-Latin estiverem
fora do escopo. CSS logical properties continuam recomendadas em
código novo (decisão #10) para reduzir custo quando RTL voltar.

### F12.8 — QA + E2E (~10h)

- Playwright: matrix nos fluxos `@critical` rodando 1× por locale =
  3 runs. 5 fluxos × 3 locales = 15 runs paralelos (CI < 10min).
- Visual regression do relatório nos 3 locales.
- Validar PDF export (`backend/app/services/pdf_renderer.py` →
  Playwright headless) renderiza locale correto via cookie injection.
- **Regressão `do_not_translate`**: teste E2E carrega relatório em
  EN/ES e confere que termos do bucket aparecem intactos no DOM
  renderizado.
- Atualizar [`docs/reference/SMOKE_TEST_HUMAN.md`](../../reference/SMOKE_TEST_HUMAN.md)
  com checklist de troca de idioma (3 fluxos × 3 locales).

**Critério de aceite:** CI verde com matrix locale em fluxos `@critical`.
PDF em en/es respeita formato `1,234.56` / `1.234,56` e não traduz
termos do `do_not_translate`. Banner DSDP visível na seção tributária.

**Commit:** `test(e2e): cobertura multi-locale para fluxos críticos (3 locales) (F12.8)`

## 6. Estratégia de tradução

### 6.1 Pipeline de qualidade

```
[pt-BR source] → [Glossário canônico (config/i18n_glossary.yaml)]
                ↓ (do_not_translate passa intacto)
              [DeepL Pro / Google Translate]
                ↓
              [Marcação de tooltips para inline_glossary]
                ↓
              [Revisor humano nativo (5h/locale)]
                ↓
              [Smoke visual + leitura de tela completa]
                ↓
              [Liberação para produção OU banner "beta"]
```

### 6.2 Glossário canônico (`config/i18n_glossary.yaml`)

Source-of-truth dos 3 buckets:

- **`do_not_translate`** (~25 termos): tributação, regulação,
  produtos RF/RV BR, indexadores, plataformas, folha CLT, garantias.
- **`inline_glossary`** (~12 termos): glossa inline na primeira
  ocorrência por seção, com texto EN/ES por termo.
- **`translate`** (universais): ativos, fluxo de caixa, reserva de
  emergência, etc. Lista exemplificativa; tudo que não cair nos
  outros dois buckets vai para DeepL normalmente.

> **Source-of-truth em pt-BR vive em
> [docs/reference/COPY_GUIDELINES.md §2](../../reference/COPY_GUIDELINES.md);**
> o YAML carrega apenas as traduções EN/ES + flag de bucket.

### 6.3 Marcação de qualidade

Cada chave em `messages/<locale>.json` carrega metadata:

```json
{
  "report.overview.title": "Net worth overview",
  "_meta": {
    "report.overview.title": { "mt": false, "reviewed_at": "2026-09-15", "reviewer": "alice@..." }
  }
}
```

CI calcula **ratio MT** por locale:

```
ratio = count(mt: true) / count(total)
```

Locale liberado para produção: `ratio < 5%`. Acima: banner "beta —
tradução em progresso, contribua para melhorar".

## 7. Trade-offs aceitos

- **Custo total de tradução** (~1.500 strings × 2 locales = 3.000
  traduções): MT de partida (~$400) + revisão humana (~10h × $50/h
  freelancer = $500). **Total: ~$900** + custo interno. Comparado ao
  plano original de 10 locales (~$4.050), redução de ~78%.
- **JWT payload muda** (claim novo): breaking segundo ADR-109. Mitigado
  com ADR-A6f.5b dedicada e parity test atualizado.
- **Refactor de `format.ts`** toca ~80 call sites: feito em commit único
  (compilador acusa todos), revisão fácil.
- **Cookie sem prefixo URL**: SEO multilíngue não suportado. Aceito —
  app é autenticado, landing pública é fora de escopo (F8 Growth).
- **Bundle size**: messages JSON ~30kb/locale × 3 = ~90kb totais, mas
  next-intl carrega só o locale ativo. **Sem fontes secundárias** —
  Plus Jakarta + Inter + JetBrains Mono cobrem Latin Extended-A nos
  3 locales.
- **Locales podem entrar em "beta"**: pt-BR sai pronto; en/es podem
  ser opt-in com banner até revisão humana fechar. Reduz risco de
  tradução errada em fintech.
- **Frente pausada com gate** (decisão 2026-05-15): F12.2–F12.8 ficam
  na fila aguardando demanda objetiva. Trade-off: tempo até produção
  pode ser longo (3+ meses) ou frente nunca destrava. Mitigação: gate
  é objetivo (números, não intuição) e revisão Q3 2026 força
  decisão consciente.

## 8. Riscos e mitigação

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Tradução errada quebra confiança em fintech | Alta | Alto | Glossário canônico (`config/i18n_glossary.yaml`) + revisão humana obrigatória antes de sair de "beta"; banner "beta" em locales não-revisados |
| Confusão regulatória se INSS → "Social Security" | Alta | Alto | `do_not_translate` + glossário inline obrigatório com disclaimer "not equivalent to US Social Security" |
| FIDC → "ABS" / FGC → "FDIC equivalent" gera queixa cível | Média | Médio | `do_not_translate` força preservação; tooltip explica risco/limite específico BR |
| Nômade que fez DSDP usa relatório em EN/ES e toma decisão errada (alíquota 25% retida não-residente) | Média | Médio | Banner "Brazilian fiscal residency assumed" em seções tributárias; modo não-residente fica em frente separada |
| ICU MessageFormat tem curva de aprendizado | Média | Baixo | Helper `<Plural count={n} one="..." other="..."/>`; doc em onboarding |
| JWT migration quebra sessões existentes | Média | Médio | Claim `locale` é **opcional** no decode; só preenchido em logins novos |
| MT ratio fica alto e nunca cai | Média | Alto | Locale fica em "beta" indefinidamente; OK se revisão não acontece. Critério explícito: < 5% para promover |
| Strings dinâmicas concatenadas (`"Você tem " + n + " documentos"`) | Alta | Médio | ESLint rule custom bloqueia; usar ICU `{count, plural, ...}` |
| **Gate de demanda nunca atingido** → frente paused indefinida | Alta | Baixo | Revisão Q3 2026 força decisão: re-priorizar com novo gate, executar mesmo sem gate (decisão consciente), ou arquivar plano |

## 9. Dependências e ordem

```
F12.1 (a–e) ✅ + cleanup 2026-05-15 ──┬─ F12.2 (format.ts)
[GATE de §10]                         ├─ F12.3 (persist DB)
                                      ├─ F12.4 (codegen)
                                      └─ F12.5 (backend msgs)

F12.4 + F12.2 ──→ F12.6 (relatório bulk)
F12.6 + F12.5 ──→ F12.8 (QA E2E)
```

- F12.1 (a–e) mergeada — fundação contra 10 locales; cleanup
  2026-05-15 reduz para 3 sem perder a infra.
- F12.2, F12.3, F12.4, F12.5 são independentes entre si —
  paralelizáveis após o gate destravar.
- F12.6 depende de F12.2 (format) e F12.4 (codegen).
- F12.7 (RTL) sai do plano atual.
- F12.8 só faz sentido com todas as outras mergeadas.

**Estimativa total** (após destravar pelo gate): ~71h engenharia +
~10h revisão humana ≈ **~81h** com 1 agente em série; **~2,5 semanas**
com 2 agentes em paralelo nas fases independentes + revisores externos
para F12.6c. Comparado ao plano original de 10 locales (~189h),
redução de ~57%.

| Fase | Horas | Pode paralelizar com | Pré-requisito |
| ---- | ----- | -------------------- | ------------- |
| F12.1 (a–e) | 16 + 4 | — | ✅ mergeado |
| Cleanup 2026-05-15 | 2 | — | F12.1e (✅ commit `94cf939`) |
| **GATE §10** | — | — | atingir gatilho A, B ou C |
| F12.2 | 8  | F12.3, F12.4, F12.5 | Gate destravado |
| F12.3 | 10 | F12.2, F12.4, F12.5 | Gate destravado |
| F12.4 | 10 | F12.2, F12.3, F12.5 | Gate destravado |
| F12.5 | 8  | F12.2, F12.3, F12.4 | Gate destravado |
| F12.6a | 10 | — | F12.2 + F12.4 |
| F12.6b | 5  | — | F12.6a |
| F12.6c | 10 | (revisores externos) | F12.6b |
| F12.7 | — | (fora do escopo F12) | — |
| F12.8 | 10 | — | tudo acima |

## 10. Gate de execução (paused-with-gate)

> **F12.2–F12.8 não iniciam até atingir 1 dos 3 gatilhos abaixo.**

Decisão 2026-05-15 (briefing `gtm-strategist`): Mathoms está pré-PMF
no ICP core BR-residente; abrir a frente i18n agora compete com 30+
tasks ativas em A11/A12 (PLATFORM_REVIEW, PLANNER_REVIEW,
CAT_LEARNING_LOOP, COMPETITIVE_PIERRE Fase 4) com ROI medido em
retenção/NRR do core. Sem evidência quantificada de demanda nômade,
mantém frente preparada (escopo + glossário + ADR) mas pausada.

### 10.1 Gatilhos (qualquer um destrava F12.2)

- **Gatilho A — sinal de aquisição:** ≥30 leads qualificados via
  formulário "notify me" / "early access" em EN ou ES na landing
  pública, dentro de uma janela de 90 dias. Mede demanda existente.
- **Gatilho B — sinal de retenção:** ≥3 churns ou feedback formal
  de beta com motivo declarado relacionado a idioma (cônjuge
  não-BR, partilha com contador local, fricção de leitura ou de
  uso conjunto). Mede demanda no usuário pagante.
- **Gatilho C — decisão de pricing:** decisão estratégica de tier
  de pricing internacional (USD/EUR) que exija UI EN como
  pré-requisito. Abrir ADR separada de pricing antes; i18n vira
  consequência.
- **Gatilho D — sinal qualitativo do beta pagante (n=1):** ≥1
  pedido formal documentado de **user pagante ativo** solicitando
  EN ou ES para uso específico (cônjuge não-BR, contador local,
  partilha de relatório com terceiro). Em produto pré-PMF, n=1 de
  usuário pagante engajado é sinal mais forte que n=30 de leads
  anônimos. Registro: thread em canal de suporte, e-mail ou tag em
  pesquisa de NPS — com `Decision` aggregate documentado se for
  pedido recorrente do mesmo workspace.

### 10.2 Revisão obrigatória

- **Checkpoint mensal lightweight:** em cada retro de sprint
  (cadência mensal), ler dashboard de sinal (gatilhos A + B + D) em
  ≤5min. **Sem ação default** — apenas leitura. Objetivo: garantir
  que instrumentação está rodando e os números estão sendo vistos.
  Sem este checkpoint, o risco é "instrumentou e esqueceu" — coleta
  de 3 meses sem leitura e a revisão Q3 vira "nunca olhamos o
  dado". O checkpoint é não-decisional; se algum gatilho atingir
  threshold, o checkpoint do mês promove para decisão formal.
- **Q3 2026** (3 meses pós-encerramento de A12): revisão de
  decisão formal. Sem nenhum gatilho atingido, três opções:
  1. **Re-priorizar com gate ajustado** (ex.: reduzir threshold do
     gatilho A para 20 leads).
  2. **Executar mesmo sem gate** (decisão consciente de produto;
     atualizar `pause_reason` no frontmatter e ADR-130).
  3. **Arquivar plano** (mover para `docs/archive/I18N_PLAN-YYYY-MM-DD.md`
     conforme protocolo CLAUDE.md §"Planos → docs/").

### 10.3 Coleta de sinal (instrumentação mínima)

Para o gate ter dados, precisa de instrumentação:

- **Landing pública** (frente F8 Growth ou `gtm-landing-publish-static`):
  campo "preferred language" no formulário de notify me, com opções
  pt-BR/en/es. Tracking em GA4 / Plausible.
- **Beta users**: pesquisa anual "qual idioma você preferiria usar?"
  + tag em churn surveys para motivo "idioma".
- **Pricing strategy** (gtm-strategist): se tier USD/EUR entrar em
  roadmap, abrir ADR de pricing referenciando este plano.

Sem instrumentação, gate é não-mensurável — bloquear F12.2 sem
sinal é tão ruim quanto destravar sem sinal. **Instrumentação de
coleta é trabalho separado, não-bloqueante para esta pause.**

## 11. Pós-launch (fase 2, fora deste plano)

- Tradução de narrativas LLM (E5 análise, E7 cross-val, E6 parecer
  planejador) via parâmetro `lang` no prompt. Abrir nova ADR. Exige
  goldens novos por locale.
- Locale-aware sorting (`Intl.Collator`) em listagens de transações.
- Detecção de `Accept-Language` em sessão anônima (signup) — hoje cai
  em pt-BR.
- **Modo não-residente fiscal BR** (usuário pós-DSDP): produto
  dedicado, não i18n. Alíquota 25% retida na fonte, sem deduções,
  PGBL em regime diferente. Abrir ADR + plano separados.
- Variantes regionais adicionais (es-MX, en-GB, en-AU): entram como
  tickets isolados — infra já estará pronta.
- **Locales fora do escopo (pt-PT, zh-CN, fr, ru, de, ja, ko, ar/he
  RTL, hi/bn Indic, id SE-Asia):** reentram apenas se ICP mudar
  (mercado global) via nova ADR. Infra de carregamento condicional
  (`localeFontHrefs`) e `RTL_LOCALES` permanecem preparadas.
- Numerais nativos opcionais (Han `一二三` em zh-CN/ja, Devanagari
  `०१२` se hi voltar) como toggle ornamental.
- Documentação técnica em en (apenas se hire internacional ou
  open-source).
- Multi-currency real (BRL → USD/EUR conversion via FX API) como
  projeto separado.
