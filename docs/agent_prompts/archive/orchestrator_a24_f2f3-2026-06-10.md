# Orquestração — A24 Data Lineage · F2 (de-leak) + F3 (walking skeleton) + F4 (evidencia_path)

> Instância do [_TEMPLATE_orchestrator.md](_TEMPLATE_orchestrator.md) para a **fase de
> RISCO** do plano [DATA_LINEAGE](../plan/DATA_LINEAGE/_README.md). Sucede a Onda 1
> (A23, fechada `done`). A23 entregou o contrato aditivo golden-safe; **A24 exerce o
> risco** que A23 não tocou (de-leak + rebaseline + dedup).
>
> **Pré-revisado** por `senior-cto` (boundary) + `data-engineer` (contrato/dados) em
> 2026-06-09 sob corretude/completude/consistência/precisão — blockers **F2-B/F2-DB**
> consolidados em [DATA_LINEAGE §"Blockers da F2"](../plan/DATA_LINEAGE/_README.md).
> Achado central: **o de-leak é cirúrgico, não sistêmico** — o risco real está na rede
> de rebaseline, endurecida ANTES do 1º rebaseline.
>
> **Uso:** copie o bloco abaixo no início da sessão. Respeita [CLAUDE.md](../../CLAUDE.md)
> e delega aos especialistas de [`.claude/agents/`](../../.claude/agents/).
>
> **Quando arquivar:** quando F2 + F3 estiverem `shipped` em `main` (G3/KR2 1/6). Mover
> para [`archive/`](archive/) com data.

---

