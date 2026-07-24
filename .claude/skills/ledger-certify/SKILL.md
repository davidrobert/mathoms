---
name: ledger-certify
description: >-
  Certifica o RAZÃO — os stages E3 (reconciliação) + E4 (categorização) de UM
  workspace, no grão transação/posição — caçando perda, dupla-contagem e
  miscategorização silenciosas (a soma fecha no relatório mas a tx foi perdida no
  reconcile, o investimento foi contado em dobro, ou a transferência virou
  receita). Use SEMPRE que o dono pedir para "certificar/validar o reconcile ou a
  categorização de um workspace", ver se transações somem ou dobram entre E2 e E4,
  conferir se a categorização não vazou transferência para receita/despesa, ou
  validar E3/E4 antes/depois de um fix de reconciliador/categorizador — mesmo sem
  a palavra "skill". NÃO certifica a ingestão E0→E2 (isso é parse-certify) nem
  roda o pipeline inteiro/avalia o relatório final (isso é pipeline-review).
  Recebe o workspace por email OU uuid.
---

# ledger-certify

Procedimento do **loop principal** (não é um agente) para: re-derivar E3
(reconcile) + E4 (categorize) de um workspace **in-process e deterministicamente**
sobre os artefatos E2 persistidos, atribuir a **cada grupo de reconciliação e
cada balde de categorização** um veredito de conservação/integridade, e produzir
uma revisão priorizada delegando aos especialistas do §Subagentes do CLAUDE.md,
com verificação adversarial.

É **análise, não implementação** — não altere reconciliador/categorizador nem
abra PR de fix; o entregável é diagnóstico + plano de ataque priorizado
(candidatos a lane).

**Fronteira vs [[parse-certify]] e [[pipeline-review]]** (a skill do meio, cita os
dois vizinhos):

- **[[parse-certify]]** certifica a **ingestão E0→E2**, grão **documento** (cada
  arquivo virou artefato correto?). Termina em E2.
- **`ledger-certify`** (aqui) certifica **E2→E4**, grão **transação/posição** (a
  tx sobreviveu ao reconcile? foi categorizada sem virar outra coisa? o
  investimento não foi contado em dobro?). E2 é a borda de entrada (assume E2
  correto — parse-certify o certificou); os **agregados E4** são a borda de saída.
- **[[pipeline-review]]** roda o pipeline inteiro e critica o **relatório final
  E5→E7**, grão **relatório**. Se um CV de conservação falha no E5, é a
  `ledger-certify` que **localiza** se a quebra entrou em E3 ou E4.

Classe canônica (skill vs. subagente vs. prompt): [[ADR-302]] — 4ª instância da
classe, não exige ADR própria. Reusa contratos existentes: [[ADR-342]]
(anti-silêncio, cents tol-zero), [[ADR-287]] (natural_key), [[ADR-271]] (dedup de
investimento), [[ADR-090]] (cents), [[ADR-343]] (estado durável / PII). Catálogo
humano: `docs/reference/SKILLS.md`. Rubrica de veredito:
[`references/rubric.md`](references/rubric.md).

## Parâmetros

- **workspace** (obrigatório) — email (ex.: `5@5.com`) ou UUID.
- **run_id** (opcional, default = run mais recente `completed`) — o run cujo E2
  persistido serve de insumo. A skill **re-deriva** E3/E4 a partir desse E2, não
  confia no E3/E4 gravado (que pode ser parcial sob modo incremental, ADR-080).
- **baldes** (opcional, default = todos os 7) — subconjunto de baldes E4 a
  certificar (`despesas`, `receitas`, `patrimonio`, `investimentos`, `seguros`,
  `pontos_milhas`, `fluxo_mensal_detalhado`). v1 cobre os 7.

## Ambiente

Rode do **checkout principal** (não um worktree) — os scripts importam `backend`
e leem `DATABASE_URL`/Fernet/`STORAGE_ROOT` do `.env`, e os artefatos E2/E3/E4
vivem em `pipeline_artifacts` (DB, [[ADR-212]], payload possivelmente Fernet).
Precisa do venv do repo. **Não é necessário worker Celery/Redis, nem chamada
LLM** — E3/E4 são determinísticos (P0, free tier); a skill re-roda a fatia E3→E4
**in-process** (`InMemoryArtifactStore`), sem disparar run e sem escrever no DB.

