---
id: ADR-220
type: adr
title: "Impacto estimado em sugestões IF — fluxo anual E patrimônio-alvo separados"
status: Proposto
phase: A12
date: "2026-05-15"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-097]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-200]]"
  - "[[ADR-202]]"
  - "[[ADR-208]]"
  - "[[ADR-212]]"
  - "[[ADR-217]]"
  - "[[ADR-219]]"
supersedes: []
superseded_by: []
aliases: ["ADR 220", "impacto-estimado-sugestoes-if", "patrimonio-alvo-regra-25x"]
tags:
  - area/relatorio
  - area/parecer
  - area/methodology
  - methodology/perini
  - phase/a12
  - status/proposto
  - type/adr
---

## Contexto

Parecer E6 ([[ADR-199]]) emite, em sugestão estratégica de Independência
Financeira, `impacto_estimado.valor_estimado_brl: 497052.0` para o
workspace 5@5.com (= despesa anual R$ 41,4k × 12). **Cálculo
matematicamente correto, contexto enganoso:** R$ 497k é o **fluxo
anual desejado** (renda passiva-alvo), não o **patrimônio
necessário** (R$ 12,4M = 25× anual, regra Perini canônica).

Risco de produto sério em fintech wealth:

- Cliente lê "R$ 497k" e pensa "preciso de meio milhão de patrimônio
  para IF" → subestima a meta por **25×**.
- Em produto fiduciário B2B2C com persona Perini/Cerbasi/AUVP
  ([[ADR-199]] §persona), confundir fluxo com estoque quebra confiança
  metodológica.
- Caveat textual no campo `caveat` é fácil de ignorar — cliente lê o
  número grande, não o disclaimer.

`ParecerMovimentoCard.tsx` exibe o `valor_estimado_brl` como hero do
card de sugestão, sem rótulo semântico distinguindo fluxo de estoque.

[[ADR-202]] (manifest declarativo do parecer) define o mapping `tema_canonico
↔ ancora`, mas não tipa o impacto. Esta ADR estende ADR-202 com tipagem
canônica de impacto + regra de obrigatoriedade para sugestões IF.

## Decisão

### D1 — Schema additivo (não breaking): `impacto_tipo`, `impacto_caveat`, `categoria_sugestao`

Schema de `sugestao` em [`config/schemas/parecer_planejador.schema.json`](../../config/schemas/parecer_planejador.schema.json)
bump menor (subschema `sugestao` versão `1.x → 1.(x+1)`), adicionando
campos **opcionais**:

```json
{
  "sugestao": {
    "tema_canonico": "if",
    "categoria_sugestao": "patrimonio_alvo",
    "titulo": "Acumular patrimônio-alvo de Independência Financeira",
    "impacto_estimado": {
      "tipo": "patrimonio_alvo",
      "valor_brl": "12426300.00",
      "valor_estimado_brl": "12426300.00",
      "caveat": "Calculado pela regra Perini 25× despesa anual essencial; reavaliar a cada ciclo conforme premissas econômicas vigentes ([[ADR-219]])."
    },
    "evidence_path": ["goals.if_meta", "fluxo_caixa.despesa_total"]
  }
}
```

**Campos novos opcionais:**

- `categoria_sugestao: ImpactoTipo` — campo explícito que define a
  natureza da sugestão (substitui parsing frágil de `evidence_path`).
- `impacto_estimado.tipo: ImpactoTipo` — natureza do impacto monetário.
  Pode diferir de `categoria_sugestao` (sugestão IF pode ter sugestão-irmã
  com tipo `fluxo_anual` complementar).
- `impacto_estimado.valor_brl: Money string` ([[ADR-090]]) — valor com
  rótulo semântico explícito. Coexiste com `valor_estimado_brl` legado
  durante janela de compat.

**Enum `ImpactoTipo`:**

| Código | Significado | Quando usar |
|---|---|---|
| `patrimonio_alvo` | Estoque-alvo (valor de patrimônio necessário) | Regra 25× IF, meta de classe, reserva-conforto |
| `fluxo_anual` | Fluxo anual desejado ou economizado | Renda passiva-alvo, despesa anual evitada |
| `economia_anual_irpf` | Economia anual em IR | PGBL, dedutíveis, planejamento sucessório |
| `gap_protecao` | Capital de seguro faltante | Cobertura vida/invalidez |
| `outro` | Sem tipagem específica ou não-monetário | Sugestões qualitativas |

