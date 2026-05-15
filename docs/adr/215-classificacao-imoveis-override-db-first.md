---
id: ADR-215
type: adr
title: "Classificação de uso econômico de imóveis via override DB substitui `residencia_principal_keyword`"
status: Proposto
phase: A12
date: "2026-05-15"
relates_to:
  - "[[ADR-145]]"
  - "[[ADR-142]]"
  - "[[ADR-143]]"
  - "[[ADR-134]]"
  - "[[ADR-137]]"
  - "[[ADR-186]]"
  - "[[ADR-157]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 215"
  - "Imovel classification override"
  - "Residência principal DB-first"
tags:
  - area/methodology
  - area/pipeline
  - area/persistence
  - area/report
  - methodology/cerbasi
  - methodology/perini
  - phase/a12
  - status/proposto
  - type/adr
---

> ADR longa (>150 linhas) por design: a decisão toca pipeline (E1.6 schema + E1.5c identity), domínio (`patrimonio_calculator._split_imoveis`), schema DB (tabela nova + coluna em workspaces), UX (pós-upload IRPF + MembersTab) e invariante de produto ([[ADR-145]] taxonomia, [[ADR-142]] anti-dupla-contagem em IF). Split produziria peças órfãs sem o contrato cruzado.

## Contexto

[[ADR-145]] fixou as **7 categorias canônicas** da composição patrimonial — entre elas `cat_1` "Residência própria" separada de `cat_2` "Imóveis investimento". A separação é metodologicamente correta (Perini: residência é improdutiva, fora do denominador de IF; Cerbasi: patrimônio de uso ≠ patrimônio de renda; AUVP: imóveis fora do Diagrama). [[ADR-142]] adiciona o invariante de exclusão mútua: cat_2 pode entrar em `investivel_efetivo` **se** `imoveis_no_if=true` e yield líquido > TRS.

A regra que separa cat_1 de cat_2 hoje vive em `pipeline/domain/services/patrimonio_calculator.py::_split_imoveis`: cada imóvel do titular casa **substring lowercase** contra `family_members.<titular>.extra.residencia_principal_keyword` (string em `extra` JSONB). Sem keyword setada → nenhum imóvel é classificado como residência → cat_1 = R$ 0,00 e tudo cai em cat_2.

Três problemas observados em produção (workspace dogfood `5@5.com`, sessão 2026-05-15):

1. **Sem UI.** O campo só é editável via Import/Export JSON ou SQL direto. Onboarding/MembersTab não captura. Usuário razoavelmente espera que upload de IRPF (com 5 imóveis, sendo 1 casa com endereço explícito "RUA TASSO DA SILVEIRA, 61 - SP") classifique sozinho — não acontece. R$ 996.821 de residência caiu em cat_2 silenciosamente.
2. **Acoplamento errado.** `residencia_principal_keyword` mora em `family_members.<titular>.extra` mas a residência é da **família**, não do titular. Casal em comunhão tem 1 residência declarada em 2 IRPFs distintos; o modelo não tem dedup nem owner correto.
3. **Modelo binário insuficiente.** "Residência sim/não" não cobre casos reais que afetam o cálculo de IF: imóvel ocupado por familiar (filho/mãe) — não rende mas não é residência principal; terreno improdutivo declarado código 13 — não rende mas hoje cai em cat_2 e infla `investivel_efetivo` quando `imoveis_no_if=true` (violando o espírito de [[ADR-142]]); sala comercial vaga vs locada. Hoje tudo binário "residência ou investimento" corrompe o sinal econômico real.

**Auditoria adjacente.** Schema E1.6 (`extract_irpf_full`, [[ADR-157]]) extrai `bens_direitos[]` com `codigo`, `descricao`, `valor_brl`, `membro_key`, `ano` — mas **não extrai** o endereço do contribuinte ("Dados do Contribuinte" no PDF IRPF). A seção tem endereço completo de correspondência fiscal, dado adjacente, custo marginal LLM ≈ 0.

## Decisão

Adotar **três mudanças coordenadas** que substituem `residencia_principal_keyword` por modelo DB-first:

### 1. Enum `classification` por imóvel (não-binário)

Cada item de imóvel ganha classificação categorial via enum:

```
classification ∈ {
  residencia_principal,    # cat_1 — sempre fora de investivel_efetivo
  uso_pessoal,             # casa de praia, imóvel onde filho/mãe mora — não-gerador
  locado,                  # gera aluguel — entra em cat_2; respeitado por [[ADR-142]]
  comercial,               # sala/galpão — entra em cat_2 se locado/produtivo
  especulacao,             # terreno vago, lote — não-gerador, nunca em investível efetivo
  desconhecido,            # default antes da classificação do usuário
}
```

