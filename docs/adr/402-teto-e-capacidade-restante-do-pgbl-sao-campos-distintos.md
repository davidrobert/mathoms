---
id: ADR-402
type: adr
title: "Teto e capacidade restante do PGBL são campos distintos; ausência carrega motivo tipado"
status: Decidido
phase: r7.FP-5A
date: "2026-08-19"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-189]]"
  - "[[ADR-196]]"
  - "[[ADR-277]]"
  - "[[ADR-305]]"
  - "[[ADR-375]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 402"
  - "teto ≠ capacidade restante do PGBL"
  - "motivo_ausencia do card PGBL"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - phase/r7
---

# ADR-402 — Teto e capacidade restante do PGBL são campos distintos; ausência carrega motivo tipado

## Contexto

O run r7 (`ws-1b9f2cf5`, run `33514dc4`) publicou em `previdencia_pgbl`:
`limite_pgbl_anual: 0.0`, `renda_tributavel_anual` positiva,
`aliquota_marginal` positiva, `aporte_mensal: null`, `economia_ir_anual: null`
e uma `nota` de 1111 caracteres que casava **duas** frases mutuamente
exclusivas — `_NOTA_REGIME_INCOMPLETO` e `_NOTA_SIMPLIFICADO`.

O diagnóstico não é aritmética errada, nem default esquecido, nem degradação.
`IRPFAnalyzer.pgbl_capacidade_dedutivel` fazia `continue` em declaração
simplificada e devolvia `Decimal("0")` — comportamento **contratual e
documentado** ("zero se modelo simplificado — G0"). `_analyze_via_irpf`
publicava esse `restante` no campo chamado `limite_pgbl_anual`. É **valor
correto sob rótulo errado**: o campo carrega *capacidade restante* sob o nome
*teto*.

Três consequências mensuráveis:

1. O leitor — humano e LLM — lê "seu limite de PGBL é R$ 0" quando o fato é "o
   modelo de declaração escolhido desabilita a dedução". O `narrative_hints`
   do parecer chegou a codificar o erro (`se limite_pgbl_anual=0 …`).
2. O mesmo `0` significava **três** fatos distintos: modelo simplificado,
   teto consumido, e aporte **acima** do teto. O `max(0, …)` apagava o
   terceiro — o mais acionável dos três.
3. `null` não carrega a razão de ser `null`. Sem motivo tipado, a nota era o
   único lugar onde o estado existia, e nada garantia que nota e campo
   concordassem. RV4-72 declarou `previdencia_pgbl` "correto" por inspeção e
   o defeito reincidiu.

## Decisão

**D1 — Duas grandezas, dois campos.** `limite_pgbl_anual` passa a carregar o
**teto** (12% × base tributável das declarações completas). Campo irmão
`capacidade_restante_anual` carrega `max(0, teto − aportado)`. O nome do campo
não muda: `previdencia_pgbl` está em `_NON_CITABLE_ROOTS`
(`parecer_citation_catalog`) e o alias-map da A40.l2 depende da chave.

Invariantes:

- `∃ declaração completa com base > 0 ⇒ teto = 0,12 × base` (e `teto > 0`);
- senão `teto = null ∧ motivo_ausencia.teto ≠ null`;
- `teto ≠ null ⇒ restante = max(0, teto − aportado)` — **aqui `0` é legítimo**;
- global: `campo == 0.0 ⇒ motivo_ausencia[campo] is None`.

**D2 — `motivo_ausencia` é objeto por campo, com enum fechado e precedência
declarada.** Campos: `teto`, `restante`, `aporte`, `economia`. Precedência:

```
sem_irpf_processado > modelo_simplificado > sem_renda_tributavel
                                          > regime_fiscal_incompleto
```

`modelo_simplificado` e `sem_renda_tributavel` anulam tudo;
`regime_fiscal_incompleto` anula aporte e economia (ADR-375 D4) e **preserva**
teto e restante — o espaço de 12% vem do IRPF e não depende da completude do
regime corrente. O motivo dominante é quem escreve a nota; os demais calam.
Sem precedência, o r7 emitia duas explicações no mesmo texto.

`nota_degradacao` **não** serve a este papel: tem dono semântico (ADR-305 D3 —
"existe ano-base mais recente não usado") e coocorre com estes motivos.

**D3 — VO no lugar do escalar.** `pgbl_capacidade_dedutivel` devolve
`CapacidadePgbl(teto, aportado, restante, status, excedente_nao_dedutivel)`.
O clamp é **por declaração**, porque o limite de 12% é por CPF: somar antes de
clampar deixaria o excesso de um titular consumir o espaço do outro.
`previdencia_pgbl` passa a publicar `pgbl_status`, `pgbl_aportado_anual` e
`excedente_nao_dedutivel_anual` — estado que só existia em prosa.

**D4 — Nota e campos derivam ambos do VO.** A nota nunca é escrita ao lado do
campo, e o campo nunca é lido da nota. "Nota derivada do campo" é inexequível:
`null` não carrega a razão de ser `null`. O pivô comum é o motivo dominante.

**D5 — `aliquota_marginal` é bicondicional com `economia_ir_anual`.** Sem
economia publicável, a marginal é ruído citável que convida o leitor a
reconstruir a prescrição que o motivo acabou de suprimir.

**D6 — A mudança é no analyzer, não no bloco da S7.** O Card B em `irpf_kpis`
continua dono único do teto (ADR-196, pós-#1448) e seu contrato de wire fica
inalterado: `pgbl_capacidade_dedutivel_brl` segue sendo a capacidade restante
como string, desambiguada por `pgbl_status`.

## Alternativas rejeitadas

- **Renomear `limite_pgbl_anual` para `capacidade_restante_anual`.** Corrigiria
  o rótulo sem publicar o teto — e o teto é a informação que falta ao card.
- **Motivos `requisito_previdenciario_desconhecido` / `_ausente`.** Exigem dado
  que o produto não coleta hoje; sem coletor, todo workspace cairia em
  "desconhecido" e a prescrição sumiria universalmente. Fora do enum até que o
  coletor exista (follow-up).
- **`sem_produto_pgbl` como motivo do teto.** O teto é espaço fiscal: existe
  para quem nunca contratou PGBL. Apagá-lo removeria a informação mais útil.
- **Anular o teto por idade ou regime previdenciário.** Nenhuma regra vigente
  anula os 12% por idade.
- **Fechar por inspeção.** Precedente direto: RV2-08 fechou duas vezes e
  reincidiu; RV4-72 declarou este mesmo bloco correto e reincidiu. O gate é
  paramétrico sobre `PgblStatus × regime_completo` e assere **coocorrência**
  campo ↔ fragmento canônico da nota, provado por mutação.

## Consequências

- `previdencia_pgbl` ganha 5 chaves; `motivo_ausencia` tem `required` nos 4
  campos e `additionalProperties: false`.
- Efeito no r7: `limite_pgbl_anual 0.0 → null`, `capacidade_restante_anual
  null`, `motivo_ausencia.teto = "modelo_simplificado"`, `pgbl_status =
  "modelo_simplificado"`, `aliquota_marginal → null`, `nota` 1111 → ~660
  chars (a frase de regime incompleto some por precedência).
- Muda texto ao cliente (padrão ADR-196 §4).
- `parecer_planejador.yaml` vai a 2.0.6: o hint que instruía sobre
  `limite_pgbl_anual=0` apontava para um valor que deixou de existir.
