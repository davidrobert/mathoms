---
id: ADR-360
type: adr
title: "Seed do cone Monte Carlo de IF é constante de modelo versionada, não entropia do SO"
status: Proposto
phase: "A40 (bloqueio nº 1 do gate de paridade F2 do GO_SHELL)"
date: "2026-08-03"
relates_to:
  - "[[ADR-237]]"
  - "[[ADR-219]]"
  - "[[ADR-217]]"
  - "[[ADR-090]]"
supersedes: []
superseded_by: []
aliases: ["ADR 360", "seed do Monte Carlo IF", "cone reprodutível"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
  - phase/a40
---

# ADR-360 — Seed do cone Monte Carlo de IF é constante de modelo

**Status:** Proposto (A40) • **Data:** 2026-08-03 • **Relaciona** [[ADR-237]] (o
cone e seu PMT), [[ADR-219]] (premissas versionadas + critério "re-run produz
mesmas projeções"), [[ADR-217]] (`score_version` como precedente de carimbo de
versão no payload), [[ADR-090]] (dinheiro nunca é `float`).

## Contexto

`IFMonteCarloConfig` declarava `seed: int | None = None` e `_simular_caminhos`
fazia `np.random.default_rng(config.seed)`. **Nenhum call-site de produção
setava seed** — o único é `e5_analyzer_adapter.py`. Com `seed=None` o numpy
semeia da entropia do SO, então o cone P10/P50/P90 mudava a cada execução com
input idêntico.

Medido em dois runs reais do mesmo workspace (`skip_llm=True`, minutos de
diferença, mesmo código): `if_monte_carlo.caminho_p10[22]` deu R$ 11.037.269,90
num run e R$ 10.961.276,98 no outro — 0,7%, divergindo em toda a série.

Sweep de 30 seeds em dois perfis de acumulação, para dimensionar:

| `n_simulacoes` | dispersão da série do cone | dispersão de `prob_if_ate_idade_meta` | ano de IF (P50) | latência |
|---|---|---|---|---|
| 10.000 (anterior) | 2,4% | 0,05–0,45 pp | **oscila 2040↔2041** num perfil | 29 ms |
| 50.000 | 1,2% | 0,02–0,23 pp | estável | 85 ms |
| 200.000 | 0,8% | 0,01–0,12 pp | estável | 529 ms |
| 1.000.000 | 0,2% | 0,00–0,06 pp | estável | 3.053 ms |

Duas leituras decidem o desenho: **subir `n` não compra reprodutibilidade** (a 1
milhão de caminhos sobra 0,2%, e o rótulo compacto do gráfico ainda alterna entre
"R$ 3,4 mi" e "R$ 3,5 mi"); e **com 10k a manchete se move** — não era só a curva
do gráfico, era o ano de IF que o cliente lê.

Três superfícies consomem esses números: o gráfico do cone em S7, o card de
probabilidade, e o **parecer do planejador** — `$.if_monte_carlo` está no catálogo
de citação e é caminho de âncora do prompt, então a recomendação escrita ao
cliente ancora em valor que se movia sozinho.

O não-determinismo já havia deixado cicatriz: `test_report_view_model_snapshot.py`
mascarava `prob_if_ate_idade_meta` como `<volatile>` com o comentário "saída Monte
Carlo não-seedada". E o critério de aceite da [[ADR-219]] — *"re-run sobre mesmo
run produz mesmas projeções"* — já estava `Decidido` e descumprido. Esta ADR fecha
dívida de conformidade, não abre decisão nova.

O achado veio do gate de paridade Go (F2, `docs/plan/GO_SHELL/tracks/f2-cutover.md`),
cujo Tier-1 exige controle Py↔Py value-exact: enquanto o cone fosse estocástico, o
controle sujava sozinho e o gate não afirmava nada sobre o executor Go.

## Decisão

**O seed é constante de modelo versionada** — `_MC_SEED = 360` (o próprio número
desta ADR, precedente [[ADR-281]]), default de `IFMonteCarloConfig.seed`. Junto:

1. **`n_simulacoes` de 10.000 → 50.000.** Não compra determinismo (isso é o seed);
   compra acurácia — 2,4% → 1,2% de dispersão, a 85 ms, dentro do orçamento de
   150 ms fixado pela [[ADR-237]].
2. **Guard de fail-fast:** `__post_init__` levanta em `seed is None`. O bug estava
   no call-site, não na função — um teste sobre `run_monte_carlo_if` não o pegaria.
   O guard torna a classe de bug **inconstruível**.
3. **Sorteio antes da premissa:** `mu + sigma·rng.standard_normal(...)` em vez de
   `rng.normal(mu, sigma, ...)`. Mesma distribuição e mesmo stream (diferença
   medida: 5,6·10⁻¹⁷), mas a estrutura location-scale passa a ser explícita no
   código em vez de detalhe interno do `Generator` — revisar `sigma`/retorno
   ([[ADR-219]] prevê revisão) muda a **largura** do cone, preservando o sorteio.
4. **Proveniência no artefato:** `mc_version` (declarado; bump exige ADR
   sucessora, padrão `score_version` da [[ADR-217]]), `seed_usado` e
   `n_simulacoes_usado` (observados do config que rodou). O artefato tem de bastar
   para reproduzir o cone. Ficam no **fim** do bloco: o distiller do parecer
   renderiza `$.if_monte_carlo` raw com cap de 300 chars, então metadado de
   auditoria não desloca dado de domínio do contexto do LLM (verificado).
5. **Schema de `if_monte_carlo` fechado** — era `{"type": "object"}`, 12 campos sem
   validação nenhuma. Ganha `properties` + `required: [exibir_cone, mc_version,
   seed_usado, n_simulacoes_usado]`, sem `additionalProperties: false`.
6. **Teto de major no numpy** (`>=1.26,<3`): a política do numpy garante o bit
   stream do `Generator` só no mesmo build/ambiente/máquina e permite quebrá-lo em
   release X.Y. Bump é **evento de rebaseline**, não upgrade silencioso.
7. **`seed_usado`/`n_simulacoes_usado` em `_NON_MONETARY_EXACT`** de
   `dev/golden_diff.py`: o classificador é monetário-por-default e tratava
   `seed_usado=360` como R$ 3,60, reportando `delta_cents` fantasma.

**O seed nunca é configurável por workspace** (nem via override) — knob por
cliente é cherry-picking com outro nome. E o valor é escolhido **ex ante**:
olhar o resultado para escolher seed é fabricar número. O gate contra isso é o
teste de robustez (§Critério de aceite), que audita a propriedade em vez de
confiar na disciplina de quem revisa.

## Alternativas consideradas

**A) Seed derivado dos inputs de domínio** (hash de patrimônio, meta, retorno,
aporte). Era a recomendação inicial do agente principal; **rejeitada pelos dois
especialistas pelo mesmo motivo, e o motivo é decisivo: quebra monotonicidade.**
Com seed fixo, cada caminho é `pv·∏r + 12·pmt·Σ∏r` — monótono em patrimônio e
aporte, logo toda estatística de ordem também é. Com seed derivado, R$ 1 a mais de
aporte re-semeia e o cenário adverso pode **cair**: +R$ 100/mês por 22 anos vale
~R$ 46 k ≈ 0,42% de um P10 de R$ 11 M, contra 2,4% de ruído de reamostragem — 6×
o sinal. "Aportei mais e minha projeção piorou" é erro **direcional** na única
alavanca em que os padrões consagrados de planejamento patrimonial brasileiro
convergem, e é pior que o cone se mover entre runs. Corolário técnico: destrói
common random numbers, então comparar dois
cenários (o what-if de aporte de S7) ou dois meses passa a medir ruído. E destrói
atribuibilidade de golden diff — qualquer PR que mova `pv`/`meta`/`r`/`pmt`
re-semearia 120 pontos do bloco, soterrando o sinal real em churn.

