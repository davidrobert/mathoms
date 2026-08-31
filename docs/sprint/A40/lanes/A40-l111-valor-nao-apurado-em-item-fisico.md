---
id: A40.l111
type: lane
title: "Imóvel com valor negativo entra na soma do patrimônio: o valor impossível vira `null` declarado, não zero nem passivo"
sprint: A40
status: in_progress
priority: P1
branch_slug: a40-l111-valor-nao-apurado-em-item-fisico
owner: financial-planner
depends_on: []
adrs: ["[[ADR-431]]", "[[ADR-394]]", "[[ADR-346]]", "[[ADR-427]]"]
tags: [type/lane, sprint/a40, status/in-progress, priority/p1, area/dados, area/produto]
---

# A40.l111 — `valor-nao-apurado-em-item-fisico`

> **Origem:** tratamento dos achados da [[A42.l19]]. Co-design `financial-planner`,
> 2026-08-31, com regra de domínio confirmada contra fonte externa (RFB).

## O fato

Um item de `imoveis_consolidados` tem **valor negativo** (ano 2025, 3 artefatos de 71).
Estrutura: `tipo: imovel`, `codigo_rfb: "11"` (apartamento), `instituicao` presente,
`low_confidence: true`, `review_reasons: []`.

## Por que ninguém pegou, medido

- A guarda de sinal do E5 ([[ADR-394]] §Emenda D6) opera no **balde agregado**. O
  agregado é **positivo** (o item negativo é ~14% do total em magnitude), logo ela
  **nunca dispara**. É estruturalmente cega a defeito de sinal no item.
- O schema tem `minimum: 0` e **pega** — mas roda em `warn`: loga e grava.
- O classificador silenciava o par `secao` + negativo. **Já consertado** pela emenda
  2026-08-31 da [[ADR-394]] — é o que tornou este achado visível.

## A regra de domínio que decide (RFB)

Apartamento financiado é declarado **em Bens e Direitos, pelo valor pago** — nunca a
mercado — e o **saldo devedor NÃO vai em Dívidas e Ônus Reais** (fazê-lo é rota de
malha fina). Os dados da instituição vão na *discriminação* da linha do bem.

Três consequências que invertem a leitura intuitiva:

1. **`instituicao` presente não é evidência de dívida** — é o campo que a Receita
   manda preencher na linha do **ativo** financiado.
2. **Não existe contraparte** a "devolver ao lugar certo".
3. **O contribuinte não consegue digitar negativo** em Bens e Direitos: o PGD não
   aceita. O sinal **não veio da declaração** — é nosso. Origem provável: o extrator
   leu o saldo devedor do texto da discriminação em vez da coluna "situação em 31/12".

Logo: defeito de **medição do valor**, com o **eixo correto**.

## A decisão

O **item** fica no inventário (o apartamento existe; apagá-lo esconde um bem da
família). O **valor** vira `null`, sai da soma, e carrega `review_reason`.