`is_residencia_principal` continua disponível como **constraint derivado**: `classification = 'residencia_principal'`. Partial unique index garante 1 row com essa classificação por workspace (regra de produto: "residência principal" é única).

**Por que enum > boolean:** sucessores de [[ADR-145]] (cat_2 "Imóveis Investimento") e [[ADR-142]] (`imoveis_no_if`) ganham granularidade real. Cat_2 deixa de englobar terreno improdutivo. `investivel_efetivo` passa a filtrar por `classification ∈ {locado, comercial}` quando `imoveis_no_if=true`, não por "tudo que não é residência".

**Renomeia cat_2.** "Imóveis Investimento" → **"Imóveis de Renda"**. Comunica o critério verdadeiro (geração de caixa) em vez do critério herdado por exclusão (~residência). Label visual no relatório muda; `template_key` interno (`imoveis_investimento`) é **estável** ([[ADR-145]] proíbe rename de key).

### 2. Override mora em `workspace_property_overrides` (DB)

Nova tabela espelha o padrão de [[ADR-137]] (`workspace_category_overrides`) e [[ADR-186]] (override-de-transação-promovido-a-regra):

```sql
CREATE TABLE workspace_property_overrides (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  property_id UUID NOT NULL REFERENCES property_identity(id),
  classification VARCHAR(20) NOT NULL,  -- enum acima
  override_source VARCHAR(20) NOT NULL, -- 'user_manual' | 'fuzzy_match_accepted' | 'migration_keyword'
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  created_by_user_id UUID REFERENCES users(id),
  CONSTRAINT uq_workspace_property UNIQUE (workspace_id, property_id),
  CONSTRAINT chk_classification CHECK (
    classification IN ('residencia_principal','uso_pessoal','locado','comercial','especulacao','desconhecido')
  )
);

CREATE UNIQUE INDEX idx_workspace_one_residencia_principal
  ON workspace_property_overrides (workspace_id)
  WHERE classification = 'residencia_principal';
```

`workspaces` ganha coluna `residencia_status VARCHAR(20) NOT NULL DEFAULT 'undeclared'` (`owned | rented | undeclared`) — captura o estado tripartite que [[ADR-145]] não modela (usuário aluga, não tem imóvel — diferente de "tem imóvel mas não classificou ainda"). Quando `rented`, UI esconde a linha "Residência" no relatório; quando `undeclared`, mostra `—` + CTA. Quando `owned`, exige exatamente 1 row `residencia_principal`.

**Por que tabela nova, não `family_members.extra` nem item do baseline:**

- `family_members.extra` é exatamente o que estamos saindo — keyword frágil acoplada ao titular (não à família) já provou o modelo errado.
- Baseline E1.5c (`baseline_patrimonial`) é **derivado** — regenerado a cada novo IRPF. Persistir override de usuário dentro do artefato derivado quebra idempotência do stage (igual ao problema que [[ADR-186]] §P3 resolveu para categorização).
- Tabela separada com FK em `property_identity` segue o padrão diff-por-workspace já consagrado.

### 3. Identidade estável: `property_identity` + matching humano-no-loop

`property_id` UUID estável **cross-IRPFs** vive em tabela nova:

```sql
CREATE TABLE property_identity (
  id UUID PRIMARY KEY,
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  titular_key VARCHAR(64) NOT NULL,
  codigo_rfb VARCHAR(4) NOT NULL,         -- 11 = apto, 12 = casa, 13 = terreno, etc.
  endereco_canonical VARCHAR(255),        -- regex-extracted da descricao, normalizado
  first_seen_year INTEGER NOT NULL,
  descricao_sample TEXT,                  -- amostra original para auditoria
  created_at TIMESTAMPTZ NOT NULL
);
```

Consolidador E1.5c (`consolidate_baseline`) emite imóveis com `property_id`. Quando casa IRPF novo:

1. Normaliza descrição (lowercase, sem acento, expande `av/avenida` `r/rua`, remove `apto/ap`).
2. Tenta extrair `(rua, numero)` via regex.
3. Busca match em `property_identity` do workspace por `(titular_key, codigo_rfb, endereco_canonical)`.
4. **Match encontrado** → reusa `property_id`. **Sem match ou ambíguo** → cria nova row + sinaliza `low_confidence` para a UI resolver merge manual.

Hash determinístico foi **descartado** (objeção do `data-engineer`, sessão 2026-05-15): correção monetária e variação LLM de descrição (`"APARTAMENTO"` vs `"APTO"` vs `"APTO 812"`) quebram o hash entre anos. Para escala atual (~5 IRPFs/workspace × dezenas de workspaces), 1 clique humano de merge no primeiro ano de cada imóvel é barato e elimina classe inteira de bug silencioso (override apontar para imóvel errado entre anos).

