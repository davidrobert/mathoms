---
id: ADR-406
type: adr
title: "Gate por item da catch-all: migração entre baldes preserva Σ e nenhum check de conservação a alcança"
status: Decidido
phase: r7/DE-2
date: "2026-08-21"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-193]]"
  - "[[ADR-209]]"
  - "[[ADR-272]]"
  - "[[ADR-343]]"
  - "[[ADR-393]]"
  - "[[ADR-394]]"
  - "[[ADR-400]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 406"
  - "gate por item da catch-all"
  - "DE-2"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
---

# ADR-406 — Gate por item da catch-all de classes de ativo

**Status:** Decidido (r7 · Onda B, passo 2) • **Data:** 2026-08-21 • **Relaciona**
[[ADR-400]] (autoridade da classe — o degrau anterior desta onda), [[ADR-272]]
(`ReviewReason` + cap de cardinalidade), [[ADR-394]] (forma do produtor de razão
no E5), [[ADR-343]] (compare de review), [[ADR-090]] (dinheiro nunca é float).

## Contexto

O §r7 (RV7-04 + DE-2) registra que reclassificação entre baldes **preserva Σ por
construção**: a perda de um balde é exatamente o ganho do outro, o total da
carteira não muda, e o resíduo mede 0,0000%. Os 16 checks de conservação passam
— não por acaso, mas **por desenho**: eles medem soma, e soma é o invariante que
a migração respeita.

O único sensor da catch-all era de **nível**: `OUTROS_EXCESSIVO_THRESHOLD_PCT =
5,0`. A participação medida no corpus do r7 é **0,84%** do total investido —
~6× abaixo do limiar. E ele produzia um `warning` de string, nunca uma
`review_reason`: nada retinha o run, nada ia para `review_reasons`.

### Medição no corpus real (run `33514dc4`, classificador pós-[[ADR-400]])

28 posições com valor sobre 55 consolidadas.

| fato | medida |
|---|---|
| autoridades | `keyword` 25 · `sem_match` 3 · `sem_haystack` **0** |
| Σ `sem_match` | **1,2847%** da carteira financeira (bate com `Outros.pct_carteira_financeira` = 1,28) |
| maior item `sem_match` | **1,2803%** |
| posições com valor **sem instituição** | **3**, a maior com **2,8104%** |
| interseção `sem_match` × `sem instituição` | **ZERO** |
| instituições distintas do titular | 18 (r5, r6) → **16** (r7), com posições constantes |
| rótulos crus × pós-`.capitalize()` | 20 → 19 |

## Decisão

### D1 — O gate mede o ITEM, não o nível

- **`sem_haystack` vira razão sempre.** Item sem `tipo` e sem `descricao` é
  violação de contrato do **produtor**, não incerteza de taxonomia — e o produtor
  não fica menos quebrado porque o item é pequeno. Medido 0/28: é raro por
  natureza, então não há risco de afogar o sinal.
- **`sem_match`/`sem_mapa` escalam por peso, por item:** `≥ 0,5%` da carteira
  financeira vira razão nomeada.
- **Braço agregado:** Σ não-classificado `> 1%` vira uma razão. Ele existe para a
  morte por mil cortes, que o braço por item não vê; e ocupa a faixa 1–2%, que
  hoje fica **abaixo** do primeiro degrau da supressão graduada
  (`suprimir_por_incerteza`, 2%/10%) e não produz sinal em lugar nenhum.

Base = **carteira financeira** (`total − imóveis físicos`), a mesma de
`pct_carteira_financeira` e de `nao_classificado_pct` (A37.l9). Imóvel é
classificado pela origem e nunca depende de keyword; incluí-lo no denominador
diluiria a incerteza.

### D2 — A cobertura de identidade é o braço mais valioso, e não estava previsto

O DE-2 do §r7 pedia "gate por item + cobertura de identidade". A medição inverteu
a prioridade dos dois: **o braço de identidade é maior que o de classe e é
disjunto dele**. O item que mais some (2,8104%) classifica num balde **nomeado**
— logo `nao_classificado_pct` é cego a ele — e não tem instituição, logo some de
`instituicoes_por_membro`. A interseção com `sem_match` mede **zero**.

Consequência: o DE-2 como escrito teria pego o item **menor** (1,2803%) e deixado
o **maior** passar. Posição com valor e sem identidade de instituição `≥ 0,5%`
vira `domain.instituicao_ausente`.

`instituicoes_por_membro` passa a publicar `n_posicoes` — sem o denominador, a
queda 18→16 é indistinguível entre corpus menor e identidade perdida.

### D3 — Três codes, não um

| code | dispara | medido no r7 |
|---|---|---|
| `domain.ativo_sem_haystack` | sempre | 0 |
| `domain.ativo_nao_classificado` | item ≥0,5% **ou** Σ >1% | 2 (1 item + 1 agregada) |
| `domain.instituicao_ausente` | posição com valor ≥0,5% sem instituição | 1 |

Três e não um porque **a remediação e o dono diferem**: o primeiro é o produtor a
montante, o segundo é a taxonomia, o terceiro é a extração de identidade.
Colapsar num código só devolveria o agregado que o DE-2 acusa.

### D4 — Retentivo por default, com kill-switch nomeado

O gate **retém o run** (`validation.valid = False` → `needs_review` em
`analyze_finances`). Razão que não retém é **descartada no chão**:
`record_review_reasons` só roda quando `validation.valid` é falso, então um
emissor advisory seria inerte — o mesmo falso-verde que esta onda existe para
matar. Construir o canal advisory é o RV7-03/DE-3, de outro dono.

**Como desligar:**

```bash
MATHOMS_E5_CLASSIFICACAO_GATE=0
```

