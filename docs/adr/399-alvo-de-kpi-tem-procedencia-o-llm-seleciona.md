---
id: ADR-399
type: adr
title: "Alvo de KPI tem procedência declarada; o LLM seleciona identidade, não autora número"
status: Decidido
phase: r7.PE-2/FP-6
date: "2026-08-19"
amended_at: ["2026-08-27", "2026-08-28"]
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-134]]"
  - "[[ADR-143]]"
  - "[[ADR-191]]"
  - "[[ADR-202]]"
  - "[[ADR-294]]"
  - "[[ADR-296]]"
  - "[[ADR-340]]"
  - "[[ADR-387]]"
  - "[[ADR-396]]"
tags:
  - type/adr
  - status/decidido
  - area/llm
  - area/dominio
aliases:
  - "ADR 399"
  - "procedência do alvo de KPI"
---

# ADR-399 — Alvo de KPI tem procedência; o LLM seleciona, não autora

> **Decidido em 2026-08-19** na remediação de **PE-2** + **FP-6** (P1) do §r7 de
> [[PIPELINE-REVIEWS-active]]. Implementação **em ondas** — ver §Estado de
> implementação antes de §Consequências.
>
> ⚠️ **Emendada em 2026-08-28** ([[A40.l93]]): o **path do observado é requisito do
> catálogo** — alvo cujo observado o resolver do parecer não consegue ler é o comparador
> com um lado fabricado pela ausência —, `alocacao_renda_fixa` vira o **quinto órfão por
> decisão de domínio**, e `unidade`/`operador` fecham como enum. Ver
> §Emenda 2026-08-28.
>
> ⚠️ **Emendada em 2026-08-27** ([[A40.l89]]): o vocabulário fecha em **13 chaves**
> (entram `renda_passiva_cobertura`, `if_prazo_ano`, `aliquota_efetiva_ir`;
> `protecao_cobertura` vira `protecao_custo_premio`), o enum passa a ser **fechado de
> verdade** — sem chave de escape —, e a correção alcança o artefato **congelado** por
> supressão na leitura. Ver §Emenda 2026-08-27.

## Contexto

`metricas[].target` do parecer — o valor-alvo que a família deve perseguir — era
string livre autorada pelo LLM. Dois defeitos medidos em runs armazenados:

**PE-2 — o alvo migra sobre dado byte-idêntico.** `ratios.concentracao_imobiliaria`
= 34,86 nos dois runs; o alvo publicado foi `< 30%` e depois `< 35%`,
**atravessando o valor observado**. Violação virou conformidade sem nada ter
mudado no patrimônio. O limiar canônico do repo é **50%** ([[ADR-340]]): os dois
números do LLM estavam errados, em direções opostas — não é viés, é ruído. E no
run em que disse `< 30%`, o produto afirmou violação a uma família que, pelo
próprio canon, estava conforme.

**FP-6 — o alvo é mais frouxo que a meta declarada.** Para renda fixa, a família
declarou `alvo_pct = 51,55`; o parecer publicou `≤ 55%`. Pior, o `valor_atual`
publicado (76,0%, base carteira financeira) vinha de base diferente do alvo
(82,30%, base carteira líquida): **dois denominadores para o mesmo conceito no
mesmo payload**. O desvio implícito saía ~21pp contra os 30,75pp que o motor já
havia calculado em `desvio_pp`.

A causa não é instrução ruim de prompt. A persona **já** diz "não invente
números" (R1) e o modelo violou em 8 dos 10 casos, porque o schema declarava
`target` **obrigatório, string livre**: um campo required cujo valor não existe no
payload é uma máquina de fabricação. A prova pelo contrário está na única métrica
cujo alvo bate com o canon ao dígito — reserva de emergência, o único cujo valor
**já é publicado no E5**. Quando o número existe no payload, o modelo copia.

Instrução não é gate. E `seed` também não resolve: [[ADR-396]] registra que ele é
descartado em `anthropic/*`.

## Decisão

**D1 — `target` e `valor_atual` são derivados; o LLM emite `metrica_key`.** O
trabalho do modelo muda de *autorar o alvo* para *selecionar a identidade do KPI*
num vocabulário fechado (`METRICA_KEYS`). KPI fora do enum não pode ser emitido —
é o cap estrutural na fabricação. Padrão [[ADR-081]] (determinístico primeiro) e
mesma forma do `valor_renderizado` de [[ADR-296]], escrito pelo finalize.

`valor_atual` entra junto e **não** é escopo extra: derivar só o alvo deixaria o
par incoerente (alvo de uma base ao lado de observado de outra) e fecharia o FP-6
apenas pela metade — o desvio seguiria subestimado. Cada KPI declara `base`, e as
duas pontas saem da mesma.

