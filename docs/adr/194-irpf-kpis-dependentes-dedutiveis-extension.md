---
id: ADR-194
type: adr
title: "Extensão de `irpf_kpis` com `dependentes` e `dedutiveis_aplicados` (reativação de 2 cards em S_IRPF_OTIMIZACAO)"
status: Decidido
phase: "A12"
date: "2026-05-12"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-189]]"
  - "[[ADR-076]]"
  - "[[ADR-090]]"
  - "[[ADR-197]]"
  - "[[ADR-198]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 194"
  - "IRPF Dependentes Dedutíveis card revival"
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

A seção `S_IRPF_OTIMIZACAO` do relatório Premium hoje publica **apenas 1
card** (`IrpfPgblCapacidadeCard`, half, 4 estados — [[ADR-189]]). Dois
cards adjacentes — "Dependentes Declarados" e "Dedutíveis
Subutilizados" — foram removidos em 2026-05 por publicarem só prose
explicativa sem dados. O comentário canônico em
[config/report_layout.yaml:357-377](../../config/report_layout.yaml)
deixa o trigger de reativação explícito:

> "Voltam quando `IRPFAnalyzer` emitir `dependentes_count` +
> `dedutiveis_por_categoria`."

Os dados-fonte **já existem** no schema E1.6
([pipeline/llm/schemas/e16_irpf_full.py](../../pipeline/llm/schemas/e16_irpf_full.py)):

- `Dependente` (lista, `relacao: RelacaoDependente` enum, 14 categorias
  RFB canônicas).
- `PagamentoDedutivel` com `codigo_rfb: CodigoPagamentoDedutivel`
  (11 valores), `valor_dedutivel_brl` já truncado por teto pelo
  LLM extractor (`teto_aplicado: bool` per-item).

A lane é **puro consumo** dos dados já extraídos — sem novo prompt LLM,
sem migração DB, sem mudança em E1.6. Falta agregar e publicar no
payload `irpf_kpis` consumido pelo frontend.

## §2 — Decisão (G2 + G0 + G4 sign-off 2026-05-12)

### D1 — Granularidade `dependentes` (G2)

Emitir objeto estruturado, não `int` simples:

```python
{
  "count": int,
  "por_relacao": dict[str, int]  # RelacaoDependente.value → count
}
```

**Rationale (G2):** custo marginal trivial (enum já tipado em E1.6);
habilita copy informativo no card sem segunda chamada. Threshold de
elegibilidade por idade (24 anos para filho estudante, 65a para pai/mãe)
fica fora de escopo — exige normativa RFB anual versionada, lane
metodológica separada.

### D2 — Granularidade `dedutiveis_aplicados` (G2)

Objeto por categoria com utilizado + teto + status, **sparse** (omitir
categorias zeradas):

```python
{
  "saude":              {"utilizado_brl": "<decimal>", "teto_brl": None,        "teto_aplicado": False},
  "educacao":           {"utilizado_brl": "<decimal>", "teto_brl": "<decimal>", "teto_aplicado": <bool>},
  "pensao_alimenticia": {"utilizado_brl": "<decimal>", "teto_brl": None,        "teto_aplicado": False},
  "previdencia_oficial":{"utilizado_brl": "<decimal>", "teto_brl": None,        "teto_aplicado": False},
}
```

**Rationale (G2):** card precisa de gap (`teto_brl - utilizado_brl`);
sem teto na payload, frontend recalcula regra fiscal — anti-padrão.
`teto_brl: null` significa "sem teto legal fixo" (saúde sem teto; INSS
integral; pensão integral conforme decisão judicial). `teto_aplicado`
no agregado é `any(p.teto_aplicado for p in pagamentos_da_categoria)`.

### D3 — Categorias publicadas (G2 + G0)

**4 categorias acionáveis**: `saude`, `educacao`, `pensao_alimenticia`
(consolidando 3 variantes RFB), `previdencia_oficial`.

**Excluídas:**
- `pgbl` (36) — **já tem card próprio** em S_IRPF_OTIMIZACAO ([[ADR-189]]).
  Republicar criaria duas fontes de verdade para a mesma métrica.
- `livro_caixa` (60) — PJ equiparada, público restrito.
- `contribuicao_funpresp` (37) — servidor público federal, não-acionável
  para o ICP do Mathoms.
- `contribuicao_inss_empregado` (50) — bucketado em `previdencia_oficial`
  para a UI? Decisão final: **não**. INSS empregador (35) é canônico;
  empregado (50) é caso excepcional de empregada doméstica/diarista.
  Excluir para evitar confusão.