`0` desliga a **retenção**; os campos do artefato (`nao_classificado_itens`,
`n_posicoes`, `posicoes_sem_identidade`) continuam publicados. Mesma forma de
`cobertura_enforcement_ligado()` ([[ADR-394]] §Emenda (b) D7) — convergência com
o produtor mais recente, não uma quinta política de retenção.

**Consequência operacional aceita:** com 0,5%/1% o gate **dispara no corpus
atual** e o próximo run de dogfood pausa em `analyze_finances` até os dois itens
serem corrigidos a montante. É recuperável por `resume_pipeline_run` (o próprio
r7 fez isso). Os dois itens são **defeito**, não estado legítimo.

Rejeitadas: subir o piso para ~1,5% (derivaria o critério do contador —
calibrar o instrumento para não ver o caso que ele foi construído para ver) e
shipar `OFF` por default (entrega o mecanismo sem o sinal).

### D5 — Locator é o `investment_id`, e a razão carrega percentual, não BRL

`investment_id` (sha256 de `tipo|instituicao|descricao`, [:16]) já é carimbado
pelo baseline: PII-free, grepável, e identidade canônica do ativo. Nomear a
**string de instituição** na razão recriaria em superfície durável o acoplamento
a rótulo volátil que a [[ADR-400]] acabou de cortar da entrada do classificador.

A razão carrega o **peso na carteira**, não o valor: é o número que decide o
limiar, e `redact_pii` mascararia o monetário. Com uma armadilha que custou um
ciclo de teste: **o percentual vai com separador decimal ponto**, porque
`_MONEY_RE` casa `\d+,\d{2}` e transformava `"1,30%"` em `"R$ ***%"` — apagando
calado o único número acionável.

### D6 — Cap de cardinalidade: 5 por code

[[ADR-272]] §Cap fixa 50 por `(run, code)`. Aqui o cap é **5**, com o excedente
agregado em `occurrence_count` na última: estas razões também viram string em
`validation.errors`, e acima de ~5 itens materiais a lista deixa de informar —
a linha agregada já é o recado.

**Cardinalidade medida no corpus real: 3 razões/run** (1 `sem_match` material +
1 agregada + 1 `instituicao_ausente`). Declarado porque foi exatamente não
declarar isto que custou o retrabalho pós-merge da [[A40.l66]], onde ligar um
emissor levou o run a 84 razões.

### D7 — Par compensatório no compare cross-run

`review_snapshot` ganha `investimentos_mix` (pct por classe em centésimos +
pares `[n_posicoes, n_instituicoes]` — o nome do membro é PII e não entra);
`SCHEMA_VERSION` 1 → 2. Duas pernas **HARD** que `corpus_grew` **não** suprime:

1. exatamente duas classes movendo ≥0,10pp em módulo igual e sinal oposto;
2. instituições distintas caindo com posições não caindo.

Em espaço de percentual os deltas somam zero por normalização — então o
fechamento do par é quase de graça e quem discrimina é a **contagem exata de
duas** classes movidas. Corpus maior move várias classes de uma vez.

## Consequências

**Positivas:** a classe de erro "migração silenciosa entre baldes" ganha detector
run-local (sem baseline) e cross-run; a faixa 1–2% deixa de ser cega; o item
órfão de identidade sai da invisibilidade.

**Negativas / trade-offs aceitos:** o próximo run de dogfood pausa; a razão não
carrega valor em BRL (por decisão) nem rótulo legível de instituição, então
diagnosticar exige cruzar o `investment_id` com o baseline; o cap de 5 perde
detalhe fino em run patológico.

## Deferimentos datados

**D1 — `.capitalize()` em `_collect_instituicoes` (2026-08-21, dono:
`data-engineer`).** A normalização é **com perda**: medido no corpus do r7, 20
rótulos crus colapsam para 19 pós-`.capitalize()`. É a mesma família do DE-1 —
normalização com perda decidindo o que o relatório mostra — e uma segunda via da
queda 18→16, no **mesmo call-site**. Não corrigido aqui porque a forma canônica
de instituição é propriedade do `institution_catalog` ([[ADR-137]]/[[ADR-384]]) e
resolvê-la no analyzer repetiria o erro que a [[ADR-400]] acabou de cortar.
**Retomada:** junto do degrau 1 da [[ADR-400]] (catálogo de instrumentos).

**D2 — `_split_by_conjuge` não propaga `tipo` para investimento (2026-08-21,
dono: `data-engineer`).** O entry que chega ao classificador tem só `descricao`,
`valor_31_12_ano_base`, `instituicao` e (agora) `investment_id` —
`e5_member_resolver.py`. O haystack é a descrição sozinha. **Medido: não muda
resultado** — rodados os dois cenários (`tipo=''` real vs. hipotético propagado)
no corpus do r7, as autoridades saem idênticas (`keyword` 25 · `sem_match` 3).
É **dívida, não bug**; registrado para o próximo agente não caçar fantasma.

## Critério de aceite

1. Replay do cenário do r7 — posição migrando de classe nomeada para catch-all
   com total inalterado — dispara o gate. ✅ (`test_de2_gate_por_item.py`)
2. Os três limiares provados por **mutação executada**: piso do item
   0,5→10,0 (5 failed/17 passed); denominador `total_financeiro`→`total`
   (3 failed/19 passed); `sem_haystack` passando a respeitar o piso
   (1 failed/21 passed). ✅
3. Cardinalidade medida no corpus real e declarada: **3 razões/run**. ✅
4. Codes no enum Python **e** em `review_reason.schema.json` (senão
   `_drop_unknown_codes` os descarta calado). ✅
5. Campos novos em `e5_analysis.schema.json` — `instituicoes_por_membro.items`
   tem `additionalProperties: false` e quebraria só no CI em strict. ✅
