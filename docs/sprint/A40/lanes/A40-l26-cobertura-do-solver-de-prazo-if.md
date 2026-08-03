---
id: A40.l26
type: lane
title: "Cobertura do solver de prazo IF: aporte zero com retorno positivo converge, e o produto nunca mostrou"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l26-cobertura-do-solver-de-prazo-if
adrs:
  - "[[ADR-360]]"
depends_on: []
parallel_with:
  - "[[A40.l25]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/pipeline
  - area/financial-planning
---

# A40.l26 — `cobertura-do-solver-de-prazo-if`

> **Item 6 do §Deferimento da [[ADR-360]]**, levantado durante o #1158 (merge
> `7107b956`), que corrigiu a **fabricação** do prazo IF mas não a **cobertura**
> do solver. Distinta da [[A40.l25]]: a l25 trata da *honestidade de exibição* do
> cone estocástico (faixa, séries, `sigma`); esta trata do *cálculo determinístico*
> que não roda. Paralelas por construção — arquivos diferentes
> (`if_projector.py` vs `if_monte_carlo.py` + superfícies de S7).

## Problema

`IFProjector._solve_prazo` resolve `n` em `PV·(1+r)^n + PMT·((1+r)^n−1)/r = FV`
**apenas** no ramo `r > 0 and aporte_mensal > 0`. Todo o resto cai em ausência:

```python
if r > 0 and aporte_mensal > 0:
    ...  # forma fechada
return None   # ← era a sentinela 999 até o #1158
```

Isso empacota dois casos que não são o mesmo:

| Caso | Premissas | Verdade matemática | Hoje |
|---|---|---|---|
| Genuinamente inatingível | `r <= 0` **e** `aporte == 0`; ou `PV == 0` e `aporte == 0` | não converge | ausência ✅ |
| **Calculável, sem ramo** | `aporte == 0`, `r > 0` | `n = ln(FV/PV) / ln(1+r)` | ausência ❌ |
| **Calculável, sem ramo** | `r == 0`, `aporte > 0` | `n = (FV − PV) / PMT` | ausência ❌ |

No workspace dogfood (PV 13 M, meta 100 M, 6% real, aporte 0) o segundo caso dá
**~35 anos**. O relatório nunca mostrou esse número: antes exibia `999` → "IF aos
1040 anos" (fechado pelo #1158), agora exibe "—". Ausência é honesta, mas **o
produto está calado sobre um prazo que sabe calcular**.

Por isso o `motivo_prazo_indefinido` do #1158 diz "não projetável com as
premissas atuais" e **não** afirma "inviável" — a redação foi escolhida para não
mentir enquanto esta lane não roda.

## Por que P2 e fora das ondas

Ninguém lê número errado hoje: o #1158 trocou fabricação por ausência e o gate
`maximum: 120` no schema E5 impede a sentinela de voltar. O custo é **informação
retida**, não informação falsa — uma classe abaixo do resto da A40, que é sobre o
relatório mentir. Fora das ondas pelo mesmo motivo da [[A40.l25]]: não compartilha
arquivo com nenhuma onda e não depende de nenhuma.

## Co-design obrigatório antes de codar

Gatilho de `financial-planner` pela tabela do CLAUDE.md (fórmula + prazo + IF).
Preencher os ramos **muda o prazo IF reportado de workspaces reais** — não é
refactor. Perguntas para o especialista, não para o agente:

1. **Projetar IF com aporte zero é honesto?** A forma fechada assume patrimônio
   compondo sozinho até a meta. "IF em 35 anos sem aportar nada" pode ser leitura
   pior que a ausência — é um cenário que a metodologia talvez não queira
   endossar.
2. **Se sim, com que rótulo?** "Prazo se nada mudar" ≠ "prazo realista"; o campo
   hoje se chama `prazo_anos_realista`.
3. **O caso `r == 0`** é premissa legítima ou sinal de config incompleta que
   deveria virar `needs_review` em vez de projeção?
4. **Interação com o cone:** com o ramo preenchido, `idade_meta_usada` volta a
   existir e `prob_if_ate_idade_meta` volta a ser emitida — o que reabre o escopo
   da [[A40.l25]]. Ordenar as duas é decisão da lane que rodar primeiro.

## Critério de aceite

- [ ] Co-design com `financial-planner` registrado (emenda datada na [[ADR-360]]
      ou ADR nova conforme o veredito — **não** reservar ID antes de escrever).
- [ ] Se **preencher**: os dois ramos implementados, com teste fixando o valor do
      dogfood (~35 anos) e teste do caso genuinamente inatingível continuando
      ausente.
- [ ] Se **não preencher**: `motivo_prazo_indefinido` ganha redação que distingue
      os dois casos — o texto atual soa como limitação técnica e passaria a
      declarar escolha de metodologia.
- [ ] `tests/test_if_horizonte_ausente.py` atualizado: o
      `test_fixture_realmente_nao_converge` **assume** que o dogfood não converge
      e guarda esse pressuposto; se o ramo entrar, a fixture precisa de um
      workspace genuinamente inatingível.
- [ ] Snapshot `backend/tests/snapshots/dogfood_view_model.json` rebaselinado
      (`MATHOMS_UPDATE_SNAPSHOT=1`) — ver [[feedback-view-model-snapshot-rebaseline]].
- [ ] Verificação renderizada (navegador ou `pdftotext`) do S7 e do Apêndice C,
      pelo débito de método herdado da r3.

## Limpeza oportunista (não bloqueia)

`scripts/analyze_finances.py::analyze_goals` (~L1226) tem a **terceira** cópia do
`999` e é dead code — `rg 'analyze_goals\('` retorna só a definição. O #1158 não
tocou por ser remoção de código morto fora do escopo de um fix. Se esta lane
abrir o arquivo, delete junto. É o item 7 do §Deferimento da [[ADR-360]].
