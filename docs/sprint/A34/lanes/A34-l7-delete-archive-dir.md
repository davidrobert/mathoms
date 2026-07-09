---
id: A34.l7
type: lane
title: "Deletar _archive/ do HEAD (checar referências vivas)"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: delete-archive-dir
adrs: []
depends_on: ["[[A34.l6]]"]
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/seguranca
---

# A34.l7 — `delete-archive-dir` (W1 · Saneamento)

## Problema

`_archive/` está tracked no HEAD com **100 arquivos** e é a maior concentração
de PII real do repositório (auditoria §1.1, [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md)).
Classificação CRÍTICO por path:tipo (valores nunca reproduzidos):

- `_archive/pdf_backup_santander_itau_c6/` — 58 PDFs de extratos bancários reais
  PF+PJ (nome + endereço embutidos no binário).
- `_archive/sessoes_anteriores/*.html` — 2 relatórios financeiros completos reais
  da família.
- `_archive/legacy_scripts/STEP_6b_*` — 2 CPFs reais do casal + nome + patrimônio.
- `_archive/tests_legacy/test_e5_patrimonio_formats.py` — os mesmos 2 CPFs reais.
- `_archive/pre-f8-cutover-2026-04-15/config/tarefas.md` — tarefas pessoais reais.
- `_archive/manual_operacao_v6.1.md` — PII espalhada (nome de familiar, empregador
  da cônjuge, nomes de solteira/casada + filho, inventário de docs, imóveis).

**Armadilha de referência viva:** `manual_operacao_v6.1.md` é citado como manual
histórico do pipeline em `CLAUDE.md` (linhas 448 e 1032) e referenciado em
`docs/reference/ARCHITECTURE.md`. Deletar cego quebra `check_doc_links`. E como o
próprio arquivo tem PII espalhada por prosa (não é PII pontual redigível), **não é
elegível para mover-sanitizado** — é deleção total, e as referências vivas precisam
sair no mesmo PR. O conteúdo não-PII que ainda tem valor (fluxo CLI legado do
pipeline) já está superado por `docs/reference/ARCHITECTURE.md` §7 + `pipeline.stage_spec`;
não há material insubstituível a preservar.

## Escopo

1. `git rm -r _archive/` — remoção total do diretório do HEAD. Nada em `_archive/`
   é recuperável por redação pontual (auditoria §1.1: "Nada é recuperável por
   redação pontual").
2. Atualizar as referências vivas a `_archive/manual_operacao_v6.1.md` **no mesmo
   PR**:
   - `CLAUDE.md` §"Planos → docs/" (nota de path proibido `_archive/`) — remover a
     menção ao manual como "conteúdo protegido"; `_archive/` deixa de existir como
     diretório histórico.
   - `CLAUDE.md` §"Fontes de verdade" bloco "Manual histórico (referência)" —
     remover a linha ou reapontar para `docs/reference/ARCHITECTURE.md` §7 (fluxo
     de stages canônico).
   - `docs/reference/ARCHITECTURE.md` — remover/reapontar a citação ao manual.
3. Confirmar que `check_forbidden_paths.py` continua bloqueando **recriação** de
   `_archive/` (bloqueio de path já existe; a lane [[A34.l6]] o torna gate ativo).
   Não é escopo desta lane alterar o hook — apenas depender do gate já verde.
4. Não tocar `docs/archive/` (histórico de planos/ADRs, PII-zero) — é diretório
   distinto e permanece.

## Critério de aceite

- `git ls-files _archive/` retorna **vazio** (nenhum arquivo tracked sob `_archive/`).
- `git grep -n "_archive/manual_operacao"` no HEAD = zero hits (referências vivas
  atualizadas).
- `python3 dev/check_doc_links.py` verde (nenhum wikilink/link relativo aponta para
  `_archive/`).
- `python3 dev/check_forbidden_paths.py` verde e ainda barra tentativa de re-add de
  `_archive/<x>` (verificação: `touch _archive/probe.txt && git add -f _archive/probe.txt`
  → hook BARRA; limpar o probe depois).
- Gate de PII estendido ([[A34.l4]]) verde no HEAD pós-remoção (sem `_archive/`, os
  achados CRÍTICO §1.1 somem do superset).
- Suíte completa verde (a remoção de `_archive/tests_legacy/*.py` não pode quebrar
  coleta de testes — confirmar que nenhum `conftest`/import vivo referencia esses
  módulos legados).

## Rollback

Toca código (hook/refs) e testes → **CI obrigatório** (não é docs-only).
`_archive/` permanece no histórico git até a Onda 3 ([[A34.l18]] rewrite), então a
remoção do HEAD é reversível por `git revert` do PR enquanto o repo é privado. A
irreversibilidade real vem só no rewrite de histórico (W3), com backup off-site
([[A34.l2]]) como rede. Se `check_doc_links` ou a suíte quebrar por referência
esquecida, reverter o PR e reabrir com a referência viva mapeada.

## Notas

- **Depende de [[A34.l6]]** (bloqueio de `_archive/` no gate + gitleaks bloqueante):
  o gate anti-regressão precisa estar verde e provado ANTES de saneamos, para
  travar re-introdução durante e após a remoção (ordem W2→W1 do plano).
- Remoção do HEAD apenas; o passivo de histórico (`e7b40d30`, PDFs 12,5 MB) é da
  Onda 3.

## Referências

- Plano canônico: [[PLAN-public-release]] (§W1 · tabela de ondas · decisão `[_archive/ delete]`).
- Anexo de auditoria: [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md) §1.1.
- Dependência: [[A34.l6]] (bloqueio de `_archive/` + gitleaks).
- Rede de segurança do rewrite: [[A34.l2]] (backup off-site) · [[A34.l18]] (rewrite de histórico).
- Gate de PII do superset: [[A34.l4]].
