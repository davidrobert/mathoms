---
id: PLAN-launch-trust
type: plan
title: Launch Trust — três frentes que precisam estar verdes antes de produção
status: in_progress
created_at: 2026-05-30
last_review: 2026-05-30
sprint_origem: A20
sprint_atual: A21
sprints_envolvidas: [A20, A21]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-246]]"
  - "[[ADR-255]]"
  - "[[ADR-267]]"
  - "[[ADR-268]]"
  - "[[ADR-271]]"
tags:
  - type/plan
  - status/in-progress
  - area/pipeline
  - area/llm
  - area/seguranca
---

# Launch Trust — três frentes que precisam estar verdes antes de produção

> **Origem:** co-design multi-agente em 2026-05-29/30 (orquestrador principal +
> 6 especialistas em paralelo: `product-manager`, `information-architect`,
> `financial-planner`, `data-engineer`, `sre-devops`, `prompt-engineer`).
> Pergunta-semente: *"assumindo que o projeto ainda não está em produção,
> quais as 3 próximas frentes?"*
>
> **Não conflita com lanes ativas:** verificado contra `git worktree list` +
> `origin/agent/*` em 2026-05-30. Sprint A20 (Docker/DX hardening) pausada;
> este plano é a próxima onda de trabalho proposta.
>
> **Tese:** três dimensões de confiança precisam estar verdes antes do
> cutover de `app.mathoms.ai`. Cada frente responde a uma pergunta que um
> cliente pagante faz implicitamente:
>
> | Frente | Pergunta do cliente | Dimensão de confiança |
> |---|---|---|
> | **F1 — Confiabilidade do número** | "Esse patrimônio é o meu de verdade?" | Confio nos **números** |
> | **F2 — Caminho crítico de produção** | "Se eu subir meus extratos, isso fica de pé e seguro?" | Confio na **infraestrutura** |
> | **F3 — Parecer defensável** | "Esse conselho financeiro é responsável?" | Confio no **conselho** |
>
> Lançar com uma das três vermelha é lançar sem confiança — o pior momento
> para um produto de planejamento patrimonial descobrir que o número está
> errado, o dado vazou, ou a IA alucinou um conselho.

---

## Mapa de leitura

