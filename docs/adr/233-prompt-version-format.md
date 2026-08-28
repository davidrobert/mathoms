---
id: ADR-233
type: adr
title: "Formato canônico de PROMPT_VERSION (semver puro) + gate CI de bump"
status: Decidido
phase: A11.W2
date: "2026-05-20"
amended_at: ["2026-05-22", "2026-08-28"]
relates_to:
  - "[[ADR-093]]"
  - "[[ADR-157]]"
  - "[[ADR-199]]"
  - "[[ADR-216]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 233"
  - "PROMPT_VERSION format"
  - "LLM prompt versioning"
tags:
  - area/pipeline
  - area/llm
  - area/ci
  - phase/a11
  - status/decidido
  - type/adr
---

> ⚠️ **Emendada em 2026-08-28** ([[A40.l93]]): o escopo do gate deixa de ser
> "arquivo `.py` em `pipeline/llm/{prompts,schemas}`" e passa a ser **"declaração
> cuja `version` entra em chave de cache que não hasheia o texto do prompt"** — o que
> traz `config/prompts/*.yaml` para dentro, por lista declarada. Ver
> §Emenda 2026-08-28.

## Contexto

Sprint A11 W2-T05 introduz gate CI que exige bump de `PROMPT_VERSION` quando o conteúdo de um prompt LLM muda — garantia de que cache (LLM call cache, cache em DB) não sirva resposta stale após mudança de prompt. Pré-requisito: todo arquivo de prompt LLM precisa declarar a constante `PROMPT_VERSION`.

Durante a investigação, três formatos já coexistem no codebase:

| Arquivo | Valor atual | Formato |
| --- | --- | --- |
| `pipeline/llm/prompts/parecer_planejador.py` | `"1.0.0"` | semver puro |
| `pipeline/llm/schemas/e16_irpf_full.py` | `"e16-v1.1.0"` | `<slug>-v<semver>` |
| `pipeline/llm/schemas/informe_aluguel.py` | `"informe-aluguel-v1.1.0"` | `<slug>-v<semver>` |

Os formatos com prefixo (`e16-v…`, `informe-aluguel-v…`) viajam **no payload do artifact** (`payload["prompt_version"]` em `extract_irpf_full.py:121` e `extract_informe_aluguel.py:97`) e em registros `LLMCallLog.prompt_version` (col String(40)). Mudar a string quebra grep histórico, comparação exata em testes e consumers (UI/relatórios) que filtram por prompt_version.

Os 3 prompts pendentes de receber a constante na W2-T05 (`e1_members`, `e15_baseline`, `e2_llm`) ainda não persistem `prompt_version` em parte alguma — escolha de formato aqui é livre de débito legado.

## Decisão

