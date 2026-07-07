---
id: ADR-226
type: adr
title: "Desambiguação conta bancária → membro: `account_number` como discriminador, `account_resolver` puro, `is_joint` reservado para V2"
status: Decidido
phase: A12.bank-account-disambig
date: "2026-05-19"
relates_to:
  - "[[ADR-127]]"
  - "[[ADR-137]]"
  - "[[ADR-097]]"
  - "[[ADR-111]]"
  - "[[ADR-146]]"
  - "[[ADR-143]]"
  - "[[ADR-186]]"
  - "[[ADR-215]]"
  - "[[ADR-157]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 226"
  - "bank account member disambiguation"
  - "banco_membro multi-titular"
tags:
  - area/methodology
  - area/persistence
  - area/pipeline
  - area/backend
  - methodology/cerbasi
  - methodology/perini
  - phase/a12
  - status/decidido
  - type/adr
---

> ADR longa (>150 linhas) por design: coordena schema DB + serializer + schema E2/E3 + resolver puro + UI + 4 PRs sequenciais; a interação entre essas camadas precisa de um documento de referência único para sobreviver à execução em PRs separados.

## Contexto

UI `/config` permite cadastrar contas bancárias por membro (`backend/app/models/family_member.py:55`, tabela `bank_accounts`), com 4 campos: `institution_code`, `account_type`, `agency`, `account_number`. O help text declara: "indique em qual membro o pipeline deve considerar cada instituição (extratos, investimentos)".

**Bug latente identificado 2026-05-19.** Três sítios constroem o mapping `banco_membro: dict[str, str]` 1:1:

- [backend/app/services/config_materializer.py:100](../../backend/app/services/config_materializer.py)
- [backend/app/api/config.py:425](../../backend/app/api/config.py)
- [pipeline/stages/extract_members.py:55](../../pipeline/stages/extract_members.py)

```python
banco_membro: dict[str, str] = {}
for m in members:
    for acc in m.accounts:
        banco_membro[acc.institution_code] = m.key   # ← SOBRESCREVE silenciosamente
```

Cenário David + Mariana ambos no Itaú: `banco_membro["itau"]` fica com o **último** processado. Transações do outro são atribuídas ao membro errado em:

- [scripts/e4_categorize.py:330](../../scripts/categorize_transactions.py) — `BANCO_MEMBRO` lookup direto em transação.
- [pipeline/domain/services/investments_consolidator.py:141](../../pipeline/domain/services/investments_consolidator.py) — fallback de membro em posição de investimento.

Sintomas correlatos no mesmo eixo:

