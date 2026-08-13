---
id: A40.l43
type: lane
title: "Card A Família: a coluna direita repetia o hero, e o validador exigia que ela existisse"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1386
ship_date: "2026-08-12"
priority: P1
branch_slug: a40-l43-perfil-familia-prosa
adrs:
  - "[[ADR-356]]"
  - "[[ADR-168]]"
  - "[[ADR-319]]"
  - "[[ADR-306]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/frontend
---

# A40.l43 — `perfil-familia-prosa-sobre-pessoas`

> **Aberta em 2026-08-11**, de um achado do parecer de design (workspace de
> dogfood). Co-design com `prompt-engineer` + `financial-planner` +
> `product-designer`; os três convergiram no diagnóstico e **divergiram no
> destino**, e o `senior-cto` fechou sob §Anti-loop do CLAUDE.md.

## Problema

O card "A Família" renderiza `narrativas.perfil_familia` em duas colunas. A
esquerda apresenta as pessoas. A **direita** tinha 3 parágrafos inteiramente
numéricos: meta de IF + TRS + investível + % da meta + aporte + retorno real +
prazo; patrimônio bruto + `n_imoveis` + carteiras nominais + endividamento;
diversificação + score + taxa de poupança + cobertura em meses.

O `HeroKpiGrid` entrega os mesmos 6 KPIs três blocos acima, com hierarquia forte
(2 deles `hero` + `accent` + progress bar). O card promete "quem é a família" no
título e gastava metade da área dizendo "quanto" — em prosa cinza `text-sm`,
que é o pior portador possível dos mesmos fatos.

**Não era 50% de duplicação; auditado fato a fato, era ~95%.** O único fato órfão
era a carteira nominal por titular — que é tabular, não narrativo, e cuja leitura
sucessória exigiria regime de bens, que o produto não modela ([[ADR-246]] usa
comunhão só para dedup de imóvel cross-IRPF).

### A causa raiz era o validador

`validate_narrativas` **exigia** `perfil_familia.right` não-vazio. Uma regra que
proíbe silêncio — e a saída de menor esforço sob ela é afirmar sem condição. Daí
as três frases:

- `"Endividamento de {x}% — saudável"`, incondicional. Com
  `taxa_endividamento_pct` acima de `thresholds_alertas.endividamento_maximo_pct`
  (20, `config/scoring.json`), o **mesmo PDF** dizia "saudável" no topo e emitia
  ponto urgente prioridade **Alta** ("Reduzir endividamento") na S10
  (`scripts/analyze_finances.py`). Contradição reproduzível.
- `"base sólida para o plano IF"` — veredito composto de 3 métricas sem limiar.
- `"Carteira diversificada entre 1 categoria de ativos"` com n=1.

Enquanto a regra vivesse, ela reproduziria o defeito na próxima mão. Por isso a
lane remove a exigência, não o conteúdo que a satisfazia.

### Por que a paridade com o mockup não era restaurável

O achado original pedia restaurar a paridade com
`docs/plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html`, onde a coluna direita abre
com **plano de vida**. Esse parágrafo é literalmente o Modo USA (visto F1/F2,
Green Card EB2-NIW, NCLEX, custo da fase), removido como dead data em A8.4 e
limpo do narrador no cleanup da [[ADR-168]] (A10.1) — o próprio código
documenta. **A duplicação é a cicatriz dessa remoção:** com o parágrafo de plano
de vida fora, o de IF subiu ao slot 1 e nada prospectivo entrou no lugar. O
mockup é anterior ao cleanup e ficou fóssil.

E não havia substrato para repor: `FamilyMember` tem nome, nascimento, papel,
CPF cifrado, `us_tax_status` e um JSON livre (profissão, formação, regime,
cidadania); `Goal` é numérico; `Decision` ([[ADR-136]]) é plano de ação
financeiro. **Nenhum campo de projeto de vida.** Narrar prospecção sem dado
seria fabricar.

