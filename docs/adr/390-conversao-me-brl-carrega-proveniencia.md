---
id: ADR-390
type: adr
title: "Conversão ME→BRL carrega taxa, data, fonte e status; ausência é explícita"
status: Decidido
phase: A40.l63
date: "2026-08-17"
amended_at: ["2026-08-24"]
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-135]]"
  - "[[ADR-238]]"
  - "[[ADR-245]]"
  - "[[ADR-382]]"
  - "[[ADR-387]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 390"
  - "conversao ME BRL"
  - "proveniencia de cambio"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/money
  - phase/a40-l63
---

# ADR-390 — Conversão ME→BRL carrega proveniência

> ⚠️ **Emendada em 2026-08-24** ([[A40.l63]] §Ataque) — D2, D4 e D5 descreviam
> garantias que o código não dava. Ver §Emenda no fim.
>
> **Decidido em 2026-08-17** no PR de implementação da [[A40.l63]].
> Origem: co-design `data-engineer` + `senior-cto`.
> Generaliza a [[ADR-387]] D3 para conversão cambial. **Não** decide qual
> taxa a coluna 31/12 usa ([[ADR-382]] / [[A40.l39]]). **Não** reabre
> [[ADR-090]] (`valor_brl` float no legado).

## Contexto

Três vias alimentam `CaixaDetalhe.valor_brl` e nenhuma registra a taxa:

1. E3 USD/EUR × câmbio corrente — sem `market_rate` cai em `5.80`/`6.35`
   silenciosos (`e5_analyzer_adapter._load_caixa_from_e3`).
2. Informe 31/12 — a entry já tem `taxa_ptax_aplicada`/`ptax_data`/`ptax_status`;
   `CaixaDetalhe` não as carrega.
3. Fallback [[ADR-245]] — o IRPF já veio em BRL, mas `moeda` vira USD/EUR e
   `saldo_original` recebe o BRL. O card imprime `US$ <valor em BRL>`.

A [[ADR-090]] cobre representação. A [[ADR-238]] D5 e a [[ADR-382]] cobrem
precedência de fontes, não o carimbo da conversão. Sem contrato, o leitor só
afirma falso ou fica calado.

## Decisão

**Valor BRL derivado de quantia em ME carrega taxa, data, fonte e status.
Ausência é status explícito, nunca `null` silencioso. As três vias passam
pelo mesmo value object.**

### D1 — O conversor não escolhe a taxa

Caller entrega a cotação (ou identidade, ou default nomeado). A função
`convert_me_brl` só multiplica e carimba. Sem `ConfigStore`, sem
`date.today()`, sem `@lru_cache`. `WisePtaxConverter` continua port de I/O
no backend; o VO vive em `pipeline/domain/services/conversao_me.py`.

### D2 — Fonte ≠ status

Objeto aninhado `conversao` em `CaixaDetalhe` (não irmãos soltos — `status`
nu colide). Writer novo **sempre** emite a chave. Ausência da chave = artefato
pré-390. Wire:

| Campo | Contrato |
| --- | --- |
| `taxa` | string decimal (paridade com `taxa_ptax_aplicada`; `NUMERIC(20,10)`) |
| `taxa_data` | `YYYY-MM-DD` da row usada (`observed_at`), nunca a data do lookup |
| `taxa_fonte` | `ptax_31_12` \| `market_rate_corrente` \| `default_hardcoded` \| `irpf_ja_em_brl` |
| `status` | `converted` \| `identity` \| `missing_rate` |

`nao_convertido` **não** entra em fonte. IRPF já-em-BRL: `fonte=irpf_ja_em_brl`,
`status=identity`, `moeda=BRL`, `taxa`/`taxa_data` nulos. Sem quantia original
em ME: `saldo_original` é o BRL fiscal; keyword "dólar" não autoriza gravar
BRL como USD nem câmbio reverso. Emenda a [[ADR-245]] §Limitações 3 no PR de
implementação — o fallback permanece.

### D3 — Default hardcoded é política do caller

`convert()` sem quote **não** inventa 5.80. Construtor nomeado
(`HardcodedFxDefault.usd_brl()` / `.eur_brl()`) dispara WARNING estruturado
(`par`, `n_linhas`; zero valor, zero PII). USD/EUR conservam o default
histórico (dogfood/offline). Par sem default (GBP, …) → `missing_rate`, sem
BRL inventado. A row seed `5.80` @ 2026-04-27 é `market_rate_corrente`
**stale**, não `default_hardcoded`.

### D4 — Funil por tipo; ratchet é backstop

Via nova não produz a coluna sem o VO. Pre-commit allowlist nominal
`(módulo, produtor) → WHY` contra multiplicação por `cambio*`/`ptax`/`quote.rate`
fora de `conversao_me.py`. Não confundir os dois.

### D5 — Schema aditivo

`$defs/CaixaDetalhe` no schema E5 com as chaves atuais + `conversao` opcional.
Fora de `required`. Sem bump de `report_version`. `valor_brl` continua
`number`/float neste ciclo.

## Consequências

- Card e `exposicao_cambial` leem o carimbo; o analyzer de exposição **inclui**
  `tipo==moeda_estrangeira_irpf` no mesmo PR da correção 245 — senão o ME
  só-IRPF some do card de exposição.
- Override de informe **copia** a conversão da entry; não remultiplica.
  `posicao_31_12.ptax_*` **não** herda `conversao` de extrato.
