---
id: A40.l35
type: lane
title: "Bundle de proteção sobre insumos reais: a S9 calcularia cobertura e ITCMD sobre zeros"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l35-bundle-de-protecao-sobre-insumos-reais
adrs:
  - "[[ADR-240]]"
  - "[[ADR-192]]"
  - "[[ADR-387]]"
depends_on:
  - "[[A40.l62]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/backend
  - area/frontend
  - area/financial-planning
---

# A40.l35 — `bundle-de-protecao-sobre-insumos-reais`

> **Aberta em 2026-08-11**, spin-off da [[A40.l7]] (precedente: [[A40.l15]] ←
> [[A40.l3]]). Recebe o ⛔ que a l7 carregava e o §Deferido da [[ADR-240]], cujo
> dono passa a ser esta lane. Colocação e prioridade: `product-manager`.

> **Split de co-design em 2026-08-13.** O aceite original é tecnicamente
> impossível com os contratos atuais sem fabricar renda ativa líquida, situs EUA,
> UF fiscal e temporalidade. A [[A40.l61]] entrega a mitigação fail-closed; a
> [[A40.l62]] cria fontes canônicas + snapshot imutável; esta lane fica
> **bloqueada** e conserva a ativação final da S9. DAG: [[A40.l61]] →
> [[A40.l62]] → [[A40.l35]].
>
> 🔓 **Desbloqueada em 2026-08-15** — a [[A40.l62]] shippou (#1471 + #1474).
> Ativação da S9 em curso no #1476.

## Problema

O ⛔ da [[A40.l7]] dizia que `data.protection_bundle` *"não tem produtor"*. A
medição corrige e **agrava**: o produtor **existe**
(`populate_protection_bundle` → `protection_bundle_adapter` →
`build_protection_bundle_sync`, consumido hoje por `db_config_store`), mas
**calcula sobre zeros**.

Hardcoded em `backend/app/services/protection_bundle_populator.py` — **5 zeros e
2 `False`**, todos com `# TODO`:

| linha | insumo | efeito |
|---|---|---|
| :177 | `annual_active_income_brl_cents=0` | cobertura ideal de **vida** |
| :178 | `outstanding_debts_brl_cents=0` | idem |
| :188 | `active_net_monthly_income_brl_cents=0` | **invalidez** |
| :189 | `passive_net_monthly_income_brl_cents=0` | idem |
| :202 | `gross_estate_brl_cents=0` | **ITCMD / sucessão** |
| :213-214 | `has_us_assets=False` / `has_us_income=False` | exposição US |

Rodando o calculator real (`life_insurance_coverage_ideal`):

| Cenário | `ideal` | `gap` |
|---|---|---|
| família com dependentes, **como roda hoje** | **R$ 0** | **R$ 0** |
| mesma família **com renda plumbada** (R$ 300k/ano) | R$ 4.500.000 | R$ 4.500.000 |

**Ligar a S9 hoje publicaria "gap de proteção = R$ 0"** — que a família lê como
*"minha proteção está adequada"* — num documento fiduciário. E o **ITCMD sai
igualmente zerado**, sobre o eixo de sucessão que a S9 hospeda ([[ADR-192]] D3).
São **dois números falsos na mesma seção**, não um.

**Predicado de dependente errado, e é secundário.** `_dependents_ages` (:113)
filtra `role == "dependente"` e **exclui `role == "filho"`**, embora o schema do
E1 declare `titular, conjuge, filho, dependente`. Secundário porque, mesmo
corrigido, o ideal continua **zero** enquanto a renda for zero.

> **Dano latente, não vivo.** Nada user-facing consome `gap_analysis` hoje (0
> hits em `frontend/src/app/**`). Vira P0 **no instante** em que alguém ligar o
> bundle — por isso a lane é P1 **com amarra**, e por isso o ⛔ da l7 estava
> certo em existir.

## Escopo original — supersedido em 2026-08-13

`data.protection_bundle` chega ao payload do relatório **e** os cinco insumos
hoje zerados passam a vir do E5/E1.5, com **predicado único de dependente
econômico** — produtor e cálculo **no mesmo PR**, como a condição de retomada da
[[ADR-240]] §Deferido já exige. Ligar a fonte antes de corrigir o cálculo troca
uma afirmação falsa por outra.

A injeção no view-model segue o padrão já usado para `recalibracao_mc`
(`get_report_data`), **não** o artefato E5 — evita mover a chave de cache do
parecer.

**Emenda datada à [[ADR-240]]**, sem ADR nova: plumbar insumo que a ADR já
pressupõe é conformance. O que é regra nova é o **predicado de dependente
econômico**, e vai na emenda com **co-design `financial-planner`** — a definição
é dele. Heading de emenda **não leva wikilink**; `amended_at` no mesmo commit.

## Escopo vigente — split 2026-08-13

O co-design `financial-planner` + `data-engineer` + `product-designer`, fechado
por `senior-cto`, refutou a premissa de que os sete campos eram simples plumbing:

- o E5 pinado contém patrimônio/dívidas e parte da renda passiva, mas não renda
  ativa líquida mensal canônica nem situs EUA;
- E1.x histórico cai em fallback workspace-scoped `latest` e não recompõe o run;
- o adapter lê apólices/membros/workspace vivos e `date.today()`, quebrando a
  fotografia do Report;
- UF default SP e tabela fiscal hardcoded violam [[ADR-135]];
- `10× renda` sem dependente econômico contradiz [[ADR-365]].

Por isso a entrega foi decomposta sem rebaixar este aceite:

1. [[A40.l61]] remove zeros/`False` implícitos, declara computabilidade por
   categoria e corrige o predicado `filho`, sem ligar a S9.
2. [[A40.l62]] produz os contratos ausentes e persiste o
   `ProtectionComputationSnapshotV1` decidido em [[ADR-387]].
3. Esta lane consome somente o snapshot, injeta-o no view-model e executa o gate
   renderizado. Merge de pré-lane **não** conta como entrega parcial desta lane.

## Critério de aceite

- Família com `role == "filho"` produz `dependents_ages` não-vazio.
- Com renda e dívidas reais, `ideal`/`gap` de vida e invalidez **≠ 0** para
  família que de fato precisa — e `gross_estate` alimenta o ITCMD.
- Nenhum dos 5 insumos permanece hardcoded; teste que falha se um `# TODO`
  voltar a zerar.
- **Sinal do delta declarado** + conferência por `dev/golden_diff.py`.
- **Verificação renderizada** da S9 (§Débito de método).
- A S9 sai do empty state **total** apenas quando o bundle tem insumo real.

## Amarra com a [[A40.l11]]

A [[A40.l11]] é dona de *"componente de proteção ausente do score"* e vira
**consumidora** desta lane: sem ela, a l11 fixa score sobre bundle zerado e
**fecha verde**. Declarado no frontmatter da l11.
