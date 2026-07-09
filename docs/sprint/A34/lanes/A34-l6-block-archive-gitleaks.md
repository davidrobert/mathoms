---
id: A34.l6
type: lane
title: "Bloquear _archive/ em forbidden-paths + gitleaks bloqueante"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: block-archive-gitleaks
adrs: ["[[ADR-319]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/seguranca
  - area/ci
---

# A34.l6 — `block-archive-gitleaks` (W2 · Gates)

## Problema

Dois gates de segurança têm buracos que deixam a camada-1 de PII reentrar no
HEAD depois que a Onda 1 a limpar:

- **`dev/check_forbidden_paths.py` não bloqueia `_archive/`.** A lista atual
  ([[PLAN-public-release]] §"O que já existe") cobre `storage/`, `data/`,
  `inbox/` etc., mas não `_archive/`. Depois que a [[A34.l7]] deletar o
  diretório (58 PDFs bancários reais), nada impede um agente de recriá-lo em
  commit futuro — a deleção seria silenciosamente revertida.
- **gitleaks é informativo, não bloqueante.** O job em `security.yml` roda mas
  **não falha o PR** em finding. Um segredo reintroduzido passa por review sem
  sinal duro. Ainda não há SARIF/GHAS (chega na [[A34.l15]], W5).

Este é um **gate anti-regressão** — pela ordem do plano (W2 antes de W1,
`senior-cto` no co-design), ele precisa estar instalado e provado VERMELHO no
HEAD contaminado **antes** de o saneamento da Onda 1 tocar qualquer arquivo.

## Escopo

1. **Forbidden-paths:** adicionar `_archive/` **e** `archive/` (raiz — variante
   sem underscore) ao conjunto bloqueado em `dev/check_forbidden_paths.py`.
   Confirmar que a mensagem de erro nomeia o path ofensor + a razão (padrão dos
   demais paths bloqueados; ver §Code style › Erros do CLAUDE.md).
2. **gitleaks bloqueante:** flipar o job em `security.yml` de informativo para
   gate de PR (exit 1 em finding). SARIF fica reservado para quando GHAS ligar
   na [[A34.l15]] (W5) — nesta lane, exit-code é o suficiente.
3. **Allowlist do Fernet dummy:** a key dummy de CI (`ci.yml:87`) NÃO tem
   anotação `# gitleaks:allow` inline — a supressão hoje é via `.gitleaks.toml`
   (que existe). Garantir que a config bloqueante mantém essa allowlist (regra
   no `.gitleaks.toml`) para não gerar falso-positivo permanente que force
   bypass. (A migração da key para secret em [[A34.l15]] elimina a necessidade.)

Toca **código de gate + config de CI** → **CI obrigatório** (não mergeia
docs-only).

## Critério de aceite (verificável)

- Commit-teste sintético que adiciona um arquivo em `_archive/` (ou `archive/`
  na raiz) é **BARRADO** por `dev/check_forbidden_paths.py` no pre-commit —
  exit ≠ 0, mensagem nomeia o path.
- Commit-teste sintético com um secret de teste (ex.: token dummy `AKIA…`
  fabricado, **nunca** um segredo real) é **BARRADO** pelo job gitleaks no PR
  (exit 1).
- O Fernet dummy anotado com `# gitleaks:allow` **não** dispara finding — o gate
  passa verde num PR que só o contém.
- No HEAD atual (contaminado), gitleaks bloqueante roda **VERMELHO** (prova de
  detecção, alinhado ao gate **G2** do plano: os gates provam que detectam antes
  do saneamento).
- Teste unitário do gate cobre os dois paths novos
  (`_archive/`, `archive/`) — mesmo padrão dos casos existentes de
  `check_forbidden_paths.py`.

## Rollback

Mudança **aditiva** e não destrutiva de dados: reverter o PR restaura o
comportamento anterior (paths não-bloqueados + gitleaks informativo). Sem
migração de estado. Cuidado único: se um PR legítimo já dependia de `_archive/`
existir, ele quebrará — mas [[A34.l7]] remove essa dependência (checar refs
vivas de `manual_operacao_v6.1.md`, ver §Registro de decisões do plano).

## Notas

- **Sem `depends_on`** — pode abrir em paralelo com [[A34.l4]] e [[A34.l5]]
  (as outras duas lanes de gate da W2). O gate G2 fecha quando as três estão
  verdes e barrando commits-teste sintéticos.
- Ordem crítica: esta lane e as demais de W2 **precedem** toda a Onda 1
  ([[A34.l7]] em diante) — o gate rodando vermelho no HEAD é o critério de
  detecção e trava regressão durante as edições de saneamento.

## Referências

- [[PLAN-public-release]] §"Ondas, lanes e dependências" (W2 · G2) + §"O que já
  existe".
- [[ADR-319]] — contrato de gates anti-regressão PII + sigilo (enforcement
  lint/sigilo/forbidden-paths/gitleaks).
- Lanes-par de W2: [[A34.l4]] · [[A34.l5]].
- Consumidor da deleção: [[A34.l7]] (deletar `_archive/`).
- GHAS/SARIF em W5: [[A34.l15]].
