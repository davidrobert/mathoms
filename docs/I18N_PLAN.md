# Plano canônico — Internacionalização (i18n)

> **Status:** Proposto · **Data:** 2026-04-25
> **ADR:** [ADR-130](DECISIONS.md#adr-130--internacionalização-com-next-intl--persistência-em-userslocale)
> **Fase no backlog:** [F12](BACKLOG.md#f12--internacionalização-i18n-11-locales)
>
> **Locales suportados (11):** ver §1.1 abaixo. Default: **pt-BR**.

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

Os 10 idiomas mais falados globalmente (Ethnologue 2024, total speakers
L1+L2) + variante pt-PT do português europeu:

| Prio | Locale (BCP-47) | Idioma | Speakers (M) | Script | Direção | Plurais |
| ---- | --------------- | ------------- | ------------ | ----------------- | ------- | ------- |
| 1    | `pt-BR` *(default)* | Português (Brasil) | ~265 | Latin            | LTR     | 2 |
| 2    | `en`            | English       | ~1.500       | Latin             | LTR     | 2 |
| 3    | `pt-PT`         | Português (Portugal) | ~10*  | Latin             | LTR     | 2 |
| 4    | `zh-CN`         | 中文 (简体, Mandarim) | ~1.100 | Han Simplified    | LTR     | 1 |
| 5    | `hi`            | हिन्दी (Hindi)  | ~610         | Devanagari        | LTR     | 2 |
| 6    | `es`            | Español       | ~560         | Latin             | LTR     | 2 |
| 7    | `ar`            | العربية (MSA) | ~270         | Arabic            | **RTL** | **6** |
| 8    | `fr`            | Français      | ~310         | Latin             | LTR     | 2 |
| 9    | `bn`            | বাংলা (Bengali) | ~270       | Bengali           | LTR     | 2 |
| 10   | `ru`            | Русский       | ~255         | Cyrillic          | LTR     | **4** |
| 11   | `id`            | Bahasa Indonesia | ~200      | Latin             | LTR     | 1 |

\* pt-PT mantido apesar de speakercount baixo: requisito explícito do
produto (mercado europeu de língua portuguesa, distinção lexical
relevante para fintech — "fatura"/"cêntimos"/etc.).

**Implicações por bucket:**

- **LTR Latin (pt-BR, en, pt-PT, es, fr, id):** baixo risco. Plus
  Jakarta + Inter + JetBrains Mono já cobrem Latin Extended-A.
  Plurais simples (1/many em pt-BR/en/es/fr; 1 em id).
- **RTL (ar):** `dir="rtl"` no `<html>`, mirroring de layout, **CSS
  logical properties** obrigatórias (`margin-inline-start` em vez de
  `margin-left`), Recharts/charts mantêm coordenadas (não mirroram
  números). Plurais ICU complexos (zero/one/two/few/many/other).
- **CJK (zh-CN):** Noto Sans SC como fallback; sem itálico
  (não-idiomático); densidade tipográfica diferente (line-height
  ajustar). Plural único (sem morfologia plural).
- **Indic (hi, bn):** Noto Sans Devanagari (hi) + Noto Sans Bengali
  (bn). Conjuntos vocálicos altos, line-height pode precisar +5%.
  Numerais mantém algarismos arábico-ocidentais (não Devanagari).
- **Cyrillic (ru):** plurais 4-form (one/few/many/other); Inter cobre.

## 2. Escopo

**Dentro do escopo:**

- ✅ UI estática (botões, labels, status, mensagens user-facing).
- ✅ Formatação de números/datas (refactor de `format.ts`,
  `<MonetaryValue/>`).
- ✅ Labels do `report_layout.yaml` via codegen.
- ✅ Mensagens de erro user-facing do backend (24 ocorrências mapeadas).
- ✅ Persistência da escolha em `users.locale` + cookie `NEXT_LOCALE`.
- ✅ RTL (árabe) com mirroring completo de layout.
- ✅ Fontes secundárias para CJK / Devanagari / Bengali.
- ✅ ICU MessageFormat para plurais.
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
- ❌ Conversão de moeda (BRL → CNY/EUR/INR). Produto é fintech BR; mostra
  BRL formatado no idioma local (símbolo "R$" mantém em todos; separadores
  seguem locale). Multi-currency real é projeto separado pós-GA.
- ❌ Locale-aware números no script local (ex.: numerais Devanagari ०१२
  em hi). Mantém algarismos arábico-ocidentais (padrão fintech global).

## 3. Decisões técnicas

| # | Decisão | Alternativa | Justificativa |
| --- | --- | --- | --- |
| 1 | `next-intl@^3` no frontend | `react-intl`, `i18next`, `lingui` | App Router-native, server components ok, bundle ~12kb, suporta ICU MessageFormat nativo, RTL ok |
| 2 | Cookie `NEXT_LOCALE` (não prefixo URL) | `/pt-BR/...` | Preserva ADR-108; SEO não é objetivo (app autenticado) |
| 3 | Persistência em `users.locale` (DB) | Só cookie/localStorage | Sobrevive a logout/troca de device; sincroniza com cookie |
| 4 | `pt-BR` como default | `Accept-Language` detect | Userbase é BR; outros locales são opt-in; menos surpresa |
| 5 | Chaves flat (`report.overview.title`) | Nested objects | Grep-friendly, codegen mais simples, reduz colisão de merge |
| 6 | Dicionários JSON em `frontend/src/i18n/messages/<locale>.json` | YAML, TOML | JSON é nativo; lint+diff bons; codegen output já é JSON-friendly |
| 7 | Backend lê locale de JWT claim → fallback `Accept-Language` → fallback `pt-BR` | Sempre header | JWT claim segue usuário entre devices |
| 8 | Locale como **enum tipado** (Pydantic + TS literal) com lista whitelist | string livre | Fail-fast em boundaries; segue ISP/ADR-097 D1 |
| 9 | **ICU MessageFormat** para plurais e seleção (`{count, plural, ...}`) | Concatenação manual | Necessário para ar (6 plurais) e ru (4 plurais); next-intl suporta nativamente |
| 10 | **CSS Logical Properties** em **todo** componente novo a partir de F12.1 | `margin-left/right` | Pré-requisito para RTL sem custo posterior |
| 11 | Fontes Indic/CJK carregadas **condicionalmente** por locale | Carregar todas sempre | Bundle CJK + Indic = ~600kb; carregar só quando locale ativo |
| 12 | Tradução: **MT (DeepL Pro) → glossário fintech → revisão humana** por locale antes de release não-beta | Tradução humana from-scratch | Custo: ~$200/locale via DeepL; humano apenas revisa (~10h/locale × 11 = 110h) vs from-scratch (~40h/locale × 11 = 440h) |

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
│       ├── hi.json
│       ├── es.json
│       ├── ar.json
│       ├── fr.json
│       ├── bn.json
│       ├── ru.json
│       └── id.json
├── middleware.ts              # next-intl middleware (cookie-based)
├── app/layout.tsx             # NextIntlClientProvider + dir + lang attrs
└── styles/
    └── rtl.css                # overrides específicos RTL (escasso, lógicas via logical props)
```

- **Server components** consomem `getTranslations()` (server-side, sem
  hydration cost).
- **Client components** consomem `useTranslations()` hook.
- **Middleware** detecta cookie `NEXT_LOCALE`; se ausente, default
  `pt-BR`. Nunca redireciona.
- **`<html lang="..." dir="...">`** definido em `app/layout.tsx`
  baseado em `getLocale()` + `RTL_LOCALES` set.
- **Fontes condicionais**: `app/layout.tsx` injeta `<link>` para
  Noto Sans SC (zh-CN), Devanagari (hi), Bengali (bn), Arabic (ar)
  apenas quando o locale ativo precisa.

### 4.2 Backend

- Migration Alembic: `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'`
  + CHECK constraint `locale IN (<lista dos 11>)`.
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
  recomendado** com 11 locales — vira ilegível. Sempre usar
  `i18n_key`.
- `dev/codegen_report_layout.py`: emite
  `frontend/src/generated/report-layout.ts` (+ Pydantic) com **apenas
  chaves i18n** (sem strings); valida que cada chave existe nos 11
  locales.
- Teste de paridade (`tests/test_i18n_parity.py`): para todas as chaves
  de `pt-BR.json`, deve existir entrada não-vazia em todos os 10
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
[<html lang dir>] aplica LTR/RTL no documento
   ↓
[<link>] carrega fonte secundária (Noto SC/Devanagari/Bengali/Arabic) sob demanda
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
- Criar `frontend/src/i18n/{config,request,plural}.ts` + `messages/<11
  locales>.json` (vazios, só `meta.locale`).
- `frontend/middleware.ts` com matcher detectando cookie + whitelist
  dos 11 locales.
- Wrap `app/layout.tsx` em `NextIntlClientProvider` + `<html lang
  dir>`.
- **`RTL_LOCALES = new Set(['ar'])`** + helper `getDir(locale)`.
- Carregamento condicional de fontes Indic/CJK/Arabic.
- Primeira string traduzida (ex.: título do menu) como prova de fluxo
  nos 11 locales.
- Teste Vitest: `useTranslations` resolve nos 11 locales; `dir="rtl"`
  ativa em `ar`.

**Critério de aceite:** alternar cookie `NEXT_LOCALE` no devtools muda
1 string visível no header em qualquer dos 11 locales. CI verde.
Fonte Noto Sans SC só carrega em zh-CN.

**Commit:** `feat(frontend): instala next-intl + middleware de locale (11 locales, cookie-based) (F12.1)`

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
- **Validar formatação BRL nos 11 locales:** `Intl.NumberFormat` cobre
  todos via runtime; smoke test confirma.

**Critério de aceite:** `BRL 1.234,56` em pt-BR/pt-PT, `BRL 1,234.56` em
en/zh-CN, `R$ ١٬٢٣٤٫٥٦` em ar (numerais arábico-orientais opcional —
ver §2 fora-do-escopo). Testes cobrem formatadores nos 11 locales.

**Commit:** `refactor(frontend): format.ts e MonetaryValue consomem locale via contexto (F12.2)`

### F12.3 — Persistência da escolha (~10h)

- Migration Alembic
  `backend/alembic/versions/<rev>_add_users_locale.py`:
  `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'` + CHECK
  constraint nos 11 valores.
- Pydantic `Locale` enum em `backend/app/domain/locale.py` (whitelist
  dos 11).
- JWT claim `locale` (abrir **ADR-A6f.5b** dedicada antes do commit;
  atualizar golden `test_auth_portability.py`).
- Endpoint `PATCH /users/me/preferences` (Pydantic schema +
  `response_model`); rodar `make update-openapi-snapshot`.
- Frontend: `/settings/preferences` com seletor de **11 opções**
  agrupadas (Ásia, Europa, Américas, Médio Oriente). Dropdown ordenado
  alfabeticamente por **nome nativo** do idioma.
- Teste integração: login em ar → JWT carrega claim → navegação
  preserva idioma e direção RTL.

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
- Traduzir labels existentes (≤30 strings) para os 10 locales
  não-pt-BR via DeepL + revisão (etapa MT delegada para F12.6).
- Teste `tests/test_i18n_parity.py`: paridade de chaves entre os 11
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

**Critério de aceite:** request com claim `locale=ar` retorna
`{"detail":"الوثيقة غير موجودة"}` (após F12.6 fechar). Logs permanecem
em formato fixo.

**Commit:** `feat(api): mensagens user-facing localizadas via JWT claim/header (F12.5)`

### F12.6 — Tradução do relatório (bulk, ~80h, paralelizável)

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
  - Output: 10 arquivos preenchidos + marca `_meta.mt: true` por chave
- Glossário fintech (`config/i18n_glossary.yaml`) força termos:
  - "fatura" → en: "credit-card statement", pt-PT: "fatura", ar:
    "كشف بطاقة الائتمان", etc.
  - "patrimônio" → en: "net worth", es: "patrimonio neto", etc.
  - "metas" → en: "goals", fr: "objectifs", etc.
- Custo estimado: ~$200/locale × 10 = $2.000 (DeepL Pro $20/mo + chars
  de overage); ~3.000 chars/locale × 10 ≈ 30k chars iniciais.

#### 6c) Revisão humana (55h)

- Por locale (~5h cada, 10 locales = 50h): revisor nativo passa por
  cada string MT, ratifica ou corrige. Marca `_meta.mt: false` quando
  ratificada.
- pt-PT: ~5h dedicadas (lexical: "centavos"→"cêntimos", "tela"→"ecrã"
  onde aplicável, evitar gerundismos, "fatura" pós-AO mantida).
- ar: revisor com expertise RTL valida quebras de linha, espaçamento,
  posição de números (ICU MessageFormat lida com bidi mark).
- Locales liberados para produção apenas com **ratio MT < 5%**. Acima
  disso, app exibe banner "beta — tradução automática".

#### 6d) Critério de aceite global

- Snapshot Playwright do relatório em 11 locales sem strings PT
  vazando (CI regex: nenhum acento PT em locales não-PT).
- pt-BR continua sendo o único default; outros locales podem ficar em
  beta na primeira release não bloqueia.

**Commit pattern:**
- `feat(frontend): extrai strings do relatório para i18n (F12.6a)`
- `chore(i18n): MT inicial via DeepL para 10 locales (F12.6b)`
- `feat(i18n): revisão humana para <locale> (F12.6c)`

### F12.7 — RTL polish (~12h)

> **Específico para árabe.** Inclui auditoria de mirroring.

- Auditoria `frontend/src/components/**` para uso de `margin-left`,
  `padding-right`, `text-align: left`, `border-left`, `transform:
  translateX(...)`. Substituir por logical properties
  (`margin-inline-start`, `padding-inline-end`, `text-align: start`,
  `border-inline-start`).
- Charts (Recharts): números mantêm algarismos arábico-ocidentais
  (não Devanagari/arábico-orientais); eixo X **não** mirrora em ar
  (datas mantêm ordem cronológica esquerda→direita).
- Ícones direcionais (setas, chevrons) recebem `class="rtl:scale-x-[-1]"`
  via Tailwind ou equivalente CSS.
- Snapshot visual em ar para 5 telas principais.

**Critério de aceite:** ar exibe layout 100% RTL sem overflow
horizontal; charts permanecem LTR (validado em snapshot).

**Commit:** `feat(frontend): polish RTL para locale ar (F12.7)`

### F12.8 — QA + E2E (~10h)

- Playwright: matrix nos fluxos `@critical` rodando 1× por locale =
  11 runs. Optar por `@critical` apenas (5 fluxos) para manter CI <
  20min: 5 × 11 = 55 runs paralelos.
- Visual regression do relatório nos 11 locales.
- Validar PDF export (`backend/app/services/pdf_renderer.py` →
  Playwright headless) renderiza locale correto via cookie injection.
- Atualizar [SMOKE_TEST.md](SMOKE_TEST.md) com checklist de troca de
  idioma (3 fluxos × 11 locales).

**Critério de aceite:** CI verde com matrix locale em fluxos `@critical`.
PDF gerado em ar tem direção RTL e fonte árabe; PDF em zh-CN tem
fonte SC.

**Commit:** `test(e2e): cobertura multi-locale para fluxos críticos (11 locales) (F12.8)`

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
  ar: "صافي الثروة"
  hi: "कुल संपत्ति"
  bn: "মোট সম্পদ"
  ru: "чистая стоимость"
  id: "kekayaan bersih"

invoice:
  pt-BR: "fatura"
  pt-PT: "fatura"
  en: "credit-card statement"
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

- **Custo total de tradução** (~1.500 strings × 10 locales = 15.000
  traduções): MT de partida (~$2.000) + revisão humana (~50h × $50/h
  freelancer = $2.500). **Total: ~$4.500** + custo interno.
- **JWT payload muda** (claim novo): breaking segundo ADR-109. Mitigado
  com ADR-A6f.5b dedicada e parity test atualizado.
- **Refactor de `format.ts`** toca ~80 call sites: feito em commit único
  (compilador acusa todos), revisão fácil.
- **Cookie sem prefixo URL**: SEO multilíngue não suportado. Aceito —
  app é autenticado, landing pública é fora de escopo (F8 Growth).
- **Bundle size**: messages JSON ~30kb/locale × 11 = ~330kb totais,
  mas next-intl carrega só o locale ativo. Fontes Indic/CJK
  condicionais (Noto SC ~150kb, Devanagari ~100kb, Bengali ~100kb,
  Arabic ~80kb) só vão pra wire quando o locale precisa.
- **RTL não-cruzado em charts**: decisão consciente (datas LTR mesmo
  em ar) — convenção fintech global. Documentado em
  [COPY_GUIDELINES.md](COPY_GUIDELINES.md) (a criar entrada).
- **Locales podem entrar em "beta"**: pt-BR + en saem prontos no
  release; demais 9 podem ser opt-in com banner até revisão humana
  fechar. Reduz risco de tradução errada em fintech.

## 8. Riscos e mitigação

| Risco | Probabilidade | Impacto | Mitigação |
| --- | --- | --- | --- |
| Tradução errada quebra confiança em fintech | Alta | Alto | Glossário fintech + revisão humana obrigatória antes de sair de "beta"; banner "beta" em locales não-revisados |
| RTL quebra layout em telas legadas | Alta | Médio | Auditoria F12.7 dedicada; CSS logical properties em todo código novo a partir de F12.1; lint rule custom |
| Fontes CJK/Indic/Arabic adicionam latência | Média | Baixo | Carregamento condicional por locale; preload via `<link rel="preload">` no critical path |
| ICU MessageFormat tem curva de aprendizado | Média | Baixo | Helper `<Plural count={n} one="..." other="..."/>`; doc em onboarding |
| JWT migration quebra sessões existentes | Média | Médio | Claim `locale` é **opcional** no decode; só preenchido em logins novos |
| MT ratio fica alto e nunca cai | Média | Alto | Locale fica em "beta" indefinidamente; OK se revisão não acontece. Critério explícito: < 5% para promover |
| Quarto locale variante (es-MX, en-GB, fr-CA) demanda explosão | Alta | Baixo | Variantes regionais NÃO entram nesse plano; quando vierem, reusam infra (overhead = só JSON novo) |
| Strings dinâmicas concatenadas (`"Você tem " + n + " documentos"`) | Alta | Médio | ESLint rule custom bloqueia; usar ICU `{count, plural, ...}` |
| Plurais ar/ru implementados errados | Média | Médio | Test goldens por locale com plural counts (0, 1, 2, 5, 11, 100) |

## 9. Dependências e ordem

```
F12.1 (fundação 11 locales) ─┬─ F12.2 (format.ts) ──┬─ F12.6 (relatório bulk)
                             ├─ F12.3 (persist DB)  ├─
                             ├─ F12.4 (codegen)     ┘
                             └─ F12.5 (backend msgs)

F12.6 ──→ F12.7 (RTL polish, depende de strings ar prontas)
F12.6 + F12.7 + F12.5 ──→ F12.8 (QA E2E)
```

- F12.1 é pré-requisito de tudo.
- F12.2, F12.3, F12.4, F12.5 são independentes entre si — paralelizáveis.
- F12.6 depende de F12.2 (format) e F12.4 (codegen).
- F12.7 depende de F12.6c (revisão ar pronta).
- F12.8 só faz sentido com todas as outras mergeadas.

**Estimativa total:** 156h engenharia + 50h revisão humana ≈
**~206h** com 1 agente em série; **~6 semanas** com 2 agentes em
paralelo nas fases independentes + revisores externos para F12.6c.

| Fase | Horas | Pode paralelizar com | Pré-requisito |
| ---- | ----- | -------------------- | ------------- |
| F12.1 | 16 | — | nenhum |
| F12.2 | 8  | F12.3, F12.4, F12.5 | F12.1 |
| F12.3 | 10 | F12.2, F12.4, F12.5 | F12.1 |
| F12.4 | 12 | F12.2, F12.3, F12.5 | F12.1 |
| F12.5 | 8  | F12.2, F12.3, F12.4 | F12.1 |
| F12.6a | 10 | — | F12.2 + F12.4 |
| F12.6b | 15 | — | F12.6a |
| F12.6c | 55 | (revisores externos) | F12.6b |
| F12.7 | 12 | — | F12.6c (ar) |
| F12.8 | 10 | — | tudo acima |

## 10. Próximos passos para começar

1. **Confirmação do usuário** sobre:
   - Lista dos 11 locales (top 10 + pt-PT).
   - Banner "beta" para locales com MT ratio > 5%.
   - Orçamento de ~$4.500 (DeepL Pro + revisão humana freelancer).
2. Abrir branch `agent/i18n-foundation/<yyyyMMdd-HHmm>` partindo de
   `origin/main`.
3. Executar **F12.1** (fundação 11 locales) como PR pequeno — prova o
   framework antes do bulk de F12.6.
4. Após F12.1 mergear, abrir lanes paralelas para F12.2, F12.3, F12.4,
   F12.5 (anunciar slugs em [BACKLOG.md F12](BACKLOG.md#f12--internacionalização-i18n-11-locales)).
5. F12.6a-b são técnicos (1 agente); F12.6c distribui entre revisores
   externos por locale.
6. F12.7 fecha RTL; F12.8 fecha QA E2E.

## 11. Pós-launch (fase 2, fora deste plano)

- Tradução de narrativas LLM (E5, E7) via parâmetro `lang` no prompt.
  Abrir nova ADR. Exige goldens novos por locale (Caminho B).
- Locale-aware sorting (`Intl.Collator`) em listagens de transações
  (especialmente para ru/ar/zh).
- Detecção de `Accept-Language` em sessão anônima (signup) — hoje cai
  em pt-BR.
- Variantes regionais adicionais (es-MX, en-GB, fr-CA, zh-TW) entram
  como tickets isolados — infra já estará pronta.
- Numerais nativos opcionais (Devanagari ०१२ em hi, arábico-orientais
  ١٢٣ em ar) como toggle.
- Documentação técnica em en (apenas se hire internacional ou
  open-source).
- Multi-currency real (BRL → USD/EUR/INR/CNY conversion via FX API)
  como projeto separado.