- [Federação — o que este plano possui vs. referencia](#federação--o-que-este-plano-possui-vs-referencia)
- [Definition of Launch-Ready (KRs)](#definition-of-launch-ready-krs)
- [Frente 1 — Confiabilidade do número](#frente-1--confiabilidade-do-número-owned) **(owned)**
  - [Estado atual](#f1-estado-atual--o-que-já-aterrissou)
  - [Análise de gap](#f1-análise-de-gap)
  - [Lanes F1-O0 … F1-O5](#f1-lanes)
  - [Invariantes de domínio](#f1-invariantes-de-domínio-financial-planner)
- [Frente 2 — Caminho crítico de produção](#frente-2--caminho-crítico-de-produção-federada) **(federada → PLATFORM_REVIEW)**
- [Frente 3 — Parecer defensável](#frente-3--parecer-defensável-federada) **(federada → PLANNER_REVIEW + LLM_PROMPTS_HARDENING)**
- [Sequenciamento entre frentes](#sequenciamento-entre-frentes)
- [Cut line — Must / Should / Defer](#cut-line--must--should--defer)
- [ADRs a abrir (Proposto)](#adrs-a-abrir-proposto)
- [Cross-links](#cross-links)

---

## Federação — o que este plano possui vs. referencia

Este plano **não duplica** trabalho já mapeado em planos canônicos
existentes. Cada frente declara explicitamente ownership:

| Frente | Modo | Dono canônico | O que este plano faz |
|---|---|---|---|
| **F1** | **OWNED** | este plano | Território verde — nenhum plano cobre `consolidate_baseline` (E1.5c). [[PLAN-platform-review]] adiou explicitamente E1.5c para "Q3 2026" (§coverage gaps). F1 puxa para agora porque é launch-blocker. |
| **F2** | **FEDERADA** | [[PLAN-platform-review]] (W3/W4) + [[ADR-228]] (G1-G5) | Declara o **subconjunto launch-blocking** de W3/W4 e os 3 gaps que nenhuma wave cobre. Não reescreve as tasks — referencia por link. |
| **F3** | **FEDERADA** | [[PLAN-planner-review]] (done) + [[PLAN-llm-prompts-hardening]] | Camada de **eval + guardrails defensáveis** sobre o Parecer já entregue. Não reabre o stage; adiciona a malha de segurança que falta para lançar. |

**Regra anti-drift:** quando uma task F2/F3 referenciada mudar de status no
plano dono, este plano **não** atualiza o detalhe — só o checkbox de
launch-blocking. Detalhe de execução mora no plano dono; aqui mora a
**decisão de que é bloqueante para lançar**.

---

## Definition of Launch-Ready (KRs)

O plano fecha quando as três frentes atingem o gate. North star da
iniciativa: **zero erro silencioso de número, dado ou conselho no caminho
do cliente pagante.**

| KR | Métrica | Meta launch-blocking | Frente |
|---|---|---|---|
| **KR1** | Suíte de invariantes de consolidação (INV-1..9) verde em CI | 9/9 passando, sem skip | F1 |
| **KR2** | `fn_rate` (duplicata real não fundida → infla PL) no golden multi-ano | ≤ 5% | F1 |
| **KR3** | `fp_rate` (entidade distinta fundida → some patrimônio) no golden | **0%** (red line) | F1 |
| **KR4** | Gates operacionais G1 (backup/restore drill) + G2 (rollback drill) | executados e documentados | F2 |
| **KR5** | Deploy reproduzível: imagem versionada de registry (não `:dev` local) em `docker-compose.prod.yml` | shipped | F2 |
| **KR6** | LGPD: audit log de acesso a dado sensível (Art.37) + rota de export/deleção (Art.18) | shipped | F2 |
| **KR7** | Golden eval do Parecer (24 fixtures) em CI, 7 red lines com hard-block | verde, 0 red-line violada | F3 |
| **KR8** | Fallback `needs_review` atômico testado: LLM down → relatório não quebra | teste de regressão verde | F3 |

---

## Frente 1 — Confiabilidade do número (OWNED)

> **Boundary:** `consolidate_baseline` (E1.5c, `scripts/e15_consolidate.py`),
> onde três mecanismos de dedup rodam em sequência: resolução de membro por
> CPF → dedup de imóveis → dedup de investimentos. É o ponto onde "o que o
> cliente declarou em N IRPFs e M extratos" vira "o patrimônio dele".

### F1: Estado atual — o que já aterrissou

A frente **não parte do zero**. Quatro ADRs fecharam buracos de dedup nos
últimos 60 dias:

| ADR | Entidade | Mecanismo | Aterrissou |
|---|---|---|---|
| [[ADR-246]] | Imóveis | `imoveis_dedup.py` — dedup co-declarado em comunhão; soma proibida; maior valor vence; label "casal" | maio |
| [[ADR-255]] | Transações | hash K4 + strip de sufixo PIX no `normalize_descricao` (C6Bank emite mesma tx em PDFs variantes) | maio (#478) |
| [[ADR-267]] | Membros | identity por **CPF**, não slug-do-nome (bug R$ 811k: Mariana solteira ≠ casada) | maio |
| [[ADR-271]] | Investimentos | `investimentos_dedup.py` — chave `(tipo, instituição_norm, descrição_norm)`; 2 eixos (cross-year une série, cross-declarante funde conta conjunta idêntica ao centavo) | 28/mai |

**Calibração herdada (de `investimentos_dedup.py`):** *"falso-positivo (some
patrimônio real) é pior que falso-negativo (infla PL)"*. Esta assimetria é a
política de domínio de toda a frente — KR3 (`fp_rate`=0%) é red line; KR2
(`fn_rate`≤5%) é meta tolerante.

### F1: Análise de gap

O que **não** existe e bloqueia confiar no número:

1. **Sem suíte de invariantes de consolidação.** `imoveis_dedup` e
   `investimentos_dedup` têm testes unitários próprios, mas ninguém valida o
   **resultado agregado** de E1.5c (conservação, não-double-count,
   idempotência). Um quarto mecanismo de dedup adicionado amanhã pode
   quebrar a conservação sem nenhum teste vermelho.
2. **Sem golden multi-ano anotado.** Não há fixture sintética com
   duplicatas conhecidas (`_expected.known_duplicates`) para **medir**
   `fn_rate`/`fp_rate`. Hoje a calibração é qualitativa, não medida.
3. **Dois arquivos-espelho sem contrato.** `imoveis_dedup.py` (387 linhas) e
   `investimentos_dedup.py` (263 linhas) implementam o **mesmo algoritmo**
   (header do segundo diz literalmente *"Espelha imoveis_dedup com duas
   divergências de domínio"*). Próxima entidade (dívida, veículo,
   previdência) copia-cola um terceiro espelho. Drift garantido.
4. **`dividas` é array livre** (schema `baseline_patrimonial.schema.json`
   L144 — sem schema). Dívida do mesmo financiamento declarada em 2 anos
   conta dobrado.
5. **Previdência PGBL/VGBL conta dobrado** (gap NOVO, `financial-planner`):
   o mesmo plano aparece como **ativo** (posição patrimonial) **e** como
   **dedução fiscal** (base PGBL). Sem dedup cross-axis, infla PL e distorce
   a recomendação de aporte.
6. **Veículo cross-year sem dedup** — `vehicle.py` tem âncora forte
   (placa/renavam, `uq_workspace_placa`), mas o consolidador não usa a placa
   como chave de série temporal; mesmo carro em 2 IRPFs duplica.

### F1: Lanes

> Ordem de risco de domínio (`financial-planner`): **dívida → previdência →
> veículo**, da âncora mais fraca para a mais forte. A dedup de âncora fraca
> é a mais perigosa (mais chance de FP) e deve vir com a malha de segurança
> (invariantes + golden) já no lugar.

| Lane | Título | Tipo | Sev | Dono | Depende de |
|---|---|---|---|---|---|
| **F1-O0** | Suíte de invariantes de consolidação (INV-1..9) | M | **P0** | data-engineer | — |
| **F1-O1** | Golden multi-ano anotado + métrica fn_rate/fp_rate | M | **P0** | data-engineer | F1-O0 |
| **F1-O2** | Extração do contrato `EntityDedup` (Protocol compartilhado) | L | P1 | senior-cto | F1-O0, F1-O1 |
| **F1-O3** | Dedup de dívida cross-year (`max(ano)` + warning de monotonicidade) | M | P1 | financial-planner + data-engineer | F1-O2 |
| **F1-O4** | Dedup previdência PGBL/VGBL (ativo × dedução fiscal) | M | **P1** | financial-planner | F1-O2 |
| **F1-O5** | Dedup veículo cross-year (chave placa + valor FIPE) | S | P2 | financial-planner | F1-O2 |

#### F1-O0 — Suíte de invariantes de consolidação (P0, sem deps)

A rede de segurança que deveria existir antes de qualquer dedup novo. Nove
invariantes empíricos sobre o output de E1.5c, em
`tests/unit/pipeline/test_e15c_dedup_invariants.py` + golden de execução em
`tests/test_e15c_golden_execution.py`.

| # | Invariante | Por quê |
|---|---|---|
| INV-1 | **Conservação:** soma de valores pós-dedup ≤ soma pré-dedup (nunca cria patrimônio) | dedup só remove/funde |
| INV-2 | **Não-double-count:** nenhuma `identity_key` aparece 2× no output | a razão de existir do dedup |
| INV-3 | **Idempotência:** `dedup(dedup(x)) == dedup(x)` | rodar 2× não muda nada |
| INV-4 | **Cobertura de ID:** todo item de saída tem `<entity>_id` estampado | rastreabilidade |
| INV-5 | **Preservação cross-declarante:** conta conjunta de 2 cônjuges vira 1 item com label "casal", não some | regra ADR-246/271 |
| INV-6 | **Tie-break determinístico:** mesmo input → mesmo vencedor (maior valor; empate → ordem estável) | sem flakiness |
| INV-7 | **Warning não-silencioso:** toda fusão emite `DedupWarning` tipado | auditabilidade |
| INV-8 | **Monotonicidade de série:** cross-year usa `max(ano)`; queda de valor entre anos emite warning, não erro | dívida amortiza, ativo oscila |
| INV-9 | **Não-pessoa (PF-only):** contribuinte com razão social PJ (`detect_pj_suffix` casa LTDA/S.A./EIRELI/MEI/…) nunca surge como membro nem soma ao PL consolidado | [[ADR-268]]: read-filter `partition_irpf_payloads` cobre E5, **não** E1.5c — INV-9 fecha o boundary de consolidação |

**Critério de aceite:** 9/9 verde, sem skip, contra os goldens de F1-O1.

#### F1-O1 — Golden multi-ano anotado + métrica (P0)

Fixture sintética **zero-PII** (`tests/fixtures/dedup/multi_year_baseline.json`)
com CPFs fictícios de dígito verificador inválido, cobrindo: mesma pessoa em
3 anos, conta conjunta de casal, imóvel em comunhão, dívida amortizando,
previdência aparecendo como ativo+dedução. Bloco `_expected.known_duplicates`
anota cada par esperado para o teste `test_dedup_recall.py` medir:

- `fn_rate` = duplicatas reais não fundidas / total de duplicatas reais → **KR2 ≤ 5%**
- `fp_rate` = entidades distintas fundidas / total de não-duplicatas → **KR3 = 0%**

#### F1-O2 — Contrato `EntityDedup` (P1)

Generaliza os dois espelhos num `Protocol` + runner único, em
`pipeline/domain/services/entity_dedup.py`. `imoveis_dedup` e
`investimentos_dedup` passam a ser **policies** (≈30 linhas cada) sobre o
runner. Esboço (data-engineer):

```python
@dataclass(frozen=True)
class DedupOutcome:
    items: list[dict]
    warnings: tuple[DedupWarning, ...]
    count_before: int
    count_after: int
    dropped_ids: tuple[str, ...]

class EntityDedupPolicy(Protocol):
    id_field: str
    casal_label: str
    def identity_key(self, entry: dict) -> tuple | None: ...
    def stamp_id(self, entry: dict, key: tuple) -> dict: ...
    def merge_cross_year(self, entries: list[dict]) -> tuple[dict, tuple[DedupWarning, ...]]: ...
    def is_joint(self, per_owner: list[dict]) -> bool: ...
    def merge_joint(self, per_owner: list[dict]) -> dict: ...
    def tie_break_winner(self, group: list[dict]) -> dict: ...
    def divergence_warning(self, per_owner: list[dict]) -> DedupWarning | None: ...

def run_entity_dedup(items: list[dict] | None, policy: EntityDedupPolicy) -> DedupOutcome: ...
```

**Risco:** refactor de código que já está em produção e correto. Mitigação:
F1-O0+F1-O1 verdes **antes** do refactor — a suíte é a rede que prova que a
extração não mudou comportamento. Abrir **ADR Proposto** antes do PR
(escopo arquitetural, regra CLAUDE.md).

#### F1-O3 / F1-O4 / F1-O5 — novas entidades (P1/P1/P2)

Cada uma vira uma `EntityDedupPolicy`. Regras de domínio (`financial-planner`):

- **F1-O3 dívida:** chave de série = identidade do financiamento; cross-year
  usa `max(ano)` (saldo devedor mais recente); queda de saldo é normal
  (amortização) → INV-8 warning, não erro. Schema de `dividas` deixa de ser
  array livre.
- **F1-O4 previdência:** double-count **cross-axis** — mesmo plano é ativo E
  dedução fiscal. Policy reconcilia os dois eixos: conta como **1 ativo**;
  a dedução PGBL alimenta a base fiscal sem somar ao PL. Lembrar invariante
  da memória: base PGBL = renda tributável PF (folclore "receita×32%"
  rejeitado, ADR-236).
- **F1-O5 veículo:** chave = placa/renavam (âncora forte já existe);
  cross-year usa valor FIPE mais recente. Menor risco de FP (âncora forte) →
  P2.

### F1: Invariantes de domínio (financial-planner)

Além dos INV-1..9 estruturais, dez regras de domínio que a frente deve
preservar (viés FP/FN por força de âncora):

1. Imóvel em comunhão = 1 ativo, label "casal", maior valor vence (ADR-246).
2. Conta de investimento conjunta idêntica ao centavo = 1 ativo (ADR-271).
3. Membro = CPF, nunca nome (ADR-267).
4. Âncora forte (placa, CNPJ, conta+agência) → dedup agressivo OK.
5. Âncora fraca (descrição livre, valor) → dedup conservador (prefere FN).
6. Cross-year ativo: valor pode subir ou cair (oscilação de mercado).
7. Cross-year dívida: valor só cai (amortização); subida = warning.
8. Previdência: 1 ativo + N deduções fiscais, nunca soma cruzada.
9. Toda fusão é auditável (warning tipado, nunca silenciosa).
10. Contribuinte PJ (razão social, sufixo LTDA/S.A./…) não é pessoa: não vira
    membro nem entra no PL — pré-filtro, não regra de dedup (ADR-268).

---

## Frente 2 — Caminho crítico de produção (FEDERADA)

> **Dono canônico:** [[PLAN-platform-review]] (Waves 3-4) + [[ADR-228]] (gates
> operacionais G1-G5). Esta seção declara **o que é launch-blocking** e os
> **gaps que nenhuma wave cobre** — não reescreve as tasks.

**Realidade verificada (sre-devops, 2026-05-30):** a Sprint A20 entregou
**higiene de imagem** (multi-stage Dockerfile, SHA pinning, non-root,
psycopg3, lockfile pip-tools) — **não** entregou o caminho de deploy.
`docker-compose.prod.yml` ainda aponta `image: mathoms-backend:dev` com
`build:` local; `trivy image` ainda é `continue-on-error: true`
(informativo). **Deploy reproduzível continua bloqueado.**

### F2: Subconjunto launch-blocking de PLATFORM_REVIEW

| Lane (dono) | O que é | Launch-blocking? | Gate |
|---|---|---|---|
| W3-T05 (injeção LLM) | defesa contra prompt injection no caminho de upload | **SIM** | F3 depende disto |
| W3 (auth/email/Fernet) | hardening de auth + Fernet PII (ADR-231) | **SIM** | KR6 |
| W4-T01 (backup) | política de backup + drill de restore | **SIM** | KR4 / G1 |
| W4-T02 (deploy) | imagem versionada de registry em prod compose | **SIM** | KR5 |
| W4-T03 (Sentry) | error tracking em prod | Should | G3 |
| W4-T05 (rate-limit/status) | rate limit + status page | Should | G5 |

**Fases (sre-devops):**

- **2.0 — Deploy reproduzível:** `docker-compose.prod.yml` consome imagem de
  GHCR (A20.l4) com tag versionada; `trivy image` vira blocking (A20.l5).
  Fecha KR5. *Reusa as 2 lanes A20 pausadas.*
- **2.1 — Backup/restore + rollback drill:** G1 + G2 executados e
  documentados em runbook. Fecha KR4.
- **2.2 — Auth/Fernet/injeção hardening:** subconjunto W3. Fecha pré-req de F3.
- **2.3 — Observabilidade mínima:** Sentry + status (Should).
- **2.4 — LGPD (gaps NÃO cobertos por wave nenhuma):** ver abaixo.

### F2: Gaps que nenhuma wave cobre (sre-devops)

Três buracos de produção que não estão em nenhuma wave do PLATFORM_REVIEW e
viram lanes deste plano:

| Lane | Gap | Sev | Por quê é launch-blocking |
|---|---|---|---|
| **F2-G1** | **Single-host SPOF** | P1 | um host = um ponto de falha; sem plano de HA mínimo ou aceite explícito de RTO |
| **F2-G2** | **Audit log de acesso a dado sensível (LGPD Art.37)** | **P0** | obrigação legal — quem acessou CPF/financeiro de quem, quando |
| **F2-G3** | **Data-subject rights — export/deleção (LGPD Art.18)** | **P0** | direito do titular; sem isto, não-conforme para cliente brasileiro |

**SLOs de launch (sre-devops):** RPO ≤ 24h, RTO ≤ 30min (consistente com a
janela do runbook de rollback de pipeline, ADR-212).

---

## Frente 3 — Parecer defensável (FEDERADA)

> **Dono canônico:** [[PLAN-planner-review]] (status `done` — Atos 0-6 mergeados,
> ADR-199..208) + [[PLAN-llm-prompts-hardening]] (telemetria/LGPD/ADR-090 nos 9
> prompts). Esta seção adiciona a **malha de eval + guardrails** que falta
> para o Parecer ser defensável diante de um cliente pagante.

O Parecer existe e renderiza. O que falta para confiar nele em produção é a
prova de que **não alucina conselho irresponsável** e **degrada com graça**
quando o LLM falha.

### F3: Lanes

| Lane | Título | Sev | Launch-blocking? |
|---|---|---|---|
| **F3-O0** | 24 golden fixtures do Parecer + métrica de eval em CI | **P0** | SIM (KR7) |
| **F3-O1** | Validação em 3 camadas (schema → invariante de domínio → red line) | **P0** | SIM |
| **F3-O2** | Fallback `needs_review` atômico (LLM down → relatório não quebra) | **P0** | SIM (KR8) |
| **F3-O3** | Defesa de injeção nas superfícies E5 + tool (ADR-175) | P1 | SIM (compartilha W3-T05) |
| **F3-O4** | Drift detection (3 sinais) + pin de model-snapshot | P1 | Should |

### F3: Estratégia (prompt-engineer)

- **Goldens:** 24 fixtures sintéticas zero-PII cobrindo casos felizes +
  adversariais (input contraditório, tentativa de injeção, dado faltante).
- **Validação em 3 camadas:** (1) schema Pydantic/Instructor
  `additionalProperties:false` + hard caps (`parecer_planejador.schema.json`
  v1.0); (2) invariantes de domínio (não recomenda alavancagem acima de
  threshold, não promete retorno, etc.); (3) **7 red lines** com hard-block.
- **CI:** goldens **mockados no PR** (rápido, determinístico) +
  **LLM-real nightly** (pega drift do provider). Temperatura 0.3 + pin de
  model-snapshot (não `latest`).
- **Guardrails:** Instructor + Pydantic; falha de validação → fallback
  `needs_review` atômico (relatório renderiza sem o Parecer, com aviso).
- **Drift (3 sinais):** distribuição de confidence, taxa de `needs_review`,
  delta de tokens/custo entre `PROMPT_VERSION` (gate ADR-233).

### F3: Red lines (hard-block) + quality gates (financial-planner)

**7 red lines** — violação = Parecer rejeitado, vai para `needs_review`:

1. Não promete/garante retorno futuro.
2. Não recomenda alavancagem acima do threshold de domínio.
3. Não recomenda zerar reserva de emergência.
4. Não dá conselho fiscal específico sem disclaimer.
5. Não inventa número fora do E5 (toda cifra rastreável ao input).
6. Não recomenda produto financeiro nominal específico (sem "compre fundo X").
7. Não contradiz invariante de domínio já calculado (ex.: IF, alocação-alvo).

**4 quality gates** (não bloqueiam, mas degradam qualidade — viram warning):
cobertura de seções obrigatórias, aderência à persona Perini/Cerbasi/AUVP,
consistência tom, ausência de jargão não explicado.

---

## Sequenciamento entre frentes

```
Dia 1 ──┬── F1-O0 (invariantes)  ──→ F1-O1 (golden) ──→ F1-O2 (contrato) ──→ F1-O3/O4/O5
        │
        ├── F2-2.0 (deploy GHCR) + F2-G2/G3 (LGPD)   [paralelo, independente de F1]
        │
        └── F3 GATED: só começa após F1-O0 verde + W3-T05 (injeção) em main
```

- **F1 e F2 rodam em paralelo no dia 1** — não compartilham código.
- **F3 é gated** por F1-O0 (a malha de invariantes prova o número que o
  Parecer consome) **e** por W3-T05/F3-O3 (injeção) — não adianta endurecer
  o Parecer sobre um número não confiável ou uma superfície injetável.

---

## Cut line — Must / Should / Defer

**Must (launch-blocking):** F1-O0, F1-O1, F1-O4 (previdência — P1 mas
double-count visível ao cliente), F2-2.0 (deploy), F2-G2, F2-G3 (LGPD),
F3-O0, F3-O1, F3-O2.

**Should (pós-launch próximo):** F1-O2 (contrato — débito de qualidade, não
de correção), F1-O3 (dívida), F2-2.3 (observabilidade), F3-O3, F3-O4.

**Defer (backlog):** F1-O5 (veículo — âncora forte, baixo risco de FP),
F2-G1 (HA — aceitar RTO single-host explicitamente no launch).

---

## ADRs a abrir (Proposto)

Por disciplina CLAUDE.md (ADR Proposto antes de PR P0/P1 com escopo
arquitetural):

| ADR (proposto) | Escopo | Frente |
|---|---|---|
| Contrato `EntityDedup` (Protocol + runner) | refactor estrutural de 2 serviços de produção | F1-O2 |
| Dedup cross-axis de previdência (ativo × dedução) | invariante de domínio novo | F1-O4 |
| Schema formal de `dividas` (sai de array livre) | contrato `config/schemas/` | F1-O3 |
| Audit log de acesso a dado sensível (LGPD Art.37) | política de segurança + modelo de dados | F2-G2 |
| Data-subject rights — export/deleção (LGPD Art.18) | contrato de API + retenção | F2-G3 |
| Malha de eval + red lines do Parecer | guardrails LLM em produção | F3-O0/O1 |

---

## Cross-links

- **F2 dono:** [`PLAN-platform-review`](../PLATFORM_REVIEW/_README.md) — Waves 3-4, [[ADR-228]] G1-G5.
- **F3 dono:** [`PLAN-planner-review`](../PLANNER_REVIEW/_README.md) — Atos 0-6, [[ADR-199]]..[[ADR-208]].
- **F3 dono:** [`PLAN-llm-prompts-hardening`](../LLM_PROMPTS_HARDENING/_README.md) — telemetria/LGPD nos prompts.
- **ADRs canônicas de F1:** [[ADR-246]] (imóveis), [[ADR-255]] (transações), [[ADR-267]] (membros por CPF), [[ADR-268]] (filtro PF×PJ — INV-9), [[ADR-271]] (investimentos).
- **Invariantes relacionadas:** [[ADR-236]] (base PGBL = renda tributável PF), [[ADR-212]] (ArtifactStore DB-only, janela RTO rollback).
