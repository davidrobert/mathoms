# Plano canônico — Internacionalização (i18n)

> **Status:** Proposto · **Data:** 2026-04-25
> **ADR:** [ADR-130](DECISIONS.md#adr-130--internacionalização-com-next-intl--persistência-em-userslocale)
> **Fase no backlog:** [F12](BACKLOG.md#f12--internacionalização-i18n-10-locales)
>
> **Locales suportados (10):** ver §1.1 abaixo. Default: **pt-BR**.

Este documento é a fonte única do plano de i18n. ADR-130 contém o resumo
arquitetural; este plano detalha fases, arquivos afetados e critérios de
aceite. Mudanças de escopo atualizam este arquivo; mudanças arquiteturais
abrem nova ADR.

---

## 1. Premissas

- Nenhuma biblioteca de i18n instalada hoje. ~1.000–1.500 strings em PT
  hardcoded no frontend (relatório concentra a maior parte), 24 mensagens
  user-facing no backend, labels do `report_layout.yaml`, narrativas de
  E5/E7 em PT.
- `frontend/src/lib/format.ts` já cria `Intl.NumberFormat` por chamada em
  funções públicas (idempotente, ADR-111 ✅), mas o **locale está
  hardcoded** (`pt-BR`/`en-US`) em ~10 pontos.
- `<MonetaryValue/>` é o renderer único de moeda
  ([frontend/src/components/report/MonetaryValue.tsx](../frontend/src/components/report/MonetaryValue.tsx)),
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

Top 7 globais por contagem de speakers (Ethnologue 2024, L1+L2) + pt-PT
(requisito de produto) + de/ja/ko (mercados-alvo APAC/EU/DACH):

| Prio | Locale (BCP-47) | Idioma | Speakers (M) | Script | Direção | Plurais |
| ---- | --------------- | -------------------- | ------ | -------------- | ------- | ------- |
| 1    | `pt-BR` *(default)* | Português (Brasil) | ~265 | Latin           | LTR     | 2 |
| 2    | `en`            | English              | ~1.500 | Latin           | LTR     | 2 |
| 3    | `pt-PT`         | Português (Portugal) | ~10*  | Latin           | LTR     | 2 |
| 4    | `zh-CN`         | 中文 (简体, Mandarim) | ~1.100 | Han Simplified | LTR     | 1 |
| 5    | `es`            | Español              | ~560  | Latin           | LTR     | 2 |
| 6    | `fr`            | Français             | ~310  | Latin           | LTR     | 2 |
| 7    | `ru`            | Русский              | ~255  | Cyrillic        | LTR     | **4** |
| 8    | `de`            | Deutsch              | ~135  | Latin           | LTR     | 2 |
| 9    | `ja`            | 日本語               | ~125  | Han + Kana      | LTR     | 1 |
| 10   | `ko`            | 한국어               | ~80   | Hangul          | LTR     | 1 |

\* pt-PT mantido apesar de speakercount baixo: requisito explícito do
produto (mercado europeu de língua portuguesa, distinção lexical
relevante para fintech — "fatura"/"cêntimos"/etc.).

**Implicações por bucket:**

- **LTR Latin (pt-BR, en, pt-PT, es, fr, de):** baixo risco. Plus
  Jakarta + Inter + JetBrains Mono já cobrem Latin Extended-A.
  Plurais 2-form em todos. `de` adiciona caracteres `ä/ö/ü/ß` (Latin
  Extended-A — já cobertos).
- **CJK (zh-CN, ja, ko):** Noto Sans SC (zh-CN), Noto Sans JP (ja),
  Noto Sans KR (ko) como fallback condicional. Sem itálico
  (não-idiomático nos três); densidade tipográfica diferente
  (line-height +5–8%). Plural único nos três (sem morfologia plural).
- **Cyrillic (ru):** plurais 4-form (one/few/many/other); Inter cobre.
- **Sem locales RTL no escopo atual.** `ar` e variantes saem da F12 —
  ver §11 pós-launch para reentrada futura.
- **Sem locales Indic no escopo atual.** `hi`/`bn` removidos pelos
  mesmos motivos.

## 2. Escopo

**Dentro do escopo:**

- ✅ UI estática (botões, labels, status, mensagens user-facing).
- ✅ Formatação de números/datas (refactor de `format.ts`,
  `<MonetaryValue/>`).
- ✅ Labels do `report_layout.yaml` via codegen.
- ✅ Mensagens de erro user-facing do backend (24 ocorrências mapeadas).
- ✅ Persistência da escolha em `users.locale` + cookie `NEXT_LOCALE`.
- ✅ Fontes secundárias para CJK (zh-CN, ja, ko).
- ✅ ICU MessageFormat para plurais (necessário para `ru`).
- ✅ **Tradução automática (MT) inicial via DeepL/Google + revisão
  humana por nativo antes de release não-beta** (ver §6 estratégia).

**Fora do escopo (fase 2, abrir nova ADR se for fazer):**

- ❌ Tradução de **dados do usuário**: nomes de instituições configurados,
  categorias custom, conteúdo de extratos e faturas (são dados, não UI).
- ❌ Tradução de narrativas LLM (E5 análise, E7 review). Risco em paridade
  dos goldens de Caminho B; quando feito, será via parâmetro `lang` no
  prompt.
- ❌ Logs internos (`mathoms.*` namespace JSON estruturado — locale-agnostic).
- ❌ Documentação técnica (`docs/**`, ADRs, CHANGELOG) permanece em PT-BR.
- ❌ Locale por URL (`/pt-BR/reports/...`). Cookie-based preserva ADR-108.
- ❌ Conversão de moeda (BRL → CNY/EUR/JPY/KRW). Produto é fintech BR;
  mostra BRL formatado no idioma local (símbolo "R$" mantém em todos;
  separadores seguem locale). Multi-currency real é projeto separado
  pós-GA.
- ❌ Locale-aware números no script local (ex.: numerais Han `一二三` em
  zh-CN/ja como toggle ornamental opcional). Mantém algarismos
  arábico-ocidentais (padrão fintech global).
- ❌ **RTL (`ar`/`he`)** — fora do escopo F12. Quando re-priorizado,
  abrir ticket dedicado (ver §11). CSS logical properties continuam
  recomendadas em código novo, mas deixam de ser pré-requisito.
- ❌ **Indic (`hi`/`bn`)** e **SE-Asia (`id`)** — fora do escopo F12;
  reusam infra quando re-priorizados.

## 3. Decisões técnicas

| # | Decisão | Alternativa | Justificativa |
| --- | --- | --- | --- |
| 1 | `next-intl@^3` no frontend | `react-intl`, `i18next`, `lingui` | App Router-native, server components ok, bundle ~12kb, suporta ICU MessageFormat nativo, RTL ok (preservado p/ extensão futura) |
| 2 | Cookie `NEXT_LOCALE` (não prefixo URL) | `/pt-BR/...` | Preserva ADR-108; SEO não é objetivo (app autenticado) |
| 3 | Persistência em `users.locale` (DB) | Só cookie/localStorage | Sobrevive a logout/troca de device; sincroniza com cookie |
| 4 | `pt-BR` como default | `Accept-Language` detect | Userbase é BR; outros locales são opt-in; menos surpresa |
| 5 | Chaves flat (`report.overview.title`) | Nested objects | Grep-friendly, codegen mais simples, reduz colisão de merge |
| 6 | Dicionários JSON em `frontend/src/i18n/messages/<locale>.json` | YAML, TOML | JSON é nativo; lint+diff bons; codegen output já é JSON-friendly |
| 7 | Backend lê locale de JWT claim → fallback `Accept-Language` → fallback `pt-BR` | Sempre header | JWT claim segue usuário entre devices |
| 8 | Locale como **enum tipado** (Pydantic + TS literal) com lista whitelist | string livre | Fail-fast em boundaries; segue ISP/ADR-097 D1 |
| 9 | **ICU MessageFormat** para plurais e seleção (`{count, plural, ...}`) | Concatenação manual | Necessário para `ru` (4 plurais); infra futura quando ar/he voltarem (6 plurais); next-intl suporta nativamente |
| 10 | **CSS Logical Properties** **recomendadas** em código novo | `margin-left/right` | Boa prática para preparar RTL futuro; sem ESLint rule custom enforcing nesta fase |
| 11 | Fontes CJK carregadas **condicionalmente** por locale | Carregar todas sempre | Noto SC + JP + KR ≈ 420kb; carregar só quando locale ativo |
| 12 | Tradução: **MT (DeepL Pro) → glossário fintech → revisão humana** por locale antes de release não-beta | Tradução humana from-scratch | Custo: ~$200/locale via DeepL; humano apenas revisa (~10h/locale × 9 = 90h) vs from-scratch (~40h/locale × 9 = 360h) |

## 4. Arquitetura

### 4.1 Frontend

```
frontend/src/
├── i18n/
│   ├── config.ts              # locales suportados + default + RTL set
│   ├── request.ts             # next-intl getRequestConfig
│   ├── plural.ts              # helper ICU MessageFormat
│   └── messages/
│       ├── pt-BR.json         # source-of-truth (escrita primeiro)
│       ├── en.json
│       ├── pt-PT.json
│       ├── zh-CN.json
│       ├── es.json
│       ├── fr.json
│       ├── ru.json
│       ├── de.json
│       ├── ja.json
│       └── ko.json
├── middleware.ts              # next-intl middleware (cookie-based)
└── app/layout.tsx             # NextIntlClientProvider + lang attr
```

- **Server components** consomem `getTranslations()` (server-side, sem
  hydration cost).
- **Client components** consomem `useTranslations()` hook.
- **Middleware** detecta cookie `NEXT_LOCALE`; se ausente, default
  `pt-BR`. Nunca redireciona.
- **`<html lang="...">`** definido em `app/layout.tsx` baseado em
  `getLocale()`. `dir="ltr"` fixo no escopo atual; `RTL_LOCALES = new
  Set()` (vazio, preservado para extensão futura sem refactor).
- **Fontes condicionais**: `app/layout.tsx` injeta `<link>` para
  Noto Sans SC (zh-CN), Noto Sans JP (ja), Noto Sans KR (ko) apenas
  quando o locale ativo precisa.

### 4.2 Backend

- Migration Alembic: `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'`
  + CHECK constraint `locale IN (<lista dos 10>)`.
- Pydantic `Locale` enum em `backend/app/domain/locale.py` (uso por todo
  backend, ISP).
- JWT payload ganha claim `locale` opcional. Mudança no payload é
  **breaking** segundo ADR-109 — abrir **ADR-A6f.5b** dedicada
  (parity test `backend/tests/test_auth_portability.py` precisa de
  golden atualizado).
- Módulo `backend/app/i18n/messages.py`: dataclass tipada com
  `.format(locale=..., **kwargs)` que delega para ICU MessageFormat
  (via `babel.support.Translations` ou equivalente Python). Sem
  strings cruas em `HTTPException`.
- Endpoint `PATCH /users/me/preferences` aceita `{ "locale": "..." }`.
  `response_model` explícito (ADR-109); rodar
  `make update-openapi-snapshot`.

### 4.3 Codegen do report layout

- `config/report_layout.yaml`: cada label vira `i18n_key:
  "report.section.title"` (apontando para `messages/<locale>.json`).
  Formato inline (`{ pt-BR: "...", en: "..." }`) **não é mais
  recomendado** com 10 locales — vira ilegível. Sempre usar
  `i18n_key`.
- `dev/codegen_report_layout.py`: emite
  `frontend/src/generated/report-layout.ts` (+ Pydantic) com **apenas
  chaves i18n** (sem strings); valida que cada chave existe nos 10
  locales.
- Teste de paridade (`tests/test_i18n_parity.py`): para todas as chaves
  de `pt-BR.json`, deve existir entrada não-vazia em todos os 9
  outros locales. Falha CI se faltar.
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
[<html lang>] documento sempre LTR (RTL_LOCALES vazio no escopo atual)
   ↓
[<link>] carrega fonte secundária (Noto SC/JP/KR) sob demanda
   ↓
[Client Components] useTranslations() / useLocale()
   ↓
[API calls] Backend lê JWT.locale (ou Accept-Language como fallback)
```

## 5. Fases (mergeable independentemente)

> Cada fase é commitável e mergeable em `main` sem quebrar a anterior.
> Estimativas em horas de engenharia (frente única).

### F12.1 — Fundação i18n no frontend (~16h)

- Instalar `next-intl@^3`.
- Criar `frontend/src/i18n/{config,request,plural}.ts` + `messages/<10
  locales>.json` (vazios, só `meta.locale`).
- `frontend/middleware.ts` com matcher detectando cookie + whitelist
  dos 10 locales.
- Wrap `app/layout.tsx` em `NextIntlClientProvider` + `<html lang>`.
- **`RTL_LOCALES = new Set()`** (vazio; preservado para extensão
  futura) + helper `getDir(locale)` retornando sempre `"ltr"` no
  escopo atual.
- Carregamento condicional de fontes CJK (SC/JP/KR).
- Primeira string traduzida (ex.: título do menu) como prova de fluxo
  nos 10 locales.
- Teste Vitest: `useTranslations` resolve nos 10 locales; `dir="ltr"`
  em todos.

**Critério de aceite:** alternar cookie `NEXT_LOCALE` no devtools muda
1 string visível no header em qualquer dos 10 locales. CI verde.
Fonte Noto Sans SC só carrega em zh-CN; Noto JP só em ja; Noto KR só
em ko.

**Commit:** `feat(frontend): instala next-intl + middleware de locale (10 locales, cookie-based) (F12.1)`

### ✅ F12.1e — Correção da lista de locales (fechada 2026-04-26, commit `94cf939`)

> **Concluída.** A fundação F12.1 foi ressincronizada com a lista
> revisada de 10 locales antes do início das lanes posteriores.
> Alteração coberta: `frontend/src/i18n/{config,fonts}.ts`,
> `messages/{de,ja,ko}.json` (substituem `hi/ar/bn/id`),
> `globals.css` (seletores `html[lang=...]`),
> `tests/i18n/foundation.test.tsx`. Suíte Vitest local 571 passed,
> lint clean. Detalhes históricos abaixo, preservados como audit
> trail.

**Mudanças concretas:**

- [frontend/src/i18n/config.ts](../frontend/src/i18n/config.ts):
  remover `"hi"`, `"ar"`, `"bn"`, `"id"` de `LOCALES`; adicionar
  `"de"`, `"ja"`, `"ko"`. `RTL_LOCALES` passa a `new Set<Locale>()`
  (vazio); `getDir(locale)` simplifica para retornar sempre
  `"ltr"`. Atualizar comentário do cabeçalho citando ADR-130
  revisado.
- [frontend/src/i18n/fonts.ts](../frontend/src/i18n/fonts.ts):
  `FONT_HREFS` remove entradas `hi`/`bn`/`ar`; adiciona `ja` (Noto
  Sans JP) e `ko` (Noto Sans KR). Manter `zh-CN` (Noto Sans SC)
  inalterada.
- `frontend/src/i18n/messages/`: deletar `ar.json`, `bn.json`,
  `hi.json`, `id.json`. Criar `de.json`, `ja.json`, `ko.json` com
  o mesmo shape (`_meta.locale` + `header.title` placeholder
  alinhado ao já presente em `pt-BR.json`).
- `frontend/middleware.ts`: atualizar matcher de cookie/whitelist
  para a nova lista de 10 locales.
- `frontend/src/app/layout.tsx`: garantir que preload de fontes
  cobre os novos `ja`/`ko` e remove referências às fontes RTL/Indic.
- `frontend/tests/i18n/foundation.test.tsx`: recalcular asserts
  (paridade JSON × 10 locales; `getDir` sempre `"ltr"`;
  `localeFontHrefs` por bucket atualizado). O número exato de
  asserts cresce/decresce — não fixar como gate.

**Critério de aceite:**

1. `pnpm test -- --run i18n/foundation` (ou `npm test -- --run
   i18n/foundation`) verde.
2. `grep -RE "\b(hi|ar|bn|id)\b" frontend/src/i18n/` retorna **só
   strings de comentário/documentação ou nada** — nenhuma key,
   nenhum import.
3. `grep -RE "\b(de|ja|ko)\b" frontend/src/i18n/messages/` retorna
   ao menos um match em cada um dos três novos arquivos.
4. Lint frontend (`npm run lint`) verde.
5. CI completo verde no PR (não exceção docs-only — toca código).

**Commit:** `fix(frontend): sincroniza F12.1 com lista revisada de 10 locales (F12.1e · ADR-130)`

### F12.2 — Refactor de `format.ts` e `<MonetaryValue/>` (~8h)

- `format.ts`: aceitar `locale` como parâmetro em **todas** as funções
  públicas. Remover constantes top-level. Substituir por funções puras.
- `<MonetaryValue/>` consome `useLocale()` em vez de heurística
  `currency === "BRL"`. Mantém `currency` como prop.
- Mapas `STAGE_DISPLAY_NAMES`, `DOC_STATUS_MAP`, etc. →
  `messages/<locale>.json`.
- Helper `useFormat()` que injeta locale automaticamente.
- Testes Vitest snapshot por locale (números, datas, mês curto, **plural
  count**).
- **Validar formatação BRL nos 10 locales:** `Intl.NumberFormat` cobre
  todos via runtime; smoke test confirma.

**Critério de aceite:** `BRL 1.234,56` em pt-BR/pt-PT, `BRL 1,234.56` em
en/zh-CN/ja/ko, `1.234,56 R$` em de (separador alemão). Testes cobrem
formatadores nos 10 locales.

**Commit:** `refactor(frontend): format.ts e MonetaryValue consomem locale via contexto (F12.2)`

### F12.3 — Persistência da escolha (~10h)

- Migration Alembic
  `backend/alembic/versions/<rev>_add_users_locale.py`:
  `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'` + CHECK
  constraint nos 10 valores.
- Pydantic `Locale` enum em `backend/app/domain/locale.py` (whitelist
  dos 10).
- JWT claim `locale` (abrir **ADR-A6f.5b** dedicada antes do commit;
  atualizar golden `test_auth_portability.py`).
- Endpoint `PATCH /users/me/preferences` (Pydantic schema +
  `response_model`); rodar `make update-openapi-snapshot`.
- Frontend: `/settings/preferences` com seletor de **10 opções**
  agrupadas (APAC, Europa, Américas). Dropdown ordenado
  alfabeticamente por **nome nativo** do idioma.
- Teste integração: login em ja → JWT carrega claim → navegação
  preserva idioma.

**Critério de aceite:** trocar idioma no settings persiste após logout.
Migration up/down testada local. Tabela CHECK constraint barra
locale inválido.

**Commits:**
1. `docs(adr): ADR-A6f.5b — JWT claim locale (extensão de auth payload) (F12.3)`
2. `feat(api): persiste user locale + endpoint preferences (F12.3 · ADR-130)`

### F12.4 — Codegen do report layout multilíngue (~12h)

- Estender schema de `config/report_layout.yaml`: labels migram
  para `i18n_key`.
- `dev/codegen_report_layout.py`: emite tipos sem strings.
- Traduzir labels existentes (≤30 strings) para os 9 locales
  não-pt-BR via DeepL + revisão (etapa MT delegada para F12.6).
- Teste `tests/test_i18n_parity.py`: paridade de chaves entre os 10
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
  pendentes") usam `babel.support.Translations` ou helper próprio.
- Não traduzir logs internos (`mathoms.*`).

**Critério de aceite:** request com claim `locale=ja` retorna
`{"detail":"ドキュメントが見つかりません"}` (após F12.6 fechar). Logs
permanecem em formato fixo.

**Commit:** `feat(api): mensagens user-facing localizadas via JWT claim/header (F12.5)`

### F12.6 — Tradução do relatório (bulk, ~70h, paralelizável)

> **Maior frente do projeto.** Custo dominante e paralelizável.

#### 6a) Extração e marcação (10h)

- Migrar ~85 componentes de `frontend/src/components/report/` strings
  → `messages/pt-BR.json` (source-of-truth).
- Cada string ganha chave estável (`report.overview.title`,
  `report.kpi.patrimony.label`, etc.).
- Strings com pluralização migradas para ICU MessageFormat:
  `{count, plural, one {# documento} other {# documentos}}`.
- ESLint rule customizada bloqueia novas strings literais em JSX
  (forçar `t(...)`).

#### 6b) Tradução automática (15h)

- Script `dev/translate_messages.py` consome DeepL Pro API:
  - Input: `messages/pt-BR.json`
  - Output: 9 arquivos preenchidos + marca `_meta.mt: true` por chave
- Glossário fintech (`config/i18n_glossary.yaml`) força termos:
  - "fatura" → en: "credit-card statement", pt-PT: "fatura", de:
    "Kreditkartenabrechnung", ja: "クレジットカード明細", ko: "신용카드 명세서", etc.
  - "patrimônio" → en: "net worth", es: "patrimonio neto", etc.
  - "metas" → en: "goals", fr: "objectifs", etc.
- Custo estimado: ~$200/locale × 9 = $1.800 (DeepL Pro $20/mo + chars
  de overage); ~3.000 chars/locale × 9 ≈ 27k chars iniciais.

#### 6c) Revisão humana (45h)

- Por locale (~5h cada, 9 locales = 45h): revisor nativo passa por
  cada string MT, ratifica ou corrige. Marca `_meta.mt: false` quando
  ratificada.
- pt-PT: ~5h dedicadas (lexical: "centavos"→"cêntimos", "tela"→"ecrã"
  onde aplicável, evitar gerundismos, "fatura" pós-AO mantida).
- de: revisor verifica padrão alemão de separadores (`1.234,56 €`),
  termos compostos longos (`Kreditkartenabrechnung`, `Nettovermögen`),
  uso de Sie/du.
- ja/ko: honoríficos consistentes (です・ます forma para ja; 합니다
  forma para ko); ordem SOV preservada nas mensagens curtas.
- Locales liberados para produção apenas com **ratio MT < 5%**. Acima
  disso, app exibe banner "beta — tradução automática".

#### 6d) Critério de aceite global

- Snapshot Playwright do relatório em 10 locales sem strings PT
  vazando (CI regex: nenhum acento PT em locales não-PT).
- pt-BR continua sendo o único default; outros locales podem ficar em
  beta na primeira release não bloqueia.

**Commit pattern:**
- `feat(frontend): extrai strings do relatório para i18n (F12.6a)`
- `chore(i18n): MT inicial via DeepL para 9 locales (F12.6b)`
- `feat(i18n): revisão humana para <locale> (F12.6c)`

### F12.7 — RTL polish (`ar`) — **fora do escopo F12 atual**

Removida do plano enquanto `ar` (e demais locales RTL) estiverem fora
do escopo da F12. Sem locales RTL ativos, mirroring de layout, ESLint
rule custom para logical properties e auditoria de Recharts deixam de
ser pré-requisito. CSS logical properties continuam **recomendadas**
em código novo (decisão #10) para reduzir custo quando RTL voltar.

Quando ar/he forem re-priorizados, abrir ticket dedicado seguindo o
roteiro descrito em §11 (pós-launch). Estimativa preservada: ~12h
auditoria + snapshots visuais.

### F12.8 — QA + E2E (~10h)

- Playwright: matrix nos fluxos `@critical` rodando 1× por locale =
  10 runs. Optar por `@critical` apenas (5 fluxos) para manter CI <
  20min: 5 × 10 = 50 runs paralelos.
- Visual regression do relatório nos 10 locales.
- Validar PDF export (`backend/app/services/pdf_renderer.py` →
  Playwright headless) renderiza locale correto via cookie injection.
- Atualizar [SMOKE_TEST.md](SMOKE_TEST.md) com checklist de troca de
  idioma (3 fluxos × 10 locales).

**Critério de aceite:** CI verde com matrix locale em fluxos `@critical`.
PDF em zh-CN/ja/ko tem fonte CJK correta (SC/JP/KR); PDF em de
respeita formato `1.234,56` e caracteres `ä/ö/ü/ß`.

**Commit:** `test(e2e): cobertura multi-locale para fluxos críticos (10 locales) (F12.8)`

## 6. Estratégia de tradução

### 6.1 Pipeline de qualidade

```
[pt-BR source] → [DeepL Pro / Google Translate]
                ↓
              [Glossário fintech (override de termos)]
                ↓
              [Revisor humano nativo (5h/locale)]
                ↓
              [Smoke visual + leitura de tela completa]
                ↓
              [Liberação para produção OU banner "beta"]
```

### 6.2 Glossário fintech (`config/i18n_glossary.yaml`)

Termos críticos com tradução normativa por locale. Aplicado **antes**
da MT (substituição literal); revisor humano não pode mudar (apenas
sinaliza ao PM).

Exemplos:

```yaml
patrimony:
  pt-BR: "patrimônio"
  pt-PT: "património"
  en: "net worth"
  es: "patrimonio neto"
  fr: "patrimoine net"
  zh-CN: "净资产"
  ru: "чистая стоимость"
  de: "Nettovermögen"
  ja: "純資産"
  ko: "순자산"

invoice:
  pt-BR: "fatura"
  pt-PT: "fatura"
  en: "credit-card statement"
  de: "Kreditkartenabrechnung"
  ja: "クレジットカード明細"
  ko: "신용카드 명세서"
  ...
```

### 6.3 Marcação de qualidade

Cada chave em `messages/<locale>.json` carrega metadata:

```json
{
  "report.overview.title": "概览",
  "_meta": {
    "report.overview.title": { "mt": false, "reviewed_at": "2026-05-10", "reviewer": "alice@..." }
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

- **Custo total de tradução** (~1.500 strings × 9 locales = 13.500
  traduções): MT de partida (~$1.800) + revisão humana (~45h × $50/h
  freelancer = $2.250). **Total: ~$4.050** + custo interno.
- **JWT payload muda** (claim novo): breaking segundo ADR-109. Mitigado
  com ADR-A6f.5b dedicada e parity test atualizado.
- **Refactor de `format.ts`** toca ~80 call sites: feito em commit único
  (compilador acusa todos), revisão fácil.
- **Cookie sem prefixo URL**: SEO multilíngue não suportado. Aceito —
  app é autenticado, landing pública é fora de escopo (F8 Growth).
- **Bundle size**: messages JSON ~30kb/locale × 10 = ~300kb totais,
  mas next-intl carrega só o locale ativo. Fontes CJK condicionais
  (Noto SC ~150kb, Noto JP ~150kb, Noto KR ~120kb ≈ ~420kb totais) só
  vão pra wire quando o locale ativo precisa.
- **Locales podem entrar em "beta"**: pt-BR + en saem prontos no
  release; demais 8 podem ser opt-in com banner até revisão humana
  fechar. Reduz risco de tradução errada em fintech.

## 8. Riscos e mitigação

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Tradução errada quebra confiança em fintech | Alta | Alto | Glossário fintech + revisão humana obrigatória antes de sair de "beta"; banner "beta" em locales não-revisados |
| Fontes CJK (SC/JP/KR) adicionam latência | Média | Baixo | Carregamento condicional por locale; preload via `<link rel="preload">` no critical path |
| ICU MessageFormat tem curva de aprendizado | Média | Baixo | Helper `<Plural count={n} one="..." other="..."/>`; doc em onboarding |
| JWT migration quebra sessões existentes | Média | Médio | Claim `locale` é **opcional** no decode; só preenchido em logins novos |
| MT ratio fica alto e nunca cai | Média | Alto | Locale fica em "beta" indefinidamente; OK se revisão não acontece. Critério explícito: < 5% para promover |
| Quarto locale variante (es-MX, en-GB, fr-CA, en-AU) demanda explosão | Alta | Baixo | Variantes regionais NÃO entram nesse plano; quando vierem, reusam infra (overhead = só JSON novo) |
| Strings dinâmicas concatenadas (`"Você tem " + n + " documentos"`) | Alta | Médio | ESLint rule custom bloqueia; usar ICU `{count, plural, ...}` |
| Plurais `ru` implementados errados (4 formas: 0/1/2-4/5+) | Média | Médio | Test goldens por locale com plural counts (0, 1, 2, 5, 11, 100) |

## 9. Dependências e ordem

```
F12.1 (a–e) ✅ ──┬─ F12.2 (format.ts) ──┬─ F12.6 (relatório bulk)
                ├─ F12.3 (persist DB)  ├─
                ├─ F12.4 (codegen)     ┘
                └─ F12.5 (backend msgs)

F12.6 + F12.5 ──→ F12.8 (QA E2E)
```

- F12.1 (a–e) fechada — fundação contra lista de 10 locales.
- F12.2, F12.3, F12.4, F12.5 são independentes entre si —
  paralelizáveis (próxima onda).
- F12.6 depende de F12.2 (format) e F12.4 (codegen).
- F12.7 (RTL) sai do plano atual — ver §11 quando re-priorizado.
- F12.8 só faz sentido com todas as outras mergeadas.

**Estimativa total:** 144h engenharia (inclui F12.1e correção, 4h)
+ 45h revisão humana ≈ **~189h** com 1 agente em série; **~5
semanas** com 2 agentes em paralelo nas fases independentes +
revisores externos para F12.6c.

| Fase | Horas | Pode paralelizar com | Pré-requisito |
| ---- | ----- | -------------------- | ------------- |
| F12.1 (a–d) | 16 | — | nenhum (✅ mergeado) |
| F12.1e | 4 | — | F12.1 (✅ commit `94cf939`) |
| F12.2 | 8  | F12.3, F12.4, F12.5 | F12.1e |
| F12.3 | 10 | F12.2, F12.4, F12.5 | F12.1e |
| F12.4 | 12 | F12.2, F12.3, F12.5 | F12.1e |
| F12.5 | 8  | F12.2, F12.3, F12.4 | F12.1e |
| F12.6a | 10 | — | F12.2 + F12.4 |
| F12.6b | 15 | — | F12.6a |
| F12.6c | 45 | (revisores externos) | F12.6b |
| F12.7 | — | (fora do escopo F12) | — |
| F12.8 | 10 | — | tudo acima |

## 10. Próximos passos para começar

1. **Confirmação do usuário** sobre:
   - Lista dos 10 locales (top 7 globais + pt-PT + de/ja/ko por
     requisito de produto APAC/EU/DACH).
   - Banner "beta" para locales com MT ratio > 5%.
   - Orçamento de ~$4.050 (DeepL Pro + revisão humana freelancer).
2. ✅ F12.1e fechada (commit `94cf939`, 2026-04-26) — fundação
   ressincronizada com a lista revisada de 10 locales.
3. Abrir lanes paralelas para F12.2, F12.3, F12.4, F12.5 (anunciar
   slugs em [BACKLOG.md F12](BACKLOG.md#f12--internacionalização-i18n-10-locales)).
4. F12.6a-b são técnicos (1 agente); F12.6c distribui entre revisores
   externos por locale.
5. F12.8 fecha QA E2E. F12.7 (RTL) volta como ticket isolado quando
   ar/he forem re-priorizados.

## 11. Pós-launch (fase 2, fora deste plano)

- Tradução de narrativas LLM (E5, E7) via parâmetro `lang` no prompt.
  Abrir nova ADR. Exige goldens novos por locale (Caminho B).
- Locale-aware sorting (`Intl.Collator`) em listagens de transações
  (especialmente para ru/zh-CN/ja/ko).
- Detecção de `Accept-Language` em sessão anônima (signup) — hoje cai
  em pt-BR.
- Variantes regionais adicionais (es-MX, en-GB, fr-CA, zh-TW, en-AU)
  entram como tickets isolados — infra já estará pronta.
- **RTL (`ar`, `he`):** quando demanda voltar, F12.7 (RTL polish)
  entra como ticket dedicado: `dir="rtl"` condicional, mirroring via
  CSS logical properties (já recomendadas), Noto Sans Arabic/Hebrew
  condicionais, ICU plurais 6-form para `ar`. Bibliotecas atuais
  (next-intl, format.ts) já comportam — overhead = só JSON novo +
  auditoria de margins.
- **Indic (`hi`, `bn`)** e **SE-Asia (`id`):** mesma extensão; reusam
  pipeline. Noto Sans Devanagari/Bengali entram em `fonts.ts`
  condicional; sem mudança arquitetural.
- Numerais nativos opcionais (Han `一二三` em zh-CN/ja, Devanagari
  `०१२` se hi voltar) como toggle ornamental.
- Documentação técnica em en (apenas se hire internacional ou
  open-source).
- Multi-currency real (BRL → USD/EUR/JPY/KRW conversion via FX API)
  como projeto separado.