## Escopo

1. `perfil_familia.right` **removida** do narrador. Os 3 adjetivos morrem por
   construção, não por edição de string.
2. `validate_narrativas` deixa de exigir `right`; segue aplicando limite de tag e
   de 300 chars **quando presente** (janela de leitura de artefato antigo).
3. Salário-base do cônjuge sai do `left`: é valor monetário (regra nova) e é PII
   de renda individual — mesma classe do endereço cortado na [[A40.l4]].
4. **Transferência bloqueante:** a declaração de ausência de prazo ([[A40.l26]])
   vai para `_s7_meta_e_prazo`, onde o prazo mora. Medição que a tornou
   bloqueante: `goals.prazo_anos_realista` e `goals.ano_if` são **`None`** no
   snapshot dogfood corrente — ramo vivo. A S7 imprimia `"prazo realista de N/D
   anos"` e `"em None"`.
5. `today` do perfil vem de `data_analise` do E5, não de `date.today()`.
6. Card React lê só `left`, em uma coluna; `right` sai da interface TS (guarda em
   ramo morto é a classe que [[ADR-356]] §D4 já julgou).
7. Emenda datada na [[ADR-356]] com a **regra**: o narrador de `perfil_familia`
   não publica valor monetário nem juízo qualitativo.

## Critério de aceite

- `perfil_familia` não tem chave `right`; `left` não contém `R$`, `US$` nem `%`,
  e nenhum dos 3 adjetivos. **Gate de classe** — e um gate **estrutural** extra:
  o módulo do narrador não importa `fmt_currency`/`fmt_usd`/`fmt_percent`/
  `fmt_num` (`fmt_num` formata sem símbolo, logo passaria pelo teste de string).
- **Prova por mutação:** reintroduzir `right` ou `— saudável` deixa vermelho.
- `today` — o narrador honra o kwarg (dois `today` produzem `left` diferente) **e**
  o call site do stage o injeta (gate separado: honrar não prova que alguém
  injeta).
- S7 com prazo ausente declara a premissa que falta, sem `N/D` nem `None`;
  contraprova com prazo presente.
- Fixture `tests/fixtures/narrativas/e5n_delivery.json` regravada **pelo
  produtor**; o par TS (`sectionSummaryDelivery.test.tsx`) verde no mesmo PR.
- Os 4 testes de gramática de imóveis **deletados**, não adaptados
  ([[ADR-210]] §pós-cutover órfão).
- `docs/adr/356` com `amended_at` + blockquote de sinal; rastro escrito nas
  lanes tocadas ([[A40.l6]], [[A40.l15]], [[A40.l29]]).

## Fora de escopo

- ~~Layout multi-coluna~~ — **entrou nesta lane** depois que o #1382 corrigiu a
  fixture `medium.json` e tornou o delta verificável. Ver §Colisão. As outras
  **5** fixtures seguem emitindo `perfil_familia` como *string*, então a seção
  ainda não aparece nelas: quem for tocar degradação/print do bloco de identidade
  corrige as 5 e ganha a primeira baseline **olhada** dos estados vazios.
- **Repor as premissas de IF** (TRS, retorno real, meta em R$, aporte-meta) — sem
  superfície no relatório hoje; destino é a [[A40.l29]] §Escopo 2. Ownership de
  superfície, não escolha de conteúdo.
- **Política de diversificação/concentração** — segue da [[A40.l15]]. Aqui a
  frase morre por consequência, sem afirmação substituta.
- **Contagem de imóveis** — [[A40.l6]], cujo item deste lado fica quitado por
  remoção.
- **Substrato declarado de plano de vida** — precisa de ADR `Proposto` própria, e
  o gatilho é PII (texto livre autorado caindo verbatim no PDF é nova superfície
  das classes que [[ADR-356]] §D9 removeu), não a forma do narrador. O
  `financial-planner` especificou o conjunto mínimo anti-campo-lixo: todo campo
  declarado tem de **mudar um número que já existe**, vocabulário fechado + ano +
  valor (nunca texto livre), máx. 5 campos, e horizonte **não** se coleta
  (`goal.if.horizonte_anos` já existe).
