---
id: CHG-2026-05-12-FEAT-IRPF-SIMPLIFICADO-COMPONENTES-PGD-MIR
type: changelog-entry
date: "2026-05-12"
sprint: A12
adrs:
  - "[[ADR-197]]"
prs: [234]
commits: ["6c31c9e"]
summary: |
  feat(frontend): Estado 2 (modelo_simplificado) do
  `IrpfPgblCapacidadeCard` ganha lista sparse de componentes elegíveis
  no modelo completo (saúde, educação, INSS, pensão, dependentes, PGBL
  aportado) + ponteiro factual ao programa PGD/MIR da Receita.
  Originalmente proposto como "card contrafactual com Δ R$"; co-design
  G0/G2/G4 vetou Δ literal e pivotou para exposição factual.
  Backend, schema e serializer intactos. ADR-197 Decidida (A12).
tags:
  - type/changelog-entry
  - sprint/a12
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# feat(frontend): Estado 2 PGBL expõe componentes elegíveis + PGD/MIR

Lane futura deferida em [[ADR-189]] §2 alt. C ("Compare simplificado vs
completa" — rejeitada com nota "pode virar lane futura com sign-off
financial-planner"). Esta é essa lane.

[[ADR-197]] **Decidida (A12)** no merge ([apps#234](https://github.com/davidrobert/mathoms/pull/234)).

## Contexto

Usuário em regime simplificado (~70-80% das declarações PF brasileiras,
estimativa G0) lia, no card PGBL Estado 2, apenas a explicação técnica
do regime — sem sinal sobre os gastos elegíveis declarados que não
compõem a base de cálculo deste regime. Seção "Otimização Tributária"
era informativa apenas para usuários no modelo completo.

## Co-design pré-ADR (2026-05-12)

Três sign-offs paralelos antes do PR:

- **G0 (financial-planner):** vetou alternativa A (Δ R$ literal entre
  IR pago no simplificado e IR hipotético na completa) — "isto é
  orientação fiscal por qualquer leitura; disclaimer não anula CTA
  implícito" — e alternativa B (qualitativo populacional "X% dos
  casos") — "modelo populacional que Mathoms não tem". Aprovou
  alternativa C (factual) com reformulação substancial: copy pivota
  para reconhecer que **o programa oficial da Receita (PGD/MIR) já
  compara automaticamente os dois modelos** durante o preenchimento e
  sugere o mais vantajoso. Mathoms expõe componentes + redireciona à
  autoridade competente; **não duplica** a comparação. Disclaimer
  **não-escalonado** ([[ADR-189]] §D4 preservado — disclaimer "Não é
  recomendação" continua restrito ao Estado 1). 4 critérios cumulativos
  registrados em §5.1 para reabertura da alternativa A.

- **G2 (data-engineer):** confirmou que pattern `FiscalParameters` VO
  injetado ([[ADR-097]] §D2) é o caminho técnico **se** lane futura
  calcular Δ. Para esta lane específica, **zero alteração de backend**
  é necessária — todos os campos (`dedutiveis_aplicados`,
  `dependentes`, `pgbl_aportado_brl`) já vivem em `irpf_kpis` via
  [[ADR-189]] + [[ADR-194]]. Levantou **bug crítico independente**:
  `fiscal_parameters.ir_brackets.deducao_brl_cents = 0` em todas as
  faixas seedadas (valores RFB corretos: 0/16944/38144/66277/89600
  cents); qualquer cálculo de IR sobre essa tabela ficaria
  silenciosamente errado em 15-30%. Não bloqueia esta ADR (que não
  calcula), mas é débito P0 para qualquer feature futura — tracker
  separado spawnado.

- **G4 (product-designer):** aprovou alternativa C variante `neutral`;
  vetou cor semântica negativa, ícone de alerta, seta direcional,
  palavras "perdidos/deixados na mesa", ranking entre categorias,
  badge "oportunidade", projeção temporal. Recomendou alternativa
  preferida: **fundir** com `IrpfDedutiveisAplicadosCard` via banner
  condicional ao topo. **Não adotada** nesta lane — o card Dedutíveis
  tem header "Valores deduzidos do imposto" que é factualmente
  incorreto em simplificado (nada foi deduzido), então adicionar
  banner ali aumentaria confusão existente; corrigir o header é
  débito separado spawnado.

## Entregue

- **ADR-197** (`docs/adr/197-*.md`) — `Proposto → Decidido (A12)`.
- **Card (frontend):**
  - `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx`
    — Estado 2 (`modelo_simplificado`) estendido com novo subcomponente
    `ComponentesElegiveisModeloCompleto` (lista sparse de saúde,
    educação, INSS, pensão, dependentes, PGBL aportado lidos do payload
    `irpf_kpis` já existente) + parágrafo factual sobre o PGD/MIR.
    Helpers `dedutiveisComponentes` + `buildComponentesElegiveis`
    extraídos para respeitar limite de 20 linhas/função
    (code-style-baseline).
- **Testes (Vitest):**
  - `frontend/tests/components/IrpfSections.test.tsx` — 8 testes novos
    sob `describe("Estado 2 — ADR-197 · A12 · componentes elegíveis +
    ponteiro PGD/MIR")`: lista completa, lista sparse, PGBL aportado em
    simplificado (caso [[ADR-196]]), lista omitida quando todos zero,
    ponteiro PGD/MIR sempre presente, variant `neutral` preservada
    mesmo com lista cheia, disclaimer ausente preservado, hero "—"
    preservado.

## Escopo preservado

- Backend `IRPFAnalyzer` **intacto** — todos os campos lidos pelo card
  já existem em `irpf_kpis` via [[ADR-189]] + [[ADR-194]].
- Serializer E5 (`scripts/e5_analyze.py::_e5_kpis_from_analyzer`)
  **intacto** — sem novo campo no payload.
- Schema `config/schemas/e5_analysis.schema.json` **intacto**.
- Goldens `tests/test_e5_golden_execution.py` **intactos**.
- OpenAPI snapshot **intacto**.
- Outros 3 estados (`capacidade_disponivel`, `no_teto`,
  `sem_renda_tributavel`) do `IrpfPgblCapacidadeCard` **inalterados**.

## Não-objetivos (esta ADR)

Ver [[ADR-197]] §5:

- Calcular ou publicar Δ de IR entre regimes (alt. A — veto G0).
- Publicar estatística populacional sem modelo sustentável (alt. B —
  veto G0).
- Criar 4º card na seção (não adotada para preservar densidade A4).
- Corrigir bug `fiscal_parameters.ir_brackets.deducao_brl_cents = 0` —
  débito G2 fora desta lane; tracker separado.
- Corrigir header enganoso do `IrpfDedutiveisAplicadosCard` em
  simplificado — tracker separado.
- URL clicável para PGD/MIR — referência textual apenas, mitiga link rot.

## Reabertura futura da alternativa A (Δ literal)

[[ADR-197]] §5.1 fixa 4 critérios cumulativos:

1. Confiança do schema E1.6 ≥ 0,85 sustentado em ≥ 90% das declarações
   reais processadas.
2. Regulamentação da Lei 15.270/2025 publicada e estabilizada em
   `fiscal_parameters` (campo `source` ≠ `STUB:*`).
3. Mathoms portar credencial CVM/CFC/CFP, ou entrar em B2B2C com
   planejador humano-no-loop.
4. Auditoria de zero incidente documentado de usuário que mudou de
   regime com base em sinal do produto e teve resultado pior.

## Débito identificado

- **Frontend visual snapshots (relatório nativo)** regrediu no PR #234
  por causa da nova lista de componentes no Estado 2 — esperado e
  correto. Job marcou failure não-blocking; gate principal "All
  checks green" passou. Regenerar baseline em lane follow-up
  (provavelmente bundle com próxima mudança em S_IRPF_OTIMIZACAO).