## Procedimento

### Passo 1 — Resolver workspace + run + inventário de artefatos

`scripts/resolve_ledger.py <workspace> [--run <run_id>]` retorna `workspace_id`,
o `run_id` alvo, e as keys de artefato por stage: E2 (`extract_bank_documents` +
baseline), E3 (`reconcile_transactions`), E4 (`categorize_transactions`, 7 keys) —
lidas via `stage_aliases()` (aceita legado `E3`/`E4` **e** descritivo, ADR-093).
Guarde o `run_id` e as keys.

### Passo 2 — Re-derivar E3+E4 in-process (determinístico, sem side-effects)

O modo primário **não** confia no E3/E4 persistido — re-roda a transformação
sobre o E2 persistido, igual o `parse-certify` re-parseia em vez de confiar no E2
gravado. Semeie um `InMemoryArtifactStore` com os artefatos E2, com os flags/config
reais do workspace (`dedup_natural_key_v2_enabled`, `learned_rules_v2`,
`config_overrides` family/categorization/transferencias_internas), e rode E3+E4
**pulando persist e learning-loop** (o learning-loop **escreve** `TransactionOverride`
— desligue-o). Zero write no DB, zero Celery.

### Passo 3 — Ledger de conservação (cents) + cross-check de drift

Compute o **ledger de conservação em int cents** (tol-zero, [[ADR-090]]) nas duas
transições — as igualdades exatas estão na [rubrica](references/rubric.md):

- **E2→E3**: toda tx extraída é reconciliada OU dedup declarado (count HARD);
  Σ valor conserva (HARD quando `dups==0`; senão `coberto-sem-verificação` — o
  valor removido no dedup **não é declarado** no artefato, só a contagem).
- **E3→E4**: cada tx em exatamente 1 balde; transferência interna netada (não
  vira despesa+receita); Σ por categoria == total; patrimônio/investimento
  separados de fluxo.

Depois **cross-check** o E3/E4 fresco vs o persistido: divergência = **drift**
(código mudou pós-último run, ou artefato stale) — reporta, não falha por si só.

### Passo 4 — Atribuir veredito + delegar aos especialistas

Classifique **cada grupo E3 e cada balde E4** em **um dos 5 vereditos** da
[rubrica](references/rubric.md): `conservado` · `coberto-sem-verificação-de-valor`
· `dedup/transfer-legítimo` · `perda/dupla-contagem-silenciosa` (P0) ·
`não-verificável`. Regra de ouro: só sobe a `conservado` quem tem **checksum que
prova o fechamento** (count-in==count-out, Σ-in==Σ-out, chave de dedup única);
sem isso, teto `coberto-sem-verificação`.

**Conservação é o piso, não o teto.** Os piores erros são **sum-preserving** e
passam por toda conservação (dedup dobrado é linha legítima de composição; swap de
categoria preserva o total). Delegue o julgamento de **fronteira de classificação**
em paralelo (1 mensagem, N `Agent` calls), brief mínimo, pedindo decisão/objeção
com evidência — `data-engineer` e `financial-planner` são **co-iguais** aqui:

| Lacuna | Especialista |
|---|---|
| Contrato de conservação cross-stage, read-path, identidade natural_key/dedup (ADR-287/271) | `data-engineer` |
| Materialidade: que dimensão do relatório o erro corrompe (patrimônio, fluxo, reserva, alocação); fronteira de categoria (transferência≠consumo, aporte≠despesa) | `financial-planner` |
| Impasse de contrato de identidade/stage — decide e fecha | `senior-cto` |

(**Sem** `prompt-engineer` — E3/E4 é LLM-free; **sem** `product-designer` — sem UI.)

### Passo 5 — Verificação adversarial

Cada candidato a `perda/dupla-contagem-silenciosa` passa por **1 verificador
cético** que tenta REFUTAR re-derivando a evidência (re-rodar a fatia E3/E4
in-process, re-query do artefato, recomputar o Σ em cents, localizar se a perda
entrou no reconciler ou no categorizer). Descarte os REFUTED.

## Guardrails

