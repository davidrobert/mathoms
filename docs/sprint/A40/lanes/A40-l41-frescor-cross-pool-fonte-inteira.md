---
id: A40.l41
type: lane
title: "Frescor cross-pool: posição stale de 2025-03 vale R$ 206k no bruto contra IRPF 31/12/2025 de R$ 2,4k"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l41-frescor-cross-pool-fonte-inteira
adrs:
  - "[[ADR-346]]"
  - "[[ADR-383]]"
depends_on: ["[[A40.l42]]"]
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l41 — `frescor-cross-pool-fonte-inteira`

> **Aberta em 2026-08-11.** Parecer `financial-planner` (hierarquia bifurcada
> por tipo de quantidade; granularidade nunca ativo-a-ativo) + `senior-cto`
> (grão = **fonte inteira**; faseamento observacional→flip) + `data-engineer`
> (contrato de datas; veto a flip no mesmo PR).

## Problema

O PL prefere "posições atuais" por **membro inteiro** com fallback IRPF
([patrimonio_calculator.py:290-347](../../../../pipeline/domain/services/patrimonio_calculator.py));
[[ADR-346]] compara recência só **dentro** do pool de reports. Nada confronta
pools: a posição E4 "CDB C6 Bank" de R$ 206.491,70 (`data_referencia`
2025-03-31) vence o IRPF 31/12/2025 (R$ 2.404,00) por default — overcount
provável de ~R$ 204k no bruto (~5,1%).

## Entregável

1. **ADR Proposto** (precedência temporal): ordem lexicográfica **data-alvo →
   proximidade sem look-ahead → qualidade no empate**; hierarquia de
   qualidade bifurcada (posição: IRPF > informe > report > derivado-de-extrato;
   caixa: extrato > informe > report); [[ADR-238]] D4 vale dentro da mesma
   data-alvo; `desconhecida` nunca vence (só quando única fonte); data
   inferida é carimbada (`data_referencia_origem: "inferida"`) e perde empate.
2. **Árbitro com grão de fonte inteira** — novo domain service; unidades:
   E4 `(instituição, membro, data_ref, total_fonte)` × IRPF
   `(instituição, membro, ano, valores_31_12[ano])` × informe
   `(cnpj_emissor, titular, ano_base, saldo_31_12)`. Nunca desmonta fonte
   (coerência intra-documento de [[ADR-346]] preservada por construção).
   Config por value object (`PrecedenciaConfig`); warnings tipados sem valor
   monetário persistido (padrão [[ADR-097]] D1 + LGPD).
3. **PR-a observacional (efeito zero):** árbitro roda, emite veredito em
   campo novo + warnings na superfície de degradação ([[A40.l22]]); PL não
   muda (teste afirma). Relatório por (instituição, membro, classe) da
   diferença veredito×atual no dogfood real.
4. **PR-b flip:** consumo do veredito; rebaseline isolado com manifesto.
   Gate de saída declarado no PR-a — a lane **não fecha** no observacional.


## Aberto — 2026-08-27 · dono: David Robert

Estado medido no fecho (skill `lane-closeout`). A lane **volta a `open`**: não
há branch remota (`git for-each-ref … | grep a40-l41` é vazio; uma das duas
locais, `a40-l41-corte-provisionado`, nem é desta lane — é o #1396 da
[[A40.l44]]), e `depends_on: [[A40.l42]]` está `shipped`.