- `contribuicao_entidade_filantropica` (40) — anti-fraude raro,
  ruído na maioria dos workspaces.
- `outro` (99_outro) — fallback do extractor, semântica indefinida.

### D4 — Consolidação `pensao_alimenticia` (G2)

3 valores do enum (`pensao_alimenticia_judicial`,
`_acordo_extrajudicial`, `_escritura`) → 1 chave única `pensao_alimenticia`
no payload. Agregação no **serializer** (`scripts/e5_analyze.py`), não no
analyzer — analyzer permanece fiel ao schema E1.6.

### D5 — Teto de Educação

Único teto fixo em código: educação tem teto de **R$ 3.561,50 por
pessoa** (titular + cada dependente) — fonte: instrução normativa RFB
1.500/2014, valor congelado pela Receita há vários anos. Implementação:

```python
EDUCACAO_TETO_PER_PESSOA = Decimal("3561.50")
# teto_brl agregado = (dependentes_count + 1) × EDUCACAO_TETO_PER_PESSOA
```

**Débito técnico assumido:** valor hardcoded é defensável para
ano-base 2024 (exercício 2025). Quando a RFB atualizar via instrução
normativa, mover constante para `fiscal_parameters` table (ADR-135).
Lane futura — anotada como não-objetivo abaixo.

### D6 — Política sparse (G2)

Categoria com `utilizado_brl == 0` é **omitida** do payload
`dedutiveis_aplicados`. Coerente com `irpf_kpis: None` para workspace
sem IRPF (já em produção). UI degrada graciosa via guards.

### D7 — Política additive + ADR Proposto obrigatória (G2)

Schema `config/schemas/e5_analysis.schema.json:95` é permissivo
(`{"type": "object"}`) — additive sem breakar contract JSON. Mas tipo TS
strict (`IrpfKpis` em `frontend/src/types/irpf.ts`) **é** invariante
arquitetural. ADR-Proposto obrigatória antes do PR (política CLAUDE.md:
"ADR Proposto antes de PR P0/P1 com escopo arquitetural"). Flippa para
`Decidido (A12)` no commit do merge.

### D8 — UI/UX (G4 + G0)

**Hierarquia visual (G4):**

```
Linha 1:  [ PGBL Capacidade · half ]  [ Dependentes · half ]
Linha 2:  [ Dedutíveis Aplicados · full                    ]
```

**Variantes:**

| Card | Variante |
|---|---|
| `pgbl_capacidade` | resolvida internamente por status ([[ADR-189]]) |
| `irpf_dependentes_declarados` | `neutral` (factual seco) |
| `irpf_dedutiveis_aplicados` | **`info`** se há ≥ 1 categoria com `teto_brl != null AND utilizado < teto_brl`; **`neutral`** caso contrário |

**Composição do Card B** (G4): lista vertical com barra de progresso
para categorias com teto (apenas Educação, hoje); valor factual para
demais. Padrão alinhado ao S3 (Alocação Atual vs Alvo, `fa75444`).
Semantic HTML `<dl>` (não `<table>`), `role="progressbar"` com
`aria-valuenow/min/max/label`.

**Rebatismo do card de "Subutilizados" → "Aplicados por Categoria"
(senior-cto, mediação G0×G4):** "Subutilizados" implica prescrição
fiscal; só Educação tem teto fixo nesta iteração — chamar o card de
"Subutilizados" passa expectativa errada. "Aplicados por Categoria" é
fiel ao que o card mostra (valores aplicados; gap factual em Educação).

### D9 — Esconder vs mostrar-vazio (G0 + G4)

Esconder via guard no `IrpfOtimizacaoSection` quando:

- `dependentes.count == 0` → omitir Card "Dependentes Declarados".
- `dedutiveis_aplicados == {}` ou todas categorias com `utilizado_brl == 0`
  → omitir Card "Dedutíveis Aplicados".

PGBL não-omitido (sempre renderiza algum dos 4 estados quando há IRPF).

Se os 3 cards somem, a seção inteira degrada via `useIrpfKpis === null`.

### D10 — Copy literal (G0 sign-off 2026-05-12)

Copy literal aprovada está em §6.1 abaixo. Cards renderizam exatamente
a copy aprovada; alterações exigem re-sign-off G0.

## §3 — Alternativas avaliadas

### A. Não reativar (status quo)

**Pros:** zero esforço.
**Contras:** seção `S_IRPF_OTIMIZACAO` permanece com apenas 1 card,
desproporcionalmente pequena vs outras seções do Premium. Trigger
explícito de reativação já documentado no YAML. **Rejeitada.**