Não contraria o D6 — estende-o um grão abaixo, onde `null` é representável e o
`Decimal` pós-soma não é. Doutrina já vigente: [[ADR-394]] §Emenda (b) D7 (*"`null` e
não `0,0`: um zero publicado é uma afirmação sobre o patrimônio da pessoa"*) e
[[ADR-346]].

| saída | erro no patrimônio líquido |
|---|---|
| publicar o negativo (hoje) | `real + X` — erro **duplo**, e o único não declarado |
| mover para dívidas | `real + 2X` — pior, e fabrica passivo que a RFB proíbe declarar |
| **`null` + fora da soma** | `real` — erro **de um lado só, e declarado** |

## Critério de aceite

- [ ] Nenhum item de `imoveis_consolidados`/`veiculos_consolidados` publica
      `valores_31_12[<ano>] < 0`; valor impossível vira `null` + `review_reason`
      nomeando ano e item.
- [ ] **Não-inércia:** o teste que falha é `secao == "bens_direitos"` **com** negativo.
      Fixture que só exercite o ramo do sinal já passa e não prova nada.
- [ ] Σ publicada exclui o item nulo; `composicao ≡ bruto` e `patrimonio_liquido`
      seguem consistentes.
- [ ] Prescrições que dependem de cat_2 saem **suprimidas** com `motivo_supressao`
      declarado (desvio vs. alocação alvo, próximo aporte, concentração imobiliária,
      cap rate do imóvel); descritivos publicam inteiros — a [[ADR-394]] §Emenda já
      decidiu que suprimir a descrição esconde o defeito onde o leitor confere.
- [ ] **Contra-prova de reversibilidade:** run com o item corrigido volta a publicar a
      prescrição e a ressalva some. Sem isso a supressão vira permanente.
- [ ] `S4`: imóvel com valor não apurado não entra em `cap_rate_*` nem na média
      ponderada da carteira (denominador/peso negativos).
- [ ] Invariante no corpus: **todo** item com `low_confidence: true` tem ≥1
      `review_reason`. Era 8/26 violando; a paridade dos call-sites mudos já entrou.

## A ressalva, em português de família

A atual (`BaldeNegativoSobrevivente.format()`) nomeia identificador interno, recita
doutrina de engenharia e **não diz a direção do erro**. É razão de operador; mantenha
nessa função. A ressalva de família precisa dizer **o quê**, **para que lado** e **o
que fazer** — sem o "para que lado", o leitor assume que o número publicado é o teto:

> **Um imóvel ficou de fora desta conta.** Não conseguimos ler o valor de um
> apartamento na sua declaração de 2025 — o número que extraímos era negativo, e
> imóvel não vale menos que zero. Ele **não** está somado abaixo: **seu patrimônio
> real é maior do que o que aparece aqui**, pelo valor desse apartamento. Confira o
> campo "situação em 31/12" desse bem na declaração e informe o valor para recompor a
> conta. Enquanto isso, as recomendações de aporte e de alocação-alvo ficam suspensas,
> porque dependem desse número.

## O que NÃO fazer

- **Não mover para dívidas** — fabrica passivo que a RFB proíbe declarar; dobra o erro.
- **Não aplicar `abs()`** — se o número veio do saldo devedor, publica a **dívida como
  se fosse o valor do bem**: plausível, auditável só contra a declaração, e o pior
  desfecho possível.
- **Não zerar em silêncio** — zero é afirmação ([[ADR-346]], [[ADR-394]] D7).
- **Não bloquear a seção de patrimônio.**
- **Não flipar o schema para `strict` como conserto** — vira abort de run e viola o
  WARN-first do D6. Com o valor virando `null`, o schema aceita `["number","null"]` e
  o **domínio** carrega a decisão.
- **Não descer a guarda de sinal ao grão da linha genericamente** — a §Taxa de disparo
  do D6 já mediu o modo de falha (6/6 runs por centavos que se anulam dentro do
  caixa). O escopo é **item de ativo físico**, onde negativo é impossível por
  definição.
- **Não culpar o contribuinte na copy** — o PGD não aceita negativo ali; o defeito é
  nosso.
- **Não ler `instituicao` como sinal de dívida** em heurística futura.

## Formalização

Emenda datada à [[ADR-394]] (feita: o sinal veta magnitude, não eixo) **+ ADR nova**
para o contrato de item `valor_nao_apurado` — muda `valores_31_12` para
`["number","null"]` e acrescenta estado de cobertura no item, o que é contrato de
produtor entre E1.5c → E4 → E5.

## Follow-up nomeado

`low_confidence` é nome sobrecarregado: lê-se "extração fraca" e significa "identidade
não canonicalizada" ([[ADR-246]], chave de dedup cross-IRPF). Quem lê o artefato
depois — inclusive o LLM do parecer no E6 — vai errar. Renomear é breaking; janela
própria, dono `data-engineer`.

---

## Entregue (2026-08-31)

Formalizada em [[ADR-431]] (`Decidido`) + emenda datada à [[ADR-394]]
§Emenda 2026-08-31 (b).

**O que a emenda à ADR-394 corrige.** A consequência 3 da §Taxa de disparo lia
"0 disparos" como "0 ocorrências": afirmava que "o item negativo não chega mais a
balde de ativo" porque a [[A40.l66]] fechou a montante. O que a A40.l66 fechou foi
o **roteamento pelo rótulo**; item cujo eixo é decidido por **fato** (`secao:
bens_direitos`) e cujo valor é negativo continua entrando. A guarda de fato não
dispara — pelo motivo da consequência 1 (mede agregado, não linha), não por
ausência do fato. D5 e a tabela do D6 ficam intactos.

### Onde a decisão mora

| ponto | arquivo |
| --- | --- |
| regra + warning tipado + predicados de leitura | `pipeline/domain/services/valor_nao_apurado.py` |
| produtor (item + boundary do stage) | `scripts/consolidate_baseline.py` |
| produtor do caminho legado E4 | `scripts/categorize_transactions.py` |
| contrato do artefato | `config/schemas/baseline_patrimonial.schema.json` |
| leitura + `null` publicado | `pipeline/domain/services/patrimonio_resolvers.py` |
| exclusão explícita da Σ | `pipeline/domain/services/patrimonio_types.py` |
| grão do item na guarda + supressão | `pipeline/domain/services/patrimonio_sign_guard.py` |
| S4 (cap rate, peso, pro-rata) | `real_estate_metrics.py` + `real_estate_adapter.py` |
| ressalva de família | `ReportDataQualityBanner.tsx` + `dataQualitySignals.ts` |
| projeção para o parecer | `config/prompts/parecer_planejador.yaml` (v2.18.0) |

### Contrafactual medido (não é "os testes passam")

Os testes rodados contra o código **pré-mudança**, asserção a asserção, em
worktree destacada no commit `1a7aa0c1`:

- **10 asserções falham** sem o fix — `valores_31_12` negativo, `valor_nao_apurado`
  ausente, `review_reason` ausente, agregado com o negativo, `bruto` 850k em vez de
  1,0M, entry com `0,0` em vez de `null`, `motivo_supressao` nulo,
  `cobertura_completa` verdadeira, `itens_sem_valor` inexistente, supressão que não
  se move entre defeito e correção.
- **6 asserções passam** sem o fix, e é isso que as torna **controle e não gate**:
  o ramo do sinal sem `secao` (imóveis vazio, dívida com 1), a contra-prova com o
  item corrigido, o item que permanece no inventário, e `composicao ≡ bruto`.

Sem essa separação, uma fixture escrita só com o negativo — sem `secao` — passaria
igual antes e depois: o classificador a rotearia para o passivo pelo sinal, e o
defeito nunca se reproduziria. `test_o_ramo_do_sinal_nao_reproduz_o_defeito` fixa
esse controle no arquivo.

### Limites declarados

- **A origem do sinal não foi consertada.** A hipótese é que o extrator leu o saldo
  devedor da discriminação em vez da coluna "situação em 31/12"; confirmá-la exige o
  documento. Esta lane decide o que **publicar** enquanto isso.
- **O golden não exercita o caminho.** O rebaseline do snapshot do view-model é uma
  linha aditiva vazia — o corpus sintético não tem item sem valor. Quem cobre o
  caminho é `tests/unit/pipeline/test_valor_nao_apurado_adr431.py`.
- **O corpus sintético do parecer não fornece o campo.** O rebaseline de
  `dev/snapshots/parecer_ancorabilidade.json` põe
  `$.patrimonio.guarda_de_sinal.itens_sem_valor[*]` em
  `paths_projetados_sem_dado_no_corpus` — ao lado dos irmãos `modo`,
  `cobertura_completa` e `motivo_supressao`, que já estavam lá. Nenhuma folha R$
  nova ficou inancorável; o que fica registrado é que **este snapshot verde não é
  evidência sobre produção** para este campo, exatamente como o `_comment` dele já
  declara para os outros 16.
- **O invariante de `low_confidence` cobre os ramos do enricher, não o corpus.** Um
  quarto sítio que marque `low_confidence` fora dele passa despercebido; o que torna
  isso improvável é o produtor único de razão, não o teste.
- **`low_confidence` segue com o nome sobrecarregado** — follow-up nomeado no corpo
  desta lane, dono `data-engineer`, janela própria.