- **`fmt_currency` contra COPY_GUIDELINES §4** (`R$ 45k` em vez de `mil`, sinal
  entre símbolo e número) — cross-cutting, toca toda string narrativa.
- **Heading order** h1 → h3 → h2 e Sumário Executivo sem heading (só
  `aria-label`) — `ReportCard` emite `<h3>` fixo; `axe` classifica
  `heading-order` como `moderate` e o gate é `critical+serious`, então não pega.
  Lane própria.

## Colisão com o PR #1382 — RESOLVIDA (ele mergeou primeiro, 2026-08-12)

O **#1382** fundiu "A Família" + `TitularesCard` numa seção de identidade
(`PerfilFamiliaSection.tsx`, card deletado) — exatamente o follow-up que o
`product-designer` levantou no co-design **desta** lane. Ele mergeou em
`ad33d456` **antes** desta lane, e a seção nova **ainda consumia `right`**
(`parseParagraphs(perfil?.right)`), o que teria produzido uma coluna vazia num
`grid sm:grid-cols-2`.

Resolvido no rebase, no cenário "#1382 primeiro" que esta seção já previa: o lado
de pipeline é disjunto e não mudou; o edit de frontend migrou do card deletado
para a seção nova.

**Duas coisas que o merge do #1382 mudou nesta lane:**

1. **O deferimento do layout caiu.** O `md:columns-2` estava fora de escopo porque
   as 6/6 fixtures E2E emitiam `perfil_familia` como *string* e o delta visual
   seria zero por construção. O #1382 **corrigiu `medium.json`** para
   `{left,right}` — a seção passou a aparecer no e2e, logo remover `right`
   deixaria coluna vazia **visível e verificável**. O motivo do deferimento morreu,
   então o fluxo multi-coluna entrou aqui, com as 3 travas do `product-designer`:
   margem no `<p>` (CSS columns não honra `gap` de flex), `columns: 1` no print
   (fragmentar multi-coluna em quebra de página é bug do Chromium, e o repo já tem
   cicatriz de PDF truncado), e ≤2 parágrafos em 1 coluna (workspace de 1 pessoa
   não deve ter parágrafo único partido ao meio).
2. **A fixture `medium.json` carregava afirmação fabricada.** O `right` que o
   #1382 escreveu à mão dizia *"Plano de vida centrado na consolidação
   patrimonial…"* — texto que o produtor **nunca** emitiu (o narrador emitia meta
   de IF, patrimônio bruto, score). Fixture escrita à mão descrevendo mundo que o
   produtor não produz é o anti-padrão que a [[A40.l3]] catalogou. Removida com a
   chave.

## Fechamento

**Entregue em `849e372b` (PR #1386, squash em `main` 2026-08-12), CI verde.**

- Medição bloqueante (§Escopo 4): `prazo_anos_realista: None` e `ano_if: None` em
  `backend/tests/snapshots/dogfood_view_model.json`. Re-medir com
  `rg -n '"prazo_anos_realista"|"ano_if"' backend/tests/snapshots/dogfood_view_model.json`.
- Call sites de `carteira_diversificacao_frase` **entregues** após esta lane:
  **zero** (`s3` desligado pela l15; `charts_narrator` inerte por deferimento
  [[ADR-356]] §D5, S1 usa `getConclusion` derivado; `perfil_familia.right`
  removido).
- Verificação adversarial em workflow **não completou** (limite de gasto); as 4
  lentes foram rodadas à mão e o que acharam está no PR: `.get("right")` morto em
  `test_e5n_no_dead_data`, razão de `trs_pct` apontando para superfície extinta em
  `test_e5n_param_classification`, e o buraco do `fmt_num` no gate de string —
  os três corrigidos.
