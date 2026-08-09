---
id: TRACK-a40-l2-3d-drain
type: track
title: "Track A40.l2 PR3d — a retenção: não colapsar chave com override ativo"
lane: "[[A40.l2]]"
sprint: A40
plan: PLAN-report-trust
status: ready
created_at: "2026-08-08"
agent_role: senior-cto
tags:
  - type/track
  - sprint/a40
  - status/ready
  - priority/p0
  - area/backend
  - area/pipeline
---

# Track A40.l2 PR3d — a retenção

> **Destravado em 2026-08-07** pelo merge do PR3b ([#1276](https://github.com/davidrobert/mathoms/pull/1276),
> `b3b8a74b`), que era sua única dependência. **É da onda desta sprint** — o §Gate de saída da
> [[A40.l2]] faz o contador de 2 re-runs consecutivos só iniciar quando a lane estiver
> terminal, e o 3d é pré-condição do 3e.
>
> **Desenho fechado em 2026-08-09** (co-design de 3 rodadas: 5 medições read-only + 3
> refutadores adversariais + `financial-planner` + `senior-cto`). **Não re-abrir a §1** — ela
> virou registro. Justificativa em [[ADR-364]] §Emenda 2026-08-09.

**Não há drain.** O colapsador recebe um guard congelado por construtor e **retém** — não
colapsa — toda chave cujo `gate_digest` tem override ativo. Zero leitura do E4, zero escrita
em `transaction_overrides`, zero re-ancoragem.

## 1. Registro — de onde vêm os candidatos (decisão fechada)

**Decidido: nem (a) nem (b).** A pergunta original era por onde os candidatos chegariam ao
drain; ela deixou de existir quando o drain saiu do desenho. O colapsador recebe o guard por
**construtor** (`_e3_build_collapser`, `scripts/reconcile_transactions.py:1028-1034`, que já
lê DB pela flag de measure) e a decisão de colapsar vira uma **subtração de conjunto**.

Por que a re-ancoragem caiu: o adjudicador de 6 passos tinha **quatro defeitos medidos** antes
de existir (adjudicação por `gate_digest`, que é direction-free e funde +100/−100; `new_category`
"em algum dos dois baldes", que libera o kind-flip; cardinalidade `≥1` no destino; destino já
ocupado sem unique key). E a propriedade da retenção — *"nenhuma row com override desaparece"* —
é **estritamente mais forte** que a que a re-ancoragem entregaria. Detalhe e deferimento na
[[ADR-364]] §Emenda 2026-08-09.

**A classe é ABERTA** — medido 2026-08-09, e é o que torna a retenção uma escolha, não uma
conveniência: 441 rows de perna LLM sem gêmea nativa sobrevivem ao colapso (grupo exige ≥2
proveniências), chegam ao E4 e são override-áveis; **146 delas viram alvo de remoção** pela
mutação de anexar a transação a um statement nativo real do mesmo banco. A retenção **vai
crescer**, e a cobertura do enforce erode com o tempo. Não presuma zero.

## 2. Restrições duras — verificadas no código

As três restrições anteriores (`_fresh_legacy`, `_preflight`, `_apply` destrutivo em
`backfill_override_identity.py`) ficam **moot**: não há escrita. O módulo é inutilizável em
qualquer call-site, e a [[ADR-364]] §Emenda 2026-08-09 registra isso. As restrições que valem:

- **Zero escrita em `transaction_overrides` pelo caminho do colapso**, provado por mutação.
  É a propriedade que torna o desenho defensável, e preserva o writer único de `orphaned_at`.
- **Guard por construtor, keyword-only, sem default.** `frozenset()` como deny-set é
  fail-**open** na direção destrutiva. A trava não é a assinatura — é **gate AST sobre o
  call-site de produção**, no molde de `tests/unit/pipeline/test_collapse_shadow.py:76-99`.
  Custo do "sem default": 21 call-sites de construtor, 2 de produção
  (`scripts/reconcile_transactions.py:1034`, `dev/certify_ledger_local.py:203`) e 19 de teste
  que passam a `OverrideRetentionGuard.sem_overrides()`.
- **A degradação aponta sempre para "retém tudo".** `not lido` **ou** `sem_snapshot > 0` ⇒ o
  run inteiro degrada para **measure-only**. Nunca "colapsa tudo". O ramo `sem_snapshot`
  espelha a cláusula que `collapse_precondition.py:105-106` já aplica ao gate.
- **`_alvos` exige `not c.retido_por_override`, por acesso a atributo** — nunca
  `getattr(..., default)`, que é a classe fail-open que esta lane já pagou ([[ADR-359]]).
  Sem isso, a chave retida mantém `liberado=False` **para sempre**: a proteção funcionando
  impediria o conserto, e uma correção de um usuário desligaria o enforce do workspace inteiro.
- **O produtor do guard é `collapse_precondition.from_active_overrides`** — reusa `_ativos` +
  `_override_gate_digest`. **Nunca re-implementar o predicado** (a classe `keep_split`, que
  esta lane pagou 2×).

### Contrato — a forma exata do VO

```python
@dataclass(frozen=True)
class OverrideRetentionGuard:
    """Digests de override ativo que NÃO podem ser colapsados. Dado congelado, sem I/O."""

    denied_digests: frozenset[str]
    overrides_ativos: int                             # denominador
    sem_snapshot: int                                 # digest devolveu None
    denied_por_source: tuple[tuple[str, int], ...]    # (("manual", n), ("rule", m))
    lido: bool                                        # separa "li e vazio" de "não li"

    @property
    def degradado(self) -> bool:
        return (not self.lido) or bool(self.sem_snapshot)
```

`from_active_overrides` é o **único** caminho para `lido=True`; `nao_lido()` cobre
`ImportError` / store ≠ `DBArtifactStore`; `sem_overrides()` **afirma** ausência (testes/CLI).
O VO é dado puro em `pipeline/domain/services/` ([[ADR-089]] intacto); o produtor mora no
backend e é importado **lazy em `scripts/`**, como `_e3_collapse_precondition` já faz.

**O guard vale também em `measure()`.** Sem isso o gate pré-flip prediz órfãos que o
enforce-com-guard não produziria, e o 3e fica bloqueado por um hipotético.

## 3. ⚠️ O guard não tem o que reter no dogfood

O PR3b mediu **0 overrides ancorados em row de candidato de colapso** (4
`casou_corpus_fora_de_candidato`, 1 `casou_nada`), re-confirmado em 2026-08-09. As travas do
guard têm de vir de **fixture sintética**, e o PR tem de **dizer isso** — senão alguém lê
"verde no dogfood" como prova de que o guard funciona.

**Frase obrigatória no corpo do PR:** *"o dogfood não prova o guard; ele prova que o guard
ainda não teve o que reter."*

**Re-meça antes de abrir:** `python3 dev/probe_collapse_adjudication.py <ws>`. "Vazio" é
propriedade do corpus **e do tempo** ([[ADR-364]] §5). O probe recusa emitir veredito com
corpus/overrides vazios (`INDETERMINADO`, exit 2) — **não contorne o guard**.

## Aceite

**Seis travas por mutação, cada uma com a mutação plausível declarada** (a que um refactor
faria):

| trava | mutação | esperado |
|---|---|---|
| 1 | `lido=False` ⇒ colapsa >0 rows | vermelho |
| 2 | apagar o ramo `sem_snapshot` do `degradado` | vermelho (fixture com override sem snapshot vê a chave colapsar) |
| 3 | remover a subtração do deny-set | vermelho (chave com override colapsa) |
| 4 | dar **default** ao `retention_guard` no construtor | vermelho por **gate AST** sobre `scripts/reconcile_transactions.py` |
| 5 | `_alvos` volta a ignorar `retido_por_override` | vermelho (gate reprova com a proteção funcionando) |
| 6 | trocar `keep_native` por `survivor_cardinality` em `keep_split` | vermelho pelo invariante `Σ removable_rows dos não-retidos == len(drop)` |

- **Fixture sintética** cobrindo `retido_por_override`, `sem_snapshot > 0` e `lido=False`, com
  a declaração explícita de que o dogfood exercita **zero** delas.
- **Trava anti-destruição:** `COUNT(*) WHERE orphaned_at IS NOT NULL`, `WHERE deleted_at IS NOT
  NULL` **e `COUNT(*) total`** iguais antes e depois. O total é obrigatório porque
  `delete_override.py:87` é **hard delete** — a row some e os outros dois contadores não mexem.
  Papel declarado no teste: prova de que o colapso **não é writer**, não prova de segurança.
- **Invariante substituto do assert morto:** `Σ removable_rows dos candidatos NÃO retidos ==
  len(drop)`, **dentro** de `collapse()` entre a declaração e o `_apply`. É a grandeza que o bug
  do `keep_split` moveu (453 vs 593); `key_digest` não era — as duas chamadas são a mesma função
  pura sobre o mesmo objeto, logo idênticas por construção.
- **Revalidação TOCTOU:** re-leitura do guard em `main_with_store` **depois** de
  `_e3_run_reconciliation`; se digest novo intersecta o conjunto colapsado, **levanta**. Exceção
  ⇒ `result is None` ⇒ `_rollback_and_close_artifact_session` (`pipeline_task.py:1417-1419`), e
  E3 é `criticality="required"`. **Não** usar `validation.valid=False`: esse caminho **commita**
  e pausa (`:1449-1456`).
- **Denominador junto do numerador** em `pipeline_stage_logs.output_summary` (nunca
  `AuditRecord` — `append_audit` é `db.add` sem commit e o rollback do loop apagaria os
  vermelhos): `{lido, overrides_ativos, sem_snapshot, candidatos, colapsaveis,
  retido_por_override_manual, retido_por_override_rule, reservatorio_llm_sem_gemea}`.
  `reservatorio_llm_sem_gemea` (441 hoje) é o **indicador antecedente**: sai da mesma passada de
  `_group_by_key`, contando as chaves com **1** proveniência que o filtro `len(buckets) > 1`
  descarta. Sem ele a lane mede 0 e conclui "vazio" pela terceira vez.
- **`ReviewReason` informativo** (não bloqueante) por chave retida — é o canal que o planejador
  B2B2C lê ao encontrar duas linhas idênticas e precisar saber se é bug ou política.
  `needs_review` **não**: pausar o run por chave retida vira fricção, contra a salvaguarda nº 2.
- **Nenhum texto novo na S2.** O contador da salvaguarda nº 1 continua verdadeiro sob retenção
  (retenção é não-remoção: não entra no `count`). Copy de "M retidos porque você editou"
  convidaria o usuário a apagar a própria correção para destravar a consolidação.
- **Declarar no PR** que `retido_por_override` **sobre-conta por construção** (o `gate_digest` é
  direction-free e funde +100/−100 do mesmo dia; sob retenção a polaridade inverte a favor —
  over-match vira sub-colapso). **Não gatear nada nele.**
- Nenhuma resposta de API vaza hash cru nem descrição de transação.
- Resultado do probe **no corpo do PR**, mesmo que confirme o esperado.

## Ordem

- **PR-A (paridade do `gate_digest`) é pré-condição deste PR.** Sem ela o guard é cego para
  descrição com sufixo de roteamento empilhado — `normalize_descricao` não é ponto fixo e era
  aplicada 2× no pipeline contra 1× no backend ⇒ o override nunca entraria no deny-set e o
  desenho ficaria decorativo. Conserto: `gate_key_digest` deixa de normalizar, o parâmetro vira
  `descricao_norm`, o backend normaliza uma vez, e a fixture pareada ganha ≥2 sufixos empilhados.
- **PR-C (3c1b) serializado antes deste.** Colisão em `scripts/reconcile_transactions.py`
  (± `e3_reconciler_adapter.py`); 3c1b é menor e já especificado.
- **PR-B (3c2) abre em paralelo** — é o long pole real da lane, com arquivos disjuntos.

## Não é escopo

- **Re-ancoragem** — deferida com gatilho verificável ([[ADR-364]] §Emenda 2026-08-09 item 4).
- Qualquer escrita em `transaction_overrides` · `absolvicao_viva` · produtor único de digest ·
  `collapse_readpath.py` · leitura do E4 pelo pipeline · track novo.
- **Superfície de órfão** da [[ADR-282]] §5 — lane própria P1, **não** pré-condição.
- `quarantine_override` + a adjudicação nominal do 1 órfão pré-existente — são do **3e**, porque
  é o ato que faz `liberado=True` e tem de ser revisado junto da decisão de ligar o enforce.
- **Ligar o enforce** (3e) — exige os 9 eixos do §Critério de saída, incluindo **ensaio de
  rollback medido**; undo nunca executado é premissa, não propriedade.
- O **custo do gate por run**, já aberto e pagando em produção — item próprio da lane.

## Referências

- Lane: [[A40.l2]] §3d · §D5 · §Salvaguardas de produto
- ADRs: [[ADR-364]] (§Emenda 2026-08-09 — quitação por retenção; re-ancoragem deferida) ·
  [[ADR-282]] (colunas de snapshot, `orphaned_at`, a superfície §5 prometida) · [[ADR-359]]
  (fail-loud onde era fail-open)
- Instrumento: `dev/probe_collapse_adjudication.py`
- Molde do gate AST: `tests/unit/pipeline/test_collapse_shadow.py:76-99`
- Teste pareado do digest (PR-A): `backend/tests/test_gate_digest_paired_derivation.py`
