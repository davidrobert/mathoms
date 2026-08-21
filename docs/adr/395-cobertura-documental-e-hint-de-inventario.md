---
id: ADR-395
type: adr
title: "Cobertura documental é hint de inventário: nunca soma, nunca zera, retém o gap"
status: Decidido
phase: A40.l73
date: "2026-08-19"
relates_to:
  - "[[ADR-192]]"
  - "[[ADR-240]]"
  - "[[ADR-375]]"
  - "[[ADR-387]]"
  - "[[ADR-394]]"
supersedes: []
superseded_by: []
aliases: ["ADR 395", "cobertura documental hint", "inventário não confirmado"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/pipeline
  - area/report
  - area/financial-planning
  - phase/a40-l73
---

# ADR-395 — Cobertura documental é hint de inventário

## Contexto

Duas fontes descrevem a mesma realidade de seguro e nunca se falam:

1. **Cadastro** — aggregate `Protection` ([[ADR-192]]), declaração humana
   atribuível. É o que o `protection_bundle` enxerga.
2. **Documento** — bloco `protecao_patrimonial` ([[ADR-240]]), produzido por
   `compute_protecao_via_store` a partir de `extract_comprovantes_bens`.

O produtor do bundle lê só (1). Com o cadastro vazio ele publica
`actual = 0`, gap igual à necessidade integral e prescrição de prioridade
alta; a S9 imprime *"sem riscos cadastrados"* enquanto a seção vizinha lista
apólices vigentes e `pontos_urgentes` as cita (PD-4 / RV6-20, run r7). O
[#1476](https://github.com/davidrobert/mathoms/pull/1476) tentou consertar no
render e foi no-op: os quatro sinais do predicado saem do mesmo bundle.

A [[ADR-240]] §D12 já decidiu que as duas fontes **não compartilham chave de
identidade** — o cadastro não guarda `apolice_numero`. Somar arrisca
dupla-contagem; ignorar afirma zero onde não se mediu.

## Decisão

### D1 — Um produtor para o número; extração é hint

Para qualquer **valor** de cobertura o produtor é o cadastro
([[ADR-375]] §D1, um produtor por publicação). O documento é **hint**:
[[ADR-394]] fixa que o fato determinístico é autoridade e o hint nunca o
sobrescreve. **As duas fontes nunca são somadas.**

### D2 — Documento vigente sem cadastro ativo ⇒ inventário não confirmado

Apólice documental vigente numa categoria em que o cadastro **não** tem
apólice ativa é prova positiva de que o inventário do cadastro está
incompleto. Nessa categoria:

- `calculation_status[categoria] = missing_data`, motivo *"cobertura
  identificada em documento, não confirmada"*;
- **sem entry** em `gap_analysis`;
- **sem** `recommendations[categoria]`, sem `RiskInferred` derivado do gap,
  sem prioridade "alta".

Isto é a aplicação literal da [[ADR-387]] §D4 (*"ausência de apólice só vale
zero com inventário confirmado para pessoa/categoria/data"*) e §D3
(*ausência, ambiguidade, conflito ou inventário parcial ⇒ `missing_data`*).

Categoria com cadastro ativo **continua computando**: um segundo documento só
poderia aumentar a cobertura real, logo o gap calculado sobre o cadastro
**superestima** a necessidade — o lado seguro de D5.

### D3 — Vocabulário de 3+1 estados (o da Onda 3 §3a, reusado)

| Estado | O que o relatório comunica |
|---|---|
| `apurado` | gap computa e prescreve |
| `nao_apurado` **parcial** | nomeia o que foi identificado em documento; declara que o capital **não foi confirmado**; necessidade estimada sai como **descrição** ([[ADR-387]] §D6, "a estimativa indica"); sem gap, sem prescrição; pede confirmação |
| `nao_apurado` **total** | ausência declarada nomeando o insumo faltante — **nunca** "sem riscos cadastrados" |
| `zero_apurado` | cliente declarou não ter cobertura: único caminho para gap = necessidade integral |

Ressalva explícita é obrigatória nos dois `nao_apurado`: omitir ≠ afirmar zero
([[ADR-240]] §D10; [[ADR-375]] §D4, "não se aplica com motivo, nunca zero").

### D4 — Retenção é ausência de entry, jamais `actual` coagido a zero

`_gap_analysis_to_response` coagia `actual` nulo para `Decimal("0.00")`. O DTO
passa a aceitar `actual_brl` nulo e a retenção é expressa por **ausência de
entry + `calculation_status`** — nunca por entry com zero fabricado.

### D5 — Assimetria de erro: fonte não confirmada nunca reduz gap

Descoberto no evento é ruína irreversível; prêmio duplicado é fluxo mensal
corrigível que ainda passa por corretor humano. Divergência que **aumenta** o
gap é sinal; divergência que o **reduz** não se aplica sem confirmação.

### D6 — Proveniência do hint

O hint é derivado do **mesmo artefato E5 pinado** que o envelope já referencia
por `analysis_artifact_id` ([[ADR-387]] §D2/§D7), então o snapshot continua
reprodutível a partir do run. Ele **não** entra em `inputs_digest_sha256`: o
digest sela a projeção **relacional** (`ProtectionComputationInputsV1`), e o
hint não é fonte relacional. O endpoint live `/protection-bundle` não tem E5
por construção e segue sem hint — não alimenta Report histórico.

### D7 — `gap_qualitativo` reconciliado com `irpf_kpis.dependentes`

`_flag_vida` decide o gatilho de vida sobre `family_members` de config. Sem
membros, ou sem data de nascimento, ele devolve `flag: False` com rationale
`sem family_members` / `sem gatilho` — silêncio que lê como "sem risco".
Havendo dependente declarado no IRPF (`irpf_kpis.dependentes.count > 0`), a
ausência de gatilho é **`nao_apurado`**, não ausência de risco: a entrada
ganha `status: "nao_apurado"` e rationale `dependentes_irpf_sem_cadastro`, e
`pontos_urgentes` classifica o item como `pendente_de_dado` (retenção), não
como conselho inexistente. `flag` permanece booleano — a semântica de
`flag: True` não muda, e nenhum consumidor existente quebra.

## Alternativas rejeitadas

- **(B) Mapear documento → categoria de cadastro e reusar o número.** As duas
  fontes não têm chave de identidade comum ([[ADR-240]] §D12); o documento não
  tem `invalidez` (só `acidentes`, equivalência recusada em §D11) e nada de
  sucessório; e `CoberturaVida.segurado_family_member_id` é opcional — não há
  prova de que o capital é do segurado em risco.
- **(C) Predicado de promoção automática documento → cadastro.** Qualquer
  predicado forte o bastante **é** o predicado da confirmação. Satisfeito ele,
  o caminho barato é promover a apólice ao aggregate `Protection` com
  proveniência ("extraído de X, confirmado em DD/MM"), não abrir segunda via de
  entrada no mesmo número ([[ADR-375]] §D1).

## Deferido — 2026-08-19

- **Conflito de vigência** (documental vencida enquanto o cadastro diz
  "Ativa") ⇒ `missing_data` + `review_reason` com as duas leituras datadas.
  Fora daqui porque exige tipo de cobertura por apólice **vencida** no payload,
  que o `apolice_resumo` não carrega. Dono: `data-engineer` +
  `financial-planner`. Retomada: junto da distinção prestamista / vida em grupo.
- **Prestamista e vida em grupo do empregador.** `_categorias_de_documento`
  fecha `flag_vida` com qualquer `tipo == "vida"` vigente, e
  `pipeline/llm/schemas/apolice.py` não distingue apólice cujo beneficiário é o
  credor do financiamento nem cobertura que morre com o vínculo. Enquanto
  aberto, o estado parcial **nomeia** o que foi identificado e **não afirma
  adequação**. Dono: `financial-planner` + `data-engineer`.
- **Inventário confirmado como gate geral de `actual = 0`.** D2 fecha só o caso
  com contraprova documental; cadastro vazio sem documento algum continua
  computando gap sobre zero. Dono: `financial-planner`.

## Critério de aceite

- Payload com `policies: []` e `protecao_patrimonial.apolices_vigentes`
  populado: a copy "sem riscos cadastrados" não sai, o estado parcial sai,
  `gap_analysis["vida"]` não tem entry e `recommendations` não cita vida.
- `_gap_analysis_to_response` com `actual` nulo não produz `Decimal("0.00")`.
- Com cadastro ativo na categoria, gap e prescrição continuam idênticos.
- `pontos_urgentes` lê o mesmo estado do render — a contradição não muda de casa.
- Nenhuma copy deriva de `missing_inputs`.
