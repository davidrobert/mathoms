---
id: ADR-420
type: adr
title: "Numerador da concentração imobiliária é rebalanceabilidade, não fluxo de caixa; e a imobilização patrimonial ganha indicador próprio"
status: Proposto
date: "2026-08-29"
amended_at: ["2026-08-31"]
relates_to:
  - "[[ADR-145]]"
  - "[[ADR-215]]"
  - "[[ADR-217]]"
  - "[[ADR-235]]"
  - "[[ADR-340]]"
  - "[[ADR-353]]"
  - "[[ADR-399]]"
  - "[[ADR-412]]"
  - "[[ADR-419]]"
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/report
  - area/methodology
aliases:
  - "ADR 420"
  - "numerador da concentração imobiliária"
  - "imobilizacao_patrimonial"
---

# ADR-420 — Numerador da concentração imobiliária, e o indicador de imobilização

> ⚠️ **Emendada em 2026-08-31** — a dependência da [[ADR-353]] declarada em §D2 era
> larga demais: ela vale para o **piso de cobertura**, não para o flip desta nota.
> Ver §Emenda 2026-08-31 ao fim.
>
> Origem: `RR6-02` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6) ·
> lane [[A40.l95]]. Co-design `financial-planner` (domínio) + `data-engineer`
> (contrato/fixture) + `senior-cto` (mecânica de ADR), 2026-08-29.

## Contexto

`compute_concentracao_imobiliaria_pct` é o SSOT do KPI ([[ADR-340]] · C11-Fase2):

```
cat_2 / (investivel_financeiro + cat_2) × 100
```

Medido no run `79a61e33` (dogfood, U2), com identidades que fecham ao centavo:

- `cat_2` (`patrimonio.imoveis_investimento`) = `imoveis_geradores` + `imoveis_nao_geradores`.
- `patrimonio.investivel_efetivo` = `investivel_financeiro` + `imoveis_geradores`. Ou seja,
  **o agregado canônico de capital produtivo já exclui o não-gerador**, e o denominador da
  concentração é `investivel_efetivo + imoveis_nao_geradores`.
- Publicado **50,62%**; sem o não-gerador, **49,08%**. Limiar 50,0, operador `<`
  ⇒ **o KPI inverte de veredito**, e **58,9%** do não-gerador é o que decide o cruzamento.
- O não-gerador é **um único** imóvel, com override **explícito** `nu_proprietario`, que
  `real_estate.excluded_properties` exclui do cap rate com o motivo literal *"não gera caixa
  nem está disponível para venda livre"*. Não é imóvel sem classificação — o defeito é
  metodológico, não de captura.

**O sinal é fixo, e é algébrico, não amostral.** `f(m) = m/(fin+m)` é estritamente crescente,
logo o publicado é **sempre ≥** o corrigido, com igualdade sse `imoveis_nao_geradores = 0`.
O defeito só **infla** concentração: produz falso alarme, nunca falso negativo.

**A crença que sustentou a fórmula é falsa.** A [[ADR-340]] afirma *"a métrica de concentração
considera só cat_2 (imóveis de renda)"*, e a [[ADR-145]] §2 define cat_2 como geradores **+**
não-geradores, nomeando `nu_proprietario`. **Sete** sítios nomeiam cat_2 (ou número derivado
dele) como "imóveis de renda" — o balde de composição, o rótulo da dimensão do score, o
docstring do SSOT, a descrição do alias no schema, o painel de metodologia, a tabela de maiores
ativos e o card de yield. E o **hero** usa o mesmo rótulo para `imoveis_geradores`: número
diferente, mesma página. O vetor do rótulo é a [[ADR-215]] P3,
cujo rename do balde cat_2 se justifica por *"comunicar o critério econômico real (geração de
caixa)"*.

