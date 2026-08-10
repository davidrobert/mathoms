---
id: A40.l26
type: lane
title: "Cobertura do solver de prazo IF: aporte zero com retorno positivo converge, e o produto nunca mostrou"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1339
ship_date: "2026-08-08"
priority: P2
branch_slug: a40-l26-cobertura-do-solver-de-prazo-if
adrs:
  - "[[ADR-360]]"
  - "[[ADR-373]]"
depends_on: []
parallel_with:
  - "[[A40.l25]]"
tags:
  - type/lane
  - sprint/a40
  - status/shipped
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

~~Por isso o `motivo_prazo_indefinido` do #1158 diz "não projetável com as
premissas atuais" e **não** afirma "inviável" — a redação foi escolhida para não
mentir enquanto esta lane não roda.~~ **Superado pela [[ADR-373]] D2:** aquela
redação, escolhida para não mentir, mentia de outro jeito — "não projetável" é
falso justamente no caso comum. São dois motivos agora. As §seções abaixo do
Problema descrevem o estado **pós-lane**; esta descreve o que a motivou.

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
4. ~~**Interação com o cone:** com o ramo preenchido, `idade_meta_usada` volta a
   existir e `prob_if_ate_idade_meta` volta a ser emitida.~~ **Dissolvida pela
   [[ADR-369]] D2** (#1269, 2026-08-07): as duas chaves não existem mais e a
   probabilidade do cone **deixou de depender do solver determinístico** — ela
   mede o prazo que a família declarou (`prob_if_ate_prazo_declarado`), cujo
   alvo vem do Goal, não do `_solve_prazo`. Preencher os ramos faltantes muda o
   **prazo realista** exibido e a **folga** (`declarado − determinístico`), que é
   o que move a probabilidade — mas não ressuscita chave nenhuma nem reabre o
   escopo da [[A40.l25]] por esta via.

## Veredito do co-design (2026-08-08) — [[ADR-373]]

O `financial-planner` **derrubou metade da recomendação inicial** e trouxe três
fatos medidos que reenquadram a lane:

1. **`aporte == 0` nunca é declaração.** `goal.aporte_mensal.schema.json` exige
   `exclusiveMinimum: 0` e o DTO usa `gt=0` — a família não *consegue* declarar
   R$ 0. O zero é sempre ausência de insumo, nunca premissa.
2. **`r == 0` É declarável** (`goal.if.schema.json`: `minimum: 0`). A pergunta 3
   desta lane supunha config incompleta; é postura legítima ("poupo e não conto
   com o mercado"), e recusar a projeção linear seria o produto ser mais
   pessimista que o pessimismo declarado da família. **A hipótese `needs_review`
   caiu.**
3. **Ausência de retorno virava 0% declarado.** `_serialize_if_goal` emite a
   chave com `None`, então `.get(chave, 6.0)` nunca dispara o default e
   `_safe_float(None)` é `0.0`. Sem corrigir isso, preencher o ramo linear
   passaria a **projetar** sobre premissa que ninguém escolheu — a fabricação
   que o #1158 fechou, reaberta por outra porta.

E dois efeitos colaterais que a lane não previa: a S1 já emitia frase falsa
("Gap de R$ 87,0M será fechado por aportes disciplinados (R$ 0,00/mês = R$ 0,00
em N/D anos)"), e `CenariosConjugeAnalyzer._compute_prazo` era uma **segunda
cópia** da mesma fórmula — preencher um lado só faria S7 e Apêndice C
discordarem sobre a mesma família.

## Critério de aceite

- [x] Co-design com `financial-planner` registrado — [[ADR-373]] (`Decidido`),
      ID alocado na escrita.
- [x] **Preencheu** o ramo `r == 0 ∧ aporte > 0` (`n = (FV−PV)/PMT`), com teste
      de valor fixado; `PV == 0 ∧ aporte == 0` e `aporte == 0 ∧ r == 0`
      continuam ausentes.
- [x] **Não preencheu** o ramo `aporte == 0 ∧ r > 0`, e
      `motivo_prazo_indefinido` vira **dois** motivos: nenhum contém "não
      projetável", o de aporte-ausente nomeia o insumo, e só o de
      não-convergência afirma inviabilidade.
- [x] Ausência de retorno cai no default de 6%; `0` declarado permanece `0`.
- [x] `solve_prazo_anos` é fonte única — `CenariosConjugeAnalyzer` delega, com
      teste parametrizado provando que os dois call-sites concordam nos 5 ramos.
- [x] S1 (`waterfall_if`) não afirma que aportes fecham o gap sem aporte
      declarado, e a linha não vira muda (gap + premissa de retorno permanecem).
- [x] `scripts/analyze_finances.py::analyze_goals` deletado (81 linhas, a
      terceira cópia do `999`) — item 7 do §Deferimento da [[ADR-360]].
- [x] `docs/reference/FORMULAS.md` §Tempo até a meta documenta os 5 ramos;
      `rule-independencia-financeira` aponta para lá.
- [x] `tests/test_if_horizonte_ausente.py` continua válido **sem alteração**: a
      fixture do dogfood tem `aporte == 0 ∧ r > 0`, que é o ramo **retido**, não
      o preenchido — o pressuposto que ela guarda não mudou.
- [x] Snapshot `backend/tests/snapshots/dogfood_view_model.json` rebaselinado
      (`MATHOMS_UPDATE_SNAPSHOT=1`). O diff é de **uma linha** e foi conferido:
      só `motivo_prazo_indefinido` muda de string. `prazo_anos_realista`,
      `ano_if` e `idade_titular_if` seguem `null` — o dogfood cai no ramo
      **retido**, então o hero KPI e a stat "Ano projetado" não se movem.
- [ ] Verificação renderizada (navegador ou `pdftotext`) do S7 e do Apêndice C —
      **não feita**, ver §Deferimento.

## Deferimento (2026-08-08) — **transferido para a [[A40.l25]] em 2026-08-09**

> ⚠️ **Este § não é mais o dono do trabalho.** A lane fechou `shipped`, e lane
> `shipped` some do [`SPRINT_CURRENT`](../../../_MOC/_generated/SPRINT_CURRENT.md):
> deixar o item aqui o tornaria invisível para quem procura trabalho — o modo
> de falha que já prendeu 3 follow-ups na [[A40.l18]]. Os itens abaixo estão
> **escritos na [[A40.l25]] §Carga herdada**, que está `in_progress`. O texto
> segue aqui como registro do porquê do corte, não como fila.

Três itens saem desta lane por dependerem de copy nova e/ou do payload que a
l25 já toca. O `financial-planner` sancionou o corte explicitamente ("se a copy
não couber na lane, ship dos itens 1+2+motivos e §Deferimento datado — **nunca a
chave sem a frase**"):

1. **O piso a aporte zero exibido dentro do motivo.** As chaves
   `prazo_anos_sem_aporte_novo` / `ano_if_sem_aporte_novo` existiriam só para o
   narrador ler o número (~35 anos no dogfood) em vez de recalcular, e **nunca**
   mapeiam para `ano_if` nem para o hero KPI. Não entram sem a frase que nomeia
   a premissa e a alavanca — `$.goals` vai cru para o LLM do parecer, e chave
   sem frase vira "o prazo até a IF é de 35 anos".
2. **A decisão simétrica sobre o cone.** O Monte Carlo **já publica** sob
   PMT = 0 (`prob_if_ate_horizonte_simulado` = 0,58 no dogfood); hoje só o gate
   `if_pct < 15%` mantém o ano fora da tela. Fechar só o lado determinístico
   deixa o produto inconsistente na direção oposta.
3. **Verificação renderizada de S7 + Apêndice C** e a grade de sensibilidade da
   premissa de retorno (5% / 6% / 7% → 41,8 / 35,0 / 30,2 anos no perfil do
   dogfood).

**Condição de retomada:** com a **metade deferida da [[A40.l25]]**, não com a
lane inteira. Medido em 2026-08-08, depois de escrever este §: a l25 mergeou o
#1338 e **segue `in_progress`** — ela shipou só o que corrige *procedência* e
deferiu, pelo mesmo motivo, tudo que **muda número exibido**, porque isso
dispara bump de `mc_version` + a nota de recalibração da [[ADR-360]] §Nota
one-shot, cuja especificação depende de `product-designer`.

Os dois deferimentos são o **mesmo bloqueio**: número novo na tela sem o aviso
que a ADR-360 torna obrigatório. Agrupar não é só economia de cache do parecer —
é publicar a nota **uma vez**, cobrindo o cone e o prazo juntos. Retomar antes
disso entrega metade do aviso.

## Fora desta lane

- **Prosa genérica de "não projetável" fora do solver** —
  `perfil_familia_narrator`, `projecao_if_narrator` e o resumo do
  `cenarios_conjuge` repetem o enquadramento antigo. Não são **falsos** (dizem
  "com as premissas deste cenário"), então trocá-los é sweep de copy, não
  correção. Entra junto do item 1 do §Deferimento, que já reescreve a família
  de frases.
