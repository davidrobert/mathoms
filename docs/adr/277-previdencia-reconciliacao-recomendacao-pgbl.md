---
id: ADR-277
type: adr
title: "Previdência F1-O4: reconciliação da recomendação PGBL (não dedup de ativo)"
status: Decidido
phase: A21.l4
date: "2026-05-30"
relates_to:
  - "[[ADR-236]]"
  - "[[ADR-189]]"
  - "[[ADR-266]]"
  - "[[ADR-271]]"
  - "[[ADR-276]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 277"
  - "Reconciliação recomendação PGBL"
tags:
  - area/pipeline
  - status/proposto
  - type/adr
  - methodology/cerbasi
---

# ADR-277 — Previdência F1-O4: reconciliação da recomendação PGBL

**Status:** Decidido (Sprint A21, lane l4) • **Data:** 2026-05-30 • **Relaciona** [[ADR-236]] (base PGBL = renda tributável PF), [[ADR-189]] (capacidade/status PGBL), [[ADR-266]] (ano-base default), [[ADR-271]] (dedup investimentos), [[ADR-276]] (EntityDedupPolicy)

## Contexto — a lane mudou de natureza no co-design

A lane F1-O4 entrou no plano ([[PLAN-launch-trust]]) como **"dedup previdência PGBL/VGBL (ativo × dedução fiscal)"**: a hipótese era que o mesmo plano de previdência aparece duas vezes — uma como ativo (saldo no PL) e outra como dedução fiscal (aporte na base PGBL) — e que faltava reconciliar os dois eixos numa `EntityDedupPolicy` ([[ADR-276]]).

O co-design obrigatório (financial-planner + senior-cto) **invalidou a premissa** e reenquadrou a lane:

1. **Cross-axis ativo×dedução não existe.** Saldo de previdência é **estoque** (entra no PL via `investimentos_consolidados`); aporte dedutível é **fluxo** (entra na base PGBL). São dimensões distintas — o aporte **nunca** vira linha de ativo. Não há o que deduplicar entre eixos.
2. **Double-count de ativo cross-fonte é latente, não vivo.** O mesmo plano poderia, em tese, ser contado 2× se chegasse pelo informe de previdência **e** pelo bem G04 do IRPF. Mas o informe de previdência é **órfão**: nenhum consumidor injeta `saldo_31_12` em `investimentos_consolidados` (o `baseline_informe_merger` é do Wise/financeiro_pf, não da previdência). Shippar uma `EntityDedupPolicy` de ativo agora seria **dead code** — sem caminho de input que a exercite.
3. **O bug real e visível é a recomendação.** `PrevidenciaAnalyzer.analyze` recomenda o **teto PGBL cheio** (`renda_tributável × 12%`) sem subtrair o que já foi aportado no ano. Para quem já aportou, isso recomenda aportar de novo o que já está deduzido — orientação financeira incorreta, e a única das três hipóteses que afeta output que o usuário vê hoje.

Logo: **F1-O4 é uma reconciliação de recomendação, não um dedup de lista.** O runner `run_entity_dedup` ([[ADR-276]]) deduplica entries **dentro de uma lista** — não faz reconciliação cross-estrutura entre o IRPF e o fluxo. Aplicá-lo aqui seria a ferramenta errada.

## Decisão

Corrigir a recomendação PGBL ancorando-a na **capacidade dedutível restante do IRPF do titular** quando ela existe, e adiar o dedup de ativo até existir caminho de input.

### Três invariantes de domínio (financial-planner)

| # | Invariante | Estado nesta lane |
|---|---|---|
| INV-PREV-1 | Mesmo plano via informe **e** via G04 → **1 ativo** (valor = informe; informe vence declaração com guarda de 5% de magnitude, senão `needs_review`) | **Diferido** — `xfail(strict=True)`; sem input vivo, seria dead code |
| INV-PREV-2 | Aporte dedutível **nunca** vira linha de ativo (eixo fiscal ≠ eixo patrimonial) | **Assert** — `PrevidenciaAnalysis` não tem campo de saldo/ativo |
| INV-PREV-3 | Aporte **recomendado** ≤ capacidade restante; nunca o teto bruto quando já_aportado > 0 | **Shipped** — o fix desta lane |

### Boundary — capacidade tipada injetada (opção a)

`PrevidenciaAnalyzer.analyze` ganha um parâmetro opcional **value object frozen**, construído pelo adapter; a lógica de reconciliação vive **no serviço que a nomeia** (`PrevidenciaAnalyzer`), não no adapter (rejeitado (b)) nem num reconciliador novo (rejeitado (c) — prematuro):

