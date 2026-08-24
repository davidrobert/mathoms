---
id: A40.l6
type: lane
title: "Cards de imóvel e dívida: PII cartorial, contrato de campo e zero-como-valor"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l6-cards-imovel-divida
adrs: ["[[ADR-337]]"]
depends_on: ["[[A40.l5]]"]
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/frontend
  - area/backend
---

# A40.l6 — `cards-imovel-divida` (RV3-06, RV3-12, RV3-27)

## Problema

**PII (RV3-06).** Descrição cartorial crua do IRPF é interpolada **verbatim** em
`RealEstateYieldCard.tsx:194,303,373` e `EndividamentoCard.tsx:75`: identificador
de terceiro em claro, matrícula, inscrição municipal, endereço com CEP. A
[[ADR-337]] é escopada a `top_ativos[].nome` e seu **critério 4 (gate de PII no
view-model) não existe**. O pior vetor (egresso ao LLM) já está fechado pelo
sanitizer; o residual é minimização violada em **artefato exportável**.

**Contrato (RV3-12).** O card lê `d.valor`/`d.taxa`; o E5 emite
`saldo_devedor`/`taxa_juros`/`parcela_mensal`. Sem adapter no boundary → a linha da
dívida exibe `—` no valor.

**Zero-como-valor (RV3-27).** Valor de imóvel `0` renderiza como zero real, contra
a regra de copy (ausência ⇒ `—`).

> **Dependência.** Parte dos zeros observados no dogfood não era ausência de dado:
> era uma identidade duplicada carregando o override do usuário sem valor
> associado ([[TRACK-property-identity-cross-era]] · [[ADR-385]]). Fechar só a
> exibição converteria a linha fantasma em `—` e deixaria o override preso vivo —
> a lane ficaria verde sobre o defeito. Confirme o estado das identidades do
> workspace de teste antes de medir esta lane.

## Escopo

- UI exibe rótulo curto derivado (`endereco_canonical`), não `descricao` bruta.
  Descrição completa, se necessária, atrás de disclosure **com redação**.
  > **Contradito pela medição — ver §Ataque A1/A2.** `endereco_canonical` não é
  > rótulo curado: é `canonicalize(descricao)`, cuja cascata devolve
  > `mat:<matrícula>` ou `iptu:<inscrição>` quando não há logradouro. O campo não
  > é redigido nem varrido pelo gate.
- Emenda [[ADR-337]]: criar o critério 4 — gate de PII sobre o view-model.
- Alinhar o tipo ao contrato E5 (consequência da [[A40.l5]]).
- Valor ausente ⇒ `—`, e **não** calcular derivados sobre base ausente.
- Tabela → cards abaixo de `md` (descrição longa quebra a tabela em mobile).
  > **Não entregue — ver §Ataque A9.** Os dois cards trocam em `sm`, não `md`; e
  > a string longa migrou para `endereco_canonical`, que é a coluna da tabela.

## Critério de aceite

> **Satisfazível com a PII na tela — ver §Ataque §Consequência.** Os três
> critérios abaixo estão escritos contra o campo `descricao` e a grafia crua; a
> PII exibida hoje está em `endereco_canonical`, na grafia normalizada. O
> predicado precisa mudar de campo, não só de superfície.

- KR-D: gate bloqueia fixture sintética com identificador de terceiro + matrícula +
  endereço no campo de descrição, citando o dot-path ofensor.
- **Teste do gate:** removê-lo faz a fixture passar — senão o teste não testa o gate.
- Três casos no teste do card: valor `null` ⇒ `—` e **sem** derivado; `0` ⇒ decisão
  explícita enquanto a origem não for saneada; valor real ⇒ renderiza.
- **Verificação renderizada** — spec com fixture contendo identificadores
  **sintéticos** (PII-zero: documento fictício, matrícula e endereço inventados) no
  campo de descrição. Assere que não aparecem em `page.inner_text('body')` **nem** no
  PDF (padrão de `print.@critical.spec.ts` + `pdftotext -layout`). As duas superfícies
  divergem: o print CSS não força `details[open]`, então o bloco colapsado pode não
  sair no PDF **e ainda assim** estar no DOM servido — testar as duas.

## Itens adotados (2026-08-05)

### `s1` publica "residência própria de R$ 0,00" (movido da [[A40.l5]])

Mesma classe do RV3-27 (zero-como-valor) que esta lane já é dona; a l5 registrou o
item em §Escopo herdado e devolveu a decisão ao dono, que o moveu para cá em
2026-08-05 (ver [[ADR-356]] §Emenda 2026-08-05).