### 4. Endereço do contribuinte no schema E1.6 como *signal*

`config/schemas/e16_irpf_full.schema.json` ganha campo aditivo opcional:

```yaml
contribuinte:
  endereco: { type: ["string","null"], description: "Endereço de correspondência fiscal da seção 'Dados do Contribuinte'. NÃO É PROVA DE RESIDÊNCIA — pode ser PJ, casa dos pais, corretora. Serve apenas para pré-seleção heurística." }
```

Pydantic em `pipeline/llm/schemas/e16_irpf_full.py`: `Optional[str] = None`. Prompt em `pipeline/llm/prompts/e16_irpf_full.py` pede explicitamente extração da seção "Dados do Contribuinte". **Lazy fill aceito** — IRPFs existentes só populam quando re-rodam E1.6; UI degrada para "lista todos sem pré-seleção" quando campo é `None`.

### 5. Heurística fuzzy é *assist*, nunca decide sozinha

Match: `rapidfuzz.fuzz.token_set_ratio` sobre `(endereco_contribuinte_normalizado, descricao_normalizada)` com regex de pré-processamento extraindo `(via, numero)` quando possível.

Thresholds:

| Score | Comportamento UI |
|---|---|
| ≥92 | Pré-marca + badge "sugerida pelo seu endereço no IRPF" + **usuário confirma** |
| 80-91 | Sugere (destaque visual) + usuário confirma |
| <80 | Sem sugestão, lista todos |

**Nunca auto-aplica sem confirmação humana** — pré-seleção mal-calibrada é pior que sem pré-seleção. Eval set parametrizado (≥20 pares positivos/negativos) trava threshold em CI; tuning empírico, não por feeling.

### 6. `_split_imoveis` vira read-time / lazy

`patrimonio_calculator._split_imoveis` torna-se função pura:

```python
def split_imoveis(
    imoveis: list[ImovelBaseline],
    overrides: dict[UUID, Classification],
) -> CompositionSplit: ...
```

A view do relatório (`/reports/[id]`) busca overrides do workspace + baseline E1.5c e faz o split na hora. Artifact E5 (`analyze_finances`) deixa de armazenar a split fechada; armazena a lista de imóveis com `property_id`. **Não invalida E5 inteiro ao trocar classificação** — recompute parcial via service-layer quando golden de paridade exigir contrato estável no E5.

**Trade-off honesto:** muda o contrato do payload E5 (`composicao_patrimonial.imoveis.{residencia,investimento}` deixa de ser campo materializado). Goldens E5 precisam refletir (lane operacional resolve).

## Alternativas consideradas

- **(B) Heurística fuzzy decide sozinha (sem confirmação).** Descartada — endereço brasileiro é frágil (abreviações, acentos, "Av./Avenida", número às vezes ausente). Funciona em ~70% e falha em silêncio em 30%, pior que pedir confirmação.
- **(C) `is_residencia_principal: bool` no item do baseline.** Descartada — quebra idempotência de stage derivado (E1.5c regenera; ou perde flag, ou consolidator lê estado mutável). Mesmo problema que [[ADR-186]] já resolveu separando override em tabela própria.
- **(D) Manter `residencia_principal_keyword` e só adicionar UI.** Descartada — mantém acoplamento errado (titular vs família), não resolve o caso de duplicação em casal/comunhão, não suporta enum (uso_pessoal vs especulacao), e endereço-keyword segue tão frágil quanto descrição-keyword.
- **(E) Hash determinístico para `property_id`.** Descartada — variação LLM + correção monetária + descrição livre quebram hash entre anos. Bug silencioso de override apontando para imóvel errado é pior que o atual.
- **(F) Tabela `workspace_counters`-like para residência.** Descartada — não é problema de sequência; é problema de classificação multi-valor por item.

## Consequências

**Positivas:**

- ✅ Caso `5@5.com` (e classe inteira de bug) resolvido: usuário marca explicitamente; sticky entre re-uploads de IRPF.
- ✅ Cat_2 "Imóveis de Renda" passa a ter critério econômico verdadeiro; terreno improdutivo sai do `investivel_efetivo` quando `imoveis_no_if=true` (consistente com espírito de [[ADR-142]]).
- ✅ Casal/comunhão: dedup por endereço no consolidador E1.5c; override é per-workspace, não per-titular.
- ✅ Endereço IRPF como signal extraído uma vez vira reuso para futuras features (KYC, comprovante de residência, alocação geográfica de patrimônio).
- ✅ Padrão DB-first override consistente com [[ADR-134]]/[[ADR-137]]/[[ADR-186]].
- ✅ Sem UI atual; nova UI é additive (pós-upload + MembersTab), não muda fluxo existente.

