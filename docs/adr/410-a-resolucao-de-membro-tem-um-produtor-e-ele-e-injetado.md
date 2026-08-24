---
id: ADR-410
type: adr
title: "A resolução de membro tem um produtor, e ele é injetado — não resolvido por dentro do consumidor"
status: Decidido
phase: A40.l77/DE-10
date: "2026-08-24"
relates_to:
  - "[[ADR-089]]"
  - "[[ADR-097]]"
  - "[[ADR-274]]"
  - "[[ADR-301]]"
  - "[[ADR-346]]"
  - "[[ADR-383]]"
  - "[[ADR-394]]"
  - "[[ADR-401]]"
  - "[[ADR-406]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 410"
  - "produtor único de membro"
  - "DE-10"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
---

# ADR-410 — A resolução de membro tem um produtor, e ele é injetado

**Status:** Decidido (A40.l77 · DE-10) • **Data:** 2026-08-24 • **Relaciona**
[[ADR-394]] §Emenda (c) D10 (o ano-base é do membro — **premissa** desta nota,
não objeto dela), [[ADR-089]]/[[ADR-097]] (ISP e config tipada em service de
domínio), [[ADR-401]] (o item é a dívida), [[ADR-406]] §D2 (custo medido de
`tipo`).

> **Esta nota não reenuncia o D10.** O D10 já decidiu **como** se resolve o
> ano-base de um membro, e continua valendo sem alteração. Aqui se decide
> **quantos produtores** existem, **que forma** o resultado tem e **quem o
> constrói** — objetos que a [[ADR-394]] não toca. Teste de falseamento aplicado
> na escrita: se a §Decisão coubesse em *"o D10 também vale para o segundo
> resolver"*, isto seria emenda à 394 e não nota nova.

## Contexto

`e5_analyzer_adapter.analyze_via_store` lê `patrimonio_raw` **uma vez**
(`:560`) e o entrega a **dois** parsers no mesmo escopo léxico: ao
`E5MemberResolver` (`:564`) e ao `PatrimonioCalculator` (`:585`), que chama
`resolve_members` **por dentro** (`patrimonio_calculator.py:146`). O mesmo dict
é resolvido duas vezes, por dois códigos, no mesmo run.

O #1578 corrigiu o eixo de ano-base em um deles. Medido em 2026-08-24 sobre
`origin/main`, com o ano **forçado idêntico** dos dois lados para isolar o que
não é o D10, as duas projeções continuam divergindo: `instituicao` só existe em
uma, `tipo` e `ano_base` só na outra, e a guarda `mesmo_ano` do top-up do titular
só numa delas.

**Não são dois vereditos — são duas projeções com perda do mesmo item.**
`consolidate_from_itens` (`scripts/consolidate_baseline.py:545-587`) emite cada
item já com `proprietario`, `valores_31_12` e `tipo`, mais `instituicao` quando
a fonte a traz. Cada resolver descarta um subconjunto diferente. Por isso
"eleger um autoritativo" só perde dado enquanto qualquer uma das duas projeções
sobreviver: a projeção sem perda é derivável da fonte.

Há ainda **três políticas de ano para o saldo da mesma dívida** no mesmo
payload: os dois resolvers fazem ano-exato-senão-**zero**
(`patrimonio_resolvers.py:508`, `e5_member_resolver.py:473`) e
`endividamento_analyzer._resolve_saldo:147` faz ano-exato-senão-**maior ano do
próprio item**. `tests/test_e5_conservation_invariants.py:194` já acopla os dois
lados; passa hoje porque a fixture é solo e mono-ano.

## Decisão

**D1 — Um produtor do item de membro.** `patrimonio_resolvers` é o site único de
construção. `E5MemberResolver` é deletado, e com ele `_resolve_members` /
`_build_members_from_consolidated` de `scripts/analyze_finances.py:368,531` — já
sem chamador, e resíduo empírico do movimento "extrai o canônico, o velho vira
fachada temporária". `resolve_members` ganha `instituicao` (dado já presente na
fonte) e `ano_base` **por item**, além do por membro que o D10 instalou.

**D2 — A resolução sobe para o adapter e é injetada.** `PatrimonioInputs.members`
passa a ser **obrigatório** e `PatrimonioCalculator` deixa de resolver por
dentro. Isso torna "dois produtores" impossível **por construção**, não vigiado
por gate — o serviço passa a receber objeto de domínio já resolvido em vez de
baseline cru ([[ADR-089]]). O calculator afirma coerência de identidade na
entrada (chaves do value object contra as da config) e **falha alto**: injeção
obrigatória sozinha não cobre "resolvido com a identidade errada".

**D3 — O contrato tipado é o do *par* de membros, não o de cada membro.**
`MembrosResolvidos` frozen em `patrimonio_types.py` carrega os dois dicts mais as
chaves de identidade — é ele que o D2 injeta e sobre o qual a afirmação de
coerência roda. O contrato **não** vai para `config/schemas/`: este dict nasce no
adapter, morre nos analyzers do mesmo stage e nunca é serializado — schema lá
validaria objeto que `DBArtifactStore.write` jamais vê.