- **Read-only rigoroso** — zero write no DB, zero Celery, learning-loop e persist
  **desligados**. Prove com assert de contagem de rows `pipeline_artifacts`/
  `transaction_overrides` inalterada antes/depois. Não dispara run (isso é
  pipeline-review).
- **Zero PII no entregável** — sem CPF, valores ou nomes reais; papéis
  (titular/cônjuge) e faixas. Descrições de tx carregam **contraparte** → scrub
  mais agressivo que no grão-documento. Nome próprio como chave de dict é smell a
  **reportar, não reproduzir**.
- **Evidência sempre** — `campo`/número em cents/`stage:key` mascarado. Hipótese
  não verificada não vira bug.

## Entregável (três destinos · [[ADR-343]])

Bifurque por natureza, como a [[pipeline-review]]:

1. **Working** → `_scratch/ledger-certify-<slug>-<AAAA-MM-DD>.md` — completo, todas
   as naturezas. **Duas** tabelas de veredito (o grão-transação tem dois eixos):
   - **Eixo E3 (por grupo):** `Grupo (banco+conta+moeda+período) · n_tx E2 · n_tx E3 · Σ conserva? (cents) · não-casadas c/ motivo · Veredito · Lacuna`
   - **Eixo E4 (por balde):** `Balde · n_itens · Σ conserva vs E3? · transferência netada? · dupla-contagem? · Veredito · Lacuna`
   - Achados priorizados (silêncio primeiro): `ID · Achado · Dimensão · Severidade · Prioridade (P0–P3) · Dificuldade (S/M/L) · Risco regr. · Fix · Candidata a lane`
2. **Cru durável (off-git)** → `storage/<uuid>/ledger_certify/<ts>-<run8>/synthesis.md`
   — cópia crua **inclusive achados de instância/dado + PII**. Path proibido no git.
3. **Curado canônico (git)** → **append** de seção `## rN — ws-<uuid8>-<data>` em
   [`docs/_MOC/LEDGER-CERTIFY-active.md`](../../../docs/_MOC/LEDGER-CERTIFY-active.md)
   com **só achados sistêmicos/defeito**, deduplicados por `(dimensão,
   evidência-âncora, regra)`. Commit-safe: zero literal monetário/nome próprio.

## Critério de aceite da skill

- Re-derivação E3+E4 in-process determinística; **zero write** no DB (provado).
- As igualdades HARD em cents int, tolerância zero (1 centavo reprova — paridade
  com o gate de produção).
- Todo grupo E3 e balde E4 com um dos 5 vereditos; `conservado` só com checksum
  que fecha (nunca "re-rodou sem exceção").
- **≥1 check que falharia num cenário sum-preserving construído de propósito**
  (mover tx entre baldes, duplicar posição cross-ano) — senão a skill herdou a
  cegueira da conservação e não agrega valor.
- Cobertura de `natural_key` reportada como número (embrião de KR pra beta).
- Candidato a silêncio sobrevive à verificação adversarial; zero PII vazada.

## Armadilhas

- **Falso-verde é o inimigo** — soma agregada fechar no E5 não prova que E3/E4
  estão certos: uma tx dropada no E3 mascarada por erro compensatório passa no CV
  agregado. Certifique **por grupo/balde**, não por total.
- **Stub E2 não é silêncio** — E2 com `requires_llm_fallback` → E3 não tem o que
  reconciliar = `escalado-honesto`, não perda. Leia o E2 **vivo não-fallback**.
- **Estado incremental (ADR-080)** — o E3/E4 persistido pode cobrir só docs de um
  run parcial; por isso o modo primário **re-deriva** sobre todo o E2, e trata a
  divergência fresco↔persistido como drift, não como perda.
- **`natural_key` null** — ~92% ausente quando falta titular (gate classe-c,
  ADR-287); mede a cobertura e reporta, mas não deixa o join sticky-override
  quebrado virar falso `perda`.
- **Checkout errado** — DB/`STORAGE_ROOT` seguem o `_PROJECT_ROOT` de onde o
  script roda (sys.path); rode do **checkout principal**, senão resolve DB/storage
  vazios do worktree.
- **NÃO se aplica** o que os moldes vizinhos fazem: sem "cripto em repouso" (lê
  artefato do DB, não bytes Fernet de `storage/data/`); sem "dispara run completo"
  e sem custo LLM (não toca E5+, não roda E0→E2).
