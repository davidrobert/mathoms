---
id: ADR-145
type: adr
title: "7 categorias canonical da composição patrimonial"
status: Decidido
phase: "Sprint A7.6 · CTO sign-off 2026-04-27"
date: "2026-04-27"
relates_to: ["[[ADR-143]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 145"]
tags:
  - area/report
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 39
---

# ADR-145 — 7 categorias canonical da composição patrimonial

**Status:** Decidido (Sprint A7.6 · CTO sign-off 2026-04-27) • **Data:** 2026-04-27 • **Relaciona** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76).

**Contexto:** O relatório financeiro do Mathoms apresenta a "Composição Patrimonial" como gráfico doughnut com **exatamente 7 buckets**. A taxonomia foi historicamente documentada em `config/methodology/regras_composicao_patrimonial.md` (movido para `docs/methodology/` em A7.4) misturando regras universais com exemplos cliente-específicos. ADR-143 elimina o markdown; esta ADR registra a decisão das 7 categorias como invariante de produto.

A taxonomia é parte do **modelo metodológico Mathoms** (não do dado cliente): assume premissa "casal com até 2 titulares de investimentos" (titular + cônjuge) e separa imóveis de moradia × investimento — escolhas de produto inspiradas nas metodologias Perini / Cerbasi / AUVP referenciadas no projeto.

Alternativas consideradas:

- **(a) N categorias dinâmicas por workspace.** Cada cliente define seus buckets. **Trade-off:** quebra comparabilidade entre relatórios e relatórios benchmarks; aumenta complexidade de UI; sem evidência de demanda.
- **(b) 5 categorias agregadas (Imóveis / Investimentos / Caixa / Crypto / Veículos).** Mais simples mas perde granularidade entre "residência principal" vs "imóveis investimento" e entre titular vs cônjuge — informação clínica para planejamento (Perini distingue residência de investimento; AUVP distingue patrimônio investível por membro).
- **(c) 7 categorias fixas com regras determinísticas.** Mantém comparabilidade, captura nuance de produto, é estável.

**Decisão:** Adotar **(c)**. As 7 categorias canônicas são:

1. **Residência própria** — moradia principal da família (sempre exatamente 1 imóvel).
2. **Imóveis investimento** — todos os imóveis dos membros, exceto a residência principal. Pós-[[ADR-215]] split interno em **geradores** (`classification ∈ {locado, comercial}`) vs **não-geradores** (`classification ∈ {uso_pessoal, especulacao, nu_proprietario, desconhecido}`). Pós-[[ADR-235]] (A16), `nu_proprietario` cobre nu-propriedade com usufruto vitalício de terceiro — entra em cat_2 **não-gerador** (paridade `uso_pessoal`); não cria categoria nova "Patrimônio ilíquido condicional".
3. **Investimentos {TITULAR}** — ativos financeiros do titular: investimentos clássicos (`investimentos[]`) + contas bancárias de tipo investimento (`tipo` contém `RDB|CDB|CDP|Renda Fixa|Investimento|Aplicacao|Poupança|Saldo em Conta` em corretora). **Inclui** fundos regulados que tenham nome sugerindo crypto mas sejam FIC FIM (ex.: Hashdex Crypto).
4. **Investimentos {CONJUGE}** — mesmo conjunto, aplicado ao cônjuge (workspace-specific labelling via `family_members.json` membros titular/cônjuge).
5. **Criptoativos** — crypto direta (BTC, ETH, ADA, etc.) mantida em exchanges. **Não inclui** fundos regulados de crypto.
6. **Caixa + Moeda Estrangeira** — `tipo` contém `Conta Corrente` (sem "Investimento" no mesmo campo) **OU** `Moeda Estrangeira`.
7. **Veículos** — categoria residual para automóveis/embarcações.

> **Nota de implementação ({TITULAR}/{CONJUGE}):** os labels exibidos no relatório vêm de `family_members.json` (campos `nome_curto` dos membros com papéis `titular`/`conjuge`); o `template_key` interno é estável (`investimentos_titular`, `investimentos_conjuge` — paralelo a [ADR-137](#adr-137--catalog--override-resolver-para-categorization-e-institutions) que proíbe rename de keys). Renaming de label não afeta o key.

Premissa de produto: **exatamente 2 titulares de investimentos** (titular + cônjuge). Famílias com configurações diferentes (apenas titular, >2 membros investidores, etc.) são tratadas como casos especiais — `Investimentos {CONJUGE}` retorna 0 quando ausente; >2 membros não suportado nesta versão.

Regras de classificação (universal, sem dados cliente) vão para docstring na função classificadora em `pipeline/domain/services/cash_flow_builder.py` (ou serviço equivalente identificado no Explore da lane A7.6). Os exemplos cliente-específicos (Hashdex matching, contas Itaú Personnalité, etc.) viram **fixtures de teste unitário** com nomes anônimos (`FundoExemplo`, `BancoExemplo`).

**Consequências:**
- ✅ Comparabilidade entre relatórios e benchmarks externos preservada.
- ✅ Taxonomia estável — clientes novos importam dados e relatório classifica determinísticamente.
- ✅ Drift entre regra documentada × código aplicado eliminado (rules-as-code).
- ⚠️ Famílias fora da premissa "casal" (>2 membros investidores, união homoafetiva com >2 titulares fiscais, etc.) são limitadas pela taxonomia. Expansão para N membros requer ADR futuro + redesenho de schema (provavelmente Sprint A8+).
- ⚠️ Fundos com classificação ambígua (ex.: ETF temático, fundos de venture) seguem regra textual no docstring; resolução duvidosa requer decisão editorial → vira test fixture nova + atualização do docstring.
- ❌ Renaming de `template_key` da categoria é PROIBIDO (apenas add/deprecate) — paralelo à regra de [ADR-137](#adr-137--catalog--override-resolver-para-categorization-e-institutions) sobre categorization templates.
