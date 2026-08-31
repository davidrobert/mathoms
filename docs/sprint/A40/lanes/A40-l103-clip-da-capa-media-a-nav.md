---
id: A40.l103
type: lane
title: "O recorte da baseline da capa media a nav — e era o único gate sobre os números-manchete"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1859
ship_date: "2026-08-30"
priority: P2
branch_slug: a40-l103-clip-da-capa
owner: senior-cto
depends_on: []
tags: [type/lane, sprint/a40, status/shipped, priority/p2, area/frontend, area/ci]
---

# A40.l103 — `clip-da-capa-media-a-nav`

> **Origem:** investigação da drift das baselines `cover-{light,dark}` em `main`
> (fechada por [[A40.l100]] · PR #1850). O rebaseline curou o sintoma; esta lane
> ataca o mecanismo.

## O defeito

O teste `Snapshots — cover (hero)` capturava com recorte **page-level**:

```ts
clip: { x: 0, y: 0, width: VIEWPORT.width, height: 720 }
```

A nav é `position: sticky; top: 0`, então os ~52px de cima da "baseline da capa"
eram **nav**; mais abaixo entravam o `aside.sidebar-toc` (240px) e o conteúdo
pós-header. O `<header data-report-cover>` era ~⅓ da própria imagem.

O acoplamento cobrou em 2026-08-27: a [[A40.l88]] (PR #1755) inseriu o chip
`2.5` na nav e a baseline reprovou com bbox `(715,16,1071,36)` — inteiramente
dentro da nav, sem tocar o header. Atribuição falsa: quem viu `cover` vermelho
procurou a causa no `ReportCover` e não achou nada.

## A medição que ninguém tinha

**O bloco de números-manchete não tem gate nenhum.** O
`<section id="sumario-executivo">` (Patrimônio Líquido, Patrimônio Investível,
Reserva de Emergência, Taxa de Poupança, IF, Score) **não** está em
`STRATEGIC_SECTIONS`, **não** tem `data-report-section` e **não** aparece em
`report-inventory.expected.json` (17 seções; nenhuma é o sumário). Ele era
coberto **só** pelo acidente do recorte de 720px — ou seja, o recorte largo
demais era, por acaso, o único gate sobre os números que o relatório mais
destaca. Estreitar sem repor derrubaria essa cobertura em silêncio.

**O render é determinístico.** Dois `workflow_dispatch` do **mesmo SHA**
(`ec50cbd7`; runs `33323919131` e `33323920209`) devolveram as **28 baselines
byte-idênticas** — zero `DIM`, zero `SHIFT`, zero diferença real. Isso refuta a
hipótese de instrumento bi-estável e, junto, o comentário do helper de seção que
afirma *"chart.js canvas tem não-determinismo inerente entre runs (~1-2% da
imagem)"*: essa afirmação descreve o mundo anterior à [[A40.l53]] e hoje não se
reproduz. É o que autoriza tolerância medida em vez de herdada.

**Mas o gate grita por mudança de zero informação.** Reproduzido à mão em
`S-parecer-retido-dark`: 5 versões commitadas, **2 hashes de pixel** distintos
(`91233c2be470` ×3, `da005a90e58e` ×2), alternando perfeitamente entre quatro
lanes sem relação. Cada transição acusa **21.128 px (9,58%)** — quase 4× a
tolerância de 2,5% — e o realinhamento `dy=±1` leva a **0 px**. Conteúdo
idêntico, deslocado um pixel. Como o render é determinístico, o deslocamento é
dirigido por commit, não por flake: o problema não é o instrumento oscilar, é a
métrica de razão amplificar reflow de 1px em imagem curta.

## O que esta lane entrega

1. `cover` passa a recortar no locator `[data-report-cover]`, com tolerância
   **medida** (`maxDiffPixelRatio: 0.0003`, entre o piso de ruído de 0px e a
   menor mudança que precisa reprovar, 304px — ver §"O primeiro valor de
   tolerância reprovou a própria contraprova", que registra por que o `0.005`
   tentado primeiro **não** serve) — e explicitamente **não** herda o `0.025`
   do helper, que existe para canvas e o header não tem canvas. Remove a última
   tolerância absoluta do arquivo, terminando a migração que a [[A40.l53]]
   deixou pela metade em 26 de 28.
2. Baseline própria para `sumario-executivo`, repondo a cobertura acidental.
   Seletor próprio, **sem** `data-report-section`, de propósito: aquele atributo
   o faria entrar no inventário da [[ADR-370]], que roda em todo PR sem label —
   mudança de contrato que não pertence a um PR de recorte de teste.
3. Gaps declarados no spec, seguindo o padrão de `SECTIONS_NOT_IN_MEDIUM_FIXTURE`:
   `ReportTopNav` (baseline agora **fossilizaria** a truncagem que a lane
   [[A40.l104]] conserta — branch `report-topnav-overflow`; vale mais depois
   daquele fix), `ReportPremissasBlock` (`<details>` fechado: o recorte provava
   uma linha de `<summary>`) e `aside.sidebar-toc` (`no-print`, derivada de
   codegen).

   > **Correção de atribuição — 2026-08-30 (closeout, 2ª passada).** Este item
   > dizia `A40.l102` e caracterizava o gate daquela lane como "de
   > alcançabilidade, não de pixel". **Ambas as afirmações eram falsas.** A lane
   > da trilha é a [[A40.l104]] (`branch_slug: report-topnav-overflow`, o mesmo
   > branch que este item citava; `ship_pr` **#1860**); a [[A40.l102]] é
   > "Superfície do gasto pontual: dedup do par publicado" (**#1864**), sem
   > relação com a nav. E a própria [[A40.l104]] §"Quem alcança o que está fora"
   > **refuta** o enquadramento: *"Cai a palavra 'inalcançabilidade': há rota. O
   > defeito é de **descoberta e de ponteiro** no desktop"*. A citação foi escrita sem wikilink de propósito
   > (a lane ainda não existia com esse número), o que a tornou **invisível ao
   > `check_doc_links`** — nenhum gate podia pegá-la.
   >
   > **Condição de retomada satisfeita:** o fix da trilha mergeou em #1860
   > (2026-08-30 18:18Z). A baseline de `ReportTopNav` deixou de ser prematura;
   > hospedada em [[PLAN-report-trust]] §"Deferimentos do closeout da
   > [[A40.l103]]".

## Fora de escopo — roteado, não perdido

| Achado | Encaminhamento |
| --- | --- |
| Gate visual obrigatório por paths-filter em vez de label. Custo medido: **zero** em wall-clock — PR de relatório já paga ~6 min de `Frontend checks` no mesmo filtro, e o visual (1m31s–2m23s) roda em paralelo e termina antes | **Registrado** como `PR 5` do [[TRACK-ci-trust-onda1-workflows]] no closeout desta lane; muda o veredito do `all-green`, logo **viaja sozinho**. Exige **emenda datada à [[ADR-210]] §Camada 1**, cuja premissa de custo (~$4/mês no overage) caiu com o repo público |
| Varredura periódica em `main` | **Não construir.** Já existe: `frontend-visual-full` em `nightly.yml`. Está morta porque o `Nightly` é `disabled_manually`, com waiver datado do dono em `.github/scheduled-workflows.yml`. É o **item 1.4** do [[PLAN-ci-trust]]; a razão de FinOps do waiver caducou com o repo público |
| Sumário executivo ausente do inventário da [[ADR-370]] | Lane própria. Os números-manchete não têm gate estrutural; esta lane só repôs o gate **de pixel** |
| Reflow de 1px marca 9,58% em imagem curta — a métrica de razão é inadequada para baseline baixa e densa em texto | Lane própria. Candidato: comparar com realinhamento `dy∈{±1,±2}` antes de reprovar |
| Ledger de proveniência por baseline (`px_sha256`, `dims`, `transition` computados; `attributed_to`, `inspected_by` humanos) | Lane própria. **Não** copiar `dev/golden_diff.py` inteiro: o pilar do commit isolado **inverte** em binário — para PNG o diff é ilegível, então o diff de código irmão no mesmo commit é o único sinal de atribuição, e isolar o destruiria |
| Encolher o ativo (**30** PNGs / **3,1 MB** working set — re-medido no closeout; o `29 / 3,2 MB` escrito na abertura já não valia depois das 2 baselines que esta lane somou) e revisar variantes `dark` | Lane própria, **depois** do ledger — que fecha de graça o buraco de baseline órfã |
| Baseline de print é golden sobre o rasterizador, e o caminho de update grava e retorna verde sem comparar | Lane própria |

### Re-verificação dos deferimentos — closeout 2026-08-30

Regra do repo: enunciado de follow-up se **re-mede antes de registrar**, senão
o registro induz regressão. As 5 linhas "Lane própria" acima foram conferidas
contra `main` neste closeout:

| Deferimento | Veredito |
| --- | --- |
| Sumário fora do inventário da [[ADR-370]] | **Confirmado** — `report-inventory.expected.json` tem 17 seções e nenhuma é `sumario-executivo` |
| Métrica de razão amplifica reflow de 1px | **Confirmado** pela medição da própria lane (9,58%, `dy=±1` → 0px) |
| Ledger de proveniência | Proposta de desenho, sem enunciado factual a medir |
| Encolher o ativo | **Número corrigido** — eram 30 PNGs / 3,1 MB, não 29 / 3,2 MB |
| Update de baseline de print grava e retorna verde | **Confirmado** — `print.@critical.spec.ts:154` faz `writeFileSync` + `return` antes de qualquer `comparePngs`; e o mesmo ramo cobre `!existsSync(BASELINE_PATH)`, então **baseline ausente também passa** |

**Nenhum dos 5 tem dono nomeado**, e por isso não ficam só aqui: foram
hospedados em [[PLAN-report-trust]] §"Deferimentos do closeout da [[A40.l103]] —
2026-08-30", que está `in_progress` e é a superfície viva da classe. Lane `open`
sem agente seria pior — mente para quem lê `status` como "pegável agora" — e a
[[ADR-370]] não serve de hospedeira por estar `Decidido`. Pegá-los continua
sendo decisão do dono; o §Gatilho de descorte lá diz o que os promove.

## Critério de aceite

- [x] `cover` recorta no locator; nenhuma baseline visual depende mais da nav.
- [x] `sumario-executivo` tem baseline nos dois temas, com controle positivo de
      card montado.
- [x] **Contraprova de atribuição nos dois sentidos**, medida sobre o MESMO
      commit: mutação no rótulo da nav (`fontSize` 9→13, run `33326058949`) →
      **`success`**, nada reprova; mutação no `subtitle` do header (run
      `33326004042`) → **`failure` com 2 failed / 38 passed**, e os 2 são
      exatamente `cover — light` e `cover — dark`. Reprova o certo e só o certo.
- [x] Gaps de cobertura declarados no spec, com dono ou lane de destino.
- [x] Job `frontend-visual` verde no PR com a label `visual` — run
      `33326297663`, `event: pull_request` sobre o **head final** do PR
      (`ecf28a05`), `conclusion: success`: **40 passed / 4 skipped** em 1m57s.
      Os 4 skips são os gaps pré-existentes de `SECTIONS_NOT_IN_MEDIUM_FIXTURE`
      (`S4`, `APP_C` × 2 temas) — nenhum é baseline desta lane. A aritmética
      fecha com a contraprova: 2 failed + 38 passed + 4 skipped = 44 coletados.

### O primeiro valor de tolerância reprovou a própria contraprova

`0.005` deixava passar a mutação de texto: acrescentar `"XX"` ao `subtitle` move
**304px** (light) / **310px** (dark), ~0,076%, contra um limiar de 2.006px —
folga de 6,6×. É a classe conhecida em que o `<h2>` da S9 mudou e o gate ficou
verde. Corrigido para `0.0003` (~120px), que fica **acima** do piso de ruído
medido (0px) e **abaixo** da menor mudança que precisa reprovar.

**Armadilha de método registrada** (produziu uma medição falsa antes desta):
`--update-snapshots` só reescreve a baseline quando a comparação **falha**.
Mutação sob a tolerância devolve o arquivo antigo intacto e a comparação acusa
`0px` — que é o arquivo comparado consigo mesmo, não medição. A medição válida
exige apagar a baseline na branch de sonda (run `33325757975`).