**O motor já tem três partições de cat_2, e a concentração usa a terceira:**
`_CLASSIFICATIONS_GERADORAS` = {locado, comercial} ⊂ `INVESTMENT_CLASSIFICATIONS` =
{locado, comercial, especulacao} ⊂ cat_2. Nenhuma outra superfície usa a terceira.

## Decisão

### D1 — O discriminador do numerador é **rebalanceabilidade**, não fluxo de caixa

As três referências consagradas de planejamento patrimonial brasileiro que o produto adota
convergem, e não sobre "gera caixa hoje": convergem sobre *"é uma decisão de alocação que a
família pode reverter?"* — o próximo aporte move este ativo? A elas soma-se o veto de
acionabilidade: nu-propriedade é instrumento **sucessório**, e prescrever rebalanceamento
sobre ela é alarme que a família não pode executar.

```
imoveis_alocacao      = cat_2 ∩ {locado, comercial, especulacao, desconhecido}
imoveis_fora_alocacao = cat_2 ∩ {uso_pessoal, nu_proprietario}
concentracao_imobiliaria = imoveis_alocacao / (investivel_financeiro + imoveis_alocacao) × 100
```

- **`especulacao` entra** — alocação escolhida, com retorno esperado e saída possível; renda
  zero é exatamente o custo que o KPI deve doer. A trava da [[ADR-340]] está **certa** aqui, e
  a ratificação tem duas rotas independentes (metodologia; e o desalinho já existente entre
  `INVESTMENT_CLASSIFICATIONS` e `_CLASSIFICATIONS_GERADORAS`).
- **`uso_pessoal` sai** — estoque de consumo, mesma natureza econômica da residência
  principal, que já está fora dos **dois** lados. Manter a casa de praia dentro e a casa
  principal fora é arbitrário na direção que ninguém defende.
- **`nu_proprietario` sai** — [[ADR-235]] §Decisão item 4.

**O corte NÃO é `geradores` vs `nao_geradores`.** Sobre esse eixo, família com a carteira
inteira em terreno especulativo pontuaria **0% de concentração** — erro pior que o defeito
que esta ADR corrige.

### D2 — `desconhecido` entra, e a ressalva suprime a prescrição, nunca a medida

Ausência de rótulo não compra verde: num KPI de risco, o não-classificado fica do lado
conservador. Quando a fatia não-classificada de cat_2 cruza o piso de cobertura, suprime-se a
**prescrição dimensionada** (o ponto urgente, o alvo do plano de ação), e **nunca** a medida —
precedente entregue em [[ADR-412]] §D7/P2. O piso reusa a escada de [[ADR-353]], que está
`Proposto`: a dependência é **declarada**, não presumida, e esta ADR não flippa antes dela.

### D3 — A imobilização patrimonial ganha indicador próprio, sem alvo

`ratios.imobilizacao_patrimonial_pct` = `(residencia + imoveis_investimento) / patrimonio_liquido`,
base `patrimonio_liquido` (já existe no enum de [[ADR-412]] §D1). **Sem limiar, sem operador,
sem componente de score, sem gatilho, sem card novo** — entra em `_ORFAOS_DOMINIO` com motivo
declarado, pelo gate de [[ADR-419]]. `null` quando PL ≤ 0.

Isto **implementa** a primeira metade da [[ADR-235]] §4 (o número de denominador PL que nunca
existiu), enquanto D1 honra a segunda. §4 deixa de ser cláusula não-financiada.

**O nome recusa "concentração".** A [[ADR-235]] chama o segundo número de *"concentração
imobiliária total"*; dois `concentracao_*` com bases distintas é o RV8-02 recriado um nível
acima — o defeito que a [[A40.l80]] gastou 11 PRs matando. Honra-se a intenção, recusa-se o rótulo.

**Por que publicar o irmão é obrigatório, e não polish.** Estreitar o numerador sozinho
**apaga** a nu-propriedade de toda superfície de risco: troca falso alarme por **silêncio**,
e numa família com sucessão ativa o silêncio é o erro mais caro dos dois.

