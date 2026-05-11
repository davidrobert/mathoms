---
id: TRACK-pgbl-card-diagnostico
type: track
title: "Track PGBL: diagnóstico tipificado (4 estados) substitui métrica monovalor no card"
sprint: A11
status: ready
created_at: 2026-05-11
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
---

# Track PGBL — diagnóstico tipificado substitui métrica monovalor

> **Lane ID:** pgbl-card-diagnostico
> **Branch prefix:** `agent/pgbl-card-diagnostico/*`
> **ADR:** [[ADR-189]] (Proposto — flippa para Decidido no merge)
> **Depende de:** [[ADR-157]] (E1.6 IRPF Full Schema, já em produção),
> [[ADR-076]] (design tokens + codegen layout).
> **Conflita com:** qualquer track ativo que mexa em
> `config/report_layout.yaml` (seção `S_IRPF_OTIMIZACAO`),
> `frontend/src/types/irpf.ts`, `pipeline/domain/services/irpf_analyzer.py`,
> ou `scripts/e5_analyze.py::_e5_load_irpf_kpis`.
> **Supervisão:** **G0 (`financial-planner`)** já assinou copy literal
> em 2026-05-11 — copy congelada conforme [[ADR-189]] §4 + §6.1.
> Re-invocar **somente** se copy divergir do ADR durante implementação.
> **G4 (`product-designer`)** já revisou direção e copy (2026-05-11)
> — re-revisar se variantes/sizes divergirem. **G2 (`data-engineer`)**
> consultivo se decidir tornar contrato `irpf_kpis` versionado em vez
> de additive.

> **Objetivo (1 frase):** transformar o card `IrpfPgblCapacidadeCard`
> de métrica monovalor ambígua (`R$ 0,00` com dupla causa) em
> diagnóstico tipificado em 4 estados (capacidade disponível, modelo
> simplificado, no teto, sem renda tributável), cada um com copy e
> variante específicas, mantendo a posição "capacidade ≠ recomendação"
> de ADR-157.

---

## Por que esta lane

### Sintoma

Screenshot atual do estado-zero:

> **Capacidade PGBL**
> R$ 0,00
> *Sem capacidade dedutível adicional em 2024 — modelo simplificado
> **ou** aporte já no teto de 12% da renda tributável.*

A copy mistura duas situações financeiramente opostas (decisão
fiscal subótima vs decisão fiscal já maximizada) num único estado
visual. Usuário do simplificado lê "nada a fazer" quando há ação
pendente; usuário no teto perde reconhecimento de boa decisão.

### Diagnóstico

Revisão paralela `product-designer` + `financial-planner` (2026-05-11)
convergiu em:

1. Card é a **única peça** da seção `S_IRPF_OTIMIZACAO` (dois cards
   adjacentes — Dependentes, Dedutíveis — removidos em 2026-05).
   Esconder = seção evapora. Reescrever em estados explícitos é o
   único caminho viável.
2. `R$ 0,00` no estado simplificado viola §4.3 do COPY_GUIDELINES
   (zero monetário ≠ "não aplicável").
3. Variante `warn` no estado positivo (`capacidade > 0`) força framing
   de "problema" para métrica que não é problema.
4. Distinguir os 3 motivos do zero **não cruza** a linha de
   "recomendação fiscal" do ADR-157 — é transparência sobre por que
   o cálculo zerou, não prescrição.

ADR canônica: [[ADR-189]].

### O que falta

1. **Backend / pipeline:**
   - Enum `PgblStatus` (4 valores) em
     `pipeline/domain/services/irpf_analyzer.py`.
   - Método novo `IRPFAnalyzer.pgbl_status(ano) -> PgblStatus`
     (determinístico, sem threshold subjetivo).
   - Serialização: `scripts/e5_analyze.py::_e5_load_irpf_kpis`
     acrescenta 3 campos ao payload `irpf_kpis`:
     `pgbl_status`, `pgbl_aportado_brl`, `pgbl_teto_brl`.
