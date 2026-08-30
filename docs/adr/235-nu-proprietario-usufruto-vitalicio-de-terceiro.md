---
id: ADR-235
type: adr
title: "Classificação `nu_proprietario`: imóvel em nu-propriedade com usufruto vitalício de terceiro"
status: Decidido
phase: A16
date: "2026-05-20"
decided_at: "2026-05-20"
amended_at: ["2026-08-29", "2026-08-30"]
relates_to:
  - "[[ADR-142]]"
  - "[[ADR-143]]"
  - "[[ADR-145]]"
  - "[[ADR-186]]"
  - "[[ADR-188]]"
  - "[[ADR-199]]"
  - "[[ADR-215]]"
  - "[[ADR-216]]"
  - "[[ADR-225]]"
  - "[[ADR-227]]"
  - "[[ADR-340]]"
  - "[[ADR-420]]"
  - "[[ADR-423]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 235"
  - "nu-propriedade"
  - "usufruto vitalício"
  - "nu_proprietario classification"
tags:
  - area/methodology
  - area/persistence
  - area/pipeline
  - area/backend
  - area/report
  - methodology/cerbasi
  - methodology/perini
  - phase/a16
  - status/decidido
  - type/adr
---

> **Emenda 2026-08-30 (auditoria cláusula-a-cláusula · [[A40.l95]]):** a decisão central
> está entregue — o enum funciona e os três invariantes são protegidos por testes que
> **discriminam**. Mas **quatro dos nove critérios de aceite não foram cumpridos**, e dois
> sítios da vault afirmam que foram. Cada cláusula em aberto recebeu disposição explícita —
> ver [§Emenda](#emenda--disposição-cláusula-a-cláusula-2026-08-30).

> **Emenda 2026-08-29 ([[A40.l95]] · `RR6-02` da rodada U2):** o item **4** do §Decisão
> ("Concentração total vs renda") nunca teve produtor, e a métrica que shipou faz o
> **oposto** dele. A cláusula ganhou dono — ver
> [§Emenda](#emenda--o-item-4-era-cláusula-não-financiada-e-ganhou-dono-2026-08-29).

## Contexto

[[ADR-215]] fixou o enum `classification` para imóveis com 6 valores: `residencia_principal | uso_pessoal | locado | comercial | especulacao | desconhecido`. O enum modela **uso econômico** (gera caixa? uso próprio? terreno improdutivo?) e governa três decisões críticas: (1) filtro de cap rate em [[ADR-216]] (`INVESTMENT_CLASSIFICATIONS = locado, comercial, especulacao`), (2) inclusão em `investivel_efetivo` em [[ADR-142]] (`_CLASSIFICATIONS_GERADORAS = locado, comercial` quando toggle on), (3) split cat_1/cat_2 em [[ADR-145]].

**Caso real observado (workspace dogfood `98432212-…`, 2026-05-20):** cliente é **nu-proprietário** de imóvel cujo antigo dono detém **usufruto vitalício gratuito** — usufrutuário mora sem pagar aluguel, e o cliente consolida propriedade plena ao falecimento. Hoje: zero fluxo, ilíquido por contrato civil até evento biológico, no IRPF pelo custo da nu-propriedade (deságio de 30-60% sobre valor pleno conforme expectativa de vida do usufrutuário, tabela AT-2000).

Nenhum dos 6 valores captura fielmente:

- `uso_pessoal` (a aproximação atual) — neutraliza corretamente em cap rate e IF, **mas** agrupa com "casa de praia onde filho mora" e apaga três sinais distintos: **liquidez** (uso_pessoal pode vender pleno; nu-propriedade só vende com deságio), **sucessão** (se nu-proprietário falece antes do usufrutuário, herdeiros recebem nu-propriedade onerada + ITCMD sobre nu-propriedade), e **expectativa de fluxo futuro** (vai virar gerador em horizonte estocástico).
- `especulacao` — terreno improdutivo aguardando valorização; nu-propriedade tem uso de terceiro, não é especulativa.
- `locado` / `comercial` — não há fluxo para o cliente.

**Frequência esperada na base** (estimativa qualitativa do `financial-planner`): caudal moderado — 5–15% dos workspaces em ICP de wealth-tech BR (família com patrimônio diversificado e planejamento sucessório ativo). Casos típicos: (a) compra com reserva de usufruto para pai/mãe (sucessório reverso), (b) recebimento por doação com reserva de usufruto do doador, (c) compra de imóvel onerado de terceiro. Não é caudal raro.

**Razão de abrir ADR ([[ADR-188]] policy "ADR Proposto antes de PR P0/P1"):** mudança em invariante crítico — extensão do enum `classification` toca CHECK constraints (2 tabelas), filtros em adapter, classifier, type TS, dropdown UI, prompt do parecer E6 ([[ADR-199]]). Sem ADR, vira dead code drift entre camadas.

## Decisão

Adicionar **`nu_proprietario`** ao enum `classification` em [[ADR-215]]:

```
classification ∈ {
  residencia_principal,
  uso_pessoal,
  locado,
  comercial,
  especulacao,
  nu_proprietario,          # NOVO — nu-propriedade com usufruto vitalício de terceiro
  desconhecido,
}
```

**Semântica:** ativo no patrimônio do cliente, com ônus civil (usufruto vitalício de terceiro), zero fluxo de caixa hoje, ilíquido até evento futuro condicional. Comporta-se como `uso_pessoal` em todos os filtros computacionais (não-gerador, fora de cap rate, fora de `investivel_efetivo`), **mas é entidade semântica distinta** para fins de relatório, parecer LLM e diagnóstico de liquidez.

**Categoria patrimonial:** cat_2 **não-gerador** (alinhado com [[ADR-145]] + [[ADR-142]]). Não cria categoria nova "Patrimônio ilíquido condicional" — eixo extra polui split sem ganho prático.

**Cap rate ([[ADR-216]]):** fora de `INVESTMENT_CLASSIFICATIONS`. Sem aluguel ≠ cap rate zero — é cap rate **indefinido**; não puxa média do portfolio pra baixo.

**`investivel_efetivo` ([[ADR-142]]):** invariante explícito — nu-propriedade **nunca** entra, independente do toggle `imoveis_no_if`. Conservadorismo Perini/Cerbasi: ativo que não pode ser convertido em renda passiva no horizonte do plano não financia IF.

**Sinais que o relatório deve surfaçar** (resgatados da análise do `financial-planner` e movidos para critério de aceite):

1. **Liquidez condicional.** Bucket dedicado "Ilíquido condicional" no breakdown de liquidez — não soma em "ativos disponíveis < 30 dias" nem em "líquido < 12 meses".
2. **Aviso sucessório.** Surfaçar no parecer LLM (E6, [[ADR-199]]) nota: se nu-proprietário tem dependentes, revisar seguro de vida para cobrir ITCMD da consolidação caso ele faleça antes do usufrutuário.
3. **Valor IRPF ≠ valor mercado consolidado.** UI MembersTab + relatório §Imóveis explicitam que `valor_brl` reflete custo da nu-propriedade (descontado), não o valor potencial após consolidação. Captura de `valor_mercado_consolidado` opcional fica em follow-up — mesma estrutura do `property_market_value` de [[ADR-227]].
4. **Concentração total vs renda.** Entra em "concentração imobiliária total" (denominador PL), **não** em "concentração de imóveis de renda".
5. **Parecer LLM (E6) recebe contexto explícito.** Prompt menciona nu-propriedade e instrui a **não** recomendar venda como solução de liquidez (recomendação tecnicamente errada e cara em credibilidade).

## Alternativas consideradas

**(B) Flag ortogonal `has_usufruct_of_third_party: bool` + campo opcional `expected_extinction_year: int | null` em `workspace_property_overrides`, mantendo `uso_pessoal` no enum.**
Rejeitada. Viola SRP do override: `classification` deixaria de ser axis único de decisão, surgindo espaço de estados inválidos (`flag=true ∧ classification=locado`) que exigem CHECK composto + validator no aggregate (padrão de discriminator [[ADR-186]]) — mais superfície de manutenção que (A). `expected_extinction_year` é YAGNI no JTBD atual: cliente não estima óbito do usufrutuário; produto não opera em tábuas atuariais (precisão falsa custa mais que silêncio honesto). **Ressalva do `financial-planner` preservada:** se demanda futura por projeção patrimonial condicional aparecer, ADR sucessora pode adicionar `expected_extinction_year` como campo ortogonal **opcional** sobre o enum estendido — sem recriar o enum nem reabrir esta decisão.

**(C) Não modelar; documentar mapeamento `uso_pessoal` + anotação em `<workspace>/notes/` ([[ADR-143]]).**
Rejeitada. Perde sinal estruturado para o parecer LLM ([[ADR-199]] lê schema, não notes free-text), impossível surfaçar em ratios e relatório, e o caso não é raro (5–15% ICP). Erosão semântica que vira dívida técnica em diagnóstico de liquidez e sucessão.

## Plano de implementação (PR de fechamento)

**Migration Alembic** (`adr235nupropriet1`):
- `up`: drop + recreate CHECK em `workspace_property_overrides.classification` (Postgres não permite editar CHECK in-place; `property_identity` não tem coluna `classification`, só a tabela de overrides). Sem backfill — rows existentes preservadas.
- `down`: pre-down guard valida que nenhuma row tem `nu_proprietario` (raise `RuntimeError` se houver, evita data loss silencioso); recriar CHECK sem o valor novo.

**Call-sites obrigatórios** (todos identificados; nenhum exhaustive switch, comportamento default = "não-investidor"):
- `backend/app/models/property_identity.py:31` — Enum/Literal.
- `pipeline/domain/services/patrimonio_imovel_classifier.py:19` — `CLASSIFICATION_NU_PROPRIETARIO`; **não** entra em `_CLASSIFICATIONS_GERADORAS`.
- `pipeline/domain/services/real_estate_metrics.py:18` — `INVESTMENT_CLASSIFICATIONS` permanece sem `nu_proprietario`.
- `backend/app/services/real_estate_adapter.py:131,156,169` — literais permanecem; nu-propriedade cai no else (`origin="none"`). Teste explícito.
- `frontend/src/lib/api/properties.ts:10` — union type estendida.
- `frontend/src/app/(app)/config/ResidenciaSection.tsx:18` — opção dropdown com label "Nu-propriedade (usufruto vitalício)" + tooltip explicando consolidação futura.

**ADRs atualizadas no mesmo PR** (extensão, não supersedure): [[ADR-215]] §1 inclui `nu_proprietario`; [[ADR-142]] declara invariante "nu_proprietario nunca em `investivel_efetivo`"; [[ADR-145]] documenta nu-propriedade em cat_2 não-gerador; [[ADR-216]] explicita exclusão do denominador de cap rate. [[ADR-199]] (parecer LLM): prompt atualizado. **Retratado em 2026-08-30:** golden e eval **não** foram — o PR de fechamento não toca nenhum arquivo com `golden` ou `eval` no path. Ver §Emenda de 2026-08-30, C6.

## Riscos

- **Schema evolution downstream** ([[ADR-188]]): readers exhaustive (TS `never`, Python `match`) falham hard com valor novo. Auditoria: backend usa whitelist literal `in (...)`, frontend não tem `switch` exhaustive sobre `Classification`. Risco baixo, mas adicionar CI gate `dev/check_classification_exhaustive.py` que falha se algum `switch (classification)` aparecer sem `default`.
- **Rollback inseguro.** Workspace que adotou `nu_proprietario` em produção bloqueia migration `down` (CHECK rejeita). Migration `down` valida pre-down (vide plano) — falha louder em vez de data loss silencioso.
- **LLM/E6 cego ao caso.** Prompt menciona classifications conhecidas; sem update + golden + eval, modelo trata como `desconhecido` e regride recomendações. Item obrigatório no critério de aceite.

## Critério de aceite (PR de Decidido)

1. Migration up/down aplica + reverte limpo em DB de teste; pre-down guard funcional.
2. `nu_proprietario` em `CLASSIFICATION_*` constants (backend + classifier), type TS, dropdown UI.
3. Testes de paridade com `uso_pessoal`: `tests/unit/pipeline/test_split_imoveis_with_overrides.py`, `tests/test_real_estate_metrics.py`, `tests/unit/pipeline/test_patrimonio_calculator.py` cobrem invariantes (fora de geradores, fora de `INVESTMENT_CLASSIFICATIONS`, fora de `investivel_efetivo`).
4. Teste E2E `@critical`: usuário muda classification de imóvel para `nu_proprietario` via UI → relatório reflete cat_2 não-gerador, fora de cap rate, fora de IF.
5. [[ADR-215]] / [[ADR-142]] / [[ADR-145]] / [[ADR-216]] atualizadas no mesmo PR (cross-doc invariants).
6. Prompt + golden + eval do parecer E6 ([[ADR-199]]) atualizados; cliente com nu-propriedade gera recomendação sem "venda este imóvel ocioso".
7. Snapshot OpenAPI regerado (`make update-openapi-snapshot`) — codegen propaga.
8. Entrada no [docs/CHANGELOG.md](../CHANGELOG.md) citando ADR-235.
9. CI gate `dev/check_classification_exhaustive.py` adicionado a [.pre-commit-config.yaml](../../.pre-commit-config.yaml).

## Não-objetivos (escopo explícito)

- `expected_extinction_year`, modelagem de cenário condicional pós-consolidação, alertas de extinção, tábua atuarial AT-2000 / IBGE, simulação de Monte Carlo.
- `valor_mercado_consolidado` separado de `valor_brl` IRPF (cabe em follow-up unificado com a [[ADR-227]], que **é** o FU-3 do Sprint A12 (a nota não tem uma §FU-3 — ponteiro corrigido em 2026-08-30) — mesma raiz: separar valor histórico/IRPF de valor de mercado livre).
- Sub-bucket "Patrimônio ilíquido condicional" como categoria nova em [[ADR-145]] — rejeitado neste escopo (cat_2 não-gerador absorve).

## Follow-ups (post-Decidido, fora deste PR)

- **FU-1 · `valor_mercado_consolidado` para nu-propriedade.** Estender `property_market_value` ([[ADR-227]]) para captura opcional do valor pleno futuro (user-declared, conservador). Sinaliza salto patrimonial esperado sem prometer precisão atuarial.
- **FU-2 · Aviso de seguro de vida no parecer E6.** Heurística: se workspace tem `classification = nu_proprietario` em ≥1 imóvel e `family_members` indica dependentes, parecer recomenda revisar cobertura para ITCMD da consolidação.
- **FU-3 · Eventual `expected_extinction_year` se demanda materializar.** Critério: ≥10 workspaces solicitando captura. Reabre via ADR sucessora — não esta.

## Emenda — o item 4 era cláusula não-financiada, e ganhou dono (2026-08-29)

**Medido no ataque ao `RR6-02`:** não existe, em lugar nenhum do repo, uma "concentração
imobiliária total" de denominador PL. Três fontes independentes: nenhum produtor no código ou
no schema; `ratios` publica **uma única** chave de concentração (mais a base dela); e o item 4
não é citado em nenhum outro doc da vault — só na linha que o enuncia aqui.

Pior: a métrica que shipou faz o **oposto** do item 4. `compute_concentracao_imobiliaria_pct`
([[ADR-340]]) soma cat_2 **completo** no numerador, e o rótulo que a acompanha em sete sítios é
"imóveis de **renda**". A nu-propriedade entrou exatamente onde esta ADR disse que ela não
entraria, e o KPI cruza o limiar por causa dela.

**Não houve colisão de decisões.** A base que a [[ADR-340]] shipou —
`investivel_financeiro + cat_2` — exclui residência e veículos (logo **não** é PL) e inclui
não-geradores (logo **não** é "de renda"): é uma **terceira** base, que não existia quando esta
nota foi escrita, e sobre a qual o item 4 é **silente**. O que fez parecer colisão foi a frase
falsa da [[ADR-340]] ("cat_2 = imóveis de renda"), retratada na emenda datada dela.

**A disposição.** A [[ADR-420]] (`Proposto`) **financia** as duas metades do item 4: publica
`ratios.imobilizacao_patrimonial_pct` sobre `patrimonio_liquido` (a primeira) e tira
`nu_proprietario` do numerador da concentração (a segunda). O nome recusa "concentração
total" de propósito — dois `concentracao_*` com bases distintas recriariam o defeito que a
[[A40.l80]] gastou 11 PRs matando. **A intenção do item 4 é honrada; o rótulo dele, não.**

**Achado de forma sobre esta própria nota, registrado para não se repetir.** O §Decisão afirma
que os sinais a surfaçar foram *"resgatados da análise do `financial-planner` e **movidos para
critério de aceite**"* — e os itens **1** ("bucket Ilíquido condicional") e **4** não foram: os
nove critérios de aceite não os mencionam, e nenhum gate podia detectar a ausência. Cláusula de
§Decisão sem correspondente no §Critério de aceite é **declaração não-financiada** — nunca teve
produtor nem detector, e a ausência dela é indetectável por construção. O item 1 **segue sem
dono**: não há bucket "Ilíquido condicional" no breakdown de liquidez.

## Emenda — disposição cláusula a cláusula (2026-08-30)

Auditoria de 17 cláusulas (5 sinais + 9 critérios + 3 follow-ups) contra o código, com
cético adversarial sobre cada ausência. **A decisão central está entregue**: o enum existe,
o CHECK existe, e os três invariantes (fora de geradores, fora de `INVESTMENT_CLASSIFICATIONS`,
fora de `investivel_efetivo`) são protegidos por testes que **discriminam** — a mutação que
promove `nu_proprietario` a gerador mata cinco testes.

**`Decidido` não é sinônimo de entregue quando nenhum gate podia detectar a diferença.**

| # | Cláusula | Veredito | Disposição |
|---|---|---|---|
| **Sinal 1** | bucket "Ilíquido condicional" no breakdown de liquidez | **não-financiada** | **Deferida com dono** — ver §Deferimento abaixo |
| **Sinal 2** | aviso sucessório de ITCMD no parecer | **não-financiada** | **Deferida com dono** — bloqueada por hold normativo |
| **Sinal 3** | valor IRPF ≠ valor pleno, na UI e no relatório | ausente | **IMPLEMENTADA** nesta rodada, nos dois sítios |
| **Sinal 4** | concentração total, não "de renda" | não-financiada | **ROTEADA** → [[ADR-420]] §D3 |
| **Sinal 5** | prompt instrui a não recomendar venda | parcial | **implementar** — o hint existe e é lido, mas `real_estate` não é projetado no manifest, então a regra fala de variável que o modelo não vê |
| **Critério 1** | migration + pre-down guard | **parcial** | o guard funciona; o `upgrade` **perdeu 2 índices** → [[ADR-423]] / [[A40.l97]] |
| **Critério 2** | constants, type TS, dropdown | entregue | — (o re-export do `patrimonio_calculator` esquecia `NU_PROPRIETARIO`; corrigido) |
| **Critério 3** | testes de paridade | entregue, e discriminam | — |
| **Critério 4** | E2E `@critical` UI→relatório | **ausente** | **implementar** — o item foi deixado `- [ ]` **desmarcado no corpo do próprio PR** de fechamento, que não toca nenhum arquivo sob `frontend/tests/` |
| **Critério 5** | ADR-215/142/145/216 atualizadas | entregue | — |
| **Critério 6** | prompt + golden + eval | **parcial** | **implementar depois do Sinal 5** — a ordem inversa fabrica verde |
| **Critério 7** | snapshot OpenAPI regerado | vacuamente satisfeito | **superseder o critério** — `classification: str` no DTO significa que o enum **nunca** esteve no contrato HTTP; não há nada a sincronizar, e trocar por `Literal[...]` mudaria contrato público para nenhum ganho de invariante |
| **Critério 8** | entrada em `docs/CHANGELOG.md` | satisfeito no endereço sucessor | **superseder o texto** — o path morreu com [[ADR-182]] F5 treze dias **antes** deste PR, e o shim proíbe escrita |
| **Critério 9** | gate `check_classification_exhaustive` | entregue, não-inerte | — |
| **§Plano** | "teste explícito" do `real_estate_adapter` | **ausente** | **IMPLEMENTADO** nesta rodada |
| **FU-1** | `valor_mercado_consolidado` | ausente | **Deferido com dono** — ver §Deferimento |
| **FU-2** | heurística ITCMD + dependentes | ausente | segue com o Sinal 2 |
| **FU-3** | `expected_extinction_year` | ausente | **manter deferido** — a ausência é o estado pretendido; registra-se apenas que o gatilho (">=10 workspaces solicitando") **não é instrumentado** |

**Achado de forma sobre esta própria nota, e é o segundo do mesmo tipo.** O §Decisão afirma
que os sinais foram *"resgatados da análise do `financial-planner` e **movidos para critério
de aceite**"*. Os itens **1**, **2** e **4** não foram — os nove critérios não os mencionam,
e nenhum gate podia detectar a ausência. A emenda de 2026-08-29 nomeou 1 e 4; o 2 também é.

## Deferimento datado (2026-08-30)

**Sinal 1 — bucket "Ilíquido condicional".** Dono: `financial-planner`. **Condição de
retomada: existir no produto um breakdown de liquidez por horizonte.** Hoje não existe: a
única decomposição de liquidez é o numerador da reserva de emergência, cujo universo é
investimentos + caixa e que nem lê `bens['imoveis']`. Não há "< 30 dias" nem "< 12 meses" no
código. **Não cite a metade negativa da cláusula como conformidade:** *"não soma em <30d nem
em <12m"* é verdade hoje porque os dois agregados **não existem** e porque cat_2 inteiro está
fora de `investivel_financeiro` — exclusão de classe, não sinal próprio. Há tensão interna a
resolver antes: o §Não-objetivos desta nota rejeita o nome no eixo de **composição
patrimonial** ([[ADR-145]]), enquanto o §Decisão 1 o pede no eixo de **liquidez**. São eixos
separáveis, mas quem financiar precisa dizer isso por escrito.

**Sinal 2 / FU-2 — aviso sucessório de ITCMD.** Dono: `financial-planner` + dono do produto.
**Condição de retomada: hold normativo da [[ADR-387]] levantado E escritor de `itcmd_uf` em
produção.** O hold diz que patrimônio bruto familiar × alíquota de uma UF não pode ser
publicado como imposto devido; recomendar capital de seguro **dimensionado** por um ITCMD
que o produto se recusa a publicar contraria o hold. E `gross_estate_brl_cents`, `itcmd_uf`
e `itcmd_aliquota_pct_por_uf` não têm escritor de produção — os construtores reais deixam os
três `None`. Não é código ausente: é input que só o dono cadastra.

**FU-1 — `valor_mercado_consolidado`.** Dono: `financial-planner` + `data-engineer`.
⚠️ **Agravante que muda o desenho e precisa estar aqui, senão o próximo agente "fecha" o
FU-1 corrompendo o patrimônio:** `resolve_valor_efetivo` é **agnóstico a `classification`* —
qualquer `property_market_value` declarado substitui o valor IRPF no patrimônio. Declarar o
valor pleno futuro pela porta existente injetaria o valor **pós-extinção do usufruto** no
patrimônio de **hoje**, que é exatamente o erro que o Sinal 3 existe para evitar. FU-1
precisa de discriminador "pleno vs onerado", não só de coluna.
