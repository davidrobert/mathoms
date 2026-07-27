---
id: ADR-352
type: adr
title: "Decomposição do prêmio de seguro por cobertura (bottom-up), não por bem dominante"
status: Proposto
phase: pipeline-review r2 (RV2-26)
date: "2026-07-27"
relates_to:
  - "[[ADR-240]]"
  - "[[ADR-090]]"
  - "[[ADR-343]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
---

# ADR-352 — Decomposição do prêmio por cobertura

> Achado **RV2-26** do pipeline-review r2 ([[ADR-343]], run `9d47574c`, ws 5@5.com).
> `Proposto` — muda um número exibido (a decomposição do prêmio no card de proteção);
> o label do bucket residual é product-visible (follow-up de label map, ver §Consequências).

## Contexto

`protecao_analyzer._premio_decomposicao` atribui o **prêmio inteiro** de cada
apólice a uma **única** categoria, escolhida por `_categoriza_apolice` (bem
dominante): `veiculo→auto`, `imovel→residencial`, `pessoa→vida/saude/ap`, e
**fallback `"auto"`** quando não há bem determinável (`protecao_analyzer.py:166`).

Dois defeitos:

1. **Colapso multi-bem.** Apólice cobrindo imóvel **e** veículo tem 100% do
   prêmio jogado em `auto` (o `veiculo` vence o `imovel` no `_categoriza_apolice`).
   A composição do gasto com seguro fica falsa.
2. **Fabricação de categoria.** No ws 5@5.com as 3 apólices vigentes vêm do E4
   `seguros` com `bens_segurados=[]` (extração sem detalhe de bem/cobertura). O
   fallback rotula os R$6.022,27 como `"auto"` — uma categoria **específica e
   errada** — em vez de admitir que a apólice não foi classificada. Resultado
   real: `premio_decomposicao = {"auto": "6022.27"}`.

## Decisão

Decompor **bottom-up por cobertura**, com invariante de conservação por apólice.

### D1 — Categoria de uma cobertura

`categoria(bem.tipo, cobertura.tipo)`:

- `veiculo` → `auto`;
- `imovel` → `residencial`;
- `pessoa` → pela cobertura: `vida→vida`, `saude→saude`, `acidentes→ap`,
  outra → `vida` (fallback conservador, igual ao V2 atual).

### D2 — Peso e alocação (invariante Σ == premio_total)

Por apólice: `peso[categoria] = Σ cobertura.premio_brl` das coberturas que mapeiam
para aquela categoria. O `premio_total_brl` (que inclui IOF + custo de emissão,
> Σ prêmios de cobertura) é **alocado proporcionalmente** aos pesos, com
arredondamento **cent-exato por maior-resto** (largest-remainder). Assim:

- a diferença `premio_total − Σ coberturas` (IOF/emissão) é distribuída na
  proporção da cobertura — não some nem infla um bucket;
- **`Σ premio_decomposicao == premio_total` cent-exato** (invariante testado).

### D3 — Cadeia de fallback (apólice sem cobertura precificada)

Quando `Σ peso == 0` (nenhuma cobertura com `premio_brl > 0`):

1. `_categoriza_apolice` (bem dominante) se houver `bens_segurados`; senão
2. **`"nao_identificado"`** — nunca fabricar `"auto"`. O prêmio total inteiro
   vai para esse bucket único (invariante trivialmente preservado).

Para o ws 5@5.com (bens vazios) isso troca `{"auto": 6022.27}` por
`{"nao_identificado": 6022.27}` — honesto sobre o que é conhecido.

## Consequências

**Positivas:** composição do prêmio fiel a apólices multi-bem; nenhuma categoria
específica fabricada para apólice sem detalhe; conservação cent-exata garante
que o card de decomposição sempre soma o prêmio total exibido.

**Negativas / trade-offs:**

- **Novo bucket `nao_identificado` é product-visible.** O card
  (`ProtecaoKpiHero.tsx`) renderiza as chaves **cruas** (`{tipo}:`) — hoje já
  mostra `auto:` literal. Trocar por `nao_identificado:` é mais honesto porém
  feio. **Follow-up product-designer:** mapa `categoria → label`
  (`auto→"Automóvel"`, `residencial→"Residencial"`, `vida→"Vida"`,
  `saude→"Saúde"`, `ap→"Acidentes Pessoais"`, `nao_identificado→"Não
  identificado"`). Fora do escopo deste PR (backend data-correctness).
- Depende da qualidade da extração de `bens_segurados`/`coberturas` em E2. A
  extração degradada (bens vazios) é sinalizada honestamente, não corrigida
  aqui — a melhora upstream do extractor de apólice é lane própria.

## Alternativas consideradas

- **(A) Manter bem-dominante** (rejeitado): colapsa multi-bem e fabrica `auto`.
- **(B) Bottom-up por cobertura + fallback honesto** (escolhido): fiel quando há
  cobertura; honesto quando não há; invariante cent-exato.
- **(C) Ratear `premio_total` igualmente entre bens** (rejeitado): sem base —
  um bem barato e um caro receberiam o mesmo peso.

## Critério de aceite

1. Apólice multi-bem (imóvel material + veículo rcfv, cada `premio_brl`) →
   decomposição `{residencial, auto}` proporcional; `Σ == premio_total` cent-exato.
2. Apólice sem `bens_segurados` → `{"nao_identificado": premio_total}` (nunca `auto`).
3. Apólice pessoa (vida + acidentes) → `{vida, ap}` proporcional.
4. Invariante `Σ premio_decomposicao == premio_total` cent-exato em toda entrada,
   incluindo mistura de apólices com e sem cobertura precificada.