**D2 — Precedência: alvo declarado pela família vence limiar de doutrina.** Na
metodologia dona desta métrica, o desvio só é definido contra o alvo declarado — substituir `alvo_pct` por
número de config não torna o conselho mais correto, **destrói a métrica**, porque
`desvio_pp` é o que decide para onde vai o próximo aporte. E publicar alvo mais
frouxo que o compromisso da família é o produto absolvendo-a da própria meta.
Quando o declarado viola um limiar canônico, publica-se o declarado como `target`
e o limiar vira `risco` — nunca um meio-termo fabricado.

**D3 — Alvo sem fonte única é órfão: publica sem `target`, com `motivo`.** Nunca
número inventado, nunca `needs_review` (ausência de meta é fato esperado e
frequente; usar o canal de retenção para o caso comum queima o canal), e nunca
omitir a métrica — a linha segue publicada como observacional para não perder o
sinal. Quatro órfãos **por decisão de domínio**, não por lacuna:

| KPI | Por quê |
|---|---|
| `carteira_trs` | [[ADR-191]] §D5: TRS efetiva é yield observado e não tem comparador. `≥ IPCA+4%` e `≥ 6% real` diferem em 2pp reais **e** comparam yield de fluxo com retorno total, induzindo "vender growth para perseguir DY" — o erro de iniciante que a métrica existe para evitar |
| `protecao_cobertura` | [[ADR-387]] proíbe afirmar capital ideal sem inventário confirmado. O publicado (`≥ 60 meses`) era 2 a 4× mais frouxo que o canon (10× renda anual × fator + dívidas), na métrica cujo erro é irreversível para os dependentes |
| `taxa_poupanca_recorrente` | RV2-24: `poupanca_referencia_pct` (25) e `pontos_fortes_taxa_poupanca_min_pct` (30) descrevem o mesmo conceito sem precedência declarada |
| `if_progresso` | O alvo é o par (ano declarado, 100%); o ano sozinho promete estado futuro sem a probabilidade do cone (persona R20) |

**Regra de segurança:** o resolver encontrando duas fontes para o mesmo conceito
**não escolhe** — publica órfão. Escolher seria inventar regra de domínio com
carimbo de procedência, pior que o alvo do LLM por parecer autoritativo.

**D4 — Leitor único do limiar **na rota do `target` publicado**, no produtor.** O
catálogo vive em `pipeline/domain/services/kpi_target_catalog.py` e é o leitor
único **do alvo que o parecer publica**. Precisa ser o produtor porque só ele
conhece a config **efetiva** após override por workspace ([[ADR-134]]) —
`concentracao_alerta_pct` entra por parâmetro, não por global; um leitor no
backend teria de reimplementar a resolução ([[ADR-143]], methodology = code).

**O escopo é essa rota, não o repo.** Os leitores pré-existentes de
`endividamento_maximo_pct` (`pontos_fortes_analyzer.py:66` e
`pontos_urgentes_analyzer.py:65`, com o default inline `20` duplicado nos dois) e
de `concentracao_alerta_pct` (`real_estate_metrics_aggregator.py:142`)
**permanecem** — não foram unificados e não estão no escopo desta ADR. Redação
anterior dizia "leitor único de cada constante", o que a medição refuta: o
catálogo é um **terceiro** leitor. Unificar os demais é trabalho à parte.

## Estado de implementação (2026-08-21)

`Decidido` refere-se à **decisão**, não à cobertura. Registro de fato, **não**
emenda — nenhuma decisão acima mudou.

**Em produção, o parecer continua publicando `target` autorado pelo LLM.** O
defeito que PE-2 e FP-6 descrevem segue vivo no relatório entregue.

