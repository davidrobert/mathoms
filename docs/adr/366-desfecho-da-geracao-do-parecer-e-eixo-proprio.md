---
id: ADR-366
type: adr
title: "Desfecho da geração do parecer é eixo próprio — `status` continua sendo publicação"
status: Decidido
phase: "A40.l20"
date: "2026-08-06"
amended_at: ["2026-08-07", "2026-08-08"]
relates_to:
  - "[[ADR-204]]"
  - "[[ADR-357]]"
  - "[[ADR-365]]"
  - "[[ADR-199]]"
  - "[[ADR-208]]"
  - "[[ADR-272]]"
  - "[[ADR-295]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 366"
  - "parecer retido"
  - "outcome do PlannerReview"
tags:
  - type/adr
  - status/decidido
  - area/backend
  - area/report
  - phase/a40
---

# ADR-366 — Desfecho da geração do parecer é eixo próprio

**Status:** Decidido (A40.l20) • **Data:** 2026-08-06 • **Lane** [[A40.l20]]

> **Emenda 2026-08-08 — o §D6 dobrava free em `not_generated_yet`, e a copy não
> cabe nos dois.** Feita ao escrever a copy da [[A40.l22]] (decisão do dono).
>
> O D6 abaixo estreita `not_generated_yet` para *"nunca tentou / **free** /
> pendente"*. Os três casos compartilham a causa técnica — sem row, sem artifact
> — mas **não compartilham a ação do usuário**: "free" pede *cadastrar a chave de
> IA*, "pendente" pede *esperar*, e nenhuma frase é verdadeira para os dois.
>
> **`free` aqui não é plano comercial** — e a revisão de copy (`product-designer`,
> 2026-08-08) mostrou que tratá-lo como tal produz duas mentiras. `tier` é BYOK:
> `_classify_llm_config` devolve `"premium"` ⟺ existe `LLMConfig` cuja
> `api_key_encrypted` decripta para texto não-vazio, e cai para `"free"` inclusive
> quando a `FERNET_KEY` foi rotacionada. Copy enquadrada por plano acusaria de
> downgrade quem perdeu a credencial **por falha da plataforma**. A copy do estado
> é enquadrada pelo **mecanismo** (chave de IA), registrado em COPY_GUIDELINES
> §2.2 `@2026-08-08`. Como quem discrimina
> é o servidor (é o próprio D6 que decide isso), dobrar aqui obrigava o cliente a
> desdobrar — e ele não tem como: o tier só chega em `meta.tier_at_generation`,
> que é exatamente o que falta no 404.
>
> **`tier_gated` entra como 5º membro do vocabulário fechado.** Discriminador:
> `PipelineRun.tier_at_run`, **não** o tier atual do workspace — a pergunta do 404
> é por que ESTE relatório não tem parecer, e a resposta não muda quando o cliente
> sobe de plano depois. Usar o tier atual faria um relatório antigo trocar de
> motivo no upgrade, e a copy deriva do motivo.
>
> **Ordem das cláusulas é normativa:** o artifact vence o tier. Run free **com**
> artifact tentou de fato (override, re-run pós-downgrade), e ali `tier_gated`
> mandaria comprar o que já foi executado. Travado por teste próprio contra a
> inversão.
>
> **Consequência fora desta ADR:** `report_not_found` sai do conjunto que a SEÇÃO
> renderiza. Ele é membro legítimo do vocabulário do 404 — o relatório não existe
> —, mas não é ausência de parecer, e a seção dizia *"parecer ainda não gerado"*
> numa página cujo relatório não resolve. Vira estado de erro no cliente. Código
> **desconhecido** segue caindo no conservador: só o caso nomeado mudou de destino.

