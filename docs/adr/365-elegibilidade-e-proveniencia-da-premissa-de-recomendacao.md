---
id: ADR-365
type: adr
title: "Recomendação retida do ranking é declarada; proveniência da premissa e elegibilidade são eixos ortogonais"
status: Proposto
date: "2026-08-06"
relates_to: ["[[ADR-167]]", "[[ADR-240]]", "[[ADR-272]]"]
tags:
  - type/adr
  - status/proposto
  - area/report
  - phase/a40
---

# ADR-365 — Elegibilidade e proveniência da premissa de uma recomendação

## Contexto

O relatório recomenda ações no plano (`pontos_urgentes`) sem distinguir a
recomendação que o payload **sustenta** da que ele **não sustenta**. Duas
medições da [[A40.l10]], em 2026-08-06:

1. **`pontos_urgentes` não consulta o gap de proteção.** `_seguro_vida_item`
   decide só por "existe apólice vigente com `tipos_bem` contendo `pessoa`" —
   não lê `gap_qualitativo`, não lê dependentes, não lê passivo. Resultado:
   *"Contratar seguro de vida e invalidez / Alta / Imediato"* é emitido para
   **todo** workspace sem apólice de pessoa, inclusive titular solteiro sem
   dependente econômico. Seguro de vida protege dependente econômico; sem
   dependente é custo puro. É conselho errado, não default conservador.
2. **Um gatilho do gap é tautológico.** `_detecta_risco_vida` dispara
   `conjuge_sem_renda_propria` a partir de `renda_propria_brl`, que
   `protecao_wiring` fixa em `Decimal("0")` por não haver fonte estruturada de
   renda por membro ([[ADR-240]] §D3). Todo workspace com cônjuge satisfaz o
   predicado, sempre.

A A40 mede "honestidade da recomendação" (KR-E): *nenhuma recomendação no topo do
plano cuja premissa o próprio payload contesta, sem pendência pareada*. Sem um
eixo declarado, as três situações — premissa sustentada, premissa que o produto
não consegue avaliar, e predicado que não discrimina — são indistinguíveis no
artefato entregue.

**Retenção silenciosa não é saída.** A 6ª classe do §Critério de done do
[[PLAN-report-trust]] proíbe retenção de conselho sem declaração **por classe de
motivo** no artefato entregue.

## Decisão

### D1 — Dois eixos ortogonais, não um

O item de recomendação carrega **dois** campos independentes:

- `origem_premissa` ∈ `{cadastro_familia, documento_ingerido, derivado_e5}` — de
  onde vem o fato que sustenta a recomendação.
- `elegibilidade` ∈ `{computavel, nao_verificavel, degenerada, pendente_de_dado}` —
  se o produto consegue avaliar a premissa.

**Um eixo só embutiria um ranking de confiança invertido.** Graduar por
"observável dentro do E5" diria ao leitor que o mais frágil é o mais sólido: um
fato de `cadastro_familia` é declaração de primeira mão do dono, enquanto
`passivo_acima_30_pct_patrimonio` deriva de baseline IRPF defasado 1-2 anos
([[ADR-305]]). Proveniência e verificabilidade são perguntas diferentes.

**Contraexemplo que prova a ortogonalidade:** `dependentes_menores_18` é
`(cadastro_familia, computavel)` e `conjuge_sem_renda_propria` é
`(cadastro_familia, degenerada)` — mesma proveniência, elegibilidade oposta. Um
eixo único não representaria o par.

### D2 — `Literal`, não `Enum`

Os dois vocabulários são `Literal[...]` no módulo do analyzer, espelhados como
`enum` **inline** em `config/schemas/e5_analysis.schema.json` §`pontos_urgentes.items`.

Precedente exato: `PctRendaSinal`/`GapAutoSinal`, `Literal` em dataclass frozen no
mesmo domínio de proteção. `ReviewReasonCode` ([[ADR-272]]) é `str, Enum` por ter
três produtores, comportamento anexado (`BLOCKING_CODES`) e schema próprio
versionado — nenhum dos três se aplica aqui.

