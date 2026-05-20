---
id: ADR-233
type: adr
title: "Formato canônico de PROMPT_VERSION (semver puro) + gate CI de bump"
status: Proposto
phase: A11.W2
date: "2026-05-20"
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
  - status/proposto
  - type/adr
---

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
