---
id: A40.l115
type: lane
title: "O sanitizer de PII mede o contexto de ENTRADA e nunca o output: o relatório publica CPF parcialmente mascarado e conta bancária completa"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l115-sanitizer-mede-a-entrada-e-publica-a-saida
owner: sre-devops
depends_on: []
adrs: ["[[ADR-319]]", "[[ADR-434]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/backend, area/seguranca]
---

# A40.l115 — `sanitizer-mede-a-entrada-e-publica-a-saida`

> **Origem:** `RR9-16` da rodada unificada **U5** ([[REPORT-REVIEWS-active]] §r9).

## O defeito

O CPF sai **mascarado com os dígitos finais em claro**, em prosa **e** no campo de
`evidencia` — dois canais, o segundo dos quais ninguém revisa. Na **mesma página**, agência
e conta saem **completas**, sem máscara nenhuma: a política protege um identificador e
publica dois.

O gate mede o **contexto de entrada** que vai ao LLM; **nada mede o output**. E a docstring
do sanitizer afirma *"CPF/CNPJ redigidos"* enquanto o conjunto de chaves que ele de fato
cobre tem **um** elemento, que não é CPF nem conta.

## Por que a docstring é a parte grave

Ela é a razão pela qual isto sobreviveu: quem lê o módulo conclui que a cobertura existe.
É o modo de falha *"afirmação global falsa se repete em N sítios"* — a asserção do
docstring vale como justificativa de ausência de gate.

## Critério de aceite

1. O sanitizer roda no **output publicado**, não só no contexto de entrada.
2. Cobertura declarada = cobertura medida: teste que enumera os tipos de identificador e
   falha quando a docstring afirma mais do que o conjunto cobre.
3. Agência/conta entram na política, com decisão explícita de máscara (é dado do próprio
   dono — a decisão é de produto, não técnica).
4. Regressão sobre `evidencia`, não só sobre prosa.

## Entregue — 2026-09-01 · [[ADR-434]]

Medido sobre o payload **real** do U5 (`report_data.json` + `parecer.json`, 5.562 strings):
o gate saía de **0 hits** e passa a **7** — exatamente os 7 ofensores medidos
independentemente, **zero falso-positivo**.

| Critério | Estado | Como |
|---|---|---|
| 1 — sanitizer roda no output publicado | ✅ | eram **três** egressos, não um (abaixo) |
| 2 — cobertura declarada = cobertura medida | ✅ | `TIPOS_COBERTOS` + igualdade de conjunto nas 2 direções + docstring comparada por teste; 5 mutações plausíveis, 5 reprovam |
| 3 — agência/conta na política, com decisão explícita | ✅ | [[ADR-434]] D4, co-design `financial-planner`: conta preserva cauda-4, agência sai inteira |
| 4 — regressão sobre `evidencia`, não só prosa | ✅ | resolvido **por construção**: o walker chaveia no valor, não em allowlist de chave |

### Três correções ao enunciado desta lane

1. **"O gate mede o contexto de entrada; nada mede o output" é falso para o relatório.**
   `redact_view_model` redige `/reports/{id}/data` desde a [[A40.l6]] ([[ADR-337]] c4). O
   defeito era **vocabulário** do gate, não ausência dele. A frase é verdadeira só para o
   parecer — e, medindo, também para um **terceiro** canal que a lane não citava:
   `suggestion_supersede` copia `acao`/`impacto_qualitativo` verbatim da prosa do LLM para
   `suggestions`, servida por `/suggestions`. Redigir só `/planner-review` fecharia um dos
   três.
2. **A docstring do sanitizer não afirma cobertura globalmente falsa.** A lane diz que "o
   conjunto de chaves que ele de fato cobre tem um elemento, que não é CPF nem conta" —
   isso confunde `_IDENTIFIER_KEYS` (por chave, 1 elemento) com `scrub_identifiers` (por
   valor, cobre CPF/CNPJ **crus**). A afirmação é verdadeira para a forma crua e falsa para
   a mascarada. O diagnóstico de fundo — a frase valeu como justificativa de ausência de
   gate — **procede**; a caracterização dela não.
3. **O CPF não sai no campo `evidencia`.** Não reproduz neste run: o `evidencia` do risco
   cita a ausência **sem** o número; o CPF está em `descricao`. O critério 4 continua certo
   como requisito de **canal**, e foi atendido por construção — mas a lane afirmava um fato
   que a medição não sustenta.

### Severidade corrigida

Conta+agência completas é **Alto**. CPF parcial **no display não é achado**: a [[ADR-259]]
§4 já sanciona `***.***.789-00`, com **5** dígitos em claro — `***.***.***-DD` tem 2 e é
*mais* conservador que a política vigente. O que restava era o **egresso ao provider**
(que a [[ADR-259]] §2 não sanciona), **Médio**, remediado no produtor.

### Ofensores medidos

| Onde | Forma | Produtor |
|---|---|---|
| `patrimonio.posicao_31_12[].instituicao` (4 de 18) | `Ag DDDD Conta DDDDDDD-D` | transcrição verbatim do rótulo do banco pelo LLM, via `informe_pf_saldos_31_12[].descricao` |
| `irpf_kpis.ano_base_nota_degradacao` · `previdencia_pgbl.nota_degradacao` | `***.***.***-DD` | `irpf_completude._missing_cpf_motivo` |
| `parecer.riscos[].descricao` | `***.***.***-DD` | round-trip: o E5 levou a nota ao provider e ela voltou na prosa |

### Follow-up com dono (deferimento datado na [[ADR-434]])

`posicao_31_12[].instituicao` **não contém instituição** — recebe `descricao or
cnpj_emissor`, e as linhas de `fonte=extrato` põem ali outra coisa. Sem emissor, mascarar
deixa duas aplicações distinguíveis só por sorte de transcrição. `nome_emissor` é
obrigatório no schema e está no mesmo dicionário que `cnpj_emissor`. Destrava concentração
por emissor e limite FGC, hoje não computáveis.
