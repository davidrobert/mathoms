---
id: ADR-364
type: adr
title: "Remover row no E3 é mudança de identidade para override — herda a restrição da ADR-354 e a quita por re-ancoragem"
status: Proposto
date: "2026-08-06"
amended_at: ["2026-08-07"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - phase/a40
---

# ADR-364 — Remover row no E3 é mudança de identidade para override

> ⚠️ **Emendada em 2026-08-07.** Nenhuma §Decisão foi revogada. O que mudou é o
> **mecanismo do gate** que a §Decisão 2 pressupunha: o predicado era inalcançável por
> construção, e a saída natural de quem estivesse sob pressão de entrega seria afrouxá-lo.
> Os itens **3** e **5** da §Estado de implementação saíram de ⬜ para ✅. Leia a §Emenda
> antes de construir sobre `evaluate()` — a assinatura mudou e o predicado tem cinco
> cláusulas, não duas.

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
| **2** — quitação por re-ancoragem | ⬜ [[A40.l2]] PR3d |
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
