---
id: A40.l69
type: lane
title: "Cobertura de investimentos por membro: zero apurado não é o mesmo que não apurado"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l69-cobertura-investimentos-por-membro
owner: data-engineer
adrs:
  - "[[ADR-145]]"
  - "[[ADR-243]]"
  - "[[ADR-267]]"
  - "[[ADR-346]]"
  - "[[ADR-357]]"
depends_on:
  - "[[A40.l66]]"
  - "[[A40.l67]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
---

# A40.l69 — `a40-l69-cobertura-investimentos-por-membro`

> Aberta em 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] (Onda 3,
> itens 3a e 3b). Fecha RV6-04 da §r6 — o único P0 do MVP que não é do seam.
> Nasce `blocked`: a regra unificadora que ela consome ("prescrição exige
> cobertura; descrição admite ressalva") é decidida na **ADR-A**, que a
> [[A40.l66]] abre, e a janela de rebaseline desta lane (J4) só abre com a J2 da
> [[A40.l67]] fechada.
>
> **Destravada em 2026-08-18.** As duas condições estão satisfeitas: a ADR-A é a
> [[ADR-394]], emendada em #1531 com a regra "prescrição exige cobertura;
> descrição admite ressalva"; e a J2 fechou em #1534 **sem consumir rebaseline**
> (`golden_diff` de `aa53d5bf~1`×`aa53d5bf`: 2 campos `new`, zero `value_delta`,
> sinal **=**), logo a J4 abre com o orçamento inteiro. O resíduo da [[A40.l67]]
> — o flip para strict — foi re-homeado à [[A40.l58]] e **não** é insumo desta
> lane: ela consome a regra e o seam, não o modo de validação do schema.
>
> **Estado em 2026-08-19 — 3a e 3b entregues, com correção medida.** Os PRs de
> 3a (#1541, #1542) shipuram o enum e o flip para `null`, mas com um predicado
> que media o **contêiner** (`bool(bens)`, sempre truthy): `nao_apurado` era
> inalcançável em produção, 0 em 114 instâncias-membro. O 3b saiu no #1550
> (match por token + gate `check_member_key_substring.py`); o `else: membro =
> membro_raw` do consolidador **segue vivo** — entregou (ii) e (iii), não (i).
> Um ataque medido a 2026-08-19 achou a raiz um andar abaixo: o **eixo de ano**
> é do domicílio, e cônjuges que declaram em anos disjuntos zeram um ao outro.
> Correção e re-medição na [[ADR-394]] §Emenda 2026-08-19 (c) — D9 (presença de
> linha não é medição) e D10 (ano-base por membro). §Ataque abaixo.

## Problema

O balde de investimentos do cônjuge publicou **0,00** com posições presentes no
artefato imediatamente a montante, `fonte_investimentos="posicoes_atuais"` e
`pl_ressalva=false`. Nenhuma das três afirmações é verdadeira, e nenhuma camada
as contradisse. A cadeia é de cinco elos, todos em `main`:

**1. O slug bruto do LLM vira chave de membro.**
[`investments_consolidator.py:317-324`](../../../../pipeline/domain/services/investments_consolidator.py)
resolve `membro` pelo resolver **name-based** ([[ADR-243]], 5 estratégias de
slug) e, no miss, **preserva o slug bruto**:

```python
resolution = self._member_name_resolver.resolve(membro_raw)
if resolution.canonical_key:
    membro = resolution.canonical_key
else:
    membro = membro_raw   # ← 6 slugs para 3 pessoas
```

A estratégia 0 da [[ADR-267]] (CPF como identidade primária) **nunca é chamada
aqui**: `resolve_by_cpf` tem um único call-site de produção,
`consolidate_baseline.py:410` (E1.5c). O caminho de investimentos não tem CPF
para consultar — `config/schemas/e2_llm_artifact.schema.json:32` declara
`membro` (`string|null`) e **nenhum campo de CPF**.

**2. A atribuição é por substring, e o titular é testado primeiro.**
[`patrimonio_calculator.py:315-327`](../../../../pipeline/domain/services/patrimonio_calculator.py):
`identity.titular_key in key_lower` antes de `identity.conjuge_key in key_lower`;
o que não casa nenhum dos dois cai em `unattributed` — e `unattributed` é
**somado ao titular**. Um slug que o resolver não canonicalizou não fica órfão:
ele é creditado à pessoa errada, em silêncio.

**3. O fallback IRPF só dispara com valor positivo.** Linhas 331-342: `if
irpf_conjuge > 0`. Sem posição atribuída e sem IRPF, o balde permanece `0.0` — e
`0.0` é publicado com a mesma cara de um zero medido.

**4. `fonte_investimentos` é uma string global do domicílio** (linha 239). Ela
descreve o caminho que o *cálculo* tomou, não a cobertura de *cada membro*: com
o titular vindo de posições atuais e o cônjuge de lugar nenhum, o campo diz
`"posicoes_atuais"` para os dois.

**5. `pl_ressalva` mede outra coisa.**
[`patrimonio_resolvers.py:532-549`](../../../../pipeline/domain/services/patrimonio_resolvers.py)
deriva a ressalva de `posicoes_sem_marcacao_por_membro` — posições de renda
variável **sem valor de mercado** ([[ADR-346]]). Membro sem posição alguma não
produz ticker sem marcação, logo `bool(tickers)` é `False`. A ressalva não está
quebrada; ela é **inerte** para esta classe, e foi lida como "PL certificado".

Efeito publicado: `next_aporte_classe` prescreveu sobre carteira truncada, e o
relatório afirmou zero onde não mediu.

**Escala do elo 2:** a varredura por substring em chave de membro tem **31
call-sites** em 4 arquivos — `patrimonio_resolvers.py` (11),
`analyze_finances.py` (10), `e5_member_resolver.py` (8),
`patrimonio_calculator.py` (2). O analyzer citado no RV6-14 é um deles, não o
conjunto.

## Escopo

**3a — cobertura por membro, com os 3 estados.** Campo **próprio**
`cobertura_investimentos[]` no payload de patrimônio (por membro:
`status`/`fonte`/`frescor`/`motivo`). **Não** sobrecarregar `pl_ressalva`
([[ADR-346]] mede posição sem marcação; são sinais distintos e a fusão apagaria
os dois). Estados, fechados em enum:

| Estado | Significado | Publica |
|---|---|---|
| `apurado` | fonte presente, valor apurado | o valor |
| `zero_apurado` | fonte presente, valor é zero | **0,00** — é o caminho de saída da ressalva |
| `nao_apurado` | sem fonte para o membro | **`null`** + ressalva + `needs_review` — **nunca 0,0** |

`fonte_investimentos` global permanece (compat de leitor), mas deixa de ser a
resposta à pergunta "este membro foi medido?" — quem responde é o campo novo.

Prescrição suprimida enquanto qualquer membro estiver `nao_apurado` (regra
unificadora da **ADR-A**): `next_aporte_classe=None` + `desvio_max_pct=None` —
ambos **já** `Optional` em
[`alocacao_alvo_deviation.py:122-123`](../../../../pipeline/domain/services/alocacao_alvo_deviation.py)
— mais `motivo_supressao`, que é **campo novo** (zero ocorrências em `main`). O
resto do relatório **não** é suprimido: descrição admite ressalva.

**3b — identidade de membro antes de qualquer agrupamento.** Duas frentes, e a
segunda é a que fecha o buraco no caminho de investimentos:

- **Onde há CPF, CPF é a chave** ([[ADR-267]]): já vale no E1.5c; esta lane
  **não** re-implementa isso, só proíbe que o agrupamento aconteça antes dele.
- **Onde não há CPF** (caminho de investimentos), slug não canonicalizado
  **deixa de virar membro**: o miss do resolver produz `nao_apurado` +
  `needs_review` nomeando o slug, e o valor **não é absorvido pelo titular**.
  Some o `else: membro = membro_raw` da linha 324.
- **Varredura + gate:** os 31 call-sites de match por substring em chave de
  membro passam a match exato contra chave canônica; gate reprova call-site novo
  (`<key> in <str>` sobre `titular_key`/`conjuge_key`). Resíduo que não couber no
  PR entra em **allowlist datada com dono**, nunca silenciosa.

**Fora desta lane, por decisão do plano:** adicionar `cpf` ao artefato de
posições é mudança de contrato do E2-llm sobre fonte que não o carrega
(extrato de corretora não declara CPF de forma confiável) — não é o fix, e
trocaria um proxy por outro.

## Enforcement

WARN-first, doutrina [[ADR-357]]/[[ADR-358]]. Default é **rebaixa/declara**:
`nao_apurado` ⇒ balde `null` + ressalva + `review_reason` tipado + supressão da
prescrição; nunca reter run, nunca abortar. Taxa de disparo medida sobre os
payloads **r5+r6** e declarada na ADR-A **antes** de qualquer flip — a medição é
por membro, não por workspace, senão um domicílio de 2 pessoas com 1 buraco conta
como "100% coberto". Kill-switch de 1 env var, provado por teste.

O gate anti-substring nasce medido: os 31 sites atuais são o denominador, e o PR
declara quantos viraram match exato e quantos entraram na allowlist.

## Critério de aceite

- **Prova por mutação — os dois zeros ficam distinguíveis.** É o aceite
  principal, e são duas mutações sobre o mesmo fixture:
  1. Renomear o slug do cônjuge no payload de posições para uma variante que o
     resolver não casa ⇒ **hoje** o valor migra para o titular e o balde do
     cônjuge sai `0,00` com `fonte_investimentos="posicoes_atuais"` e
     `pl_ressalva=false`; **pós-fix** ⇒ `status="nao_apurado"`, balde `null`,
     ressalva + `needs_review` nomeando o slug, e o **titular não absorve** o
     valor (assert sobre o balde do titular, não só sobre o do cônjuge — sem ele
     a mutação não prova o elo 2).
  2. Zerar de fato as posições do cônjuge, com fonte presente ⇒
     `status="zero_apurado"`, balde `0,00`, **sem** ressalva e **sem** supressão
     de prescrição. Sem esta segunda mutação o fix vira "tudo vira ressalva", que
     é o modo de falha oposto e igualmente inútil.
- Teste que constrói `unattributed > 0` à mão e prova que ele **não** é somado ao
  titular sem carimbo de cobertura.
- Gate anti-substring reprova um call-site novo introduzido no próprio teste
  (prova por mutação do gate, não só sua existência); allowlist datada com dono
  para o resíduo.
- Supressão de prescrição exercitada ponta-a-ponta: `nao_apurado` ⇒
  `next_aporte_classe is None` **e** `motivo_supressao` preenchido **e** o resto
  do payload publicado.
- Taxa de disparo por membro medida sobre r5+r6 e escrita na ADR-A.
- **Nenhuma ADR nova.** 3a é coberto pela ADR-A (§ADRs a abrir do plano: "Cobre
  1a/1b/1c/1d/**3a**"); 3b é [[ADR-267]], já `Decidido`. Se a implementação
  exigir decisão que nenhuma das duas cobre, **pare e escreva** — não alargue a
  ADR-A por conta própria.
- Rebaseline em commit isolado dentro do PR do fix
  (`dev/check_golden_rebaseline_isolation.py`), `dev/golden_diff.py --manifest`,
  sinal ↑/↓/= declarado. **Janela J4** (§0d do plano) — abre com a J2 fechada.
  O sinal esperado é **↓ no balde do titular** e **↑ ou `null` no do cônjuge**:
  se o titular não cair, o elo 2 não foi cortado.

## Fora de escopo

- **Render** dos 3 estados (donut, tabela, banner) → [[PLAN-report-trust]]
  (7e é o predicado único da composição; 7a é o guard de contrato). Esta lane
  entrega o **dado**; publicar `null` sem quebrar a UI é lá.
- **Fallback IRPF re-eleito por membro** — fase 2 do 3a no plano, sequenciada
  **pós-Onda 1** para não herdar roteamento sujo. Entra como PR próprio desta
  lane só depois da [[A40.l67]] mergeada.
- `cpf` no artefato de posições (E2-llm) — ver §Escopo.
- Cenário do cônjuge, `fator_reduzido` e elegibilidade [[ADR-167]] → item 3d do
  plano (RV6-14), fora do MVP. Esta lane toca o **mesmo** `conjuge_key`, então
  quem pegar 3d confirma no pickup se o diff colide.
- Tripwire fluxo×estoque (3e) e histerese da reserva (3f) → `planned` no plano.
- `gap_qualitativo` × `irpf_kpis.dependentes` (3c, RV6-05) → item próprio da
  Onda 3, produtor distinto.

## Ataque medido — 2026-08-19

Ataque adversarial aos PRs de 3a, **depois** do merge deles e **durante** o do
3b. O que a medição achou, com a saída que a sustenta na [[ADR-394]] §Emenda (c):

- **`nao_apurado` era inalcançável.** `tem_bens_irpf = bool(conjuge_bens)` e
  `build_members_from_consolidated` materializa `bens` com 4 chaves sempre. Os
  três efeitos do estado (`null`, `review_reason`, supressão) nunca armaram —
  0/114 instâncias-membro. Suíte verde o tempo todo.
- **A raiz não era o predicado.** `_max_value_year` escolhe **um** ano para o
  domicílio; os dois membros declaram em anos disjuntos, então por construção só
  um pode ser valorado. Os 9 lançamentos do cônjuge valem **R$ 110.130,67** em
  2023 e saíam `0,00`. Com o ano forçado a 2023, quem zera é o **titular** — o
  defeito é do eixo, não da pessoa.
- **O conserto óbvio não consertava.** `any(bens.values())` e
  `bens["investimentos"]` não-vazio medem **0/114**, igual ao predicado quebrado.
  A distinção que importa é presença × valor.
- **A ordem é restrição dura.** O predicado de valor **antes** do fix de ano
  suprimiria a prescrição em 5/5 dos runs recentes, publicando `null` sobre valor
  que existe. Depois dele: 0/114.
- **A taxa da ADR era do mecanismo pretendido**, não do entregue. A tabela de
  sintomas segue verdadeira; a inferência de rotulagem, não. Corrigida na (c).
- **O fixture dos 22 testes usava um shape que nenhum produtor emite**
  (`baseline={"members": <dict>}`). Trocado pelo do E1.5c; com ele, reintroduzir
  o ramo mata 5 testes — antes matava 0.
- **`frescor` nunca foi implementado.** A §Escopo pediu
  `status`/`fonte`/`frescor`/`motivo`; shipou com 3. Entra na (c).

### Entregue

| PR | o quê |
| --- | --- |
| #1541 · #1542 | 3a — enum de cobertura + flip para `null` (predicado inerte) |
| #1550 | 3b (ii)+(iii) — match por token + gate anti-substring |
| _este_ | D10 (ano por membro + guarda do top-up) e D9 (ramo do contêiner sai, `frescor` entra, gate de alcançabilidade) |

### Aberto, com dono

- **3b (i)** — `else: membro = membro_raw` em `investments_consolidator.py:324`.
- **Trava do cônjuge dependente** e **válvula declarada** para domicílio sem
  investimentos → §Deferimento datado da [[ADR-394]] §Emenda (c).
- **68 % do balde do titular é chave vazia** (`total_por_membro` tem `''`).
  Pós-#1550 vai para `nao_atribuido`, que **não** gera linha de cobertura nem
  `review_reason` e não suprime nada — buraco maior que o do cônjuge.
- **Kill-switch parcial**: `valor_publicavel` não consulta
  `cobertura_enforcement_ligado()`; com a env em `0` o balde segue `null` e some
  a razão que o explica.
- **Copy de `null` na narrativa** sai "Bia possui N/D concentrados em
  instituições…" — é da lane de render ([[PLAN-report-trust]] 7e).
- **Colapso cross-ano** no consolidador: 26→9 itens do cônjuge em 2026-08-12 com
  input idêntico, survivor keyed no ano velho.