**`PROMPT_VERSION` segue [semver](https://semver.org/lang/pt-BR/) puro como formato canônico daqui pra frente:**

```python
PROMPT_VERSION = "1.0.0"          # major.minor.patch — sempre 3 segmentos
```

- **major** (`1.x.x → 2.x.x`): mudança de contrato semântico — schema de output muda, instruções de extração mudam de forma que reprocessamento manual é necessário, output esperado é incompatível com cache prévio.
- **minor** (`1.0.x → 1.1.x`): novo campo opcional, regra adicional não-breaking, refinamento de instrução que melhora qualidade.
- **patch** (`1.0.0 → 1.0.1`): typo, reformatação de texto, ajuste cosmético — invalida cache mas não muda comportamento esperado.

**Padrão de declaração:**

```python
# pipeline/llm/prompts/<stage>.py
PROMPT_VERSION = "1.0.0"   # bumpar quando SYSTEM_PROMPT/USER_PROMPT_TEMPLATE mudar — gate CI valida (W2-T05).

SYSTEM_PROMPT = """..."""
USER_PROMPT_TEMPLATE = """..."""
```

A constante mora **no módulo do prompt** (`pipeline/llm/prompts/<stage>.py`), não no schema — porque ela versiona o **template de instruções**, não o contrato de output. `parecer_planejador.py` é o exemplar canônico.

### Tolerância para legados

`e16_irpf_full.PROMPT_VERSION` (`"e16-v1.1.0"`) e `informe_aluguel.PROMPT_VERSION` (`"informe-aluguel-v1.1.0"`) permanecem **inalterados** — a constante já viaja em payloads em produção, em rows `llm_call_log.prompt_version` e em assertions de teste. Quebrar o formato custaria coordenação com migrations + dados existentes sem ganho proporcional.

**O gate CI (`dev/check_prompt_version_bumped.py`) aceita ambos:**

```regex
^(\d+\.\d+\.\d+|[\w-]+-v\d+\.\d+\.\d+)$
```

- semver puro: `1.0.0`, `2.1.3`
- prefix legado: `e16-v1.1.0`, `informe-aluguel-v1.1.0`

Não aceita `v\d+` (sugestão original do track W2-T05 — preditiva, não existe no codebase).

### Onde a constante vive

- `pipeline/llm/prompts/<stage>.py` é o **destino padrão** para prompts novos.
- `pipeline/llm/schemas/<stage>.py` é aceito apenas para os 2 legados (`e16_irpf_full`, `informe_aluguel`) que persistem `prompt_version` como default de campo Pydantic no schema. Não migrar.

### Trade-offs

| Aspecto | Semver puro | `<slug>-v<semver>` | `v\d+` |
| --- | --- | --- | --- |
| Auto-descrição | Baixa (precisa contexto do arquivo) | Alta (slug embutido) | Mínima |
| Compatibilidade com `version.parse()` Python | ✅ | ❌ (precisa strip do prefix) | ❌ |
| Tamanho col DB (`String(40)`) | Folga grande | Folga média | Folga grande |
| Compat com padrão semver da indústria (pip, npm) | ✅ | ❌ | ❌ |
| Custo de migração de legado | n/a | n/a | Alto (32k+ rows hipotéticos) |

Semver puro vence em legibilidade automatizada (pyver / packaging) e padronização. Slug no formato legado fica acoplado ao filename — quando renomeia arquivo, slug fica defasado mas string em DB não.

## Consequências

- **Bom:** prompt novo escolhe `"1.0.0"` deterministicamente; gate CI exige bump; `version.parse(p)` funciona para ordenação cronológica.
- **Bom:** legados continuam funcionando sem mudança — sem risco de quebrar produção.
- **Ruim:** dois formatos convivem indefinidamente. Mitigação: dev/check_prompt_version_bumped.py valida ambos contra a mesma regex; novo prompt usa semver puro por convenção (CLAUDE.md doc não atualizado nesta lane — diff trivial em sprint subsequente).
- **Ruim:** semver puro não embute identificador do arquivo. Mitigação: column `llm_call_log.stage` + nome do prompt em logs estruturados já dão a rastreabilidade equivalente.

## Plano de migração

Não há migração — convive. Critérios de revisitação:

- Se o gate causar falsos-positivos crônicos por confusão entre formatos → revisar.
- Se um terceiro padrão emergir (ex.: hash do conteúdo do prompt) → ADR de superseção.

## Alternativas consideradas

1. **Forçar uniformização para semver puro agora.** Custo: editar 2 arquivos schemas + atualizar consumers + escrever migration para `llm_call_log.prompt_version` reescrevendo `"e16-v1.1.0"` → `"1.1.0"`. Risco: drift entre histórico (e16-v1.1.0) e novo (1.1.0). Ganho marginal. Rejeitado.

2. **Forçar uniformização para `<slug>-v<semver>` (padrão e16).** Quebra `parecer_planejador.py` (já em prod). Mesmo problema de migração. Rejeitado.

3. **`v\d+` counter simples (sugestão original do track).** Não casa com nenhum formato existente, não é semver, perde granularidade major/minor/patch. Track autoriza ADR para refinamento — esta ADR é o output. Rejeitado.

4. **Hash do conteúdo do prompt como versão.** Bypassa o problema de bump manual (gate vira só verificação de drift). Custo: muda contrato de `prompt_version` em payloads existentes (string opaca em vez de versão legível). Adiável para ADR futura se necessário.

## Aceite

- 3 prompts em `pipeline/llm/prompts/` (`e1_members`, `e15_baseline`, `e2_llm`) recebem `PROMPT_VERSION = "1.0.0"`.
- `dev/check_prompt_version_bumped.py` valida regex `^(\d+\.\d+\.\d+|[\w-]+-v\d+\.\d+\.\d+)$`.
- ADR-233 flipa para `Decidido` no PR de fechamento da W2-T05.

---

## §Migration (errata 2026-05-22, oriunda do plano [[PLAN-llm-prompts-hardening]] W2-T01)

**Status da errata:** Proposto • Revisita parcial da decisão original (formatos legados continuariam coexistindo) à luz de novos requisitos de telemetria.

### Por que a errata

Revisão paralela do plano [[PLAN-llm-prompts-hardening]] em 2026-05-22 (`data-engineer` + `senior-cto`) identificou que **manter `<slug>-vX.Y.Z` legado coexistindo com semver puro causa ruído em telemetria por `prompt_version`** ([[ADR-260]]):

- Label OTLP `mathoms.llm.confidence{prompt_version="e16-v1.1.0"}` é desnecessariamente longo.
- Agrupamento por `prompt_version` em SQL `LLMCallLog` retorna 2 buckets para o mesmo prompt (semver vs. legado) se houver bump misturado.
- Coordenada de dimensão (`prompt_name`) é informação separada — slug no `prompt_version` é redundância informacional.

Decisão da errata: **migrar os 5 prompts legados para semver puro com migration coordenada de histórico**, em vez de "conviver indefinidamente" como decidido na primeira versão.

### Escopo da migration

5 prompts em formato `<slug>-vX.Y.Z` migram para semver puro:

| Prompt / schema | Versão legada | Versão pós-migration |
|---|---|---|
| `apolice.py` | `apolice-v1.0.0` | `1.0.0` |
| `crlv.py` | `crlv-v1.0.0` | `1.0.0` |
| `e16_irpf_full.py` (schema) | `e16-v1.1.0` | `1.1.0` |
| `informe_aluguel.py` (schema) | `informe-aluguel-v1.1.0` (ou `1.2.0` pós-W1α) | `1.2.0` |
| `informe_previdencia.py` | `informe-prev-v1.0.0` | `1.0.0` |

### Migration coordenada de histórico

**Antes** da migration de `PROMPT_VERSION` no código:

1. Snapshot histórico via `dev/snapshot_llm_call_log_history.py` ([[ADR-261]]):
   ```bash
   python3 dev/snapshot_llm_call_log_history.py --all-legacy \
     --output _archive/llm_call_log_pre_semver_migration_<date>.csv
   ```
2. Migration Alembic atualiza `LLMCallLog.prompt_version` via regex `^([\w-]+)-v(\d+\.\d+\.\d+)$ → \2`. Preserva linha original em coluna nova `prompt_version_legacy` (text, nullable) para grep histórico.
3. Migration coordenada de `pipeline_artifacts.metadata.prompt_version` via JSON path UPDATE — mesmo padrão.

### Gate CI pós-migration

`dev/check_prompt_version_bumped.py` ganha **modo estrito**: regex `^\d+\.\d+\.\d+$` (sem alternativa `<slug>-v`). Falha PR que tenta reintroduzir formato legado.

### Coordenação com [[ADR-260]]

Esta errata é pré-requisito de [[ADR-260]] (telemetria) — sem migration, labels OTLP ficam misturados entre semver e slug. Errata executada em PR coordenado de W2-T01 do plano [[PLAN-llm-prompts-hardening]].

### Aceite da errata

- `LLMCallLog.prompt_version` 100% em formato `\d+\.\d+\.\d+` pós-migration.
- `pipeline_artifacts.metadata.prompt_version` 100% em semver puro pós-migration.
- Snapshot `_archive/llm_call_log_pre_semver_migration_<date>.csv` commitado.
- Gate `dev/check_prompt_version_bumped.py` em modo estrito.
- ADR-233 + esta errata flipam para `Decidido` no PR de fechamento da W2-T01.

## Emenda 2026-08-28 — o critério é a chave de cache, não o diretório

**Origem:** achado **N2** do painel de fecho da [[A40.l89]], executado pela [[A40.l93]].

`config/prompts/parecer_planejador.yaml` declara `version:`, que vira
`manifest_version` e entra na chave do cache Redis do parecer com **TTL de 7 dias**
(`parecer_orchestrator.compute_cache_key`). O gate não alcançava o arquivo: editar o
manifest sem bump servia parecer gerado sob o manifest anterior por uma semana. Mesma
forma em `config/prompts/section_summaries.yaml` (chave da narrativa de seção, TTL 24h).

### O critério de admissão, e por que não é o diretório

Admite-se um arquivo quando **a `version` dele entra numa chave de cache que não
hasheia o texto do prompt**. O cache genérico de resposta LLM ([[ADR-307]]) hasheia
`system_prompt` + `user_prompt` renderizados e **se auto-invalida**; prompt que passa
só por ele não precisa do bump manual. Foi por isso que `config/prompts/*.yaml` inteiro
não entrou por glob: `e16_codigos_rfb_2024.yaml` é tabela injetada no user prompt e já
protegida pelo hash; `chart_conclusions.yaml` tem `version:` **sem leitor nenhum**.

Glob cobraria bump nesses dois — falso positivo em toda edição editorial — e, pior,
produziria **garantia falsa**: quem lesse o hook assumiria cobertura onde não há cache
a proteger.

### Igualdade de conjunto, não allowlist

Todo `.yaml` de `config/prompts/` tem de estar em `YAML_VERSIONADO` **ou** em
`YAML_SEM_CACHE_VERSIONADO`, cada entrada com o motivo em uma linha. Arquivo novo em
nenhuma das duas **reprova**, pedindo o veredito. A razão é o próprio N2: allowlist que
só cresce falha aberta, e foi assim que o manifest ficou de fora por meses.

### Duas correções ao instrumento, exigidas pela ampliação

1. **O gate falhava aberto com ref irresolvível.** `_read_upstream` devolvia `None`
   tanto para "arquivo novo" quanto para "ref não existe", e `_check_bump` tratava os
   dois como OK — ref quebrada desligava o gate **inteiro** em silêncio. Agora
   `git rev-parse --verify` roda antes e falha alto, nomeando
   `MATHOMS_PROMPT_VERSION_BASE`. Ampliar a cobertura de um instrumento que pode estar
   desligado seria a classe de defeito que a l93 fecha nos outros três.
2. **Presença é checagem local.** No `.py` a ausência da constante significa "não é
   prompt" (auto-discovery); no YAML a lista **é** a declaração de que aquela `version`
   é load-bearing, então ausência é contradição e o gate a nomeia. Essa checagem lê só
   o disco e roda **fora** do ramo que exige a ref — sobrevive a clone raso, ao
   contrário da guarda equivalente do `.py`, que vive dentro de `_check_bump`.

### Formato: uma classe só

Os cinco YAMLs com `version` usavam `"1.1"`, `1`, `"1.2"`, `"2.5.0"`. Migraram para
semver puro (`section_summaries` `1.1`→`1.1.0`, `lineage_debug` `1.2`→`1.2.0`) em
commit próprio, **antes** do que estende o gate. Manter duas disciplinas de formato é
o que a §Migration de 2026-05-22 já rejeitou uma vez, pela mesma razão (bucket-splitting
na telemetria por `prompt_version`). Custo aceito e medido: uma invalidação de 24h na
narrativa de seção e um bucket de telemetria dividido.

### O que esta emenda NÃO faz

- **Não cria job de CI.** O gate vive só no pre-commit — `rg 'prompt_version_bumped'
  .github/workflows/` é vazio. Quem citar "gate de CI" a partir daqui está citando o
  título da ADR, não o entregue.
- **Não resolve a atribuição do e16.** Editar as tabelas RFB muda o prompt sem bumpar
  `pipeline/llm/schemas/e16_irpf_full.py::PROMPT_VERSION`. O cache está protegido pelo
  hash da [[ADR-307]]; o defeito é de **atribuição** (dois prompts distintos carimbados
  com a mesma `prompt_version` em `LLMCallLog`). Follow-up com dono, fora da l93.