Decisão (vs. alternativa "schema breaking obrigatório"): aditivo
preserva compatibilidade com artifacts E6 históricos
(`pipeline_artifacts`), evita força-bruta de migration e respeita o
volume baixo de runs históricos pré-A11/A12. Renderer trata `tipo:
undefined → "outro"` como degrade limpo.

### D2 — Regra de obrigatoriedade vive no **manifest check**, não no JSON Schema

Validação em duas camadas claras:

- **JSON Schema** (`config/schemas/parecer_planejador.schema.json`):
  permissivo. Aceita `categoria_sugestao` ausente, aceita `impacto_tipo`
  ausente. Hook `validate_dict` ([[ADR-212]]) em modo `warn` indefinidamente.
  Justificativa: parecer LLM é probabilístico — schema strict-rejeita
  pareceres pontualmente errados = produção frágil.
- **Manifest check** (`dev/check_parecer_manifest_in_sync.py`):
  rigoroso. Regra adicionada: "**toda sugestão com `tema_canonico` em
  {`if`, `independencia_financeira`} deve ter ≥1 sugestão associada com
  `impacto_estimado.tipo == 'patrimonio_alvo'`**". Falha CI = falha
  governance, não falha persistência.

Pattern já existe no projeto ([[ADR-200]]/[[ADR-202]] manifest check
para temas canônicos). Esta ADR adiciona uma regra a esse mesmo gate.

### D3 — `ParecerMovimentoCard` renderiza label semântico explícito

Card hoje exibe `valor_estimado_brl` como hero. Pós-ADR:

- `tipo: "patrimonio_alvo"` → label "**Patrimônio-alvo**" + `MonetaryValue`
  + microcopy "Estoque necessário para sustentar este movimento (regra
  metodológica aplicada)".
- `tipo: "fluxo_anual"` → label "**Renda anual desejada**" / "**Custo
  anual**" + microcopy adequada.
- `tipo: "economia_anual_irpf"` → label "**Economia anual em IR**".
- `tipo: "gap_protecao"` → label "**Capital de seguro faltante**".
- `tipo: "outro"` ou ausente → label "**Impacto estimado**" (comportamento
  legado preservado para artifacts antigos).

Renderer agrupa sugestões com mesmo `categoria_sugestao` num accordion
(ex.: as duas sugestões IF — fluxo + patrimônio — aparecem juntas).
[`ParecerMovimentoCard.tsx`](../../frontend/src/components/report/sections/SParecer/ParecerMovimentoCard.tsx)
recebe ajuste mínimo.

### D4 — LLM degrade: tipo inválido → `"outro"` + `needs_review=true`

Se LLM retorna `impacto_tipo` fora do enum (hallucination), service de
parse aplica fallback determinístico:

- `impacto_estimado.tipo = "outro"`
- Adiciona ao aggregate `needs_review: true` (mesmo padrão de
  [[ADR-081]] confidence < 0.7).
- Não retry em produção (caro, latência variável). Log warning
  estruturado em `mathoms.parecer.tipo_invalido` para drift watching.

Pydantic `Literal["patrimonio_alvo", "fluxo_anual",
"economia_anual_irpf", "gap_protecao", "outro"]` + `extra='forbid'`
([[ADR-097]]) na deserialização.

### D5 — Prompt do E6 atualizado para emitir tipagem em sugestões IF

`config/prompts/parecer_planejador.yaml` recebe instrução explícita:

- "Para sugestões de Independência Financeira (tema `if`), emitir **par
  de sugestões irmãs**: uma com `impacto_tipo: patrimonio_alvo` (cálculo
  pela regra Perini 25× ou metodologia escolhida) e uma com
  `impacto_tipo: fluxo_anual` (renda passiva mensal/anual-alvo)."
- Cita explicitamente a regra 25× e fontes Perini/Cerbasi/AUVP em
  sigilo metodológico ([[ADR-207]] §sigilo).

Decisão: regra fica no prompt (LLM emite ativamente), não em
post-processing determinístico (calcular 25× depois do parecer). Razão:
LLM precisa **decidir** se a regra 25× se aplica ou se há ressalva
(família com legacy patrimonial, FII sem despesa correlacionada etc.).
Lógica determinística podaria nuance.

### D6 — Goldens regeneram seletivamente

Não regenerar em massa. Adicionar **golden novo específico** para
sugestão IF tipada (workspace 5@5.com, sugestão estratégica IF deve ter
par patrimonio_alvo + fluxo_anual). Goldens antigos continuam válidos
em modo `warn` ("tipo ausente = ok"). Após estabilização, possível flip
strict em PR sucessor.

### D7 — Custo LLM aceito