**B) Seed derivado de `(workspace_id, competência, versão)`.** Rejeitada: exige
encanar `workspace_id` até o domínio (o adapter E5 não o recebe); "competência do
run" reintroduz o defeito (cone muda de mês em mês com input idêntico), quebra
idempotência de re-run/backfill, viola o critério já `Decidido` da [[ADR-219]] e
mata o Tier-1 do gate se derivar de `date.today()`. E o benefício — caminho
distinto por cliente — é irrelevante: não há agregação cross-workspace no produto.

**C) Só subir `n`, sem semear.** Rejeitada por medição: a 1 M de caminhos sobram
0,2% de variação e o rótulo exibido ainda alterna. Reprodutibilidade não é
assintótica.

**D) Decorrelacionar o viés entre clientes** (o medo legítimo do seed comum: se
aquele sorteio é levemente otimista, todos herdam na mesma direção). Rejeitada
como remédio: o problema é de **magnitude** (≤0,6% com n=50k), não de correlação,
e é uma ordem de grandeza menor que o erro de modelo que a própria [[ADR-237]]
documenta (`sigma` fixo, sem choque de PMT, sem inflação heterogênea).
Decorrelacionar *esconde* o viés no agregado em vez de reduzi-lo, e destrói
auditabilidade: com seed comum a dispersão residual é medida uma vez e publicada.

