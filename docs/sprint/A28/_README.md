---
id: MOC-sprint-a28
type: moc
title: "Sprint A28 — Report Trust: o relatório para de afirmar precisão que os dados não sustentam"
aliases: ["A28", "Sprint A28"]
sprint_status: current
date: "2026-07-03"
theme: "report-trust"
---

# Sprint A28 — Report Trust: o relatório para de afirmar precisão que os dados não sustentam

> **Status:** `current` (promovida 2026-07-03) — sucede [[MOC-sprint-a26]]
> (`current → paused`, re-priorização do owner, [[ADR-234]]). 1ª janela do plano
> [[PLAN-report-trust]], nascida da revisão completa do relatório dogfood
> `72883bde` (2026-07-03). Co-design 2026-07-03: `product-manager`
> (corte/ondas/KR/gates de owner) + `information-architect` (plano/forma/
> transição de estado) + `data-engineer` (l6/l7/l8 — contratos e raízes) +
> `prompt-engineer` (l11 — guardrails pós-LLM) + `financial-planner` e
> `product-designer` (parecer de origem). Prompt de orquestração:
> [agent_prompts/orchestrator_a28_report_trust.md](../../agent_prompts/orchestrator_a28_report_trust.md).
>
> **Por que fura a fila da A27:** a A26 está `blocked` por gates de **tráfego
> que só o dogfood do owner gera** (≥20 gerações de parecer) e a A27 tem o Must
> já entregue antecipadamente — não há trabalho de código A26/A27 que a A28
> impeça. A A28 corrige os *inputs* do parecer (TRS, reserva, mensalização) e
> **é a máquina que produz o tráfego** que destrava [[A26.l2]]/[[A26.l4]].
> Sequência: corrigir dados (A28) → gerar tráfego limpo → fechar gates A26.

## Tese

O relatório dogfood contém **três recomendações que, se seguidas, pioram a
situação do cliente**: desacelerar aporte (TRS fictícia de 22,63% a.a. —
dividendos da própria PJ no numerador, só imóveis geradores no denominador);
desmobilizar carteira produtiva (reserva "Excessiva" de 31,6 meses — numerador
= todo o investível, denominador = despesa total em vez de custo essencial);
cortar gasto errado (rótulo Cerbasi "Gastador" com 97,5% presente sobre R$ 401k
de despesa não-identificada, no mesmo relatório que celebra 28% de poupança).
Duas dessas são **violação de contrato já escrito**
([FORMULAS.md](../../reference/FORMULAS.md) §Reserva · [[ADR-191]]), não decisão
em aberto. Em produto fiduciário com critério "refinar até perfeito antes de
abrir", a sprint fecha o gap entre o que o relatório *afirma* e o que os dados
*sustentam* — corrigindo fórmulas, fechando o loop de dados e tornando a
apresentação honesta sobre qualidade/completude.

## Ondas e lanes (co-design 2026-07-03)

| Lane | Slug | Onda | Corte | Status | Dep / Gate |
|---|---|---|---|---|---|
| [[A28.l4]] | `mensalizacao-base-unica` | 0 | **Must** | planned | ADR `Proposto` é T0 · **upstream de l1** (base do denominador da reserva) |
| [[A28.l1]] | `reserva-formula-canonica` | 0 | **Must** | planned | [[A28.l4]] (base mensal decidida antes do re-snapshot) |
| [[A28.l2]] | `trs-universo-consistente` | 0 | **Must** | planned | — · ∥ com l4→l1 e l3 |
| [[A28.l3]] | `pgbl-ano-base-unico` | 0 | **Must** | planned | ADR `Proposto` é T0 · ∥ |
| [[A28.l5]] | `nao-identificado-learning-loop` | 1 | Should | planned | código fecha sozinho · KR2 avaliado pós-gate `G-owner-reclassify` |
| [[A28.l6]] | `protecao-apolices-flow` | 1 | Should | planned | — · reescopo data-engineer: alvo é `compute_protecao` ([[ADR-240]]), não só o balde E4 |
| [[A28.l7]] | `imoveis-excluidos-dedup` | 1 | Should (tático) | planned | dedup na projeção · re-medição pós-gate `G-owner-label` · poda estrutural = débito A29+ |
| [[A28.l8]] | `higiene-ingestao-periodos` | 1 | Should | planned | — · períodos 1899/2100 não são sentinel oficial (`999999`) — risco de ano-base fantasma |
| [[A28.l10]] | `ancoras-formatter-curadoria` | 2 | Should | planned | — · **∥ desde o dia 1** (independe dos valores da Onda 0) |
| [[A28.l9]] | `report-data-quality-banner` | 2 | Should | planned | skeleton ∥ · **merge após Onda 0** (consome números que a Onda 0 corrige) |
| [[A28.l11]] | `parecer-guardrails-pos-llm` | 2 | Should | planned | skeleton ∥ · merge após Onda 0 · guardrail TRS mora na l2 (l11 só consome o flag) |

**Precedência de corte:** **Must** = l1+l2+l3+l4 (Onda 0 inteira — violações de
fórmula e contradições que o owner priorizou explicitamente; **nunca cortar
l1/l2**). **Should** = l5, l6, l9, l10, l11 (l9 é o que torna o relatório
honesto mesmo com dados imperfeitos — mitiga o dano das lanes de dados que não
fecharem) + l7 (código tático) + l8 (integridade de período). **Could /
cortável** = re-medição de concentração da l7 (derivada do gate de owner) e
qualquer follow-up estrutural (poda de `PropertyIdentity`, migration).

