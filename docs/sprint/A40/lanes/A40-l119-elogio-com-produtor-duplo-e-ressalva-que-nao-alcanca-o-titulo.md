---
id: A40.l119
type: lane
title: "O elogio à reserva tem dois produtores e o guard alcança um; e a ressalva reescreve a descrição sem tocar o título que o leitor vê"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l119-elogio-com-produtor-duplo-e-ressalva-que-nao-alcanca-o-titulo
owner: prompt-engineer
depends_on: []
adrs: ["[[ADR-412]]"]
tags: [type/lane, sprint/a40, status/open, priority/p2, area/backend]
---

# A40.l119 — `elogio-com-produtor-duplo-e-ressalva-que-nao-alcanca-o-titulo`

> **Origem:** os três follow-ups que a [[A40.l116]] mediu e **não** fechou (#1969 ·
> `a5cb8b59`). Nenhum é achado novo de rodada: os três saíram da medição do conserto.

Os três compartilham o eixo da [[A40.l117]] — *o que o modelo escreve não é confrontado com
o que a máquina sabe* — mas **não** entraram nela porque o `#1966` estava em voo sobre o
arquivo dela quando esta lane foi aberta. ~~Se a l117 fechar antes desta ser pega, a fusão é
a decisão certa.~~

> **A condição se cumpriu e a fusão foi RECUSADA (2026-09-02, fecho da [[A40.l117]]).**
> Absorver três follow-ups não iniciados reabriria aquela lane por tempo indeterminado, e
> os três são self-contained — nasceram da medição do conserto da [[A40.l116]], não dela.
> Esta lane segue pegável sozinha.
>
> ⚠️ **O item 3 abaixo mudou por causa daquela entrega.** Depois da [[ADR-438]],
> `tema_canonico` nulo em `PontoForte` tem um **segundo** consumidor além do guard: o
> destino de leitura, que sem tema cai no ramo `sintese` (S10). O `0 em 64` segue válido;
> o que sobe é o custo de ele deixar de ser zero.

## 1. O elogio tem dois produtores, e o guard alcança um

`pipeline/domain/services/pontos_fortes_analyzer.py:186` emite
`titulo="Reserva de Emergência Robusta"` **deterministicamente** sob `avaliacao ==
"excessiva"`. Isso é **por desenho** e não é o defeito: a `descricao` que o acompanha
(`_descricao_reserva_robusta`) já carrega *"o excedente pode ser realocado para a classe mais
defasada"*. Ele renderiza em **S10** (`PontosFortesCard`), fora do alcance de qualquer regra
pós-LLM.

O defeito é o que acontece a jusante: `config/prompts/parecer_planejador.yaml:699` projeta
`$.pontos_fortes` **cru** no exec context, sob a label *"Pontos fortes determinísticos —
referência, não duplique"*. O título que a **U5** flagrou é **idêntico** ao determinístico —
o modelo **ecoa** o que o prompt lhe entregou, e descarta a ressalva da descrição.

Consequência com o guard já consertado: a página pode manter elogio (S10, determinístico) ×
alerta (parecer). **É o resíduo do mesmo sintoma do `RR9-09`**, um nível acima do que a
[[A40.l116]] alcançava.

Saídas possíveis (não decididas): não projetar `$.pontos_fortes` quando o próprio E5
contradiz o item · pendurar o veredito na label da `:699` · hint na `:719`.

⚠️ **Custo que manteve isto fora do #1969:** mexer no manifesto é bump
`manifest_version` + re-eval, e o golden mensal do parecer **não roda por default**
(`planner-golden-monthly.yml` skipa sem `ANTHROPIC_API_KEY`). Mudança de prompt embarcaria
**não medida**. Quem pegar isto precisa resolver a medição antes do bump.

## 2. A ressalva reescreve a descrição e não toca o título

`parecer_pos_llm_guardrails._com_ressalva` reescreve **só** `descricao`. No regime em que o
piso `PONTOS_FORTES_MIN = 3` amarra — medido, **1 dos 14 runs** — o guard não remove, só
ressalva, e o título *"…Robusta"* sobrevive ao lado do risco *"…Excessiva — Capital
Ocioso"*. O contraste que o leitor vê **persiste**, e o contador de telemetria diz a
verdade (`ressalvados: 1`), o que torna isto invisível a quem só lê o número.

## 3. `tema_canonico` é opcional em `PontoForte`, e é a única âncora que restou

Pós-[[A40.l116]] o guard casa por `tema_canonico`. O campo é **obrigatório** em `Risco` e
**opcional** em `PontoForte`
(`pipeline/llm/schemas/parecer_planejador.py:242`): um elogio à reserva com o campo nulo
escapa dos dois braços.

**Medido 0 em 64** pontos fortes de 14 runs — buraco de **contrato**, não observado. Por
isso ficou **contado** (`autocontradicao_tema_ausente`) em vez de virar regra: tornar o
campo obrigatório no schema empurra o output para reask, e esse custo já foi pago na
[[ADR-292]].

**Condição de retomada:** `autocontradicao_tema_ausente > 0` em qualquer run. Enquanto o
contador for zero, este item **não** é trabalho — é vigilância com gatilho mecânico.

## Critério de aceite

1. O item 1 fecha com medição do efeito na página, não só no artefato: com o E5 declarando
   a reserva excessiva, o relatório publicado não exibe título de elogio à reserva sem a
   ressalva junto — e o bump de `manifest_version` vem acompanhado de como o eval rodou.
2. O item 2 fecha quando a ressalva alcança o que o leitor lê, ou quando se decide (com
   razão escrita) que o título pode divergir da descrição ressalvada.
3. O item 3 **não** abre trabalho enquanto `autocontradicao_tema_ausente == 0`; se disparar,
   a decisão entre regra e obrigatoriedade de schema pesa o custo de reask da [[ADR-292]].
