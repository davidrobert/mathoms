---
id: TRACK-a40-l2-3c2-superficie-do-colapso
type: track
title: "Track A40.l2 PR3c2 — a superfície do colapso cross-documento (contador da S2 + caption da V0)"
lane: "[[A40.l2]]"
sprint: A40
plan: PLAN-report-trust
status: ready
created_at: "2026-08-07"
agent_role: product-designer
tags:
  - type/track
  - sprint/a40
  - status/ready
  - priority/p0
  - area/report
  - area/frontend
---

# Track A40.l2 PR3c2 — a superfície do colapso cross-documento

> **Aberto junto do PR3b**, como a [[A40.l2]] §"Ordem de trabalho" manda: o 3c2 é o **long
> pole real** da lane (frontend + snapshot + brief), não o 3d. Abrir tarde é o que faz o
> enforce ficar pronto e esperar semanas pela tela.

**Depende de:** `3c1 — o dado` (carrier E3→E4→E5 + `$defs/remocao`). Sem o campo no E5 não
há o que renderizar. **Não** depende do 3d nem do 3b.

## Por que é bloqueante do PR3, e não polimento

O `financial-planner` cravou como **salvaguarda nº 1** (lane §"Salvaguardas de produto"):
sem a linha visível, *"o agregado fica irreconciliável contra o extrato do banco, e para o
planejador B2B2C, que responde profissionalmente pelo número, ledger irreconciliável é veto
de adoção"*. O erro que o enforce corrige não é +19% na receita — é **+63% no superávit**, e
entra na janela 12m que é denominador de todo headline.

> **"Apagar dinheiro real não é a quebra de confiança pior — apagar sem dizer é."**

## Escopo — três sítios, e o terceiro precisa ser medido antes

**1. Contador na S2 (Fluxo de Caixa).** *"N lançamentos consolidados por sobreposição de
documentos, em M meses"* — o **fato**, nunca a lista (o detalhe da remoção vai para ops/E7,
salvaguarda nº 5). Aterrissa no metadata de `fluxo` do `analise_financeira`.

**2. Caption da V0, derivado do dado — não hardcoded, não flag de migração.** Regra
**corrigida** pela §D6 para **cruzar zero**: dispara quando **exatamente um** dos dois lados
(relatório atual, snapshot comparado) tem `count > 0`. A regra por *presença* acenderia em
quase todo workspace — a maioria tem zero colapsos —, produzindo o falso-positivo acusatório
que a D6 existe para impedir; e a forma que cruza zero cobre **de graça** o rollback (flag
off ⇒ receita salta +19% de volta com "▲ ótimo"). **Sem suprimir cor** — o delta de
patrimônio é legítimo.

**3. 🔴 A prosa DENTRO da S2 — medir e declarar o resultado no PR.**
`sectionSummarySource.ts::changelogSuffix` anexa ao parágrafo de abertura da seção o
`ChangelogEntry.summary`, cujo template rende *"Receita total recuou R$ X desde o relatório
anterior (−19,0%)"*. **Rodapé de 12px não vence narrador de 14px acima dele.** Se a prosa
narrar a queda, a salvaguarda nº 1 **não** está cumprida por contador+caption e a prosa é
**bloqueante**.

> **Decisão do dono, não do agente:** se o conserto da prosa é da l2 ou vira lane própria é
> mudança de escopo de lane P0. **Meça, declare, e pergunte** — não decida sozinho.

## Armadilhas verificadas — cada uma já custou um dia nesta lane

- **`dev/golden_diff.py::is_monetary` é monetário-por-DEFAULT.** `count` está em
  `_NON_MONETARY_EXACT`, mas `lancamentos` e `valor_cents_credito` saem **monetários** ⇒
  `to_cents` multiplica por 100 ⇒ snapshot e `delta_cents` saem **100× errados no mesmo PR**
  cujo aceite manda conferir com `golden_diff`. Payload decidido:
  `consolidacao_cross_documento = {count, meses, receitas_omitidas, despesas_omitidas}`,
  dinheiro em **reais** como o resto de `fluxo_caixa`, magnitudes **separadas por direção**,
  nunca net assinado.