**Ordem de execução:** Onda 0 = `[l4 → l1] ∥ l2 ∥ l3` (l4 decide a base
temporal ANTES de l1 re-snapshotar golden — senão duplo rebaseline). Onda 1 =
l5 ∥ l6 ∥ l7 ∥ l8 (independentes). Onda 2 = l10 paralela desde o início;
l9/l11 fazem skeleton em paralelo e **seguram o merge até a Onda 0 mergear**.

## Gates de ação-do-owner (padrão A26 §"dono do gatilho")

Lanes de dados separam **código autônomo** (fecha sozinho) de **rodada manual
do owner** (gate nomeado, verificável, sem prazo):

- **`G-owner-reclassify`** ([[A28.l5]]): rodada de reclassificação dogfood dos
  maiores ofensores de `nao_identificado` via Learning Loop. KR2 (<5%) só é
  avaliado após o gate; sem o gate, mede-se a redução por regras novas.
- **`G-owner-label`** ([[A28.l7]]): rotulagem dos imóveis "classificação
  pendente" em Configurações (pós-dedup serão ~7-8 CTAs, não 11). Re-medição da
  concentração imobiliária (ancora o risco Crítico do parecer) roda pós-gate.
- **Fila do owner:** reclassificar categorias → rotular imóveis → (contínuo)
  re-gerar parecer a cada marco para acumular gerações (sinergia A26).

## KRs da janela

- **KR1 — conformidade de fórmula:** re-run dogfood com reserva e TRS conformes
  [FORMULAS.md](../../reference/FORMULAS.md)/[[ADR-191]] — teste de invariante
  (numerador/denominador do mesmo universo; reserva exclui carteira produtiva;
  `meses_alvo` por perfil de renda) + golden re-snapshot com diff explicado.
- **KR2 — categorização:** `nao_identificado` **<5%** das despesas no re-run,
  avaliado **pós-`G-owner-reclassify`**; se o gate não executar na janela,
  reporta-se a redução atingível só por regras (sem falhar a sprint).
- **KR3 — zero contradição cross-seção:** uma única recomendação PGBL por
  relatório (teste "PGBL statement count == 1"); toda métrica mensalizada
  carrega rótulo de janela no payload; rótulo Cerbasi coerente com a taxa de
  poupança exibida.
- **KR4 — honestidade de apresentação:** leitor do hero + banner responde "quão
  confiável é este relatório?" sem abrir `<details>`; nenhuma probabilidade/
  projeção sobre premissa fallback sem ressalva adjacente; âncoras do parecer
  renderizam no tipo certo (probabilidade em %, idade em anos, dinheiro em R$).

## Sinergia com A26 (nota — NÃO é KR)

Efeito colateral esperado: as re-gerações de parecer desta sprint alimentam o
gate de tráfego de [[A26.l2]] (flip strict: ≥20 gerações reais com budget
`needs_review` ≤15%) e exercitam o override v2 ([[A26.l4]]). Ao fim da sprint,
reavaliar se acumularam ≥20 gerações **qualificadas** e, em caso positivo,
retomar a A26 (`paused → current`). Não é KR para não incentivar re-runs vazios
(Goodhart) — o gate real da A26 exige qualidade, não contagem.

## ADRs exigidas (política ADR `Proposto` antes de PR P0/P1)

- **[[A28.l4]]** — ADR `Proposto` de **política de base temporal**: qual base de
  mensalização é canônica por família de métrica (ratios/KPIs = janela 12m;
  média full-period só com rótulo), e como meses de cobertura documental parcial
  entram no denominador. Co-design `financial-planner` + `senior-cto`.
- **[[A28.l3]]** — ADR `Proposto` curta de **regra de ano-base PGBL** (proposta
  inicial: ano-base mais recente **completo**; incompleto degrada com nota).
  Co-design `financial-planner`.
- l1/l2 **não** exigem ADR nova — conformam FORMULAS.md §Reserva e [[ADR-191]]
  já decididos (bug-fix de conformidade).

## Correções de fato registradas no co-design

1. O balde E4 `seguros` é **placeholder hardcoded** (`{"dados": []}` em
   `e4_serialization.py`), não um pipe quebrado; o texto "nenhuma apólice
   identificada" vem de `pontos_urgentes_analyzer.py` **incondicional**. O
   consumidor canônico de apólices é `compute_protecao` ([[ADR-240]]) — hoje
   dead code sem caller de produção. → escopo real da [[A28.l6]].
2. A duplicação 4× de imóvel na lista de excluídos vem das rows de
   `PropertyIdentity` persistidas **antes** do dedup [[ADR-246]] (e15 step 3 vs
   3b); `dropped_property_ids` é calculado e descartado. Fix tático na projeção
   é seguro (lista informativa); poda estrutural exige migration + backfill →
   débito fora da sprint. → [[A28.l7]].
3. Períodos `1899-12`/`2100-xx` passam por `_expand_periodo_string` (valida mês,
   não ano) e **não** são reconhecidos como sentinel (oficial: `999999`) —
   risco de ano-base fantasma. Banco vazio nas keys E3 vem de parsers E2 com
   `institution` vazio. `generate_legacy_filename` está correto — **não tocar**.
   → [[A28.l8]].
4. `$.protecao_patrimonial.apolices` que o parecer pediu **não existe mesmo no
   E5** (bug da l6 — o pedido do LLM estava certo e não deve ser suprimido
   enquanto a l6 não fechar); só `dependentes` existe sob path diferente
   (`$.irpf_kpis.dependentes`). → política 3-vias da [[A28.l11]].

- **Plano dono:** [[PLAN-report-trust]] ([plan/REPORT_TRUST/_README.md](../../plan/REPORT_TRUST/_README.md)).
- **Origem:** dossiê da revisão dogfood em `_scratch/dogfood_report_review/`
  (gitignored — dados sensíveis; achados incorporados nas lanes).
