---
id: TRACK-taxa-divida-numerica
type: track
title: "Track — Extração de taxa numérica de dívida (endurece RL-2 de best-effort para hard)"
sprint: A26
status: ready
created_at: "2026-07-02"
consumed_at: null
agent_role: data-engineer
tags:
  - type/track
  - sprint/a26
  - status/ready
  - area/pipeline
  - area/llm
  - priority/p2
---

# Track — Extração de taxa numérica de dívida

> **Lane ID:** `taxa-divida-numerica`
> **Branch prefix:** `agent/taxa-divida-numerica/<yyyyMMdd-HHmm>`
> **Origem:** análise competitiva visorfinance.app (2026-07-02) — Visor expõe detecção de recorrências/parcelamento; a tradução patrimonial correta é endurecer a análise de dívida já existente, não copiar o app de gastos.
> **Follow-up de:** [[ADR-300]] §Follow-ups ("Extração de `taxa_mensal` numérica — fortalece RL-2") + [[ADR-301]] §Follow-ups.
> **Severity:** P2 · **Effort:** S · **Owner:** data-engineer (co-review financial-planner)
> **Não reabre:** [[ADR-300]] RL-2 nem [[ADR-301]] (schema/dedup). Este track só preenche o campo que os torna hard.

---

## 1. Contexto — o gap é estreito e nomeado

O invariante "dívida cara precede risco" **já está decidido e enforced**:
[[ADR-300]] RL-2 `DIVIDA_CARA_PRECEDE_RISCO` bloqueia parecer que recomenda aporte
em risco sem priorizar quitação de dívida cara. Mas hoje é **best-effort**:

- `pipeline/domain/services/endividamento_analyzer.py:42` — `DividaItem.taxa_juros: str = "N/D"` (string livre, default N/D).
- `scripts/e5_analyze.py:1791` — mesmo default `"N/D"`.
- `backend/app/services/parecer_red_lines.py:250-256` — `_parse_taxa_mensal(div["taxa_juros"])`; RL-2 só dispara **hard** quando a taxa parseável `> 1,5% a.m.`. Com `"N/D"` → `None` → degrada para proxy `ratios.taxa_endividamento_pct ≥ 40` como **warning** (não bloqueia).

Ou seja: quando o documento de origem **traz** a taxa (fatura de cartão com rotativo/
parcelamento; empréstimo com CET), ela é descartada no parsing e a red line de maior
severidade fica cega. A dívida inserida manualmente via `/debt` já captura
`taxa_juros_aa` numérico (`backend/app/models/debt.py:129`); o buraco é só no **caminho
de extração automática**.

## 2. Escopo

Popular um campo de taxa **numérico e parseável** em `dividas[]` a partir da origem,
sem inventar valor quando o doc não traz:

1. **E2 — faturas de cartão:** extrair taxa do rotativo e taxa de parcelamento quando
   impressas na fatura (regex sobre o texto já extraído; padrão determinístico primeiro,
   E2-llm como fallback — [[ADR-081]]). Não inferir taxa pelo valor da parcela.
2. **E1.5 — Ficha de Bens e Dívidas / baseline:** capturar taxa/CET quando presente na
   descrição livre da dívida (regex em `e15_consolidate.py`, já apontado no follow-up da
   [[ADR-301]]).
3. **Contrato:** emitir `taxa_juros_aa` (a.a., paridade com o modelo DB e o schema
   opcional da [[ADR-301]]) **e/ou** `taxa_mensal` numérico. Alinhar o nome único com
   `data-engineer` antes de tocar `config/schemas/baseline_patrimonial.schema.json`
   (campo já é opcional lá — aperto não-breaking, modo `warn` primeiro).
4. **Consumo:** `_parse_taxa_mensal` passa a ler o campo numérico direto (sem parsing de
   string quando o numérico existe); RL-2 hard-fira sempre que a taxa numérica exceder o
   limiar. `DividaItem.taxa_juros` string permanece para display/legado.

## 3. Fora de escopo

- Inserção manual via `/debt` (já captura `taxa_juros_aa`).
- Detecção de recorrências/assinaturas e projeção de saldo de curto prazo — descartadas
  para o ICP na análise competitiva (feature de app de gastos, não patrimonial).
- Reabrir a calibração da RL-2 (limiar 1,5% a.m., versionamento `RED_LINES_VERSION`) —
  é da [[ADR-300]]; este track só alimenta o input.

## 4. Critério de aceite

- [ ] Fatura de cartão com rotativo/parcelamento impresso → `dividas[].taxa_juros_aa`
      numérico no artefato (fixture PII-zero em `tests/fixtures/`).
- [ ] Baseline com taxa na descrição da dívida → campo numérico populado; ausência → campo
      nulo (nunca valor inventado).
- [ ] `parecer_red_lines._parse_taxa_mensal` lê o numérico; teste determinístico prova
      RL-2 **hard** quando taxa numérica `> 1,5% a.m.` vinda de extração (não só de
      `/debt`), em `tests/test_parecer_red_lines.py` (padrão de fixtures envenenadas).
- [ ] Schema `baseline_patrimonial` valida o campo em `warn`; promoção a `strict` fora
      deste track.
- [ ] Goldens de execução (E5) regenerados; `total_dividas` inalterado (o campo é
      enriquecimento, não muda soma).

## 5. Delegação / gates

- **data-engineer:** contrato do campo (nome único `taxa_juros_aa` vs `taxa_mensal`),
  aperto de `config/schemas/baseline_patrimonial.schema.json`, impacto em golden.
- **financial-planner (co-review):** confirmar que só a taxa **impressa** vira input de
  RL-2 (sem folclore de inferência — cf. [[ADR-236]] "receita×32%" e [[ADR-301]] §3
  "não inferir tipo pelo valor").
- **Sem novo ADR:** conforma a [[ADR-300]]/[[ADR-301]] já decididas. Se o parsing exigir
  extensão de contrato entre stages além do campo opcional, aí sim ADR adjacente
  (decisão do data-engineer no pickup).