**Negativas:**

- ⚠️ Mudança breaking no contrato do payload E5 (`composicao_patrimonial.imoveis.*`). Goldens precisam atualizar; lane operacional cuida.
- ⚠️ Migration do legado `residencia_principal_keyword` para `workspace_property_overrides` exige matching de keyword contra descrição em E1.5c — workspaces sem IRPF processado ficam com `residencia_status='undeclared'` até primeiro upload. Aceito.
- ⚠️ Enum de 6 valores aumenta superfície cognitiva no UX. Mitigação: UX só pergunta classificação detalhada quando relevante (residência principal é a única pergunta obrigatória; restante vira "investimento" default com botão "refinar").
- ⚠️ `property_identity` com baixa confiança exige 1 clique de merge humano no primeiro ano. Aceito como custo de evitar bug silencioso.

**Riscos:**

| Risco | Mitigação |
|---|---|
| Migration do legado quebra workspace com keyword exótica | Script idempotente com dry-run; workspaces sem match viram `undeclared`, usuário re-classifica via nova UI. Audit pré-merge documenta casos. |
| Heurística fuzzy mal-calibrada gera má pré-seleção | Eval set parametrizado ≥20 pares trava threshold em CI; threshold ≥92 ainda exige confirmação humana — sem auto-aplica. |
| Cutover de payload E5 quebra renderer/relatório | Lane operacional faz read-time lazy em paralelo com payload antigo (feature flag); cutover quando goldens passam. |
| Casal com 2 residências reais (caso raro: cada um com casa antes do casamento, mantidas como uso pessoal) | Modelo aceita: 1 `residencia_principal` (família escolhe) + N `uso_pessoal`. Documentado no copy da UI. |
| Imóvel financiado com saldo devedor distorce patrimônio bruto | Fora do escopo desta ADR. Follow-up: `valor_mercado` + linkagem `saldo_financiamento` ao passivo. Registrado em débito na §Follow-ups. |

## Follow-ups (fora do escopo desta ADR)

- **Imóvel financiado:** separar `valor_irpf` (custo histórico) de `valor_mercado` (user-declared) + linkar `saldo_financiamento` ao passivo correspondente. ADR futuro.
- **`imoveis_no_if` por workspace** (hoje global em `pipeline.json`): coluna `workspaces.imoveis_no_if` substituindo o toggle global — débito catalogado em [[ADR-142]].
- **Sub-bucket "Patrimônio de uso (não-gerador)"** agregando `uso_pessoal + especulacao + veiculos` no relatório: decisão de UX a refinar com `product-designer`.

## Gates

- **Schema E1.6:** lazy fill validado por golden duplo (`e16_irpf_full_completo.json` com endereço + `e16_irpf_full_sem_endereco.json` sem) — coverage do caminho de fallback.
- **Property identity:** golden de paridade em `tests/unit/pipeline/test_property_identity.py` — 2 IRPFs do mesmo workspace, mesmo imóvel descrito ligeiramente diferente em cada ano → mesmo `property_id`.
- **Override persistência:** test integration em `backend/tests/integration/test_property_override_sticky.py` — re-upload de IRPF após override seteado **não altera** classificação.
- **Heurística:** eval set parametrizado em `tests/unit/pipeline/test_residencia_fuzzy_match.py` com TP/FP documentado e threshold travado.
- **Migration legado:** script de cutover idempotente com dry-run; audit registrando workspaces afetados e classificação inferida.
- **Snapshot OpenAPI** atualizado (`make update-openapi-snapshot`) para endpoints novos de classificação ([[ADR-109]]).
- **Concorrência:** override é write único por `(workspace_id, property_id)` — UNIQUE constraint protege; sem advisory lock necessário.

## Referências

- [[ADR-145]] — 7 categorias canonical (relaciona-se; renomeia label de cat_2; preserva `template_key`)
- [[ADR-142]] — `imoveis_no_if` (passa a filtrar por enum, não por cat_2 inteira)
- [[ADR-143]] — rules-as-code (regras de classificação vão para docstring no calculator)
- [[ADR-134]] — `ConfigStore` DB-first (padrão consistente)
- [[ADR-137]] — catalog + override resolver (espelha modelo `workspace_category_overrides`)
- [[ADR-186]] — override sticky pattern (mesmo princípio: override sobrevive a reprocessamento)
- [[ADR-157]] — schema E1.6 `extract_irpf_full` (adiciona campo aditivo opcional)
- Co-design 2026-05-15: `financial-planner` (taxonomia + invariante IF), `product-designer` (UX pós-upload + estado tripartite), `data-engineer` (schema DB + property identity + lazy split)
