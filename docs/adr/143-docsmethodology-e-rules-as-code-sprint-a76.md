---
id: ADR-143
type: adr
title: "`docs/methodology/` é rules-as-code (Sprint A7.6)"
status: Decidido
phase: "Sprint A7.6 · CTO sign-off 2026-04-27"
date: "2026-04-27"
relates_to: ["[[ADR-134]]", "[[ADR-136]]", "[[ADR-137]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 143"]
tags:
  - area/methodology
  - area/multitenancy
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 40
---

# ADR-143 — `docs/methodology/` é rules-as-code (Sprint A7.6)

**Status:** Decidido (Sprint A7.6 · CTO sign-off 2026-04-27) • **Data:** 2026-04-27 • **Relaciona** [ADR-134](#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend), [ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain), [ADR-137](#adr-137--catalog--override-resolver-para-categorization-e-institutions). **Supersedes-a-aproximação-de** A7.4 (entregue 2026-04-27 — `git mv config/*.md docs/methodology/*.md`, mantida a estrutura híbrida que esta ADR corrige).

**Contexto:** A versão CLI mono-cliente do Mathoms usava 4 arquivos markdown editoriais em `config/` (`definitions.md`, `regras_composicao_patrimonial.md`, `source_hierarchy.md`, `milhas.md`) que misturam dois conteúdos:

1. **Regras universais de produto** — invariantes que o Mathoms enforce em runtime (as 7 categorias da composição patrimonial, hierarquia de fontes para reconciliação E3, método de valuation de pontos de milhagem).
2. **Instâncias cliente-específicas do workspace piloto** — David, Mariana, Tasso da Silveira, Hashdex, valores BRL reais, contas Itaú/BTG, programas de milhas com saldos.

A7.4 tratou esses arquivos como "documentação metodológica universal" e fez `git mv` puro para `docs/methodology/`. Auditoria pós-merge (2026-04-27) revelou **102 hits cliente-específicos** distribuídos pelos 4 arquivos (definitions: 59 · regras_composicao: 19 + valores BRL · source_hierarchy: 19 · milhas: 5). Isso viola CLAUDE.md §Regras críticas ("nunca expor valores monetários reais ... em commits"), e expõe o anti-padrão estrutural: **regra de produto como markdown gera drift** (quando o código muda, o doc fica desatualizado), e mistura com dados cliente cria caminho duplo (markdown vs DB) para a mesma informação.

Alternativas consideradas:

- **(a) Sanitizar `docs/methodology/`:** reescrever os 4 arquivos com placeholders (`TITULAR`, `CONJUGE`) sem dados cliente. Mantém o diretório como "spec doc paralelo ao código". **Trade-off:** drift garantido — toda mudança de regra em código requer atualização manual em 2 lugares. Adia o problema; não resolve.
- **(b) Eliminar `docs/methodology/` (rules-as-code):** regras universais migram para docstrings + ADRs co-localizados com a função/classe que enforce; dados cliente migram para DB (estruturado) ou `storage/<workspace_id>/notes/` (gitignored, não-estruturado). Source of truth: o código.
- **(c) Manter `docs/methodology/` como overview com links:** README curto linkando para os docstrings/ADRs. Trade-off intermediário — ainda exige sincronização do README, mas reduz superfície.

**Decisão:** Adotar **(b) rules-as-code**.

`docs/methodology/` deixa de existir. Para cada arquivo:

1. **Regras universais** migram para docstrings na função/classe que enforce (e.g., 7 categorias da composição patrimonial → docstring em `pipeline/domain/services/cash_flow_builder.py` ou similar) + ADR específica (ADR-145, ADR-146, ADR-147 — uma por domínio) que captura o "porquê" da regra.
2. **Dados cliente-estruturados** (categorias workspace-specific, contas bancárias, etc.) já vivem em DB ou migram via lanes correlatas (A7.2a Decision aggregate absorveu contratos PJ + estratégia de aportes; A7.3 absorve categorias/instituições; futuro A8.1 absorve programas de milhas).
3. **Dados cliente-não-estruturados** (notas livres, observações editoriais que não cabem em entidades DB ainda) vão para `storage/<workspace_id>/notes/` — gitignored, workspace-scoped. Bridge transitório enquanto não há entidade DB modelada.

`dev/check_forbidden_paths.py` ganha bloqueio para `docs/methodology/**` (impede recriação acidental).

CLAUDE.md §Regras críticas ganha parágrafo: "Methodology = code. Nada em `docs/methodology/`. Regras universais vivem em docstrings + ADRs; dados cliente em DB ou `storage/<ws>/notes/`."

**Consequências:**
- ✅ Source of truth única: o código que enforce. Drift estrutural eliminado.
- ✅ CLAUDE.md §Regras críticas (anti-PII em commits) reforçada por construção — não há mais lugar onde dados cliente "naturalmente" se misturam com regras de produto em git.
- ✅ Regras universais ganham testes diretos via testes unitários da função que as enforce (não dependem de leitura de markdown).
- ✅ Onboarding melhora: leitor encontra a regra **junto com a função que a aplica**, não em doc separado que pode estar desatualizado.
- ⚠️ Quem busca "qual a regra do produto X?" precisa pesquisar no código (via grep/IDE) em vez de abrir um índice doc. Mitigação: ADRs especializadas (ADR-145..147) servem como índice canônico — referenciadas por nome em commits e docs.
- ⚠️ Curva de migração: A7.6 sub-task 4 (sanitização de `definitions.md`) depende soft de A7.3 (categorias/instituições absorvidas) + A7.2a (decisões absorvidas) já mergeadas, para que o "drop" seja seguro.
- ❌ Conteúdo histórico de `docs/methodology/` permanece em git history; auditoria pós-fato requer git blame / git log (não acessível via UI atual). Aceito — o vazamento de PII no history é o mesmo que tinha em `config/` antes; remoção retroativa do history exige `git filter-branch` que está fora do escopo desta lane.
- ❌ Para regras que cruzam múltiplos arquivos (ex.: como E3 hierarchy interage com E4 categorização), o leitor precisa navegar entre N docstrings. Mitigação: ADRs do A7.6 (143, 145, 146, 147) servem como pontes cross-cutting.
