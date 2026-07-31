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

> **Use o gate executável.** [`dev/fernet_rotation_gate.py`](../../../../dev/fernet_rotation_gate.py)
> implementa os passos abaixo com os guards embutidos — inclusive o que impede
> o falso-limpo descrito na §Critério. Rode-o **no mesmo container do worker**
> (a env que ele lê precisa ser a mesma que cifra os dados). Os comandos
> `celery` crus continuam documentados no runbook `fernet_rotation.md` para
> quem precisar do controle manual.

1. **Preflight — a janela de rotação está aberta?**

   ```bash
   python3 dev/fernet_rotation_gate.py preflight
   ```

   **Não pule.** Com a janela fechada (só a chave atual no ambiente), um valor
   cifrado com a chave antiga não decifra e é contado como `skipped` — o
   dry-run sai `rotated=0 failed=0` e você leria como "já está tudo certo",
   exatamente no cenário que o gate existe para pegar. O `preflight` sai 1
   nesse caso, em vez de deixar o falso-limpo passar.

   Abrir a janela é ação de plataforma (Coolify), não do script: setar
   `MATHOMS_FERNET_KEYS=<chave_nova>,<chave_antiga>` em **backend e worker**
   com redeploy síncrono (runbook §2).

2. **Rotacionar** — dry-run, mostra o report, pede confirmação, executa:

   ```bash
   python3 dev/fernet_rotation_gate.py rotate
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

4. **Fechar o gate** — 2º dry-run + as duas condições, e a query de `kid`:

   ```bash
   python3 dev/fernet_rotation_gate.py verify
   ```

   Saindo 0, ele imprime a linha de confirmação pronta para colar no G0 — só
   contadores e o `kid` de 8 chars, sem chave nem valor sensível.

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
