---
id: ADR-189
type: adr
title: "PGBL: diagnóstico tipificado (4 estados) substitui métrica monovalor no card de Otimização Tributária"
status: Decidido
phase: "A11"
date: "2026-05-11"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-076]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 189"
  - "PGBL diagnóstico"
  - "Card Capacidade PGBL refactor"
tags:
  - area/irpf
  - area/frontend
  - area/report
  - methodology/auvp
  - methodology/cerbasi
  - phase/a11
  - status/decidido
  - type/adr
---

## §1 — Contexto

O card `IrpfPgblCapacidadeCard` na seção `S_IRPF_OTIMIZACAO` do
relatório premium publica hoje uma única métrica monetária —
`pgbl_capacidade_dedutivel(ano)`, calculada como
`max(0, 0,12 × renda_tributavel - pgbl_aportado)` em
[pipeline/domain/services/irpf_analyzer.py:130-140](../../pipeline/domain/services/irpf_analyzer.py).
Quando essa métrica é zero, a copy atual diz:

> *"Sem capacidade dedutível adicional em 2024 — modelo simplificado
> **ou** aporte já no teto de 12% da renda tributável."*

Revisão paralela `product-designer` + `financial-planner` (2026-05-11)
identificou que essa frase mistura **duas situações financeiramente
opostas** num único estado visual:

1. **Modelo simplificado** → decisão fiscal corrente que **pode estar
   subótima** (Cerbasi puro: famílias com saúde/educação/dependentes/
   pensão erram de regime por inércia). Capacidade zero aqui é
   **artefato do regime**, não otimização real.
2. **No teto (modelo completa, aporte máximo)** → decisão fiscal
   **já otimizada** (boa notícia). Capacidade zero aqui é
   **eficiência fiscal**.

Há ainda um terceiro caso — `sem_renda_tributavel` (declarante apenas
com isentos/exclusiva) — onde a métrica não se aplica.

Apagar o sinal entre esses três casos transforma a **única seção
dedicada à otimização tributária** do relatório premium em ruído:
usuário do simplificado lê "nada a fazer" quando há ação pendente;
usuário no teto perde reconhecimento de boa decisão; usuário sem
renda tributável vê `R$ 0,00` como se fosse zero monetário real.

Adicionalmente:

- `R$ 0,00` em hero `font-mono text-2xl` viola §4.3 do
  `COPY_GUIDELINES` (zero monetário ≠ "métrica não aplicável" — caso
  simplificado e sem renda tributável deveriam render `—`).
- Variante `warn` no estado positivo (`capacidade > 0`) usa framing de
  "problema" para uma métrica que não é problema — só vira sinal sob
  condições AUVP (alíquota marginal ≥ 22,5%, horizonte ≥ 10a, tabela
  regressiva, taxa de adm baixa). Variante deveria ser `info`.

## §2 — Alternativas avaliadas

### A. Status quo (manter copy ambígua)

**Pros:** zero esforço.
**Contras:** ambos especialistas marcaram a copy como falha de produto
do Premium. Não considerada.

### B. Esconder card quando `capacidade ≤ 0`

**Pros:** elimina ruído visual.
**Contras:** a seção `S_IRPF_OTIMIZACAO` tem **só este card** hoje (dois
cards adjacentes — Dependentes, Dedutíveis — foram removidos em 2026-05
por publicar texto sem dados, ver comentário em
[config/report_layout.yaml:357-364](../../config/report_layout.yaml)).
Esconder = seção evapora; usuário Premium acha que comprou seção em
branco. Pior que ruído. Só ficaria viável quando os outros dois cards
voltarem com dados reais. **Rejeitada.**

### C. Transformar em CTA "Compare simplificado vs completa"

**Pros:** acionável.
**Contras:** cruza a linha de **recomendação fiscal** definida no
docstring G0 do componente e no ADR-157 (capacidade ≠ recomendação
automática). Exigiria calcular contrafactual da declaração completa —
fora de escopo, e a decisão regime envolve INSS + perfil previdenciário
que o produto ainda não coleta. **Rejeitada para esta lane;** pode
virar lane futura com sign-off financial-planner.

### D. Diagnóstico tipificado em 4 estados (recomendada)

**Pros:**
- Cada caso recebe copy + variante específica → seção entrega o que o
  título "Otimização Tributária" promete.
- **Não cruza a linha de recomendação** — é transparência sobre **por
  que a métrica zerou**, não prescrição de mudança de regime ou
  contratação de PGBL. ADR-157 não veda explicar o cálculo; veda
  recomendar.
- Determinístico: enum derivado de dados que já existem no
  `IRPFAnalyzer` (modelo, renda tributável, aporte). Sem mudança em
  E1.6 ou prompt LLM.
- Contrato `IRPFAnalyzer.pgbl_capacidade_dedutivel(ano) -> Decimal`
  **preservado intacto** — método novo `pgbl_status(ano) -> PgblStatus`
  é additive.

