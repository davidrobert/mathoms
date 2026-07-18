---
id: ADR-336
type: adr
title: "Roteamento de lucro PJ mal-classificado como dividendo via segundo sinal de fluxo (TRS)"
status: Proposto
phase: dogfood cluster A
date: "2026-07-14"
supersedes: []
relates_to:
  - "[[ADR-191]]"
  - "[[ADR-236]]"
  - "[[ADR-330]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-336 — Roteamento de lucro PJ via segundo sinal de fluxo

> Cluster **A** (P0) da re-review dogfood 2026-07-13 · PLAN-dogfood-report-fix.
> Co-design `financial-planner` + `data-engineer` (2026-07-14) sobre evidência empírica.
> Supersede parcial da [[ADR-191]] (A28.l2 tratava só o match por-linha do IRPF).

## Contexto

No dogfood, a TRS efetiva é **14,08%** e a renda passiva mensal **R$ 27,2k** (≈89% do custo
essencial → parece quase-IF), contra o honesto `goals.if_pct=24,94%`. A causa é empírica e
**verificada** (não a hipótese `ganho_capital`, que é **0** neste run): o bucket `dividendos`
concentra **R$ 284.875** (87% da renda passiva) — que é **distribuição de lucro PJ do titular
mal-classificada**, não yield de carteira. Três provas convergentes: (a) yield implícito >190%
sobre o sleeve de RV-BR é impossível; (b) o sinal de fluxo `fluxo_caixa.por_fonte.lucros_distribuidos`
anualizado (≈R$ 308k/ano) **excede** o cod-09 de dividendos; (c) as fontes do fluxo são PJs
operacionais do titular (zero custodiante B3).

O roteamento por-linha existente (`_split_dividendos` + match de participação societária via IRPF
cod-32, A28.l2) **falhou**: `distribuicao_pj_titular=0`. O match exige que a quota esteja declarada
como cod-32 **e** que o campo `fonte` do cod-09 contenha CNPJ/nome resolvível — condição não
satisfeita aqui (formato de declaração / redação).

## Decisão

**Segundo sinal determinístico**, independente do IRPF: a classificação de fluxo de caixa
`lucros_distribuidos` ([[ADR-236]]), exposta pela [[ADR-330]] em `receita_por_natureza`, eleva
`distribuicao_pj_titular` acima do piso do match IRPF.

1. **VO tipado** `DistribuicaoPJSignal(lucros_distribuidos_brl, janela_meses)` com
   `.anualizado() = lucros × 12 / janela_meses`. Parâmetro **opcional** (`None` → comportamento
   idêntico ao atual) em `PassiveIncomeCalculator.calculate(...)`; conversão dict→VO no adapter
   (ADR-097 D2), a partir de `por_fonte["lucros_distribuidos"]` (isolado — **não** o agregado
   `receita_pj`, que vazaria pró-labore).
2. **Fórmula** (piso + teto, monótona): `distribuicao_pj_titular = MIN(cod09_total,
   MAX(matched_irpf, lucros_anualizado))`; `dividendos_yield = cod09_total − distribuicao_pj_titular`.
   Piso no match IRPF (só eleva, nunca reduz); teto no cod-09 declarado (nunca fabrica além).
3. **Ordem (conservação):** a elevação é o **último** passo, **após** `_complement_with_informes`
   — senão o informe re-injeta os dividendos zerados quando `dividendos==0`.
4. **`ganho_capital` fora do numerador** `.total` (realização one-time ≠ yield recorrente) **e**
   subtraído no delta de aluguéis (linha ~203) — senão vaza para `alugueis`. Permanece visível em
   `renda_passiva_por_fonte_brl` (transparência).

## Rationale

Roteamento (decisão travada do owner: lucro PJ do titular = renda ativa) via sinal robusto e
independente do IRPF. **Conservation-safe**: a reclassificação vive no pool
`(dividendos + distribuicao_pj_titular) = cod09_total` (invariante); o delta de aluguéis subtrai
`cod09_total` qualquer que seja o split, logo `alugueis` **não muda**. Lucro de PJ operacional é
remuneração de trabalho do sócio — não é yield de capital.

## Alternativas consideradas

- **Excluir só `ganho_capital`** (hipótese da revisão final do FP): **refutada** — é 0 no dogfood;
  não toca a inflação. Mantida como hardening (ponto 4), não como fix.
- **`MAX(matched, flow)` sem teto**: fabricaria distribuição além do cod-09 declarado. Rejeitada
  (teto no cod-09).
- **Proteção `yield_ref`** (preservar fatia de dividendo genuíno = `sleeve_RV_BR × ~8%`): **follow-up
  documentado** — exige threading do sleeve RV-BR + constante nova; o dogfood não tem dividendo
  genuíno (fluxo mede a PJ real, teto no cod-09 já limita). Endereça mis-classificação do E4, 2ª ordem.

## Consequências

- TRS efetiva cai de 14,08% → faixa plausível (~2%); `status` "suspeito" limpa **naturalmente**
  (o gate detectou problema real; o fix remove o problema, não o detector).
- **Gate de supressão** (C3) vira **defense-in-depth** (mantido, não removido; não dispara aqui).
- **Estimador** `renda_passiva_estimada` (base `investivel_efetivo`) + relabel do campo `*_4pct`:
  feature P1 **desacoplada** (forward-looking ≠ observado) — não segura este P0.
- Sem bump de schema (`distribuicao_pj_titular` já existe desde A28.l2). Sem mudança de DB.
- **Follow-up:** (a) `yield_ref` p/ portfolios com dividendo genuíno + PJ; (b) emitir
  `lucros_distribuidos` 12m por-categoria no enricher (precisão de anualização vs janela longa).

## Critério de aceite (4 lentes)

- **Completude** — `distribuicao_pj_titular > 0` no dogfood; nenhum consumidor lê `dividendos`
  cru como se fosse yield sem passar pelo split.
- **Corretude** — golden red-before-green: TRS 14,08% → <8%, `distribuicao_pj_titular` ≈ R$ 273–285k,
  `dividendos_yield` ≥ 0; unit com `matched=0` (eleva via fluxo), `matched>0` (piso preservado),
  teto (`flow>cod09` ⇒ cap em cod09), `signal=None` (bit-idêntico ao atual).
- **Consistência** — invariante `dividendos + distribuicao_pj_titular == cod09_total` (cents);
  `alugueis` idêntico com/sem sinal (delta invariante); `ganho_capital` fora de `.total` não move `alugueis`.
- **Precisão** — `Decimal` exato ([[ADR-090]]); `lucros_anualizado = lucros × 12 / janela_meses`;
  teto no cod-09 impede fabricação.