**Condição de promoção a `str, Enum`, escrita para não virar juízo:** quando um
segundo produtor emitir os campos, **ou** quando comportamento passar a ser
anexado ao valor (mapa de bloqueio, precedência).

### D3 — `code` estável é identidade, não enfeite

Cada item ganha `code` estável por regra (`reserva_insuficiente`,
`endividamento_alto`, `seguro_vida`, `rentabilidade_nao_medida`).

Sem ele a ordenação é **insegura**: `build_default_tarefas` numera `n = i + 1`
sobre `pontos_urgentes` e `build_default_tarefas_status` chaveia por essa
posição — reordenar remapearia o status registrado pelo dono para outra tarefa.
É a mesma classe do RV4-02 que a [[A40.l10]] PR1 fechou. E `dev/golden_diff.py`
cai em diff posicional sem chave natural na lista.

`code` é **pré-condição** da ordenação por tier (ADR de ordenação, a abrir no PR
seguinte), não parte dela.

### D4 — Retido é declarado, não omitido — e é projeção de uma lista única

`analyze()` devolve **uma** lista com todos os itens avaliados. A serialização
E5 **particiona**:

- `pontos_urgentes` — ranqueado, só `elegibilidade == computavel`.
- `pontos_urgentes_retidos` — os demais, cada um com `code`, `origem_premissa`,
  `elegibilidade` e `dado_faltante`.

Os dois arrays são **projeções da mesma lista**, não stores. Colapsá-los no
futuro é deletar um ramo do serializer, não migrar dado.

**Não há conflito com a [[ADR-167]].** Ela governa elegibilidade de **bloco
irrelevante** ("este cenário não existe para esta família" — não há conselho a
declarar). Aqui o conselho existe e a **premissa** é que não se sustenta.
Sobrevive dela a metade arquitetural, que é a que importa: **uma** camada
decide, o TS não duplica lógica de elegibilidade.

**Ausência de gatilho não é retenção.** Quando o predicado de domínio não
dispara (titular sem dependente econômico), o item **não é produzido** — não há
conselho a retirar do ranking nem a declarar. Isso é [[ADR-167]], não a 6ª classe.

### D5 — O vocabulário nunca chega à tela

`computavel`, `nao_verificavel`, `degenerada`, `pendente_de_dado`,
`cadastro_familia`, `documento_ingerido`, `derivado_e5` são jargão de
implementação e **não aparecem em string renderizada**. A copy nomeia
`dado_faltante` ou a razão de a regra não discriminar.

O leitor que legitima o array de retidos nesta ADR é a **sentença por classe de
motivo na narrativa `summaries.s10`**, que já renderiza na S10 e sai no PDF —
não um componente novo. Componente com CTA é superfície da [[A40.l22]]; leitor
sem copy decidida seria meia-superfície.

### D6 — `degenerada` é valor transitório

`degenerada` marca predicado que não discrimina por defeito de produtor, não uma
categoria permanente de domínio. **Condição de deleção:** quando
`renda_propria_brl` tiver produtor real, `conjuge_sem_renda_propria` deixa de ser
`degenerada` e o predicado passa a ser dependência econômica
(`renda_conjuge < k × custo_essencial_familiar`), não `renda == 0`. Se nenhum
valor `degenerada` sobrar, o membro sai do `Literal`.

O gatilho **permanece** em `protecao_analyzer` — marcá-lo na camada de conselho é
contido; removê-lo mudaria o payload `protecao_patrimonial` para os outros
consumidores.

## Alternativas consideradas

1. **Um enum único de elegibilidade** — rejeitada em D1 (ranking de confiança
   invertido; não representa o par mesma-proveniência/elegibilidade-oposta).