```python
@dataclass(frozen=True)
class CapacidadePgblIRPF:
    restante_anual: Decimal        # Σ(tributável×12% − já_aportado), clamp ≥0
    renda_tributavel_anual: Decimal  # base p/ resolver alíquota marginal + display
    ano_base: int
    fonte: str                     # proveniência (ex.: "irpf_pgbl_capacidade")

class PrevidenciaAnalyzer:
    def analyze(self, fluxo, capacidade_irpf: CapacidadePgblIRPF | None = None) -> PrevidenciaAnalysis: ...
```

- **`capacidade_irpf` presente** → recomendação = `restante_anual` (`limite_pgbl_anual`, `aporte_mensal = restante/12`); alíquota marginal resolvida de `renda_tributavel_anual` pela tabela de `PrevidenciaConfig`. `restante = 0` (no teto, modelo simplificado, sem renda tributável) → recomenda 0 com nota explicativa. `fonte_recomendacao = "irpf_capacidade"`.
- **`capacidade_irpf` None** (sem IRPF do titular no workspace) → **fallback** ao cálculo-proxy atual (receita PJ anualizada × lucro presumido × 12%). `fonte_recomendacao = "proxy_receita_pj"`.

O adapter (`e5_analyzer_adapter`) já carrega `irpf_analyzer` (linha 518) e calcula previdência (linha 593) no mesmo escopo `analyze_via_store` — **sem novo I/O**. Ele ancora no `irpf_analyzer.ano_base_default()` ([[ADR-266]]); se `None`, passa `capacidade_irpf=None` (fallback). `restante_anual` vem de `pgbl_capacidade_dedutivel(ano)` ([[ADR-189]], já líquido de aportado e clamped ≥0).

### Proveniência

`PrevidenciaAnalysis` ganha `fonte_recomendacao: "irpf_capacidade" | "proxy_receita_pj"` (+ no `to_legacy_dict`), para o relatório/QA distinguir recomendação ancorada em declaração real vs. proxy.

### ISP ([[ADR-089]]/[[ADR-097]])

`PrevidenciaAnalyzer` recebe **só o value object**, nunca o `IRPFAnalyzer` inteiro. PGBL≠VGBL no eixo fiscal já é respeitado: `pgbl_capacidade_dedutivel` filtra `codigo_rfb == pgbl` (VGBL não é dedutível). Previdência **nunca** é "casal" — sempre 1 titular (≠ ADR-246/271).

## Escopo — mudança de comportamento intencional

A recomendação muda **apenas** para workspace com IRPF do titular contendo aporte PGBL já feito: antes recomendava o teto bruto, agora recomenda a capacidade restante. Sem IRPF, comportamento idêntico ao atual (fallback proxy). É correção de bug, não regressão.

## Consequências

**Positivas:** orientação PGBL deixa de recomendar aporte já feito; proveniência auditável; reconciliação centralizada no serviço de domínio; nenhum dead code (asset-dedup só entra quando houver input). **Negativas / trade-offs aceitos:** `CapacidadePgblIRPF` é uma 4ª micro-config tipada no adapter (custo pequeno de boilerplate, ganho de ISP). INV-PREV-1 fica `xfail` — débito explícito e rastreado, não esquecido.

## Alternativas consideradas

- **(b) Reconciliar no adapter:** rejeitado — empurra regra de domínio para a camada de orquestração; o serviço que nomeia a recomendação deve ownar a reconciliação.
- **(c) Novo `PrevidenciaReconciler`:** rejeitado — prematuro; uma única regra (subtrair já_aportado) não justifica serviço novo.
- **Shippar asset-dedup (INV-PREV-1) agora via `EntityDedupPolicy`:** rejeitado — dead code sem input vivo; `run_entity_dedup` é list-dedup, não reconciliação cross-fonte.
- **Estender `multi_year_baseline.json` com caso de previdência known-duplicate:** rejeitado nesta lane — E1.5c não deduplica previdência, então o caso seria um **falso-negativo permanente** que quebraria o gate `fn_rate` de l2. A cobertura de INV-PREV-1 vai como `xfail(strict)` unitário, não no golden de recall.

## Critério de aceite

1. `CapacidadePgblIRPF` (frozen) + `PrevidenciaAnalyzer.analyze(fluxo, capacidade_irpf=None)` + `fonte_recomendacao` em `PrevidenciaAnalysis`/`to_legacy_dict`.
2. INV-PREV-3: teste — com `capacidade_irpf` (já_aportado > 0), `aporte_mensal*12 ≤ restante_anual`; sem capacidade, fallback proxy idêntico ao atual.
3. INV-PREV-2: assert — `PrevidenciaAnalysis` não expõe saldo/ativo.
4. INV-PREV-1: `xfail(strict=True, reason="lane futura: input de ativo de previdência inexistente")`.
5. Adapter constrói/injeta o value object ancorado em `ano_base_default`; `None` → fallback. Sem novo I/O.
6. 22 unit tests previdência existentes verdes; INV-1..9 (l1) + `fn`/`fp` (l2) **sem alteração**.