### D4 — O limiar 50,0 **não se move**; a justificativa dele é que se emenda

A procedência do 50 é **doutrinária**: `risk_trigger_registry.py` encoda a banda em que
as referências do produto divergem legitimamente entre si — 40 a 60, estabilidade contra
diversificação —, e 50 é o ponto médio dela. Não é função do numerador. Numerador menor
sobre o mesmo limiar é **mais** conservador, não menos: sai do numerador só o que nenhuma
prescrição alcança.

O que apodrece e precisa de emenda é o **rationale**: `FORMULAS.md` §219 sustenta o 50 dizendo
*"base carteira → leituras 1,5-2× as da base antiga → o limiar sobe 40→50"*, frase parcialmente
falsa com o numerador estreitado. Idem `docs/reference/rules/rule-concentracao-imobiliaria.md`,
**terceira cópia** e desatualizada nas duas dimensões (limiar 40, base "do patrimônio").

### D5 — O numerador passa a ser **declarado** no payload

Hoje o payload nomeia o denominador (`ratios.base_concentracao_imobiliaria`) e **não nomeia o
numerador em lugar nenhum**; o gate compensa fixando `numerador = patrimonio["imoveis_investimento"]`
em `tests/test_cobertura_de_base.py`. É o C14 da [[A40.l80]] (*"declarada ≠ usada"*) deslocado um
campo, e ela é dona assinada de C14/C19 e do arquivo. **Precondição de D1**, número-neutra:
o produtor publica primeiro, o gate passa a ler a declaração, e só então o rótulo muda — a ordem
que o C19 provou fechar a **classe** em vez da instância.

### D6 — Contrato

`patrimonio` publica `imoveis_alocacao` e `imoveis_fora_alocacao`;
`TERMOS_DA_BASE[carteira_produtiva_fixa]` passa a citar `imoveis_alocacao`. Sem isso
`bases_reproduzem` para de fechar, porque ele soma os `termos` lendo chave top-level de
`patrimonio`. **Termo de base mudando ⇒ bump de `BASE_VERSAO_CORRENTE`** ([[ADR-412]] §D8).
`score_version` **não** bumpa: o componente segue lendo `ratios.concentracao_imobiliaria`
([[ADR-217]] §D3 exige bump só se a fórmula do score mudar).

## Alternativas consideradas

**(A) Só trocar o rótulo — assumir que o KPI sempre foi de iliquidez.** Leitura legítima, e o
contra-argumento óbvio ("aporte não move esse ativo") falha: o aporte fecha o gap crescendo o
denominador. Rejeitada porque não é barata quando seguida até o fim — exige tirar "carteira
produtiva" do denominador (o relatório define produtivo em `investivel_efetivo`, excluindo
justamente este ativo), exige a contagem dizer 5 e não 4, e o denominador certo dela é
**patrimônio**, que é literalmente o D3. A alternativa identifica uma **segunda pergunta
legítima**; o defeito é um número só tentar responder as duas.

**(B) Só estreitar o numerador.** Rejeitada: apaga o ativo ilíquido, com ônus civil e ITCMD à
frente, de toda superfície de risco. Ver D3.

**(C) Cortar por `geradores` vs `nao_geradores`.** Rejeitada em D1 — erra em `especulacao`, e
errar ali é pior que o defeito de hoje.

**(D) Superseder a [[ADR-340]].** Rejeitada. Supersedure neste repo é **file-level**; sem a
cláusula do numerador a [[ADR-340]] segue governando oito decisões vivas (aposentar a contagem
de buckets, `invertido: true`, `range 0–60`, peso 1.0, rename do `nome_display`,
`SCORE_VERSION 2.1`, os thresholds 50/45/75/85, e a base = carteira produtiva). Marcar a nota
`superseded_by` diz "pule isto" sobre oito coisas que continuam valendo.

