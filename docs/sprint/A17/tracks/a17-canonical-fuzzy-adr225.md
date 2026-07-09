---
id: TRACK-a17-canonical-fuzzy-adr225
type: track
title: "Track A17 — Canonical fuzzy para números próximos (extensão ADR-225)"
lane: "[[A17.canonical-fuzzy]]"
sprint: A17
status: consumed
created_at: "2026-05-23"
consumed_at: "2026-05-23"
shipped_pr: 471
agent_role: senior-cto
tags:
  - type/track
  - sprint/a17
  - status/consumed
  - area/pipeline
  - area/persistence
  - area/backend
  - methodology/data-quality
---

# Track A17 — Canonical fuzzy para números próximos (extensão ADR-225)

> ✅ **Entregue em [PR #471](https://github.com/davidrobert/mathoms/pull/471) (2026-05-23).** ADR canônica [[ADR-265]] (Decidido). Co-design data-engineer + financial-planner ajustou K=10 do track para **K=4 default** + **K=8 com complemento string-equal** + **guard duro de complemento divergente**. 46 testes novos; 0 regressões. Caso real do workspace founder (Praça Exemplo 190 vs 186) consolidado.

**Branch sugerida:** `agent/canonical-fuzzy-adr225/<yyyyMMdd-HHmm>`
**Relaciona:** [[ADR-225]] (property identity dedup), [[ADR-239]] (comprovantes de bem), [[ADR-246]] (dedup cross-IRPF de imóveis).
**Origem:** follow-up deixado em aberto pelo PR #468 (cross-codigo dedup do ADR-246).

---

## Problema

`endereco_canonicalizer.canonicalize` ([pipeline/domain/services/endereco_canonicalizer.py](../../../../pipeline/domain/services/endereco_canonicalizer.py)) produz canonicals **string-exatos** via cascata (via+numero → matrícula → QA → IPTU). Quando o **mesmo imóvel físico** é descrito em fontes diferentes com **números levemente divergentes** (ex.: número do prédio vs número da torre, transcrição da escritura diferente da declaração IRPF), a cascata `via_numero` gera canonicals distintos e o dedup falha.

**Caso real do report `fae3544d` (workspace founder, run `a90ce448-7e3f-4c09-b3f9-06edb064a5c1`, 2026-05-23):**

| Fonte | Descrição | `canonical` produzido |
|---|---|---|
| IRPF (`codigo_rfb=11`) | `APARTAMENTO - CONDOMINIO EXEMPLO C - APTO 34 - PRACA EXEMPLO 190` | `exemplo 190` |
| Comprovante de bem (`codigo_rfb=01`) | `Apartamento - Praça Exemplo, 186 - Ap 34, São Paulo - SP` | `exemplo 186` |

É o **mesmo imóvel** (Praça Exemplo, mesmo prédio, mesmo apartamento 34). O número difere porque um documento traz o número da torre/bloco (190) e outro o número do prédio (186) — variação editorial típica entre escritura, IPTU e IRPF.

Como o canonical é string-exato, [`DBPropertyIdentityResolver._find_by_canonical_loose`](../../../../backend/app/services/db_property_identity_resolver.py) não casa, [`dedup_imoveis_consolidados`](../../../../pipeline/domain/services/imoveis_dedup.py) não casa, e a duplicata sobrevive até o relatório.

## Restrições / invariantes

- **Não introduzir falso-positivo.** Falso-positivo (imóveis distintos colapsados) é estritamente pior que falso-negativo (duplicata visível). Decisão de domínio explícita em [[ADR-246]] §"Sem chave robusta → não dedup".
- **`codigo_rfb` continua imutável** (invariante [[ADR-225]] §1 + memória `feedback_codigo_rfb_invariant`). Não tocar.
- **First-write-wins** preservado: o canonical canônico de uma propriedade é o primeiro escrito, novos matches APONTAM para ele; não há in-place upgrade.
- **Cascata atual da ADR-225** (`via_numero → matrícula → QA → IPTU`) **não muda**. A extensão vive como **nova etapa de match**, não substituição.
- **Sem migration destrutiva** de dados existentes. Próximo run E1.5c sana via re-execução; backfill opcional via `dev/dedup_property_identity.py` (Passe 3 já existe; adicionar Passe 4 análogo).
- **Não acoplar ao backend** dentro de `pipeline/`. Resolver via repositório DB pode receber lookup fuzzy, mas `canonicalize` em `pipeline/` continua síncrona/pura (sem dependência de FastAPI/SQLAlchemy — ver `dev/check_pipeline_boundaries.py`).

## Opções consideradas (recomendação preliminar)

### Opção A — Fuzzy de número apenas dentro da MESMA via (Recomendado)

Match loose adicional: dois canonicals do tipo `<via_norm> <n>` casam quando:

1. `<via_norm>` é **idêntica** (mesma rua/avenida/praça, mesma normalização ortográfica via ADR-225 §1).
2. `|n1 - n2| ≤ K` (ponto de partida K=10, threshold conservador).

**Onde aplicar:** apenas no resolver `_find_by_canonical_loose` E no helper de dedup — não muda `canonicalize` em si. O canonical persistido continua único; o **lookup** é que tolera fuzzy.

- **Pró:** preserva contrato de `canonicalize` (determinístico, string-exato). Cobre o caso real. Threshold ajustável.
- **Contra:** edge cases — números próximos em via grande (ex.: Av Paulista 1500 vs 1490) são imóveis distintos com K=10. Calibrar K via golden + audit.

### Opção B — Match por prefixo de via SEM número (mais agressivo)

Loose nível 2: canonicals com mesma via mas números diferentes (qualquer diff) viram match.

- **Pró:** cobre 100% dos casos editoriais.
- **Contra:** falso-positivo garantido em vias longas. **Rejeitar.**

### Opção C — Normalizar número via expansão de prédio ↔ torre/bloco

Aprendizagem assistida por LLM: ao encontrar canonicals `X 190` e `X 186` com matrícula/IPTU comum, registrar mapping persistente `(via, 190) ↔ (via, 186)` em nova tabela `address_aliases`. Match futuro consulta tabela.

- **Pró:** zero falso-positivo (depende de evidência).
- **Contra:** requer schema novo, gatilho de aprendizado, infra. Escopo muito maior — ADR sucessora própria, não esse track. **Adiar.**

### Recomendação inicial

**Opção A com K=10** como ponto de partida, calibrado contra golden + relatório do workspace founder. Implementar como **novo método** no resolver e no helper, **não** alterando `canonicalize`. Abrir ADR Proposto antes do PR (P0 — toca invariante de identidade de imóvel).

## Tarefas

1. **Abrir ADR Proposto** (próximo ID disponível na hora; reservar cedo via PR de doc-only para evitar colisão — ver memória `feedback_adr_id_collision_long_session`). Status `Proposto`, fase A17.canonical-fuzzy. Cite [[ADR-225]] como base e [[ADR-246]] como motivador. Inclua tabela de canonicals (Praça Exemplo 190 vs 186 etc.).
2. **Novo helper puro** `pipeline/domain/services/canonical_fuzzy_match.py::matches_fuzzy(canonical_a: str, canonical_b: str, *, max_number_diff: int = 10) -> bool`. Lógica: extrai `<via, numero>` de ambos (regex `^(.+?)\s+(\d+)$`), casa se via idêntica e diff numérico ≤ K. Canonicals que não casam o regex (formato `mat:`, `qa:`, `iptu:`) só casam por igualdade exata — não usar fuzzy.
3. **Resolver DB** ([db_property_identity_resolver.py](../../../../backend/app/services/db_property_identity_resolver.py)): adicionar `_find_by_canonical_fuzzy` como **3º nível** de cascata (estrito → loose → fuzzy → insert). Carrega candidatos da MESMA via via prefix LIKE e aplica `matches_fuzzy` em Python.
4. **Helper de dedup** ([imoveis_dedup.py](../../../../pipeline/domain/services/imoveis_dedup.py)): novo pass 4 (após cross-codigo do PR #468) que agrupa por via comum e aplica fuzzy. Reusa as regras de "não conflito específico" do pass 3 — `cod=11` + `cod=12` no mesmo bairro com números próximos não funde.
5. **Golden test** com canonicals divergentes reais do workspace founder (anonimizados).
6. **Calibração de K**: rodar contra todos os workspaces existentes; tabular falsos positivos potenciais; ajustar.
7. **Backfill opcional** via `dev/dedup_property_identity.py`: novo Passe 4 espelhando a regra.
8. **Documentar** em `docs/reference/ARCHITECTURE.md §4.1` glossary se a regra de domínio mudar (não deve — é refinamento técnico).

## Critério de aceite

- Workspace founder: re-roda E1.5c → `imoveis_consolidados` cai de **7 → 6** imóveis (Praça Exemplo consolidado).
- Falso-positivo zero em amostra de validação (rodar contra ≥5 workspaces e auditar manualmente o diff).
- Property_id continua único após match fuzzy (não duplica row).
- `WorkspacePropertyOverride` (residência principal, classification) continua sticky pós-fuzzy-merge.
- Tests:
  - Unit (`tests/unit/pipeline/test_canonical_fuzzy_match.py`): matches verdadeiros, edge cases (números limítrofes K, vias homônimas em ruas distintas, formatos `mat:`/`qa:`/`iptu:` que NÃO devem fuzzy), normalização ortográfica preservada.
  - Integration: `test_e15_consolidate_dedup.py` ganha cenário "mesmo prédio, números 190 vs 186" → 1 entry.
  - Backend: `tests/test_db_property_identity_resolver.py` ganha cenário fuzzy match retorna row existente.
- `python3 dev/check_code_style_regression.py` — sem regressões.
- Suite ampla `-k "imovel or dedup or property_id or e15"` — 0 regressões em ~370 tests.

## Anti-tarefas (escopo proibido)

- **Não** alterar `canonicalize` em si — apenas o lookup tolera fuzzy.
- **Não** introduzir LLM ou aprendizado online (Opção C). É escopo separado, ADR própria.
- **Não** tocar `WorkspacePropertyOverride` (UI/schema) — só consumidor.
- **Não** mudar a regra "maior valor vence" do helper ([[ADR-246]]).
- **Não** misturar com outras lanes (apolice, parecer, etc.) — branch dedicada.

## Especialistas a invocar antes de codar

- **`data-engineer`** — revisão da chave de matching, threshold K, impacto cross-stage no payload de imóveis, schema/migration impacts. **Obrigatório** (mexe em invariante de PropertyIdentity).
- **`financial-planner`** — confirmar invariante: se 2 imóveis distintos colapsarem por bug, qual o impacto patrimonial e na alocação-alvo. Sanity check de domínio.
- **`prompt-engineer`** — **NÃO invocar** (sem LLM nesse PR).

## Arquivos relevantes

- [pipeline/domain/services/endereco_canonicalizer.py](../../../../pipeline/domain/services/endereco_canonicalizer.py) (linhas 170-200 — cascata atual)
- [backend/app/services/db_property_identity_resolver.py](../../../../backend/app/services/db_property_identity_resolver.py) (linhas 21-69 — match cascade)
- [pipeline/domain/services/imoveis_dedup.py](../../../../pipeline/domain/services/imoveis_dedup.py) (linhas 50-74 — pass cross-codigo, modelo para novo pass fuzzy)
- [dev/dedup_property_identity.py](../../../../dev/dedup_property_identity.py) (linhas 100-133 — Passe 3 cross-codigo, modelo para Passe 4 fuzzy)
- [docs/adr/225-property-identity-dedup-robusto.md](../../../adr/225-property-identity-dedup-robusto.md) (precedente)
- [docs/adr/246-dedup-imoveis-cross-irpf.md](../../../adr/246-dedup-imoveis-cross-irpf.md) (motivador)
- `_scratch/verify_cross_codigo_fix.py` (modelo de script de verificação contra baseline real — não commitado, em gitignore)

## Pontos de atenção (lições do PR #468)

- **Property_id de pré-fix está cristalizado.** Workspaces existentes têm property_identity rows criadas antes deste track; o resolver fuzzy não vai consolidá-las retroativamente sem o Passe 4 do script. Documentar isso no PR.
- **Tipo de imóvel cod=01 vs cod=11/12.** Caso real: comprovante de bem ADR-239 sempre traz codigo genérico `01`. O fuzzy precisa combinar com a regra cross-codigo do PR #468 (já implementada) para que IRPF (cod=11) com canonical `X 190` case com comprovante (cod=01) canonical `X 186`. **Verificar ordem dos passes:** cross-codigo (PR #468) → fuzzy (este track), ou cross-codigo subsume fuzzy? Analisar.
- **Threshold K é decisão de domínio.** Não chutar; calibrar contra dados reais. K=10 é ponto de partida; pode precisar ser maior em zonas com numeração esparsa ou menor em vias densas.
- **`endereco_canonical` é coluna persistida em `property_identity`.** Se decidirmos REGRAVAR canonicals existentes (cenário improvável), é migration substantiva e exige nova ADR. Default: manter persistido + tolerância apenas em lookup.
- **Edits perdidos entre turnos** — worktree `.claude/worktrees/<x>` pode ser revertido por outras sessões. Primeira ação: criar branch `agent/canonical-fuzzy-adr225/<ts>` antes de editar (lição do PR #423/#468).