2. **Omitir o item não-computável** (molde [[ADR-167]] literal) — rejeitada:
   viola a 6ª classe do gate de saída, e por construção manteria o gate vermelho.
3. **`str, Enum` + schema standalone** (`advice_eligibility.schema.json`) —
   rejeitada em D2: um produtor, sem comportamento anexado. Schema próprio
   custaria manutenção sem comprar gate.
4. **Transformar `pontos_urgentes` em objeto `{ranqueados, retidos}`** —
   rejeitada: quebra todos os leitores atuais do array (card, dashboard,
   manifest do parecer) por uma economia de uma chave.
5. **Ler `gap_qualitativo` e manter o predicado próprio como fallback** —
   rejeitada: manteria dois produtores do mesmo predicado, que é o defeito.

## Consequências

- **Um workspace deixa de receber uma recomendação que recebia.** Titular sem
  dependente econômico e sem apólice de pessoa não vê mais "Contratar seguro de
  vida". É correção de conselho, e o delta é de **população**, não de valor — os
  gates mecânicos de golden são cegos a isso, então o PR declara a medição por
  perfil no corpus dogfood.
- **Um workspace passa a receber uma recomendação que não recebia.** O predicado
  canônico do gap ([[ADR-240]] KPI F) exige cobertura de **vida**; o predicado
  antigo aceitava qualquer bem `pessoa`. Apólice de acidentes sem vida deixa de
  suprimir o item. É verdadeiro-positivo antes suprimido.
- **O schema passa a ser gate deste bloco.** `pontos_urgentes.items` é declarado
  com `additionalProperties: false`, e `tests/test_e5_golden_execution.py` valida
  um E5 **gerado de verdade**, hard, fora do modo `warn` de `config/pipeline.json`.
  Campo novo no item passa a exigir schema no mesmo PR.
- **`prazo` é declarado, não removido.** Tem dois leitores vivos —
  `dashboard_service` (serve `GET /dashboard`) e o manifest do parecer, que
  injeta `$.pontos_urgentes` raw. O `description` do bloco nomeia os dois, para
  a [[A40.l5]] não mirar o campo errado no cleanup.
- **`pontos_urgentes_retidos` fica fora do whitelist do parecer.** Injetar item
  degenerado no contexto do LLM amplificaria exatamente o que a taxonomia existe
  para conter.
- **Os campos novos não se propagam para `tarefas`.** `build_default_tarefas`
  segue projetando só os ranqueados. `tarefas` não é conceito, é alias com perda;
  estendê-la tornaria a duplicação permanente.

## Estado-alvo (declarado para não virar meia-migração)

O produto tem hoje **cinco** representações de "o que a família deve fazer":
`pontos_urgentes`, `tarefas`/`tarefas_status`, `Suggestion`, `Decision` e a
tabela do apêndice `plano_de_acao`. O painel de 2026-08-06 **divergiu** sobre o
alvo — `Suggestion` como conceito único de recomendação autorada por motor
(já tem `code`/`severity`/`kind`/`dedup_key` e ponte para `Decision`) versus
manter diagnóstico do motor e compromisso do dono como agregados separados. A
divergência fica registrada; não há decisão aqui.

O que **é** consenso e esta ADR fixa: `tarefas` é alias com perda e não recebe
campo novo; e o passo desta lane é **o campo, não o store** — os dois eixos
nascem nomeados no nível de **recomendação**, para que adoção futura por outro
produtor seja rename, não retradução. Sem esta seção, o próximo agente
reinventa `elegibilidade` dentro de `suggestion_rules` e o produto passa de cinco
representações para seis.

**Condição que abre o trabalho de convergência:** quando um segundo produtor
precisar dos dois eixos, ou quando o parecer passar a receber o plano que o dono
cura em vez da reprojeção derivada.

## Regra de domínio

[[RULE-elegibilidade-da-recomendacao]] — enforcers e tabela de mapeamento.