| decisão | estado em `main` |
|---|---|
| **D1** — `target`/`valor_atual` derivados, LLM emite `metrica_key` | **não construído.** `Metrica` não tem `metrica_key`, `target` segue required-string, e nada estampa o alvo no pós-LLM |
| **D2** — precedência declarado > doutrina | refletida no catálogo (#1557, `13deaa8f`); **sem consumidor** enquanto D1 não existir |
| **D3** — órfão publica `motivo`, nunca número | idem D2 — o invariante vive no catálogo e no `e5_analysis.schema.json` |
| **D4** — leitor único na rota do `target` | catálogo é o leitor único **do alvo publicado** (#1557). Os leitores pré-existentes citados em D4 **permanecem** |
| publicação de `kpi_targets` no payload E5 | #1591 — **habilita** D1, não o entrega |

Dono, faltantes (a)–(d) e condição de retomada: **§Deferimento D3 (2026-08-21)**
em [[PIPELINE-REVIEWS-active]].

## Consequências

- Cobertura **do catálogo** medida sobre o payload do run r7: **6/10 resolvem,
  4 órfãos documentados** (não é cobertura do parecer publicado — ver §Estado). A premissa "toda métrica % vira drop → a seção esvazia" não se
  materializa: nenhuma métrica é omitida.
- O bloqueio declarado do **catálogo KPI não se aplica a este eixo** — ver
  §Bloqueio abaixo.
- `Metrica` **passará a ter** `metrica_key`, com `target` `Optional` (D1 — ver §Estado). Bump do schema de
  saída + `PROMPT_VERSION` ([[ADR-396]] D3 explica por que o bump é load-bearing).
- O LLM emite **menos** tokens (perde `target` e `valor_atual`, ganha um enum
  curto).

## Bloqueio do catálogo KPI: não procede para o eixo `target`

O PE-2 estava registrado como bloqueado pela dependência do catálogo KPI (RV2-01),
sob o argumento de que `parecer_citation_catalog.py` é money-only e sem catálogo
curado toda métrica % viraria drop. **A dependência não existe no código, e está
invertida.** Evidência:

1. `metricas[]` **não tem campo de âncora** — nem `evidencia_path`, nem
   `ancoras[]`. O catálogo de citação alimenta riscos/sugestões/pontos_fortes; não
   tem superfície de contato com `metricas[]`.
2. O catálogo é **input-side**: seu único consumidor renderiza um bloco markdown
   para dentro do prompt. O verificador de saída não o importa — resolve por
   `get_e5_jsonpath`. O catálogo decide o que o LLM é *informado* que pode citar,
   não o que *resolve*.
3. Âncora é afirmação **sobre o payload** ("este número está em `$.path`"); alvo é
   afirmação **normativa** ("deveria ser X"). Prescrição não se ancora em JSONPath
   — ancora-se em config/goals. Eixos ortogonais.

**Inversão:** um registro `metrica_key → {observado_path, target}` entrega à
RV2-01 o path resolvível por métrica **sem** tocar `monetary_only`. Este trabalho
**destrava** a ancoragem de percentual; não é destravado por ela. O **PE-1**
(rota de âncora de citação) segue aberto por mérito próprio, mas deixa de ser
bloqueante — e encolhe, porque perde a exigência de curar limiar normativo.

## Emenda 2026-08-27 — o enum fecha em 13 chaves, e a leitura subtrai

> **A D1 não muda: o LLM seleciona, não autora.** O que muda é o *tamanho* do
> vocabulário, o *nome* de uma chave, e o *alcance* da correção.

**E1 — corrigir o vocabulário, não abrir exceção.** Das 10 métricas publicadas no run
da U1, **4 estavam fora** do enum de 10 chaves. Fechar sem corrigir apagaria 4 linhas do
painel; abrir uma chave de escape genérica devolveria ao modelo os campos que a D1
fechou — a máquina de fabricação **realojada de `target` para `valor_atual`**, num campo
que a D1 fechou de propósito e junto ("renda passiva mensal *projetada*" é R$/mês **sem
produtor no payload**, publicado ao lado de números derivados e lido como medido).

Regra de admissão, agora explícita: admite-se chave quando **(a)** existe fonte
determinística única para o limiar, **ou (b)** a ausência de alvo é ela própria regra de
domínio decidida e vale publicar ao usuário.

| chave | veredito |
|---|---|
| `renda_passiva_cobertura` | **admitida** por (a) — limiar **100 `>=`**, que não é doutrina: é o **ponto fixo da razão** (numerador = denominador), o único número que não seria uma escolha. Base declarada `despesa_essencial_mensal_12m`; `status != "ok"` ⇒ órfã, **nunca 0%** |
| `if_prazo_ano` | **admitida** por (b) — o "atual" só existe como percentil de cone, e [[ADR-361]] intercala a flag de censura ao lado de cada ano |
| `aliquota_efetiva_ir` | **admitida** por (b) — "monitorar tendência" *é* a regra; alíquota efetiva é descritiva, e o limiar dependeria do regime |
| renda passiva mensal *projetada* | **recusada** — sem produtor no payload, não entra |

**E2 — `protecao_cobertura` → `protecao_custo_premio`.** A chave nomeava um conceito que
o payload **não publica**: não existe agregado de capital segurado no schema, por desenho
— é a própria [[ADR-387]]. O que `pct_renda_anual` entrega é prêmio/renda. Medido:
6.022,27 / 0,005686 ⇒ renda ≈ 1,06 MM, logo **razão 0–1** declarada como `pct`; quem
lesse pelo contrato publicaria 0,0057% no lugar de 0,57%. Agora `unidade: ratio_0_1`,
base `renda_anual_liquida`.

**E3 — `rotulo` entra no catálogo.** O nome da métrica carrega domínio e rótulo autorado
não é gateável: cobrir 100% da despesa **essencial** é o marco de segurança, não a
independência (medida contra o custo de vida total). Publicar sem o qualificador ensina a
família a se declarar independente cedo demais.

**E4 — a correção alcança o artefato congelado, por SUPRESSÃO.** A D1 corrige o
write-path e não toca os **51 pareceres persistidos**, dos quais 42 publicam alvo
prescritivo para métrica que este catálogo declara órfã. A leitura passa a servir `target`
apenas quando o artefato traz `metrica_key`. **Backfill e derivação-na-leitura ficam
recusados**: o artefato é o registro forense do regime em que foi gerado ([[ADR-204]]
§D1/§D7), e recomputar o catálogo no backend reimplementaria a resolução de config
efetiva por workspace — o que a D4 existe para impedir — além de carimbar config de hoje
sobre E5 antigo. A regra é subtrativa: **a leitura só remove afirmação, nunca acrescenta
número a documento entregue.**

**E5 — o cap estrutural é o enum, e ele não tem escape.** Métrica fora do vocabulário
**não é emitível**. Chave nova exige passar pela regra de admissão acima — nunca um
número escolhido na hora, nunca um balde genérico.

**Fora desta emenda, com endereço:** o alvo determinístico do plano de ação
(`suggestion_rules.trs_target_pct`) e a prosa da E5 que entrega limiar ao modelo são
**leitores isentos pela D4** e migram para a [[A40.l90]], sob emenda própria — ver
§Deferimento datado 2026-08-27 da [[A40.l89]].

## Emenda 2026-08-28 — o path é requisito, e a alocação perde o comparador

> **A D1 e a D3 não mudam.** O que muda é: um requisito novo sobre `observado_path`, um
> quinto órfão por (b), e o fecho do vocabulário de `unidade`/`operador`.

**Origem:** §Fecho da [[A40.l89]] (painel de 2026-08-28), executado pela [[A40.l93]].
Duas das 13 chaves publicavam alvo cujo `observado_path` o resolver de **produção**
(`PlannerDrillDown` com `load_manifest().tools_section_whitelist`) devolvia
`path_not_whitelisted`, por causas diferentes sob o mesmo `reason`.

### E6 — `observado_path` legível pelo resolver é requisito, e a rota é ponto fixo

Alvo pareado a observado que o parecer **nunca** consegue ler é o defeito da D1 pela
outra ponta: o comparador aparece com um dos lados fabricado pela ausência. `_par`
publica `target: null` + motivo, então não há número inventado — mas a linha nasce
inútil, e o alvo fica publicado no artefato sem par possível.

`alocacao_renda_fixa` usava `comparaveis[classe=renda_fixa].atual_pct` — **predicado de
filtro**, que o `_JSONPATH_RE` do `planner_drill_down` recusa por desenho (o subset
rejeita filtro e recursive descent). A rota é publicar a folha em **ponto fixo**
(`goals.alocacao_alvo.derived.renda_fixa_atual_pct`), **não** alargar o subset: o
guardrail é declarado, e alargá-lo daria capacidade de filtro **ao modelo** para servir
um consumidor interno que não precisa de query.

Gate: `dev/check_kpi_path_legivel_pelo_parecer.py` (pre-commit), que mede a metade
decidível sem payload — sintaxe + raiz na whitelist — e **declara no nome e no docstring
que não cobre `value_absent`**, que continua com
`tests/test_e5_golden_execution.py::test_todo_observado_path_do_catalogo_resolve_no_payload`.
A allowlist `_RESOLUCAO_DIVIDA_DECLARADA` daquele teste foi **deletada**: sem ofensor,
ela viraria estado permanente protegido por teste.

### E7 — `alocacao_renda_fixa` é órfã por (b), e o operador que ela tinha era falso

O catálogo publicava `operador="<="` sobre o par (atual, alvo): **menos** renda fixa que
o alvo estaria conforme. Falso nas três metodologias de referência, e falso na direção
que machuca — a família sub-protegida vende ativo de risco na baixa. Ficava mascarado
pelo path irresolvível: consertar E6 sozinho **ativaria** o comparador errado com o selo
do produto.

Co-design `financial-planner`: **nenhum operador escalar diz a verdade aqui.** Desvio de
alocação é bidirecional e **soma zero** entre classes comparáveis (denominador único), e
as duas direções diferem em natureza, urgência e remédio — sub-alocar é risco de ruína,
súbito, com sinal direto (o próximo aporte vai para a classe); sobrealocar é custo de
oportunidade, lento, e na metodologia dona nunca é achado autônomo. Um teto ou um piso
colapsa os dois.

**E a banda de ±2pp do motor não serve de régua.** `SEVERITY_ALINHADO_MAX_PP` é piso de
**acionabilidade** — a [[ADR-400]] o reusa literalmente assim ("a incerteza não pode ser
maior que a menor diferença que o produto trata como acionável") — e a [[ADR-141]]
§Emenda item 10 difere a calibração **relativa** para pós-dogfood. Publicá-lo como
`limiar` com `procedencia: limiar_canonico` promoveria limiar interno a doutrina sem a
doutrina ter sido decidida: é o modo de falha desta ADR com o ator trocado — não o LLM
fabricando, o produto carimbando.

Admitida por **(b)**, ao lado de `if_progresso` e `if_prazo_ano`, que são órfãos pela
**mesma forma**: o alvo é um par, e publicar um lado sozinho promete o que a outra
dimensão nega. A linha segue publicada como observacional, com o observado em ponto fixo
— o alvo declarado pela família **não some do produto**: vive no card Alocação · Atual vs
Alvo (S3), com direção, desvio assinado, severidade e destino do próximo aporte. O que
sai é uma cópia escalar de menor resolução, e é ela que não sabe dizer a verdade.

**A D2 continua certa para alocação, e o critério fica escrito** (a [[A40.l89]] §Fecho já
registrou que ela está **errada para reserva**, onde a regra é `max(declarado, canonico)`):
*o declarado vence quando é a **definição** da métrica e a doutrina não tem piso
independente; o canônico vence quando a doutrina define **piso de sobrevivência** e a
declaração pode ficar abaixo dele.* Em alocação, `desvio_pp = atual − alvo_declarado`:
substituir por doutrina não aperta a métrica, **apaga** a métrica. Em reserva existe piso
canônico independente. Critério, não lista de exceções — lista quebra na próxima métrica.

**Efeito colateral que não é pequeno.** Sem comparador, dois estados que fabricariam
conformidade deixam de ser representáveis: **denominador zero** (`_pct_of` devolve `0.0`
quando a carteira líquida é ≤ 0, e "0% ≤ 44,4%" leria conforme) e **supressão declarada**
([[ADR-394]]/[[ADR-400]]: o produtor se recusa a julgar o desvio, e o comparador o
recriaria por outra porta). Os dois estão vivos na fixture do golden hoje.

### E8 — `unidade` e `operador` fecham como enum

`procedencia` já era enum; os outros dois eram string livre com o vocabulário só na
`description` — assimetria sem razão. A proteção que o enum compra é **assimétrica e
medida**: unidade fora de `_UNIDADE_RENDER` faz `_render_valor` devolver `None` e a
métrica sai **sem valor e sem alvo, em silêncio**; operador desconhecido é
**renderizado literal** por `_OPERADOR_GLIFO.get(op, op)`, com cara de autoridade.

`unidade` = `{pct, pct_aa, meses, ano, ratio_0_1}`, **igual** ao renderer. `operador` =
`{<, <=, >=, null}`, subconjunto **estrito** do glifo (`>` fica de fora: ampliar é ato
deliberado do produtor que precisar, e consumidor mais permissivo que o contrato é a
direção segura). Paridade de três vias gateada em
`tests/test_parecer_metrica_stamping.py`.

Banda de tolerância **não cabe como símbolo novo**: `~=` esconderia dois números num
`limiar` escalar e o leitor não saberia de que lado está. Qualquer banda exige mudança de
**forma** (`limiar_min`/`limiar_max`, ou `limiar` + `tolerancia_pp`) e paga emenda de
contrato de todo jeito — o enum fechado força essa conversa em vez de deixar passar
`~= 40%` significando nada.

### O que esta emenda NÃO faz

- **Não conserta o denominador zero em `comparaveis[].atual_pct`.** O card S3 continua
  publicando `0,0%` para carteira líquida zero, e a folha nova é cópia fiel disso de
  propósito: consertar só a cópia daria duas respostas para o mesmo fato. É defeito
  pré-existente do card, com dono, fora desta lane.
- **Não toca a D4.** Os leitores pré-existentes de `endividamento_maximo_pct` e
  `concentracao_alerta_pct` permanecem.