- **Arquivo é `pipeline/`, não frontend:** o f-string do `s1` em
  `pipeline/domain/services/narrativas/summaries_narrator.py` (a parcela
  `residência própria de {…}`). A regra já está decidida — [[ADR-356]] §D7 ("ou o
  número vem do payload, ou não é afirmado") — e a implementação-precedente é
  `_S4_VALOR_TEMPLATES` + `_s4_portfolio_head`, no mesmo módulo: parcela
  condicional a `> 0`. **Não** é redecisão de produto; é aplicar a regra à parcela
  que ficou fora da lista fechada da l4.
- **Independe do `depends_on: [[A40.l5]]`** desta lane: o item não passa pelo
  codegen nem pelo gate de contrato. Pode ir em PR próprio, antes da l5.
- **Coordenar com a [[A40.l15]]**, que também edita esse módulo (decisão do `s3`).
  Hunks disjuntos (`s1` vs `_summary_s3`); quem chegar depois rebaseia.
- Aceite: fixture com `residencia = 0` ⇒ a parcela **não é afirmada** (nem
  "R$ 0,00", nem `—` dentro da frase); com valor real ⇒ afirmada. Prova por
  mutação: restaurar o f-string incondicional deixa o teste vermelho.

### ~~`perfil_familia.right` publica `n_imoveis`~~ — QUITADO POR REMOÇÃO (2026-08-11)

> **Fechado sem a unificação que este item especificava.** A [[A40.l43]] removeu a
> chave `perfil_familia.right` inteira (emenda [[ADR-356]], commit na branch
> `a40-l43-perfil-familia-prosa`): o card de perfil deixou de publicar contagem de
> imóveis — e qualquer outro número. O lado do perfil desta contradição cross-seção
> **não existe mais**, então o aceite abaixo ficou **insatisfazível como escrito**
> (não há `perfil_familia.right` para suprimir em paralelo com a S4).
>
> **O que sobra para esta lane:** só o lado da S4 — a tabela suprimir ou afirmar a
> contagem conforme a fonte, decisão que já era desta lane. Não há mais "fonte
> única" a estabelecer entre duas superfícies; há uma superfície.
>
> Registro aqui em vez de deleção porque o item veio da [[A40.l4]] §Residual e um
> ponteiro que desaparece sem explicação vira drift na lane que o originou.

Follow-up órfão da [[A40.l4]] §Residual: `perfil_familia.right` publica
`{n_imoveis} imóvel/imóveis` de forma independente do card S4 — a mesma contagem
que a l4 deixou de afirmar na tabela da S4 por já estar sob suspeita (fonte que não
é a da seção). Contradição **cross-seção**, não intra-seção, e pré-existente à l4.

- ~~Fonte única: `perfil_familia.right` passa a ler a mesma contagem canônica que a
  tabela da S4 usa~~ — sem objeto: a chave foi removida.
- ~~Critério de aceite: fixture com a S4 suprimindo a contagem (fonte suspeita) ⇒
  `perfil_familia.right` também suprime~~ — insatisfazível; ver blockquote.
- **Aceite vigente:** a tabela da S4 suprime a contagem quando a fonte é suspeita,
  em vez de afirmar número órfão. Prova por mutação: restaurar o f-string
  incondicional deixa o teste vermelho.

## Nota datada — 2026-08-24: o que o #1569 fechou e o que sobra

O #1569 (`dfd561b9`) mergeou e a branch foi apagada, então `lane_pickup` responde
`LIVRE`. **Isso não quer dizer que a lane está abandonada nem que está pronta** — a
ferramenta mede ocupação, não progresso. O status segue `in_progress` com razão.

**Entregue e verificado:**

- `RealEstateYieldCard.tsx:205` renderiza `imovelDisplayLabel(im)`; a `descricao`
  crua saiu do card. Fecha a instância nomeada pelo **RV7-05** do §r7.
- `redact_cartorial` wired em `real_estate_metrics_payload.py` e
  `endividamento_analyzer.py`.
- [[ADR-337]] emendada (+29 linhas).
- Testes de componente (`RealEstateYieldCard.test.tsx`, `imovelDisplay.test.ts`).

**Aberto — são os dois termos da KR-D, e nenhum é cosmético** (o §Ataque
2026-08-24 confirma os dois e acrescenta que fechá-los não fecha a KR-D — A1):

1. **O gate não tem chamador.** `scan_view_model_pii`
   (`pipeline/observability/view_model_pii.py:61`) é chamado **só** pelo próprio
   unit test. Zero ocorrências em `.github/`, `.pre-commit-config.yaml`, `dev/` ou
   em qualquer stage (medido 2026-08-24). O §Critério de aceite pede *"gate bloqueia
   fixture sintética… citando o dot-path ofensor"* e a KR-D pede *"bloqueio no CI"*;
   scanner sem chamador não bloqueia. Mesma família de "faceta inerte" que esta
   sprint já catalogou.
2. **Não existe a verificação renderizada.** O §Critério de aceite pede spec
   assertando ausência em `page.inner_text('body')` **e** no PDF, justamente porque
   as duas superfícies divergem (o print CSS não força `details[open]`). Não há spec
   em `frontend/tests/e2e/` citando `cartorial`/`matrícula`. A infra existe e está
   pronta para usar: `frontend/tests/e2e/helpers/report-pdf.ts` (`pdfToText`,
   `pdftotextInstalado`).

O §r7 registra isso do lado de fora como resíduo do RV7-05 — *"gate sobre payload
real"*, *"baseline visual usa fixture sintética e não alcança"*. É o mesmo item,
visto de duas atas. Roteamento em [`_README`](../_README.md) §Inventário dos achados
do r7 sem hospedeiro.

## Ataque — 2026-08-24

Medido sobre `origin/main` (`1318ad18`) com PII **sintética** — os placeholders
canônicos da [[ADR-319]] (`999.999`, `Rua Exemplo, 100`, `00000-000`,
`123.456.789-09`). Zero DB, zero workspace real.

**O que a §Nota datada acerta, reproduzido:** `scan_view_model_pii` tem **zero**
chamadores fora do próprio teste (`.pre-commit-config.yaml`, `.github/`, `dev/`,
`scripts/`, `backend/`, `pipeline/stages/` — nenhuma ocorrência); não há spec em
`frontend/tests/e2e/` assertando ausência de PII. `redact_cartorial` está wired
nos dois produtores e `RealEstateYieldCard.tsx:205` renderiza
`imovelDisplayLabel(im)`.

**O que a medição acrescenta: os dois itens abertos não são os únicos, e o gate
não fecharia a KR-D mesmo com chamador.** O #1569 não removeu a PII da tela — ele
a **trocou de campo**, e o campo novo é o que nem o redator nem o gate tocam.

### A1 — a PII migrou para `endereco_canonical`, que não é redigido nem varrido

`endereco_canonical` não é rótulo curado: é
`canonicalize(descricao)` (`property_identity_enricher.py:50`) — uma **cascata**
(`endereco_canonicalizer.py:174-179`) que, quando a descrição não tem
logradouro+número, cai em `mat:<matrícula>`, `qa:<código>` ou
`iptu:<inscrição>`. Medido:

| descrição sintética | `endereco_canonical` resultante | `cartorial_pii_tipos` do canonical |
| --- | --- | --- |
| com logradouro | `exemplo 100` | `()` |
| só matrícula | `mat:999999` | `()` |
| só inscrição municipal | `iptu:9999999999` | `()` |
| abreviado (`R.`/`MATR.`) | `exemplo 100` | `()` |

O valor viaja intacto até a tela: `real_estate_adapter.py:200` →
`real_estate_metrics_payload.py` (que redige **só** `descricao`, l.39 e l.77) →
`imovelDisplay.ts:11` → `RealEstateYieldCard.tsx:205`. E
`DESCRIPTION_KEYS = {"descricao","detalhe"}` (`view_model_pii.py:14`) **não
inclui** `endereco_canonical`. A mesma string, medida nas duas chaves:

```
scan_view_model_pii(...imoveis[0].descricao)           -> 4 hit(s)
scan_view_model_pii(...imoveis[0].endereco_canonical)  -> 0 hit(s)
```

⇒ A **matrícula** — um dos três itens que a KR-D manda bloquear — sai de um campo
redigido e vira o **rótulo do imóvel**, num campo que o gate não olha. Wire o
gate hoje e a KR-D fecha verde com `mat:999999` na tela.

### A2 — a emenda da [[ADR-337]] autoriza o que a decisão 2 do corpo proíbe

Corpo, decisão 2: *"**Nenhum** CPF/CNPJ/matrícula/IPTU/endereço de terceiro chega
ao payload E5"*. Emenda 2026-08-19, item 2: *"A UI lê o rótulo curto
(`endereco_canonical` ou classe)"*. Medido acima, `endereco_canonical` **é**
matrícula ou inscrição municipal em dois dos quatro níveis da cascata — e
`imoveis[].imobiliaria_cnpj` chega ao payload cru (o próprio
`cartorial_pii_tipos` o classifica `IDENTIFICADOR` quando apontado nele). A
emenda não emendou a decisão 2; ela abriu uma exceção sem dizer que abriu.

### A3 — os dois testes do #1569 afirmam o oposto sobre a mesma string

| arquivo:linha | asserção |
| --- | --- |
| `tests/unit/pipeline/test_view_model_pii.py:45` | `assert "Rua Exemplo" not in redacted` |
| `frontend/tests/components/imovelDisplay.test.ts:9` | `.toBe("Rua Exemplo, 100")` |

Mesmo PR. O lado Python trata `Rua Exemplo, 100` como PII que **precisa sumir**;
o lado TypeScript trata a mesma string como o rótulo que **precisa aparecer**.
Os dois verdes.

### A4 — a asserção de PII do card fica verde com o logradouro na tela (mutação)

`RealEstateYieldCard.test.tsx:215-244` sobrescreve
`endereco_canonical: "Imóvel locado"` nos dois imóveis. Produção **nunca** emite
esse valor: `CLASS_LABEL` só entra quando o canonical é vazio
(`imovelDisplay.ts:11-13`). Mutação plausível — trocar pelo valor que
`canonicalize()` emite para **aquela mesma descrição cartorial** (`exemplo 100`):

```
✓ expect(body.textContent).not.toContain("matrícula 999.999")   // verde
✓ expect(body.textContent).not.toContain("Rua Exemplo, 100")    // verde
✓ expect(body.textContent).toContain("exemplo 100")             // verde
```

Verde com logradouro **e** número no `body`. A causa não é o override: é que a
asserção compara a grafia **crua** e o card renderiza a grafia **normalizada**
que a cascata produz. Substring sobre a forma errada não vê a forma exibida.
O instrumento é cego ao efeito **por construção**, não por descuido.

### A5 — as fixtures e2e do próprio repo já carregam endereço + CEP no campo renderizado

`frontend/tests/e2e/fixtures/reports/degraded.json` e `long-strings.json` trazem
em `imoveis[0].endereco_canonical` um logradouro completo com número, bairro,
cidade e CEP. Varredura sobre as 6 fixtures de relatório:

| keys varridas | hits |
| --- | --- |
| `{descricao, detalhe}` (gate de hoje) | **0** |
| `+ endereco_canonical` | **4** (`ENDERECO`+`CEP` × 2 fixtures) |

O caso que a KR-D quer bloquear já está commitado no repo, e o gate — se
chamado — diz que está limpo.

### A6 — `redact_cartorial` fecha grafia, não classe

Dois dos quatro tipos atravessam, e `cartorial_pii_tipos` devolve `()` (limpo)
nos dois:

- `INSCRICAO MUNICIPAL (IPTU): 999.999.9999` — intacto. `_CONTRATO` exige o
  número **colado** ao rótulo; o `(IPTU): ` no meio quebra o match.
- `R. Exemplo, 100` / `MATR. 999999` / CPF sem máscara `12345678909` — intactos.
  `_ENDERECO` abrevia só `Av.`; `_CONTRATO` exige a palavra inteira;
  `contains_identifier` (`pii_patterns.py`) casa só CPF/CNPJ **mascarados**.

A fixture `_CARTORIAL` está grafada exatamente como cada regex espera. O verde
mede a grafia da fixture, não a classe: gate por regex fecha sintaxe, não classe.

### A7 — a prova de mutação do gate não muta o gate

`test_remover_as_keys_faz_a_fixture_passar` passa `keys=frozenset()`: muta o
**argumento do chamador**, não o gate. Nenhuma regex é exercitada por essa
prova. E como o gate não tem chamador em produção, "removê-lo" (o que o §Critério
pede) não muda **nada** observável exceto o próprio teste dele — o gate é hoje o
seu único consumidor.

### A8 — a verificação renderizada está especificada contra o DOM pré-#1569

O §Critério manda testar as duas superfícies porque *"o print CSS não força
`details[open]`"*. Medido: o `<details>` do card (`RealEstateExcluded`,
`RealEstateYieldCard.tsx:339-350`) hoje renderiza `{e.classification} —
{e.motivo}` — **sem `descricao`**. A PII que está na tela
(`endereco_canonical`) está na tabela/card sempre visível, que sai nas **duas**
superfícies. Escrever a spec exatamente como está posta testaria um bloco
colapsado que não carrega mais PII e não veria o rótulo que carrega. (Precedente
de `[open]` forçado no print existe e é escopado por classe:
`SParecer.print.css`.)

