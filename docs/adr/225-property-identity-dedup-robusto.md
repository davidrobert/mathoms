---
id: ADR-225
type: adr
title: "Dedup robusto de PropertyIdentity — matrícula/QA como canonical fallback + first-write-wins cross-codigo_rfb"
status: Decidido
phase: A12
date: "2026-05-19"
decided_at: "2026-05-19"
relates_to:
  - "[[ADR-215]]"
  - "[[ADR-157]]"
  - "[[ADR-143]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 225"
  - "Property dedup robusto"
  - "Canonicalizer matrícula"
tags:
  - area/persistence
  - area/pipeline
  - area/methodology
  - phase/a12
  - status/decidido
  - type/adr
---

> ADR longa (>150 linhas) por design: estende [[ADR-215]] §3 (matching cross-IRPFs) sem reescrever §1/§2/§4/§5/§6, mas a coordenação canonicalizer ↔ resolver ↔ backfill script ↔ invariante E5 exige um único documento de referência.

## Contexto

[[ADR-215]] introduziu `property_identity` com chave de dedup
`(workspace_id, codigo_rfb, endereco_canonical)`. O canonicalizer
(`pipeline/domain/services/endereco_canonicalizer.py`) extrai
`(via, numero)` via regex que exige prefixo `rua|avenida|rodovia|estrada|travessa|alameda|praca`.
Quando o regex falha, `endereco_canonical=NULL`, e o resolver
(`backend/app/services/db_property_identity_resolver.py:31`)
**pula o lookup e sempre insere row nova** — `low_confidence=true`
no DTO sinaliza para UI, mas não há ação de merge automatizada.

Reproduzido em produção (workspace dogfood `5@5.com`, 2026-05-19):
14 rows visíveis em `/config` → "Residência principal e imóveis"
quando o usuário tem **5–6 imóveis físicos reais**. Três classes
distintas de duplicata observadas:

1. **Low-confidence × IRPF multi-ano (3 rows).** "CASA - EXEMPLO 100,
   QUADRA 1 LOTE 1, BAIRRO EXEMPLO" não casa o regex (sem
   prefixo de logradouro). Cada IRPF anual (2022, 2023, 2024) gera
   row separada — `dev/dedup_property_identity.py` atual pula
   `endereco_canonical IS NULL`.
2. **Cross-codigo_rfb mesma propriedade (5 imóveis × 2-3 rows).**
   Mesmo endereço aparece como `codigo_rfb="11"` (Apto, IRPF refinado)
   E `codigo_rfb="01"` (grupo-pai genérico, LLM não inferiu subcódigo
   ou fonte XLSX/contrato). Match key requer codigo_rfb idêntico →
   2 identities para o mesmo imóvel.
3. **Variação numérica entre fontes (1 par).** "Praça Exemplo
   190" (IRPF) vs "Praça Exemplo 186" (QuintoAndar) — typo
   numa fonte; canonicalizer trata como endereços distintos.

[[ADR-215]] §5 explicitamente rejeitou hash determinístico em favor de
"fuzzy + human-in-loop merge". O modelo é correto, mas: (a) human-in-loop
merge **não existe na UI hoje** — usuário vê duplicatas sem ação;
(b) o canonicalizer só usa logradouro+número, ignorando **identificadores
estáveis** que a descrição já carrega (matrícula RFB, código QuintoAndar,
IPTU).

**Invariante adjacente a preservar:**
`backend/app/services/real_estate_e5_integration.py:_match_identity` (linhas 102-115)
filtra `PropertyIdentity` por `codigo_rfb` **estrito** ao agregar
`valor_brl` por imóvel cross-IRPFs. Qualquer mudança que altere
`codigo_rfb` de uma row após primeira escrita **quebra a agregação E5
para os IRPFs históricos que trouxeram o codigo antigo**. Esta ADR
respeita o invariante via decisão de first-write-wins (§2).

## Decisão

Adotar **três extensões coordenadas** ao modelo de [[ADR-215]] §3, sem
mudar contrato de DTO, schema DDL, nem invariante de agregação E5:

### 1. Canonicalizer com fallback por identificador estável

`canonicalize()` em `endereco_canonicalizer.py` estende a cascata.
**Order matters:** via+numero **primeiro** (path quente + backward-compat
com rows legadas no DB); identificadores estáveis como **fallback** quando
via+numero falha.

