---
id: TRACK-irpf-otimizacao-cards-revival
type: track
title: "Track IRPF Otimização — reativar cards Dependentes Declarados + Dedutíveis Subutilizados"
sprint: A12
status: consumed
created_at: 2026-05-12
consumed_at: 2026-05-12
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/consumed
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# Track IRPF Otimização — reativar 2 cards (`Dependentes Declarados`, `Dedutíveis Subutilizados`)

> **Lane ID:** irpf-otimizacao-cards-revival
> **Branch prefix:** `agent/irpf-otimizacao-cards-revival/*`
> **Depende de:** [[ADR-157]] (E1.6 IRPF Full Schema, em produção),
> [[ADR-189]] (PGBL diagnóstico tipificado — não regredir card PGBL),
> [[ADR-076]] (design tokens + codegen layout).
> **Conflita com:** qualquer track que mexa em
> `config/report_layout.yaml` (seção `S_IRPF_OTIMIZACAO`),
> `frontend/src/types/irpf.ts`,
> `pipeline/domain/services/irpf_analyzer.py`,
> ou `scripts/e5_analyze.py::_e5_load_irpf_kpis`.
> **Supervisão:** **G2 (`data-engineer`)** obrigatório — desenha
> granularidade do contrato `irpf_kpis` estendido.
> **G0 (`financial-planner`)** obrigatório — semântica do KPI
> "Dependentes Declarados" e "Dedutíveis Subutilizados" + copy literal
> dos 2 cards. **G4 (`product-designer`)** — hierarquia visual
> dos 3 cards na seção (PGBL ainda half + 2 novos).

> **Objetivo (1 frase):** reativar os cards "Dependentes Declarados" e
> "Dedutíveis Subutilizados" da seção `S_IRPF_OTIMIZACAO`, removidos em
> 2026-05 por serem prose-only, agora com **números reais** vindos de
> 2 novos KPIs em `IRPFAnalyzer` consumindo dados já extraídos por E1.6.

---

## Por que esta lane

### Sintoma