### A9 — §Escopo item 5 não foi entregue, e a razão dele mudou de campo

"Tabela → cards abaixo de `md`". Medido: os dois cards trocam em **`sm`** —
`RealEstateYieldCard.tsx:166,171` e `EndividamentoCard.tsx:61,74`, ambos de
#1569. Entre 640 e 768px a tabela renderiza. O item foi escrito porque
"descrição longa quebra a tabela"; a descrição saiu, mas as fixtures do A5
mostram que a **string longa foi junto com a PII** para `endereco_canonical`, que
é exatamente a coluna da tabela. O item segue aberto e ninguém registrou a
mudança.

### A10 — RV3-27: o aviso da própria lane se realizou

O §Problema avisa que fechar só a exibição "converteria a linha fantasma em `—` e
deixaria o override preso vivo — a lane ficaria verde sobre o defeito". Medido:
`valorApurado` (0 ⇒ `—`) shipou em #1569 e a [[ADR-385]] segue **`Proposto`**
(`date: 2026-08-11`). A perna de exibição fechou; a perna de origem não. O
blockquote não é premonição — é o estado de hoje.

### A11 — camada 2: o registro de review contradiz a medição nos dois sentidos

`docs/_MOC/REPORT-REVIEWS-active.md`:

- **RV3-06** (l.121) segue `procede-aberto` com a justificativa *"critério 4 da
  ADR-337 inexistente"*. O critério **existe** (`amended_at: ["2026-08-19"]`) e a
  instância nomeada (`RealEstateYieldCard.tsx:194,303,373`) não existe mais.
  Fechar a linha também seria errado: o residual medido (A1–A2) não é o que a
  linha descreve.