> **Ajuste de 2026-08-24, pré-implementação.** A redação original decidia um VO
> tipado **por membro** (`MembroPatrimonial`). Medido ao executar o PR1: não é
> implementável sem mudar comportamento. `resolve_members` tem quatro ramos de
> formato e dois deles **repassam o dict cru do baseline**; e `get_bens`
> (`patrimonio_types.py:361`) devolve **o próprio membro** quando não há chave
> `bens`, então as chaves arbitrárias do layout flat *são* lidas como categorias
> de bem. Um VO de campos fixos as descartaria — perda silenciosa, exatamente a
> classe que esta nota fecha. O VO por membro só fica seguro depois que os ramos
> de passthrough morrerem, e vai junto com o item tipado no §Deferimentos.

Tipar o **item** (`bens[].*`) toca sete consumidores e fica deferido
(§Deferimentos), agora acompanhado do VO por membro.

**D4 — Uma política de ano para o saldo de dívida: o ano do próprio item.**
Ausência é ausência, nunca `0` — [[ADR-346]] aplicada no grão em que a
[[ADR-394]] §D10 a aplicou para bens. `endividamento` já publica
`saldo_ano_referencia` por item ([[ADR-401]]), então a data continua no grão
certo e a [[ADR-383]] §6 é satisfeita onde deve. Consequência a declarar antes
do merge: onde a dívida tem `{2022, 2023}` e o domicílio escolhia 2022, o saldo
do item se move.

**D5 — O ramo dict do E1.5 v2 sai dos resolvers.** Não há produtor de
`investimentos_financeiros_consolidados` no repo — todas as ocorrências são
leitores. O conhecimento do shape agregado já mora, corretamente e num lugar só,
em `BaselineNormalizer` (`:131-162`). Nos resolvers ele é uma bomba: as chaves
são `<membro>_<ano>` e **todas** as do membro são somadas, então membro com
declaração de dois anos no mesmo agregado tem o patrimônio dobrado. O
normalizador ganha `review_reason` tipado quando recebe `investimentos_consolidados`
já como dict e por isso **não** converte — hoje ele pula em silêncio.

**D6 — `frescor` ganha leitor nesta lane.** O campo existe desde a [[ADR-394]]
§Emenda (c) e não tem consumidor (DE-9). Ele é alimentado por
`titular_data["ano_base"]` (`patrimonio_calculator.py:163`), campo que **só** o
produtor sobrevivente emite: enquanto os dois existirem, qualquer superfície
alimentada pelo outro tem `frescor` nulo por construção. Esta é também a
primeira vez que o campo fica não-nulo **e** não-uniforme entre membros — antes
dela era trivialmente constante e dar-lhe leitor não teria o que exibir.

## Gate

O gate de **comparação entre superfícies** que a lane pedia é gate para o
desenho que o D1/D2 deletam. O que fica de pé:

1. **Estrutural** — `PatrimonioCalculator` não tem resolver para chamar
   (`members` obrigatório). Teste de construção, não de valor. É esta peça que
   fecha a classe.
2. **Conservação, não comparação** — `Σ tabela_classes == total_financeiro` em
   cents exatos, identidade relacional no mesmo payload, na forma que
   `tests/test_e5_conservation_invariants.py` já usa. O D1 unifica o produtor do
   **item**, não o da **agregação**: `patrimonio.investimentos_conjuge` passa por
   `valor_publicavel` (que devolve `None`) enquanto `tabela_classes` soma itens
   — dois caminhos de agregação sobrevivem, e é conservação que os prende.
3. **Contradição** — `n_posicoes > 0 ⇒ status ∈ {apurado, zero_apurado}`.
   Resolve o critério que a lane escreveu sobre um campo `valor` que
   `MembroInstituicoes.to_dict()` não publica, **sem** criar um quarto lugar
   onde o dinheiro de um membro é afirmado. **Obrigatório declarar o
   denominador medido**: `cobertura_investimentos` é `[]` em 6/6 artefatos
   pré-#1550, então este gate é vacuoso sobre o corpus histórico e só tem
   extensão em run novo — sem a declaração, passa verde por vazio.

A comparação de valor entre superfícies rebaixa de gate a **prova por mutação**:
reverter o eixo por membro deixa vermelho o teste do cônjuge **e** o do titular.
Critério só sobre o cônjuge é satisfazível com o payload errado.

Um `dev/check_*.py` por regex sobre call-sites fecha sintaxe, não classe —
entra só se sair de graça, nunca como substituto de (1).

**Precondição de todos**: fixture de dois membros em anos disjuntos, shape
`itens[]`, PII-zero. A fixture atual (`minimal-baseline-1.5_consolidated.json`)
é `membros: ["david"]`, `patrimonio_por_ano: ["2024"]` e **sem**
`investimentos_consolidados` — estruturalmente incapaz de exibir o caso, e é por
isso que 98 testes verdes e o golden de execução não viram nem o defeito nem o
fix do #1578. Ela é reaproveitada inteira pelo DE-7.

## Consequências

