---
id: A40.l81
type: lane
title: "Diagnóstico sem canal de saída: o stage que não pausa entrega razão no artefato e ela não chega nem à tabela nem ao usuário"
sprint: A40
plan: PLAN-deterministic-authority
status: shipped
ship_pr: 1697
ship_date: "2026-08-25"
priority: P0
branch_slug: a40-l81-diagnostico-sem-saida
adrs:
  - "[[ADR-357]]"
  - "[[ADR-404]]"
  - "[[ADR-272]]"
  - "[[ADR-411]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/observability
---

# A40.l81 — Diagnóstico sem canal de saída (RV8-09)

> **Vai primeiro na fila do §r8.** Não porque seja o mais grave — é o que torna
> RV8-01 e RV8-19 **observáveis em produção** sem depender de outra revisão
> manual. Consertar os outros antes é consertar às cegas de novo.

## O fato, re-medido no r8 (run `d0f6260a`)

O artefato do `consolidate_baseline` — stage WARN-first, que **não pausou** —
carrega **4 razões**:

| onde | código | n |
|---|---|---|
| `validation.review_reasons` | `domain.baseline_divergence` | 2 |
| `imoveis_consolidados[].review_reasons` | `domain.property_identity_uncanonical` | 2 |

A tabela `review_reasons` do mesmo run tem **2 rows, ambas de `analyze_finances`**
— o único stage que pausou. Cobertura do stage WARN-first: **0 de 4**.

**Refutado antes de virar pista falsa:** não é o `_drop_unknown_codes`. Os dois
códigos **estão** na allowlist de `config/schemas/review_reason.schema.json`
(24 códigos). A causa é que a chamada nunca acontece fora do ramo de pausa.

## Por que "mover a chamada" fecha um terço

`record_review_reasons` tem call-site único: `backend/app/tasks/pipeline_task.py:1166`,
dentro de `_record_stage_needs_review` (`:1150`), que só roda no desfecho
`needs_review`. Mas esse bloco faz **três coisas acopladas**, e as três se perdem
juntas:

1. **Sanitiza** — `sanitize_review_reasons(validation.get("review_reasons"))` (`:1154`).
2. **Projeta para o usuário** — `_workspace_and_issues` (`:1099-1107`) transforma
   razão em `validation_issues`, que entram no `StageReview` (`:1139`) e chegam ao
   frontend por `GET /runs/{run_id}/reviews` ([[ADR-272]]).
3. **Persiste o analítico** — `record_review_reasons` na tabela.

**São dois sinks com audiências diferentes**, e a lane tem de decidir os dois:

- **`StageReview.issues` → usuário.** É a superfície que a pessoa vê. Hoje
  `StageReview` significa *"alguém precisa aprovar"*. Publicar aviso de um run que
  **completou** muda o significado do objeto — isso é **decisão de produto**, não
  encanamento. Co-design `product-designer` + `senior-cto`.
- **Tabela `review_reasons` → analítico.** Hoje é **write-only**: a varredura por
  leitor em `backend/` e `frontend/src/` não achou nenhum consumidor de dado (só
  `review_reason_boundary.py`, que lê o *tipo* da coluna). Ver §Armadilha.

## Armadilha central: consertar só a escrita repete o defeito que o r8 já achou três vezes

Fazer a razão chegar a uma tabela **que ninguém lê** é exatamente o padrão de
RV8-17 (`nao_classificado_itens` no payload com zero consumidores) e RV8-12
(campos `null` por construção no snapshot). O r8 registrou essa classe três vezes.

**A lane não está fechada enquanto não houver leitor.** Ou entrega um consumidor
junto (a rota mais barata: o próprio `review_snapshot`/`compare_reviews`, que hoje
não olha para razões), ou **declara por escrito quem vai ler e quando** — com dono
e data, no formato de deferimento que a [[ADR-356]] estabeleceu. Escrita sem
leitor declarada como "entregue" é falso-verde.

## Segunda armadilha: as razões têm duas formas, e o sink só conhece uma

O sink lê `validation.get("review_reasons")` — a coleção **de topo**. As razões
**por item** (`imoveis_consolidados[].review_reasons`, produzidas por
`property_identity_enricher.py`) não estão nesse caminho. No r8 elas eram **2 das
4**.

Um fix que move a chamada e não trata o aninhamento fecha metade **e fica verde**.
Decida explicitamente: o produtor promove razão de item para
`validation.review_reasons` (o enricher já constrói o dict), ou o sink caminha as
coleções aninhadas. Uma das duas, declarada.

## Terceira armadilha: o gate óbvio é cego pela mesma metade

O gate natural — *"roda um stage WARN-first e afirma
`count(review_reasons) == len(artefato.validation.review_reasons)`"* — compara
contra a coleção **de topo**. Com as razões de item fora dela, esse gate
**certifica o meio-fix**: passa verde sobre 2 de 4.

O predicado tem de contar a razão **onde quer que ela esteja no artefato**
(topo + aninhadas), senão o instrumento nasce cego para o caso que motivou a lane.
Precedente da classe: [[A40.l59]] e [[A40.l25]].

## Restrição dura: a ordem da [[ADR-404]]

O comentário em `pipeline_task.py:1145-1148` não é decoração:

> *Ordem obrigatória (ADR-404): controle commita primeiro e sozinho; o analítico
> vem depois, em sessão própria. O inverso grava razão de pausa para um run que
> pode nunca ter pausado.*

