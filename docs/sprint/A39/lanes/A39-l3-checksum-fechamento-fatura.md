---
id: A39.l3
type: lane
title: "Checksum de fechamento de fatura: total_fatura + identidade de domínio (ADR-343 nova, corrige ADR-342 item 1)"
sprint: A39
status: planned
priority: P0
branch_slug: a39-l3-checksum-fechamento-fatura
adrs: ["[[ADR-342]]"]
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
  - priority/p0
  - area/pipeline
  - area/dados
---

# A39.l3 — `checksum-fechamento-fatura` (achado PC-01)

## Problema (certificação 2026-07-23 — maior materialidade)

**36/36 faturas** do corpus têm `total_fatura` **não setado** → **nenhum
checksum de fechamento** é possível → toda fatura é teto `coberto-sem-verificação`.
É o lado de **despesa inteiro** incertificável, e viesa **otimista**: item
faltante → despesa subestimada → taxa de poupança inflada → o relatório diz que
a família está mais saudável do que está. Ausência de checksum é pior que
checksum falhando (financial-planner: pior modo num produto que orienta decisão).

**Descoberta (senior-cto):** a [[ADR-342]] §Decisão **item 1 já legisla fatura
com a identidade errada** (`total_fatura ausente/divergente do Σ lançamentos`) —
`Σitens==total` **infla com saldo rotativo** — e o check está **inerte no código**
(`validate_fatura_result` só cobre `empty_result`/`missing_transactions`). Logo
esta lane **corrige** a ADR-342, não só adiciona.

## Escopo

- **ADR-343 `Proposto` ANTES do PR de impl** (identidade de domínio nova,
  rules-as-code ADR-143; co-design financial-planner na forma da equação):
  identidade de fechamento **`saldo_anterior + Σcompras − Σpagamentos + encargos
  == total_fatura`** (cents, tol zero) — **não** `Σitens==total`. Confirmar que
  `encargos` cobre IOF+juros+multa e `saldo_anterior` = total da fatura anterior.
- **Emenda-ponteiro datada à [[ADR-342]] item 1** (protocolo ADR-027, commit
  separado): cláusula `Σlançamentos==total` marcada como **supersedida
  parcialmente** por ADR-343 (só a cláusula de fatura; ADR-342 segue governando
  extrato/CDB/dormância). ADR-343 declara `relates_to: [[ADR-342]]`.
- Popular `total_fatura` **só onde o total é lido independente**:
  `parse_santander_unique`/`parse_santander_fatura_csv` (lê `Valor Total`) e
  `parse_quintoandar`. **NÃO** no `parse_c6_carbon_csv` (`saldo_atual =
  round(Σitens)` → checksum tautológico; documentar a exclusão).
- Implementar o checksum em `validate_fatura_result`; divergência > tol →
  `needs_review`.

## Critério de aceite

- ADR-343 `Decidido (A39.l3)` no merge; emenda-ponteiro em ADR-342 mergeada
  (commit separado).
- Golden com **saldo rotativo** onde `Σitens > total_fatura` mas a equação de
  fechamento **fecha** (prova que a identidade nova ≠ `Σitens==total`);
  tolerância cents zero; red-before-green.
- Santander/quintoandar setam `total_fatura`; C6 Carbon CSV **sem** checksum
  (assert de ausência).
- Harness [[A39.l1]]: faturas com total independente sobem para `completo`
  (checksum passa) ou escalam (KR-C, `checksum_ok` contado separado).

## Risco

Médio — maior blast radius (todos os parsers de fatura). Mitigação: identidade
reconcilia **subtotais declarados**, não soma flat; co-design financial-planner
na equação; ADR-gated.
