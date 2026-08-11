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
**qualquer** matriz de correlação (desigualdade triangular em L²), logo a soma
ponderada é um **limite superior demonstrável** — afirmação verdadeira sem
conhecer o insumo que falta. É exatamente o que a [[ADR-219]] pede de uma
premissa auditável.

**Precondição, sem a qual o limite não é limite:** os pesos têm de **cobrir o
pool simulado**, isto é `Σ wᵢ = 1` sobre as classes que compõem
`patrimonio_investivel` (= `investivel_efetivo`). Peso que cobre parte do pool
produz um número **menor** que o limite real, e a afirmação de D8 (*"nunca mais
estreito"*) passa a ser falsa. É o que o D9 resolve para imóveis.

O limite **sobrevive à transformação log-normal**: `σ_log = √ln(1 + σ²/(1+r)²)`
é monótona crescente em σ, então majorar σ majora `σ_log`, que é o parâmetro
que o simulador de fato usa.

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
volatilidade do pool — no alvo padrão dá 11,94% em vez de 10,80%.

**O mapa de nomes é explícito porque 3 das 7 chaves NÃO derivam por sufixo.**
`key.removesuffix("_pct")` produz `rf_ipca`, `acoes_int` e `fiis`, que **não
existem** em `economic_asset_class` — as três cairiam como "classe sem σ
vigente", D4 abortaria e o resultado seria `fallback_codigo` em **100% dos
runs**, com a feature parecendo entregue:

| `goal.alocacao_alvo.v2.inputs` | `economic_asset_class.code` |
|---|---|
| `rf_pos_pct` | `rf_pos` |
| `rf_pre_pct` | `rf_pre` |
| `rf_ipca_pct` | **`rf_inflacao`** |
| `acoes_br_pct` | `acoes_br` |
| `acoes_int_pct` | **`acoes_intl`** |
| `fiis_pct` | **`fii`** |
| `caixa_pct` | `caixa` |

**D3 — Sem alvo declarado ⇒ `fallback_codigo`.** Sem alvo não há vetor de pesos.
Consequência desejada: a parametrização só dispara para quem declarou alvo, que é
a população onde o número significa algo, e o raio de rollout encolhe.

**D4 — Classe com peso > 0 e sem σ vigente ⇒ abortar a agregação inteira.**
A agregação é definida **se e somente se** toda classe de peso positivo tem σ
vigente. Peso zero não entra na soma, então sua ausência é irrelevante — isto é
aritmética, não threshold. **"Peso positivo" é medido nos pesos normalizados
FINAIS**, isto é depois da composição de D9.

**Sob o seed vigente, D4 é inalcançável por declaração** — as 7 chaves do alvo v2
mapeiam todas para classes com σ, e `imoveis_diretos` também tem. D4 só dispara
se um `effective_to` vencer sem sucessor, ou se um override vier malformado. Isso
está escrito para que o implementador não super-engenhe o caminho **nem** trate o
teste de abort como decorativo: ele é a guarda do CRUD do console (wave 2 da
[[ADR-219]] D7), que é justamente quem pode criar o estado.

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
(`alocacao_alvo_declarada` **ou** `alocacao_alvo_declarada_mais_imoveis_observados`
— ver D9; um valor único mentiria sobre base mista), e `sigma_procedencia` passa a
resolver `workspace_override` quando **qualquer** classe contribuinte veio de
override, senão `global`.

**D9 — Imóvel de renda no pool entra com peso OBSERVADO.** Quando
`imoveis_no_if = true` e `cat2_efetivo > 0`, `imoveis_diretos` entra com peso
`cat2_efetivo / investivel_efetivo`, e o alvo declarado **renormaliza sobre o
restante**.

Sem isto, D1 é **falso** para uma população nomeável e na direção proibida.
Medido, não inferido: `patrimonio_calculator.py:194` faz
`investivel_efetivo = investivel_financeiro + cat2_efetivo`, e
`e5_analyzer_adapter.py:602` passa esse total ao MC — o imóvel **está** no pool.
Mas `goal.alocacao_alvo.v2.schema.json` tem `additionalProperties: false` e
**nenhuma chave de imóvel**: o alvo é estruturalmente incapaz de descrever a
classe. Pool 60% financeiro / 40% imóvel de renda, alvo conservador:

| | σ |
|---|---|
| o que D1 publicaria sem D9 | **1,80%** |
| limite real com o pool coberto (`0,6·1,80 + 0,4·10,00`) | **5,08%** |

Cone **2,8× mais estreito** que o limite, por ausência de dado — e a falha
concentra-se em *alvo conservador + imóvel de renda*, que é o ICP nomeado no
produto (aluguel + carteira defensiva), não um edge case.

**Peso observado não é remendo, é o que a metodologia manda.** D2 justifica pesos
do alvo porque a família rebalanceia **por aporte**; um prédio não se rebalanceia
por aporte. E a [[ADR-223]] exige signal afirmativo de que o capital está
comprometido com a IF para o toggle ligar. Logo, para imóveis, **o peso observado
É o peso prospectivo** — a ADR-374 honra o que o toggle já decidiu em vez de
reabrir a divergência de método.

**Isto NÃO se aplica a `fora_alvo` (cripto/outros)**, e a distinção importa
porque um implementador aplicaria a mesma regra aos dois e erraria um: cripto
**é** rebalanceável por venda, então "assumimos convergência para o alvo
declarado" é declaração defensável — e cripto **não tem σ no seed** ([[ADR-219]]
D2 adia explicitamente), então nem haveria número para usar.

