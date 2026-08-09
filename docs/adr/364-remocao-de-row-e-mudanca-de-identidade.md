---
id: ADR-364
type: adr
title: "Remover row no E3 é mudança de identidade para override — herda a restrição da ADR-354 e a quita por re-ancoragem"
status: Proposto
date: "2026-08-06"
amended_at: ["2026-08-07", "2026-08-09"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - phase/a40
---

# ADR-364 — Remover row no E3 é mudança de identidade para override

> ⚠️ **Emendada em 2026-08-07 e em 2026-08-09.** A emenda de 2026-08-07 corrigiu o
> **mecanismo do gate** (predicado inalcançável por construção; cinco cláusulas, não
> duas) e moveu os itens **3** e **5** da §Estado de implementação de ⬜ para ✅. A de
> **2026-08-09 revoga o mecanismo da §Decisão 2**: a quitação deixa de ser re-ancoragem e
> passa a ser **retenção** — o colapso não remove row cujo `gate_digest` tem override
> ativo. A §Decisão 1 permanece intacta; a re-ancoragem fica **deferida** com gatilho
> verificável. Não construa `ReanchorPlan`/`CollisionPlan` a partir do texto original da
> §Decisão 2 — leia a §Emenda 2026-08-09 primeiro.

## Contexto

A [[ADR-354]] §Não-decisão proíbe `_hash_v3` com um argumento que **não é sobre
hashes**, e sim sobre consequência:

> Mudar os inputs de v2 **órfãna a categorização manual do dono** — regressão
> user-facing **pior** que a duplicação que se está corrigindo, e já vivida neste
> repositório.

A §Emenda da mesma ADR autoriza o colapsador e afirma que a §Não-decisão "segue
integralmente válida", porque o service **seleciona rows** e não toca input de hash.

**Isso é verdade sobre o mecanismo e falso sobre a consequência.** O enforce da
[[A40.l2]] produz **o mesmo resultado proibido** por outro caminho: em vez de mudar o
hash sob a row, remove a row sob o hash. Nos dois casos o `transaction_hash` ao qual um
override está ancorado deixa de resolver.

Uma ADR que proíbe X **porque X órfãna override**, seguida de um PR que órfãna override,
é contradição que leitor futuro não resolve a partir das emendas — e o §Escopo desta lane
já foi ressuscitado errado uma vez a partir de histórico de PR.

## Decisão

**1. Remoção de row no E3 é, para `transaction_overrides`, mudança de identidade.**
Herda integralmente a restrição da [[ADR-354]] §Não-decisão. Não é isenta por não tocar
`_hash_v2`: a restrição é sobre o override deixar de resolver, não sobre a função de
hash.

**2. A restrição é quitada por RE-ANCORAGEM, não por evitação.** O colapsador conhece o
sobrevivente — `_targets` computa `keep_native`/`keep_llm`. O contrato passa a emitir o
par **`(hash removido → hash sobrevivente)`**, e o backend re-ancora com a máquina que já
existe ([[ADR-282]]): `ReanchorPlan`, `CollisionPlan`, revalidação TOCTOU plan→apply, e o
filtro `orphaned_at IS NULL`.

Trade-off aceito: re-ancorar é **mutar dado do usuário por heurística**. Mas é a **mesma
heurística que o colapso já executa** — recusar re-ancorar não é mais seguro, é
silenciosamente pior (o override some da UI sem que ninguém declare por quê).

**3. `RemovalTarget` tem consumidor legítimo ou é deletado.** Hoje é registro de decisão
**sem leitor**, e estrutura órfã apodrece e depois é adotada errada por quem não leu a
lane. É também o falsificador **F1** da retirada de `alvo_enderecavel`: se alguém
resolver `RemovalTarget.hash` contra um conjunto de rows e **agir** por ele, aquela
métrica volta a valer e a retirada vira trave movida retroativamente.

**4. Plano de controle do enforce — duas flags, não uma.**

| flag | default | efeito |
|---|---|---|
| `cross_document_collapse_measure_enabled` | `True` ao shipar | injeta o colapsador em produção, **measure-only**. Zero mudança de output; popula candidatos → gate → `AuditRecord` por run. É a **sombra**, e o código já a tem (o ramo `elif ... measure(reconciled)`) |
| `cross_document_collapse_enforce_enabled` | `False`, **por workspace** | o flip destrutivo |

Por workspace porque o gate é workspace-scoped (`transaction_overrides` é
workspace-scoped); flag global ligaria o enforce onde o gate nunca rodou.

**O write-path de `set_flag` para `enforce=True` recusa sem um `PreconditionReport` com
`liberado=True` daquele workspace, do run corrente, gravado em `AuditRecord`.** Isso
**não** viola a decisão de não ler o gate em runtime: não é o pipeline consultando DB, é
pré-condição sobre a **ação do operador**, no backend, onde acesso a DB é legal. Fecha o
TOCTOU do lado do flip mantendo o boundary ([[ADR-089]]/[[ADR-111]]) intacto.

Ambas as flags entram em `OPERATOR_ONLY` — sem isso a própria família flipa o enforce
pelo endpoint normal, contornando o gate.

**5. O gate roda TODO run, não uma vez antes do flip.** `evaluate()` já é read-only e
recebe os candidatos por parâmetro. "Vazio" é propriedade do corpus **e do tempo**: gate
one-shot pré-flip caduca no dia seguinte. Rodando por run e gravando `AuditRecord`, vira
série temporal — e é o gatilho de rollback (subiu de zero ⇒ operador desliga a flag).

## Não-decisão explícita

**Nenhum rollout percentual.** A população de workspaces é pequena, o dogfood **é** o
canário, e o undo existe (flag off + re-run reconstrói o artefato E3). Percentual
adicionaria complexidade sem habilitar decisão. A sombra do item 4 dá o estágio que
importa; o contador visível na S2 dá o sinal de rollback de produto.

## Estado de implementação

Registro de fato, **não** emenda — nenhuma decisão acima mudou. A ADR segue `Proposto`
porque 4 dos 5 itens não têm código.

| item | estado |
|---|---|
| **1** — remoção herda a restrição | decidido, sem código próprio (é premissa dos outros) |
| **2** — quitação por **retenção** (re-ancoragem deferida, ver §Emenda 2026-08-09) | ⬜ [[A40.l2]] PR3d |
| **3** — `RemovalTarget` com consumidor | ✅ PR3b — o consumidor é a **adjudicação do gate** (`survivor_hash` absolve o override que já ancora a row sobrevivente), não o drain |
| **4** — flag de sombra `measure` | ✅ [#1231](https://github.com/davidrobert/mathoms/pull/1231) (`65464db6`) — em produção, `OPERATOR_ONLY`. A flag de **enforce** e a recusa do write-path são do PR3e |
| **5** — gate todo run | ✅ PR3b — chamada em `main_with_store`, relatório em `pipeline_stage_logs.output_summary`, **não** `AuditRecord` por run (`append_audit` é `db.add` sem commit e o loop do `pipeline_task` faz *rollback* em falha, então a série que este item promove a gatilho de rollback nasceria com os **vermelhos apagados**). O `internal_ops_audit` recebe **uma** row quando o operador flippa a flag |

**Achado que a §Decisão 2 pressupunha e que não era verdade** (medido 2026-08-06, painel de 5
especialistas): o gate de pré-condição, como escrito, **não pode ficar verde**. O `gate_digest`
é `(data, cents, moeda, descricao_norm)` e as duas pernas o compartilham **por construção** —
re-ancorar no sobrevivente não muda nenhum componente, logo o override segue `hit` para sempre,
e a única saída existente é quarentenar, que esta ADR §2 proíbe como forma de quitação. A
decisão de quitar por re-ancoragem **permanece**; o que muda é o mecanismo do gate: descoberta
por **digest**, adjudicação por **hash**. Detalhe e travas na §"O PR3 foi serializado" da
[[A40.l2]].

## Emenda 2026-08-07 — o predicado do gate era inalcançável, e o mecanismo foi corrigido

Entregue no PR3b da lane. **Nenhuma decisão acima foi revogada.**

**1. Descoberta por digest, adjudicação por hash.** O `gate_digest` é
`(data, cents, moeda, descricao_norm)`; as duas pernas o compartilham **por definição de
candidato**, e re-ancorar no sobrevivente não muda nenhum dos quatro componentes ⇒ sob um
predicado que só olhasse o digest, o override seguiria `hit` **para sempre** e a única saída
seria quarentenar — o que a §Decisão 2 proíbe como forma de quitação. A descoberta continua
por digest (as duas razões medidas em 2026-08-05 seguem válidas); a **adjudicação** passa a
usar o `survivor_hash`, que **não** é invariante sob re-ancoragem. É isto que dá consumidor
legítimo ao `RemovalTarget` e satisfaz a §Decisão 3.

**2. O predicado é cumulativo — cinco cláusulas, não duas.** `medido` · `hits == 0` ·
`sem_snapshot == 0` · `tx_data_nao_iso == 0` · vivacidade **universal**
(`snapshot_casa_corpus == com_snapshot`). Cada uma fecha um caminho por que `hits == 0`
seria vácuo, e as três novas correspondem a furos medidos:

| furo | como saía `liberado` |
| --- | --- |
| `evaluate(db, ws, [], frozenset())` | `alvos = ∅ ⇒ hits = 0`. Run com a flag de measure **desligada** autorizava o flip destrutivo. Agora exige `medido` |
| `tx_data` fora do ISO | contava em `com_snapshot`, nunca casava nada, e saía `liberado` — medir sem impedir |
| vivacidade existencial (`> 0`) | um único match certificaria vivacidade para todos os que o join não vê |

**3. Fail-loud onde era fail-open.** `_alvos` usava `getattr(c, "collapsible", False)`:
qualquer rename em `CollapseCandidate` dava `alvos = ∅ ⇒ liberado=True` **em silêncio**.
Vira acesso por atributo, `AttributeError` alto (precedente [[ADR-359]]). E `corpus_digests`
perde o default de `evaluate()` — argumento esquecido certificava vivacidade vazia.

**4. Medição de 2026-08-07, no corpus dogfood, pelo join que o gate usa.** O probe promovido
adjudica por `_hash_v2`; a cláusula de vivacidade adjudica por `gate_digest`. Medidas as
duas, o resultado é o mesmo e **reprova hoje**:

| | |
| --- | --- |
| corpus observado | 5227 digests / 5560 row-hashes, 117 statements, 331 candidatos colapsáveis |
| overrides ativos | 5 — todos com snapshot, nenhum com `tx_data` fora do ISO |
| `snapshot_casa_corpus` | **4 de 5** ⇒ vivacidade universal **reprova**, existencial passaria |
| `hits` | 0 — nenhum override ancora em row que participe de candidato |
| predicado antigo | **`liberado=True`** — isto é, o gate autorizava o flip com 1 de 5 overrides que ele não sabe julgar |

**Esta é a polaridade correta.** O 1 que não casa é exatamente o override sobre o qual o
gate não tem o que dizer. E a escapatória de absolvição é exercitada por **zero** overrides
neste corpus: ela é necessária para o gate ser alcançável em princípio, mas o dogfood **não
a prova** — as travas dela vêm de fixture sintética. "Gate verde no dogfood" não é evidência
de que a absolvição funciona.

**5. O que a emenda NÃO faz.** Não liga o enforce (§Critério de saída do 3e segue com os 9
eixos, incluindo ensaio de rollback medido), não re-ancora nada (PR3d) e não afrouxa
`liberado` — a trave que o texto acima nomeia como incentivo permanece onde estava, mais
apertada.

## Emenda 2026-08-09 — a quitação passa a ser RETENÇÃO; a re-ancoragem fica deferida

Fechada por co-design de 3 rodadas (2 refutadores adversariais + `financial-planner` +
`senior-cto`). **A §Decisão 1 não muda.** O que muda é como ela é quitada.

**1. O mecanismo: não colapsar, em vez de colapsar-e-re-ancorar.** O colapsador recebe
por construtor um `OverrideRetentionGuard` congelado — os `gate_digest` dos overrides
ativos do workspace — e **retém** toda chave cujo digest está nele. Zero leitura do E4,
zero escrita em `transaction_overrides`, zero adjudicação.

A propriedade obtida é **estritamente mais forte** que a da §Decisão 2 original:
*"nenhuma row com override desaparece"* domina *"toda row removida tem seu override
re-ancorado"*, e sai de uma subtração de conjunto em vez de um adjudicador de 6 passos.
O trade-off que a §Decisão 2 aceitava — *"re-ancorar é mutar dado do usuário por
heurística, mas é a mesma heurística que o colapso já executa"* — **está errado nos dois
termos**: não é a mesma heurística (o colapso escolhe qual row descartar; a re-ancoragem
escolhe a qual linha uma correção humana passa a se referir), e o adjudicador tinha
**quatro defeitos medidos** antes de existir (item 4). Erro de retenção é sub-colapso
**nomeado e contado**; erro de re-ancoragem é sobre-colapso **silencioso, irreversível e
auto-atribuído** — o produto passa a exibir o badge `editado` numa linha que a família
nunca tocou, e `_is_sticky` a imuniza contra a categorização automática para sempre.

**2. Custo aceito, dito sem eufemismo.** Cada chave retida é uma duplicação **permanente**
no razão — o defeito que a KR-B mede. A classe **não é fechada**: medido em 2026-08-09,
441 rows de perna LLM sem gêmea nativa sobrevivem ao colapso (um grupo exige ≥2
proveniências), chegam ao E4 e são override-áveis; 146 delas passam a alvo de remoção pela
mutação de anexar a transação a um statement nativo real do mesmo banco. A retenção
**vai crescer** — a cobertura do enforce erode com o tempo, e o número tem de ser lido,
não presumido zero.

**3. Contadores obrigatórios, com denominador.** Em `pipeline_stage_logs.output_summary`:
`lido`, `overrides_ativos`, `sem_snapshot`, `candidatos`, `colapsaveis`,
`retido_por_override_manual`, `retido_por_override_rule`, `reservatorio_llm_sem_gemea`.
Zero-medido e zero-não-medido são estados **distintos** — foi o defeito que esta lane
pagou quatro vezes. O guard degradado (`not lido` **ou** `sem_snapshot > 0`) degrada o
run inteiro para **measure-only**: o alvo da degradação é sempre "retém tudo", nunca
"colapsa tudo".

**4. §Deferimento datado — 2026-08-09, dono A42.** O motor de re-ancoragem fica deferido
com os quatro defeitos já nomeados, para que quem retomar não os redescubra:

| defeito | conserto exigido antes de qualquer escrita |
|---|---|
| adjudicação por `gate_digest` | o digest é **direction-free** por desenho e `decimal_cents` é magnitude ⇒ +100 e −100 do mesmo dia colidem. Adjudicar por `key_digest` **e** exigir âncora = `hash` de um `RemovalTarget` com `hash_desaparece == True` |
| `new_category` "em algum dos dois baldes" | `_apply_one_override` não move row de balde ⇒ tem de ser **o mesmo balde do sobrevivente** |
| destino com cardinalidade ≠ 1 | exigir `\|rows(survivor)\| == \|rows(âncora)\|`, nunca `≥1` |
| destino já ocupado | `unique=False` na migration da [[ADR-282]] ⇒ checar `destino_ocupado` antes de escrever |

**Ordem de construção quando o gatilho disparar** — do mais barato ao mais perigoso, e
**não** direto para o motor: (1) `retido[rule] > retido[manual]` ⇒ excluir `source='rule'`
da retenção (a regra é keyword sobre a descrição normalizada, que é a própria chave de
colapso: ela se reproduz sozinha no sobrevivente); (2) `retido[manual] ≥ 5% dos
colapsáveis` por 2 runs ⇒ superfície da [[ADR-282]] §5, o usuário re-aplica; (3) quitação
por **equivalência sem escrita** (colapsa quando já existe override ativo no sobrevivente
com o mesmo `new_category`); (4) motor semântico, e só com o defeito de adjudicação
fechado.

**Gatilho verificável no código, não na memória:** `retido_por_override > 0` em qualquer
workspace por 2 runs consecutivos **ou** `reservatorio_llm_sem_gemea` crescendo entre runs
de referência. Os dois são campos de `output_summary` — consultáveis, não lembrados.

**5. Correção de fato — o número `4282/4320` está publicado invertido e com a causa
errada.** O comentário de `gate_key_digest` (e a §791 da [[A40.l2]]) afirma *"a direction
do E4 vem do balde enquanto a do E3 vem do sinal (deriva medida 4282/4320)"*. Medido:
**direction concorda 4320/4320**. O `4282/4320` é o **acerto**, e a divergência de 38 rows
(0,9%) é de **proveniência**, disjunta do conjunto colapsável. A decisão de descartar
`direction` do digest **permanece** — ela se sustenta sozinha em "gate que BLOQUEIA deve
sobre-detectar" —, mas deixa de ter apoio empírico falso.

**6. Correção de fato — o `gate_digest` não era derivável pelos dois lados.** O pipeline
aplicava `normalize_descricao` **duas** vezes (a chave de colapso já a aplica, e
`gate_key_digest` a aplicava de novo) enquanto o backend a aplicava **uma** (o snapshot
guarda a descrição crua). A função **não é ponto fixo**: o regex de sufixo de roteamento
está ancorado no fim da string e remove **um** sufixo por passada, então descrição com
sufixos empilhados produz digests distintos nos dois lados — e o override **nunca**
entraria no deny-set. Medido em 2026-08-09: 4 de 5 formas com sufixo empilhado divergem;
exposição no corpus dogfood é **0/6398 rows** — inerte, e **por isso** invisível,
exatamente como a divergência do `keep_split` sobreviveu à suíte. Conserto:
`gate_key_digest` deixa de normalizar e passa a receber `descricao_norm`; cada lado
normaliza **uma vez**. Passar a descrição **crua** dos dois lados **não** é alternativa:
um grupo agrega rows cuja descrição crua difere por construção (é o que a [[ADR-255]]
it.2 compra), então "a crua do grupo" não existe. Afeta também a cláusula
`snapshot_casa_corpus` do gate já shipado, que sub-contava pela mesma classe.

**7. O que esta emenda NÃO faz.** Não liga o enforce (§Critério de saída do 3e segue com
os 9 eixos, incluindo ensaio de rollback medido). Não revoga a §Decisão 1, a §Decisão 3, a
§Decisão 4 nem a §Decisão 5. Não autoriza quitação por destruição: o único ato que escreve
`orphaned_at` continua sendo operador nominal, auditado, com a medição no corpo do PR.

## Consequências

- Em produção o colapsador **deixa de ser `None`** — sempre instanciado, com a flag
  decidindo `measure()` vs `collapse()`. É o que torna o gate por-run possível.
- A janela de exposição de um override criado entre medir e flipar passa a ser **um run**,
  e é **recuperável**: as colunas de snapshot da [[ADR-282]] sobrevivem ao órfão, então o
  `backfill_override_identity` re-ancora post-hoc. Sem essa propriedade, o desenho exigiria
  gate em runtime.
- `ReviewReason` fica sendo canal de **exceção**, não o normal: N overrides colapsando num
  sobrevivente (`CollisionPlan`), âncora indecidível, ou sobrevivente com override
  divergente. É o `needs_review` cirúrgico — review em bloco vira approve-all e o
  mecanismo morre.

## Alternativas rejeitadas

- **Evitar o problema não removendo row.** É a opção A da decisão de cardinalidade,
  reprovada por medição: fazia a identidade do lançamento depender de **quantos arquivos**
  a família subiu, com sinal perverso (quem envia extrato anual + mensais veria mais renda).
- **Gate em runtime dentro do pipeline.** Acopla estado e força `pipeline/**` a consultar
  DB, contra [[ADR-089]]/[[ADR-111]]. E faria o resultado do run depender de o usuário ter
  categorizado uma transação 5 minutos antes.
- **`ReviewReason` post-hoc como única mitigação.** Quando o aviso sai, o override já não
  resolve e o relatório que a família está olhando já perdeu a categorização manual.
  Reversão silenciosa de decisão do usuário pede **auto-cura**, não aviso.
