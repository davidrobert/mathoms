---
id: A42.l13
type: lane
title: "Completude por ficha: `não-shell` é fraco demais para sustentar `completo`"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l13-completude-por-ficha
adrs:
  - "[[ADR-266]]"
  - "[[ADR-157]]"
  - "[[ADR-405]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A42.l13 — Completude por ficha

> **Estado:** `planned`. Liberação é decisão do dono (§Gatilho de promoção da
> A42). A falsificação que a origina está registrada na emenda 2026-08-21 da
> [[ADR-266]]; esta lane decide o **predicado novo**, que a emenda
> deliberadamente não decide.

## O achado, medido (2026-08-21)

A [[ADR-266]] define `completo` como *"ano fiscalmente fechado **E** continuidade
familiar **E** ≥ 1 decl não-shell"*. O limiar `não-shell` é fraco demais:
`_is_shell_decl` ([`irpf_completude.py`](../../../../pipeline/domain/services/irpf_completude.py))
exige **todos** os blocos vazios, então uma declaração com rendimentos e bens
mas `pagamentos_efetuados == []` sai como `completo` com `nota_degradacao = None`.

`resolve_ano_base_fiscal` então elege esse ano como canônico, e `_pgbl_aportado`
— que filtra `codigo_rfb == "36"` **dentro** de `pagamentos_efetuados` — conclui
aporte zero. A direção do erro é a pior: `restante = teto − 0 = teto`, ou seja, a
ficha vazia **maximiza** a capacidade prescrita.

Medido no dogfood: dois artefatos de IRPF com a versão corrente degradada (0 de 2
e 1 de 5 `pagamentos_efetuados`), e o relatório publicado usa essas.

## A pergunta que esta lane decide

Completude é predicado **da declaração** ou **do conjunto de fichas relevantes
para o consumidor**? As duas leituras têm defensor:

- **Por declaração** — ficha vazia é estado legítimo (simplificado; completo sem
  gasto dedutível). `CompletudeAno` está corretamente escopada; o mapa por ficha
  gateia o **consumidor** sem re-eleger o ano. Argumento adicional: fazer a
  eleição andar para trás produziria número correto sobre ano em que a ação é
  impossível — o teto do PGBL é do próprio ano-calendário do aporte.
- **Por ficha** — o consumidor precisa saber que *aquela* ficha não foi apurada,
  e hoje não há canal para isso.

Há convergência num ponto: o estado é **tri-estado, não booleano**, e
`imposto_apurado.deducoes_totais_brl` (obrigatório no schema) é quem arbitra:

| `pagamentos_efetuados == []` com… | estado | efeito |
|---|---|---|
| `modelo == simplificado` | `nao_aplicavel` | sem ressalva — desconto substitui deduções |
| `modelo == completo` e deduções ≈ 0 | `vazia_de_fato` | sem supressão — legítimo |
| `modelo == completo` e deduções > piso de dependentes+previdência | `nao_apurada` | supressão — a declaração afirma dedução que os itens não explicam |

## Escopo

1. Decidir o predicado (ADR `Proposto` antes do PR, [[ADR-182]]).
2. Canal do estado por ficha, aditivo — `irpf_kpis` não tem
   `additionalProperties: false` nem `required`, então campo novo passa em
   `strict` sem migração.
3. `nota_degradacao` nomeia a ficha, não o ano.

## Fora de escopo

- **Não adicionar valor ao enum de completude.** `parecer_pos_llm_guardrails._status_for_year`
  compara literal `!= "completo"` e trataria valor novo como uncovered em
  silêncio; o union TS gerado quebra o build.
- **Não mudar o veredito de eleição** (`pagamentos_efetuados == []` ⇒
  `incompleto`): trocaria o ano-base fiscal do relatório inteiro, e por
  invariante ([[ADR-305]] D4) `previdencia_pgbl.ano_base` migra junto.
- A guarda de prescrição do PGBL/saúde é da [[A40.l65]] §Fora de escopo.

## Débito vizinho, medido junto

`_is_shell_decl` ([`irpf_completude.py`](../../../../pipeline/domain/services/irpf_completude.py))
e `_is_shell` ([`irpf_declaration_deduplicator.py`](../../../../pipeline/domain/services/irpf_declaration_deduplicator.py))
são cópias literais e **ambas ignoram `rendimentos_exterior`** — declaração só
com renda no exterior é shell nas duas. Se tocar o predicado, unifique.

## Critério de aceite

- `modelo == completo`, deduções > 0, ficha vazia → ano continua `completo`,
  ficha `nao_apurada`, PGBL suprimido com nota nomeando a ficha.
- `modelo == simplificado`, ficha vazia → **sem** ressalva de apuração.
- Estado alcançável pela fachada de produção, não só pelo construtor — estado de
  enum que nunca ocorre é código morto ou predicado quebrado.
