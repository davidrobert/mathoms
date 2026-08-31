---
id: ADR-430
type: adr
title: "Contrato E1→E4 do mapa instituição→membro: hint tier 1 fundido no produtor único, com origem carregada até o E5"
status: Proposto
phase: A40.l96
date: "2026-08-31"
relates_to:
  - "[[ADR-226]]"
  - "[[ADR-229]]"
  - "[[ADR-146]]"
  - "[[ADR-243]]"
  - "[[ADR-394]]"
  - "[[ADR-412]]"
  - "[[ADR-212]]"
  - "[[ADR-259]]"
  - "[[ADR-111]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 430"
  - "contrato E1 E4 banco_membro"
  - "origem da atribuicao de titularidade"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/backend
  - area/persistence
  - sprint/a40
---

# ADR-430 — Contrato E1→E4 do mapa instituição→membro

**Status:** Proposto • **Data:** 2026-08-31 • Origem: [[A40.l96]] §Co-design

## Contexto

O mapa `instituição → membro` que resolve a titularidade dos investimentos é
produzido pelo E1 e **morre antes do E4**. O relatório publica o buraco como
fato sobre a família — *"49,03% da carteira financeira sem titular
identificado"* — acendendo 8 superfícies, entre elas risco de severidade Alta no
parecer e a supressão da prescrição de realocação da reserva.

Medido em 2026-08-31 (run `79a61e33`): `bank_accounts` tem **0 rows no banco
inteiro** e nenhum writer no pipeline, enquanto o artefato E1 do mesmo run traz
`banco_membro` com 11 instituições e `contas[]` com 18 contas. São **dois
produtores do mesmo mapa lendo fontes diferentes**: `extract_members` escreve só
no artefato; `serialize_family_members` monta a partir da tabela vazia — e é
este que vira `config_overrides["family_members.json"]`, que o E4 consome.

Duas decisões vigentes conflitam sobre quem deveria fechar essa lacuna:

- **[[ADR-226]] §5** (2026-05-19) decidiu que o E1 opera em *"modo merge
  idempotente"* escrevendo em `bank_accounts` — **nunca implementado**.
- **[[ADR-229]] §1** (2026-05-20) decidiu o mecanismo oposto: o artefato E1 é
  **tier 1**, e o **clique humano** promove a tier 5. Este está implementado
  ponta a ponta (endpoint, adapter lendo `stage=extract_members`, UI com
  detecção de colisão de conta).

## Decisão

### 1. `bank_accounts` é curada pelo usuário; o pipeline não escreve nela

[[ADR-229]] §1 prevalece. A tabela responde *"quais contas a família tem"* —
entidade editorial com `label`, número como o usuário digitou, `source_tier`,
`irpf_snapshots`. O E4 faz outra pergunta (*"de quem é esta posição"*), e o erro
foi as duas terem o mesmo produtor: **quando a curadoria está vazia, o pipeline
não degrada para um tier inferior — publica ausência de curadoria como fato.**

A [[ADR-226]] §5 é declarada morta por emenda datada na própria 226.

**Rejeitada — persistir o E1 em `bank_accounts`:** o partial unique index da
ADR-226 PR4 é parcial (`WHERE account_number IS NOT NULL`), então conta de IRPF
sem número fica fora do índice e **duplica a cada run**; e `extract_members`
skipa em modo incremental, fazendo o estado do DB depender da ordem de upload.
Além de tornar output de LLM uma row editorial, contra a ADR-229 §1.

**Rejeitada — o E4 ler o artefato E1 direto:** `serialize_family_members`
alimenta **três** rotas (E4, `consolidate_baseline`, `extract_informe_aluguel`).
Consertar no consumidor conserta 1 de 3.

### 2. O merge é no produtor único, e a conta carrega a origem

`serialize_family_members` funde as contas do artefato E1 como **hint tier 1**.
`BankAccountRecord` ganha `origem: Literal["curada", "irpf_hint"]`, default
`curada`.

Precedência, **na granularidade da conta** — nunca por instituição, o que
mataria a ambiguidade legítima:

| caso | regra |
|---|---|
| match exato `(institution_code, account_number_norm)` com row curada | hint não entra — é a mesma conta |
| hint em `workspace_irpf_suggestion_dismissals` | **não entra** — a tabela é o registro do "não" do usuário ([[ADR-229]] §3) |
| hint de membro sem conta curada na instituição | entra, marcado `irpf_hint` |
| conflito de `member_key` na mesma conta | curada vence **sempre**, mesmo com IRPF mais novo ([[ADR-146]] tier 5 > tier 1, [[ADR-186]] override sticky) |

