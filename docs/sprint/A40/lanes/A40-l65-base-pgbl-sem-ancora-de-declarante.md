---
id: A40.l65
type: lane
title: "A base do PGBL perdeu a âncora de declarante: lê o IRPF mais recente, e o teto de 12% é por CPF"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l65-base-pgbl-sem-ancora-de-declarante
owner: data-engineer
adrs:
  - "[[ADR-236]]"
  - "[[ADR-305]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l65 — `base-pgbl-sem-ancora-de-declarante`

> Aberta em 2026-08-17 no co-design da [[A40.l36]] (`financial-planner`). **A
> l36 é o que torna isto load-bearing** — antes dela o pró-labore ancorava o
> titular; depois, nada ancora.

## Problema

A [[A40.l36]] fez a base do PGBL ser o total do IRPF, fonte única. Com isso, a
proveniência do artifact IRPF passou a ser **100% do número publicado** — e ela
tem dois defeitos que antes ficavam mascarados pela parcela de pró-labore.

### 1 · O ano-base não é resolvido

`tributario_input_builder._load_irpf_renda_tributavel` usa
`_read_latest_workspace_artifact(workspace_id, ("extract_irpf_full",))` — a row
**mais recentemente criada por `created_at`**, sem passar por
`resolve_ano_base_fiscal` ([[ADR-305]] D1/D2) e sem dedup.

O resolvedor existe (`pipeline/domain/services/irpf_completude.py`) e é
consumido pelo E5 e pelo Card B. São **dois resolvedores do mesmo corpus** no
mesmo documento: a S8 pode publicar sobre o ano X enquanto o Card B publica
sobre o ano Y — a classe exata que dá nome à [[ADR-375]].

### 2 · O artifact é POR DECLARANTE, e o teto de 12% é por CPF

`e16_irpf_full` tem `contribuinte.cpf_masked` e `ano_base` como `required`. Numa
família com dois declarantes, "o mais recente" é **a declaração de quem foi
processado por último** — que pode ser o cônjuge.

O limite de 12% é **por contribuinte**, não por família. Workspace é família
([docs/reference/tenancy.md](../../../reference/tenancy.md)). Publicar a base de um sobre o nome do outro é erro de identidade,
não de aritmética.

O modelo certo já existe no repo: `pgbl_capacidade_dedutivel` aplica os 12% **por
declaração** e só então soma. Apontar a S8 para `cap.renda_tributavel_anual`
herdaria a agregação familiar e criaria um **segundo modo de inflar** — não é o
caminho.

## Escopo

1. `_load_irpf_renda_tributavel` passa por `resolve_ano_base_fiscal` e dedup, em
   vez de `created_at`.
2. Âncora de declarante: a base é a do **titular**, resolvido por CPF mascarado
   contra `family_members`. Sem identidade resolvível, a base é ausente — não a
   de quem sobrou.
3. Gate: a S8 e o Card B não podem publicar sobre anos-base diferentes no mesmo
   relatório.

## Fora de escopo

- Agregação familiar dos 12% (é por CPF; somar declarações é outro defeito).
- Ausência vs. zero (`sem_irpf_processado` vs. `renda_tributavel_pf_zerada`) —
  `has_renda_tributavel` já é computado e descartado. Follow-up separado.
- **O predicado de completude que alimenta a eleição do ano** (anotado
  2026-08-21 por sessão externa, sem tocar §Escopo nem §Critério de aceite).
  Esta lane torna a âncora determinística **passando pelo** `resolve_ano_base_fiscal`;
  ela não é dona de `irpf_completude.py`. Medido: `_is_shell_decl` exige *todos*
  os blocos vazios, então declaração com `pagamentos_efetuados == []` sai
  `completo` com `nota_degradacao = None` — a âncora fica determinística **sobre
  documento furado**, e cala. A falsificação do limiar está na emenda 2026-08-21
  da [[ADR-266]]; o predicado substituto é da [[A42.l13]]. Sem essa anotação, o
  critério de aceite desta lane passaria com fixture e calaria em produção.

## Critério de aceite

- Dois declarantes no workspace → base do PGBL é a do titular, sempre, e não
  varia com a ordem de processamento.
- Identidade não resolvível → base ausente com motivo, nunca a de outro CPF.
- Teste que prova que S8 e Card B citam o **mesmo** ano-base.