**Contras:**
- Adiciona 3 campos ao payload `irpf_kpis` (`pgbl_status`,
  `pgbl_aportado_brl`, `pgbl_teto_brl`) → requer codegen + snapshot
  OpenAPI (caso a entidade trafegue por endpoint tipado).
- Aumenta superfície de UI (1 componente → switch 4 ramos) com testes
  correspondentes.

## §3 — Decisão

Implementar a **alternativa D**:

### D1 — Novo método em `IRPFAnalyzer`

```python
class PgblStatus(str, Enum):
    capacidade_disponivel = "capacidade_disponivel"
    modelo_simplificado = "modelo_simplificado"
    no_teto = "no_teto"
    sem_renda_tributavel = "sem_renda_tributavel"

def pgbl_status(self, ano: int) -> PgblStatus: ...
```

Regra de transição (determinística, sem threshold subjetivo):

| Pré-condição (agregada sobre declarações do ano) | Estado |
|---|---|
| Toda declaração com `modelo == simplificado` | `modelo_simplificado` |
| Renda tributável total = 0 (todos só isentos/exclusiva) | `sem_renda_tributavel` |
| Capacidade calculada = 0 mas há renda tributável e ao menos uma decl. completa | `no_teto` |
| Capacidade calculada > 0 | `capacidade_disponivel` |

`pgbl_capacidade_dedutivel(ano)` **continua existindo** — chamado pela
UI no estado `capacidade_disponivel` e pelo serializador para campos
informativos.

### D2 — Contrato `IrpfKpis` (additive, não-breaking)

```typescript
// frontend/src/types/irpf.ts
pgbl_status: "capacidade_disponivel" | "modelo_simplificado"
            | "no_teto" | "sem_renda_tributavel";
pgbl_aportado_brl: string;  // Decimal string, total aportado no ano
pgbl_teto_brl: string;       // Decimal string, 12% × tributável (= 0 em simplificado)
```

Backend `pipeline/domain/services/irpf_serialization.py` (ou
`scripts/e5_analyze.py::_e5_load_irpf_kpis`) acrescenta os 3 campos
ao payload já emitido. Workspaces sem IRPF continuam ausentes.

### D3 — Reescrita do componente em 4 ramos

Cada ramo com copy + variante específicas (ver §4 abaixo). Card muda
de `size: "full"` para `size: "half"` em
[config/report_layout.yaml:374](../../config/report_layout.yaml) —
card monovalor não precisa de hero.

### D4 — Disclaimer "Não é recomendação" mantido **só** no estado
positivo (`capacidade_disponivel`)

Nos estados `modelo_simplificado` e `sem_renda_tributavel` o disclaimer
não cabe — não há recomendação a desclarar. Estado `no_teto` é
observação factual ("espaço fiscal bem utilizado") sem disclaimer.

### D5 — Variantes corretas por semântica

| Estado | Variante |
|---|---|
| `capacidade_disponivel` | `info` (era `warn` — corrigir framing) |
| `modelo_simplificado` | `neutral` |
| `no_teto` | `feature` (positivo discreto, sem gamificação) |
| `sem_renda_tributavel` | `neutral` |

## §4 — Copy canônica por estado

### Estado 1 — `capacidade_disponivel` (variante `info`)

> **Capacidade PGBL**
> *Espaço dedutível remanescente · {ano_base}*
> **R$ {capacidade}**
>
> Você aportou **R$ {aportado}** dos **R$ {teto}** dedutíveis em
> {ano_base} (12% da renda tributável). **Não é recomendação:**
> contratar PGBL exige análise de tabela regressiva vs. progressiva,
> horizonte de resgate, taxa de administração e contribuição ao INSS.

### Estado 2 — `modelo_simplificado` (variante `neutral`)

> **Capacidade PGBL**
> *Não se aplica · {ano_base}*
> **—**
>
> Você declarou pelo modelo simplificado em {ano_base} — neste regime,
> a Receita já aplica um desconto fixo sobre os rendimentos tributáveis
> (limitado a teto anual), e contribuições a PGBL não geram dedução
> adicional. A capacidade de 12% só vale no modelo completo.

### Estado 3 — `no_teto` (variante `feature`)

> **Capacidade PGBL**
> *Teto dedutível atingido · {ano_base}*
> **R$ 0,00**
>
> Você aportou **R$ {aportado}** em {ano_base}, esgotando os 12%
> dedutíveis da renda tributável (**R$ {teto}**). Não há capacidade
> dedutível remanescente em {ano_base}.

### Estado 4 — `sem_renda_tributavel` (variante `neutral`)

> **Capacidade PGBL**
> *Não se aplica · {ano_base}*
> **—**
>
> Em {ano_base}, sua declaração registrou apenas rendimentos isentos
> ou de tributação exclusiva. PGBL deduz da renda tributável — sem
> ela, a métrica não se aplica neste ano.

## §5 — Consequências

### ✅ Ganhos

- Seção `S_IRPF_OTIMIZACAO` deixa de publicar mensagem ambígua para
  ~70-80% dos usuários (modelo simplificado é majoritário em renda
  PF brasileira).
