---
id: ADR-197
type: adr
title: "Estado modelo_simplificado expõe componentes elegíveis e redireciona para PGD/MIR (estende ADR-189 §4 Estado 2)"
status: Decidido
phase: "A12"
date: "2026-05-12"
relates_to:
  - "[[ADR-189]]"
  - "[[ADR-157]]"
  - "[[ADR-194]]"
  - "[[ADR-195]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 197"
  - "IRPF simplificado componentes elegíveis"
  - "PGD/MIR ponteiro"
tags:
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
  - phase/a12
  - status/decidido
  - type/adr
---

## §1 — Contexto

A seção `S_IRPF_OTIMIZACAO` do relatório premium tem hoje (pós ADR-189
+ ADR-194) três cards: `IrpfPgblCapacidadeCard` (half, 4 estados),
`IrpfDependentesCard` (half, ADR-194 §6.1) e `IrpfDedutiveisAplicadosCard`
(full, ADR-194 §6.2).

Usuários em modelo simplificado lêem, no card PGBL Estado 2
(`modelo_simplificado`), apenas a explicação técnica do regime:

> "Você declarou pelo modelo simplificado em {ano_base} — neste regime,
> a Receita já aplica um desconto fixo sobre os rendimentos tributáveis
> (limitado a teto anual), e contribuições a PGBL não geram dedução
> adicional. A capacidade de 12% só vale no modelo completo."
> — [ADR-189 §4 Estado 2](189-pgbl-diagnostico-tipificado-substitui-metrica-monovalor.md)

