---
id: A40.l103
type: lane
title: "O recorte da baseline da capa media a nav — e era o único gate sobre os números-manchete"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P2
branch_slug: a40-l103-clip-da-capa
owner: senior-cto
depends_on: []
tags: [type/lane, sprint/a40, status/in-progress, priority/p2, area/frontend, area/ci]
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
   **medida** (`maxDiffPixelRatio: 0.005`, piso de ruído observado 0px) — e
   explicitamente **não** herda o `0.025` do helper, que existe para canvas e o
   header não tem canvas. Remove a última tolerância absoluta do arquivo,
   terminando a migração que a [[A40.l53]] deixou pela metade em 26 de 28.
2. Baseline própria para `sumario-executivo`, repondo a cobertura acidental.
   Seletor próprio, **sem** `data-report-section`, de propósito: aquele atributo
   o faria entrar no inventário da [[ADR-370]], que roda em todo PR sem label —
   mudança de contrato que não pertence a um PR de recorte de teste.
3. Gaps declarados no spec, seguindo o padrão de `SECTIONS_NOT_IN_MEDIUM_FIXTURE`:
   `ReportTopNav` (baseline agora **fossilizaria** a truncagem que a lane
   `A40.l102` conserta — branch `agent/report-topnav-overflow/20260830-1830`,
   ainda não mergeada, por isso citada sem wikilink; vale mais depois daquele
   fix, e o gate daquela lane é de alcançabilidade, não de pixel), `ReportPremissasBlock` (`<details>`
   fechado: o recorte provava uma linha de `<summary>`) e `aside.sidebar-toc`
   (`no-print`, derivada de codegen).

## Fora de escopo — roteado, não perdido

| Achado | Encaminhamento |
| --- | --- |
| Gate visual obrigatório por paths-filter em vez de label. Custo medido: **zero** em wall-clock — PR de relatório já paga ~6 min de `Frontend checks` no mesmo filtro, e o visual (1m31s–2m23s) roda em paralelo e termina antes | Item novo em `TRACK-ci-trust-onda1-workflows`; muda o veredito do `all-green`, logo **viaja sozinho**. Exige **emenda datada à [[ADR-210]] §Camada 1**, cuja premissa de custo (~$4/mês no overage) caiu com o repo público |
| Varredura periódica em `main` | **Não construir.** Já existe: `frontend-visual-full` em `nightly.yml`. Está morta porque o `Nightly` é `disabled_manually`, com waiver datado do dono em `.github/scheduled-workflows.yml`. É o **item 1.4** do [[PLAN-ci-trust]]; a razão de FinOps do waiver caducou com o repo público |
| Sumário executivo ausente do inventário da [[ADR-370]] | Lane própria. Os números-manchete não têm gate estrutural; esta lane só repôs o gate **de pixel** |
| Reflow de 1px marca 9,58% em imagem curta — a métrica de razão é inadequada para baseline baixa e densa em texto | Lane própria. Candidato: comparar com realinhamento `dy∈{±1,±2}` antes de reprovar |
| Ledger de proveniência por baseline (`px_sha256`, `dims`, `transition` computados; `attributed_to`, `inspected_by` humanos) | Lane própria. **Não** copiar `dev/golden_diff.py` inteiro: o pilar do commit isolado **inverte** em binário — para PNG o diff é ilegível, então o diff de código irmão no mesmo commit é o único sinal de atribuição, e isolar o destruiria |
| Encolher o ativo (29 PNGs / 3,2 MB working set) e revisar variantes `dark` | Lane própria, **depois** do ledger — que fecha de graça o buraco de baseline órfã |
| Baseline de print é golden sobre o rasterizador, e o caminho de update grava e retorna verde sem comparar | Lane própria |

## Critério de aceite

- [ ] `cover` recorta no locator; nenhuma baseline visual depende mais da nav.
- [ ] `sumario-executivo` tem baseline nos dois temas, com controle positivo de
      card montado.
- [ ] **Contraprova de atribuição nos dois sentidos** — mutação sintética na nav
      **não** reprova `cover`; mutação no header **reprova**. Sem os dois
      sentidos, a lane provou que recortou, não que desacoplou.
- [ ] Gaps de cobertura declarados no spec, com dono ou lane de destino.
- [ ] Job `frontend-visual` verde no PR com a label `visual`.