- Moeda fora de {BRL, USD, EUR} sem quote: linha não soma no total BRL.
- `analyze_finances` disco e `generate_narratives` BRL→USD ficam fora
  (allowlist `WHY=legacy-disk` / direção inversa).

## Alternativas rejeitadas

- **Fail-closed sem market_rate.** Quebra offline/dogfood. Vetada.
- **Copiar `ptax_*` para `CaixaDetalhe` sem VO.** Congela a assimetria
  informe-com-PTAX / extrato-sem-nada. Vetada.
- **Manter ADR-245 L3** (USD no label, BRL no valor). O card mente. Vetada.
- **Câmbio reverso IRPF→USD.** Inventa original. Vetada.

## Critério de aceite

Golden das três vias com `taxa_fonte` distinto. `default_hardcoded` com
`ConfigStore` sem `market_rate` + WARNING sem valor. Regressão 245:
`moeda` ≡ unidade de `saldo_original`. GBP sem row → `missing_rate`.
Mutação (multiplicação crua num produtor) derruba o gate. Seed 5.80 ≠
hardcoded (fonte diferente).

## Emenda 2026-08-24 — três garantias eram prosa, não contrato (A40.l63)

O ataque à lane mediu o entregue contra o decidido e achou três frases desta
ADR que o código não sustentava. Nada aqui reverte a decisão; tudo aperta a
implementação até ela dizer a verdade.

### E1 — D4 «via nova não produz a coluna sem o VO» era falsa

`CaixaDetalhe.conversao` nasceu `ConversaoMeBrl | None = None`, com o
comentário *"writer novo sempre preenche"*. Medido: produtor novo construía a
linha sem carimbo, `to_dict()` omitia a chave e o schema validava — payload
indistinguível de artefato pré-390, que é justamente o que D5 diz que a
ausência significa.

**A tensão entre D4 e D5 é real** e a ADR original as tratava como compatíveis.
Uma única ausência não codifica "legado" e "produtor esqueceu" ao mesmo tempo.
Resolve-se separando os lados:

- **escrita** — `conversao` é obrigatório e keyword-only. Esquecer levanta
  `TypeError` na construção. *Este* é o funil por tipo que D4 promete.
- **leitura** — `conversao` segue fora de `required` no schema (D5 intacta).
  Artefato pré-390 continua validando.

O ratchet de D4 continua backstop, e passou de **3/10** para **10/10** formas
plausíveis de reintrodução (bateria em `tests/dev/test_check_conversao_me_funnel.py`).
O miss decisivo era de método: `_RATE_ATTR` foi escrito a partir do nome do
*parâmetro* de `__init__` (`cambio_usd_brl`), não do atributo que a instância
carrega (`self._cambio_usd_brl`).

### E2 — D2: o enum de `taxa_fonte` não era enum

A tabela de D2 lista quatro valores fechados. Eles viviam em `Literal` Python
(hint, não checado em runtime), na união do TS escrito à mão e na `description`
do schema — **em nenhum `enum`**. `taxa_fonte="chute_do_agente"` validava.
Agora é `enum` de verdade, e o carimbo ganha restrição cruzada:

- `converted` ⇒ `taxa_fonte` presente;
- `missing_rate` ⇒ `taxa` e `taxa_fonte` nulos;
- `identity` fica livre **de propósito** — `identity_native_brl` traz `taxa=1`
  sem fonte, `identity_already_brl` traz fonte sem taxa, e os dois são honestos.

`converted` com `taxa` nula segue válido: cobre o informe cujo emissor converteu
e não divulgou a taxa.

### E3 — D2: `taxa_data` era inpreenchível na via corrente

D2 exige `taxa_data` = `observed_at` **da row usada, nunca a data do lookup**.
Medido: `taxa_data` era `null` em *toda* via de extrato; só `ptax_31_12` o
preenchia, e essa já trazia a data antes da ADR. O campo não adicionou
informação nenhuma.

A causa não era o produtor, era a fronteira: `ConfigStore.get_market_rate(pair,
observed_at) -> Decimal` devolve só a taxa e descarta a data da row que
resolveu (*"última cotação em data <= observed_at"*). Sem mudar o port, D2 é
inatingível.

**Decisão:** o port ganha `get_market_quote(pair, observed_at) -> PtaxQuote |
None`, aditivo — `get_market_rate` fica intacto para os demais chamadores.
`PtaxQuote` já existia (`ptax_types.py`) e já era o shape que
`WisePtaxConverter` produzia; o port apenas para de achatá-lo.

Permanecem nulos, e é o comportamento certo:

| via | `taxa_data` | por quê |
| --- | --- | --- |
| `taxas.json` legacy | `null` | o arquivo não versiona data — o dado não existe, não foi perdido |
| `default_hardcoded` | `null` | `5.80`/`6.35` são constante de política, não observação |

### E4 — o vocabulário de `fonte` não tinha termo para baseline IRPF

Fora do escopo original da ADR, mas na mesma linha: o fallback [[ADR-245]]
herdava `fonte="extrato"`, e `build_posicao_31_12` filtra por esse valor — a
posição de IRPF entrava no card 31/12 com id `extrato:irpf_…` e
`data_referencia` nula, afirmando ser posição de extrato bancário. Ver §Emenda
da [[ADR-238]]. Se e como o snapshot 31/12 do IRPF *deve* aparecer naquele card
é pergunta da [[A40.l39]].
