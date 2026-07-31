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

A neutralização real é **rotação**: a task Celery `rotate_fernet_secrets`
([[ADR-171]], runbook `fernet_rotation.md`) re-cifra as colunas com a chave
nova. Depois disso, o blob histórico deixa de ser uma alavanca — decifra nada.

Se a rotação **não** rodou em prod, isso é um **P0 de segurança independente
do flip**: o repo hoje é privado, mas a chave já vazou para o histórico e para
qualquer backup/clone. A rotação precisa acontecer de qualquer forma; o flip
apenas torna a exposição pública, elevando a urgência.

**Não é verificável do repositório.** O estado das colunas cifradas é um fato
de produção. Esta lane é um **gate de confirmação do owner**, não uma tarefa
de código.

> **Correção 2026-07-31.** A versão anterior deste doc mandava rodar
> `python3 scripts/rotate_fernet_secrets.py --confirm` e aceitar a métrica
> `old_key_decryptable=0`. **Nenhum dos dois existe:** o arquivo não está no
> repo (o mecanismo é uma task Celery) e a task não emite esse campo. O
> escopo abaixo foi reescrito contra o código real
> ([`backend/app/tasks/rotate_fernet_secrets.py`](../../../../backend/app/tasks/rotate_fernet_secrets.py)).

## Escopo

1. **Dry-run primeiro** — conta sem escrever e já responde se a rotação é
   necessária:

   ```bash
   celery -A backend.app.worker call rotate_fernet_secrets --kwargs '{"dry_run": true}'
   ```

   `rotated > 0` no dry-run significa que **ainda há colunas na chave velha**
   → a rotação não rodou (ou rodou parcial). `rotated = 0` com `failed = 0`
   significa que tudo já está na chave atual → gate já satisfeito.

2. **Rodar de verdade**, se o dry-run acusou pendência (runbook
   `fernet_rotation.md` §4):

   ```bash
   celery -A backend.app.worker call rotate_fernet_secrets
   ```

3. **Ler o report.** A task devolve contagens **por coluna**, não um número
   único:

   ```
   {"dry_run": false,
    "targets": {"<tabela>.<coluna>": {"rotated": N, "skipped": N, "failed": N},
                "pipeline_artifacts.content_json": {...}}}
   ```

   Semântica (de `_rotate_row_value`): `skipped` = o valor **já está** na
   chave atual · `rotated` = estava numa chave antiga e foi re-cifrado ·
   `failed` = **não decifrou com chave nenhuma** e por isso nunca é
   sobrescrito.

4. **Registrar a confirmação** somando os contadores dos targets, sem colar
   segredo, chave ou valor sensível — só os números (ex.: "rotação de
   2026-07-XX: `failed=0 rotated=N skipped=M` em K targets").

5. Se a rotação **não** rodou: escalar como P0 imediato e rodá-la **antes** de
   qualquer avanço para W1+ (bloqueia G0).

## Critério de aceite (verificável)

O gate fecha com **as duas condições juntas**, nesta ordem:

1. Passe completo (`dry_run: false`) com **`failed = 0`** somado nos targets.
2. **Segundo dry-run** (passo 6 do runbook) retornando **`rotated = 0` e
   `failed = 0`** em todos os targets — a prova de que nada ficou para trás.

A condição 2 não é redundante: é ela que fecha o gate. Sem o segundo passe, um
lote interrompido (a task é resumível) passaria como sucesso.

### Por que `failed = 0` sozinho não bastaria — e o que `skipped` esconde

> **Correção 2026-07-31 (segunda).** A primeira versão deste critério afirmava
> que toda coluna termina em `skipped` (= já na chave atual) ou `rotated`, e
> que `failed` capturaria o resto. **A derivação estava errada** e vale
> registrar, porque o erro é sutil e reaparece em qualquer releitura apressada
> do report.

Em [`vault.py`](../../../../backend/app/services/security/vault.py) o
`needs_rotation` retorna `False` em **dois** casos diferentes:

- o valor decifra com a chave **primária** (está certo, nada a fazer);
- o valor **não decifra com chave nenhuma** (`self.decrypt(...) is None`).

Os dois caem no mesmo contador: `skipped`. Como `_rotate_row_value` só chega
ao ramo `failed` quando `needs_rotation` já disse `True`, esse ramo é
**praticamente inalcançável para as 4 colunas**. Quem produz `failed` de
verdade é só o caminho dos artifacts, que compara `kid` em vez de tentar
decifrar.

Consequências práticas ao ler o report:

- **A propriedade de segurança continua válida.** Um valor que não decifra com
  nenhuma chave também não decifra com a vazada — logo não é vetor de
  vazamento, que é o que o gate G0 precisa garantir.
- **Mas `skipped` é ambíguo** e mistura "está tudo certo" com "isto aqui é
  ilegível". Isso é um risco de **integridade**, não de segurança, e o report
  não o distingue. Um `skipped` alto e inesperado merece investigação.
- Para desambiguar os artifacts, use a query por `kid` do runbook
  `fernet_rotation.md` §6: toda linha deve estar no `kid` da chave primária.

### Checklist

- [ ] Passe completo com `failed = 0` em todos os targets.
- [ ] Segundo dry-run com `rotated = 0` e `failed = 0`.
- [ ] Query por `kid` nos artifacts: 100% no `kid` da chave primária.
- [ ] `failed > 0` **não** fecha o gate: investigar linha a linha pelo log
      (`fernet rotation: artifact undecryptable`, com `artifact_id` e
      `kid_stored`) antes de seguir.
- [ ] Confirmação anexada ao gate **sem** reproduzir chave/segredo — só os
      contadores.
- [ ] Se não havia rodado: rotação executada e concluída antes de G0 liberar W1+.

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