### B. Reativar como prose-only (volta ao estado pré-2026-05)

**Pros:** trivial.
**Contras:** repete o erro que motivou a remoção — Premium não pode
publicar "análise entra em próxima iteração". **Rejeitada.**

### C. Implementar com `dependentes_count: int` simples (G2 Opção A)

**Pros:** payload mínimo, codegen menor.
**Contras:** UI não pode mostrar "3 dependentes · 2 filhos + 1 pai"
sem segunda fonte. Custo marginal da Opção B é ~5 linhas no analyzer.
**Rejeitada em favor de B.**

### D. Calcular tetos no frontend (G2 Opção A para `dedutiveis_aplicados`)

**Pros:** payload menor.
**Contras:** regra fiscal vaza para TS; quando RFB atualizar teto,
drift garantido. **Rejeitada em favor de B.**

### E. Incluir PGBL na tabela `dedutiveis_aplicados` (G2 anterior)

**Pros:** completude.
**Contras:** já há card PGBL dedicado ([[ADR-189]]); duplicar confunde
fonte de verdade. **Rejeitada por G0 + G2.**

### F. Tabela `<table>` para Card "Dedutíveis" (G0 desenhou em markdown)

**Pros:** semântica nativa para dados tabulares.
**Contras:** densidade tipográfica perde vs lista vertical com
progressbar; padrão S3 (`fa75444`) estabeleceu lista-com-barra como
norma do design system para listas-com-medida. **Rejeitada por G4.**

## §4 — Consequências

### ✅ Ganhos

- Seção `S_IRPF_OTIMIZACAO` ganha 2 cards com **números reais** —
  remove constraint "1 card só" assinalado em [[ADR-189]] §B.
- Card "Dependentes" expõe composição familiar declarada à RFB —
  diagnóstico cru valorado por Cerbasi/AUVP, sem prescrição.
- Card "Dedutíveis Aplicados" expõe transparência por categoria —
  Educação ganha gap factual sem cruzar para "inclua mais despesas".
- Contrato `IrpfKpis` strict TS evita drift cliente↔servidor.

### ⚠️ Riscos

- **Risco de cruzar linha de recomendação fiscal.** Copy literal §6.1
  enfaticamente não-prescritiva; disclaimer-rodapé no Card "Dedutíveis"
  cobre subutilização. G0 sign-off congelado.
- **Diff de payload `irpf_kpis`.** Goldens de execução
  (`tests/test_e5_golden_execution.py`) precisam ser regenerados se
  o fixture canônico já tem IRPF Full.
- **Hardcode `EDUCACAO_TETO_PER_PESSOA`.** Defensável para ano-base
  2024; débito técnico anotado para migrar a `fiscal_parameters`
  table (ADR-135) quando RFB atualizar. TODO no código.
- **Composição com [[ADR-189]] (PGBL).** Card PGBL `half` na linha 1
  continua intacto — não regredir; teste de regressão
  `tests/test_irpf_analyzer_pgbl_status.py` é gate.

### 🔄 Reversibilidade

Alta. Para reverter:

1. Remover 2 cards do YAML (`config/report_layout.yaml`) +
   codegen.
2. Remover 2 chaves do payload `_e5_kpis_from_analyzer`.
3. Remover 2 métodos do `IRPFAnalyzer`.
4. Remover 2 componentes React + entradas em `IrpfKpis` TS.

Sem migração DB; sem mudança em E1.6 / prompt LLM; sem breaking de
contrato externo.

## §5 — Não-objetivos (esta ADR)

- **Não** introduzir lookup de tetos via `fiscal_parameters` table.
  Hardcode de Educação 2024 fica como débito ADR-135-pendente.
- **Não** introduzir threshold AUVP / Cerbasi para modular variantes
  (alíquota efetiva, horizonte, ICP de família).
- **Não** cruzar com `family_members` do workspace para inferir
  "dependentes elegíveis faltando". Correlação frágil hoje.
- **Não** recomendar mudança de regime, contratação de produto, ou
  qualquer ação fiscal. Mantida posição "capacidade ≠ recomendação"
  do [[ADR-157]].

## §6 — Copy canônica por card

### §6.1 — Card `irpf_dependentes_declarados` (variante `neutral`, size `half`)

Estado único de presença (`count > 0`):

> **Dependentes Declarados**
> *Composição declarada à RFB · {ano_base}*
> **{count}**
>
> {count_extenso} {dependente_singular_ou_plural} {declarado_singular_ou_plural} em {ano_base}: {lista_relacoes}.

**Variáveis de template:**