> **Regra de fronteira** (aplicável além deste caso): use `supersedes` quando cai a **tese** da
> nota. Quando cai uma **cláusula** e a tese sobrevive, o par é **emenda datada de retratação na
> nota alvo, que aponta, + ADR nova que decide, com `supersedes: []`**. Teste: *a nota alvo, lida
> sem a cláusula removida, ainda governa decisão viva?* Sim → emenda.

## Consequências

**O fix não move dinheiro.** `bruto`, `liquido`, `investivel_efetivo` e cat_2 ficam
byte-idênticos. Movem-se a razão, o alerta `concentracao_alta`, `pontos_urgentes`, a
componente 4 do score e a evidência que o parecer cita.

**O score é materialmente insensível, e a lane não deve prometer o contrário.** A nota da
componente vai de 4,0 para 4,2 e o composto de 7,438 para 7,463 — **arredonda 7,4 nos dois**.
Quem se move são as **quatro superfícies de limiar binário**. O `spread_critico` (piso 45)
**sobrevive** ao conserto, e é ele que continua dizendo o risco real desta família.

**A queda para 49,08% é correção de medição, não progresso.** A copy não pode narrar o flip
para verde como melhora — [[ADR-419]] e o §Rebaseline consciente da [[A40.l80]] são o precedente.

**Nenhum golden do repo pode provar o conserto.** `backend/tests/snapshots/dogfood_view_model.json`
tem `imoveis_geradores = 0` e `imoveis_nao_geradores` = 100% de cat_2 (concentração 82,19%), e
`real_estate` é `null` inteiro — o alias, o alerta, o `spread_critico` e `excluded_properties`
não são exercidos por golden nenhum. As duas leituras são **extremos degenerados** ali, então
verde depois do conserto provaria só que geradores é zero. É extensão maior que o §Follow-up
declarado da [[ADR-340]], e é **precondição bloqueante**: a fixture é o gate.

## Critério de aceite (PR de `Decidido`)

1. **Conservação, tolerância zero:** `imoveis_alocacao + imoveis_fora_alocacao == imoveis_investimento`
   em cents; `bruto`, `liquido`, `investivel_efetivo`, cat_2 **inalterados** no golden.
2. **A fixture discrimina antes do gate existir:** golden ganha ≥1 `locado` **e** ≥1 `especulacao`
   com valores distintos e não-nulos, e teste irmão de `test_a_fixture_discrimina_as_bases` prova
   que os destinos são dois-a-dois distintos. Sem isso, verde é vacuoso.
3. **Mutação como prova:** trocar o numerador no produtor deixa `test_cobertura_de_base` vermelho
   **pela declaração do produtor** (D5), não pela chave fixa no teste.
4. **`bases_reproduzem` verde** com os termos novos; `BASE_VERSAO_CORRENTE` bumpado;
   `score_version` **não** bumpado.
5. **Contagem == cardinalidade:** o número de imóveis exibido ao lado do KPI é o do conjunto
   somado no numerador. Hoje o card diz 4 e o numerador soma 5.
6. **Zero superfícies dizendo "renda" sobre número que inclui não-alocação** — hero, balde de
   composição, card, `Top15AtivosCard`, `RealEstateBreakdownPanel`, docstring do SSOT,
   `financial_score_calculator._DIMENSION_LABELS`, e a descrição do alias em
   `config/schemas/e5_analysis.schema.json`.
7. **O ativo não desaparece:** `imobilizacao_patrimonial_pct` publicado, órfão declarado, e o
   parecer o alcança. A [[ADR-235]] §4 deixa de estar não-financiada.
8. **Rationale reconciliado:** `FORMULAS.md` §219 e `rule-concentracao-imobiliaria.md`.
9. **`golden_diff` per-família** com manifesto 1× ([[ADR-340]] §Critério de aceite), e
   `compare_reviews` com paths esperados declarados no PR.

## Não-objetivos

