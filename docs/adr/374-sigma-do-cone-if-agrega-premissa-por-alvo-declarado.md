---
id: ADR-374
type: adr
title: "Sigma do cone de IF agrega premissa vigente pelos pesos do alvo declarado"
status: Proposto
phase: A40
date: "2026-08-10"
relates_to:
  - "[[ADR-219]]"
  - "[[ADR-237]]"
  - "[[ADR-360]]"
  - "[[ADR-361]]"
  - "[[ADR-369]]"
  - "[[ADR-373]]"
  - "[[ADR-193]]"
  - "[[ADR-141]]"
supersedes: []
superseded_by: []
aliases: ["ADR 374", "sigma do cone", "volatilidade da projeção de IF"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
  - phase/a40
---

# ADR-374 — Sigma do cone de IF agrega premissa vigente pelos pesos do alvo declarado

**Status:** Proposto (A40) • **Data:** 2026-08-10 • **Lane:** [[A40.l25]] •
**Co-design:** `financial-planner` (2026-08-10) • **Relaciona** [[ADR-219]] (a
tabela versionada que existe para isso), [[ADR-237]] (o cone e seu orçamento de
latência), [[ADR-360]] (seed + `mc_version` + nota one-shot), [[ADR-369]] (o alvo
da probabilidade), [[ADR-193]]/[[ADR-141]] (buckets e normalização de alocação).

## Contexto

O cone P10/P50/P90 da S7 é a superfície que comunica **incerteza** à família. Sua
largura vem de um `sigma` anual. Medido em 2026-08-10:

- `if_monte_carlo.py` declara `_SIGMA_FALLBACK_CODIGO = 0.11` como default de
  `IFMonteCarloConfig.sigma_anual`.
- `e5_analyzer_adapter.py:603` monta o config **sem passar `sigma_anual`** ⇒
  **todo run usa 0,11**.
- `rg -n "premissas_economicas" pipeline/domain/services/e5_analyzer_adapter.py`
  ⇒ **zero hits**. A tabela versionada da [[ADR-219]] D5 **não alimenta o MC**.

O payload já declara isso honestamente desde #1338 (`sigma_procedencia:
"fallback_codigo"`), e a legenda da S7 passou a qualificar em #1360. Esta ADR
decide o passo seguinte: **de onde o número vem quando existe premissa**.

**O defeito não é o nível — é a invariância.** 0,11 é plausível para uma carteira
balanceada. O problema é que uma família 80% Tesouro Selic e uma 90% ações
recebem **o mesmo cone**. Com os σ do seed vigente
(`backend/app/scripts/seed_economic_assumptions.py`, 0,5% caixa a 22% ações BR),
o intervalo real dos alvos declaráveis é **~2% a 18%**.

## Decisão

**D1 — Agregação: soma ponderada dos σ de classe** (`σ_p = Σ wᵢ σᵢ`).

O argumento **não** é "é mais precisa". É que `σ_p ≤ Σ wᵢ σᵢ` vale para
**qualquer** matriz de correlação (desigualdade triangular), logo a soma
ponderada é um **limite superior demonstrável** — afirmação verdadeira sem
conhecer o insumo que falta. É exatamente o que a [[ADR-219]] pede de uma
premissa auditável.

**D2 — Pesos: alocação-ALVO declarada, não a atual.** Dois motivos, e o primeiro
é de disponibilidade de dado, antes de metodologia:

1. A alocação **atual** não existe na granularidade da tabela de σ.
   `alocacao_alvo_deviation.py` colapsa renda fixa num bucket único
   (`rf_comparacao: "agregada"`), enquanto a tabela tem `rf_pos`, `rf_pre` e
   `rf_inflacao` separados. Pesar pela atual exigiria inventar o split
   pós/pré/IPCA+ — insumo que o produto não coleta. O `goal.alocacao_alvo.v2.inputs`
   tem as chaves que mapeiam 1:1 para `economic_asset_class`.
2. Coerência de método: o MC já assume 40 anos de aporte disciplinado, e o
   próprio relatório recomenda o rebalanceamento por aporte duas seções antes.
   Assumir simultaneamente que a família **nunca** rebalança contradiz a
   recomendação que ela acabou de ler. O risco prospectivo é o risco do **alvo**.

**Usar os `inputs` crus normalizados a 100, incluindo `caixa_pct`.** **Não**
reusar `_normalize_alvo`: a renormalização dele exclui caixa ([[ADR-141]] §Emenda
item 1) porque responde outra pergunta, e reusá-la apaga o único amortecedor de
volatilidade do pool — no alvo padrão dá 11,9% em vez de 10,8%.

**D3 — Sem alvo declarado ⇒ `fallback_codigo`.** Sem alvo não há vetor de pesos.
Consequência desejada: a parametrização só dispara para quem declarou alvo, que é
a população onde o número significa algo, e o raio de rollout encolhe.

**D4 — Classe com peso > 0 e sem σ vigente ⇒ abortar a agregação inteira.**
A agregação é definida **se e somente se** toda classe de peso positivo tem σ
vigente. Peso zero não entra na soma, então sua ausência é irrelevante — isto é
aritmética, não threshold.

As duas alternativas são piores e na direção errada:

- *Excluir e renormalizar* redistribui silenciosamente o peso da classe faltante
  sobre as que têm premissa, enviesando σ numa direção não declarada — e, se a
  faltante for a volátil, **para baixo**.
- *Fallback por classe* exige uma constante por classe: é a mentira de
  procedência que a [[A40.l25]] está deletando, com granularidade maior.

⚠️ **Isto contradiz a [[ADR-219]] D4**, que manda *"omite a classe ou usa default
conservador documentado"*. A contradição é resolvida por **emenda datada** lá, no
mesmo PR desta ADR — não por reinterpretação silenciosa.

**D5 — μ não se move.** `retorno_real_esperado` continua vindo de
`_cfg.retorno_real_anual_pct`. Ele alimenta **dois** números da mesma tela — o
prazo determinístico ([[ADR-373]]) e o centro do cone —, e trocar a fonte de um sem
o outro dessincroniza os dois. A divisão defensável: **μ é parâmetro do plano**
(a família escolhe com que retorno planeja); **σ é parâmetro de mercado** (ela não
escolhe). A fragilidade de μ tem destino próprio na [[A40.l25]] (grade 5/6/7%).

**D6 — Campos de auditoria no payload** (aditivos, schema em `warn`):
`sigma_agregacao` (a hipótese adotada), `sigma_base_pesos`
(`alocacao_alvo_declarada`), e `sigma_procedencia` passa a resolver
`workspace_override` quando **qualquer** classe contribuinte veio de override,
senão `global`.

**D7 — `mc_version` → `"6.0"`**, com entrada no ledger de
`if_recalibracao.py` (facetas `largura_cone` + `precisao_probabilidade`). O bump é
legítimo porque o **modelo** muda — não é mudança de exibição.

**D8 — A S7 declara quatro coisas** sobre o número (microcopy final é
`product-designer`): fonte + vigência, que os pesos são do **alvo** e não da
carteira atual, a hipótese de correlação em linguagem de cliente (*somamos o
risco das classes sem descontar diversificação; o cone sai mais largo que o
provável, nunca mais estreito*), e o fallback quando `fallback_codigo`.

## Alternativas consideradas

**A) Correlação zero** (`σ_p = √Σ wᵢ² σᵢ²`). **Refutada por medição**, não por
preferência: com os σ do seed vigente ela devolve ~11,3% para a carteira
agressiva — o **mesmo número da constante**. A diversificação-por-hipótese come
o risco exatamente onde o risco é real, e a premissa (correlação zero) é
**conhecidamente falsa**: Ibov e IFIX co-movem, e o próprio seed descreve
`acoes_intl` como hedgeado a BRL, removendo o diversificador cambial.

| Alvo declarado | D1 (`Σwσ`) | A (`√Σw²σ²`) | hoje |
|---|---|---|---|
| padrão | **10,8%** | 6,3% | 11% |
| conservador (60 rf_pos / 20 IPCA+ / 20 caixa) | **1,8%** | 1,2% | 11% |
| agressivo (45 BR / 25 intl / 20 FII / 10 rf_pos) | **17,6%** | 11,3% | 11% |

**B) Matriz de correlação explícita.** Correta e **fora do horizonte**: exige
série histórica por classe, e `market_rates` ([[ADR-135]]) é câmbio + indexadores
point-in-time, não série. É construir capacidade de dado de mercado — decisão
separada, com `build-vs-buy`.

**C) Haircut/piso calibrado sobre D1.** Rejeitada: o fator de haircut é
justamente o número que o produto não sustenta, e ele destrói a única virtude de
D1 — deixar de ser limite provável e virar estimativa pontual inventada. Se D1 é
conservadora demais, o remédio é dizer isso na copy, não calibrar às escuras.

**D) Manter `fallback_codigo` e fechar a lane.** É o estado de hoje, já honesto
quanto à procedência (#1338/#1360). Rejeitada porque preserva a **invariância**:
o cone continua não respondendo à carteira, que é a mensagem inteira da seção.

## Consequências

- **Muda número exibido para toda família com alvo declarado.** Coberto
  procedimentalmente pela §Nota one-shot da [[ADR-360]] (já em `main`, #1356) —
  a faceta `largura_cone` entra no ledger.
- **Ganho não-óbvio:** `_lognormal_params` subtrai ½σ²_log para preservar E[r],
  então σ carrega *drag de volatilidade* sobre o caminho central. Com σ=11% e
  r=6% o drag é ~0,54%/ano; com σ=3%, ~0,04%. A família conservadora é hoje
  penalizada por ~0,5%/ano de volatilidade que não tem, o que **afasta**
  `ano_if_cenario_central` do `prazo_anos_realista` determinístico exibido **na
  mesma seção**. Corrigir σ aproxima dois números que hoje se contradizem.
- **Direção da probabilidade não é monotônica** — σ move
  `prob_if_ate_prazo_declarado` para os dois lados conforme a folga do plano.
  Coincide com a [[ADR-360]] §Emenda (c), que já abandonou a monotonia.
- **Gaming: declarado, não gateado.** Pesar pelo alvo permite estreitar o próprio
  cone declarando alvo conservador que não se pratica. Gatear por `desvio_max_pct`
  faria a largura saltar descontinuamente ao cruzar o limiar e esconderia o número
  honesto justamente quando o alvo mais importa. A S3 já publica o desvio; a frase
  da S7 nomeia a base. As duas telas juntas expõem a lacuna.
- **`fora_alvo` (cripto/outros) tem peso zero por construção** — família com 30%
  em cripto recebe σ que ignora isso. A frase "assumimos convergência para o alvo
  declarado" é a declaração correta; o desvio aparece na S3.
- **Governança fica exposta.** A [[ADR-219]] §Custos exige revisão trimestral das
  premissas. Hoje σ obsoleto era inofensivo (ninguém o lia); depois disto ele move
  o cone de toda a frota. O CRUD do console (D7 da ADR-219, wave 2) sai de
  *nice-to-have* para pré-requisito de operação.
- **Sanidade de unidade:** o seed é **pct** (`22.000`) e o config é **decimal**
  (`0.11`). Um `/100` esquecido dá σ = 1080% e um cone absurdo que passa em todo
  teste de tipo.

## Critério de aceite

- Dois workspaces com patrimônio, aporte e meta **idênticos** e **alvos
  diferentes** produzem σ diferente. Hoje é impossível — é o teste que prova que
  a invariância morreu.
- Alvo padrão do fixture reproduz **10,8%**; conservador **1,8%**; agressivo
  **17,6%**. Derivados do seed vigente: se o seed mudar, o teste muda junto, e
  isso é sinal, não ruído.
- `has_alvo: false` ⇒ σ inalterado (0,11), `sigma_procedencia = "fallback_codigo"`,
  **e a ressalva da S7 aparece** (entregue em #1360).
- Classe com peso > 0 e `status: indisponivel` ⇒ `fallback_codigo`, com teste que
  exercita **o caminho de abort**, não só o resultado.
- Invariante de sanidade: `min(σᵢ | wᵢ>0) ≤ σ_agregado ≤ max(σᵢ | wᵢ>0)` — pega
  erro pct↔decimal de 100× e erro de normalização de pesos.
- σ com `caixa_pct` incluído dá **10,8%**, não 11,9%: teste que falha se alguém
  reusar `_normalize_alvo`.
- **Verificação renderizada** da S7 (§Débito de método da [[A40]]): a frase nomeia
  fonte, base de pesos e hipótese de correlação; a nota de recalibração aparece
  uma vez, com a faceta do cone.
- Nenhuma superfície diz *"sua carteira tem volatilidade de X%"* — nem a copy, nem
  o narrador, nem o parecer.

## Referências

- `pipeline/domain/services/if_monte_carlo.py` — `_SIGMA_FALLBACK_CODIGO`,
  `_lognormal_params` (o drag de ½σ²)
- `pipeline/domain/services/alocacao_alvo_deviation.py` — a granularidade dos
  buckets e a renormalização que **não** se reusa
- `backend/app/scripts/seed_economic_assumptions.py` — os σ vigentes, em pct
- `pipeline/domain/services/if_recalibracao.py` — o ledger que o bump alimenta