- **`titular: string` em E3 schema** ([config/schemas/e3_reconciled.schema.json](../../config/schemas/e3_reconciled.schema.json)) é mono-membro — fatura conjunta David+Mariana atribui tudo a um só. Mesma classe de bug; corrigida na mesma ADR.
- `account_number` e `agency` **são extraídos pelos parsers E2** ([scripts/e2/banks/*.py](../../scripts/e2/banks/)) heterogeneamente — BTG retorna `"12345678"` puro, Itaú/C6 via `extract_account_number` mantém hífens/pontos, Bradesco entrega regex group cru. **Nunca normalizado**, **nunca propagado** ao E3, **nunca consumido** pelo E4. Coleta morta no caminho do dado.
- Não há UNIQUE constraint em `bank_accounts` prevenindo `(workspace_id, institution_code, account_number)` duplicado.
- Stage E1 ([extract_members](../../pipeline/stages/extract_members.py)) ao processar IRPF **reprocessa o JSON inteiro**, podendo sobrescrever cadastros manuais já feitos pelo usuário.
- Não há teste cobrindo multi-membro+mesmo-banco — [tests/test_llm_golden.py:41](../../tests/test_llm_golden.py) é single-member por banco.
- `BANCO_MEMBRO` (uppercase) em [e4_categorize.py:332](../../scripts/categorize_transactions.py) é variável de módulo carregada de JSON em import — formalmente OK enquanto imutável, mas reforça o pattern global; refactor mata isso passando config via DI ([[ADR-111]]).

**Impacto patrimonial (review `financial-planner` 2026-05-19).** ICP brasileiro de alta renda multi-membro **frequentemente** tem múltiplos membros no mesmo banco (concentração regulatória: Itaú/Bradesco/Caixa/Nubank/Inter). Cerbasi (Equilíbrio Familiar) trata "quem ganha, quem gasta, quem investe" como **core**, não nice-to-have — atribuir errado vira feedback perigoso, pior que não dar feedback. Perini (Renda Passiva) depende de titularidade fiscal correta para JCP/dividendos isentos vs tributáveis — bug atual produz relatório **fiscalmente incorreto**. AUVP (Diagrama do Cerrado) tolera consolidação familiar, mas perfil individual de risco (cônjuges com horizontes diferentes) reativa o P0.

**O pior risco é a silenciosa**: usuário não percebe que o relatório mente. Warning honesto é o mínimo ético antes de qualquer fix.

## Decisão

Adotar **cinco mudanças coordenadas** que materializam `account_number` como discriminador real, preservam o boundary `pipeline ↔ backend` ([[ADR-097]]), respeitam `source_tier` ([[ADR-146]]) e reservam schema para conta conjunta (V2 follow-up) sem sobrecarregar V1.

### 1. `account_number` normalizado no boundary (digits-only, sem coluna nova)

Parsers E2 continuam retornando `numero_conta` heterogêneo (compat backward). **Normalização canônica é responsabilidade do resolver**, não do DB nem da UI:

```python
def normalize_account_number(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits or None  # vazio pós-normalização vira None
```

- DB armazena `bank_accounts.account_number` como o usuário digitou (preservar `1234567-8` para exibição).
- Comparação roda sempre via normalização no resolver — `"12.345-6" == "12345-6" == "123456"` todos viram `"123456"`.
- Custo: ~10ms regex por transação no E4; desprezível.
- Documente em docstring de `BankAccount.account_number` + `pipeline/domain/services/account_resolver.py` ([[ADR-143]] rules-as-code).

**Por que não coluna `account_number_normalized`**: backfill em DB existente; duplicidade de fonte; index sobre expressão (`regexp_replace`) é equivalente em PostgreSQL e dispensa coluna ([[ADR-097]] princípio de simplicidade).

### 2. Schema `family_members.json` ganha `contas[]` aditivo; legado `banco_membro` permanece como fallback degradado

Em vez de quebrar o contrato existente, **aditivo**:

```json
{
  "membros": { "david": {...}, "mariana": {...} },
  "titular": "david",

  "banco_membro": {       // mantido p/ compat — fallback quando account_number ausente
    "itau": "mariana"     // último-ganha; intencional fallback only
  },

  "contas": [             // novo, primário
    {"institution_code": "itau", "account_number_norm": "123456", "agency": "1234", "account_type": "corrente", "member_key": "david"},
    {"institution_code": "itau", "account_number_norm": "789012", "agency": "1234", "account_type": "corrente", "member_key": "mariana"},
    {"institution_code": "nubank", "account_number_norm": null,   "agency": null,   "account_type": "corrente", "member_key": "mariana"}
  ]
}
```

`config_materializer.serialize_family_members` ([backend/app/services/config_materializer.py:56](../../backend/app/services/config_materializer.py)) gera ambos; consumidores leem `contas[]` primeiro, caem para `banco_membro` quando `account_number` da transação é `None` ou ambíguo.

### 3. Resolver puro em `pipeline/domain/services/account_resolver.py`

Função pura, sem I/O, ≤40 linhas, testável isoladamente:

```python
@dataclass(frozen=True)
class AccountResolution:
    member_key: str | None
    confidence: Literal["strict", "fallback_bank", "ambiguous", "unknown"]
    matched_account: ContaConfig | None

class AccountResolver:
    def __init__(self, contas: list[ContaConfig], banco_membro: dict[str, str]):
        self._contas = contas
        self._banco_membro = banco_membro
        self._by_bank_and_num = {
            (c.institution_code, c.account_number_norm): c
            for c in contas
            if c.account_number_norm is not None
        }
        self._by_bank = defaultdict(list)
        for c in contas:
            self._by_bank[c.institution_code].append(c)

    def resolve(self, institution_code: str, account_number_raw: str | None) -> AccountResolution:
        norm = normalize_account_number(account_number_raw)
        # 1. Match estrito (banco + account_number normalizado)
        if norm is not None:
            hit = self._by_bank_and_num.get((institution_code, norm))
            if hit is not None:
                return AccountResolution(hit.member_key, "strict", hit)
        # 2. Fallback: banco único membro
        bank_contas = self._by_bank.get(institution_code, [])
        if len(bank_contas) == 1:
            return AccountResolution(bank_contas[0].member_key, "fallback_bank", bank_contas[0])
        # 3. Ambíguo: múltiplos membros no banco, sem account_number na transação
        if len(bank_contas) > 1:
            return AccountResolution(None, "ambiguous", None)
        # 4. Unknown: banco não cadastrado
        return AccountResolution(None, "unknown", None)
```

Reusa em [e4_categorize.py:330](../../scripts/categorize_transactions.py), [investments_consolidator.py:141](../../pipeline/domain/services/investments_consolidator.py) e — opcionalmente — em E1 quando merge idempotente.

**Em `pipeline/domain/services/`** porque é regra de domínio pura ([[ADR-097]] D3). **Não importa SQLAlchemy**.

### 4. Schema E2/E3 propaga `account_number` normalizado por transação; `titular: string` vira `titulares: list[str]`

Schema bump em [config/schemas/e3_reconciled.schema.json](../../config/schemas/e3_reconciled.schema.json):

- Top-level: `account_number: ["string", "null"]` aditivo opcional. `titular` deprecated (mantém leitura por compat); `titulares: array[string]` primário (≥1 string; conta conjunta tem 2+).
- Transação (`transacoes[].`): `account_number: ["string", "null"]` aditivo opcional.

Parsers E2 ([scripts/e2/common.py:344](../../scripts/e2/common.py) `make_result_template` + helper compartilhado `account_normalization.py`) normalizam ao gravar — formato canônico digits-only — e propagam para E3 reconciliação.

`MATHOMS_PIPELINE_SCHEMA_MODE=strict` em CI valida o bump aditivo.

### 5. E1 (extract_members) opera em modo **merge idempotente**, respeitando `source_tier` ([[ADR-146]])

[pipeline/stages/extract_members.py](../../pipeline/stages/extract_members.py) deixa de sobrescrever o JSON inteiro. Para cada `(workspace_id, institution_code, account_number_norm)` extraído do IRPF (LLM):

- **Existe match exato no DB?** → skip + log INFO `extract_members.skip_existing`. Cadastro manual (`source_tier` editorial) sempre vence IRPF/LLM.
- **Existe `(workspace_id, institution_code)` mas account_number difere?** → **append** nova `BankAccount` para o mesmo `member` quando `member_key` resolve, ou para titular default quando ambíguo + warning.
- **Member do IRPF não casa com `family_members.cpf_encrypted` (após decrypt)?** → cria com `role="dependente"` + warning para review humano.

Sem isto, qualquer fix em V1 regride no próximo upload de IRPF do usuário.

### Bonus: investments_consolidator deixa de **chutar silenciosamente**

[investments_consolidator.py:141](../../pipeline/domain/services/investments_consolidator.py) passa a usar `AccountResolver.resolve(institution_code, None)`. Quando `confidence in {"ambiguous", "unknown"}`, posição é marcada `needs_review=true` com `motivo: "membro indeterminado — múltiplas contas no mesmo banco sem identificador"`. UI mostra `needs_review` no card do relatório (financial-planner: "fiscal e metodologicamente falso enviar a cliente sem disclaimer").

### Bonus: UNIQUE constraint em DB com normalização

Migration nova ([[ADR-146]] família):

```sql
ALTER TABLE bank_accounts ADD COLUMN workspace_id UUID NULL;
-- backfill:
UPDATE bank_accounts ba SET workspace_id = (
  SELECT fm.workspace_id FROM family_members fm WHERE fm.id = ba.member_id
);
ALTER TABLE bank_accounts ALTER COLUMN workspace_id SET NOT NULL;

CREATE UNIQUE INDEX CONCURRENTLY uq_bank_account_workspace_inst_num
  ON bank_accounts (workspace_id, institution_code, regexp_replace(account_number, '\D', '', 'g'))
  WHERE account_number IS NOT NULL;
```

`workspace_id` denormalizado em `bank_accounts` (pattern já comum em outras tabelas filhas neste repo). Index parcial só quando `account_number IS NOT NULL` — preserva legacy NULL sem rompimento. UI bloqueia colisão antes de hit DB.

### Reservar `is_joint` + `co_titulares` no schema **sem implementar V1**

Schema `BankAccount` ganha:

- `is_joint: bool DEFAULT FALSE NOT NULL` — flag conta conjunta.
- `co_titulares: JSONB NULL` — lista de `member_id` quando `is_joint=true`. Não popular em V1; default `NULL`.

V1 **não rateia** transações de conta conjunta — `member_id` (titular principal) continua único receptor. V2 (ADR follow-up) ativa `co_titulares` + `default_split` editorial 50/50 Cerbasi-style.

**Por que reservar agora**: evita migration breaking em V2; schema pronto custa ~5 linhas; benefício (compat forward + sinaliza intenção) é grande.

## Alternativas consideradas

- **(B) Detectar colisão e bloquear cadastro** — warning honesto, força usuário a inventar `institution_code` distinto (e.g., `itau_pf_david`). **Rejeitado**: quebra `institution_catalog` ([[ADR-137]] — `institution_code` mapeia a entidade canônica). É só tapa-buraco; não suporta o caso de uso real.
- **(C) Esconder UI de contas para workspace de 1 membro** — esconde fricção mas mascara o bug quando família cresce; rejeitado por `financial-planner` ("família cresce; fricção da primeira vez ≪ desconfiança ao descobrir relatório errado").
- **(D) DB-lookup via `ConfigStore` injetado no E4** — `pipeline/**` não importa SQLAlchemy ([[ADR-097]]); workaround via `WorkspaceContext.config_overrides` adiciona dependência runtime sem ganho funcional sobre o JSON materializado. **Rejeitado**: materialização preserva simetria com `pipeline/adapters/config_parsers.py:parse_family_members` (parser puro).
- **(E) Coluna `account_number_normalized`** em `bank_accounts` — duplica fonte de verdade, exige backfill, complica updates. **Rejeitado** em favor de index sobre expressão (`regexp_replace`) — PostgreSQL nativo.
- **(F) Conta conjunta V1 com rateio proporcional 50/50** — escopo cresce 2x (mexe em E4 rateio + E5 agregação + IRPF reconciliation + UI). **Adiado** para V2 ADR follow-up; reserva de schema em V1 destrava sem bloquear.
- **(G) Não fazer nada, só warning e roadmap** — bug silencioso continua produzindo relatórios fiscalmente incorretos. `financial-planner` veto: "não enviável a cliente de planejamento sem fix".

## Consequências

**Positivas**

- ✅ Cenário canônico ICP (casal mesmo banco) deixa de produzir relatório errado. Transações vão pro membro certo.
- ✅ Schema E3 ganha `account_number` por transação — destrava agregações futuras por conta (cash flow por conta, alocação por veículo).
- ✅ Schema E3 ganha `titulares: list` — destrava conta conjunta sem nova migration de schema em V2.
- ✅ `account_resolver` puro reusável em E4, InvestmentsConsolidator, E1, qualquer card futuro. Função única de truth.
- ✅ E1 merge idempotente preserva cadastro manual ([[ADR-146]] `source_tier`) — usuário não perde dados ao re-upload IRPF.
- ✅ `needs_review` explícito em ambiguidade — silenciosa morre. Disclaimer honesto no card.
- ✅ Schema `is_joint` reservado destrava V2 sem migration breaking.
- ✅ Compat backward total: `banco_membro` permanece como fallback; goldens single-member não regridem.

**Negativas**

- ⚠️ 4 PRs sequenciais em ~5-6d eng. Toca E2 (heterogêneo entre parsers), E3 (schema bump aditivo), E4, E1, config_materializer, UI. Surface area larga.
- ⚠️ Schema bump em E3 exige update de goldens (`make update-openapi-snapshot` para endpoints que expõem schema; aditivo, baixo risco de quebra).
- ⚠️ Coluna `workspace_id` denormalizada em `bank_accounts` adiciona invariante a manter (sincronia com `family_members.workspace_id`). Mitigado: FK CASCADE + check em service-layer + denormalização padrão do repo.
- ⚠️ V1 não resolve conta conjunta — workaround manual (atribuir a 1 membro, ajuste editorial no relatório). Documentar em FAQ até V2.

**Riscos**

| Risco | P | Mitigação |
|---|---|---|
| Schema bump aditivo quebra parser legado em workspace antigo | P1 | `MATHOMS_PIPELINE_SCHEMA_MODE=strict` valida; goldens single-member preservados intactos; aditivo é leitura tolerante. |
| E1 merge idempotente regride: re-upload IRPF não atualiza nada quando esperado | P1 | Teste `test_extract_members_idempotent` cobre re-run; `source_tier=editorial` (cadastro manual) sempre vence; IRPF só preenche gaps. |
| Heterogeneidade entre parsers E2 deixa `account_number` `None` em algum banco | P1 | Helper compartilhado `account_normalization.normalize_or_none()` + audit em PR2 percorre 11 parsers; gate de teste por banco. |
| UNIQUE com normalização rejeita row legado válido | P2 | Partial index só sobre `account_number IS NOT NULL`; NULL preservado; UI permite leave-blank. |
| Ambiguidade vira ruído (muitos `needs_review`) | P2 | Telemetria `account_resolver_fallback_total{confidence}` — se >10% workspaces piloto têm ambíguo, sprint follow-up melhora UX de declaração. |
| `BANCO_MEMBRO` global em `e4_categorize.py:332` viola [[ADR-111]] se ficar mutável após este refactor | P1 | Resolver recebe config via DI no PR3; global some por construção. |
| Fatura de cartão (E2-faturas) não tem `account_number` — tem `final_cartao` | P2 | Out-of-scope V1; documentado em §Follow-ups; fallback `banco_membro` cobre 95% do ICP. |

## Bugs latentes correlatos (resolvidos ou documentados)

1. **`titular: string` em E3 schema** — incluído nesta ADR (§4): vira `titulares: list[str]`. Conta conjunta deixa de perder titular.
2. **`BANCO_MEMBRO` global em `e4_categorize.py:332`** — resolvido por construção quando resolver recebe config via DI (§3 + PR3).
3. **Faturas de cartão sem `account_number`** — documentado out-of-scope V1; `final_cartao` entra em ADR futura quando ICP exigir (raro).
4. **Investments sem `numero_conta` em notas de corretora** — fallback `banco_membro` v1 continua cobrindo; brokers (XP, BTG) normalmente têm 1 conta por CPF; o caso multi-membro+mesmo-broker é menos comum (CPFs distintos separam naturalmente nas notas).
5. **Conta de filho menor** (titular formal ≠ operador) — V2 follow-up; estrutura `co_titulares` reservada cobre.

## Gates

- **Migration Alembic** `<rev>_bank_accounts_workspace_id_and_unique.py`: adiciona `workspace_id NOT NULL` (com backfill), `is_joint BOOL DEFAULT FALSE`, `co_titulares JSONB NULL`, partial unique index `CONCURRENTLY` sobre `(workspace_id, institution_code, regexp_replace(account_number, '\D', '', 'g')) WHERE account_number IS NOT NULL`. Downgrade reversível em estrutura (dados de overrides perdidos via DROP COLUMN documentado).
- **Schema E3 bump** ([config/schemas/e3_reconciled.schema.json](../../config/schemas/e3_reconciled.schema.json)): `account_number` opcional top-level e em `transacoes[]`; `titulares: array[string]` aditivo. `MATHOMS_PIPELINE_SCHEMA_MODE=strict` valida em CI. `make update-openapi-snapshot` se algum endpoint expõe a estrutura.
- **`account_resolver.resolve()` puro** em `pipeline/domain/services/account_resolver.py`, ≤40 linhas, sem I/O. Teste unitário `tests/unit/pipeline/test_account_resolver.py` cobre 8 cases: strict match, fallback_bank (1 membro), ambiguous (2+ membros sem account_number), unknown banco, account_number normalização (5 variações), `None` graceful.
- **Goldens multi-membro** novo em `tests/test_e4_golden_multi_member.py` (ou similar) com fixture Itaú-David + Itaú-Mariana — **vermelho hoje**, verde no PR3. Sem este golden, regressão silenciosa volta.
- **Goldens single-member existentes verdes** (`tests/test_llm_golden.py:41`, `test_e3/e4/e5_golden_execution.py`) — paridade backward.
- **Teste idempotência E1** em `tests/test_extract_members_idempotent.py`: 2× sobre mesmo IRPF não duplica `bank_accounts`; `source_tier=editorial` (manual) vence IRPF/LLM.
- **Teste migration backfill** em `backend/tests/test_migration_bank_accounts_workspace_id.py`: backfill multi-workspace, NOT NULL após backfill, partial index criado, idempotência em re-up.
- **Teste normalização account_number** em `tests/unit/scripts/test_account_normalization.py`: cobertura por banco (11 parsers); helper compartilhado, mesmo input canônico independente do parser.
- **UI bloqueia colisão**: ao salvar `BankAccount`, frontend valida UNIQUE local (`useEffect` + check) + backend retorna 409 com mensagem clara quando UNIQUE viola.
- **Telemetria** `mathoms.account_resolver.resolve_total{confidence=strict|fallback_bank|ambiguous|unknown}` via [backend/app/core/logging.py](../../backend/app/core/logging.py) (estrutura pós [[ADR-110]]).
- **Pre-popular UI a partir de E1/IRPF** (financial-planner item): quando `extract_members` (E1) já rodou, UI de `/config` "Contas bancárias" mostra contas extraídas como pre-fill, usuário confirma/corrige em vez de digitar do zero.

## Implementação

Lane planejada em **Sprint A12** (`A12.bank-account-disambig`). 4 PRs sequenciais, ~5-6d eng total em ~2 semanas calendário.

| PR | Conteúdo | Effort | Gate principal |
|---|---|---|---|
| **PR1** | Migration: `workspace_id` denormalizado em `bank_accounts` (backfill + NOT NULL), `is_joint`/`co_titulares` reservados; serializer `config_materializer` gera `contas[]` aditivo + parser `pipeline/adapters/config_parsers.py` constrói `account_map`; UI bloqueia UNIQUE em-app (sem partial index DB ainda) | ~1.5d | Backfill staging completo + zero break em goldens single-member |
| **PR2** | E2 normaliza `account_number` em `account_normalization.py` compartilhado + 11 parsers atualizados; E3 propaga `account_number` por transação + `titulares: list`; schema E3 bump aditivo; `make update-openapi-snapshot` | ~2d | Schema strict mode verde; goldens single-member verdes; normalização canônica testada por banco |
| **PR3** | `account_resolver.py` puro + DI no E4 (`BANCO_MEMBRO` global some), InvestmentsConsolidator e E1 (merge idempotente); **golden multi-membro novo verde**; `needs_review` em ambiguidade investments | ~2d | Golden multi-membro verde; golden single-member verde (paridade); teste idempotência E1 verde |
| **PR4** | `CREATE INDEX CONCURRENTLY` partial unique no DB; backend 409 conflict em colisão; UI mensagem clara + pre-fill IRPF; telemetria `account_resolver.resolve_total{confidence}`; ADR-226 flippa `Proposto` → `Decidido (A12.bank-account-disambig)` | ~1d | Index criado sem lock visível; telemetria emitindo; fallback rate em workspaces piloto monitorado |

**Ordem obrigatória:** PR1 → PR2 → PR3 → PR4. PR1+PR2 são aditivos (zero risco runtime); PR3 muda comportamento (gate canary opcional se sre-devops pedir); PR4 fecha contrato.

**Branch prefix:** `agent/bank-account-disambig-pr<N>/<yyyyMMdd-HHmm>`.

## Follow-ups (fora do escopo V1)

- **V2 ADR — Conta conjunta com rateio proporcional**: ativa `co_titulares` + `default_split: {david: 0.5, mariana: 0.5}` editável; aplica a transações (rateio fluxo) mas **não** a investimentos (titularidade fiscal Perini/IRPF). Disparado quando 5%+ workspaces piloto reportam conta conjunta.
- **Faturas de cartão multi-titular**: `final_cartao` como discriminador alternativo quando ICP exigir.
- **UI merge human-in-loop**: quando E1 detecta cadastros divergentes vs IRPF, oferece review explícito. Complementa merge idempotente do §5.
- **Telemetria fallback rate → descontinuar v1**: se `mathoms.account_resolver.resolve_total{confidence=strict}/total > 95%` por 4 semanas, sprint follow-up remove `banco_membro` legado do schema `family_members.json`.

## Referências

- [[ADR-127]] — E1 `extract_members` (LLM extrai contas do IRPF; merge idempotente respeita `source_tier`).
- [[ADR-137]] — `institution_catalog` (`institution_code` canônico; não inventar variantes).
- [[ADR-097]] — Boundary `pipeline ↔ backend` (resolver puro em `pipeline/domain/services/`, sem SQLAlchemy).
- [[ADR-111]] — Stateless rigoroso (`BANCO_MEMBRO` global some via DI no resolver).
- [[ADR-146]] — `source_tier` hierarchy (editorial manual > IRPF LLM; E1 merge respeita).
- [[ADR-143]] — Rules-as-code (normalização account_number documentada em docstring + ADR canônica).
- [[ADR-186]] — Override sticky pattern (precedente: manual sempre vence quando declarado).
- [[ADR-215]] — `workspace_property_overrides` (pattern de partial unique + denormalização de workspace_id).
- [[ADR-157]] — E1.6 IRPF full (fonte upstream de contas extraídas; pre-fill UI).
- Co-design 2026-05-19: `data-engineer` (schema E3 aditivo + normalização no boundary + workspace_id denormalizado + partial index sobre expressão + bugs latentes correlatos), `financial-planner` (Cerbasi/Perini/AUVP — atribuição correta é core; conta conjunta é regra no ICP; warning bloqueante > silenciosa).
- Diagnóstico: investigação `/config` Mathoms 2026-05-19, sessão David Robert.

## Status — Decidido (A12.bank-account-disambig)

Lane completa em 4 PRs:

- **PR1** absorvido em PR2 squash (#337) — migration `workspace_id` + `is_joint`/`co_titulares` + serializer aditivo + UI in-app UNIQUE
- **PR2** ([#337](https://github.com/davidrobert/mathoms/pull/337)) — E2→E3 propaga `account_number` + `titulares: list`
- **PR3** ([#339](https://github.com/davidrobert/mathoms/pull/339)) — `account_resolver` puro + DI no E4/InvestmentsConsolidator/E1
- **PR4** — partial unique index `CONCURRENTLY` + 409 conflict no backend + telemetria `mathoms.account_resolver.resolve` + flip ADR

FAQ produto em `docs/reference/FAQ_bank_account_member.md`.
