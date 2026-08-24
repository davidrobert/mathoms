---
id: A40.l67
type: lane
title: "Guarda de publicação no E5: nenhum balde de patrimônio publica negativo, e o schema deixa de aceitá-lo"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1534
ship_date: "2026-08-18"
priority: P0
branch_slug: a40-l67-guarda-de-publicacao-e5
owner: financial-planner
adrs:
  - "[[ADR-145]]"
  - "[[ADR-212]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
depends_on:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l67 — `a40-l67-guarda-de-publicacao-e5`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (itens 1d,
> 1e). **Destravada em 2026-08-18** — a [[A40.l66]] shipou (#1522) e o roteamento
> por fato existe. Era `blocked` por ela: a guarda tem de rodar sobre roteamento já
> corrigido, senão mede o defeito da lane anterior e a taxa de disparo sai
> inflada — e o flip do schema para strict é, por desenho, o **último** passo da
> Onda 1.

## Problema

O E5 publicou um balde de **ativo negativo** e nada o segurou. A assimetria está
medida em `pipeline/domain/services/patrimonio_calculator.py`: a linha 194
clampa (`investivel_efetivo = max(0.0, …)`), a 179 não — o
`split_imoveis_geradores_vs_nao_geradores` e os baldes que alimentam
`composicao` passam o negativo adiante. No r6 isso publicou "Imóveis de Renda"
com valor rebaixado, as dívidas caíram 89%, e o score **subiu**.

O contrato tampouco segura: medido nesta sessão, `validate_dict` do payload r6
contra `baseline_patrimonial` retorna `True` — não há `minimum` nos
`valores_31_12` dos baldes de ativo. Vale notar que o retorno de `validate_dict`
é **dependente de modo** (warn devolve `True` mesmo com payload inválido), então
o golden da Onda 0 mede `iter_errors` direto.

## Escopo

**1d — guarda de sinal nos 7 baldes [[ADR-145]], com rota de reclassificação
ANTES da guarda.** Negativo legítimo (cheque especial, conta margem)
**reclassifica** determinístico para dívida de curto prazo e **publica**
normalmente; só o negativo que sobrevive à reclassificação vira warning tipado +
`needs_review`. Sem essa rota, a guarda transformaria saldo devedor legítimo em
ruído recorrente.

Regra unificadora (vai na ADR-A): **prescrição exige cobertura; descrição admite
ressalva.** Cobertura incompleta ⇒ `next_aporte_classe=None` +
`desvio_max_pct=None` + `motivo_supressao` (os três campos já são `Optional`),
**sem** suprimir o resto do relatório.

**1e — simetrização do contrato.** `patternProperties` `^(31_12_)?\d{4}$` com
`minimum: 0` nos 3 baldes de ativo de `baseline_patrimonial.schema.json`.
**Sem** fechar `additionalProperties` — os resolvers leem 3 formas de chave
vivas (§Anti-decisões do plano). O flip de `mode_overrides` para strict dos 2
schemas de baseline é o **último passo da Onda 1**, com gate medido: drift = 0
por ≥7 dias de dogfood, e o número citado no PR do flip.

## Enforcement

WARN-first ([[ADR-357]]/[[ADR-358]]). Budget de 1d medido sobre r5+r6 e
declarado antes do flip; kill-switch por env var. Para 1e o kill-switch é
`mode_overrides`. Estado terminal de unidade não processada é `degraded` +
`needs_review` — nunca run vermelho.

## Coordenação declarada

- **[[A42.l6]]** cede o eixo dos 2 schemas de baseline e mantém
  retenção/`SCHEMA_BY_STAGE`; **[[A40.l58]]** mantém `mode_overrides` e o
  kill-switch como infra. Disposição tripartite escrita na §Roteamento do plano
  (RV6-06) — esta lane **não** abre PR nas superfícies delas.
- O flip para strict compartilha a **fila serializada de rebaselines e
  migrations** do plano (§Onda 0 · 0d): uma janela por onda, dono declarado.

## Critério de aceite

- `tests/test_e15c_golden_execution.py::test_e15c_r6_payload_reprova_no_schema`
  desmarcado e verde.
- Balde negativo legítimo (cheque especial) **publica** após reclassificação —
  fixture própria, não coberta pelo golden r6.
- Balde negativo sobrevivente produz warning tipado + `needs_review` e **não**
  aborta o run (teste do kill-switch inclusive).
- Cobertura incompleta suprime só a prescrição (`next_aporte_classe`,
  `desvio_max_pct`) e emite `motivo_supressao`; o resto do relatório publica.
- ~~Drift do schema = 0 por ≥7 dias de dogfood, número citado no PR do flip.~~
  **Re-homeado para a [[A40.l58]] em 2026-08-18** — ver §Deferimento abaixo.
- ADR-A (aberta na [[A40.l66]]) emendada com a regra "prescrição exige
  cobertura; descrição admite ressalva", ou a lane cita a seção já escrita.

## Fora de escopo

- Roteamento por fato e conservação por eixo → [[A40.l66]].
- Copy/estado de banner e o 3º estado do export → lanes de render no
  [[PLAN-report-trust]] (7a/7e), fora desta lane.
- Subir `schema_validation.mode` **global** — anti-decisão explícita do plano;
  só per-schema com janela medida.

## 1e entregue — 2026-08-18 (#1529 · `144911a6`)

`patternProperties` `^(31_12_)?\d{4}$` com `minimum: 0` nos 3 baldes de ativo;
`additionalProperties` segue **aberto**. `test_e15c_r6_payload_reprova_no_schema`
desmarcado e verde, provado por mutação nas duas direções.

A assimetria era literal: `dividas[].saldo_31_12` **já** declarava `minimum: 0`
e os três `valores_31_12` de ativo eram `{"type": "object"}`. O passivo era
guardado; o ativo aceitava qualquer coisa.

**Flip para strict NÃO entra** — o critério da lane é drift = 0 por **≥7 dias**
de dogfood, temporal por construção. Retomada: medir a janela e citar o número
no PR do flip, coordenado com [[A40.l58]] (dona de `mode_overrides`).

## 1d — desenho corrigido antes de codar (2026-08-18)

**Correção factual da própria lane:** ela afirma que `next_aporte_classe`,
`desvio_max_pct` e `motivo_supressao` "já são `Optional`". Os dois primeiros são
(`alocacao_alvo_deviation.py:122-123`); **`motivo_supressao` não existe no
repo** — é campo novo. O plano repete a afirmação em §Onda 1 1d. Mesma correção
já feita ao escrever a [[A40.l69]].

**O seam da reclassificação não é a `composicao`.** Medido:
`_compute_bruto` e `_build_composicao` (`patrimonio_calculator.py:165` e `:196`)
são **duas somas independentes sobre os mesmos seis componentes**. Uma guarda que
pós-processe as linhas da `composicao` — zerando o balde negativo e somando à
dívida — dessincroniza `composicao` de `bruto`, e o `pct` por largest-remainder
passa a distribuir sobre um total que não existe.

A reclassificação tem de acontecer **no componente**, a montante das duas somas:
`caixa_total_brl` (cheque especial) e os `investimentos_*` (conta margem) são
corrigidos antes de alimentar `_compute_bruto`/`_build_composicao`, e o montante
vai para `total_dividas`. Assim `composicao ≡ bruto` se preserva e
`patrimonio_liquido` **não muda** — o que muda é a honestidade da apresentação.

Consequência de fila: o 1d tem efeito monetário no publicado (baldes e dívidas
mudam de valor mesmo com líquido constante), logo **precisa da janela J2**, com
`dev/golden_diff.py --manifest` e sinal ↑/↓/= declarado.

Uma primeira versão do serviço foi escrita sobre a `composicao` e **descartada
sem commit** ao medir isto — guarda meio-certa que dessincroniza dois agregados
é pior que guarda nenhuma, porque o defeito passa a ser invisível no lugar onde
o leitor confere.

## 1d entregue — 2026-08-18 (#1534 · `aa53d5bf`)

`patrimonio_sign_guard.py` aplica a guarda **no componente**, a montante de
`_compute_bruto` e `_build_composicao`, como o §desenho corrigido acima exigia.
Caixa saiu para `patrimonio_caixa.py` para o saldo corrente chegar cru à guarda
(e o calculator ficar sob o teto de 500 linhas). A [[ADR-394]] §Emenda 2026-08-18
(#1531) carrega a regra "prescrição exige cobertura; descrição admite ressalva"
e as decisões D5/D6.

**Correção da própria lane, confirmada:** `motivo_supressao` **não existia** —
nasceu aqui, em `AlocacaoDeviationResult` e no `AlocacaoDerived` do schema (que
tem `additionalProperties: false`, então declarar não era opcional).

### A medição que mudou o escopo

Sobre `report_data.json` dos **6 runs completos** do dogfood:

| nível | disparo | efeito no desenho |
|---|---|---|
| 6 componentes < 0 | **0/36** | a guarda no componente é rede, não detector |
| split derivado < 0 | **1/12** — só r6, `imoveis_nao_geradores` = −125.381,88 | **entrou no escopo** |
| linhas de `caixa_detalhes` < 0 | **6/6 runs** (−95,62) | a guarda mede **agregado**, não linha |

O `imoveis_geradores`/`imoveis_nao_geradores` é o split de cat_2
([[ADR-142]]/[[ADR-215]] §6), **não** um dos 7 baldes [[ADR-145]] que o item 1d
nomeia. Uma guarda literal ao texto teria passado **verde sobre o r6**: lá o
agregado `imoveis_investimento` seguia positivo (437.324,36) com o negativo
escondido dentro do split. Entrou em `BALDES_FISICOS` e é detectado **sem
mutação** — mutá-lo quebraria a invariante 4a (`imoveis_investimento ≡
geradores + não-geradores ≡ imoveis_fisicos_brl`) que a Onda 0 instalou.

A linha de −95,62 é o argumento contra medir por linha: ela se anula dentro de
um caixa de +257.683,53, em **todo** run — a guarda viraria ruído recorrente,
que é o modo de falha que a §Escopo cita ao exigir a rota de reclassificação.

### Efeito colateral corrigido de passagem

`_compute_caixa` aplicava `max(0.0, caixa)` no ramo de posições atuais: caixa
negativo **evaporava**, e o bruto (logo o líquido) saía superestimado pelo mesmo
montante. Agora o montante vai para `total_dividas` e o líquido cai o que devia
cair. Disparo medido: **0** — o agregado de caixa nunca foi negativo nos 6 runs.
O modo `off` reaplica esse clamp: kill-switch que não restaura o comportamento
anterior não é kill-switch.

### Janela J2 — aberta e fechada sem consumir rebaseline

`dev/golden_diff.py` sobre o payload E5 do golden, `aa53d5bf~1` × `aa53d5bf`:
dois campos `new` (`patrimonio.guarda_de_sinal`,
`goals.alocacao_alvo.derived.motivo_supressao`) e **zero `value_delta`**. Sinal
declarado: **=**. O rebaseline do view-model é igualmente aditivo (8 linhas, 1
campo `new`). Nenhum valor monetário publicado se moveu, logo a janela segue
disponível para o flip strict do 1e.

### Kill-switch `MATHOMS_E5_SIGN_GUARD`

| valor | comportamento |
|---|---|
| ausente / `enforce` | reclassifica, declara, sobrevivente pausa em `needs_review` (artefato já persistido — pausa, não aborto) |
| `warn` | reclassifica e declara no artefato, sem pausar |
| `off` | status quo ante literal, clamp `max(0, caixa)` incluído |

### Follow-up re-roteado — 2026-08-21

Esta lane hospedava um follow-up com **dono `senior-cto`** — papel de revisor,
não rota de trabalho. Lane `shipped` não guarda pendência sem destino vivo, e o
`check_closure.py` o pegou como `CLOSE-BLOCK-01`. O item foi **movido** para o
§Deferimentos datados do [[PLAN-deterministic-authority]], que é onde o plano
guarda trabalho com condição de retomada declarada.

**O item, em uma linha:** `enrich_alocacao_with_deviation` recebe o patrimônio
como kwarg com default `None`; call-site que o omitir publica a prescrição sobre
cobertura possivelmente incompleta e passa verde.

**O ponteiro também envelheceu em 3 dias.** A função saiu de
`e5_serialization.py:436` para
[`alocacao_derived_enricher.py:15-21`](../../../../pipeline/domain/services/alocacao_derived_enricher.py).
Re-medido em `5f73b116`: o default `patrimonio: dict[str, Any] | None = None`
**persiste**, e 3 call-sites de teste seguem omitindo o kwarg
(`backend/tests/test_alocacao_bundle_serialization_v2.py:81,91,94`). O achado
continua válido; só a coordenada estava errada.

### Deferimento datado (2026-08-18) · dono: `data-engineer` — re-homeado em 2026-08-24

> ⚠️ **A rota mudou em 2026-08-24 (a l58 shipou).** O texto abaixo é preservado como
> escrito; o que envelheceu é o destino, não o conteúdo. Hoje o item se parte em dois:
>
> - **O flip em si** não é entregável de lane nenhuma — é procedimento do
>   [runbook §3.1](../../../reference/runbooks/schema_validation_strict_flip.md),
>   gated pelo §1.3, que desde a [[ADR-409]] §B é um comando com exit code
>   (`dev/measure_schema_drift.py --gate`). Qualquer sessão executa quando houver runs.
> - **`baseline_patrimonial` não pode ser flipado** e o bloqueio não é temporal: o
>   contrato declara **5 de 13** chaves do payload real. Re-derivá-lo do produtor E1.5c
>   é §Deferimento datado com dono: `data-engineer` na [[A40.l58]] §Fecho.
> - `e15_baseline_extract`, o irmão, mede **0/66** e está elegível hoje ([[ADR-409]] §D).

**O flip de `mode_overrides` para strict sai desta lane.** Ele estava na
§Critério de aceite acima, e era um critério que **esta lane não podia
executar**: o §Roteamento RV6-06 do plano já atribui `mode_overrides` e o
kill-switch à [[A40.l58]], e a §Coordenação declarada desta lane diz literalmente
que ela "**não** abre PR nas superfícies delas". Um critério inexequível não
adia a entrega — ele a esconde, e neste caso travava a [[A40.l69]], o último P0
do MVP, por uma dependência que o trabalho real já satisfez.

Escopo do que foi re-homeado: flip de `schema_validation.mode` para `strict` nos
**2 schemas de baseline** (`baseline_patrimonial`, `e15_baseline_extract`), via
`mode_overrides` — nunca global (§Anti-decisões). Condição de retomada:
**drift = 0 por ≥7 dias de dogfood, com o número citado no PR do flip** —
critério **temporal** por construção, que nenhuma sessão fecha por esforço.
A simetrização do contrato que o flip torna executável já shipou no #1529.

> ⚠️ **Marcador de 2026-08-24 — a condição de retomada é inalcançável para 1 dos 2
> schemas** (medido no §Ataque da [[A40.l58]], PR #1650). `baseline_patrimonial`
> mede **100% de drift em 91/91 artefatos** do corpus: exige
> `required: [pipeline_stage, data_processamento]` e o writer
> (`scripts/consolidate_baseline.py:1003`) não estampa nenhum dos dois — quem
> estampa é o `BaselineNormalizer`, na **leitura**, dentro do E4. "Drift = 0 por
> ≥7 dias" não é critério temporal aqui: é **estrutural**, e só fecha depois de um
> fix de contrato ou de produtor. `e15_baseline_extract` mede **0/66** e segue
> elegível. O deferimento e o dono não mudam; o que muda é que o flip dos 2
> schemas **não é um único passo**.

### Segue aberto

- **Copy/banner do estado de ressalva** no relatório: 7a/7e no
  [[PLAN-report-trust]], fora desta lane. O artefato já carrega
  `guarda_de_sinal` e `motivo_supressao` para o render consumir.