Tokens marginais (~10 por sugestão para enum + caveat). Risco de
hallucination mitigado por Pydantic + fallback `"outro"` + needs_review.
Vale o eval cost para eliminar o viés de 25× — bloqueante de produto
fiduciário.

## Custos & Trade-offs

- **Schema additivo vs. breaking.** Additivo preserva runs históricos.
  Custo: dois campos coexistem (`valor_brl` novo, `valor_estimado_brl`
  legado) durante a janela. Limpeza opcional em PR sucessor — não
  bloqueante.
- **Manifest check vs. JSON Schema strict.** Permissivo no schema +
  rigoroso no check = parecer LLM sobrevive a edge case raros + CI
  bloqueia drift sistemático. Trade-off correto para input LLM.
- **Custo de regenerar prompt + golden + UX.** Esforço estimado: 1 PR
  com escopo amplo (schema + prompt + renderer + manifest check +
  golden). Aceito.
- **`categoria_sugestao` redundante com `tema_canonico`?** Não —
  `tema_canonico` é editorial (Perini/Cerbasi/AUVP), `categoria_sugestao`
  é semântica do impacto. Sugestão pode ser tema `if` mas categoria
  `gap_protecao` (proteção de patrimônio em formação). Mantidos
  ortogonais.

## Alternativas consideradas

- **Schema breaking obrigatório** — força migration de artifacts E6.
  Rejeitada: runs históricos eram experimentais (parecer é A11/A12);
  volume baixo justifica preservação.
- **Caveat só textual, sem tipagem** — perpetua viés de leitura
  (cliente vê número, ignora caveat). Rejeitada.
- **Parsing de `evidence_path` para identificar sugestão IF** — magia
  frágil; mudou path, regrediu silenciosamente. Rejeitada (senior-cto +
  data-engineer convergem).
- **Banir sugestão IF que não traga par patrimonio_alvo + fluxo_anual**
  (validação no schema strict) — bloqueia parecer LLM em edge case raro.
  Rejeitada — robustez de produção > rigor schema.
- **Calcular `patrimonio_alvo` em post-processing determinístico após
  parecer** — perde nuance editorial do LLM (regra 25× tem ressalvas).
  Rejeitada.

## Implementação

PR único, escopo:

- `config/schemas/parecer_planejador.schema.json` — adicionar campos
  opcionais; bump versão menor.
- `config/prompts/parecer_planejador.yaml` — atualizar com instrução
  de par patrimonio_alvo + fluxo_anual para tema IF.
- `pipeline/domain/services/parecer_parser.py` (ou similar) — Pydantic
  `Literal` para `ImpactoTipo` + fallback `"outro"` + needs_review.
- `dev/check_parecer_manifest_in_sync.py` — adicionar regra de
  obrigatoriedade tema IF.
- `frontend/src/components/report/sections/SParecer/ParecerMovimentoCard.tsx`
  — label semântico + accordion de sugestões irmãs.
- Golden novo em `tests/test_e6_golden_execution.py` (sugestão IF tipada
  para workspace 5@5.com).
- Telemetria: log warning estruturado para `tipo` inválido (drift watch).

**Dependências:**

- **Bloqueado por [[ADR-217]]** (componente score `diversificacao_auvp`
  alimenta um dos `valor_brl` calculáveis) e **[[ADR-219]]** (cálculo de
  `patrimonio_alvo` IF usa retorno esperado por classe da tabela
  versionada). Ordem: 219 → 218 → 217 → **220**.
- [[ADR-202]] (manifest declarativo) — esta ADR estende o check existente.
- [[ADR-208]] (gating free vs premium) — não afeta. Sugestão IF tipada é
  conteúdo, não gating.

## Critério de aceite

- [ ] Schema aceita `categoria_sugestao` e `impacto_estimado.tipo`
      opcionais.
- [ ] Manifest check falha CI se sugestão com `tema_canonico == "if"`
      não tem ≥1 par com `impacto_estimado.tipo == "patrimonio_alvo"`.
- [ ] LLM emite `patrimonio_alvo` + `fluxo_anual` em sugestão IF para
      workspace 5@5.com (golden novo).
- [ ] Renderer `ParecerMovimentoCard` mostra label semântico correto
      por tipo.
- [ ] Sugestões irmãs (mesma `categoria_sugestao`) aparecem agrupadas.
- [ ] Tipo inválido vindo do LLM cai para `"outro"` + sinaliza
      `needs_review`.
- [ ] Artifacts E6 antigos (sem campos novos) renderizam com label
      "Impacto estimado" legado, sem erro.