- Estado positivo (`capacidade_disponivel`) ganha contexto numérico
  (aportado / teto) — métrica passa a ser auto-explicativa.
- Estado `no_teto` reconhece boa decisão fiscal — Premium passa a
  validar quem faz certo, não só apontar gaps.
- Variante `info` no positivo corrige framing de "alerta" indevido.
- `R$ 0,00` deixa de ser usado para "não se aplica" → conformidade
  com COPY_GUIDELINES §4.3.

### ⚠️ Riscos

- **Risco de cruzar linha de recomendação fiscal.** Estado 2 ("vale
  comparar com completa") **não está incluído** nesta ADR justamente
  por isso — copy do estado simplificado se limita a explicar o
  mecanismo do regime. Sign-off final do `financial-planner` na copy
  literal antes do merge (G0).
- **Diff de payload `irpf_kpis`.** Goldens de execução
  (`tests/test_e5_golden_execution.py`) precisam ser regenerados
  quando os 3 campos novos forem serializados. Estado de `irpf_kpis` é
  opcional no contrato (workspace sem IRPF não emite) — sem regressão.
- **Codegen `report_layout.py` se size muda.** Mudança em YAML requer
  `python3 dev/codegen_report_layout.py` antes de commit (ADR-076).

### 🔄 Reversibilidade

Alta. Para reverter:
1. UI volta a usar `kpis.pgbl_capacidade_dedutivel_brl ≤ 0` como
   sinal de estado vazio (1 condição vs 4 estados).
2. Remover método `pgbl_status` e 3 campos do payload — `Decimal`
   monovalor continua disponível.

Sem migração DB; sem mudança em E1.6 / prompt LLM; sem breaking de
contrato externo.

## §6 — Não-objetivos (esta ADR)

- **Não** introduzir recomendação automática "contrate PGBL" /
  "mude de regime". Mantida a posição G0/ADR-157.
- **Não** introduzir threshold subjetivo (alíquota efetiva mínima,
  horizonte) para modular variante — pode virar ADR futura
  (alternativa M2 do `financial-planner` review).
- **Não** voltar os cards "Dependentes Declarados" e "Dedutíveis
  Subutilizados" removidos em 2026-05 — exigem dados que
  `IRPFAnalyzer` ainda não expõe (`dependentes_count`,
  `dedutiveis_por_categoria`).
- **Não** reconciliar com card `previdencia_pgbl` em S7 (fluxo PJ
  inferido vs IRPF declarado). Lane separada.

## §6.1 — Sign-off G0 (`financial-planner` · 2026-05-11)

Copy literal de §4 revisada por `financial-planner` em sessão paralela:

- Estado 1: APROVADO COM AJUSTE — lista de gates AUVP corrigida para
  "tabela regressiva vs. progressiva, horizonte de resgate, taxa de
  administração e contribuição ao INSS" (substitui "regime de
  tributação, contribuição ao INSS e perfil previdenciário" que era
  vago e não acionável).
- Estado 2: APROVADO COM AJUSTE — explicação do regime simplificado
  reescrita para precisão técnica ("desconto fixo sobre rendimentos
  tributáveis limitado a teto anual" em vez de "desconto padrão de
  20%" que sugere percentual sobre imposto); concordância gramatical
  corrigida ("modelo completo", não "modelo completa").
- Estado 3: APROVADO COM AJUSTE — "Espaço fiscal bem utilizado no
  ano" removido (paternalista/scorecard) e substituído por
  declarativo factual "Não há capacidade dedutível remanescente em
  {ano_base}".
- Estado 4: APROVADO sem ajuste.

Copy de §4 acima já reflete os 4 estados conforme G0. Restrições
inegociáveis preservadas: disclaimer só no Estado 1, `R$ 0,00` só no
Estado 3, neutralidade nos Estados 2 e 4, posição "capacidade ≠
recomendação" do ADR-157 mantida.

## §7 — Critério de aceite

Mergeada quando:

1. `IRPFAnalyzer.pgbl_status(ano) -> PgblStatus` implementado com
   testes unitários para os 4 estados (incluindo casal com 1 simpl. +
   1 completa, sem renda tributável, e edge de capacidade truncada
   por `max(0, ...)`).
2. Payload `irpf_kpis` serializa `pgbl_status` + `pgbl_aportado_brl`
   + `pgbl_teto_brl` em `scripts/e5_analyze.py`.
3. `IrpfKpis` (TS) reflete os 3 campos novos com tipos exatos.
4. `IrpfPgblCapacidadeCard` re-implementado como switch sobre
   `pgbl_status` com copy literal de §4.
5. `config/report_layout.yaml` muda `size: "full" → "half"` no card;
   codegen rodado e commitado.
6. Testes Vitest cobrem os 4 estados visualmente (estrutura DOM +
   variant).
7. `financial-planner` valida copy literal dos 4 estados antes do
   merge (G0).
8. CI verde + snapshot OpenAPI atualizado se houver endpoint que
   trafegue `irpf_kpis` tipado.
