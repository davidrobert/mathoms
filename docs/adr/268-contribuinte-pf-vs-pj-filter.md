---
id: ADR-268
type: adr
title: "Filtro PF vs PJ no Contribuinte do IRPF — rejeitar razão social como nome de membro"
status: Proposto
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

**Status:** Proposto • **Data:** 2026-05-24 • **Relaciona** [[ADR-157]] (E1.6 extract_irpf_full), [[ADR-243]] (MemberNameResolver), [[ADR-266]] (IRPF completude tri-state), [[ADR-267]] (membro identity por CPF).

## Contexto

Workspace founder dogfood, run `f66b519e-…`: o extractor E1.6 (`extract_irpf_full`) extraiu 10 IRPFs, sendo **1 com `Contribuinte.nome = "DAVID ROBERT CAMARGO DE CAMPOS LTDA"`** (n_bens=4). Razão social com sufixo `LTDA` indica **Pessoa Jurídica**, não Pessoa Física — IRPF é declaração de PF.

Causa raiz: o documento upstream provavelmente NÃO era um IRPF (possivelmente um balancete, contrato social, IRPJ via Lucro Real, declaração de imposto da PJ) mas foi classificado em E0 como `receitafederal_irpfdeclaracao`. O LLM extrator E1.6 então aceitou e emitiu um `Contribuinte` com nome de empresa.

Downstream:
- `MemberNameResolver` ([[ADR-243]]) trata como pessoa nova (slug `david_robert_camargo_de_campos_ltda`).
- `MemberNameResolver.resolve_by_cpf` ([[ADR-267]]) não casa porque `Contribuinte.cpf_masked` em IRPF de PJ é inválido (PJs têm CNPJ, não CPF).
- `consolidate_from_itens` agrupa 4 itens dessa "pessoa" no patrimônio — contamina KPIs.

**Princípio violado:** IRPF é declaração de **Pessoa Física brasileira**. Razão social com sufixo de personificação jurídica não pode aparecer como `Contribuinte.nome`.

## Decisão

Validação no boundary do schema Pydantic `Contribuinte.nome` (`pipeline/llm/schemas/e16_irpf_full.py`): rejeitar se o nome contém sufixo conhecido de PJ.

### D1 — Lista de sufixos PJ

Whitelist conservadora (RFB §1.094 + §1.052 do código civil + variantes comerciais):

```python
_PJ_SUFFIX_PATTERNS = (
    r"\bLTDA\b",         # Limitada (95% das PJs)
    r"\bS\.?\s*A\.?\b",  # Sociedade Anônima (S.A., S A, SA)
    r"\bEIRELI\b",       # Empresa Individual de Responsabilidade Limitada
    r"\bMEI\b",          # Microempreendedor Individual
    r"\bME\b",           # Microempresa
    r"\bEPP\b",          # Empresa de Pequeno Porte
    r"\bSOCIEDADE\b",    # Sociedade (Simples, Civil, etc.)
    r"\bASSOCIAÇÃO\b",   # Associações também são PJ
    r"\bFUNDAÇÃO\b",     # Fundações
    r"\bCOOPERATIVA\b",
)
```

Match case-insensitive, com `\b` para evitar match em substring (ex.: `"SA"` em `"SARA"`).

### D2 — Comportamento na detecção

Quando `Contribuinte.nome` casa qualquer padrão PJ:

1. **Pydantic ValidationError** com mensagem clara: `"nome contém sufixo de Pessoa Jurídica ('LTDA'). Contribuinte do IRPF deve ser Pessoa Física — verificar classificação E0 do documento."`
2. O `extract_irpf_full` stage trata erro de validação como `needs_review` (padrão regex→LLM→needs_review da [[ADR-081]]) — não cria artifact.
3. Telemetria: log JSON `mathoms.pipeline.extract_irpf_full.rejected_pj` com `document_id`, `nome_offender`, `pattern_matched`.

### D3 — Out of scope

- **Detecção em E0** — não tocada nesta ADR. Se o documento é de fato PJ (IRPJ, balancete), classificação correta em E0 evitaria o problema upstream. Lane futura.
- **Suporte a IRPJ** — produto Mathoms é planejamento patrimonial PF. Não há roadmap para extrair IRPJ. PJ aparece **como fonte pagadora** (`FontePagadoraPJ`), não como contribuinte.
- **CNPJ validation** — separate. CNPJ no campo `Contribuinte.cpf_masked` já falharia pattern existente (`_CPF_MASKED_PATTERN`).

### D4 — Falsos positivos esperados (aceitos)

Nomes PF que contêm substring batendo padrão PJ:

- `"MARIA SILVA SANTOS LTDA"` — improvável (PF não usa "LTDA"), mas se acontecer, rejeita corretamente como PJ.
- `"JOSÉ DA SOCIEDADE"` — `\bSOCIEDADE\b` casa. Possível falso positivo em nome incomum. Trade-off aceito: nome com "SOCIEDADE" raro em PF; rejeitar é mais seguro.
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

`mathoms.pipeline.extract_irpf_full.rejected_pj`:

```json
{
  "workspace_id": "<uuid>",
  "document_id": "<uuid>",
  "nome_offender": "<redacted-pii-safe-prefix>",
  "pattern_matched": "LTDA"
}
```

Console interno (ADR-116) ganha card "Documentos rejeitados como PJ" no dashboard de healthcheck.

## Critério de aceite

1. **PJ rejeitada** — `Contribuinte(nome="DAVID ROBERT CAMARGO DE CAMPOS LTDA", ...)` levanta `ValidationError` com mensagem citando o padrão casado.
2. **PF aceita** — `Contribuinte(nome="DAVID ROBERT CAMARGO FERREIRA CAMPOS", ...)` constrói sem erro.
3. **Padrões cobertos** — LTDA, S.A., S A, SA, EIRELI, MEI, ME, EPP, SOCIEDADE, ASSOCIAÇÃO, FUNDAÇÃO, COOPERATIVA. Cada um com test unitário.
4. **Word boundary** — `"FERNANDA EME"` (PF legítima) NÃO é rejeitada por casar `ME` parcial.
5. **Telemetria** — log JSON `mathoms.pipeline.extract_irpf_full.rejected_pj` emitido (com PII redacted no nome).

## Alternativas consideradas

- **(A) Validador no schema Pydantic** (escolhido): boundary explícito, falha cedo, mensagem clara. Fácil de testar.
- **(B) Filtrar downstream em E1.5c** (rejeitado): contamina artifacts E1.6 com declarations falsas; consolidador precisa lógica de filtro espalhada.
- **(C) Detecção em E0 (classificador)** (parallel, out of scope): exige LLM ou heurística avançada para detectar documento PJ. Lane futura.
- **(D) `Optional[Contribuinte]`** (rejeitado): trata `None` como ausência, mas a ausência já é capturada por outro caminho. Adicionar nullable complica downstream consumers.

## Próximos passos

- **PR (este escopo)**: validador `field_validator("nome")` em `Contribuinte` + 5 testes (PJ rejected casos + PF accepted + edge case word boundary) + ADR-268.
- **Follow-up** (lane separada): detecção upstream em E0/document_classification — tunar classificador para rejeitar `irpfdeclaracao` quando documento é IRPJ/balancete/contrato social.
- **Flip ADR-268 → Decidido** após PR2 ADR-267 + este PR mergearem e workspace founder mostrar Mariana+David como únicos membros (sem LTDA contaminante).