2. **Frontend:**
   - `frontend/src/types/irpf.ts` reflete os 3 campos novos
     (TypeScript strict).
   - `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx`
     reescrito como switch sobre `pgbl_status`.
3. **Layout:**
   - `config/report_layout.yaml:371-374` muda `size: "full" →
     "half"` em `pgbl_capacidade`.
   - Codegen `python3 dev/codegen_report_layout.py` para sincronizar
     `frontend/src/generated/report-layout.ts` +
     `backend/app/generated/report_layout.py`.
4. **Testes:**
   - Pytest: 4 cenários para `pgbl_status` (`tests/test_irpf_full_schema_unit.py`
     ou novo `tests/test_irpf_analyzer_pgbl_status.py`).
   - Vitest: 4 cenários DOM para o card (atualizar
     `frontend/tests/components/IrpfSections.test.tsx`).
   - Golden de execução: regenerar
     `tests/test_e5_golden_execution.py` se o run canônico inclui
     `irpf_kpis` (depende de o fixture já ter IRPF Full).

---

## Regras inegociáveis

- **Não introduzir recomendação automática.** Estado 2
  (`modelo_simplificado`) **não** sugere "mude para completa" — só
  explica o mecanismo do regime. Copy literal de [[ADR-189]] §4 é
  fonte da verdade.
- **Disclaimer "Não é recomendação"** mantido literalmente no estado
  `capacidade_disponivel`, removido nos outros 3.
- **`R$ 0,00`** só pode ser usado quando é zero monetário real
  (estado `no_teto`). `modelo_simplificado` e `sem_renda_tributavel`
  usam `—`.
- **Não regredir** workspaces sem IRPF — `irpf_kpis` continua
  opcional; ausência do payload não quebra o relatório.
- **Não mexer** em `IRPFAnalyzer.pgbl_capacidade_dedutivel(ano)` —
  método canônico preservado, só **adiciona** `pgbl_status`.
- **Codegen primeiro, edit depois** —
  `frontend/src/generated/report-layout.ts` e
  `backend/app/generated/report_layout.py` são auto-gerados; mudança
  em YAML exige `dev/codegen_report_layout.py` antes de commitar.
- **G0 sign-off da copy** antes do merge — invocar
  `financial-planner` com copy literal dos 4 estados (sessão curta).

---

## Passos sugeridos

### S1 — Backend (`IRPFAnalyzer.pgbl_status`)

1. Em `pipeline/domain/services/irpf_analyzer.py`:
   - Adicionar `class PgblStatus(str, Enum)` com 4 valores conforme
     [[ADR-189]] §D1.
   - Implementar `pgbl_status(self, ano: int) -> PgblStatus` com
     regra de transição:
     - Toda declaração `modelo == simplificado` → `modelo_simplificado`
     - Renda tributável total = 0 → `sem_renda_tributavel`
     - Capacidade > 0 → `capacidade_disponivel`
     - Caso restante (cap = 0, com renda tributável, ao menos uma
       decl. completa) → `no_teto`
   - Adicionar `__all__` entry.
2. Tests: `tests/test_irpf_analyzer_pgbl_status.py` com 4 cenários
   determinísticos. Edge: casal misto (1 simpl. + 1 completa) — o
   ano vira `modelo_simplificado` só se **todas** as declarações
   são simplificado, senão classifica como completa.

### S2 — Serialização (`_e5_load_irpf_kpis`)

1. Em `scripts/e5_analyze.py::_e5_load_irpf_kpis`, acrescentar 3
   campos ao dict retornado:
   - `pgbl_status` (string, `.value` do enum)
   - `pgbl_aportado_brl` (Decimal string)
   - `pgbl_teto_brl` (Decimal string — `0,12 × tributável`, igual a 0
     no estado simplificado)