- `{count}` — número inteiro, font-mono hero.
- `{count_extenso}` — `1`→"Um", `2`→"Dois", `3`→"Três", `≥4`→cardinal numérico.
- `{dependente_singular_ou_plural}` — `1`→"dependente"; `>1`→"dependentes".
- `{declarado_singular_ou_plural}` — `1`→"declarado"; `>1`→"declarados".
- `{lista_relacoes}` — agregado por `RelacaoDependente`, ordem fixa de
  prioridade: `conjuge_companheiro` → `filho_filha` → `enteado_enteada`
  → `irmao_irma` → `neto_neta` → `pai_mae` → `avo` → `sogro_sogra`
  → `menor_pobre` → `tutelado` → `incapaz` → `bisavo` → `bisneto_bisneta`
  → `outro`. Formato: "cônjuge · 1, filho/filha · 2". Separador `, `;
  último item sem "e" (telegráfico).

**Labels traduzidos** (mapping `RelacaoDependente.value` → label pt-BR):

| Enum value | Label pt-BR |
|---|---|
| conjuge_companheiro | cônjuge |
| filho_filha | filho/filha |
| enteado_enteada | enteado/enteada |
| pai_mae | pai/mãe |
| avo | avô/avó |
| irmao_irma | irmão/irmã |
| bisavo | bisavô/bisavó |
| neto_neta | neto/neta |
| bisneto_bisneta | bisneto/bisneta |
| sogro_sogra | sogro/sogra |
| menor_pobre | menor pobre |
| tutelado | tutelado |
| incapaz | incapaz |
| outro | outro |

**Estado oculto:** `count == 0` OR payload ausente → card não renderiza.

### §6.2 — Card `irpf_dedutiveis_aplicados` (variante condicional, size `full`)

Layout: header + lista vertical (1 linha por categoria publicável) +
disclaimer-rodapé.

> **Dedutíveis Aplicados por Categoria**
> *Valores deduzidos do imposto · {ano_base}*
>
> {Para cada categoria publicável, em ordem fixa:}
>
> - **{categoria_label}** — Aplicado **R$ {utilizado}**.
>   {teto_render}
>   {status_chip}
>
> *Valores extraídos diretamente da declaração entregue à Receita. O "limite RFB" reflete o teto legal vigente em {ano_base} para a categoria; **não é recomendação** de incluir despesas adicionais — comprovantes precisam atender às regras de dedutibilidade (origem, vínculo com dependente, exclusividade do exercício).*

**Variáveis de template:**

- `{categoria_label}`:
  - `saude` → "Saúde"
  - `educacao` → "Educação"
  - `pensao_alimenticia` → "Pensão alimentícia"
  - `previdencia_oficial` → "Previdência oficial (INSS)"
- `{utilizado}` — `utilizado_brl` formatado pt-BR (`1.234,56`),
  font-mono tabular-nums.
- `{teto_render}`:
  - `teto_brl == null` → omitir linha de teto.
  - `teto_brl > 0` → "Limite RFB: R$ {teto_brl}." Para Educação, sufixo
    "(R$ 3.561,50/pessoa)" entre parênteses.
- `{status_chip}`:
  - `teto_brl == null` → chip "Sem teto legal" (variante `neutral`).
  - `teto_aplicado == true` OR `utilizado >= teto_brl` → chip "No teto"
    (variante `neutral`, **sem warn**).
  - `teto_brl > 0 AND utilizado < teto_brl` → chip "Espaço de R$ {teto_brl - utilizado}" (variante `info`).
- **Barra de progresso** renderizada apenas quando `teto_brl != null`:
  `<progress value={utilizado} max={teto_brl}>`, `aria-valuenow` em %,
  `aria-label="{categoria_label}: {pct}% do teto aplicado"`.

**Ordem fixa de linhas:** `saude` → `educacao` → `pensao_alimenticia`
→ `previdencia_oficial`. Linhas com `utilizado_brl == 0` ou ausentes
do payload são omitidas.

**Variante do card (resolução interna):**

- ≥ 1 linha com `teto_brl != null AND utilizado < teto_brl` → `info`.
- Demais casos com ≥ 1 linha publicável → `neutral`.
- Zero linhas publicáveis → card não renderiza.

**Disclaimer-rodapé** é renderizado sempre que o card renderiza
(cobre todas as linhas com teto; não há custo de redundância em
mostrar para linhas factuais).

### §6.3 — Sign-off G0 (`financial-planner` · 2026-05-12)

Copy literal §6.1 e §6.2 aprovada com as 3 restrições enforçadas no
mapeamento:

