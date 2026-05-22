---
id: ADR-239
type: adr
title: "Comprovantes de Bem (CRLV) + Apólices de Seguro polimórficas + FIPE refresh assíncrono — Sprint A18"
status: Decidido
phase: A18.l1
date: "2026-05-21"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-127]]"
  - "[[ADR-135]]"
  - "[[ADR-137]]"
  - "[[ADR-143]]"
  - "[[ADR-144]]"
  - "[[ADR-145]]"
  - "[[ADR-157]]"
  - "[[ADR-212]]"
  - "[[ADR-216]]"
  - "[[ADR-225]]"
  - "[[ADR-231]]"
  - "[[ADR-236]]"
  - "[[ADR-238]]"
  - "[[ADR-240]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 239"
  - "Comprovantes de Bem"
  - "Apólices de Seguro"
  - "FIPE integration"
  - "extract_comprovantes_bens"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/persistence
  - area/methodology
  - methodology/auvp
  - methodology/cerbasi
  - phase/a18
---

## Contexto

Sessão dogfood 2026-05-21 com **6 PDFs reais** do owner expandiu o batch fiscal de 15 (Sprint A17 — ADR-238) para 21 documentos. Os 6 novos são:

- **3 CRLV-e** (Certificados de Registro e Licenciamento de Veículo, exercício 2025): Yamaha NMAX 160 STH2C88 2024, Yamaha NMAX DAV0351 2018, Fiat Toro GDK6A27 4×4 2022.
- **3 apólices de seguro**: Tokio Marine (NMAX STH2C88), Porto Moto (NMAX DAV0351), **Porto Proteção Combinada** (Toro GDK6A27 **+ residência R Tasso da Silveira 61**).

Hoje:

1. **CRLV cai em `.other` silencioso.** [`backend/app/services/classification/type_classifier.py`](../../backend/app/services/classification/type_classifier.py) não tem regra para DETRAN/RENAVAM/CRLV. Veículos no Mathoms são `baseline_patrimonial.veiculos_consolidados[]` (array sem schema interno) + Grupo G02 do IRPF E1.6 ([[ADR-157]]).
2. **Apólice cai em `.other` silencioso.** Nenhum schema, classifier, parser ou categoria de proteção patrimonial existe. Há bucket de despesa "seguros" em `scoring.json`, mas zero modelagem do documento da apólice.
3. **Não há integração FIPE.** Valor de veículo no relatório usa apenas o que o IRPF declarou (valor de aquisição, congelado). Sem fonte de valor de mercado atualizado.
4. **`baseline_patrimonial.veiculos_consolidados[]` é o anti-pattern que [[ADR-216]] e [[ADR-225]] vieram consertar para imóveis.** Array livre, sem identidade canônica, sem invariantes.

Insights críticos extraídos da inspeção dos 3 PDFs reais:

- **Apólice combinada (auto + residencial num único PDF)** é padrão Porto Seguro — caso V1, não edge case.
- **FIPE code vem direto da apólice** (Tokio: 827125-9; Porto Moto: 8271020; Porto Combinada: 15253). Lookup BrasilAPI fica trivial — `GET /fipe/preco/v1/<code>` sem fuzzy matching.
- **Renovação inter-seguradora ("congênere")** preserva classe de bônus — Tokio doc declara "Renovação Congênere PORTO 8891272 classe 2". Schema precisa de `congenere_anterior` para lineage.
- **Pagador ≠ Segurado** — Tokio Marine paga pela SONIA (cônjuge) no cartão dela; segurado é David. FK opcional para `family_members` em ambos os campos.
- **3 corretoras diferentes** (Bedoni SUSEP 202020138, Mrr Miseg SUSEP 202020150, Thiago Alcântara SUSEP 201008086) — fragmentação de mercado é cidadã V1.

Co-design `data-engineer` + `financial-planner` em paralelo (2026-05-21) consolidou as decisões abaixo. ADR companheira [[ADR-240]] cobre o **card S_PROTECAO** no relatório (Sprint A19).

## Decisão

Adotar **modelo de domínio expandido para bens e proteção** com 9 decisões coordenadas. Sprint A18 entrega ingestão + persistência + FIPE; Sprint A19 ([[ADR-240]]) entrega card de produto. V1 cobre auto + residencial; vida/saúde/acidentes/PJ ficam para V2 com schema já preparado (discriminated union antecipa).