Qualquer reposicionamento da chamada preserva: (a) leitura em sessão própria
**antes** da transição (`_workspace_and_issues` já faz isso); (b) sink analítico
**depois** do commit de controle, em sessão própria, **fail-open** (`record_review_reasons`
nunca levanta, por decisão da ADR-404). Há hook de pre-commit
(`Diagnóstico não divide sessão com transição de run`) — ele reprova o atalho.

## Escopo

| Peça | Superfície | Decisão |
|---|---|---|
| Sink em todo desfecho | `pipeline_task.py` — caminho de saída de stage, ao lado de `_mark_stage_log_*` | encanamento, respeitando ADR-404 |
| Razão de item | `property_identity_enricher.py` **ou** o sink | promover no produtor **ou** caminhar aninhadas — declarar qual |
| Superfície do usuário | `StageReview.issues` / `GET /runs/{run_id}/reviews` | **produto**: run completo pode carregar aviso sem virar "aprove isto"? |
| Leitor do analítico | `dev/review_snapshot.py` (candidato barato) | sem leitor, a lane não fecha |
| Gate | teste novo | conta razão em **qualquer** posição do artefato |

## Critério de aceite

**Corretude** — para um stage WARN-first que não pausa, toda razão do artefato
tem row correspondente. Medido com o corpus que produziu o caso: 4 razões no
artefato do `consolidate_baseline` ⇒ 4 rows.

**Completude** — as duas formas cobertas (topo + item). O gate falha se qualquer
uma sumir. Nenhum stage fica de fora por omissão: o sink roda no caminho de saída,
não num ramo.

**Consistência** — `StageReview` continua significando uma coisa só. Se aviso de
run completo entrar ali, o vocabulário muda **explicitamente** (campo de natureza,
não sobrecarga silenciosa do mesmo objeto); se não entrar, a decisão fica
registrada com o porquê.

**Precisão** — a razão persistida preserva o `stage` produtor real e o locator do
item, não o nome do stage que estava rodando. Sem isso o operador recebe ponteiro
que não reencontra — o mesmo defeito de RV8-19.

**Prova de fecho (o predicado que o r9 mede)** — num run em que nenhum stage pause,
`review_reasons` **não** fica vazia se algum artefato carregar razão; e existe pelo
menos um consumidor que lê a tabela e falha/alerta quando ela cresce.

## Volume e retenção

Escrever em todo desfecho multiplica rows. `review_reasons` tem FK para
`pipeline_runs` (classificada por [[ADR-371]]) — confirme o `ondelete` e se a poda
de artefatos alcança a tabela. Row de diagnóstico que sobrevive ao run que a gerou
é lixo com FK.

## Rastro

Achado RV8-09 do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`, 2026-08-24).
Cru off-git em `storage/<uuid>/reviews/20260824-2235-d0f6260a/`. As medições acima
foram refeitas nesta lane, não copiadas da revisão.

## Fecho — 2026-08-25 (#1697 · [[ADR-411]])

**A lane tinha a causa pela metade, e a metade que faltava invalidava o fix que
ela desenhou.** Ao medir os `detail` de todos os stages do run `d0f6260a`:

| stage | desfecho | Σ occ no `detail` | persistido |
|---|---|---:|---:|
| `extract_baseline` | entregou | 11 | 0 |
| `reconcile_transactions` | entregou | 28 | 0 |
| `analyze_finances` | **pausou** | 3 | 3 |
| `consolidate_baseline` | entregou | 0 (no artefato: 4) | 0 |

Duas correções ao enunciado:

1. **A escala.** Não são 4 ocorrências perdidas: são **43 de 46** (6,5% de
   cobertura). O volume dominante — 39 — vem de `reconcile_transactions` e
   `extract_baseline`, que já emitiam no canal certo e só precisavam que o sink
   rodasse fora do ramo de pausa. A lane dimensionou o caso pelo stage errado.
2. **O canal.** O `detail` do `consolidate_baseline` **não tem bloco `validation`
   nenhum** — as 4 razões existem só dentro do artefato. O §Escopo desta lane
   dizia "sink em todo desfecho · encanamento"; sozinho ele colheria **zero**
   para o stage que deu origem ao achado. Faltava o produtor declarar no canal
   que o sink lê ([[ADR-411]] D2b).

**As três armadilhas, todas alcançadas.** A tabela ganhou leitor (coletor →
snapshot → `compare_reviews`, perna HARD quando o canal emudece). As duas formas
estão cobertas por um caminhamento único, usado por sink, produtor e gate. E o
gate não é cego pela mesma metade: **medido por mutação** — sink só na pausa
reprova 5/6, colheita só no topo reprova 3/6.

**Um número do §Critério estava errado.** "4 razões ⇒ 4 rows" é **2 rows** com
`occurrence_count` 2 sob a consolidação da [[ADR-272]] Fase 2. O predicado que o
gate mede é Σ `occurrence_count`; `count(rows) == 4` reprovaria o comportamento
correto.

**Fica deferido, com dono e condição** ([[ADR-411]] §Deferimento): a superfície
de usuário para aviso-sem-pausa. `StageReview` continua exclusivo do contrato de
pausa — publicar aviso de run completo ali passaria a pedir aprovação para um run
que não parou, e `resume_run` depende disso.

**Retenção conferida:** `review_reasons.pipeline_run_id` já é FK
`ON DELETE CASCADE` ([[ADR-371]]) — a row morre com o run. Nada a fazer.
