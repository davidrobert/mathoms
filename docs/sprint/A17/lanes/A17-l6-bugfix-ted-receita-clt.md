---
id: A17.l6
type: lane
title: "Bugfix — RECEBIMENTO DE TED engole salário CLT (categorização)"
sprint: A17
status: in_progress
priority: P1
branch_slug: a17-l6-bugfix-ted-receita-clt
tags:
  - type/lane
  - sprint/a17
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/categorization
---

# A17.L6 — Bugfix: `RECEBIMENTO DE TED` engole salário CLT

> **Lane de hotfix** fora do tema "Informes anuais" da A17 — alocada aqui porque A17 é a sprint corrente. Não tem dependência das ondas L1-L5.

## Sintoma

Workspace `ffde7f63-7e28-42ac-b2a3-9adc135a06ce` (David, em prod) reporta no card "Receitas por Fonte":

| Fonte | Média/mês 3M |
|---|---|
| Lucros distribuídos | R$ 92.597,95 |
| Aluguéis | R$ 3.916,90 |
| **CLT** | **R$ 3.806,13** |

Esposa do usuário é CLT no Hospital Albert Einstein com salário > R$ 3k/mês. Sozinho, o salário dela já deveria superar R$ 3.806/mês — está claramente **subdimensionado**.

## Root cause (confirmado experimentalmente)

`internal_transfer_patterns` no seed default `category_template` v1 inclui dois padrões **overbroad** ([alembic a5b6c7d8e9f0 §_AUX_METADATA linhas 882-883](../../../../backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py)):

```
RECEBIMENTO TRANSFERENCIA
RECEBIMENTO DE TED
```

`InternalTransferDetector.is_internal_transfer` faz **substring match case-insensitive sem acento** ([internal_transfer_detector.py:117-124](../../../../pipeline/domain/services/internal_transfer_detector.py)). Logo, **qualquer** TED entrante (que no Brasil é o mecanismo padrão de depósito de salário de empregadores grandes como Einstein) bate em `RECEBIMENTO DE TED` e é classificado como `transferencia` antes mesmo de chegar na resolução de receita ([transaction_classifier.py:363-374](../../../../pipeline/domain/services/transaction_classifier.py)).

A própria docstring do detector ([linhas 6-13](../../../../pipeline/domain/services/internal_transfer_detector.py)) é categórica:

> *"Conservador por design — só marca como interna quando o match é claro. Genéricos (PIX/TED desconhecido) NÃO são marcados como internos."*

O seed contradiz o princípio.

### Evidência reproduzível

Script `_scratch/reproduce_ted_bug.py` constrói o `TransactionClassifier` com os seeds literais e roda 5 descrições típicas — 3/5 engolidas:

```
❌ TRANSF (engolido) | cat=—           | 'RECEBIMENTO DE TED 3221 SOC BENEF ISRAELITA'
❌ TRANSF (engolido) | cat=—           | 'RECEBIMENTO DE TED                  SOC BENEFICENTE ISRAELITA'
❌ TRANSF (engolido) | cat=—           | 'RECEBIMENTO TRANSFERENCIA 3221 HOSPITAL ALBERT EINSTEIN'
✅ RECEITA           | cat=receita_clt | 'SALARIO DEPOSITO SOC BENEFICENTE ISRAELITA'
✅ RECEITA           | cat=receita_clt | 'TED-CRED SOCIEDADE BENEFICENTE ISRAELITA'
```

## Impacto

- **Toda receita CLT/PJ recebida via TED** com prefixo `RECEBIMENTO DE TED` ou `RECEBIMENTO TRANSFERENCIA` é silenciosamente removida do fluxo de caixa do usuário.
- Distorce: card "Receitas por Fonte", taxa de poupança, parecer do planejador (E6), cascata fiscal PJ ([[ADR-236]]) — toda a renda CLT da esposa é fantasma no relatório.
- **Não há warning ao usuário.** Falha silenciosa em invariante de domínio crítico (receita ≠ transferência interna).
- Afeta **todos os workspaces** que herdam o seed v1 — não só `ffde7f63-…`.