```
Continue a sprint A24 (Data Lineage) — **F2 (de-leak da extração) + F3 (walking skeleton)
+ F4 (evidencia_path ∥)**. É a FASE DE RISCO do plano. Fatie em branches/PRs próprios.

## Onde estamos (em origin/main — NÃO refazer)
Sprint corrente: A24 (docs/sprint/A24/_README.md). Plano: docs/plan/DATA_LINEAGE/_README.md.
A23 FECHADA (done): Ondas 0–1 (gate F0 + contrato aditivo) 100% em main, 7 lanes. Já existe:
- Contrato E2 endurecido + FECHADO (ADR-283): natural_key v2, amount decimal, direction,
  source_ref/data_source + FK DB. config/schemas/e2_extract.schema.json é additionalProperties:false.
- Gate dev/check_extract_no_domain_imports.py (extração ∌ category_template/*_dedup/config_store).
  ⚠️ Pega IMPORT, não regex inline. NÃO cobre account_normalization (dívida na linha 17 — F2 fecha).
- Substrato de golden: dev/golden_diff.py + backend/tests/test_report_view_model_snapshot.py +
  tests/test_e5_conservation_invariants.py.

## Leia primeiro (canônico)
1. CLAUDE.md — code style (gate exigente), git/PR, delegação.
2. docs/plan/DATA_LINEAGE/_README.md — §"Blockers da F2 (gate G2)" (F2-B/F2-DB — LEIA INTEIRO),
   §Critério de corte Extract|Transform (tabela file:line), §Ondas (Onda 2/3 = A24), §Guard-rails
   (G-c rebaseline, G-f dogfood), §Verificação F2/F3, §Q2 (F2 antes de F3).
3. docs/adr/280-*.md (de-leak), 279-*.md §E (E5→E6 evidencia_path), 242-*.md §D4 (hint = sinal),
   283-*.md (contrato E2 fechado).
4. Espelhe formato de lane: docs/sprint/A23/lanes/A23-l7-extract-check.md. IDs livres: A24.l1+.

## Achado da revisão (muda o desenho — NÃO re-fatie por seção do relatório)
- `tipo_lancamento` é DEAD-DOWNSTREAM: zero consumidores em pipeline/backend; morre no dict E2;
  e2_natural_key.py:59 confirma que NÃO alimenta a K4. Único toque: parser-interno + testes.
- `numero_conta_norm` já é re-normalizado em todo consumidor (document.from_e2_dict:158 fallback;
  account_resolver.py:63). bank_accounts (ADR-226) lê norm da config, NÃO do E2. O vazamento REAL
  é o IMPORT de normalize_account_number em scripts/e2/common.py:393.
- Logo: re-fatiar POR VAZAMENTO (não por seção). slice1≈residual se fatiar por "patrimônio".

## As lanes (crie docs/sprint/A24/lanes/A24-l{1..}-*.md)
ORDEM/DEPENDÊNCIAS:

- dl-f2-discovery (A24.l1 — GATE, PRIMEIRO, NÃO move código de extração): (a) classifica TODOS
  os consumidores de tipo_lancamento/numero_conta_norm em {domínio downstream | parser-interno |
  teste-only} (F2-B1); enumera as N variantes de tipo_lancamento por banco (F2-B2). (b) ENDURECE
  O SUBSTRATO antes de qualquer rebaseline: +invariante de conservação POR CATEGORIA em
  tests/test_e5_conservation_invariants.py (Σ despesas[cat]==despesa_total, idem receita, cents
  int — F2-DB7); estende ManifestEntry de golden_diff.py com reason(file:line)+adr obrigatórios
  (F2-DB6); cria dev/check_golden_rebaseline_isolation.py (golden+código no mesmo commit→falha,
  F2-DB5). (c) blast radius SOBRE DOGFOOD (dado real local/gitignored), NÃO só fixtures (fixtures
  não exercitam os campos → falso conforto; F2-DB8); esperado ZERO value_delta (de-leak cirúrgico)
  — qualquer delta = consumidor oculto = blocker. Co-design: data-engineer + senior-cto.

- dl-f2-deleak-account-norm (A24.l2, após discovery): remove a chamada/import de normalize_account_number
  de scripts/e2/common.py:393 (extração emite só numero_conta raw); mantém o fallback em
  document.from_e2_dict durante a janela. AMPLIA check_extract_no_domain_imports com
  account_normalization (F2-B4) + teste de violação→exit 1. Golden esperado = NO-OP (Transform
  recomputa idêntico); rebaseline deve ser delta-zero verificável, não manifesto de valores.
  Co-design: data-engineer + senior-cto.

- dl-f2-deleak-tipo-lancamento (A24.l3, ∥ a l2): remove tipo_lancamento do OUTPUT da extração +
  do contrato fechado e2_extract.schema.json (ADR-283) na MESMA PR + migra test_schema_validation.py:195
  (F2-DB1); enforcement por AUSÊNCIA-DE-CAMPO (test_e2_contract_no_methodological_fields), NÃO gate
  de regex inline (F2-B5). Se a classificação for desejável, recria como sinal na Transform — NÃO
  cria stage Transform só p/ campo que ninguém lê. Co-design: data-engineer + senior-cto.
  ⚠️ category_hint (ADR-242) NÃO é desta fila — já é sinal preservado; só anexar origin=llm_extract
  FLAT (mín. aditivo); objeto {value,origin,confidence} aninhado é DEFERIDO (breaking em 3 superfícies,
  F2-DB2).

- dl-f4-evidencia-path (A24.l4, ∥ INDEPENDENTE — pode abrir já): E5→E6 citação verificada (ADR-279 §E).
  evidencia_path condicional-obrigatório no VALIDATOR Pydantic (NÃO no JSON Schema). Guardrail 3
  camadas: (1) path ∈ whitelist E5; (2) resolve não-nulo; (3) match número↔valor; falha→needs_review.
  Golden estrutural ≥3 negative cases; tokens +<5%; check_planner_manifest_coverage. Co-design:
  prompt-engineer (guardrail/eval/determinismo) + data-engineer (whitelist E5).

- dl-f3-skeleton-patrimonio (A24.l5, após F2) + dl-f3-skeleton-resto (A24.l6): _lineage field-level
  no patrimonio_calculator + lineage_registry (dict literal eager, ADR-281 B2) + LineageResolver
  (stateless, ADR-111) + CLI + gates check_lineage_refs (import real) / check_lineage_sum
  (Σ amount[member_hashes]==value, cents int). G3: localizar patrimônio líquido via 1 comando;
  run 2× → VIEW-MODEL SNAPSHOT byte-idêntico (NÃO payload E2 bruto — F2-B8). Co-design:
  senior-cto + data-engineer.

## Inegociáveis (DIFERENTE da Onda 1 — aqui REBASELINA de propósito)
- Substrato endurecido (F2-DB5/6/7) ANTES do 1º rebaseline — é entrega do discovery, não pré-existe.
- Rebaseline só via golden_diff + manifesto com reason/adr + commit isolado (check_golden_rebaseline_isolation)
  + label golden-rebaseline + 2º revisor (G-c). Invariantes de conservação (incl. a nova por categoria)
  NÃO podem quebrar pós-rebaseline — 2ª testemunha.
- Discovery ANTES de mover (Q2); blast radius sobre DOGFOOD; esperado zero value_delta.
- Remoção de campo conforma ao contrato fechado ADR-283 na mesma PR; enforcement por ausência-de-campo.
- check_extract_no_domain_imports continua verde + ampliado com account_normalization.
- Dinheiro nunca float (ADR-090); stateless (ADR-111); pipeline/** não importa fastapi/celery/sqlalchemy.
  CI verde antes do merge. Concluído = PR squashed em main.
- Co-design ANTES de codar. Múltiplos gatilhos → especialistas em PARALELO.

## Antes de começar
- git fetch origin && git worktree list && git for-each-ref --sort=-committerdate
  refs/remotes/origin/agent/ | head (confirme ninguém em dl-f2-*/dl-f3-*/dl-f4-*).
- Crie UMA branch por lane (agent/dl-f2-<slug>/<yyyyMMdd-HHmm>) a partir de origin/main.
- Comece por dl-f2-discovery (gate + substrato) + dl-f4-evidencia-path em paralelo (independentes).
  deleak-* só após discovery fechado; F3 só após F2. Anuncie cada operação git. Comece lendo as
  fontes e propondo plano + co-design por lane.
```
