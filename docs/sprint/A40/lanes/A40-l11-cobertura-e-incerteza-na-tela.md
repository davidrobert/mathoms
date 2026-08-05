---
id: A40.l11
type: lane
title: "Cobertura e incerteza na tela: três percentuais para o mesmo conceito, prazo de IF como fato"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P2
branch_slug: a40-l11-cobertura-e-incerteza-na-tela
adrs: ["[[ADR-353]]"]
depends_on: ["[[A40.l3]]", "[[A40.l4]]"]
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p2
  - area/frontend
---

# A40.l11 — `cobertura-e-incerteza-na-tela` (RV3-13, RV3-14, RV3-29)

## Problema

**Três percentuais, um conceito (RV3-13).** `diagnostico_confianca` é a **única
chave top-level do view-model sem consumidor**. O banner recomputa por conta
própria sobre outra janela; uma seção exibe um terceiro número. O Score aparece
verde "Bom" sem ressalva, construído sobre cobertura parcial.

**Prazo como fato (RV3-14).** O KPI imprime o ano em `<strong>` sem marca de
incerteza; a probabilidade e a divergência vs. o P50 vivem em `text-xs`.

**Cinco bases (RV3-29).** O painel confirmou que o escopo é **deliberado e
correto** — reserva não é classe rebalanceável, imóvel ilíquido não se rebalanceia
por aporte. Mas isso **não** é defesa contra o defeito registrado, que é *ausência
de rótulo declarando o escopo*. Ao contrário: o escopo ser conhecido é o que torna
o rótulo barato e obrigatório. Risco concreto: a família dimensiona o aporte contra
a base errada e executa o rebalanceamento no tamanho errado.

**Bloqueio de ADR:** o flip de [[ADR-353]] para `Decidido` fica **bloqueado** até o
campo-portador ter consumidor — flipar antes embarca decisão sem entrega, que é
exatamente o padrão que esta sprint combate.

## Escopo

- Uma **única** fonte para o share de não-identificado (a canônica, por valor), com
  janela rotulada; o cliente para de recomputar.
- Selo de confiança no card de Score — forma + cor + texto, não só cor.
- Sub-linha de probabilidade no KPI de IF; a estatística passa a mostrar P50 e meta.
- Rótulo de escopo na base do rebalanceamento.

## Critério de aceite

- `rg 'diagnostico_confianca' frontend/src` > 0.
- Um só número para o mesmo conceito na mesma tela.
- **Verificação renderizada** — este cluster é inteiramente de percepção; fechar
  sobre inferência de código não é aceitável. Spec com a fixture `degraded` (que já
  liga os degrades) + assert de que o selo de confiança aparece e de que existe **um
  só** percentual para o conceito na tela.
- [[ADR-353]] só flipa **depois** de o consumidor existir.

## Item adotado (2026-08-05)

Follow-up de [[A40.l3]] §Assimetria de rótulo (handoff explícito, sem destino até
então): dos 8 blocos com chave `janela` no substrato, **3 não cumprem** a obrigação
da [[ADR-306]] — não 2. Correção de contagem: `reserva_emergencia` só tem tooltip
(`InfoTooltip`), e a [[ADR-306]] §Emenda A40.l3 já declara que tooltip **não conta**
como rótulo, porque não sai no PDF. Os 3 que não cumprem: `equilibrio_cerbasi` (sem
base alguma), `passive_income` (janela `irpf` nunca exposta), `reserva_emergencia`
(só tooltip).

- Mesma classe de defeito que esta lane já cobre (RV3-29): campo existe, rótulo que
  o declara não chega ao usuário.
- Critério de aceite adicional: os 3 blocos passam a ter rótulo **impresso** (não
  tooltip) lido do campo `janela`/base declarada, verificado em render + PDF (mesmo
  padrão `pdftotext -layout` das demais lanes de `clareza-ux` desta sprint).