> **Emenda 2026-08-07 — flip `Proposto` → `Decidido (A40.l20)`.** A condição
> declarada no §Consequências era o merge do **PR2**, não do PR1: a tese "o
> desfecho retido é estado distinto **e alcançável**" só ficava provada quando o
> membro `retido` ganhasse produtor. Ganhou.
>
> **Quatro coisas que a execução mediu diferente do escrito**, registradas aqui
> porque quem reler o texto abaixo merece saber onde ele erra:
>
> 1. **A barreira era UMA, e não estava no filtro.** O texto e a lane apontavam
>    `_should_persist_planner_review`. A medição mostrou que o corpo dele era
>    **dead code** no caminho retido: quem barrava era `if outcome.delivered:` no
>    `_record_stage_result`, um andar acima. O parecer é `degradable`, o retido
>    devolve `success: False`, logo `StageOutcome.degraded`, cujo `.delivered` é
>    `False`. As duas condições do filtro (`success` e `status == "needs_review"`)
>    barrariam **se** a de cima fosse aberta sozinha — contrafactuais, não causa.
> 2. **`persona_hash` nunca barrou.** O PR1 já pusera `_audit_detail` no retorno
>    do retido. A guarda fica, mas o que ela fecha é a **rota de exceção**, cujo
>    detail não tem campo de auditoria algum.
> 3. **O §D6 enumerava 3 códigos de 404 e omitia `parecer_artifact_missing`,** que
>    o router já produzia. Fechar o vocabulário nos 3 escritos faria o snapshot
>    OpenAPI mentir sobre o 4º. O `Literal` entregue tem os **quatro**. O
>    discriminador de `generation_unavailable` é o **artifact**, não `stage_logs`:
>    o produtor o grava mesmo nos ramos de indisponibilidade, e ele sobrevive à
>    degradação — então "sem row + com artifact" isola o caso com exatidão.
> 4. **Copiar o gate de paridade da [[A40.l18]] tal-e-qual produz verde-falso.** O
>    §Consequências manda seguir aquele padrão; o extrator dele usa `[a-z_]+`, que
>    não casa o ponto de `parecer.sigilo` nem a maiúscula de `Gerado`, e devolveria
>    conjunto vazio comparado com conjunto vazio. O gate entregue corrige o
>    character class e tem teste próprio contra essa mutação.
>
> **Não entregue, e por quê:** a copy da UI para `generation_unavailable`. O
> §D6 já declarava que quem discrimina é o servidor e que o cliente chaveia na
> [[A40.l22]]; o hook passa a **transportar** o código, sem escolher palavra.

## Contexto

O desfecho "o parecer foi gerado e o conteúdo foi retido" não existe no modelo.
Em retenção não há row de `PlannerReview`, a API responde 404, e a seção do
relatório cai na copy de "ainda não gerado" — que **mente** para um cliente
premium que pagou a geração.

Medido, e é o que dimensiona esta decisão: **são dois desfechos de retenção, não
um**, mutuamente exclusivos por construção em
[`parecer_strict_enforcement.py`](../../backend/app/services/parecer_strict_enforcement.py)
`enforce_strict_per_item`:

- **Parecer inteiro retido** — `needs_review_reason` preenchido e `dropped=()`.
  O stage devolve `success: False`. Sem row hoje.
- **Itens retidos, parecer entregue** — `dropped` não-vazio e
  `needs_review_reason=None`. A row **já existe** com `status="Gerado"`,
  `items_shown_count` conta a lista **pós-drop** e `items_gated_count=0`
  hardcoded. O drop é invisível: `_check_evidencia` colapsa a tupla em
  `len(decision.dropped)`.

E são **três** eixos empacotados num campo só na formulação original da lane:
publicação (o `status` da [[ADR-204]] §D1), desfecho da geração, e ausência
(não contratado / free / nunca rodou / rodou e degradou).

## Decisão

### D1. `status` fica intocado; o desfecho ganha coluna própria

`PlannerReview.status` continua sendo **exclusivamente** o eixo de publicação da
[[ADR-204]] §D1 — `Pendente → Gerado → Publicado → Superseded`, mesmas
transições, mesmo gate de imutabilidade. **Esta ADR não emenda a ADR-204.**

O desfecho vive em `outcome`, com 4 membros:

| membro | quando | produtor |
| --- | --- | --- |
| `entregue` | sem retenção | caminho de sucesso atual |
| `entregue_com_retencao` | `dropped` não-vazio | `enforce_strict_per_item` — alcançável já no PR1 |
| `retido` | parecer inteiro retido por política ou qualidade | os 3 ramos de política do orchestrator — PR2, atrás da [[A40.l18]] |
| `nao_registrado` | rows anteriores à migration **e** qualquer writer que não declare o desfecho | `server_default` da migration + default do modelo |

