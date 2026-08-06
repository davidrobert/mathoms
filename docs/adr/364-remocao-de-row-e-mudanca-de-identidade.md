---
id: ADR-364
type: adr
title: "Remover row no E3 é mudança de identidade para override — herda a restrição da ADR-354 e a quita por re-ancoragem"
status: Proposto
date: "2026-08-06"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - phase/a40
---

# ADR-364 — Remover row no E3 é mudança de identidade para override

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
