---
id: A40.l62
type: lane
title: "ProtectionComputationSnapshotV1: fontes run-scoped e computabilidade por categoria"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1474
ship_date: "2026-08-15"
priority: P1
branch_slug: a40-l62-protection-computation-snapshot-v1
adrs:
  - "[[ADR-387]]"
depends_on:
  - "[[A40.l61]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
  - area/persistence
  - area/financial-planning
---

# A40.l62 — `protection-computation-snapshot-v1`

> **Aberta bloqueada em 2026-08-13**, no co-design da [[A40.l35]], e
> **desbloqueada em 2026-08-14** após a [[A40.l61]] shippar no PR #1443.
> Decisão arquitetural em [[ADR-387]] (`Decidido` em 2026-08-14).
>
> ✅ **Entregue em 2026-08-15.** PR1 #1471 (`ea1a2c6a`) — fontes relacionais e
> contrato E5 V1. PR2 #1474 (`5cc4a02f`) — snapshot pinado ao Report, GET só
> lê `snapshot.bundle`, hash `report-v2`. Nenhuma metade ligou a S9; isso
> continua com a [[A40.l35]] (#1476). `ship_pr` nomeia o último código.

## Problema

O Report aponta para um E5 exato, mas `Protection`, `FamilyMember` e `Workspace`
são estado vivo, e o adapter usa `date.today()`. Recompor o bundle no GET faria a
mesma fotografia mudar após edição de apólice, membro, perfil ou passagem do
calendário. Além disso, o E5 não possui hoje renda ativa líquida mensal nem
status/situs EUA suficientes; E1.x histórico não é recuperável por run sem
fallback `latest`.

## Escopo em dois PRs ordenados

1. **Fontes e regras canônicas.** Contrato E5 person-scoped para renda líquida,
   dependência, segurado/benefício/inventário e cenários fiscais; rule-sets
   ITCMD/FBAR/FATCA/Estate NRA por vigência; correção dos calculators atuais.
   Ausência permanece `null`; nenhum PR1 liga a S9.
2. **Snapshot e integridade.** Migrations nullable de Report/publicação,
   envelope V1, captura transacional e hash `report-v2`. O GET apenas injeta o
   bundle persistido; legado não consulta estado live.

As duas partes formam uma propriedade única: “o relatório usa os insumos
vigentes quando foi gerado”. Nenhuma metade libera a S9 isoladamente.

## Critério de aceite

- Schema E5 × produtor estrito e golden de execução verdes; dinheiro em cents,
  pessoa/check explícitos e nenhum default zero para ausência.
- Vida/invalidez não cruzam segurados; capital único não vira benefício mensal;
  inventário parcial não vira cobertura zero.
- Sucessório é cenário por pessoa/direito; FBAR, FATCA e Estate NRA têm bases e
  status separados. USD não prova situs e UF ausente não cai em SP.
- Parâmetro fiscal traz rule-set, vigência e fonte; zero ou ambiguidade retêm só
  a instância afetada.
- Snapshot contém versão, `captured_at`, `as_of_date`, proveniência, versões de
  calculator e estados por instância.
- Editar apólice, membro, perfil, parâmetro ou relógio depois da criação não muda
  o slice servido pelo mesmo `report_id`.
- Report legado sem snapshot não consulta estado live: proteção fica indisponível.
- Publicação nova referencia o Report e hash `report-v2` detecta qualquer
  alteração semântica; `e5-v1` legado continua verificável.
- Migration, schema do overlay, OpenAPI/view-model snapshot e testes estão
  squash-mergeados em `main` antes de desbloquear a [[A40.l35]].

## Residual após o merge — 2026-08-15

O que **não** saiu dos PRs, de propósito (D6) ou por falta de insumo no V1:

- Checks EUA não produzem `computed`. Fontes e `fiscal_rule_sets` existem;
  o populator ainda retém `compliance_us` até a regra separar FBAR/FATCA/Estate
  NRA. Dono da superfície: [[A40.l35]]; a promoção do calculator não é automática.
- Sucessório sem cenário de espólio no V1 permanece `missing_data`. É proibido
  publicar patrimônio familiar × UF como imposto devido.
- S9 continua desligada. Pré-lane não conta como entrega da l35.

## Achados medidos entregues ao PR1 — 2026-08-14

> Origem: sessão que começou a l62 sobre base pré-#1451 e teve o escopo superado
> pela [[ADR-387]] `Decidido`. O código foi descartado; **estas três medições
> sobrevivem** porque são fatos do repositório, não desenho. Cada uma tem
> call-site citado — re-meça antes de usar, o rastro envelhece.

**1. `endividamento.total_dividas` é cópia derivada, não segunda medição.**
`endividamento_analyzer.py:88` faz `dividas_total = patrimonio.get("dividas")`, e
`to_legacy_dict` emite `round(self.total_dividas, 2)`. Tratar os dois campos como
fontes independentes é a dupla soma que o §Critério de aceite proíbe. A fonte
única para `dívida atribuída` (D4, vida) é `patrimonio.dividas` — e ela é
**familiar**, então a atribuição por segurado que a D4 exige ainda não tem
produtor.

**2. `passive_income.renda_passiva_mensal_brl` não tem base única.**
`passive_income_calculator.py:488-490` usa `buckets.dividendos` (razão) quando
`> 0` e cai para `renda.dividendos_liquido_brl` (IRPF) senão — bruto e líquido
alternam **por fonte, dentro do mesmo campo**. A D4 exige renda ativa e passiva
líquidas *na mesma janela*: este campo não satisfaz o par, e usá-lo produziria o
gap de invalidez inventado que a [[A40.l61]] acabou de fechar.

**3. `itcmd_estimated` já declara proveniência que não existe.**
`itcmd_estimator.py` monta `sources=f"Tabela ITCMD {uf} (fiscal_parameters)"`,
mas `fiscal_parameters` não tem coluna de ITCMD — o model é `year`, `ir_brackets`,
`pgbl_limit`, `inss_ceiling`, `lucro_presumido`. Hoje é **inerte** (a l61 retém a
categoria antes do calculator rodar), então não há dano vivo; vira dano no
instante em que `fiscal_rule_sets` (D5) ligar o sucessório sem trocar a string.

**Contexto de renda ativa, para quem escrever o `protection_computation_inputs_v1`:**
o E5 não tem renda ativa canônica. Existe `renda_ativa_pj_excluida_brl`, que é a
parcela PJ *excluída* do cálculo de renda passiva — subconjunto, não a renda. O
material mais próximo é `fluxo_caixa.receita_por_natureza` ([[ADR-330]]:
`receita_pj + receita_clt + receita_aluguel + receita_outras == receita_total`,
conservativo em cents), mas ele é **familiar e bruto**, e a D4 pede
**por segurado e líquido de 12 meses completos** — a distância entre os dois é
trabalho de produtor, não de projeção.