### D1 — Tabela canônica `vehicles` (não array livre)

Migration Alembic cria tabela `vehicles` seguindo padrão [`real_estate_assets`](../reference/PIPELINE_ARTIFACTS.md) ([[ADR-216]]). Identidade composta imutável **`(workspace_id, placa_normalizada, renavam)`** com invariante tipo [[ADR-225]]: identidade não sofre upgrade in-place — mudança = veículo diferente (transferência ou erro de OCR → `needs_review`).

```python
class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[UUID]
    workspace_id: Mapped[UUID]
    placa: Mapped[str]              # normalizada (uppercase, sem hífen)
    renavam: Mapped[str]
    marca: Mapped[str]
    modelo: Mapped[str]
    ano_modelo: Mapped[int]
    ano_fabricacao: Mapped[int]
    fipe_code: Mapped[Optional[str]]
    cor: Mapped[Optional[str]]
    combustivel: Mapped[Optional[str]]
    codigo_rfb: Mapped[Optional[str]]  # cruza IRPF G02 (default "21" auto, "22" aero, "23" embarc)
    archived_at: Mapped[Optional[datetime]]  # veículo vendido
    __table_args__ = (
        UniqueConstraint("workspace_id", "placa", name="uq_vehicle_workspace_placa"),
        CheckConstraint("renavam ~ '^[0-9]{9,11}$'", name="ck_renavam_format"),
    )
```

`baseline_patrimonial.veiculos_consolidados[]` deixa de ser fonte e vira **projection** com FK (igual `real_estate_e5_integration` em [[ADR-216]] D9).

### D2 — Schema polimórfico `ApolicePayload` com Discriminated Union

Padrão de [[ADR-238]] D2. Top-level lenient (`additionalProperties: true`), sub-models strict.

```python
class ApolicePayload(BaseModel):
    apolice_numero: str
    seguradora: str  # institution_catalog code (porto, tokiomarine, ...)
    vigencia_inicio: date
    vigencia_fim: date
    classe_bonus: int | None
    congenere_anterior: CongenereRef | None  # {seguradora, apolice_numero}
    premio_total_brl: Decimal  # wire string ADR-090
    forma_pagamento: Literal["a_vista", "cartao", "boleto", "debito"]
    pagador_cpf: str | None        # ≠ segurado quando cônjuge paga
    pagador_family_member_id: UUID | None  # FK opcional ADR-127
    segurado_cpf: str
    segurado_family_member_id: UUID | None
    corretor: CorretorRef
    bens_segurados: list[BemSeguradoDiscriminated]
    sinistro_indenizacao_recebida_brl: Decimal | None  # placeholder V2 (evita migration breaking quando entrar IR sobre indenização)
    confidence: float
    prompt_version: str

class CorretorRef(BaseModel):
    susep_code: str
    nome: str
    cpf_or_cnpj: str  # PJ (CNPJ) majoritário, mas PF (CPF + SUSEP) existe
    cnpj_or_cpf_kind: Literal["cnpj", "cpf"]

class BemSeguradoVeiculo(BaseModel):
    tipo: Literal["veiculo"]
    placa: str
    fipe_code: str | None
    marca: str
    modelo: str
    ano_modelo: int
    veiculo_id: UUID | None  # FK opcional — reconciliação assíncrona (D3)
    coberturas: list[CoberturaDiscriminated]

class BemSeguradoImovel(BaseModel):
    tipo: Literal["imovel"]
    endereco: EnderecoStruct
    tipo_imovel: Literal["casa", "apartamento", "comercial"]
    imovel_id: UUID | None  # FK opcional para real_estate_assets (ADR-216)
    coberturas: list[CoberturaDiscriminated]

class BemSeguradoPessoa(BaseModel):  # V2: vida/saúde/acidentes
    tipo: Literal["pessoa"]
    pessoa_cpf: str
    family_member_id: UUID | None
    coberturas: list[CoberturaDiscriminated]

class CoberturaMaterial(BaseModel):
    tipo: Literal["material"]
    nome: str  # "Colisão/Incêndio/Roubo", "Incêndio Residencial", ...
    ramo_susep: str | None
    lmi_modo: Literal["valor_fixo", "fipe_percentual", "primeiro_risco_absoluto"]
    lmi_brl: Decimal | None  # quando lmi_modo='valor_fixo'
    lmi_fipe_percentual: Decimal | None  # quando lmi_modo='fipe_percentual' (ex.: 1.00 = 100% FIPE)
    franquia_brl: Decimal | None
    premio_brl: Decimal

class CoberturaRcfv(BaseModel):
    tipo: Literal["rcfv"]
    nome: Literal["danos_materiais", "danos_corporais", "danos_morais"]
    lmi_brl: Decimal
    premio_brl: Decimal

class CoberturaVida(BaseModel):  # V2 — placeholder em V1
    tipo: Literal["vida"]
    capital_segurado_brl: Decimal
    beneficiarios: list[BeneficiarioRef]  # FK opcional family_members
    premio_brl: Decimal

# (CoberturaSaude, CoberturaAcidentes idem — V2)
```