- **Campo OMITIDO quando `count == 0`** (precedente ADR-132 T2). O argumento decisivo não é
  estético: `parecer_orchestrator` mete `sha256(json.dumps(e5_data, sort_keys=True))` na
  chave de cache ⇒ campo sempre presente forçaria **regeração integral do parecer em toda a
  base** num PR que corrige zero — contra o hard-stop de budget da [[ADR-173]], e com
  precedente de degradação em regeração (incidente 2026-08-03).
- **Nome de chave decide formatação no parecer.** Chave que o `is_monetary` do renderer leia
  como dinheiro vira `R$` na prosa. **Meça antes de fixar o nome.**
- **Supressor não-declarado no frontend (herdado da [[A40.l10]]).** `dedupeBySemanticKey` em
  `frontend/src/components/report/utils/curadoriaDestaques.ts` colapsa itens por chave
  semântica de **regex sobre texto**, *first-wins*: o sobrevivente depende da **ordem de
  chegada**. Duas consequências: (a) o contador declarado pode **divergir** do que o card
  renderiza; (b) **asserção sobre payload não prova o renderizado** — teste no nível de
  render, sempre.
- **Wrappers `base-ui`:** `Select.Value` sem `items` mostra o value cru; variant custom do
  shadcn faz ponte por `data-attr` — CSS vivo não prova comportamento. Popup é async: teste
  que só falha em máquina rápida precisa de `await`, não de `sleep`.

## Aceite

- Contador da S2 e caption da V0 renderizam; **nenhum** dos dois contém identificador de
  máquina (`stage`, `E3`, `E5`, `error_detail`, digest, hash).
- Caption **cruza zero nos dois sentidos**: flip (0 → N) **e** rollback (N → 0), cada um com
  teste próprio. Só o flip deixa metade da D6 inexercitada.
- **Prova por mutação** no gatilho do caption: torná-lo por *presença* deixa um teste
  vermelho. Sem isso a regra volta a ser a que a D6 revogou.
- Teste no nível de **render** (não de payload) para o contador — ver `dedupeBySemanticKey`.
- **Rebaseline explícito** dos snapshots visuais (light+dark) no próprio PR. O job visual não
  é bloqueante, então **não pode ficar para o próximo agente**. View-model novo ⇒
  `MATHOMS_UPDATE_SNAPSHOT=1` no snapshot do view-model.
- `golden_diff` conferido **com o sinal do delta declarado** (§Decisões nº 5 do sprint) — e
  com o resultado do `is_monetary` sobre cada chave nova declarado no PR.
- Resultado da medição do item 3 (prosa da S2) **no corpo do PR**, com a pergunta ao dono se
  a prosa narrar a queda.

## Não é escopo

- Ligar o enforce (3e) — ele exige os 9 eixos do §Critério de saída, incluindo **ensaio de
  rollback medido**.
- A V0 **julgar** (`avaliação ruim`) mudança de método em vez de movimento real: a noção de
  **base não-comparável** pertence ao plano
  [SNAPSHOT_CHANGELOG_V3](../../../plan/SNAPSHOT_CHANGELOG_V3/_README.md) — abrir item lá,
  débito registrado, não desta lane.
- A classe de duplicação intra-proveniência cross-arquivo (**716 rows**) — é da [[A42.l5]].
  Diga isso no PR3, senão alguém conclui que a classe estrutural fechou.

## Referências

- Lane: [[A40.l2]] §D6 · §"Salvaguardas de produto" · §"Duas armadilhas de nome"
- ADRs: [[ADR-354]] · [[ADR-364]] · [[ADR-347]] · [[ADR-173]]
- Gatilhos de especialista: `product-designer` (componente + copy) · `financial-planner`
  (o que o número mostra) — em paralelo, no **planejamento**, não no review do PR pronto.
