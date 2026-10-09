---
id: A40.l121
type: lane
title: "O prompt 1.4.1 tirou o endereço da descrição e a identidade de imóvel perdeu a âncora: a chave passa a vir da ficha estruturada do IRPF"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l121-ancora-estruturada-de-imovel
owner: data-engineer
depends_on: []
parallel_with: ["[[A40.l113]]"]
adrs: ["[[ADR-440]]", "[[ADR-215]]", "[[ADR-225]]", "[[ADR-392]]", "[[ADR-439]]"]
tags: [type/lane, sprint/a40, status/in-progress, priority/p0, area/pipeline]
---

# A40.l121 — `ancora-estruturada-de-imovel`

> **Origem:** desdobramento da [[A40.l113]] pedido pelo dono em 2026-10-08. É o item 3 do
> §Deferimento dela (critério 3, "a identidade de imóvel ancora em campo **estruturado**"),
> que a l113 registrou como "precisa de lane própria". A l113 entrega a rede de segurança
> ([[ADR-439]]: balde de imóvel sem classificação apurada sai `null` com veredito); esta lane
> conserta a **causa**.

## O que está medido

Passo 0, 2026-10-08, autorizado pelo dono: artefatos `E1.5a` decriptados **read-only** e
lidos só por traço booleano, comprimento, contagem e nível da cascata do `canonicalize` —
nenhum texto, valor, membro ou endereço impresso. Três runs sobre os **mesmos 10
documentos** (mesmo hash na `artifact_key`): `3a5b9c7d` e `7d860f0b` no prompt `E1.5a`
`1.3.0`, `40d1af2a` (o do `U5`) no `1.4.1`. Três dessas declarações têm imóvel: **10**
itens com `categoria_hint=imovel` e `secao=bens_direitos`.

### A descrição perdeu o endereço, não o churn

| era do prompt | `canonicalize(descricao)` em `via_numero` | em `mat`/`qa`/`iptu` | `None` |
|---|---|---|---|
| `1.3.0` (dois runs) | **8** de 10 | 0 | 2 |
| `1.4.1` | **2** de 10 | 0 | 8 |

Os 2 que resistem na `1.4.1` são os únicos cuja **própria discriminação** traz via+número.

### O endereço mora na ficha, em campo rotulado

Lidos os 3 PDFs com o mesmo extrator do `E1.5a` (`DocumentTextExtractor(max_chars=80_000)`,
nenhum truncado): **toda** ficha de imóvel traz os rótulos estruturados — a contagem de cada
rótulo na seção de Bens e Direitos é igual ao número de imóveis da declaração (4, 4 e 2).
A ordem no texto é fixa:

`[discriminação]` → `Inscrição Municipal (IPTU)` → `Logradouro` → `Nº` → `Bairro` →
`Município` → `UF` → `CEP` → `Área Total` → `Data de Aquisição` → `Registrado em
Cartório` → `Nome do Cartório` → `Matrícula`

| traço | contagem |
|---|---|
| itens com via na `1.3.0` cujo via está no **valor do campo `Logradouro`** | **8 de 8** |
| desses, cuja discriminação **não tem** via | **6 de 8** |
| descrições `1.4.1` com recall de tokens 1,00 contra o PDF (transcrição literal) | 10 de 10 |

**Conclusão:** a `1.3.0` ("Descrição do item (como consta na declaração)") dobrava os campos
estruturados da ficha para dentro da descrição; a `1.4.1` ([[A42.l15]], "copie INTEGRALMENTE
o texto da discriminação… transcrição literal", efeito declarado **não medido** no próprio
arquivo do prompt) copia só a discriminação — e copia **certo**. O defeito não é a regra
nova: é que a identidade de imóvel dependia de um efeito colateral da regra velha.

### A medição de 2026-09-01 da [[A40.l113]] cai neste ponto

A l113 registrou "o caractere duplicado não é a causa… o motivo é **estrutural**, não churn:
`canonicalize` exige via+número, e as descrições de IRPF em que ela falha são nome de
condomínio ou narrativa de compra". A parte "não é o typo" procede; a parte "estrutural"
não: as mesmas declarações canonicalizavam 8 de 10 dois dias antes. O eixo é a **era do
prompt**. A correção do texto da l113 fica com a sessão dela.

### As classificações do usuário, e o que as re-alcança

`property_identity` do workspace: **19** rows, **6** com override em
`workspace_property_overrides` — 4 `locado`, 1 `residencia_principal`, 1 `nu_proprietario`.
Cinco foram cunhadas no nível `via_numero`; a de `nu_proprietario`, no nível **`mat:`**.

Contrafactual com **extrator perfeito** (os valores lidos da própria ficha do PDF), em modo
**sem mint**, comparando byte a byte com o `endereco_canonical` gravado:

| chave montada a partir da ficha | rows com override re-alcançadas |
|---|---|
| só `via_numero` — `Logradouro` + `Nº` | **5 de 6** (a `nu_proprietario` fica órfã) |
| os três níveis — `via_numero`, `mat:` (`Matrícula`), `iptu:` (`Inscrição Municipal`) | **6 de 6**, zero mint |