Wire monetário sempre string decimal ([[ADR-090]]). Enums `codigo_rfb` reaproveitados de [[ADR-225]] sem alteração in-place.

### D3 — FK opcional + reconciliação assíncrona

`bens_segurados[*].veiculo_id` / `imovel_id` / `family_member_id` são **`UUID | None`**. Apólice ingerida antes da entity canônica materializar grava `None`; **job de reconciliação** rodando ao final de `extract_comprovantes_bens` preenche FK retroativamente quando placa/CPF/endereço materializa.

Padrão idêntico a `possible_duplicate_of_id` em uploads ([[ADR-238]]) e `real_estate_e5_integration` ([[ADR-216]]). Reconciliação é idempotente e segura para retry.

### D4 — Dedupe hierárquico com fail-fast em conflito

- **Chave forte:** `(workspace_id, placa_normalizada)` — UNIQUE constraint enforça.
- **Defesa em profundidade:** se placa colide com RENAVAM diferente → **`needs_review=true`** sem merge automático (transferência de propriedade ou erro OCR — humano decide).
- **FIPE code** é chave **fraca** (genérica modelo/ano) — usar para enriquecimento, nunca dedupe.
- **Fuzzy marca+modelo+ano** só na reconciliação IRPF G02 → `vehicles`. Confidence ≥ 0,85 = auto-merge; < 0,85 = `needs_review`.
- **Cross-workspace dedupe não existe** ([[ADR-127]] tenancy). Veículo vendido vira `archived_at` no workspace antigo; cadastro novo no comprador.

### D5 — FIPE refresh assíncrono via BrasilAPI

