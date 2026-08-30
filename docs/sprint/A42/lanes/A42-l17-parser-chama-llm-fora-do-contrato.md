---
id: A42.l17
type: lane
title: "Um parser de banco chama o SDK LLM fora do contrato, e a saída livre vira chave de junção"
sprint: A42
status: shipped
ship_pr: 1846
ship_date: "2026-08-30"
priority: P0
branch_slug: a42-l17-parser-chama-llm-fora-do-contrato
owner: data-engineer
depends_on: []
adrs: ["[[ADR-173]]", "[[ADR-287]]", "[[ADR-349]]", "[[ADR-355]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p0, area/dados, area/llm]
---

# A42.l17 — `parser-chama-llm-fora-do-contrato`

> **Origem:** `R1` da **U3** ([[LEDGER-CERTIFY-active]] §r7). Cético: `PARCIAL`, Crítico → Alto,
> **com escalação que a lente não viu**.

## O defeito

Um parser de banco instancia o SDK do provider **direto** e chama o modelo **sem
`temperature`** (o default do SDK é o valor mais alto), sem seed, sem cache, sem contrato
tipado — e **sem escrever na tabela de telemetria LLM** que é a fonte única declarada. A
descrição que o modelo devolve alimenta a **chave natural** da transação.

## Evidência medida

Sobre o **mesmo documento**, em quatro runs consecutivos, mudaram **2, 1 e 4** de 8 chaves
naturais (25% · 12,5% · **50%**). No corpus E2 inteiro — 136 unidades, 7.991 transações — as
**quatro** chaves que mudaram entre os dois últimos runs estão **todas nesta única unidade**,
a única cujas notas declaram extração por LLM. A tabela de telemetria não tem **nenhuma**
linha para este documento, enquanto tem para 13 outros.

## Blast radius hoje = 0, e isso é o que rebaixa a severidade

Nenhum override vivo casa com as chaves que churnaram. O dano está no **mecanismo**: uma
chamada LLM não-determinística, não-logada e fora do contrato de custo alimentando
identidade de lançamento.

**Medição que reescalaria para Crítico:** um override vivo cuja chave case com transação
desta unidade.


## Execução (2026-08-30)

### O que a medição confirmou

O ofensor é `scripts/e2/banks/caixa.py::_extract_via_llm`. Instancia
`anthropic.Anthropic(...)` e chama `client.messages.create(...)` **sem
`temperature`** — o SDK então usa o default do provider, o extremo alto. Sem seed,
sem cache, sem schema tipado, sem `LLMCallLog`, sem budget, sem sanitização.

O caminho até a chave de junção fecha: `descricao` → `build_hash_inputs(descricao=…)`
→ `HashInputs.descricao` → `compute_natural_key`
(`pipeline/domain/services/_tx_identity.py`). `normalize_descricao` só faz
lowercase, colapsa espaço e tira sufixo PIX — não embota reescrita do modelo, logo
descrição reescrita **é outra identidade de lançamento**.

**Conjunto de ofensores por igualdade, no repo inteiro** (não só nos diretórios
esperados): `anthropic.Anthropic(` + `.messages.create(` = **2 arquivos, 4 sítios**
— `scripts/route_documents.py` (585, 591) e `scripts/e2/banks/caixa.py` (233, 235).
O `import anthropic  # noqa: F401` de `document_classification.py` é sonda de
instalação, não chamada. Os dois diferem num eixo: `route_documents` **passa**
`temperature`; a caixa não passava.

> **A medição se auto-invalida se você repetir o `rg` cru.** Depois desta lane o
> mesmo comando devolve **4** arquivos: entram `dev/check_llm_sampling.py` (o
> detector, que cita os dois padrões como *string*) e
> `tests/unit/pipeline/test_llm_sampling_gate.py` (a fixture que os escreve para
> provar que o gate morde). Nenhum dos dois é chamada. O número que se re-mede é o
> do próprio gate — `python3 dev/check_llm_sampling.py` diz hoje **4 chamadas cruas,
> todas em resíduo declarado** —, não o `rg`.

### O gate existia e era cego por construção — em três eixos

`dev/check_llm_sampling.py` afirmava no docstring que "call-site novo em arquivo
novo é pego por construção". Falso para quem **não passa** por `LLMService`:

1. `files:` do hook era `^(pipeline/…|backend/app/…)$` — editar `scripts/` **não
   disparava o hook**. Medido: o commit da correção da caixa mostrou o hook como
   `Skipped (no files to check)`.
2. `RAIZES = ("pipeline", "backend/app")` — `scripts/` não era varrido.
3. O discriminador é a **assinatura** `LLMService.call` (`system_prompt` +
   `output_schema`), que um `messages.create` cru nunca carrega.

Os dois sítios de SDK cru do repo moram exatamente nessa cegueira. O comentário
acima do hook já registrava a mesma lição para `backend/app/services/` — ela foi
corrigida uma vez e não generalizada.

### Corroboração (não refutação) — a [[A41.l3]] já tinha medido isto

Cheguei por medição independente à conclusão de que **deletar o call-site perde
dado**: `DocumentTextExtractor.is_image()` casa só `{.jpg, .jpeg, .png}`, um `.pdf`
não é multimodal, `_READER_BY_SUFFIX[".pdf"]` devolve `text=""` para PDF escaneado
→ `ReaderOutcome.documento_vazio` → `_skip_entry`, e o LLM nunca é chamado.

**A [[A41.l3]] já registrava exatamente esse gap**, e com uma medição que eu não
tinha: o pulo é *silencioso* ([[A40.l24]], 2026-08-03) — `success: True`, o doc não
entra em `processed` nem em `errors`. Ela conclui, textualmente, que deletar o
call-site antes de fechar o gap troca "conta desaparece só no Tier-1" por "conta
desaparece em todo tier, sem sinal". O que ela propõe é *delete-and-delegate* —
deletar **e** mover a capacidade PDF-como-documento para `extract_with_llm` —
gateado por ADR `Proposto` (Ato 1) antes de qualquer implementação.

Fica registrado como corroboração para não inflar o achado: o que é curto demais é
a [[ADR-355]] §Deferido nº 1 lida **isolada** ("o fix pode ser deletar o call-site
em vez de propagar o contexto"); quem parar nela, sem abrir a lane, executa o corte
que perde dado. Esta lane **não** decidiu o reframe — o Ato 1 da [[A41.l3]] segue
sendo o dono dele.

### Refutação — do que eu mesmo supus: rotear não compra determinismo

Hipótese natural: rotear pelo choke-point mataria o churn. **Falso.** `use_cache`
é `False` por default em `LLMService.call` e só `comprovantes_bens_llm.py` opta
por `True`; `extract_with_llm` **não** passa `use_cache`. E
`pipeline/llm/deterministic_extraction` é explícito: `temperature=0.0` "reduz
variância, não torna a extração idempotente", e o `seed` é descartado por
`litellm.drop_params` em `anthropic/*`.

Consequência para o registro, e é o que esta lane acrescenta ao que a [[A41.l3]]
já sabia: o reroute compra budget, `LLMCallLog`, métricas, anti-injection e schema
tipado — **não** compra chave natural estável. Nenhum dos cinco critérios de aceite
da [[A41.l3]] menciona churn de identidade, e o *delete-and-delegate* passaria os
cinco **com o churn intacto**. Quem congelaria a amostra é o cache, e ele está
desligado no caminho E2 canônico.

### O que entrou

1. `temperature=EXTRACTION_TEMPERATURE` no call-site cru da caixa — do default do
   provider para o modo da distribuição. **Claim honesto: reduz variância, não
   torna idempotente.** É o único eixo fechável sem a Fase 2, e não antecipa o
   reframe: não deleta nem roteia nada, então o Ato 1 da [[A41.l3]] segue livre.
2. `check_llm_sampling` ganha a segunda verificação: SDK cru fora de
   `pipeline/llm/` é ofensor. Resíduo **declarado por igualdade de conjunto**
   (`RESIDUO_DECLARADO`, arquivo → contagem exata + ADR dona), nunca isenção por
   arquivo. `files:` do hook passa a incluir `scripts/`.
3. Quatro discriminações provadas em árvore-espelho: bypass em arquivo novo
   reprova; sítio **extra** em arquivo já declarado reprova; entrada que sobrevive
   à dívida paga reprova; chamada crua **dentro** de `pipeline/llm/` passa.

**Não fecha a [[A41.l4]]** — é precursor dela, e a diferença importa. A [[A41.l4]]
mira `import anthropic` (não a instanciação), exige `rg` retornando **0** fora de
`pipeline/llm/` e `tests/fakes/`, e pede entrada no `CLAUDE.md` §Regras críticas. Ela
declara que só entra "junto com a última superfície roteada", porque antes disso
falharia no próprio código que a [[A41.l2]]/[[A41.l3]] estão consertando.

O `RESIDUO_DECLARADO` é exatamente o mecanismo que dissolve esse impasse: permite o
gate existir **antes** das superfícies serem roteadas, barrando a quarta hoje sem
reprovar as duas conhecidas. O alvo 3 → 0 da [[A41.l4]] segue aberto e continua
dependendo dos reroutes. Diferença deliberada de recorte: eu caso a **chamada**
(`Anthropic(...)` / `messages.create(...)`), não o import — por isso a sonda de
capacidade de `document_classification.py` não precisa de exceção nomeada. A
[[A41.l4]], ao casar o import, ainda terá de nomeá-la.

### O que continua aberto

- **[[ADR-349]] Fase 2** — bloco `document` no `LLMService`. É a precondição de
  fechar os dois sítios crus; enquanto não entra, a caixa segue sem budget,
  `LLMCallLog`, cache e sanitização.
- **Chave natural alimentada por texto livre de LLM.** Nem `temperature=0`, nem o
  reroute, nem o cache (que está desligado no E2) tornam `descricao` reproduzível
  por construção. Se identidade de lançamento deve depender de campo
  não-reproduzível é decisão de desenho, não de call-site — e é a pergunta que
  esta lane deixa medida para [[ADR-287]].
- **Blast radius segue 0** — nenhum override vivo casa com as chaves que churnaram.
  A medição que reescalaria para Crítico continua sendo a mesma.