- **RV3-27** (l.142) segue `procede-aberto` com dono *"data-engineer (origem do
  zero) + product-designer"*. A perna do `product-designer` shipou; a do
  `data-engineer` é o A10, e é a que continua viva.

### Consequência para o §Critério de aceite

Os três critérios são satisfazíveis com a PII na tela:

1. *"gate bloqueia fixture sintética com identificador + matrícula + endereço **no
   campo de descrição**"* — a descrição já sai redigida; a matrícula que sobra
   está em `endereco_canonical`, fora do escopo da frase.
2. *"removê-lo faz a fixture passar"* — A7: sem chamador, remover não muda nada.
3. *"assere que não aparecem em `page.inner_text('body')` nem no PDF"* — A4: a
   asserção por substring da grafia crua é verde com a grafia normalizada na
   tela.

O critério precisa mudar de **campo** (não só de superfície): o predicado é
"nenhum campo de texto do view-model que a UI renderiza carrega PII cartorial",
com `endereco_canonical` e `imobiliaria_cnpj` dentro, e a fixture derivada do
**produtor** (`canonicalize()`), não escrita à mão.

### Encaminhamento

Tudo acima é **desta lane** — ela é dona do critério 4 da [[ADR-337]] e segue
`in_progress`. Não roteio nada para fora. Duas amarras vivas a respeitar:

- A [[A40.l72]] (`open`) declara "Gate de PII do view-model (7f, RV6-17) →
  [[A40.l6]]" — o alcance do gate decidido aqui é pré-condição dela.
- A perna `data-engineer` do RV3-27 (A10) depende da [[ADR-385]] sair de
  `Proposto`. Fechar a lane pelo lado da exibição sem dizer isso é o cenário que
  o próprio §Problema descreve.

### Como reproduzir

1. `PYTHONPATH=. python3 _scratch/ataque_l6_medicao.py` — cascata, redação e
   varredura (script efêmero; o corpo está nas tabelas acima).
2. A4: em `RealEstateYieldCard.test.tsx:222,228`, trocar
   `endereco_canonical: "Imóvel locado"` por `"exemplo 100"` e ajustar a última
   asserção para `getAllByText("exemplo 100")` — 15/15 verdes.
3. `rg -c scan_view_model_pii .pre-commit-config.yaml .github/ dev/ scripts/ backend/` — zero.