Sete superfícies se movem num único payload: `tabela_classes`, `top_ativos`,
`instituicoes_por_membro`, `total_financeiro`, reserva de emergência, score
(que lê a reserva canônica) e endividamento. Duas de segunda ordem, que não
aparecem no diff: `reserva_liquidez._is_liquid_item:221` monta o haystack com
`instituicao`, então portar o campo **melhora** a detecção de renda fixa
ilíquida e **move** a reserva; e `_split_dividas` de B tem substring crua
(`e5_member_resolver.py:237`) que morre com a unificação.

**Rebaseline é não-monetário e não exige a janela J5.**
`test_e5_conservation_invariants.py` roda sobre fixture sem listas consolidadas
e afirma **identidades relacionais**, não valores fixos — número que se move não
as quebra; quebra quem muda *quais termos entram na identidade*, que é o DE-7,
não isto. `backend/tests/snapshots/dogfood_view_model.json` tem um membro só, e
o único campo que flipa é `top_ativos[].autoridade`. Critério: `dev/golden_diff.py`
com `value_delta == 0` em todo campo monetário.

**Medição sobre o corpus não se apaga nem se reprocessa.** Taxa lida de artefato
E5 armazenado (DE-7, DE-8) fica congelada no eixo que a produziu e não é
comparável através desta fronteira. Sem backfill (precedente [[A40.l69]]), mas
toda taxa publicada depois desta nota **declara o run a partir do qual o produtor
é único**. Reprocessar baseline antigo com o código novo produz valor que nunca
foi publicado — foi exatamente a confusão que o §Ataque A0 da lane pegou.

## Alternativas rejeitadas

- **Portar `anos_base_por_membro` para o segundo resolver.** Sem a guarda
  `mesmo_ano` o top-up subtrai R$ 110.130,67 do titular (medido) — família
  `unattributed → titular` que a [[ADR-394]] §D8 cortou. E escreve a terceira
  cópia da regra num arquivo que se quer apagar.
- **Resolver canônico novo, com os dois virando fachadas finas.** É o movimento
  que já produziu os dois resíduos órfãos que o D1 enterra. Com `tipo` medido
  inerte pela [[ADR-406]] §D2, o superset é o produtor atual mais um campo —
  módulo novo seria diff maior e duas janelas de rebaseline.
- **Manter os dois com contrato escrito.** Contratar a divergência não a impede.
  O precedente da [[ADR-392]] §D3 (dois resolvers obedecendo a mesma regra) não
  autoriza aqui: lá o segundo é duplo de teste implementando o mesmo *port*, com
  paridade testável por construção; aqui os dois são caminhos de produção sem
  port comum.
- **Emenda à [[ADR-394]].** Ela decide *como se afere que um membro foi medido*;
  esta decide *topologia de produtor*, *forma do resultado* e *eixo do saldo de
  dívida*. A 394 já está em quatro blocos de emenda, e a atomicidade da
  [[ADR-182]] existe para isto. Sem `## Emenda` na 394 — `relates_to` resolve a
  referência sem disparar `dev/check_adr_amendment_signal.py`.

## Deferimentos

**Item `bens[]` tipado + VO por membro (2026-08-24, dono: `data-engineer`).** Sete
consumidores leem `dict[str, Any]`, e `if item.get("instituicao")` faz
**presença de chave** ser load-bearing — a mesma família que a [[ADR-394]] §D9
queimou (`bens` com 4 chaves sempre ⇒ predicado constante). Item tipado com
`None` explícito mata a família. Fora desta lane porque tocaria sete
consumidores e atrasaria a J5, que está atrás dela. O VO por membro entra aqui
pelo motivo do §D3: enquanto `resolve_members` tiver ramos de passthrough, campos
fixos descartam chave que o layout flat usa como categoria de bem. Condição de
retomada: após o D1/D2 mergeados, os ramos de passthrough mortos e o rebaseline
fechado.

**Proveniência do numerador da reserva (2026-08-24, dono: a nomear · P1).**
`_filter_liquid` pula `valor <= 0`, então membro cujos itens somam zero sai
`LiquidezMembro(0, 0, fonte="irpf")` — proveniência afirmada sobre medição que
pode não ter havido — em vez de cair no ramo `agregado_sem_itens`. Junto com
ele, a ressalva de KPI para o balde `None` (`reserva_liquidez._dec(None) == 0`,
desenho datado e travado por `test_reserva_conta_membro_nao_apurado_como_zero`,
com a ressalva já nomeada como follow-up da [[A40.l69]]). Os dois são o mesmo
objeto de decisão — vocabulário de estado do numerador — e sobrevivem à
unificação, então não entram no rebaseline desta nota.

**`autoridade` não distingue produtor de substring (2026-08-24, dono:
`prompt-engineer`/`data-engineer` · território [[ADR-400]]).**
`classify_asset_outcome` concatena `tipo` e `descricao` numa haystack única
(`asset_classifier.py:256`), então `autoridade == "keyword"` não separa "o
produtor declarou o tipo" de "casei substring em texto livre", embora a
[[ADR-400]] diga que o degrau 1 é `tipo`. Registrado aqui para não se perder;
decisão é da 400.
