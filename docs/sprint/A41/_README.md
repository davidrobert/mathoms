---
id: MOC-sprint-a41
type: moc
title: "Sprint A41 — Governança de chamada LLM: fechar a rota alternativa ao choke-point"
aliases: ["A41", "Sprint A41"]
sprint_status: candidate
date: "2026-08-03"
theme: "llm-governance"
---

# Sprint A41 — Governança de chamada LLM (follow-ups da ADR-355, 2026-08-03)

> **Status:** `candidate`. A [[A40]] segue `current` — duas sprints `current` é
> hard fail em `build_doc_index.py --check`, e a decisão do dono de 2026-08-03
> ("nada sai da A40") é explícita em não despejar lane para cá. As 3 lanes
> nascem `planned`: escritas, **não autorizadas para pickup**.

> **Origem:** §Escopo deferido da [[ADR-355]] (mergeada 2026-08-03, PRs #1138 +
> #1141) + 1 achado colateral medido durante aquela implementação. Nenhum item
> aqui é hipótese: os 4 têm `path:linha` e comportamento observado — 3 aqui, o
> quarto em [[A40.l24]].

> **Objeção do `product-manager` (2026-08-03) — acatada em parte.** O PM
> recomendou **não abrir A41**: desmembrar, com a lane do gate F2 direto na A40
> (tem consumidor com data) e o resto como frente nova em [[PLAN-launch-trust]]
> com gatilho de evento. Decisão do dono no mesmo dia: **a metade urgente foi
> acatada** — a lane virou [[A40.l24]] na sprint corrente, que é o único lugar
> de onde ela é pescável antes do próximo `make go-parity`. A A41 permanece com
> as 3 lanes que **esperam gatilho** e não têm consumidor datado. A numeração
> começa em `l2` de propósito: o vão registra a promoção.
>
> O resto da revisão está incorporado (fusão de duas lanes em [[A41.l3]], KR
> reformulado, free tier fora do DoD). Se a A41 for colapsada nos planos depois,
> as 3 lanes migram sem reescrita — `plan:` já aponta para a casa temática.

## Tese

A [[ADR-355]] fez `skip_llm` cumprir o que promete **nas superfícies que ela
alcançou**. O que ela expôs é maior: existe uma **rota alternativa ao
choke-point** `LLMService`. Três arquivos de produção instanciam o SDK
`anthropic` direto, e não há gate impedindo o quarto.

Quem passa por fora do choke-point não tem hard-stop de budget ([[ADR-173]]),
não grava `LLMCallLog`, não usa cache ([[ADR-307]]), não emite métrica
([[ADR-110]]) e não passa pela sanitização de prompt-injection ([[ADR-175]]) —
com input que é **conteúdo de documento de terceiro**, exatamente a superfície
que a ADR-175 cobre.

A A41 não conta superfícies roteadas: fecha a rota.

## KR

**`rg 'import anthropic|anthropic\.Anthropic' --type py` retorna 0 fora de
`pipeline/llm/` e `tests/fakes/`, e existe gate no pre-commit que hard-falha no
próximo.**

Linha de base medida em `main` (2026-08-03) — 3 arquivos de produção:

```
backend/app/services/documents/document_classification.py
scripts/e2/banks/caixa.py
scripts/route_documents.py
```

Contar "N superfícies roteadas" seria Goodhart: para de contar quando alguém
adiciona a próxima. O KR mede **ausência de rota alternativa**, e o gate é o que
o torna durável (mesmo padrão do KR-A da [[A40]]: provar que o gate morde).

## Lanes

| Lane | O quê | Prio | `plan:` |
| --- | --- | --- | --- |
| [[A41.l2]] | E0 classify passa pelo choke-point `LLMService` | P1 | [[PLAN-launch-trust]] |
| [[A41.l3]] | Caixa: decidir o reframe em ADR antes de dimensionar | P1 | [[PLAN-launch-trust]] |
| [[A41.l4]] | Gate que fecha a rota alternativa (fecha o KR) | P1 | [[PLAN-launch-trust]] |

Ordem: **l2 → [ADR do reframe] → l3 → l4**. Todas P1, nenhuma P0 — não há
produção (#1130) e nenhum item é incidente de custo hoje.

A quarta lane desta sprint vive na sprint corrente: [[A40.l24]] (asserção "0
LLM" do gate F2). Ela saiu daqui porque é a única com **consumidor datado** — o
[[TRACK-f2-cutover]] declara que nada mais avança sem o dono rodar o Tier-1, e o
§Critério de aceite dele afirma `assert 0 invocação LLM`. Lane `planned` em
sprint `candidate` não aparece em `SPRINT_CURRENT`; esperar o gatilho da A41
significaria deixar o dono rodar o gate contra uma asserção que não prova nada.

`l4` fecha por último por construção: o gate falharia no próprio código que
`l2` e `l3` estão consertando.

## Gatilho de promoção a `current`

Evento, não calendário. Qualquer um dos dois:

- **(a)** decisão de abrir o beta fechado / 2º usuário — mesmo gate de
  [[ADR-228]] G2/G3 e da F2 de [[PLAN-launch-trust]]; ou
- **(b)** o `make go-parity` com o hook de [[A40.l24]] medir **≥1 chamada de
  visão da Caixa** no corpus do dogfood — aí [[A41.l3]] tem alcance provado e
  sobe para P0.

Até lá as 3 lanes ficam `planned`. O gatilho (b) depende de [[A40.l24]] ter
entrado: sem o hook no boundary do SDK, o gate não sabe medir o que dispararia
esta sprint.

## Decisão pendente (não é lane) — LLM no E0 para free tier

`tier == "free"` pula stages `is_llm`
([`pipeline_task.py:1254`](../../../backend/app/tasks/pipeline_task.py)) mas o
E0 continua chamando. O `PRODUCT.md` §4 promete Free = pipeline determinístico
sem LLM, e BYOK = zero custo para a plataforma.

**Não vira lane** porque o número que a justificaria não é mensurável com
validade hoje: `llm_classified` sobre o corpus do dono mede taxa de fallback num
corpus premium, curado e já roteado — extrapolar para um free user novo (corpus
100% inbox, não curado) enviesa **para baixo**. Fechar uma lane verde sobre essa
extrapolação repetiria o defeito de método que o painel da [[A40]] apontou
(aceite verificado contra constante, não contra payload).

**Reframe que muda a pergunta:** o E0 já aceita `api_key` explícita com
precedência sobre a env var (A37.l3). Então a opção não é binária "desligar LLM
no free" (regressão de ~10% do corpus). É **remover o fallback para a env var
quando o tier é free**: quem trouxe BYOK mantém a qualidade, quem não trouxe não
tem LLM em lugar nenhum — que é o que o contrato já promete. Isso rebaixa o item
de *decisão de produto com regressão* para *conformidade com contrato*.

Pergunta estreita para o `gtm-strategist`, quando houver tráfego: LLM no E0 é
isca de conversão para free, ou é violação do BYOK?

Query que produz o insumo (o contador já está em `main` desde a [[ADR-355]]):

```sql
SELECT r.tier_at_run,
       SUM(CAST(json_extract(l.output_summary,'$.llm_classified') AS INTEGER))
FROM pipeline_stage_logs l
JOIN pipeline_runs r ON r.id = l.pipeline_run_id
WHERE l.stage = 'route_documents'
GROUP BY r.tier_at_run;
```

## Critério de fechamento

1. KR verde: `rg` retorna 0 fora dos dois diretórios permitidos **e** o gate
   morde — fixture com o import ⇒ `EXIT≠0`.
2. Run com `skip_llm=True` sobre o corpus do dogfood: **0 chamadas ao SDK** e
   **0 rows novas em `LLMCallLog`**. É o teste ponta-a-ponta da promessa da
   [[ADR-355]].
3. A decisão pendente do free tier está **nomeada e transferida** para o dono
   com gatilho escrito — não conta como débito (precedente: A28, A22, A39).

Não é critério desta sprint: `make go-parity` Tier-1 ficar vermelho com ≥1
chamada ao SDK. Isso é aceite de [[A40.l24]], que fecha na A40 — a A41 **consome**
esse instrumento (gatilho (b)) em vez de responder por ele.
