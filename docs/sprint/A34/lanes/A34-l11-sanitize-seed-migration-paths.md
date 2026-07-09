---
id: A34.l11
type: lane
title: "Neutralizar seed de produção + report_spec + paths"
sprint: A34
plan: PLAN-public-release
status: shipped
priority: P0
branch_slug: sanitize-seed-migration-paths
adrs: []
depends_on: ["[[A34.l4]]"]
tags:
  - type/lane
  - sprint/a34
  - status/shipped
  - priority/p0
  - area/db
  - area/seguranca
---

# A34.l11 — `sanitize-seed-migration-paths` (W1 · Saneamento)

## Problema

Cinco arquivos **de código/config tracked no HEAD** carregam nomes reais de
terceiros, situação fiscal real e paths de máquina local. Ao contrário das ADRs
([[A34.l9]], texto pedagógico) e dos CPFs/endereço ([[A34.l10]], PII do titular),
aqui o vazamento está **dentro de artefatos que rodam** — uma migration de seed
de produção e um baseline de estilo que o CI carrega. Referências mascaradas
(seção §1.5 e §1.8 do [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md)):

- `backend/alembic/versions/a5b6c7d8e9f0_seed_category_template_v1.py` — **CRÍTICO.**
  Keywords de categorização = nomes reais de terceiros (relação familiar por
  extenso, ocupação doméstica nominal) + empregadores nominais + mapping do tipo
  `"<Empregador> (<Inicial> - CLT)"`. É seed de **PRODUÇÃO**: o texto neutralizado
  precisa continuar categorizando corretamente.
- `config/report_spec.md` — **ALTO.** Linhas de orçamento com nomes de terceiros
  + situação fiscal real (regime PJ em atraso, carnê-leão).
- `dev/code_style_baseline.json` + `dev/dedup_property_identity.py` — **BAIXO.**
  Path absoluto `/Users/<owner>/...` vaza username e estrutura de diretório
  local.
- `docker-compose.prod.yml:4` — comentário de infra nomeia provedor de VPS +
  plataforma de deploy (topologia de produção que não deve ser pública).

## Escopo

1. **Seed (migration):** substituir as keywords/labels nominais por genéricos
   que preservem a **função de categorização** — relação familiar → termo
   genérico (ex.: `familiar`), ocupação doméstica → categoria genérica (ex.:
   `servico_domestico`), empregador nominal → placeholder (ex.: `EMPREGADOR_CLT`).
   **Não** alterar a estrutura do seed nem a coluna/contrato — só os valores-string.
   Migration é seed de produção: se a edição tocar **contrato/coluna** (não apenas
   valores-string), coordenar com `data-engineer` antes do PR ([[ADR-137]] rege
   `category_template`).
2. **`config/report_spec.md`:** trocar nomes de terceiros por `Titular`/`Cônjuge`
   e a situação fiscal real por caso sintético (`R$ X`, regime genérico), mantendo
   a estrutura pedagógica das linhas de orçamento.
3. **Paths locais:** substituir `/Users/<owner>/...` em `dev/code_style_baseline.json`
   e `dev/dedup_property_identity.py` por path relativo ou placeholder
   (`<REPO_ROOT>` / caminho relativo ao repo). Confirmar que o baseline de estilo
   ainda casa no CI após a troca.
4. **`docker-compose.prod.yml:4`:** genericizar o comentário — remover nome do
   provedor de VPS e da plataforma de deploy; descrever a intenção sem nomear
   fornecedor (`# deploy target: VPS gerenciado + orquestrador de containers`).
5. Rodar `git grep` dos termos-alvo após as edições para garantir zero resíduo
   (incluindo variantes) — este é o critério de detecção da lane.

> **Fora do escopo desta lane:** `backend/app/scripts/seed_if_goal_<sobrenome>.py`
> (sobrenome da família no filename + metas reais, §1.5; achar via
> `git ls-files 'backend/app/scripts/seed_if_goal_*'`) — envolve **rename de arquivo** e
> valores de metas, não apenas valores-string internos; tratar em [[A34.l10]]
> (purga de PII do titular) para não fragmentar a operação de rename.

## Critério de aceite (verificável)

- `git grep -n -i -E '<termos-nominais-de-terceiros>'` nos 5 alvos = **zero**
  (a lista concreta de termos vem da §1.5/§1.8 do anexo; não transcrever valor
  real nesta lane).
- `git grep -nE '/Users/[^/]+/' -- dev/` = **zero** (nenhum path de home local).
- `git grep -niE '<provedor-vps>|<plataforma-deploy>' -- docker-compose.prod.yml` = **zero**
  (os dois termos concretos estão em `docker-compose.prod.yml:4`; não transcrever aqui —
  mesma disciplina de mascaramento do anexo §1.5).
- O gate de PII/domínio estendido em [[A34.l4]] roda **verde** sobre os 5 arquivos
  (antes desta lane deve rodar vermelho — critério de detecção de W2).
- Seed re-executa sem erro e categorização de fixture sintética permanece
  correta: `pytest backend/tests -q -m migration` verde (teste de migration com
  `pytestmark = pytest.mark.migration`).
- Baseline de estilo casa pós-troca de path: `pre-commit run --all-files` verde.
- Suíte completa verde (código neutralizado não quebrou contrato).

## Rollback (toca código/testes)

Reverter o PR (`git revert`) restaura os valores originais — porém isso
**reintroduz PII**, então o rollback só é aceitável **antes** do flip público
([[A34.l22]]) e nunca após W3 ([[A34.l18]], rewrite de histórico). A migration
de seed é forward-only: a neutralização é edição de **valores-string** no corpo
do `upgrade()`, sem alteração de schema, portanto não exige downgrade. Se a
edição tiver tocado contrato (fora do escopo previsto), `data-engineer` valida
o revert.

**CI obrigatório** — toca migration + baseline de estilo + código; roda a suíte
completa antes do push (não é docs-only).

## Referências

- Anexo de auditoria (fonte, mascarado): [audit-2026-07-08.md](../../../plan/PUBLIC_RELEASE/audit-2026-07-08.md) §1.5, §1.8.
- Plano canônico: [[PLAN-public-release]] (Onda W1 · Saneamento do HEAD).
- Gate de detecção (dependência): [[A34.l4]] — estende `lint_no_real_pii` a
  `docs/` + domínio (deve estar verde antes desta lane commitar).
- Pares de saneamento W1: [[A34.l9]] (ADRs in-body) · [[A34.l10]] (CPFs + endereço +
  seed nominal do titular).
- Contrato de dados do seed: [[ADR-137]] (`category_template` DB, versionado).