Essa copy fechou a porta de "compare com completa" (alternativa C
rejeitada na ADR-189 §2 com nota "pode virar lane futura com sign-off
financial-planner"). A lane futura é esta ADR.

Trade-off identificado:

- **Modelo simplificado é majoritário em renda PF brasileira (~70-80%
  dos contribuintes).** Para muitos desses, o regime escolhido por
  inércia pode ser subótimo, mas a seção "Otimização Tributária" não
  oferece nenhum sinal direcional.
- **Computar contrafactual completa (R$ Δ entre IR pago em simplificado
  e IR hipotético em completa) é orientação fiscal de fato** — disclaimer
  não anula CTA implícito, e o número viraliza em screenshot sem
  contexto. Veto G0.
- **O programa oficial da Receita (PGD/MIR) já compara os dois regimes
  automaticamente** durante o preenchimento e sugere ao contribuinte o
  mais vantajoso (`https://www.gov.br/receitafederal/...`). Mathoms
  duplicar essa comparação fora do contexto da declaração agrega risco
  sem agregar valor.

## §2 — Alternativas avaliadas

Vereditos do co-design pré-ADR (2026-05-12):
[financial-planner (G0)](../../.claude/agents/financial-planner.md),
[data-engineer (G2)](../../.claude/agents/data-engineer.md),
[product-designer (G4)](../../.claude/agents/product-designer.md).

### A. Card "Comparativo" com Δ literal em R$ (Δ = IR pago − IR hipotético)

**Pros:**
- Máxima transparência; usuário pode agir.

**Contras:**
- **VETO G0:** "isto é orientação fiscal por qualquer leitura — disclaimer
  não anula CTA implícito. Aproxima Mathoms de robo-advisor de regime
  tributário sem credencial CVM/CFC."
- Δ em hero number sai do contexto do relatório — screenshot em
  WhatsApp sem disclaimer.
- Confiança do schema E1.6 (LLM extraction, `confidence` variável,
  reconciliação cross-field cap 0,7) ≠ confiança que Δ em hero exige.
- Lei 15.270/2025 (IRPFM) introduz redutor mensal e tabela nova a partir
  de 2026 — qualquer fórmula desenhada hoje quebra cedo.

**G2 nota:** seed atual de `fiscal_parameters.ir_brackets` tem
`deducao_brl_cents=0` em todas as faixas (valores RFB corretos:
0/16944/38144/66277/89600 cents). Qualquer Δ calculado hoje seria
silenciosamente errado. Débito independente — ver §5.

**Rejeitada.** Reabertura condicionada a 4 critérios cumulativos em §5.

### B. Qualitativo direcional ("em X% dos casos com perfil similar, completa é mais eficiente")

**Pros:**
- Mantém valor informativo sem entregar número que vira "verdade fiscal".

**Contras:**
- **VETO G0:** "modelo populacional que Mathoms não tem; fabricar
  percentual é pior que Δ literal porque dá ilusão de evidência
  estatística."
- "X% dos casos" vira argumento de venda; cruza linha sem ferramenta
  metodológica para sustentar a estatística.

**Rejeitada.**

### C. Exposição factual de componentes elegíveis + ponteiro PGD/MIR (recomendada)

**Pros:**

- **APROVADA G0** com reformulação substancial: "É a única que satisfaz
  Perini (renda líquida calculável), Cerbasi (educacional) e AUVP (expõe
  componentes para o investidor decidir) sem cruzar linha de prescrição."
- Zero cálculo de IR contrafactual: usa **só** componentes já extraídos
  pelo schema E1.6 (saúde, educação, dependentes, INSS, PGBL aportado) —
  os mesmos valores que `IrpfDedutiveisAplicadosCard` e `IrpfDependentesCard`
  publicam.
- **Redireciona a comparação** para a autoridade competente (PGD/MIR da
  Receita) em vez de duplicá-la. Desonera Mathoms do papel de "comparador".
- Determinístico, sem LLM novo, sem mudança no analyzer, sem mudança no
  serializer, sem mudança em fiscal_parameters.

**Contras:**

- Cards `IrpfDedutiveisAplicadosCard` e `IrpfDependentesCard` já mostram
  os mesmos números em outro lugar da seção — risco de duplicação visual.
  Mitigação: copy do Estado 2 sinaliza explicitamente a função
  diferente (componentes **fora da base de cálculo do simplificado**, não
  "dedutíveis aplicados"); densidade da seção tolerável (Estado 2 antes
  era ~3 linhas, fica ~8 — ainda half).
- **G4** recomendou alternativa: fundir com `IrpfDedutiveisAplicadosCard`
  via banner condicional ao topo do card existente. **Não adotada nesta
  lane.** Razão: o card Dedutíveis tem semântica "valores deduzidos do
  imposto" (cabeçalho atual) — em simplificado nada foi de fato deduzido,
  então adicionar banner ali aumenta a confusão existente. Bug de header
  enganoso do card Dedutíveis em simplificado é débito separado registrado
  como `track_irpf_dedutiveis_simplificado_header_fix.md` (lane futura).

### D. Substituir a seção `S_IRPF_OTIMIZACAO` por seção "Componentes da Declaração"

**Pros:**
- Reframe arquitetural que separa diagnóstico (cards atuais) de
  contextualização (este ADR).

**Contras:**
- Esforço alto: re-arquitetar `config/report_layout.yaml`, codegen,
  copy de seção, e-mail/PDF, paridade narrativa S_IRPF_OTIMIZACAO no E5.
- **G4:** "`S_IRPF_OTIMIZACAO` é o lar certo. Criar section nova custa
  codegen + dilui foco; não compensa por uma extensão de copy."

**Rejeitada.**

## §3 — Decisão

Implementar **alternativa C — Exposição factual de componentes elegíveis
no Estado 2 do `IrpfPgblCapacidadeCard`** com ponteiro literal para o
PGD/MIR da Receita.

### D1 — Backend: zero mudança

Todos os campos necessários já estão em `irpf_kpis`
(ADR-194 + ADR-189):

- `dedutiveis_aplicados.saude.utilizado_brl`
- `dedutiveis_aplicados.educacao.utilizado_brl`
- `dedutiveis_aplicados.previdencia_oficial.utilizado_brl` (INSS)
- `dedutiveis_aplicados.pensao_alimenticia.utilizado_brl`
- `pgbl_aportado_brl` (soma todas as declarações, inclusive simplificadas)
- `dependentes.count`

`IRPFAnalyzer`, `_e5_kpis_from_analyzer` e schema `e5_analysis` permanecem
intactos.

### D2 — Frontend: Estado 2 estendido

O ramo `status === "modelo_simplificado"` em
[frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx:106-119](../../frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx)
ganha, abaixo do parágrafo explicativo do regime:

1. **Lista sparse de componentes elegíveis** lidos de
   `kpis.dedutiveis_aplicados` + `kpis.pgbl_aportado_brl` +
   `kpis.dependentes.count`, com framing **"fora da base de cálculo do
   simplificado"** (não "deduzidos", não "perdidos").
2. **Ponteiro literal para PGD/MIR** — uma linha factual sobre o
   simulador da Receita comparar automaticamente os dois regimes.

Variant continua `neutral` (G4: "se o card tem número grande + caveat
curto → neutral. Se tem caveat estendido + disclaimer obrigatório → info").
Disclaimer **não-escalonado** (G0: "Reforçar disclaimer acima do
nível do PGBL `capacidade_disponivel` produz Streisand — aumenta peso
percebido do número").

### D3 — Copy canônica do Estado 2 (substitui ADR-189 §4 Estado 2)

> **Capacidade PGBL**
> *Não se aplica · {ano_base}*
> **—**
>
> Você declarou pelo modelo simplificado em {ano_base} — neste regime,
> a Receita já aplica um desconto fixo sobre os rendimentos tributáveis
> (limitado a teto anual), e contribuições a PGBL não geram dedução
> adicional. A capacidade de 12% só vale no modelo completo.
>
> **Componentes elegíveis no modelo completo** (declarados em {ano_base}
> mas fora da base de cálculo do simplificado):
>
> - Saúde · R$ {saude}
> - Educação · R$ {educacao}
> - Previdência oficial (INSS) · R$ {inss}
> - Pensão alimentícia · R$ {pensao}
> - Dependentes · {n}
> - PGBL aportado · R$ {pgbl_aportado}
>
> O programa da Receita (PGD/MIR) compara automaticamente os dois
> modelos durante o preenchimento e sugere o mais vantajoso.

Notas:

- **Lista é sparse:** categoria com valor zero ou ausente é omitida.
- **Não usa palavras "perdidos", "deixados na mesa", "economizar"** (G4:
  cruzam linha de recomendação).
- **Não há Δ R$ visível** (G0).
- **Não há CTA** "mude de regime", "considere", "avalie" (G4).
- **PGD/MIR sem URL clicável** no PDF — apenas referência textual ao
  programa oficial. Risco de link rot mitigado.
- Parágrafo explicativo do regime simplificado **preservado** integralmente
  do ADR-189 §4 Estado 2 / §6.1 (G0 sign-off original).

### D4 — Sign-offs co-design pré-ADR

- **G0 (financial-planner) · 2026-05-12** — Aprovou Opção C, vetou A e
  B, redigiu copy do bloco de componentes, ratificou ponteiro PGD/MIR
  como dispositivo de desonerar Mathoms de "comparador". Disclaimer
  inline curto preservado (sem escalonamento).
- **G2 (data-engineer) · 2026-05-12** — Validou que o pattern de
  `FiscalParameters` value object existente é o caminho **caso a lane
  futura calcule Δ**. Para esta lane, confirmou que **zero alteração de
  backend é necessária** (componentes já no payload). Levantou bug
  independente em `fiscal_parameters.ir_brackets.deducao_brl_cents = 0`
  — débito tracker separado.
- **G4 (product-designer) · 2026-05-12** — Aprovou variante factual,
  reforçou vetos preventivos (cor semântica negativa, ícone de alerta,
  seta direcional, "perdidos"/"deixados na mesa", ranking de categorias,
  badge "oportunidade"), recomendou alternativa de fusão com card
  Dedutíveis (não adotada — ver §2 C).

## §4 — Consequências

### ✅ Ganhos

- Usuário em simplificado deixa de ler **apenas** a explicação do regime
  e passa a ver os componentes concretos que vivem fora da base de
  cálculo — alinhado com Cerbasi (revisão familiar anual de regime) e
  AUVP (expor componentes, não prescrever regime).
- Ponteiro para PGD/MIR transfere o ato de comparação para a autoridade
  competente — Mathoms se posiciona como **organizador**, não como
  **calculador alternativo**.
- Zero impacto em pipeline, schema, OpenAPI, ou paridade golden — apenas
  copy + leitura de campos já existentes.

### ⚠️ Riscos

- **Risco residual de leitura como recomendação.** Listar componentes
  com valor monetário ainda induz comparação mental. Mitigação:
  framing "fora da base de cálculo" (não "deduzidos", não "perdidos")
  + ponteiro explícito para PGD/MIR + caveat inline curto (G4 anti-Streisand).
- **Duplicação visual** com `IrpfDedutiveisAplicadosCard` e
  `IrpfDependentesCard` (ambos mostram os mesmos números em outro lugar
  da seção). Risco baixo: cabeçalhos distintos e contexto explicitado.
  Lane futura de fusão é tracker separado.
- **Header enganoso do `IrpfDedutiveisAplicadosCard` em simplificado**
  ("Valores deduzidos do imposto" — nada foi deduzido). Bug
  pré-existente, não introduzido por esta lane. Tracker separado.
- **Lei 15.270/2025 IRPFM** — copy não cita Δ nem alíquotas; não há
  invariante a quebrar quando RFB publicar regulamento. Lane robusta a
  essa transição.

### 🔄 Reversibilidade

Alta. Para reverter:

1. Restaurar ramo `status === "modelo_simplificado"` em
   `IrpfPgblCapacidadeCard.tsx` para a versão pre-ADR-197.
2. Re-arquivar este ADR como `Decidido (rejeitada)` em revisão de
   sprint subsequente.

Sem migração DB, sem alteração de schema, sem mudança em E1.6/E5/serializer.

## §5 — Não-objetivos (esta ADR)

- **Não** calcular ou publicar Δ de IR entre regimes (alternativa A —
  veto G0).
- **Não** publicar estatística populacional ("X% dos casos") sem modelo
  populacional sustentável (alternativa B — veto G0).
- **Não** criar 4º card na seção (alternativa G4 — não adotada para
  preservar densidade A4).
- **Não** corrigir bug `fiscal_parameters.ir_brackets.deducao_brl_cents = 0`
  — débito G2 fora desta lane; tracker separado.
- **Não** corrigir bug de header enganoso do `IrpfDedutiveisAplicadosCard`
  em simplificado — tracker separado.
- **Não** introduzir URL clicável para PGD/MIR — referência textual
  apenas, para evitar link rot e responsabilidade implícita pela URL.

### §5.1 — Reabertura da alternativa A (Δ literal)

A alternativa A só pode ser reaberta sob **todos** os 4 critérios
cumulativos (acordados com G0):

1. Confiança do schema E1.6 ≥ 0,85 sustentado em ≥ 90% das declarações
   reais processadas (atualmente cap em 0,7 com flag `needs_review`).
2. Regulamentação da Lei 15.270/2025 publicada e estabilizada em
   `fiscal_parameters` (campo `source` ≠ `STUB:*` para o ano-base).
3. Mathoms portar credencial CVM/CFC/CFP ou entrar em B2B2C com
   planejador humano-no-loop — neste caso lane prescritiva fica
   reservada ao planejador, não ao card.
4. Auditoria de zero incidente documentado de usuário Mathoms que mudou
   de regime com base em sinal do produto e teve resultado pior.

## §6 — Critério de aceite

Mergeada quando:

1. `IrpfPgblCapacidadeCard.tsx` Estado 2 renderiza a copy literal de §D3
   com lista sparse (categoria com valor zero ou ausente é omitida).
2. Testes Vitest cobrem:
   - Estado 2 com **todas** as categorias presentes (saúde, educação,
     INSS, pensão, dependentes, PGBL aportado).
   - Estado 2 com **nenhuma** categoria (lista omitida, copy explicativa
     do regime + ponteiro PGD/MIR ainda renderiza).
   - Estado 2 com **subset** (saúde + educação só) — sparse correto.
3. Variant continua `neutral`. Subtitle continua `"Não se aplica · {ano}"`
   sem sufixo direcional.
4. Disclaimer **não-escalonado** — apenas a frase "Não é recomendação"
   permanece restrita ao Estado 1 (ADR-189 §D4 preservado).
5. Nenhum hex literal de cor; uso de `var(--*)` + `<MonetaryValue/>`.
6. Pre-commit verde, Vitest verde, snapshot OpenAPI inalterado (sem
   mudança de payload).
7. ADR flipped `Proposto → Decidido (A12)` no commit-merge.