**D10 — σ é resolvido do SNAPSHOT, com `as_of` = data de referência do run.**
Honra a caixa **aberta** do §Critério de aceite da [[ADR-219]] (*"Monte Carlo S7
lê do snapshot do payload, não do DB direto durante o cálculo — preserva
determinismo de re-run"*), que a ordem de chamada atual **não** satisfaz: em
`scripts/analyze_finances.py`, `_e5_build_premissas_economicas(ctx)` roda na linha
**2599** — depois de o adapter já ter executado o MC —, e usa `as_of=TODAY`
(linha 2448), enquanto o MC usa `ano_base=self._reference_date.year`. **Duas bases
de tempo.** Sem esta decisão, re-run do mesmo run em data de calendário posterior
a uma revisão de premissa produz cone diferente — exatamente a falha que a
[[ADR-219]] D5 existe para prevenir, e que o determinismo da [[ADR-360]] **não**
cobre (lá o determinismo é do seed, não do config).

Implementação: reordenar para o snapshot preceder o adapter, ou injetar o resolver
no adapter. `TODAY` não é aceitável como `as_of`.

**D7 — `mc_version` → `"6.0"`**, com entrada no ledger de
`if_recalibracao.py` (facetas `largura_cone` + `precisao_probabilidade`). O bump é
legítimo porque o **modelo** muda — não é mudança de exibição.

**D8 — A S7 declara CINCO coisas** sobre o número (microcopy final é
`product-designer`): fonte + vigência; que os pesos são do **alvo** e não da
carteira atual; a hipótese de correlação em linguagem de cliente (*somamos o
risco das classes sem descontar diversificação; o cone sai mais largo que o
provável, nunca mais estreito*); o fallback quando `fallback_codigo`; e —
**quinta, acrescentada pela revisão** — que **a largura é calibrada à alocação-
alvo, mas o centro é a premissa do plano, não da alocação**.

Sem a quinta, a seção publica um par incoerente. Ver §Consequências.

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
- ⚠️ **Incoerência μ/σ — a consequência mais grave, achada na revisão.** Depois
  de D1 a **largura** reflete a alocação declarada e o **centro não**. No alvo
  conservador (60 `rf_pos` / 20 IPCA+ / 20 caixa) σ cai para 1,80% enquanto μ
  continua sendo a premissa do plano (tipicamente 6%); o μ **implícito** daquela
  alocação, pelos `retorno_real_esperado_pct_anual` do mesmo seed, é
  `0,6·3,5 + 0,2·5,5 + 0,2·0,0 = **3,2%**`. Publica-se **cone estreito em torno
  de um centro que a alocação declarada não entrega** — e estreiteza comunica
  confiança, que é o pior quadrante num relatório fiduciário. É **pior que hoje**
  (cone largo sobre o mesmo centro). O caso patológico é declarável: todo `_pct`
  do schema aceita `maximum: 100`, então `caixa_pct: 100` dá σ = 0,5% prometendo
  6% real sobre 100% de caixa. Mitigação nesta ADR: a **quinta** declaração de
  D8. Insumo recomendado: emitir `retorno_implicito_do_alvo_pct` pelos mesmos
  rows (zero I/O extra), **declarado e não gateado** — mesma postura de D2 sobre
  gaming, e insumo pronto para a grade 5/6/7% da [[A40.l25]].
- **A faixa declarável é 0,5% a 22%, não "~2% a 18%"** — este último é o intervalo
  dos três exemplos, e a imprecisão escondia justamente o pior caso.
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

## Deferimento datado — 2026-08-10

**Revisão de premissa move o cone da frota SEM bump de `mc_version`, portanto
invisível à nota de recalibração.** O gatilho da nota é diff sobre o ledger de
`mc_version` ([[ADR-360]] §Emenda (a)). Depois desta ADR, σ passa a vir de uma
tabela com **revisão trimestral obrigatória** ([[ADR-219]] §Custos): no trimestre
seguinte o operador ajusta `acoes_br` de 22% para 19% e o cone de toda família com
alvo declarado muda **sem nota e sem versão**. Hoje isso é impossível — mudar σ
exige deploy, e deploy bumparia a versão.

Pior instância: o CRUD da wave 2 permite setar `effective_to`. Uma linha que vence
sem sucessor derruba a frota para `fallback_codigo` via D4 — a família conservadora
salta de 1,80% para 11% (**6×**) sem aviso nenhum.

**Dono:** [[A40.l25]]. **Condição de retomada:** estender o gatilho do ledger em
`if_recalibracao.py` para considerar também diff de
`premissas_economicas.classes[].effective_from` entre os dois relatórios do par —
o insumo já existe (`load_snapshot_pair` devolve o `content_json` dos dois, e o
`effective_from` está no payload). **Não fechar o passo 3 sem isto decidido:**
publicar σ parametrizado com a nota cega a revisão de premissa troca um silêncio
por outro.

Também deferido, mais barato: entrada da fórmula em `FORMULAS.md` /
`docs/reference/rules/` (a regra é de domínio, [[ADR-143]]);
`sigma_anual_pct` chega como `str` no snapshot
(`economic_assumptions_snapshot.py`), então a conversão é `str → Decimal`, não só
pct→decimal; e a prosa de §Contexto da [[ADR-237]] §33 (*"10 000 simulações …
`sigma_anual=0.11`"*) tem dois números hoje falsos — precedente do repo é não
emendar prosa descritiva de ADR antiga.

## O que esta ADR fecha em outras ADRs

- **[[ADR-237]] §E** e **[[ADR-360]] §Deferimento item 2** pedem *"σ por perfil de
  risco, depende de campo novo em `goals` e UX de perfil"*. Esta ADR **fecha os
  dois**, por rota diferente da prevista: **zero campo novo, zero UX** — reusa o
  alvo v2 que já existe. Sem este registro, um auditor de deferimentos encontra
  dois ponteiros vivos para decisão já tomada, com enquadramento que a decisão
  rejeitou.
- **A recomendação anterior de 14%** (constante global única, [[ADR-237]] §E) é
  **superada, não revertida**. Lido isolado, "10,8% no alvo padrão" parece que o
  cone da família modal **encolheu** vs. os 11% de hoje. Não é: 14% era uma
  constante para todos; 10,8%/17,6% é parametrização que **encaixota** os 14%
  dentro da faixa declarável.

## Critério de aceite

- Dois workspaces com patrimônio, aporte e meta **idênticos** e **alvos
  diferentes** produzem σ diferente. Hoje é impossível — é o teste que prova que
  a invariância morreu.
- Alvo padrão do fixture reproduz **10,80%**; conservador **1,80%**; agressivo
  **17,55%**. Derivados do seed vigente: se o seed mudar, o teste muda junto, e
  isso é sinal, não ruído. **Assertar o valor não-arredondado** (17,55 / 0,1755)
  ou com tolerância — nunca a string `"17,6%"`: o agressivo cai em **meia exata**
  a 1 decimal, e é frágil justamente na convenção de arredondamento que esta lane
  gastou um PR inteiro consertando (#1360, meio-para-par vs. meio-para-cima).
- **Pool com imóvel (D9):** `imoveis_no_if = true` ∧ `cat2_efetivo > 0` produz
  `σ_agregado ≥ min(σ do pool)` e `sigma_base_pesos` diz **base mista** — teste
  que falha se reportar `alocacao_alvo_declarada` puro. É a instância que hoje
  violaria o limite de D1.
- **Determinismo de re-run (D10):** mesmo run, `as_of` deslocado por wall-clock
  ⇒ **mesmo σ**.
- `has_alvo: false` ⇒ σ inalterado (0,11), `sigma_procedencia = "fallback_codigo"`,
  **e a ressalva da S7 aparece** (entregue em #1360).
- Classe com peso > 0 e `status: indisponivel` ⇒ `fallback_codigo`, com teste que
  exercita **o caminho de abort**, não só o resultado.
- Invariante de sanidade: `min(σᵢ | wᵢ>0) ≤ σ_agregado ≤ max(σᵢ | wᵢ>0)`, **e
  asserida sobre o valor que `IFMonteCarloConfig.sigma_anual` de fato recebe**
  (decimal), com teto duro `0 < σ ≤ 0,30`. A redação anterior dizia que ela pegava
  o erro pct↔decimal de 100× e **não pegava**: em pct, `1,5 ≤ 10,8 ≤ 22` passa, e
  o erro nasce no handoff para o config, que é decimal. Gate cuja potência
  declarada excedia a real. Prova: mutação `×100` derruba.
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