O default é `nao_registrado` **nos dois níveis**, e não `entregue`: writer que
esquece de declarar não passa a **afirmar completude**. É o mesmo princípio de
`cost_known` — "zero real" e "desconhecido" precisam ser distinguíveis no tipo,
não por convenção. Há 4 construtores campo-a-campo de `PlannerReview` no repo, e
esse default é o que impede que um deles minta por omissão.

**O argumento decisivo é o desfecho `entregue_com_retencao`:** ele é um parecer
**publicável**. Se o desfecho fosse valor de `status`, `POST .../publish`
responderia 409 (`_conflict_publish`, [`api/planner_review.py`](../../backend/app/api/planner_review.py))
para um parecer perfeitamente publicável. Dois desfechos — um publicável, outro
não — não cabem no eixo de publicação. Reusar `status` também deixaria a
re-geração fora da chain de supersedure da [[ADR-204]] §D3, que só conhece
`Publicado → Superseded`.

Ortogonalidade não é invenção desta ADR: a [[ADR-365]] §D1, um stage antes e na
mesma sprint ([[A40.l10]] PR2), separa proveniência da premissa de elegibilidade
da recomendação pelo mesmo motivo. Colapsar aqui produziria um terceiro
vocabulário para "conselho retido, declarado por classe de motivo" no mesmo
relatório.

### D2. O 409 do publish passa a ser invariante declarada, não acidente de string

Colocar `Retido` em `status` compraria de graça o 409 do
`publish_planner_review` — e é uma objeção legítima, porque publicar um parecer
retido congelaria `immutable_hash` sobre o artifact placeholder, corrompendo
exatamente a defesa que a [[ADR-204]] §D7 existe para construir.

A proteção é preservada **explicitamente**: `outcome == "retido"` ⇒ 409. Duas
linhas, com teste próprio. Invariante declarada é melhor que comparação de
string que funciona por coincidência do vocabulário.

### D3. `retention_reason` — classe fechada de 3, namespaced

`parecer.citacao_nao_confirmada` · `parecer.sigilo` · `parecer.conselho_vedado`

`NULL` ⟺ `outcome ∈ {entregue, nao_registrado}`. Forma: `str, Enum` no padrão
do `ReviewReasonCode` ([[ADR-272]]); coluna DB é `String`, **nunca** `Enum` SQL —
é o que dispensa `ALTER TYPE` e mantém fora do caminho a classe de drift que a
[[ADR-357]] §7 documenta.

**O código nasce como argumento obrigatório do construtor do desfecho**, nunca
derivado por parse de `error_detail`. Duas razões medidas: (a) a
[[A40.l16]] já mudou essas strings uma vez, e regex sobre prosa de operador é o
acoplamento que se quer proibir; (b) no ramo de sigilo a prosa **contém o
próprio termo §13**, então parseá-la para classificar seria transportar o termo
proibido pelo caminho de classificação. Com argumento obrigatório não existe
ramo não-mapeado: produtor novo não compila sem decidir.

Gate correspondente: função **total** `set(MAP_REASON_TO_DTO) == set(Enum)`. Sem
membro genérico de fallback — com o mapa total ele não tem instância, mesmo razor
que corta `dado_insuficiente` (zero produtores).

**Os 4 nomes da 6ª classe do gate de saída de [[PLAN-report-trust]]** — sigilo /
pareamento / severidade / degradação — decompõem-se sem perda: sigilo e conselho
vedado são membros de `retention_reason`; pareamento é uma das 3 camadas hard,
que ao cliente significam todas a mesma coisa (`citacao_nao_confirmada`);
**severidade não é motivo, é regra de escalada** — decide *quanto* foi retido
(item vs parecer inteiro), o que o próprio `outcome` já distingue; degradação de
stage é eixo da [[ADR-357]] §3, não deste aggregate.

### D4. Contador é `items_dropped_count`, com o nome do produtor

