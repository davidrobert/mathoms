---
id: ADR-390
type: adr
title: "Conversão ME→BRL carrega taxa, data, fonte e status; ausência é explícita"
status: Decidido
phase: A40.l63
date: "2026-08-17"
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