Cobertura de nível por ficha no mesmo proxy (10 fichas): `via_numero` 8, `mat` ≥7,
`iptu` 5, algum nível **10**.

### Outros dois traços do mesmo corpus

- **Estabilidade `1.3.0`×`1.3.0`:** 10 de 10 descrições de imóvel byte-idênticas entre
  `3a5b9c7d` e `7d860f0b`. É **amostra única** (um par de runs, três documentos) e não diz
  nada sobre a estabilidade da âncora nova — essa é medição desta lane.
- **`codigo_rfb`:** a `1.4.1` emitiu `01-11`/`01-12` (grupo-código) em 1 das 3 declarações;
  na `1.3.0` as mesmas saíam `11`/`12`. A grafia composta nasce da era do prompt.

## O que o co-design mudou no plano

O plano de entrada tinha três PRs — contrato, **bump do prompt** e enricher. Dois pontos caíram
no co-design de 2026-10-08 (`data-engineer`, `prompt-engineer`, `senior-cto`):

- **O produtor não é o LLM.** O `data-engineer` objetou que a âncora transcrita pelo LLM repete a
  causa ([[ADR-400]]; o `01-11`×`11` da mesma era é deriva de transcrição), e o `prompt-engineer`
  cobrou o mesmo pela [[ADR-081]]. **O dono decidiu** pelo parser determinístico de rótulo. Medido
  antes da decisão, no mesmo corpus: âncora em 10 de 10 fichas, e o join ficha↔item só pelo valor
  dá ficha única em 8 de 10 itens (2 ambíguos, zero sem ficha), com coerência 6/6 contra o via da
  `1.3.0`. Ganho decisivo: o parser cura **todo** artefato já gravado sem re-extração LLM, que
  re-sortearia os demais campos e é decisão de custo do dono ([[ADR-311]] D3).
- **A âncora não entra no `baseline_patrimonial`.** O consolidado a carrega em memória até o
  enricher e a remove depois da identidade: matrícula e inscrição são quasi-identificadores, e o
  gate de PII da [[ADR-435]] não veria valor solto. Logo o PR0 declara só no schema do `E1.5a`.

O desenho fechado está na [[ADR-440]] (D1–D7).

## Critério de aceite

1. O `E1.5a` grava `ancora_imovel` nas fichas de imóvel que o parser lê, sem LLM, em **todo** IRPF
   do run — inclusive os que o incremental não reenvia — e regrava só quando a âncora muda (o
   segundo run regrava zero rows).
2. Join ambíguo ou ficha não achada fica sem âncora, com `extract.ancora_imovel_ambigua` /
   `extract.ancora_imovel_sem_ficha` e `offending_value` sem PII.
3. A chave por nível sai dos **mesmos** extractors do `endereco_canonicalizer`; sem âncora, a chave
   é byte-idêntica à de hoje.
4. Medição read-only no dogfood, com o enricher novo em modo sem mint: **6 de 6** rows com override
   re-alcançadas, Δrows = 0, zero conflito de veto.
5. `backend/tests/integration/test_property_override_sticky.py` existe e prova que a classificação
   sobrevive ao re-upload. Os contrafactuais reprovam: sem âncora o colapso volta, sem veto dois
   apartamentos do mesmo prédio fundem, e cada nível sozinho tem o seu caso.
6. A âncora não aparece em `baseline_patrimonial`, E5, view-model nem parecer (teste de ausência).

## Plano de PRs

| PR | conteúdo | depende de |
|---|---|---|
| docs | esta lane + [[ADR-440]] `Proposto` | — |
| PR0 | `ancora_imovel` + `ancora_versao` em `e15_baseline_extract.schema.json`; teste de que o schema aceita e recusa as formas certas | docs |
| PR1 | parser + join + integração no `E1.5a` (antes do early-return do incremental) + razões; `golden_diff` do dogfood igual a zero | PR0 |
| PR2 | `match()` no port e nos adapters; enricher em duas fases com veto; repasse em `consolidate_from_itens` + remoção da âncora após a identidade; teste sticky; medição no dogfood; [[ADR-440]] vira `Decidido` com as emendas datadas da [[ADR-225]] e da [[ADR-265]] | PR1 · davidrobert/mathoms#2062 (normalização do `codigo_rfb`) |

O PR2 toca o mesmo trecho do enricher que o #2062 (`_lookup_or_mark`) e monta cada chave pelo
sub-código normalizado dele: o `PropertyLookupKey` passa a recusar grafia crua. O #2062 espera uma
consulta de colisão em produção pelo dono, então o PR2 não tem data.

## Fora do escopo

- O `llm_call_log` grava só a 1ª de ~10 chamadas do `E1.5a` por run (medido nos mesmos três runs:
  10 artefatos com 38–104 s de intervalo, 1 linha de log). Subestima custo e o hard-stop de
  orçamento; virou tarefa própria.
- Conjunto de chaves por row e namespace de matrícula por município/UF — [[ADR-440]] §Deferimentos.
