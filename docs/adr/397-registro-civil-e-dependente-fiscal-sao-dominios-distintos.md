---
id: ADR-397
type: adr
title: "Registro civil e dependente fiscal são domínios distintos, projetados juntos"
status: Decidido
phase: r7.PE-3
date: "2026-08-19"
relates_to:
  - "[[ADR-200]]"
  - "[[ADR-206]]"
  - "[[ADR-231]]"
  - "[[ADR-240]]"
  - "[[ADR-292]]"
  - "[[ADR-305]]"
  - "[[ADR-341]]"
  - "[[ADR-394]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 397"
  - "composicao_familiar"
  - "faixa_ref"
  - "PE-3"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - phase/r7
---

## Contexto

Na revisão r7 (ws-1b9f2cf5, run 33514dc4) o parecer emitiu, sobre a **mesma
família**, dois itens incompatíveis: `riscos[0]` (S9, severidade Crítica,
confiança **alta**, citando o rationale `dependentes_menores_18`) e `riscos[11]`
(S_IRPF_OTIMIZACAO, severidade Baixa, confiança **baixa**, "dependendo da
composição familiar real"). Δ de confiança 2, zero reconciliação.

O diagnóstico do r6 dizia que o produtor se contradizia. Está errado. Os dois
fatos são **verdadeiros**: registro familiar civil e dependente-fiscal-IRPF são
domínios diferentes, com critérios e datas de referência diferentes. O defeito
era do **manifest**, que projetava só o lado fiscal
(`$.irpf_kpis.dependentes`). Sem o lado civil, o modelo não tinha como fechar —
afirmava os dois lados e hedgeava um deles.

O guardrail pós-LLM agravava: `FIELD_PATH_ALIASES` mapeava
`$.composicao_familiar.dependentes` → `$.irpf_kpis.dependentes`, tratando um
pedido do domínio civil como "path errado" do fiscal. Era a fusão de domínios
codificada.

## Decisão

**D1 — O E5 publica `composicao_familiar`, par civil do bloco fiscal.**
`{faixa_ref, fonte, membros[{papel, faixa_etaria}]}`. Produtor puro em
`pipeline/domain/services/composicao_familiar.py`.

**D2 — O bloco emite faixa etária, nunca idade nem data de nascimento.** A
garantia é **estrutural**, por `additionalProperties: false` no sub-schema E5, e
não por sanitizer: `parecer_context_sanitizer._scrub_node` troca nome por papel e
rasga CPF/CNPJ, mas **uma data ISO passa intacta** — não existe padrão de data de
nascimento. Logo a derivação mora no produtor.

**D3 — `faixa_ref` é 31/12 do ano-calendário do IRPF sob reconciliação, não a
data do run.** A idade que decide elegibilidade fiscal é a de 31/12 do ano-base.
Recortar em `today` produz **falso positivo** "declarado indevidamente" para quem
completou 22 (ou 25) entre 1º de janeiro e o dia do run. O ano vem do mesmo
`resolve_ano_base_fiscal` que alimenta `irpf_kpis.ano_base_default` ([[ADR-305]]).
Sem IRPF não há ano a reconciliar: cai no último ano-calendário fechado — relógio
no passado, nunca à frente da realidade. A data viaja **no bloco**, uma vez, para
que o modelo saiba contra qual relógio a banda foi cortada.

**D4 — Os dois enums são fechados e normalizados no produtor.**
`faixa_etaria` ∈ `0-17 · 18-21 · 22-24 · 25-59 · 60+ · desconhecida`. Os cortes
são fronteiras de decisão fiscal: filho/enteado dependente até 21, até 24 se
cursando superior ou técnico (Lei 9.250/95 art. 35; RIR/2018 art. 71 §1º; IN RFB
1.500/2014 art. 90). Irmão/neto/bisneto sob guarda judicial e menor pobre reusam
**os mesmos 21 e 24** — nenhuma banda extra. `desconhecida` é obrigatório: sem
data de nascimento o snapshot devolve `None`, e omitir o membro o tornaria
invisível. `papel` ∈ `titular · conjuge · filho · enteado · ascendente ·
outro_dependente`; valor não reconhecido vira `outro_dependente`. A normalização é
**requisito de PII**, não estilo — `family_members` é editável pelo dono e carrega
texto livre na natureza.

**D5 — Reconciliação de direção única: o parecer só afirma subdeclaração.**
Faixa `0-17` ou `18-21` com contagem fiscal zero sustenta achado. `22-24` depende
de matrícula, que não está no payload: não-conclusivo. `25+` e `desconhecida`:
não-conclusivo. **Papel `ascendente` nunca é conclusivo** — o critério é teto de
*rendimento*, não idade (art. 35, VII), e declarar obriga a somar os rendimentos
dele à declaração, então não declarar é frequentemente a escolha **correta**. A
doutrina vive como **hint factual** no manifest (descreve o que o par sustenta),
nunca como instrução imperativa de comportamento.

**D6 — Os dois lados são co-locados na mesma seção do manifest**
(`previdencia_irpf`), de propósito: assim **evictam juntos** ([[ADR-341]] D2) e
nunca sobra um sem o outro — que é exatamente o estado que produz o hedge.

**D7 — O guardrail pós-LLM passa a classificar o path em 3 estados.**
`missing` (nenhum ramo existe) · `empty` (o path existe e não rende dado) ·
`present`. Só `present` autoriza remover o pedido do planejador. `empty` emite
telemetria e **não** entra em `_meta.field_request_audit` — o enum do schema tem 2
valores e promovê-lo a `PlannerFieldRequest.reason` é mudança de contrato
([[ADR-206]]). `FIELD_PATH_ALIASES` fica vazio; o mecanismo da via 2 segue vivo
para um alias que seja de fato o **mesmo fato**.

## Alternativas descartadas

**Publicar `dependentes_fiscais_declarados` no bloco civil.** Duplicaria
`$.irpf_kpis.dependentes.count`, que já existe e já é projetado, e recriaria a
fusão de domínios. Prova de que não bastava: no r7 o modelo **tinha** o count e
mesmo assim hedgeou — faltava o lado civil.

**Corrigir o comportamento no prompt ("reconcilie em vez de hedgear").**
Treinaria comportamento antes de medir se o fato projetado já resolve. Se o r8
ainda hedgear com o campo presente, aí a mudança de hint tem evidência.

**Campo `dependente_por_incapacidade`.** Incapacidade é dado de saúde, pessoal
sensível (LGPD art. 5º, II). Trocar data de nascimento por faixa e depois
embarcar diagnóstico seria regressão de PII. O buraco (dependente incapaz de 30
anos cai em `25-59`) fecha pela direção única de D5, não por campo novo.

**Fazer (b) — o guardrail — depois de (a).** Medido: com `membros` publicado sem
`idade`, o pedido `$.composicao_familiar.membros[*].idade` resolvia para a lista
de membros (`walk_path` para no primeiro wildcard) e era marcado espúrio. O
guardrail apagaria a observação que a própria decisão de faixa etária torna
inevitável. Os dois entram juntos.

**Mexer em `walk_path`.** É o renderizador do exec context; a convenção "wildcard
é terminal" sustenta `_render_scalar`/`_render_table`. Alterá-la causaria drift de
prompt e invalidação de cache sem ganho.

## Consequências

- `version` do manifest 2.0.5 → **2.1.0**: entra na chave de cache e em
  `PlannerReview.manifest_version` ⇒ 100% cache miss na primeira geração
  pós-deploy (custo pontual, precedente [[ADR-332]]). `PROMPT_VERSION` **não**
  muda — o gate cobre `^pipeline/llm/(prompts|schemas)/.*\.py$`, fora do diff.
- Custo medido do bloco no corpo orçado do r7: **281 bytes** para 3 membros
  (15.997 → 16.278 de 16.384; folga 106). O custo é **limitado** por
  `max_chars: 260` — satura em ~337 bytes e não cresce com o tamanho da família.
  Nenhum marcador de eviction em nenhum tamanho medido.
- A ordem de `PAPEIS` decide quem sobrevive ao `max_chars`: o corte é no fim e
  deixa por último `ascendente` e `outro_dependente`, que por D5 não sustentam
  achado. Consequência desenhada, não acidente.
- Trocar um corte de faixa é **breaking** no schema E5 — por isso o vocabulário
  existe num único lugar.
- `composicao_familiar` **não** entra na whitelist de `get_e5_section`: ampliaria
  a superfície de egresso sem ganho.