Provedor: **[BrasilAPI](https://brasilapi.com.br/api/fipe)** (open-source, mantido pela comunidade, zero lock-in). Escolha registrada após análise comparativa com Parallelum e SaaS pagos — Caminho A da sessão exploratória 2026-05-21.

Extensão de [[ADR-135]] `market_rates`:

```sql
ALTER TABLE market_rates ADD COLUMN reference_month text;  -- 'YYYY-MM'
-- série existente: ('currency_brl', 'USD', ...)
-- nova série: ('fipe_vehicle', '827125-9', value, date, source='brasilapi_v1', reference_month='2026-12')
```

**Lookup assíncrono — nunca síncrono no upload:**

1. Stage `extract_comprovantes_bens` produz payload com `fipe_code` mas `fipe_value=None, fipe_status="pending_refresh"`.
2. Hook pós-write em `DBArtifactStore` ([[ADR-212]]) enfileira Celery task `refresh_fipe_value(fipe_code, ano_modelo)`.
3. Task consulta `market_rates` → cache hit (TTL = 30 dias após `reference_month`) retorna; miss → HTTP BrasilAPI + persiste.
4. Stage E1.5c consolidate baseline tolera `fipe_status in {fresh, stale_acceptable, pending_refresh, missing}`. Só `missing` em veículo ativo bloqueia (passa por `needs_review`).
5. **Cron job anual (Janeiro)** atualiza Dezembro/<ano-1> para todos os `fipe_codes` ativos em `vehicles` — base para IRPF.

### D6 — LLM cascata Haiku → Sonnet com gate explícito

Apólice combinada é multi-bem e tem cláusulas que confundem Haiku (LMI atribuído ao bem errado). Custo Sonnet em todos os docs é 5× exagero quando 90% das apólices são simples.

**Cascata:**

1. **Haiku V1** em toda apólice.
2. **Re-run com Sonnet** se qualquer destes for verdade:
   - `len(bens_segurados) > 1` (multi-bem detectado)
   - `confidence < 0.7`
   - Texto contém `"combinada"` + (`"residencial"` OU `"residência"`) + (`"auto"` OU `"veículo"`)
3. Cache de prompt por SHA do PDF ([[ADR-144]]).

Custo médio esperado: ~$0.015/doc (~90% Haiku, 10% Sonnet).

**Goldens obrigatórios:** 3 PDFs do owner (anonimizados/sintetizados — CPF mascarado, valores arredondados, nomes fictícios) + 3 sintéticas mock (vida, saúde, acidentes — V2 placeholder). Sem golden, mudança de prompt = regressão silenciosa.

### D7 — Histórico de apólices imutável temporal

Apólices são **eventos temporais** (vigência início+fim). Modelo:

- **Múltiplas rows em `pipeline_artifacts`** ([[ADR-212]]), uma por apólice, `artifact_key = "apolice_<numero>"`.
- Query "apólice ativa do veículo X em data D" = filtro temporal `vigencia_inicio <= D <= vigencia_fim AND veiculo_id = X`.
- `congenere_anterior` no payload preserva lineage de bônus (não FK porque congênere pode ser pré-Mathoms, sem row).
- Renovação anual = apólice nova, não update.
- **Retenção:** apólices vigentes + 5 anos pós `vigencia_fim` (prescrição cível BR para sinistro).

### D8 — Stage único `extract_comprovantes_bens`

Stage descritivo único ([[ADR-093]] F9.2) com sufixo `-2_comprovante_bem.json` em `_STAGE_TO_SUFFIX` ([[ADR-212]]). `artifact_key` codifica tipo + identificador:

- CRLV: `crlv_<placa>_<ano_exercicio>` → `crlv_sth2c88_2025`
- Apólice: `apolice_<numero_normalizado>` → `apolice_37837540`

Despacho interno por `tipo_comprovante: Literal["crlv", "apolice"]` detectado em E0.

### D9 — Catálogo institucional expandido

Migration Alembic ([[ADR-137]]):

- Enum `institutions.category` ganha `insurance_carrier` (seguradora), `insurance_broker` (corretora), `reference_data` (fonte de dados — BrasilAPI, FIPE).
- Seeds novos: `portoseguro` (insurance_carrier), `tokiomarine` (já no seed atual — mudar `category` de `bank` para `insurance_carrier` se inconsistente; investigar em P1), `brasilapi` (reference_data).
- Corretoras NÃO vão no `institutions` (não são contrapartes fiscais). Persistem como objeto `CorretorRef` inline no payload da apólice.

## Gates

- **G1** — Migration Alembic `vehicles` + extensão `market_rates.reference_month` mergeada antes do PR1 da L1.
- **G2** — `extract_comprovantes_bens` em `STAGE_REGISTRY` desde o PR1 da L1.
- **G3** — `dev/codigo_rfb_invariant_check.py` continua verde após adição de `codigo_rfb='21'/'22'/'23'` em `vehicles` — código RFB não muda in-place ([[ADR-225]]).
- **G4** — 6 PDFs do batch (3 CRLV + 3 apólices) classificam corretamente com `confidence ≥ 0.7` ao final de cada lane. 15 PDFs de informes ([[ADR-238]]) e demais documentos continuam em seu fluxo (não regridem).
- **G5** — `pytest backend/tests tests -q` + `cd frontend && npm test -- --run` + `pre-commit run --all-files` verdes por PR.
- **G6** — BrasilAPI lookup é **sempre assíncrono** (Celery) — teste unitário valida que stage não bloqueia em HTTP.
- **G7** — Apólice combinada Porto (Toro + residência) renderiza com `len(bens_segurados) == 2` no golden — bug de "LMI atribuído ao bem errado" é regressão de prompt.
- **G8** — Goldens sintéticos em `tests/fixtures/comprovantes/` (CRLV + apolice simples + apolice combinada + 3 placeholders V2).

## Implementação

Detalhe operacional por lane:

- **L1 — CRLV** → [[TRACK-a18-l1-crlv-veiculos]] (~5d eng, 4 PRs)
- **L2 — Apólice** → [[TRACK-a18-l2-apolice-seguro]] (~6d eng, 5 PRs; combinada como caso V1)
- **L3 — FIPE refresh** → [[TRACK-a18-l3-fipe-refresh]] (~3d eng, 2 PRs)

Lanes em [`docs/sprint/A18/lanes/`](../sprint/A18/lanes/).

PR de Proposto desta ADR inclui apenas: este arquivo + [[ADR-240]] + estrutura de Sprints A18 e A19 + entradas de changelog. **Nenhum código de runtime.**

## Não-objetivos

- **Vida / saúde / acidentes pessoais** — schema preparado (discriminated union antecipa), mas extração e UI ficam para V2 (Sprint A20+ ou condicional a demanda).
- **Empresarial PJ** — V2 com co-design [[ADR-236]] cascata fiscal PJ.
- **Sinistro / indenização** — `sinistro_indenizacao_recebida_brl` placeholder em V1 para evitar migration breaking quando integrar com [[ADR-238]] (informes anuais que reportam IR sobre indenização recebida).
- **CRLV histórico (>2 anos)** — só último exercício em V1.
- **Cobertura "saúde" / "vida" embutida em capitalização** — Tokio Marine vende seguros com sorteio + título de capitalização. V1 ignora componente capitalização (entra em V2 com modelagem de patrimônio + sorteio em rendimentos isentos).
- **CBE BACEN sobre seguro internacional** — ADR-238 D1 (Wise) já cobre o equivalente em conta. Seguro internacional fora do escopo.
- **Valor de reconstrução do imóvel** (gap residencial sub-segurado) — V1 mostra LMI nominal incêndio; V2 integra valor de reconstrução via CUB regional.
- **Franquia / LMI ratio** ("proteção efetiva real") — V1 mostra apenas LMI; V2 calcula `franquia / LMI` como sinal de proteção efetiva.

## Riscos

- **R1 — Acoplamento futuro com [[ADR-238]] sobre indenização IR.** Mitigado por `sinistro_indenizacao_recebida_brl` placeholder no schema V1 — evita migration breaking quando integrar.
- **R2 — Cobertura V2 (vida/saúde) precisa campos específicos** (beneficiários, rede credenciada, capital morte). Mitigado por `CoberturaDiscriminated` antecipada já em V1.
- **R3 — Corretor pessoa física existente em mercado.** Mitigado por `CorretorRef.cpf_or_cnpj` aceitar ambos com validador.
- **R4 — Renovação de apólice cria entry duplicado.** Mitigado por D7 (imutável temporal) — query temporal filtra "ativa em data D".
- **R5 — BrasilAPI degradação ou outage.** Mitigado por D5 (lookup assíncrono + cache + `fipe_status=pending_refresh` aceitável).
- **R6 — Cobertura de placa cross-workspace.** Mitigado por tenancy ([[ADR-127]]) — UNIQUE é `(workspace_id, placa)`, não global.
- **R7 — LGPD sobre PDF sintético em golden.** Mitigado por D6: PDFs sintéticos do owner são **anonimizados** (CPF mascarado, valores arredondados, nomes fictícios). Eval real fora do git.

## Alternativas consideradas

- **A1 — `veiculo.apolice_id` (acoplamento inverso).** Rejeitado pelo owner: não escala para seguros que não cobrem bens materiais (vida, saúde, acidentes apontam para pessoa, não bem).
- **A2 — `baseline_patrimonial.veiculos_consolidados[]` como hoje (sem tabela `vehicles`).** Rejeitado: anti-pattern que [[ADR-216]]/[[ADR-225]] vieram consertar para imóveis; identidade canônica sem tabela é divergência de dados.
- **A3 — FIPE SaaS pago (Invertexto, Sintegra).** Rejeitado: BrasilAPI cobre 100% do caso de uso com zero lock-in e custo zero.
- **A4 — Scraping direto do site Fundação FIPE.** Rejeitado: contra TOS, frágil, manutenção alta.
- **A5 — LMI como `Decimal | Literal["valor_referenciado_fipe"]` (union no tipo do valor).** Rejeitado: consumer precisa `isinstance` em todo lugar. Substituído por `lmi_modo` discriminator + valores separados.
- **A6 — Stage por tipo (`extract_crlv`, `extract_apolice`).** Rejeitado: padrão [[ADR-238]] D3 — stage único + despacho por kind em `artifact_key`.
- **A7 — Histórico de apólices via `superseded_by` ou `archived_apolices` table.** Rejeitado: apólice **expira**, não é superseded. Imutável temporal por vigência é semanticamente correto.
- **A8 — `Cobertura` como struct genérica sem discriminator.** Rejeitado: V2 (vida/saúde/acidentes) tem campos heterogêneos. Discriminator antecipa V2 sem migration breaking.

## Entrega — L1 (CRLV-e)

Lane [[A18.l1]] entregue em 5 PRs squash-mergeados em `main` (todos CI verde):

- **P1** [#388](https://github.com/davidrobert/mathoms/pull/388) — migration Alembic `vehicles` (UNIQUE `(workspace_id, placa)`, CHECK RENAVAM ANSI portátil 9-11 dígitos, CHECK `codigo_rfb IN ('21','22','23')`) + `market_rates.reference_month` + `SQLAlchemy` model + invariante `codigo_rfb` imutável.
- **P2** [#391](https://github.com/davidrobert/mathoms/pull/391) — `CRLVPayload` Pydantic V2 strict (regex placa Mercosul+legado, normalização `mode='before'`) + prompt LLM Haiku + `PROMPT_VERSION = "crlv-v1.0.0"` + cache key SHA-256 do PDF.
- **P3** [#412](https://github.com/davidrobert/mathoms/pull/412) — `TypeRule crlv_eletronico` content-first + `DocumentType.comprovante_bem` + migration `adr239vehicles2` ALTER TYPE ADD VALUE (Postgres) / no-op (SQLite).
- **P4** [#414](https://github.com/davidrobert/mathoms/pull/414) — stage `extract_comprovantes_bens` (despacho por `tipo_comprovante`, L1 só `crlv`; raise `NotImplementedError` em outros tipos com mensagem clara V2) + upsert vehicles (identidade imutável; colisão placa↔renavam ≠ → `needs_review`) + telemetria LGPD-safe `mathoms.comprovantes.classified`.
- **P4 parte 2+3** [#416](https://github.com/davidrobert/mathoms/pull/416) — função pura `reconcile_baseline_veiculos` (fuzzy `difflib.SequenceMatcher`, gate triplo `auto_merge ≥ 0.90` + `tiebreaker_gap_min 0.05` + dual threshold `review ≥ 0.75` financial-planner) + runner backend `vehicle_reconciliation_runner.py` + hook em `e15_consolidate.py::main_with_store` + schema bump `baseline_patrimonial.json` (`veiculo_id` opcional retroativo).
- **P5** (este PR) — goldens sintéticos LGPD-safe em `tests/fixtures/llm_golden/crlv_*.json` (moto + carro + zero-km) + 9 testes em `TestCRLVGoldens` + flip ADR `Proposto → Decidido (Sprint A18 L1)` + lane status `shipped`.

**Padrão arquitetural validado:**

- Tabela canônica para identidade cross-source (CRLV + IRPF G02) — replica padrão `real_estate_assets` (ADR-216).
- Identidade imutável (ADR-225) — colisão `placa↔renavam` ≠ vira `needs_review`, não merge automático.
- Reconciliação assíncrona com função pura no `pipeline/domain/services/` + runner backend no `backend/app/services/` (ADR-097 isolation).
- LGPD ADR-231 — telemetria sem PII (placa mascarada, CPF mascarado em Python pós-LLM, valores agregados); LLM nunca retorna CPF.
- Cache LLM idempotente por SHA-256 do PDF + PROMPT_VERSION (ADR-144).
- Schema validation em `DBArtifactStore.write` (ADR-212 PR3) — `informe_base.schema.json` reaproveitado para comprovantes na L1.

**L2 (apólice de seguro) e L3 (FIPE refresh) replicam:** mesmo padrão `tipo_*` polimórfico + classifier content-first + LLM cascata (Haiku → Sonnet) + tabela canônica + reconciliação assíncrona.

**Débito conhecido:**

- UI S4 com disclaimer "Valor atualizado via FIPE (refresh anual)" — bloqueado por L3 (FIPE integration).
- `veiculos_consolidados[]` ainda é fonte de E5 (não substituído por query direta em `vehicles`) — débito que A18 L2/L3 ou Sprint A19 resolve dependendo de prioridade.
- Vehicle não tem `member_key` confiável pós-upload (CPF mascarado por LGPD); blocking por proprietario degrada para "todos candidatos". Resolução em V2 quando associação `vehicle ↔ family_member` for adicionada via UI explícita.

## Entrega — L2 (Apólice polimórfica)

Lane [[A18.l2]] entregue em 5 PRs squash-mergeados em `main` (todos CI verde):

- **P1** [#419](https://github.com/davidrobert/mathoms/pull/419) — `ApolicePayload` Pydantic V2 strict com **Discriminated Union em 2 níveis**: `bens_segurados[]` (veiculo|imovel|pessoa-V2) e `<bem>.coberturas[]` (material|rcfv|vida-V2|saude-V2|acidentes-V2). LMI via `lmi_modo` discriminator (3 modos: valor_fixo | fipe_percentual | primeiro_risco_absoluto) — não union de tipo no valor. `CorretorRef.cpf_or_cnpj` aceita PJ (CNPJ 14) e PF (CPF 11 + SUSEP). Top-level lenient (ADR-238 D2); sub-models strict. PROMPT_VERSION="apolice-v1.0.0". 3 goldens sintéticos LGPD-safe (auto, residencial, combinada).
- **P2** [#420](https://github.com/davidrobert/mathoms/pull/420) — `TypeRule apolice_seguro` content-first (regex Apólice/SUSEP/Cobertura/CNPJs top-5) + migration `adr239apolice` seed top-5 seguradoras (porto, tokiomarine, bradesco_seguros, itau_seguros, zurich) categoria `insurance` (mesma já usada para BrasilPrev em ADR-238) + mapping `_COMPROVANTE_BEM_PREFIXES` ganha "apolice_seguro" / "apolice" (stage único dispatch por tipo).
- **P3** [#422](https://github.com/davidrobert/mathoms/pull/422) — stage `extract_comprovantes_bens` ganha dispatch `tipo_comprovante=apolice` + cascata LLM Haiku→Sonnet (gate triplo D6: `len(bens_segurados) > 1` OU `confidence < 0.7` OU strings "combinada"/"residencial+auto"). Cache key inclui modelo (haiku vs sonnet) preservando idempotência ADR-144. CPFs mascarados em Python pós-LLM (ADR-231 D8); `sinistro_indenizacao_recebida_brl` forçado null (placeholder V1). Artifact key apólice = `apolice_<numero_sanitized>_<vigencia_ano>` (D7 histórico imutável temporal).
- **P4** [#424](https://github.com/davidrobert/mathoms/pull/424) — função pura `reconcile_apolice_bens` + runner backend `apolice_reconciliation_runner.py`. Match estrito por placa (veículo, ADR-225) + match token-set inclusivo em endereço canônico (imóvel, tolera "Apartamento 42" extra de um lado). 4 outcomes: matched / no_candidate / stale_cleared / idempotent_skip. Plumbing em `_persist_processed` apolice path (try/except backend — degrada graceful).
- **P5** [#425](https://github.com/davidrobert/mathoms/pull/425) — 3 goldens V2 placeholder (vida, saude, acidentes) validando que schema antecipa V2 sem migration breaking + flip ADR-239 ganha seção `## Entrega — L2` + lane `A18.l2 → shipped` + changelog entry.

**Padrão arquitetural revalidado (replicar em L3 FIPE refresh):**

- Discriminated Union 2 níveis antecipa V2 (vida/saúde/acidentes) já em V1 — payload aceita sem migration breaking; UI consome quando V2 entrar.
- LMI discriminator (não union de tipo) — consumer não precisa `isinstance` em todo lugar.
- Cascata LLM Haiku→Sonnet com gate explícito (cost-optimized para apólices simples; Sonnet só quando combinada multi-bem).
- Cache key inclui modelo (Haiku vs Sonnet) — re-run com mesmo modelo serve do cache (ADR-144).
- Match imóvel via token-set inclusivo, não fuzzy ratio — preserva rigor sem floats arbitrários.
- Pessoa V2 placeholder em `_reconcile_one_bem` retorna `no_candidate` sem expor pool de `family_members` (LGPD).

**Débito conhecido (L2):**

- UI de proteção (card S_PROTECAO, A19) consome `bens_segurados[].coberturas[]` apenas em V2 — apólice ingerida em V1 fica em DB sem render frontend até A19 mergear.
- Pagador FK `pagador_family_member_id` resolvida apenas quando UI for adicionada (V2) — V1 captura `pagador_cpf_masked` em texto livre mas não vincula a `family_members`.
- Apólice combinada Porto V1: cascata Sonnet dispara em ~30% dos casos onde Haiku confunde LMI/cobertura por bem; gate aceitável (custo Sonnet ~3× Haiku, mas só para combinadas).