**O PR-b não começou.** `git log origin/main -- pipeline/domain/services/fonte_precedencia_arbiter.py`
tem **1 linha** (`ec37d561`, #1419), 15 dias sem commit; a [[ADR-383]] segue
`Proposto`. O §PR-a acima declara que *"o observacional não fecha a lane"* — o
que segue valendo.

### O flip está inimplementável como escrito — o árbitro contradiz o produtor

Não é preferência de estilo: os dois eixos discordam sobre **para onde vai
posição sem dono**, e o flip consumiria o veredito do lado errado.

| lado | o que faz | onde |
| --- | --- | --- |
| árbitro (l41) | `membro = _slug(pos.get("membro")) or membro_default`, e o adapter passa `membro_default=self._identity.titular_key` | `fonte_precedencia_arbiter.py:159` · `e5_analyzer_adapter.py:873` |
| calculador (canônico) | *"Posição cujo membro o resolver não canonicalizou sai em `nao_atribuido`, **nunca** no balde do titular ([[ADR-394]] §D8)"* | docstring de `patrimonio_calculator.py:350-353` |
| papel da chave | *"o vazio é órfão, **nunca** titular"* → `PapelMembro.sem_dono` | `carteira_por_papel.py:22-25` |

E o produtor **emite mesmo** o vazio: `investments_consolidator.py:333-335`
devolve `"needs_review"` quando o resolver é ambíguo e `""` quando não resolve.
Hoje o efeito é zero (fase observacional), mas a célula `(instituição, titular)`
do veredito já mistura dinheiro órfão com dinheiro do titular. **Corrigir isto é
pré-requisito do PR-b, não parte dele.**

### `pool_atual_por_celula` é afirmado, não observado

`e5_analyzer_adapter.py:875` monta `atual = {(f.instituicao, f.membro):
"posicoes_atuais" for f in e4}` — valor **fixo**, com o comentário `:869-871`
declarando a simplificação. O calculador publica **três** valores no mesmo
payload, uma chave acima: `"posicoes_atuais+irpf"` e `"posicoes_atuais"`
(`patrimonio_calculator.py:383`) e `"irpf"` (`:404`). Enquanto o veredito for só
publicado, o custo é um relatório veredito×atual que compara contra uma
constante; no flip, é decisão tomada sobre premissa não observada.

### O golden não exercita o caso que abriu a lane

`backend/tests/snapshots/dogfood_view_model.json` traz:

```json
"frescor_fontes": {"celulas": [{"data_referencia": "2024-12-31",
  "instituicao": "bancoficticio", "membro": "alex", "pool_vencedor": "irpf"}],
  "contradicoes": []}
```

Uma célula, vinda só do pool IRPF, `contradicoes: []`. O caso real — C6 Bank
`2025-03-31` (R$ 206.491,70) contra IRPF 31/12/2025 (R$ 2.404,00) — **não tem
representação no golden**, então o ramo de contradição não é exercitado por
nenhum teste de snapshot. O gate de saída do PR-b pede *"relatório
veredito×atual por célula sobre o dogfood real"*: isso continua exigindo run
real, não golden.

### Os warnings não existem na forma que a própria ADR exige

A [[ADR-383]] `:90` diz, literalmente, **"warning só em log não existe"** e
manda o veredito para o `ReportDataQualityBanner`. Hoje a contradição sai em
`_logger.warning("mathoms.pipeline.e5.frescor_contradicao")`
(`e5_analyzer_adapter.py:883`) e em lugar nenhum da superfície de degradação da
[[A40.l22]]. O critério de aceite do PR-a pedia warnings emitidos com
`(instituição, membro, classe, data adotada, data descartada, motivo)` — o
campo `patrimonio.frescor_fontes` cumpre a metade publicada; a metade de
**aviso** não.

### O critério 4 (datas) nasce no schema errado

*"Datas: `data_referencia` sempre `YYYY-MM-DD` no produtor; gate rejeita
`YYYY-MM`/`YYYYMM`/int"* não tem onde morder: `config/schemas/e4_unified.schema.json`
tem **0** ocorrências de `data_referencia`, e as 2 do `e5_analysis.schema.json`
resolvem para `$defs.CaixaDetalhe` — superfície da [[A40.l39]], e o árbitro se
exclui de caixa por escrito (`fonte_precedencia_arbiter.py:26-28`). A
remediação começa no **`e4_unified.schema.json`**.

### Sem rota fora da lane

`patrimonio.frescor_fontes` não tem leitor e não aparece em registro nenhum.
Não confundir com o **DE-9** da `PIPELINE-REVIEWS-active`, que é
`cobertura_investimentos[].frescor` — outro campo, com casa própria na
[[A40.l77]] §Resíduo. E a [[A42]] devolveu esta lane explicitamente:
*"Nenhuma das 12 lanes daqui é dona desses arquivos. Ficam na A40."*
(`A42/_README.md:297-301`).

### Ordem obrigatória para o PR-b

1. `membro_default` → órfão (alinhar com [[ADR-394]] §D8) e `pool_atual_por_celula`
   observado — **pré-requisitos**, efeito ainda zero no PL.
2. Decisão de produto sobre `top_ativos` da fonte não adotada
   (`product-designer` + `financial-planner`) — já era gate de saída declarado.
3. Só então o flip, **dentro da janela de rebaseline compartilhada** do
   `_README` (§*Moeda do contador*: hoje `l91 → l89 → l90`). O flip muta E5 e
   zera o contador de 2 re-runs; entrar fora da janela custa uma janela inteira.

## Critério de aceite

- PR-a: `investimentos_titular/conjuge` e `bruto` idênticos (golden byte-a-byte
  nos campos monetários); warnings emitidos com
  `(instituição, membro, classe, data adotada, data descartada, motivo)`.
- PR-b: C6 renda fixa cai para a fonte mais fresca; delta do bruto medido e
  justificado linha a linha no manifesto.
- Decisão de produto registrada antes do PR-b: o que acontece com
  `top_ativos` da fonte não adotada (`product-designer` +
  `financial-planner`).
- Datas: `data_referencia` sempre `YYYY-MM-DD` no produtor; gate rejeita
  `YYYY-MM`/`YYYYMM`/int.

## PR-a (observacional) entregue — 2026-08-12 (PR #1419)

`fonte_precedencia_arbiter` compara fontes inteiras por célula
(instituição, membro) na ordem data-alvo → proximidade sem look-ahead →
qualidade; publica veredito + contradições em `patrimonio.frescor_fontes`
(sem valor monetário) e **não altera** nenhum número do PL — contrato com
teste próprio sobre o caso real do dogfood (C6 2025-03-31 × IRPF 31/12/2025).

**Gate de saída para o PR-b** (o observacional não fecha a lane): relatório
veredito×atual por célula sobre o dogfood real, decisão de produto sobre
`top_ativos` da fonte não adotada (`product-designer` + `financial-planner`),
e só então o flip do consumo com rebaseline isolado e manifesto.
