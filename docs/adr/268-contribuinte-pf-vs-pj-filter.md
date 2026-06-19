---
id: ADR-268
type: adr
title: "Filtro PF vs PJ no Contribuinte do IRPF — rejeitar razão social como nome de membro"
status: Decidido
phase: A17.member-identity
date: "2026-05-24"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-243]]"
  - "[[ADR-266]]"
  - "[[ADR-267]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 268"
  - "PF vs PJ filter"
  - "Contribuinte LTDA reject"
tags:
  - area/pipeline
  - area/llm
  - area/identity
  - status/proposto
  - type/adr
---

# ADR-268 — Filtro PF vs PJ no Contribuinte do IRPF

**Status:** Decidido • **Data:** 2026-05-24 • **Relaciona** [[ADR-157]] (E1.6 extract_irpf_full), [[ADR-238]] (data_adesao não é hard-fail), [[ADR-243]] (MemberNameResolver), [[ADR-266]] (IRPF completude tri-state), [[ADR-267]] (membro identity por CPF).

> **Revisão 2026-05-30.** A v1 desta ADR (mecanismo: `field_validator` em
> `Contribuinte.nome` que `raise ValidationError`) shipou em `PROMPT_VERSION
> e16-v1.1.1`. Em dogfood o validator **brickou o stage `analyze_finances`**:
> ele dispara em **todo** `model_validate`, inclusive na desserialização de
> artifacts persistidos no **read path** de E5 (`IRPFAnalyzer.from_payloads`).
> 1 IRPF-PJ legado abortava o stage inteiro em 0,4s; o segundo reader descartava
> os 10 IRPFs silenciosamente. Mesmo anti-padrão da [[ADR-238]] (hard-fail em
> dado que o mundo real produz). Esta revisão **mantém a decisão de produto**
> (razão social PJ não é contribuinte PF) mas **troca o mecanismo**: guardrail
> determinístico **pós-LLM sem raise** + filtro no read boundary. Detalhe nas
> seções Decisão, D2, Alternativas e Critério de aceite, atualizadas abaixo.