| # | Sinal | Regex | Namespace | Justificativa |
|---|---|---|---|---|
| 1 | Via + número (legado) | atual `_VIA_NUMBER_PATTERN` | `<via> <numero>` (sem prefixo, compat backward) | Caminho quente: cobre maioria dos IRPFs hoje; preserva canonical de rows já em DB |
| 2 | Matrícula RFB | `r"matr[íi]cula[\s.:#nº°]*([\d.]{4,})"`, normaliza sem pontos, exige ≥4 dígitos pós-normalização | `mat:NNNN` | Imutável por CRI; resolve low-confidence multi-ano quando via+numero falha (QUADRA/LOTE) |
| 3 | Código QuintoAndar | `r"quintoandar[:\s]+(\d+)"` | `qa:NNNNN` | Estável enquanto imóvel na plataforma; cobre fontes externas |
| 4 | IPTU / Inscrição municipal | `r"(?:iptu\|inscri[cç][aã]o\s*municipal)[:\s]+([\d.\-/]+)"`, exige ≥6 caracteres | `iptu:NNN` | Último recurso quando demais falham |

**Por que via+numero precede matrícula** (revisão de design pós-co-design):
preserva `endereco_canonical` de rows existentes (`exemplo 100`,
`exemplo 320`…). Se matrícula viesse primeiro, novos IRPFs
gerariam canonical `mat:NNN` ≠ legacy → duplicatas adicionais ao deploy.
Resolve Case A (low-confidence multi-ano sem via+numero extraível) via
cascata fallback. Case C (typo 190 vs 186 com via+numero em ambos) **não
é resolvido** por este caminho — documentado em §Follow-ups; futura ADR
pode propor backfill que normalize para preferência matrícula com
migration de rows legadas.

**Mínimo 4 dígitos em matrícula** (mitigação senior-cto): evita pegar
lixo OCR ("matrícula 12" = página/parágrafo, não matrícula real).
Matrículas reais sempre têm ≥4 dígitos.