2. Aportado e teto vêm de helpers expostos pelo `IRPFAnalyzer` (novo
   método `pgbl_resumo(ano) -> tuple[Decimal, Decimal]` ou propriedades).
3. Atualizar `tests/test_llm_golden.py` se assertar shape exato do
   payload.

### S3 — Frontend types

1. `frontend/src/types/irpf.ts`: estender `IrpfKpis` com os 3 campos
   novos. Manter campos antigos.
2. Atualizar `parseDecimalString` consumidores se necessário.

### S4 — Card componente

1. `frontend/src/components/report/cards/IrpfPgblCapacidadeCard.tsx`
   reescrito:
   - Substituir lógica `semCapacidade` por switch sobre
     `kpis.pgbl_status`.
   - 4 ramos com copy literal de [[ADR-189]] §4.
   - Variantes: `info` / `neutral` / `feature` / `neutral`.
   - Hero: `<MonetaryValue/>` no estado disponível e no teto;
     `<span className="font-mono text-2xl text-[var(--surface-muted-foreground)]">—</span>`
     nos outros dois.
2. Atualizar/expandir `frontend/tests/components/IrpfSections.test.tsx`
   com 4 cenários DOM (texto da copy + presença de `—` ou valor
   monetário).

### S5 — Layout YAML + codegen

1. `config/report_layout.yaml:374` muda `size: "full" → "half"`.
2. Atualizar comentário de bloco da seção (linhas 357-364) para
   refletir [[ADR-189]].
3. Rodar `python3 dev/codegen_report_layout.py` e commitar
   `frontend/src/generated/report-layout.ts` +
   `backend/app/generated/report_layout.py` juntos.

### S6 — G0 sign-off + PR

1. Invocar `financial-planner` com prompt enxuto: "copy literal dos
   4 estados em [[ADR-189]] §4 — objeção?".
2. Iterar se houver objeção (1 rodada, conforme protocolo).
3. Abrir PR com título `feat(report): PGBL diagnóstico tipificado em
   4 estados (ADR-189)`.
4. Flippa ADR-189 para `status: Decidido (Sprint A11)` no commit do
   merge — convenção [[ADR-182]] §F2.

---

## Critério de aceite

Ver [[ADR-189]] §7. Resumo:

- `pgbl_status` cobre 4 estados com testes determinísticos.
- Payload `irpf_kpis` ganha 3 campos sem regressão de workspaces sem IRPF.
- Card renderiza copy literal de §4 da ADR para cada estado.
- `R$ 0,00` só aparece no estado `no_teto` (zero real).
- Disclaimer "Não é recomendação" só no estado `capacidade_disponivel`.
- Variante `info`/`feature`/`neutral` conforme tabela §D5.
- `size: "half"` em YAML; codegen sincronizado.
- G0 sign-off documentado no PR (comentário do `financial-planner`).
- CI verde, snapshot OpenAPI atualizado se aplicável.

---

## Não-objetivos

Lanes que **NÃO** entram neste track (anotar para backlog futuro):

1. **Threshold AUVP** (alíquota efetiva ≥ 22,5%, horizonte ≥ 10a) para
   modular variante — recomendação do `financial-planner`, requer ADR
   nova + decisão sobre proxy de horizonte (idade declarada?).
2. **Comparativo Simplificada vs Completa** — card de alto leverage
   sugerido pelo `financial-planner`, requer cálculo de contrafactual
   da declaração completa. Lane própria.
3. **Voltar cards "Dependentes" e "Dedutíveis Subutilizados"** — requer
   novos KPIs em `IRPFAnalyzer` (`dependentes_count`,
   `dedutiveis_por_categoria`).
4. **Reconciliar dois cards PGBL** (S7 `previdencia_pgbl` inferido de
   fluxo vs `S_IRPF_OTIMIZACAO` declarado em IRPF) — lane separada
   quando ambos forem para Premium.