> **Extensão 2026-05-30 (b) — boundary de consolidação E1.5c (A21.l1, INV-9).**
> O read-filter `partition_irpf_payloads` (A') cobre o read path dos **payloads
> IRPF (E1.6)** no E5, mas existe um **segundo caminho de dados** que ele não
> intercepta: o artifact **consolidado** `baseline_patrimonial` que o E1.5c
> (`consolidate_from_itens`) escreve a partir de `itens[]` — que ainda inclui o
> item PJ, porque E1.6 só marca `needs_review` (não dropa). A própria seção
> Contexto já diagnosticava essa contaminação (*"consolidate_from_itens agrupa
> 4 itens dessa 'pessoa' no patrimônio"*) sem fechá-la. A suíte de invariantes
> da A21.l1 (INV-9) provou empiricamente o vazamento (R$4M no agregado). Fix:
> `detect_pj_suffix` como **pré-filtro no E1.5c** (o reader que origina o
> consolidado) — defense-in-depth, **não** substituto de A'. Cada boundary
> filtra o caminho que ele de fato origina; `itens[]` permanece **fiel** ao
> extraído (mesmo princípio de A', que não contamina o artifact E1.6). Detalhe
> em D2c + Alternativa (B) + Critério de aceite 8-9.

## Contexto

Workspace founder dogfood, run `f66b519e-…`: o extractor E1.6 (`extract_irpf_full`) extraiu 10 IRPFs, sendo **1 com `Contribuinte.nome = "DAVID ROBERT CAMARGO DE CAMPOS LTDA"`** (n_bens=4). Razão social com sufixo `LTDA` indica **Pessoa Jurídica**, não Pessoa Física — IRPF é declaração de PF.

Causa raiz: o documento upstream provavelmente NÃO era um IRPF (possivelmente um balancete, contrato social, IRPJ via Lucro Real, declaração de imposto da PJ) mas foi classificado em E0 como `receitafederal_irpfdeclaracao`. O LLM extrator E1.6 então aceitou e emitiu um `Contribuinte` com nome de empresa.

Downstream:
- `MemberNameResolver` ([[ADR-243]]) trata como pessoa nova (slug `david_robert_camargo_de_campos_ltda`).
- `MemberNameResolver.resolve_by_cpf` ([[ADR-267]]) não casa porque `Contribuinte.cpf_masked` em IRPF de PJ é inválido (PJs têm CNPJ, não CPF).
- `consolidate_from_itens` agrupa 4 itens dessa "pessoa" no patrimônio — contamina KPIs.

**Princípio violado:** IRPF é declaração de **Pessoa Física brasileira**. Razão social com sufixo de personificação jurídica não pode aparecer como `Contribuinte.nome`.

## Decisão

Detecção determinística de razão social PJ em `Contribuinte.nome` via helper puro
`detect_pj_suffix` (`pipeline/llm/schemas/e16_irpf_full.py`), consumido em **dois
pontos sem raise**: (1) E1.6 marca o artifact `needs_review=True` + telemetria; (2)
read boundary de E5 (`partition_irpf_payloads`) exclui a declaração PJ da análise.

**Princípio (schema evolution):** um guard de domínio write-time **não pode** viver
como `field_validator` que `raise` num model de **artifact persistido**. Validators
Pydantic disparam em todo `model_validate` — incluindo a desserialização no read.
Um artifact escrito antes do guard (ou via incremental) passa a quebrar o read em
reprocess. Guard de domínio → função pura chamada explicitamente onde faz sentido,
não validator de schema acoplado ao boundary de (de)serialização.

### D1 — Lista de sufixos PJ

Whitelist conservadora (RFB §1.094 + §1.052 do código civil + variantes comerciais),
compilada como regex único `_PJ_SUFFIX_RE` (`pipeline/llm/schemas/e16_irpf_full.py`):

```python
_PJ_SUFFIX_RE = re.compile(
    r"\b(?:LTDA|S\.?\s*A\.?|EIRELI|MEI|ME|EPP|SOCIEDADE|"
    r"ASSOCIA[CÇ][AÃ]O|FUNDA[CÇ][AÃ]O|COOPERATIVA)\b",
    re.IGNORECASE,
)
```

Cobre: LTDA (Limitada), S.A./S A/SA (Sociedade Anônima), EIRELI, MEI, ME, EPP,
SOCIEDADE, ASSOCIAÇÃO/ASSOCIACAO, FUNDAÇÃO/FUNDACAO, COOPERATIVA. Match
case-insensitive, com `\b` para evitar substring (ex.: `"SA"` em `"SARA"`).

### D2 — Comportamento na detecção (write — E1.6)

Quando `detect_pj_suffix(Contribuinte.nome)` casa um padrão PJ no `extract_irpf_full`:

1. **Sem raise.** O modelo desserializa normalmente — documento genuinamente PJ não
   é erro de extração do LLM; `raise` dispararia retry storm no `instructor`
   (`max_retries=3`), anti-padrão [[ADR-238]].
2. `payload["needs_review"] = True` (padrão regex→LLM→needs_review da [[ADR-081]]).
   O **artifact ainda é persistido** — fica inerte, sinalizado para revisão humana.
3. Telemetria: `logger.warning("rejected_pj", ...)` (logger `mathoms.pipeline.extract_irpf_full`)
   com `workspace_id`, `doc` (filename PII-redacted), `pattern_matched`.

### D2b — Comportamento no read boundary (E5)

`partition_irpf_payloads(payloads, keys)` (`pipeline/domain/services/irpf_analyzer.py`)
é o filtro único compartilhado pelos **dois** readers de E5 (`e5_analyzer_adapter` e
`scripts/e5_analyze`), que antes divergiam. Para cada payload exclui:

- **PJ** (`detect_pj_suffix` casou) → razão `pj_contribuinte`;
- **schema-inválido** (`model_validate` levanta) → razão `invalid_schema` — resiliência
  a schema evolution / artifact legado: 1 artifact ruim não derruba o stage.

Payloads válidos seguem para a análise; os pulados emitem
`logger.warning("irpf_payload_skipped", extra={"artifact_key", "reason"})`. Função
pura (sem I/O); o caller emite a telemetria.

### D2c — Comportamento no boundary de consolidação (E1.5c)

`consolidate_from_itens` (`scripts/e15_consolidate.py`) lê o baseline flat
`itens[]` — que **ainda contém** o item PJ (E1.6 só sinaliza, não dropa) — e
escreve o artifact consolidado `baseline_patrimonial` que o E5 também consome.
A' não toca esse caminho. Pré-filtro no início do loop, **antes** de resolver
membro:

```python
if detect_pj_suffix(item.get("membro") or ""):
    pj_skipped += 1
    continue
```

Dois cuidados de contrato:

1. **Agregado.** O `resumo.total_ativos`/`total_passivos` do LLM **somou o PJ**
   na extração; o consolidador o usa por padrão (mais confiável p/
   arredondamento). Quando `pj_skipped > 0`, esse override é **suprimido** e o
   agregado usa a soma recomputada dos itens PF-only — senão `patrimonio_por_ano`
   herdaria o valor PJ mesmo após dropar os itens (vazamento parcial silencioso).
2. **`itens[]` fiel.** O filtro vive no **reader** (E1.5c), não no produtor
   (`extract_baseline`/E1.5). `itens[]` permanece fiel ao extraído — mesmo
   princípio de A' (não contaminar o artifact E1.6). Dois readers PJ-aware (E5
   payloads + E1.5c itens) compartilham a **mesma** função `detect_pj_suffix`;
   sem duplicação de regra.

Telemetria: `log_stage("WARN", "pj_contribuinte_skipped (E1.5c): N item(ns)")`,
paralela a `rejected_pj` (write) e `irpf_payload_skipped` (read).

### D3 — Out of scope

- **Detecção em E0** — não tocada nesta ADR. Se o documento é de fato PJ (IRPJ, balancete), classificação correta em E0 evitaria o problema upstream. Lane futura.
- **Suporte a IRPJ** — produto Mathoms é planejamento patrimonial PF. Não há roadmap para extrair IRPJ. PJ aparece **como fonte pagadora** (`FontePagadoraPJ`), não como contribuinte.
- **CNPJ validation** — separate. CNPJ no campo `Contribuinte.cpf_masked` já falharia pattern existente (`_CPF_MASKED_PATTERN`).

### D4 — Falsos positivos esperados (aceitos)

Nomes PF que contêm substring batendo padrão PJ:

- `"MARIA SILVA SANTOS LTDA"` — improvável (PF não usa "LTDA"), mas se acontecer, marca `needs_review` (não bloqueia; humano decide).
- `"JOSÉ DA SOCIEDADE"` — `\bSOCIEDADE\b` casa. Possível falso positivo em nome incomum. Trade-off aceito: como o guardrail apenas sinaliza (não raise), o custo de um falso positivo é uma revisão humana, não perda de dado.
- `"FERNANDA EME"` — `\bME\b` casa só com `EME` se `\b` falhar. Regex usa word boundary; `EME` é uma palavra, `ME` é outra — não bate. Safe.

Não há regex perfeito; whitelist conservadora cobre 99%+ dos casos reais.

## Consequências

**Positivas:**

- "DAVID ROBERT CAMARGO DE CAMPOS LTDA" e similares são bloqueados antes de chegar ao consolidador.
- Membro identity (ADR-267) opera sobre PFs apenas — sem contaminação PJ.
- Telemetria identifica documentos PJ mal-classificados em E0 (sinal para tunar classificador).

**Negativas / trade-offs aceitos:**

- Lista finita de sufixos — pode haver formas legais novas no futuro (ex.: SLU - Sociedade Limitada Unipessoal, criada em 2019). Solução: PR incremental quando observado.
- Falso positivo em nome incomum (ex.: "FERNANDA DA SOCIEDADE BRASILEIRA DE GENÉTICA" — improvável mas possível). Mitigação: telemetria flagga para review.

## Observabilidade

Write (E1.6) — `logger.warning("rejected_pj")`:

```json
{
  "workspace_id": "<uuid>",
  "doc": "<filename-pii-redacted>",
  "pattern_matched": "LTDA"
}
```

Read (E5) — `logger.warning("irpf_payload_skipped")`:

```json
{ "artifact_key": "irpfdeclaracao_<ano>", "reason": "pj_contribuinte" }
```

Console interno (ADR-116) pode ganhar card "Documentos sinalizados como PJ" no dashboard de healthcheck.

## Critério de aceite

1. **PJ detectada, sem raise** — `detect_pj_suffix("DAVID ROBERT CAMARGO DE CAMPOS LTDA")` retorna `"LTDA"`; construir/`model_validate` o `IRPFFullOutput` com esse nome **nunca** levanta (a desserialização do artifact persistido sobrevive).
2. **PF não detectada** — `detect_pj_suffix("DAVID ROBERT CAMARGO FERREIRA CAMPOS")` retorna `None`.
3. **E1.6 sinaliza** — stage com IRPF-PJ persiste o artifact com `needs_review=True` e **1 chamada LLM** (sem retry storm).
4. **E5 sobrevive a PJ** — `partition_irpf_payloads` exclui o payload PJ + os schema-inválidos e mantém os válidos; o analyzer roda sem abortar mesmo com 1 IRPF-PJ no conjunto.
5. **Padrões cobertos** — LTDA, S.A., S A, SA, EIRELI, MEI, ME, EPP, SOCIEDADE, ASSOCIAÇÃO, FUNDAÇÃO, COOPERATIVA. Cada um com test unitário.
6. **Word boundary** — `"FERNANDA EME"` (PF legítima) NÃO casa `ME` parcial.
7. **Telemetria** — `rejected_pj` (write) e `irpf_payload_skipped` (read) emitidos.
8. **E1.5c não vaza PJ (itens)** — `consolidate_from_itens` sobre `itens[]` com 1 membro PJ não produz nenhum item com `proprietario` casando `detect_pj_suffix`; o ativo PF legítimo sobrevive (INV-9, A21.l1).
9. **E1.5c não vaza PJ (agregado)** — com `resumo.total_ativos` contaminado pelo valor PJ, `patrimonio_por_ano[ano].total_bens` reflete apenas o PF (override de `resumo` suprimido quando `pj_skipped > 0`).

## Alternativas consideradas

- **(A) `field_validator` que `raise` no schema** (v1, **revertido** — ver Revisão 2026-05-30): parecia "falha cedo, mensagem clara", mas validators Pydantic disparam em **todo** `model_validate`, inclusive no read de artifact persistido — brickou `analyze_finances` e disparou retry storm no write. Anti-padrão [[ADR-238]].
- **(A') Guardrail determinístico pós-LLM + read-boundary filter** (escolhido): mesma detecção (regex), mas como função pura sem raise. Write sinaliza `needs_review`; read filtra. Não acopla regra de domínio ao boundary de (de)serialização.
- **(B) Filtrar downstream em E1.5c** (rejeitado como mecanismo **único**; adotado como **defense-in-depth** na Extensão 2026-05-30 (b)): a objeção original — "consolidador precisa lógica de filtro espalhada" — valia para (B) como *substituto* de A'. O diagnóstico posterior (INV-9) mostrou que A' não cobre o caminho do artifact consolidado que o E1.5c origina. Adotar o pré-filtro em E1.5c como **segunda linha** (não substituto) honra a rejeição: cada boundary filtra o caminho que de fato origina, via a mesma função `detect_pj_suffix` (sem regra duplicada). Ver D2c.
- **(C) Detecção em E0 (classificador)** (parallel, out of scope): exige LLM ou heurística avançada para detectar documento PJ. Lane futura.
- **(D) `Optional[Contribuinte]`** (rejeitado): trata `None` como ausência, mas a ausência já é capturada por outro caminho. Adicionar nullable complica downstream consumers.

## Próximos passos

- **v1 (merged)**: `field_validator("nome")` em `Contribuinte` (`PROMPT_VERSION e16-v1.1.1`).
- **Revisão (merged)**: remove o validator; `detect_pj_suffix` + `_flag_pj_contribuinte` (E1.6) + `partition_irpf_payloads` (read boundary E5); `PROMPT_VERSION e16-v1.1.2`.
- **Extensão E1.5c (A21.l1)**: pré-filtro `detect_pj_suffix` em `consolidate_from_itens` + supressão do override de `resumo` quando há PJ filtrado; coberto por INV-8/9 da suíte de invariantes de consolidação. Defense-in-depth no boundary que origina o artifact consolidado.
- **Follow-up** (lane separada): detecção upstream em E0/document_classification — tunar classificador para rejeitar `irpfdeclaracao` quando documento é IRPJ/balancete/contrato social.
- **Flip ADR-268 → Decidido** após o workspace founder reprocessar e mostrar Mariana+David como únicos membros (sem LTDA contaminante) e `analyze_finances` rodar verde.