**Namespace de cidade/UF em matrícula** foi **deferido** para follow-up
(originalmente proposto pelo data-engineer como `mat:NNN@cidade-uf`).
Detecção robusta entre formatos variados ("SAO PAULO/SP", "São Paulo
- SP", "Cyrela Campinas - SP") tem heurística complexa o suficiente
pra valer ADR/PR próprio. Por ora, o risco real (colisão entre matrículas
coincidentes de CRIs em cidades distintas no MESMO workspace) é baixo:
workspace dogfood 5@5.com tem 100% dos imóveis em SP. Cobre caso B/C
futuros via ADR-226 quando aparecer workspace multi-cidade afetado.

Cada cascata retorna o **primeiro hit não-vazio**; sem hits → `None`
(low_confidence, comportamento atual preservado).

### 2. Resolver loose-match SEM upgrade de codigo_rfb

`DBPropertyIdentityResolver.match_or_create` ganha **fallback de match**
quando codigo_rfb difere mas endereco_canonical coincide. **Não há
upgrade in-place de codigo_rfb** — first-write-wins; codigo_rfb fica
estático após primeira escrita.

```python
def match_or_create(workspace_id, lookup, first_seen_year, descricao_sample):
    if lookup.endereco_canonical is not None:
        # 1. Estrito: codigo_rfb + endereco_canonical (path quente)
        existing = self._find_by_canonical_strict(workspace_id, lookup)
        if existing is not None:
            return _to_record(existing)
        # 2. Loose: mesmo endereco_canonical, qualquer codigo_rfb
        loose = self._find_by_canonical_loose(workspace_id, lookup.endereco_canonical)
        if loose is not None:
            return _to_record(loose)  # reusa row existente; NÃO modifica codigo_rfb
    inserted = self._insert_row(workspace_id, lookup, first_seen_year, descricao_sample)
    # 3. Reconciliation read pós-insert (defesa contra race E1.5c concorrente)
    if lookup.endereco_canonical is not None:
        reconciled = self._reconcile_after_insert(workspace_id, inserted, lookup.endereco_canonical)
        if reconciled is not inserted:
            return _to_record(reconciled)
    return _to_record(inserted)
```

**Por que NÃO upgrade de codigo_rfb:**
`real_estate_e5_integration._match_identity` (linhas 102-115) filtra
candidatas por `i.codigo_rfb == codigo` estrito. Se upgrade muta
codigo_rfb de `"01"` → `"11"` no DB, IRPF histórico que extraiu
`codigo="01"` deixa de casar — `valor_brl` zera para aquele property_id
**silenciosamente**. First-write-wins preserva o invariante de
agregação. Custo: UI pode mostrar "Imóvel" (label do "01") em vez de
"Apto" para imóveis onde fonte XLSX/contrato chegou antes do IRPF
refinado. Aceito; mitigado pelo Phase A (ADR-225 PR1, já mergeado) que
deu label legível ao "01".

**Insert + reconciliation read** (mitigação data-engineer): após insert,
re-SELECT loose por `(workspace_id, endereco_canonical)` ordenado por
`created_at ASC LIMIT 1`. Se a row mais antiga não for a recém-inserida,
deletar a recém-inserida e retornar a antiga. Cobre race condition de
2 workers Celery processando IRPFs distintos do mesmo workspace
simultaneamente. Custo: 1 SELECT extra por insert (frio). SQLite-safe;
PG-safe sem advisory lock.

### 3. Dedup script estendido (3 passes idempotentes)

`dev/dedup_property_identity.py` ganha 2 passes novos após o atual:

```
Passe 1 (atual): agrupa por (workspace_id, codigo_rfb, endereco_canonical),
                  funde first-write-wins.
Passe 2 (novo):  agrupa rows com endereco_canonical IS NULL por
                  (workspace_id, titular_key) e funde pares com
                  rapidfuzz.token_set_ratio(descricao_sample) ≥ 92.
                  Output JSON registra fuzzy_score por par para auditoria.
Passe 3 (novo):  agrupa por (workspace_id, endereco_canonical) ignorando
                  codigo_rfb. Funde quando UM lado é "01" ou "" e outro
                  é subcódigo específico ("11", "12", "13", …).
                  Quando AMBOS são subcódigos específicos divergentes
                  (ex.: "11"+"12"), NÃO funde — marca em log estruturado
                  para review humano (futura UI de merge).
```

**Por que threshold ≥ 92** (mitigação data-engineer): valida pares como
`"APTO 80m² PINHEIROS"` vs `"APARTAMENTO PINHEIROS 80 m2"` (legítimo
match cross-anos) mas rejeita `"APTO PINHEIROS 80m²"` vs `"CASA
PINHEIROS 80m²"` (tipos distintos). Eval set parametrizado trava o
threshold em CI.

Determinismo: passes 1 e 3 são exatos (sem fuzzy). Passe 2 é fuzzy
controlado com auditoria. `--dry-run` default; relatório JSON por
passe; `--apply` exige `--yes` explícito.

Idempotente; rerun após `--apply` em workspace já dedupado produz
relatório vazio.

## Alternativas consideradas

- **(B) Drop codigo_rfb da chave de dedup.** Mais simples, mas funde
  apartamento e casa coexistindo no mesmo lote (edge case real).
  Cascata estrita-primeiro de §2 preserva sem perder dedup cross-fonte.
- **(C) Hash determinístico de (matrícula | QA | IPTU).** Já rejeitado
  por [[ADR-215]] §5 — mas a objeção (correção monetária + variação LLM)
  não aplica a matrícula/QA estáticos. Não adotado porque cascata em §1
  captura o mesmo benefício sem opaqueness — chave continua legível em
  SQL queries.
- **(D) Upgrade in-place de codigo_rfb.** Versão anterior desta ADR
  propunha. Rejeitada porque quebra invariante de agregação E5
  (`real_estate_e5_integration._match_identity` filtra estrito). Alternativa
  considerada: coluna `codigo_rfb_aliases JSONB` + match com membership.
  Adia decisão para ADR futura — não é necessário para resolver o caso
  `5@5.com`.
- **(E) Merge UI human-in-loop.** Complementar, não substitutivo. Cobre
  o caso de matrícula+QA+IPTU+via_numero todos ausentes (raro).
  Rastreado em §Follow-ups.
- **(F) Advisory lock por `(workspace_id, endereco_canonical)`.**
  Considerado para race E1.5c concorrente. Não funciona em SQLite e
  exige design distinto em PG. Reconciliation read pós-insert é
  SQLite-safe e funcionalmente equivalente.

## Consequências

**Positivas:**

- ✅ Caso `5@5.com` resolvido: 14 → ~5 rows (paridade com imóveis
  físicos reais). Mensurado via dry-run pré-merge.
- ✅ Aplicável a todos os workspaces (passe 2/3 do script roda
  retroativamente); fix de canonicalizer/resolver impede regressão em
  novos uploads.
- ✅ Sem mudança no DTO `PropertyResponse` nem em
  `WorkspacePropertyOverride` — overrides existentes continuam apontando
  para o `property_id` canônico (após dedup), via realocação que o
  script atual já faz (passe 1, generalizado).
- ✅ Sem mudança de DDL — schema atual permite o que precisa.
- ✅ Race E1.5c concorrente mitigado via reconciliation read.
- ✅ Cascade observability via counter `mathoms.property_identity.cascade_hit{level}`.

**Negativas:**

- ⚠️ codigo_rfb fica estático (first-write-wins). UI pode mostrar "Imóvel"
  para casos onde fonte genérica chegou antes do IRPF refinado.
  Mitigado em PR1 (Phase A) com label legível. Upgrade explícito fica
  para ADR futura (não bloqueia este caso).
- ⚠️ Cascata em §1 aumenta superfície do canonicalizer. Eval set específico
  exigido em gates.
- ⚠️ Resolver com 2-pass + reconciliation read adiciona 2 queries por
  imóvel novo. Em E1.5c o volume é dezenas, não milhares — overhead
  desprezível.
- ⚠️ Passe 2 do backfill é fuzzy (determinismo parcial). Output JSON
  com fuzzy_score por par garante auditoria pré-`--apply`.

**Consumers de codigo_rfb a auditar:**

| Site | Uso | Impacto desta ADR |
|---|---|---|
| `real_estate_e5_integration._match_identity` | Filtro estrito por codigo_rfb ao agregar valor_brl IRPF | Preservado (first-write-wins) |
| `set_property_classification` (override) | Não filtra; usa property_id direto | Sem impacto |
| `PropertyResponse.codigo_rfb` (DTO) | Label UI (PR1 já robusto) | Sem impacto |
| `property_identity_enricher` | Lookup via resolver | Adapta automaticamente à nova lógica |

**Riscos:**

| Risco | Mitigação |
|---|---|
| Cascata pega falso-positivo (matrícula coincidente entre cartórios SP+RJ) | Namespace `mat:NNN@cidade-uf` quando cidade/UF detectável; fallback `mat:NNN` puro só quando ambíguo |
| OCR ruim em matrícula vira fallback errôneo | Regex exige ≥4 dígitos pós-normalização; OCR ruim cai para próxima cascata naturalmente |
| Backfill funde rows com overrides conflitantes | Passe 1 já tem precedente; output script lista `overrides_realocados` por property_id; `--dry-run` mandatório no PR |
| Race E1.5c concorrente cria dupes mesmo após fix | Reconciliation read pós-insert detecta e remove dupe; teste com 2 sessões simulando concorrência em `tests/test_db_property_identity_resolver_concurrency.py` |
| codigo_rfb estático prejudica futura agregação refinada | Trade-off aceito; ADR-225 documenta consumers; futura ADR pode introduzir aliases JSONB |
| Passe 2 fuzzy gera falso-merge silencioso | Output JSON com `fuzzy_score` + revisão humana pré-`--apply`; threshold ≥92 calibrado por eval set em `tests/test_dedup_property_identity.py` |

## Follow-ups (fora do escopo)

- ✅ **Case C — typos numéricos em via+numero entre fontes** (ex.: 190 vs
  186 mesmo imóvel). **Entregue** em [[ADR-265]] / [PR #471](https://github.com/davidrobert/mathoms/pull/471)
  via fuzzy lookup (não requereu inverter cascata nem migration destrutiva):
  3º nível na cascata do resolver (strict → loose → **fuzzy** → insert) +
  pass 4 no helper de dedup E1.5c + Passe 4 no backfill script. K=4
  default + K=8 com complemento string-equal + guard de complemento
  divergente. `canonicalize` preservado intacto.
- **Namespace de cidade/UF em matrícula** (`mat:NNN@saopaulo-sp`):
  detectar cidade/UF na descrição com heurística confiável (sem grab de
  "Imóvel em ..." ou "Cyrela Campinas...") demanda parsing mais robusto
  que regex simples. Justifica ADR/PR próprio quando aparecer caso real
  de colisão multi-cidade em produção. Hoje, matrícula puro
  (`mat:NNN`) é suficiente para todos os workspaces ativos.
- **Merge UI human-in-loop.** Para casos onde todas as cascatas falham
  E passe 2 fuzzy não pega. Endpoint `POST /workspaces/{ws}/properties/merge`
  + UI checkbox grupos. Tracking em `docs/agent_prompts/track_property-merge-ui.md`
  quando priorizado.
- **`codigo_rfb_aliases JSONB`.** Quando casos como `5@5.com` se
  acumularem com label "Imóvel" insistindo, vale evoluir. ADR futura
  preserva agregação E5 via match com membership.
- **Sinal de IPTU em E1.6.** Prompt LLM pede extração explícita quando
  presente no PDF IRPF — `bens_direitos[].iptu: Optional[str]`. Aditivo, lazy fill.
- **`property_label` curado por workspace.** Permitir usuário renomear
  "Apto Pinheiros" via UI.

## Gates

- **Canonicalizer:** eval set em `tests/unit/pipeline/test_endereco_canonicalizer.py`
  com 4 cascatas, ordem de prioridade, edge cases OCR (matrícula <4
  dígitos rejeitada), namespace cidade/UF.
- **Resolver:** `backend/tests/test_db_property_identity_resolver.py`
  com cenários: (a) match estrito; (b) match loose preserva codigo_rfb
  da row mais antiga; (c) reconciliation read deleta dupe em race
  simulada; (d) low-confidence ainda cria row nova quando canonical=None.
- **Dedup script:** `tests/test_dedup_property_identity.py` com workspace
  sintético de 14 rows → 5 esperadas (cobre os 3 passes); auditoria
  fuzzy_score em output; passe 3 não funde subcódigos divergentes.
- **Backfill dry-run em produção:** `dev/dedup_property_identity.py 5@5_workspace_id --dry-run`
  pré-merge, JSON anexo ao PR; `--apply` pós-aprovação humana
  documentada em runbook a criar em `docs/reference/runbooks/dedup_properties.md`
  (parte da entrega do PR3).
- **Property identity goldens:** `tests/unit/pipeline/test_property_identity_enricher.py`
  ganha caso com 3 fontes (IRPF ano N + N+1 + QA) para mesmo imóvel →
  1 `property_id` final, codigo_rfb da primeira escrita preservado.
- **Real-estate E5 integration:** `backend/tests/test_real_estate_e5_integration.py`
  ganha caso pós-merge confirmando que agregação por property_id casa
  IRPFs com codigo_rfb original (não upgraded).
- **Sem regressão de override:** `backend/tests/integration/test_property_override_sticky.py`
  continua passando após backfill (override sobrevive a realocação).
- **Cascade counter:** `mathoms.property_identity.cascade_hit{level=mat|qa|iptu|via_numero|none}`
  via `backend/app/core/logging.py` (estrutura disponível pós ADR-110).
- **Estimativa Phase B+C:** 1.5–2 dias de trabalho (revisado pós-review senior-cto).

## Referências

- [[ADR-215]] — Modelo base PropertyIdentity + classificação override
  (esta ADR estende §3 sem reescrever §1, §2, §4, §5, §6).
- [[ADR-157]] — Schema E1.6 `extract_irpf_full` (potencial extensão
  `iptu` em follow-up).
- [[ADR-143]] — Rules-as-code (regex extractors viram docstring no
  módulo + esta ADR como canônica).
- Diagnóstico: workspace dogfood `5@5.com` 2026-05-19, screenshot
  `/config` mostrando 14 rows. Co-design 2026-05-19: `data-engineer`
  (dedup semantics + backfill fuzzy + race condition), `senior-cto`
  (invariante E5 + namespace matrícula + estimativa testes).

## Status — Decidido

PR1 (Phase A — labels legíveis + ADR Proposto) mergeado 2026-05-19 ([apps#329](https://github.com/davidrobert/mathoms/pull/329)).
PR2 (Phase B + C — canonicalizer cascade + resolver loose-match +
dedup script 3 passes + runbook + tests) consolidado nesta entrega.
Passe 2 (fuzzy low-confidence) ficou de fora — risco vs valor exige
curadoria; adia para follow-up se sinalizar real em monitoração.