- Recalibrar o limiar 50, o `range_max: 85` do score, o co-threshold 45 ou o hard-block 75.
- Card novo, componente de score novo ou gatilho para `imobilizacao_patrimonial_pct`.
- Convergir `carteira_produtiva_fixa` sobre `carteira_produtiva_familia` — [[ADR-412]] §E5
  fechou esse ramo, e D1 não o reabre (o numerador novo é subconjunto próprio de cat_2, não
  `cat2_efetivo`, e segue toggle-independente).
- O regime default de classificação — imóvel **sem override** cai no numerador por caminho
  distinto. É defeito de **captura**, não de metodologia: fix por estado ternário e cobertura
  ([[ADR-412]] §D2), critério de aceite próprio. Registrado no §Follow-ups da [[A40.l95]] e
  **ainda sem lane id alocado** — a alocação é do rito de abertura de lanes da sprint.

## Deferimento datado — cardinalidade de `especulacao` no corpus (2026-08-29)

D1 ratifica `especulacao` no numerador por metodologia, sobre corpus onde ela **não ocorre**:
o dogfood tem zero, e nenhum golden a exercita. A ratificação é doutrinária e não empírica.
**Dono:** [[A40.l95]]. **Condição de retomada:** primeiro workspace com `classification =
especulacao` e valor material, ou a fixture do critério 2 revelando comportamento não previsto.

## Emenda 2026-08-31 — a dependência da [[ADR-353]] vale para o piso, não para o flip

A §D2 fecha com *"o piso reusa a escada de [[ADR-353]], que está `Proposto`: a dependência
é declarada, não presumida, e **esta ADR não flippa antes dela**"*. A última oração é
retratada: ela gateia a nota inteira numa dependência que pertence a **uma** de suas
cláusulas. Três medições, feitas no fechamento da [[A40.l95]]:

1. **A escada da [[ADR-353]] está em produção.** `NAO_IDENTIFICADO_PARCIAL_PCT = 10` e
   `_INSUFICIENTE_PCT = 30`, `_confianca_nivel`, e `diagnostico_confianca` publicado no
   payload (`{"nivel": "alta", "share_nao_identificado_pct": …}` no golden), lido pelo
   `kpi_target_catalog`. O que falta é o **consumidor de frontend**, não o mecanismo.
2. **O flip da [[ADR-353]] pende da [[A40.l11]]**, `planned` e **P2**, cujo critério é
   *"`rg 'diagnostico_confianca' frontend/src` > 0"*. O §D1 desta nota é **P0**. Gatear
   P0 atrás de P2 por uma cláusula de forma é o custo que a emenda remove.
3. **O precedente já existe, e é mais novo que esta nota.** A [[ADR-425]] (`Decidido`,
   2026-08-30) **importa** as constantes da [[ADR-353]] com ela ainda `Proposto`, e diz
   isso literalmente: *"importando as constantes da [[ADR-353]] (nunca redeclarando-as)"*.

**O que a emenda muda:** o §D1 (numerador por rebalanceabilidade), o §D3, o §D4 e o §D6
deixam de esperar a [[ADR-353]]. **O que ela NÃO muda:** o **piso de cobertura** do §D2 —
a supressão da prescrição dimensionada quando a fatia `desconhecido` de cat_2 cruza o
piso — continua atrás do flip da [[ADR-353]], porque é ele que reusa a escada. Até lá,
`desconhecido` entra no numerador **sem** ressalva de supressão, que é o lado
**conservador** e o mesmo comportamento de hoje para imóvel não classificado.

**Por que emenda e não ADR nova:** cai uma **cláusula**, e a tese — o numerador corta por
rebalanceabilidade — sobrevive inteira. É o teste da §Alternativas (D) desta própria nota
aplicado a ela mesma.

**Deferimento datado — piso de cobertura do §D2 (2026-08-31).** **Dono:** [[A40.l95]].
**Condição de retomada:** flip da [[ADR-353]] para `Decidido`, que a [[A40.l11]] destrava.
