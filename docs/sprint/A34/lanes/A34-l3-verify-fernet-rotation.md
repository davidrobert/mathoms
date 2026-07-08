---
id: A34.l3
type: lane
title: "Confirmação operacional: rotação Fernet executada em prod"
sprint: A34
plan: PLAN-public-release
status: planned
priority: P0
branch_slug: verify-fernet-rotation
adrs: ["[[ADR-171]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/planned
  - priority/p0
  - area/seguranca
---

# A34.l3 — `verify-fernet-rotation` (W0 · Gate)

## Problema

A chave Fernet antiga vive no **histórico git**: um `.env` foi commitado em
`ae340c60` e removido depois em `90279c68`. O rewrite de histórico da Onda 3
([[A34.l18]]) remove o **blob** que contém a chave, mas isso **não a torna
inócua** — se a mesma chave ainda decifra colunas vivas em produção
(credenciais em `services/vault.py`, tokens, segredos por-workspace), a
recuperação do blob por qualquer clone anterior ao rewrite continua valendo
como ataque real. Remover a chave do repo é condição necessária, não
suficiente.

A neutralização real é **rotação**: `rotate_fernet_secrets.py` ([[ADR-171]],
runbook `fernet_rotation.md`) re-cifra as colunas com a chave nova e retira a
chave antiga do conjunto de decifração. Depois disso, o blob histórico deixa
de ser uma alavanca — decifra nada.

Se a rotação **não** rodou em prod, isso é um **P0 de segurança independente
do flip**: o repo hoje é privado, mas a chave já vazou para o histórico e para
qualquer backup/clone. A rotação precisa acontecer de qualquer forma; o flip
apenas torna a exposição pública, elevando a urgência.

**Não é verificável do repositório.** O critério (`old_key_decryptable=0`)
é um fato de produção. Esta lane é um **gate de confirmação do owner**, não
uma tarefa de código.

## Escopo

1. Owner executa (ou confirma execução prévia de) `rotate_fernet_secrets.py`
   em produção, conforme o runbook `fernet_rotation.md` ([[ADR-171]]).
2. Capturar as três métricas de saída da rotação:
   - `failed = 0` (nenhuma coluna falhou na re-cifração);
   - `rotated > 0` (colunas efetivamente re-cifradas com a chave nova);
   - `old_key_decryptable = 0` (a chave antiga não decifra mais nenhuma
     coluna viva — o critério que fecha o gate).
3. Registrar a confirmação **por métrica**, sem colar segredo, chave ou valor
   sensível — apenas os contadores (ex.: "rotação de 2026-07-XX:
   `failed=0 rotated=N old_key_decryptable=0`").
4. Se a rotação **não** rodou: escalar como P0 imediato e rodá-la **antes** de
   qualquer avanço para W1+ (bloqueia G0).

Comando de referência (não executar como parte deste doc — é ação de prod do
owner):

```bash
python3 scripts/rotate_fernet_secrets.py --confirm
# saída esperada: failed=0 rotated=<N> old_key_decryptable=0
```

## Critério de aceite (verificável)

- Rotação confirmada em prod com `old_key_decryptable=0` — a chave antiga
  (a que vazou no histórico) **não decifra nenhuma coluna viva**.
- `failed=0` e `rotated>0` registrados na confirmação do gate G0
  ([[PLAN-public-release]] §Verificação).
- Confirmação anexada ao gate **sem** reproduzir chave/segredo — só os
  contadores.
- Se não havia rodado: rotação executada e concluída antes de G0 liberar W1+.

## Rollback

Não destrutiva no repositório — **docs-only** do lado do vault (registra uma
confirmação operacional). A ação de produção subjacente (rotação de chave) tem
rollback próprio no runbook `fernet_rotation.md` ([[ADR-171]]: dual-key window,
re-cifração idempotente). Reverter a *confirmação* é apenas remover a linha de
registro; reverter a *rotação* é fora do escopo desta lane e coberto pelo
runbook.

**Mergeia sem CI** (docs-only). A validação de segurança real é o fato de prod
confirmado pelo owner, não um gate de CI.

## Referências

- [[ADR-171]] — rotação de segredos Fernet (dual-key window, runbook
  `fernet_rotation.md`).
- [[PLAN-public-release]] §W0 / §Riscos & invariantes ("Fernet: o rewrite
  remove o blob, mas a key só é inócua se a rotação rodou em prod — não
  verificável do repo").
- [[A34.l2]] — backup mirror off-site + tag (par de pré-condições de W0).
- [[A34.l18]] — runbook do rewrite de histórico que remove o blob da chave
  (esta lane garante que o blob removido também seja inócuo).
- Auditoria de origem: [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md)
  (achado do `.env` histórico em `ae340c60`, removido em `90279c68`).

## Owner

Owner (confirmação operacional de produção — owner-gated). Agente da lane
apenas registra a confirmação no gate G0 após o owner reportar as métricas;
não executa rotação nem acessa credenciais de prod.