### 3. A origem sobrevive até o E5 — pré-condição, não acabamento

Hoje `AccountResolution.confidence` é calculado, logado e **descartado**: os dois
call-sites colapsam o enum de 4 estados em `{chave | "needs_review" | ""}`.
Fechado o wiring, `fallback_bank` (banco de dono único) passa a sustentar quase
toda a atribuição — e isso é **hint com boa confiança, não fato declarado**.

A posição carrega `atribuicao_fonte ∈ {declarada, conta_casada, banco_unico,
indeterminada, sem_dono}` até o E5. Sem isso, fechar o wiring **troca
falso-negativo por falso-positivo**: o Top 15 afirmaria titularidade inferida
com o peso visual da declarada, e as 8 superfícies apagariam sem registro —
regressão sob [[ADR-394]] (fato ≠ hint) e sob a distinção que a [[ADR-412]]
construiu.

Corolário: `"needs_review"` **deixa de ser usado como `member_key`**. Hoje vira
chave em `total_por_membro` (`additionalProperties: number`) — um membro
fantasma somando dinheiro.

### 4. O artefato E1 passa a ter schema

`config/schemas/e1_members.schema.json`, registrado em `SCHEMA_BY_STAGE`
([[ADR-212]] PR3a). O E1 rodou ~15 meses **sem contrato** — é por isso que a
rota pôde quebrar em silêncio.

O schema **enforça `institution_code` canônico** (`^[a-z0-9]+$`). O produtor E1
não normaliza — o campo é `str` livre do LLM, cuja descrição apenas *pede*
código canônico — enquanto o consumidor E2 aplica `.lower().replace(" ","")`.
Uma grafia acentuada faz o resolver errar o match **em silêncio**, que é o mesmo
modo de falha desta lane. Enforça também a proibição de CPF cru ([[ADR-259]] §2).

**O alcance do mapa até o E4 NÃO é hard-fail.** "E1 com `banco_membro` cheio e
materializado vazio" será estado **legítimo** depois do fix — é o workspace cujas
contas de hint foram todas recusadas. Gate que falha alto aí treina o usuário a
ignorá-lo. O sinal é telemetria (`family_members.hint_merge{curadas, hint,
dismissed, conflito}`) + `review_reason` quando `pct_inferido > 0`.

### 5. O merge é recomputado após o E1, dentro do mesmo run

`config_overrides` congela **uma vez por run**, antes de qualquer stage. Sem
recomputar, o hint do E1 do run corrente não chega ao E4 do mesmo run: o critério
*"run novo do workspace de dogfood publica abaixo do piso"* passaria por
acidente — lá o E1 já rodou antes — e **falharia no primeiro run de um workspace
novo**, que é o momento que importa.

Hook pós-stage recomputa `ctx.config_overrides["family_members.json"]` quando
`stage_name == "extract_members"`, com log. Mutação de campo de objeto per-run
não viola [[ADR-111]] — o proibido é estado de módulo.

## Consequências

- `extract_members` é `tier="premium"`: **no free tier o hint não existe**. A
  copy não pode prometer o que a tier não entrega, e fixture de gate não pode ser
  free-tier, ou mede o vazio.
- O hint pode vir de artefato E1 antigo, com ano-base velho. Frescor é da
  [[A40.l41]]/[[A40.l42]]; aqui só se carrega o ano.
- Muta E4 e E5 ⇒ entra na janela de rebaseline da sprint.
- Resíduo medido, fora do escopo: **42 dos 95 artefatos E1** do banco de dogfood
  carregam `cpf` cru, todos entre 2026-05-15 e 2026-06-22. De 2026-07-03 em
  diante, zero — o produtor foi corrigido e o schema agora guarda a regressão.
  O expurgo do resíduo histórico é linha própria.

## Alternativas rejeitadas

- **Hard-fail no alcance do mapa** — ver §4: o estado "vazio" vira legítimo.
- **Merge por instituição** em vez de por conta — mata a ambiguidade legítima de
  banco com contas de dois membros.
- **Fail-fast em `origem` desconhecida** — `family_members.json` também chega de
  import de config do usuário; derrubar o run por um campo cosmético trocaria
  precisão por indisponibilidade. Degrada para `curada` com WARNING carregando o
  ofensor.