## Proposta de fix

### Premissa (a validar com `financial-planner`)

Receita de empregador via TED **nunca** é transferência interna no sentido contábil. "Transferência interna" implica movimentação entre contas do **mesmo titular/família** — TED de empregador é receita externa.

### Mudanças propostas

1. **Remover do seed** (`backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py`):
   - `RECEBIMENTO TRANSFERENCIA`
   - `RECEBIMENTO DE TED`
2. **Migration Alembic nova** — varre `category_templates.metadata_json["internal_transfer_patterns"]` e `workspace_category_overrides.metadata_json["internal_transfer_patterns"]` removendo as duas strings exatas (idempotente).
3. **Princípio enforçado em teste de regressão** (em `tests/unit/pipeline/test_internal_transfer_detector.py`): nenhum padrão em `internal_transfer_patterns` pode ser um prefixo TED/PIX/DOC/RECEBIMENTO genérico. Lista de prefixos proibidos hardcoded; teste roda contra o seed real.
4. **Reclassificação dos workspaces afetados** — runbook em `docs/reference/runbooks/` documenta como rerunner `categorize_transactions` (E4) sem precisar refazer E0-E3. Não é automático — usuário/admin decide quando reprocessar.

### Out-of-scope (separar em lane própria se priorizado)

- Outros padrões suspeitos no mesmo seed (`Cambio`, `Pagto Cobranca`, `Pagamento de fatura`, `SALDO DO DIA`) — auditoria sistemática vs. padrões legítimos.
- `*3221` em `receita_clt` keywords — não é causa raiz do sintoma reportado (é dead keyword inofensivo), mas deveria ser revisto.

## ADR

Considerar **ADR Proposto** documentando o princípio "internal_transfer_patterns require specificity — generic income-channel prefixes (TED/PIX/DOC/RECEBIMENTO) forbidden" para evitar regressão por adições futuras. Decisão: P1 sem invariante novo de DB, então ADR é **opcional** (avaliar com `senior-cto` antes de abrir).

## Co-design

Antes do PR de fix, consultar em paralelo:

- **`financial-planner`** — validar premissa: "TED de empregador nunca é transferência interna" (regra de domínio de fluxo de caixa).
- **`data-engineer`** — revisar migration Alembic + impacto de re-rodar E4 em workspaces existentes (cost de re-categorização).

## Critério de aceite

- [ ] `_scratch/reproduce_ted_bug.py` reportar 0/5 engolidos após o fix.
- [ ] Teste de regressão `test_no_overbroad_ted_patterns` falha sem o fix, passa com o fix.
- [ ] Migration aplicada em todos os ambientes (dev/staging/prod).
- [ ] Workspace `ffde7f63-…` reprocessado em E4 → card "Receitas por Fonte" mostra CLT > R$ 3.806/mês (validação humana com o dono do workspace).
- [ ] Pre-commit + `pytest backend/tests tests -q` verdes.

## Riscos

- **Falso negativo no detector** — TED legítimo entre contas do mesmo titular (ex.: TED Itaú → Bradesco do mesmo usuário) deixará de ser detectado como transferência interna. Mitigação: o detector tem outras camadas (`internal_recipients`, `bank_specific_patterns`) que continuam catching esses casos quando o recipient é conhecido. TED genérico (sem recipient identificado) virou agora `receita` por default — que é mais conservador (sobra como `outras_receitas`) que sumir do fluxo.
- **Reclassificação não-idempotente em workspaces que aprenderam regras (ADR-186)** — `learned_rules_v2` pode ter override que aponta `RECEBIMENTO DE TED ...` para outra categoria. Migration não deve mexer em `category_keywords` (learned rules) — apenas `internal_transfer_patterns`.

## Anexos

- Reprodução: `_scratch/reproduce_ted_bug.py` (gitignored — copiar para `tests/unit/pipeline/test_ted_overbroad_regression.py` no PR).
