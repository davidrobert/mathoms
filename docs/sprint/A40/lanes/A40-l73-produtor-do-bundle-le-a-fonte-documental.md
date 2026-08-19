---
id: A40.l73
type: lane
title: "Produtor do bundle de proteção lê a fonte documental, e o gap_qualitativo reconcilia com os dependentes do IRPF"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
priority: P1
ship_pr: 1576
ship_date: "2026-08-19"
branch_slug: a40-l73-3c-produtor-protecao
adrs:
  - "[[ADR-395]]"
  - "[[ADR-240]]"
  - "[[ADR-192]]"
  - "[[ADR-387]]"
depends_on: []
parallel_with:
  - "[[A40.l60]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l73 — `produtor-do-bundle-le-a-fonte-documental`

> ✅ **Entregue em 2026-08-19** em 5 PRs: **#1549** (lane + [[ADR-395]]) · **#1554**
> (canal `categorias_somente_no_documento`) · **#1560** (`e6774876`, retenção no
> populator + `actual` nulo deixa de virar `0,00`) · **#1564** (S9 de vazio para
> **parcial**) · **#1576** (metade (i) + `pontos_urgentes` lendo o mesmo estado).

> **Aberta em 2026-08-19** pelo item **3c inteiro** da Onda 3 do
> [[PLAN-deterministic-authority]] (`_README.md:441`), por autorização
> explícita do dono — é escopo fora do MVP declarado da A40. Cobre o achado
> **PD-4** do r7, re-teste de **RV6-20** / **RV5-03**.

## O defeito

Duas fontes de apólice que nunca se falam:

1. `ProtectionBundle.policies` — tabela `protections` com `status == "Ativa"`,
   cadastrada à mão ([[ADR-192]]).
2. `protecao_patrimonial.apolices_*` — bloco vivo do E5, produzido por
   `compute_protecao_via_store` a partir de `extract_comprovantes_bens`
   ([[ADR-240]] §D8).

`hasRealProtectionInputs` olha só a fonte 1 e imprime *"sem riscos
cadastrados"*, enquanto a seção vizinha renderiza a fonte 2 e
`pontos_urgentes` cita apólices vigentes. Com o cadastro vazio, o populator
publica `actual = 0`, gap igual à necessidade integral e prescrição de
prioridade alta — afirma zero onde não mediu.

> **`protecao_patrimonial` não é código morto.** Uma análise anterior concluiu
> isso grepando só `backend/**`. O bloco é produzido em `pipeline/`.

O #1476 ([[A40.l35]]) tentou consertar render-side e foi **no-op por
construção**: os 4 sinais do predicado saem do mesmo bundle. Daí o
re-roteamento do 7c para o produtor.

## A decisão de domínio

Fechada pelo `financial-planner` e formalizada em [[ADR-395]]. Resumo
operacional: apólice extraída de documento **não entra na aritmética**, mas
"gap intocado" não pode virar "gap publicado como se a cobertura fosse zero".
Documento vigente numa categoria **sem cadastro ativo** ⇒ `missing_data`,
sem entry em `gap_analysis`, sem prescrição, S9 de vazio para **parcial**.

## Divisão de arquivos com a [[A40.l60]]

`dev/lane_pickup.py A40.l60` (rodado em 2026-08-19) devolve **OCUPADA** por
duas branches — `agent/a40-l60-ressalva-conselho-seguro/20260812-1030`
(último commit 2026-08-12) e `agent/a40-l60-ressalva/20260815-1520` (último
commit 2026-08-17). Nenhuma tem worktree vivo e nenhuma tem PR aberto: a lane
está **dormente**, não ocupada. O PR1 dela (#1480) mergeou; o **PR2 segue
pendente** e toca os mesmos arquivos.

| Arquivo | Dono |
|---|---|
| `S9RiscosSection.tsx` — predicado de vazio + estado parcial | **l73** |
| `S9RiscosSection.tsx` — ressalva fiduciária nos cards | l60 PR2 |
| `s9ProtectionInputs.ts` | **l73** |
| `summaries_narrator._S9_GAP_VIDA` | l60 PR2 (não tocar) |
| `protection_bundle_populator` — `calculation_status` por fonte documental | **l73** |
| Separação vida × invalidez no conselho | l60 PR2 (não tocar) |
| `pontos_urgentes_analyzer._seguro_vida_item` — retenção por dependente IRPF | **l73** |

O escopo da l60 (ressalva fiduciária, separação vida×invalidez, afirmação de
invalidez sem fonte) **não é resolvido aqui**.

## Entregável

- **PR1** — esta lane + [[ADR-395]] `Proposto`.
- **PR2** — `escopo_cobertura.categorias_somente_no_documento` no payload
  ([[ADR-240]]) + `actual` nulo deixa de virar `Decimal("0.00")`.
- **PR3** — `documentary_coverage` no `ProtectionBundle`; populator retém a
  categoria com contraprova documental.
- **PR4** — render S9: predicado lê as duas fontes, estado parcial nomeia o
  que foi identificado.
- **PR5** — metade (i): `gap_qualitativo` × `irpf_kpis.dependentes` +
  `pontos_urgentes` lendo o mesmo estado.

## Fora de escopo (registrado, não consertado)

- **Prestamista e vida em grupo do empregador.** `_categorias_de_documento`
  (`cobertura_consolidada.py`) fecha `flag_vida` com **qualquer** `tipo ==
  "vida"` vigente, e `pipeline/llm/schemas/apolice.py` (`CoberturaVida`) não
  distingue apólice prestamista (beneficiário = credor) nem vida em grupo
  (morre com o vínculo). Prestamista quita dívida e não deixa nada à família:
  silenciar gap de vida com ela é falso conforto. **Defeito vivo hoje,
  independente desta lane.** Dono: `financial-planner` + `data-engineer`.
  Mitigação aqui: o estado parcial **nomeia** o identificado e **não afirma
  adequação de cobertura**.
- **Conflito de vigência** (documental vencida × cadastro "Ativa"). Deferido em
  [[ADR-395]] §Deferido com dono e condição de retomada.
- **Residual PE** (precedência entre fontes contraditórias no prompt do
  parecer) é item próprio da **Onda 5** (achado PE-3). Manifest e prompt não
  são tocados aqui.

## Como ficou

| Estado | Gatilho | O que o relatório publica |
|---|---|---|
| `apurado` | cadastro sustenta o cálculo | gap e prescrição, como antes |
| `parcial` | só o documento identificou apólice | nomeia apólices, seguradoras e vigência; declara o gap **retido**; sem número, sem conselho |
| `nao_apurado` | nenhuma fonte | ausência declarada nomeando o insumo — **não** "sem riscos cadastrados" |

`gap_qualitativo` ganhou `status: apurado | nao_apurado`; `flag` seguiu booleano
de propósito (o prompt do parecer lê `flag == True` e **não foi tocado** — PE-3
é Onda 5).

## Aceite

- `policies: []` + `apolices_vigentes` populado ⇒ copy "sem riscos cadastrados"
  não sai; estado parcial sai; `gap_analysis["vida"]` sem entry;
  `recommendations` sem vida.
- `_gap_analysis_to_response` com `actual` nulo não devolve `Decimal("0.00")`.
- Regressão: com cadastro confirmado, gap e prescrição idênticos a hoje.
- Prova por **mutação** por metade, com a saída colada no PR.