`Integer NOT NULL default 0`, separado de `items_gated_count`, cuja semântica de
gating comercial ([[ADR-208]]) fica **inalterada** — ação "comprar" e ação
"reprocessar" não somam no mesmo número.

O nome casa com o produtor (`items_dropped` no summary da verificação) para que a
identidade `review.items_dropped_count == artifact._meta.evidencia_verification.items_dropped`
seja asserível. `withheld`/`retained` foram rejeitados por **prometerem demais**:
existem ao menos 4 mecanismos subtrativos distintos no parecer — gating comercial
por tier, drop por qualidade, truncagem de horizonte (`riscos_truncados`) e o
próprio retido global — e o contador cobre **um**. O termo do cliente ("retidos
na conferência") mora no `COPY_GUIDELINES`, não em nome de coluna.

Assimetria a respeitar: `items_shown_count` é **request-scoped** (recomputado
pós-tier em `_build_response`), `items_dropped_count` é **generation-scoped**.
Não recomputar pós-filtro — daria double-count com o gating.

### D5. `content` é `Optional`, e no retido é `None`

O artifact do desfecho retido é o placeholder de `empty_needs_review_output`:
`pontos_fortes` com 3 itens intitulados `"placeholder"` e `diagnostico_geral`
instruindo *"Inspecione `_meta.error_detail` para diagnóstico"*. A docstring da
própria função declara que ele "não é salvo nem publicado".

Servir 200 sem suprimir o conteúdo trocaria a mentira por uma pior: conteúdo
**fabricado** e vocabulário de operador num relatório patrimonial, com
`items_shown_count=3`. Então `outcome == "retido"` ⇒ `content=None`,
`items_shown_count=0`, decidido **antes** de carregar e filtrar o artifact.

Sanitizar a prosa do placeholder foi rejeitado: seria whitelist a manter para
sempre. `null` é porta fechada, e a invariante "nenhum conteúdo de LLM retido
cruza o boundary" fica enforçada **por tipo** — o `Optional` força erro de
compilação no único consumidor TS.

### D6. Ausência continua 404, com vocabulário fechado de `code`

> ⚠️ **Revisado pela §Emenda 2026-08-08:** o "free" abaixo saiu de
> `not_generated_yet` e virou membro próprio (`tier_gated`), porque a ação do
> usuário difere. O vocabulário fechado tem **5** membros; a lista abaixo é o
> estado de 2026-08-06.

`report_not_found` · `not_generated_yet` (estreitado para "nunca tentou / free /
pendente") · `generation_unavailable` (**novo** — o run tentou e não houve
output: LLM indisponível, ou chamada falhou).

**Os ramos de indisponibilidade não geram row.** Persistir "retido" ali contaria
a mentira invertida — diria "seu conteúdo foi retido" quando nada foi gerado, e
no ramo de LLM indisponível nem houve cobrança. As colunas de auditoria são
`NOT NULL`: uma row ali teria `model_id` *configurado*, não usado — lineage
fabricada, no aggregate cuja razão de existir é lineage auditável. O custo do
ramo de chamada-falhou já tem SSOT em `llm_call_log` ([[ADR-173]]).

Quem discrimina é o **servidor**, não o cliente. O corpo do 404 é tipado com
`responses={404: ...}` para o vocabulário aterrissar no snapshot OpenAPI —
sem isso a [[A40.l22]] chavearia estado numa string que nenhum gate protege.

### D7. Cache carrega a retenção; não se deixa de cachear

`_write_cache` grava o output **já mutilado**, e no hit `_hit_result` não repopula
o summary de verificação — logo o contador cairia a 0 servindo um parecer
parcialmente retido. É a mesma forma de defeito que o bump
`EVIDENCIA_VERIFICATION_VERSION` documenta para caches anteriores, e a causa (o
hit não repopular) nunca foi tocada.

O valor cacheado passa a carregar a tupla de retenção, com bump do composite da
cache key. **Rejeitado "não cachear output mutilado":** drops são comuns, e
cobrar re-geração implícita contradiz a [[A40.l17]], onde a re-geração é o retry
**explícito** do usuário — nunca efeito colateral de política de cache.

## Alternativas rejeitadas

- **Valor novo em `status` (`"Retido"` / `"Degradado"`)** — quebra o eixo de
  publicação para `entregue_com_retencao`, que é publicável; e deixa a
  re-geração fora da chain da [[ADR-204]] §D3. Ver D1.
- **`degraded` / `partial_failure` como token do aggregate** — são os eixos de
  **stage** e de **run** ([[ADR-357]] §3), e não são 1:1 com o review:
  `generate_narratives` degradando dá stage `degraded` + run `partial_failure`
  com o parecer `Gerado`. Token idêntico nos três eixos convidaria à inferência
  falsa "o desfecho do review deriva do status do stage".
- **Tabela filha para a tupla dropada** (padrão `PlannerFieldRequest`) — aquela
  tabela existe porque há superfície de agregação (`top_requested_fields`). A
  tupla dropada não tem consumidor equivalente: o consumidor declarado é o
  tripwire T1 do plano, satisfeito por `count(*) WHERE items_dropped_count > 0`.
- **Membro genérico de fallback em `retention_reason`** — com argumento
  obrigatório no construtor e mapa total, não tem instância.
- **Tri-estado `Optional[int]` no contador** (precedente `cost_known`) — empurra
  desconhecido para a API, a copy e toda agregação futura. D7 remove a causa.

## Consequências

- **Migration:** 3 colunas em `planner_review_metadata`, todas com
  `server_default`. `status` **não** muda em DDL — é `VARCHAR(20)` sem CHECK nos
  dois dialetos, logo não há assimetria SQLite↔Postgres a esconder.
- **`make update-openapi-snapshot` obrigatório:** o DTO ganha `outcome`,
  `retention` e `content` nullable. `content` deixar de ser obrigatório é
  **breaking** no wire — anunciar no PR.
- **`make update-db-schema-reference`** pelas colunas.
- **Snapshot do view-model NÃO se move.** `dogfood_view_model.json` tem zero
  ocorrência de parecer/planner — a seção é aggregate-driven por endpoint
  próprio, e o substrato golden não executa o stage. Rebaselinar produz diff
  vazio ou captura drift alheio: falso-verde. Corrigido no §Critério de aceite
  da [[A40.l20]].
- **Paridade Python↔TS:** os tipos do cliente são espelho **manual**, não
  codegen. Os dois vocabulários novos entram no padrão de gate de paridade que a
  [[A40.l18]] PR1 estabeleceu, em vez de tripwire negativo auto-deletável — o
  repo já substituiu um desses nesta mesma janela por ser one-shot.
- **`nao_registrado` torna o PR1 client-facing no merge:** todo relatório
  existente passa a declarar que o desfecho não foi registrado, em vez de
  afirmar completude implícita sobre runs que sabidamente perderam itens.
  Membro explícito e não `NULL`, pelo mesmo motivo que `cost_known` existe —
  "zero real" e "desconhecido" precisam ser distinguíveis no tipo.
- **Débito nomeado, não corrigido aqui:** (a) `check_orphan_planner_artifacts`
  casa `stage == "E6-parecer"` sem `stage_aliases`, logo é falso-verde hoje;
  ganha a guarda de `_meta.status` neste PR para que corrigir o filtro depois
  não cunhe row "Gerado" para parecer retido, mas o filtro **não** é corrigido
  aqui; (b) free tier cai no mesmo 404 de "ainda não gerado" — é a outra metade
  da mesma mentira, e o flag da [[ADR-208]] §D2 que faria free gerar não existe
  em código; (c) `output_summary` de `stage_logs` expõe a prosa crua por outro
  endpoint; (d) `riscos_truncados` é uma 4ª subtração silenciosa.
- **Esta ADR nasce `Proposto`** e flippa para `Decidido` no merge do **PR2**, não
  do PR1: a tese "o desfecho retido é estado distinto **e alcançável**" só fica
  provada quando o membro `retido` ganha produtor. Se a [[A40.l18]] escorregar
  até a `date_target`, a reversão leva o PR1 e a ADR segue `Proposto` — nenhuma
  ADR `Decidido` descrevendo código inexistente. Regra herdada da [[ADR-358]]
  via [[ADR-357]] §Consequências.