1. **Saúde nunca usa "subutilizado"** — chip "Sem teto legal" + valor
   factual; sem cálculo de gap.
2. **"No teto" não usa variante `warn`** — observação positiva, não
   alerta.
3. **Subutilização não prescreve** — copy se limita a "Espaço de R$ X";
   disclaimer-rodapé cobre a posição "comprovantes precisam atender
   regras RFB".

Posição AUVP/Cerbasi preservada: diagnóstico cru sem prescrição.

### §6.4 — Header condicional ao `pgbl_status` (amend 2026-05-12, pós-[[ADR-197]])

[[ADR-197]] expôs no card PGBL Estado 2 a lista de componentes elegíveis
no modelo completo. Em workspace com `pgbl_status == modelo_simplificado`
ou `sem_renda_tributavel`, o header literal de §6.2 ("Valores deduzidos
do imposto · {ano_base}") afirma efeito fiscal que não ocorreu — em
simplificado, o desconto fixo substitui qualquer dedução legal; sem
renda tributável, não há base de cálculo. Header passa a ser condicional:

| `pgbl_status` | Subtítulo |
|---|---|
| `capacidade_disponivel` | "Valores deduzidos do imposto · {ano_base}" (inalterado) |
| `no_teto` | "Valores deduzidos do imposto · {ano_base}" (inalterado) |
| `modelo_simplificado` | "Pagamentos elegíveis a dedução · {ano_base}" |
| `sem_renda_tributavel` | "Pagamentos elegíveis a dedução · {ano_base}" |

Regra de transição agregada espelha [[ADR-189]] §3 D1 — workspace com
qualquer declaração em modelo completo no ano resolve para o subtítulo
original. Título do card ("Dedutíveis Aplicados por Categoria"),
chips, barra de progresso e disclaimer-rodapé permanecem inalterados.

**Rationale da copy "Pagamentos elegíveis a dedução":** "Elegíveis" é o
termo técnico exato (espelha enum `PagamentoDedutivel` do schema E1.6),
factual sobre natureza da despesa e neutro sobre efeito no IR daquele
ano. Se o workspace mudar de regime no ano seguinte, os mesmos valores
continuam "elegíveis" — copy serve as duas trajetórias temporais.
Alternativas avaliadas: "potencial dedutibilidade" (rejeitada — tom
hipotético), "informadas à Receita" (rejeitada — perde a informação
relevante de que poderiam ter reduzido IR).

**Débito imediato (lane separada):** chip "Espaço de R$ X" também
implica gap acionável para reduzir IR — em simplificado é igualmente
falso. Tratar em ADR separada (variante condicional do chip por
`pgbl_status`); não bloqueia este amend.

**Update (2026-07-04):** débito encerrado por [[ADR-198]] (chip "Espaço"
condicional a `pgbl_status`).

**G0 sign-off (`financial-planner` · 2026-05-12 · amend):** APROVADO.
Posição AUVP/Cerbasi preservada — corrige afirmação factual incorreta
que estava furando "diagnóstico cru sem prescrição". A omissão original
no §6.2 (cobertura só do regime completa) foi falha de cobertura, não
decisão contrária.

## §7 — Critério de aceite

ADR flippa para `Decidido (Sprint A12)` quando:

1. `IRPFAnalyzer.dependentes_count(ano) -> dict[str, Any]` implementado
   conforme D1 com ≥ 4 testes determinísticos (count 0, 1, vários,
   relações distintas).
2. `IRPFAnalyzer.dedutiveis_aplicados(ano) -> dict[str, Any]` (renomeado
   de `dedutiveis_por_categoria` para refletir D8) implementado conforme
   D2 + D4 + D5 com ≥ 4 testes determinísticos (zero, com teto aplicado,
   educação com 0/1/N dependentes, mix sparse).
3. `_e5_kpis_from_analyzer` em `scripts/e5_analyze.py` emite 2 chaves
   novas no payload `irpf_kpis`.
4. `IrpfKpis` (TS) reflete os 2 KPIs novos com tipos exatos; guard
   `isIrpfKpis` valida shape.
5. `IrpfDependentesCard.tsx` + `IrpfDedutiveisAplicadosCard.tsx` com
   copy literal §6.1 + §6.2.
6. `IrpfOtimizacaoSection.tsx` renderiza os 3 cards com guards D9.
7. `config/report_layout.yaml` adiciona 2 cards; codegen rodado e
   commitado.
8. Vitest cobre presence/absence/variantes de cada card.
9. Regressão `tests/test_irpf_analyzer_pgbl_status.py` continua verde.
10. CI verde + merge squash em `main`.