**E) Quase-aleatório (Sobol) / antithetic variates.** Determinístico por
construção e menos erro amostral para o mesmo `n`. **Adiada, não rejeitada:** o
ganho de variância é provado para expectativas de funções monótonas, não para
P10/P90 de riqueza terminal — afirmar sem medir é exatamente o pecado que este bug
expôs. Retomada com critério empírico: reduzir a dispersão do sweep de 30 seeds a
`n` fixo. Seria segundo bump de `mc_version`.

## Consequências

**Positivas:**

- O cone passa a ser função pura dos inputs: mesmo input → mesmo número, citável e
  conferível. Fecha o critério de aceite pendente da [[ADR-219]].
- Monotonicidade em patrimônio e aporte vira **invariante testada** — o what-if de
  aporte de S7 e a comparação mês a mês passam a medir sinal, não ruído.
- Desbloqueia o Tier-1 do gate F2: o controle Py↔Py deixa de sujar sozinho.
- O `<volatile>` de `prob_if_ate_idade_meta` no snapshot morre; o campo volta a
  ser asserido.

**Negativas:**

- **Números que o cliente já viu mudam.** Seed + `n` novos deslocam todo o bloco;
  um relatório que dizia "IF em 2040" pode dizer 2041 sem que a carteira tenha
  mudado. Mitigação: `mc_version` no payload + nota one-shot no primeiro relatório
  pós-merge ("recalibração do modelo de projeção — a variação nesta seção vem do
  modelo, não da sua carteira"). Sem isso, a inferência racional do cliente é "meu
  plano piorou". Atenua o risco: `if_monte_carlo` **não** está em
  `DEFAULT_SECTION_VALUE_PATHS`, então nenhum card de variação fabrica a piora.
- Latência do MC 29 ms → 85 ms (dentro dos 150 ms da [[ADR-237]]); pico de memória
  transiente sobe na mesma proporção (~5 arrays de `n×40` float64).
- **Sobra 1,2% de erro amostral.** Reprodutível ≠ preciso: o número para de se
  mover, mas continua sendo estimativa. As séries do cone **não são valor
  citável** — o artefato as serializa com 10 dígitos significativos porque o gate
  precisa disso, não porque a precisão existe.
- Bump de numpy e troca de arquitetura de runner passam a ser eventos de
  rebaseline conscientes.
- A Alternativa D da [[ADR-237]] ("versão paralela `MonteCarloIFResult.version`",
  rejeitada) era sobre **coexistir v1 e v2 calculando**, não sobre carimbo de
  versão — `mc_version` não a reabre.

## Critério de aceite

- `run_monte_carlo_if` 2× com config default (sem seed explícito) → resultado
  idêntico campo a campo, incluindo as 3 séries.
- `E5AnalyzerAdapter.analyze_via_store` 2× sobre o mesmo store → bloco
  `if_monte_carlo` idêntico. É o único teste na topologia do bug.
- `IFMonteCarloConfig(seed=None)` levanta `ValueError` com o valor ofensor.
- Monotonicidade: `pv' > pv ⇒ caminho_pXX'[t] ≥ caminho_pXX[t] ∀t`; idem para
  `aporte_mensal`. É o teste que impede alguém "melhorar" isso para seed derivado
  sem ler esta ADR.
- Robustez de seed (anti seed-shopping): sobre 10 seeds alternativos a n=50k, a
  dispersão da série é ≤2%, a de `prob_if_ate_idade_meta` ≤0,6 pp, e o ano do P50
  é o mesmo em todos. Falha aqui significa que o seed escolhido é sorte — a
  resposta é subir `n`, **nunca** trocar o seed.
- `mc_version`/`seed_usado`/`n_simulacoes_usado` presentes nos dois caminhos (com
  e sem cone) e validados pelo schema.
- `prob_if_ate_idade_meta` fora de `_VOLATILE_LEAVES`, snapshot rebaseado no mesmo
  PR. Se o snapshot ficar vermelho **só** nas folhas de MC no CI, a resposta é
  quantizar na precisão do estimador, **não** remascarar.
- `make go-parity WS=<dogfood> RUNS=2` → controle Py↔Py com 0 diff residual, sem
  allowlist para o cone.

## Deferimento datado — 2026-08-03

Levantado no co-design, **fora do escopo desta ADR**, com dono no owner:

1. **Honestidade do que é exibido** (recomendação do `financial-planner`): exibir
   probabilidade em faixa de 5 pp ("cerca de 30%") em vez de inteiro; aposentar a
   manchete de **ano** do MC (S7 já tem o ano determinístico — dois anos
   concorrentes, um ruidoso, é ferimento autoinfligido) e publicar faixa; declarar
   as séries do cone explicitamente fora do catálogo de citação. Retomada: junto
   da próxima mudança de copy de S7.
2. **`sigma` por perfil de risco** — follow-up da [[ADR-237]] §E que nunca
   aterrissou: `_SIGMA_POR_PERFIL` (0,07/0,11/0,15) é dead code e o adapter não lê
   `premissas_economicas`, apesar de a [[ADR-219]] ter construído a tabela para
   isso. `sigma_usado: 0.11` é constante de código apresentada como premissa
   auditada — erro de premissa domina o erro amostral que esta ADR reduziu.
3. **P50 condicional aos sobreviventes:** `anos = primeiro_true[alguma_vez] + 1`
   tira os percentis só das simulações que atingem a meta em 40 anos, enquanto
   `prob_if_ate_idade_meta` usa `n` cheio no denominador. O "P50" exibido é a
   mediana **dos bem-sucedidos** — otimista por construção, e mais otimista quanto
   pior o plano. Distorção maior que os 2,4% desta ADR.
4. **`int(np.percentile(...))` trunca** (piso, não arredonda) — viés sistemático
   de ~meio ano para baixo no ano de IF.
5. **`idade_meta_usada: 1040`** no payload: sentinela 999 de `_solve_prazo` somada
   à idade, em path citável formatado como "anos" — o parecer pode ancorar "IF aos
   1040 anos".

## Referências

- `pipeline/domain/services/if_projector.py` — `_MC_SEED`, `IFMonteCarloConfig`,
  `_simular_caminhos`, `run_monte_carlo_if`.
- `pipeline/domain/services/e5_analyzer_adapter.py` — único call-site; passou a
  herdar o default correto sem mudar de forma.
- `pipeline/domain/services/e5_serialization.py` — bloco `if_monte_carlo`.
- `config/schemas/e5_analysis.schema.json` — bloco fechado.
- `backend/tests/test_report_view_model_snapshot.py` — `_VOLATILE_LEAVES`.
- `dev/golden_diff.py` — `_NON_MONETARY_EXACT`.
- `tests/test_if_projector_v2.py`, `tests/unit/pipeline/test_e5_analyzer_adapter.py`.
- `docs/plan/GO_SHELL/tracks/f2-cutover.md` §"1ª execução real do Tier-1".