Seção `S_IRPF_OTIMIZACAO` hoje publica **apenas 1 card** (PGBL,
half-width). Anterior versão tinha 3 cards; 2 foram removidos em
2026-05 por publicarem só prose explicativa ("análise entra em próxima
iteração") — Premium não pode mostrar promessa de feature futura.

O comentário canônico em
[config/report_layout.yaml:357-364](../../../config/report_layout.yaml)
deixa o gatilho de reativação explícito:

> "Voltam quando `IRPFAnalyzer` emitir `dependentes_count` +
> `dedutiveis_por_categoria`."

### Diagnóstico

Dados-fonte **já existem** no schema E1.6
([pipeline/llm/schemas/e16_irpf_full.py](../../../pipeline/llm/schemas/e16_irpf_full.py)):

- `Dependente` (lista, com `relacao` RFB + `data_nascimento`).
- `PagamentoDedutivel` com `codigo_rfb` em 11 categorias canônicas
  (`saude`, `educacao`, `pensao_alimenticia_*`, `previdencia_oficial`,
  `pgbl`, etc.) e `valor_dedutivel_brl` já truncado por teto pelo
  E1.6 (campo `teto_aplicado: bool`).

Falta apenas **agregar e publicar** no payload `irpf_kpis` — sem
extrair dado novo, sem mexer no prompt LLM. Lane é puro consumo dos
dados já extraídos.

### O que falta

1. **Backend / pipeline:**
   - 2 métodos novos em
     [pipeline/domain/services/irpf_analyzer.py](../../../pipeline/domain/services/irpf_analyzer.py):
     - `dependentes_count(ano) -> int | dict` (granularidade decidida
       pelo co-design G2).
     - `dedutiveis_por_categoria(ano) -> dict[str, dict]` (categorias
       + utilizado + teto, granularidade decidida pelo co-design G2).
   - Serialização em
     [scripts/e5_analyze.py::_e5_kpis_from_analyzer](../../../scripts/e5_analyze.py)
     emitindo 2 chaves novas no payload `irpf_kpis`.
2. **Frontend:**
   - Estender `IrpfKpis` em
     [frontend/src/types/irpf.ts](../../../frontend/src/types/irpf.ts)
     com tipos exatos dos 2 KPIs novos (TS strict).
   - 2 cards novos em
     [frontend/src/components/report/cards/](../../../frontend/src/components/report/cards/):
     - `IrpfDependentesCard.tsx`
     - `IrpfDedutiveisSubutilizadosCard.tsx`
   - Integração em
     [IrpfOtimizacaoSection](../../../frontend/src/components/report/sections/IrpfOtimizacaoSection.tsx)
     com guards de ausência (esconder card se KPI ausente — workspace
     sem IRPF, ou IRPF sem essa categoria).
3. **Layout:**
   - `config/report_layout.yaml` — adicionar 2 cards à seção
     `S_IRPF_OTIMIZACAO`; atualizar o comentário de bloco
     (357-377) para refletir reativação.
   - Codegen `python3 dev/codegen_report_layout.py` para sincronizar
     `frontend/src/generated/report-layout.ts` +
     `backend/app/generated/report_layout.py`.
4. **Testes:**
   - Pytest: `tests/test_irpf_analyzer_dependentes_dedutiveis.py` com
     ≥ 4 cenários determinísticos cada (incl. casos null/empty).
   - Vitest: estender `frontend/tests/components/IrpfSections.test.tsx`
     com cenários de presence + absence + valores canônicos.
   - Regressão: rodar
     `tests/test_irpf_analyzer_pgbl_status.py` (não regredir card PGBL).

---

## Regras inegociáveis

- **Não criar novo prompt LLM** nem extrair dado novo. Lane é consumo
  dos dados já em `IRPFFullOutput`.
- **Não recomendar** automaticamente "adicione dependente X" ou "use o
  teto de saúde". Copy fica em **transparência/diagnóstico**,
  literalmente nos termos definidos pelo G0.
- **Esconder card** quando faltar dado (workspace sem IRPF inteiro, ou
  IRPF sem essa categoria) — degradação graciosa via guard no
  `IrpfOtimizacaoSection`. Card não-publicável ≠ card vazio.
- **Não regredir** o card PGBL (size half, 4 estados — [[ADR-189]]).
- **`irpf_kpis` é additive** — workspaces sem IRPF continuam ausentes;
  o campo permanece `Optional[dict]` em
  [pipeline/domain/services/e5_serialization.py](../../../pipeline/domain/services/e5_serialization.py).
- **G2 sign-off do contrato** antes da implementação (granularidade
  `dependentes_count` simples vs estruturado; granularidade
  `dedutiveis_por_categoria` flat vs aninhado; lista de categorias
  publicadas; representação de "teto não aplicável").
- **G0 sign-off da copy** antes do merge — copy literal dos 2 cards
  congelada no ADR (se ADR for emitida) ou em §6 deste track.
- **Codegen primeiro, edit depois** — YAML → codegen → commit junto.

---

## Co-design consolidado · 2026-05-12

Vereditos paralelos:

- **G2 (`data-engineer`):** contratos Opção B/B; 4 categorias publicadas (PGBL excluído por anti-duplicação); ADR Proposto obrigatória; sparse omit zerados; `teto_aplicado` no agregado = `any(...)`; pensão consolidada no serializer; rounding Decimal.quantize ROUND_HALF_UP.
- **G0 (`financial-planner`):** copy literal congelada (ver [[ADR-194]] §6.1, §6.2); card "Dependentes" `neutral` half sem disclaimer; card "Dedutíveis" rebatizado para "Aplicados por Categoria" (não-prescritivo), variante `info`/`neutral` condicional, disclaimer-rodapé único.
- **G4 (`product-designer`):** ordem PGBL+Dependentes na linha 1, Dedutíveis (full) na linha 2; lista vertical com barra de progresso (não tabela), padrão S3; A11y `<dl>` + `role="progressbar"`.

Divergência G0×G4 resolvida pelo senior-cto: variante condicional do
Card B (G0) mantida; a barra apenas reforça visualmente o sinal
semântico. ADR-194 documenta.

ADR canônica: [[ADR-194]] (Proposto · A12 · flippa para Decidido no merge).

## Decisões pendentes do co-design (HISTÓRICO — resolvidas em ADR-194)

### G2 (`data-engineer`) — contrato `irpf_kpis` estendido

1. **Granularidade `dependentes_count`:** apenas `int` ou
   `{ count: int, elegiveis_idade: int, por_relacao: dict }`?
   - Tradeoff: simples = trivial; estruturado = card pode mostrar
     "3 dependentes (2 cônjuge/filho, 1 pai/mãe)".
   - **Recomendação inicial do orquestrador:** intermediário —
     `{ count: int, por_relacao: {conjuge_companheiro: 1, filho_filha: 2} }`.
     `elegiveis_idade` exige threshold legal (24 anos para filho
     estudante) que escapa do escopo desta lane (precisa cruzar com
     RFB normativa); deixar para lane futura.
2. **Granularidade `dedutiveis_por_categoria`:**
   `{ saude: {utilizado_brl, teto_brl | null} }` ou `{ saude: "12345.67" }`?
   - Tradeoff: completo = pode mostrar bar/progress; flat = pode
     mostrar só lista de valores.
   - **Recomendação inicial:** completo —
     `{ saude: { utilizado_brl, teto_brl | null, teto_aplicado: bool } }`,
     onde `teto_brl: null` significa "sem teto definido em código"
     (educação tem teto fixo R$ 3.561,50; saúde sem teto; PGBL teto
     dinâmico 12%×renda — esses casos diferem semanticamente).
3. **Categorias publicadas:** todas as 11 do enum
   `CodigoPagamentoDedutivel` ou subset semanticamente útil para o
   card "Subutilizado"?
   - **Recomendação inicial:** subset por valor — `saude`, `educacao`,
     `pensao_alimenticia` (todas variantes consolidadas em 1 chave),
     `previdencia_oficial`, `pgbl`. Excluir `livro_caixa` (só PJ
     equiparada), `funpresp` (público específico), `inss_empregado`
     (não-acionável), `entidade_filantropica` (anti-fraude raro),
     `outro`.
4. **Versionamento `irpf_kpis`:** schema atual em
   `config/schemas/e5_analysis.schema.json:95` é `{"type": "object"}`
   (permissivo). Adicionar 2 campos é additive sem breakar contract.
   ADR necessária? **Recomendação:** não, additive sem ADR — mas G2
   decide se quer formalizar.

### G0 (`financial-planner`) — semântica + copy

1. **"Dependentes Declarados":**
   - Card mostra apenas o `count` como número factual, ou cruza com
     contexto (ex.: "1 dependente declarado · sem indício de
     dependente elegível faltando")?
   - **Recomendação inicial:** factual puro — "N dependentes
     declarados em {ano}" + lista de relações. Sem cruzar com
     "elegíveis faltando" porque o produto não tem dado para inferir
     família completa (Mathoms tem `family_members` mas a correlação
     é frágil); evitar paternalismo.
2. **"Dedutíveis Subutilizados":**
   - Mostrar subutilização **só** quando há teto e `utilizado < teto`?
   - Que categorias mencionar quando o teto é informativo (saúde sem
     teto = só publicar valor)?
   - **Recomendação inicial:** card mostra **todas** as categorias
     publicadas com valor não-zero (top 3-5 visualmente), destacando
     subutilização (`utilizado < teto`) e teto-atingido
     (`utilizado >= teto`). Saúde (sem teto) vira "Aplicado: R$ X"
     factual. Categorias zeradas omitidas (ruído).
3. **Copy literal** dos 2 cards — G0 escreve seguindo o rigor do
   [[ADR-189]] §6.1.

### G4 (`product-designer`) — UX

1. **Hierarquia visual** na seção `S_IRPF_OTIMIZACAO`:
   - 3 cards: PGBL (half, fixo por [[ADR-189]]) + Dependentes + Dedutíveis.
   - **Recomendação inicial:** PGBL `half` + Dependentes `half`
     (pareados na linha 1) + Dedutíveis `full` (linha 2, mais denso —
     tabela/lista de categorias).
2. **Variante por card:**
   - Dependentes: `info` (informativo) ou `neutral` (factual)?
   - Dedutíveis: `info` se houver subutilização? `feature` se tudo no
     teto? `neutral` default?
3. **Quando esconder card** por ausência de dado:
   - `dependentes_count == 0` → esconder card ou mostrar "Sem
     dependentes declarados"?
   - `dedutiveis_por_categoria == {}` ou só zerados → esconder card?
   - **Recomendação inicial:** esconder ambos se vazios (degradação
     graciosa, evita ruído).

---

## Passos sugeridos (sequência após co-design)

### S0 — Co-design (gate antes de codar)

1. Invocar G2 + G0 + G4 em paralelo (1 mensagem, 3 `Agent` calls)
   com brief enxuto + recomendações iniciais acima.
2. Consolidar vereditos em ADR (se G2 decidir) ou no §6 deste track.

### S1 — Backend (`IRPFAnalyzer` + serialização)

1. Adicionar `dependentes_count(ano)` e `dedutiveis_por_categoria(ano)`
   ao `IRPFAnalyzer` (assinatura definida em S0).
2. Pytest: `tests/test_irpf_analyzer_dependentes_dedutiveis.py`
   (≥ 4 cenários cada).
3. Estender `_e5_kpis_from_analyzer` com 2 chaves novas.

### S2 — Frontend types

1. `frontend/src/types/irpf.ts`: estender `IrpfKpis` + guard
   `isIrpfKpis` com novos campos. Tipos exatos (sem `any`).

### S3 — Cards componentes

1. Criar `IrpfDependentesCard.tsx` + `IrpfDedutiveisSubutilizadosCard.tsx`
   seguindo padrão do `IrpfPgblCapacidadeCard.tsx`.
2. Integrar em `IrpfOtimizacaoSection.tsx` com guards de ausência.
3. Vitest: estender `IrpfSections.test.tsx` com cenários de
   presence + absence + variantes.

### S4 — Layout YAML + codegen

1. `config/report_layout.yaml` — adicionar 2 cards à seção;
   atualizar comentário de bloco.
2. `python3 dev/codegen_report_layout.py` + commit dos generated.

### S5 — Gates locais + PR

1. `pre-commit run --all-files`
2. `pytest tests/test_irpf_*.py -q`
3. `pytest tests/test_irpf_analyzer_pgbl_status.py -q` (regressão)
4. `cd frontend && npm test -- --run`
5. PR único `feat(report): reativa cards Dependentes + Dedutíveis em S_IRPF_OTIMIZACAO`.

---

## Critério de aceite

1. G2 aprovou contrato `irpf_kpis` estendido.
2. G0 aprovou copy literal dos 2 cards.
3. G4 validou hierarquia visual (sizes + variantes + ordem).
4. `IRPFAnalyzer.dependentes_count(ano)` +
   `IRPFAnalyzer.dedutiveis_por_categoria(ano)` com testes
   determinísticos (≥ 4 cenários cada, edge null/empty incluídos).
5. `_e5_kpis_from_analyzer` serializa novos campos.
6. 2 cards React + `IrpfOtimizacaoSection` renderiza os 3 (PGBL + 2
   novos) com guards de ausência.
7. Vitest cobre presence + absence + valores canônicos.
8. YAML reativado, codegen sincronizado, comentário atualizado.
9. PR mergeado em `main` com CI verde.

---

## Não-objetivos

Lanes que **NÃO** entram neste track (anotar para backlog futuro):

1. **Comparativo Simplificada vs Completa** — lane separada, exige
   cálculo de contrafactual da declaração completa.
2. **Threshold AUVP** para PGBL (alíquota efetiva, horizonte) — lane
   separada, exige proxy de horizonte que produto ainda não coleta.
3. **Reconciliar S7 `previdencia_pgbl` (fluxo inferido) × IRPF
   declarado** — lane separada quando ambos forem para Premium.
4. **Dependentes elegíveis faltando** — exige cruzar `family_members`
   do workspace com declaração; correlação frágil hoje, escopo
   metodológico próprio.
