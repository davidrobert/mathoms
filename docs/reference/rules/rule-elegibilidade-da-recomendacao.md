---
id: RULE-elegibilidade-da-recomendacao
type: domain-rule
concept: "Elegibilidade e proveniência da premissa de uma recomendação do plano"
canonical_adr: "[[ADR-365]]"
enforcer_modules:
  - pipeline/domain/services/pontos_urgentes_analyzer.py
  - pipeline/domain/services/e5_serialization.py
formula_ref: null
tags:
  - type/domain-rule
  - area/report
---

# RULE — Elegibilidade e proveniência da premissa de uma recomendação

**Conceito.** Toda recomendação do plano (`pontos_urgentes`) declara em dois eixos
independentes: `origem_premissa` (de onde vem o fato — `cadastro_familia`,
`documento_ingerido`, `derivado_e5`) e `elegibilidade` (se o produto consegue
avaliar a premissa — `computavel`, `nao_verificavel`, `degenerada`,
`pendente_de_dado`). Só `computavel` entra no ranking; o resto vai para
`pontos_urgentes_retidos` com o motivo e o `dado_faltante`. **Ausência de gatilho
não é retenção** — quando o predicado de domínio não dispara, o item não é
produzido.

**Por quê.** Recomendação cuja premissa o payload não sustenta, no topo do plano,
é o defeito que o KR-E da [[A40]] mede. Suprimir em silêncio não resolve: a 6ª
classe do §Critério de done do [[PLAN-report-trust]] exige declaração **por classe
de motivo** no artefato entregue. E um eixo único embutiria ranking de confiança
invertido — fato declarado pelo dono é de primeira mão, enquanto fato derivado do
baseline IRPF é defasado 1-2 anos.

**Doutrina canônica.** Decidida em
[ADR-365](../../adr/365-elegibilidade-e-proveniencia-da-premissa-de-recomendacao.md).
Vocabulários são `Literal` no analyzer + `enum` inline em
`e5_analysis.schema.json`; `code` estável por regra é pré-condição de qualquer
ordenação (numeração posicional de `tarefas`/`tarefas_status` remapearia o status
do dono); os dois arrays são projeções de **uma** lista; as strings do vocabulário
**nunca** aparecem em texto renderizado — a copy nomeia o dado que falta.

**Tabela de mapeamento — gap de proteção de vida → recomendação.** O item de
seguro de vida deixa de ter predicado próprio e passa a mapear
`protecao_patrimonial.gap_qualitativo[categoria="vida"]` ([[ADR-240]] KPI F):

| Estado do gap | Emite item? | `origem_premissa` | `elegibilidade` |
| --- | --- | --- | --- |
| `flag=True`, `rationale="dependentes_menores_18"` | sim | `cadastro_familia` | `computavel` |
| `flag=True`, `rationale="passivo_acima_30_pct_patrimonio"` | sim | `derivado_e5` | `computavel` |
| `flag=True`, `rationale="conjuge_sem_renda_propria"` | sim | `cadastro_familia` | `degenerada` |
| `flag=False`, `rationale="sem family_members"` | sim | `cadastro_familia` | `pendente_de_dado` |
| `flag=False`, `rationale="sem gatilho"` | **não** | — | — |
| `flag=False`, `rationale="apolice_vida_ativa"` | não | — | — |
| bloco `protecao` ausente (caller legado) | sim | `derivado_e5` | `nao_verificavel` |

`degenerada` é **transitório**: sai quando `renda_propria_brl` tiver produtor real
e o predicado passar a ser dependência econômica em vez de `renda == 0`.

**Enforcer.**
- [`pipeline/domain/services/pontos_urgentes_analyzer.py`](../../../pipeline/domain/services/pontos_urgentes_analyzer.py) —
  `OrigemPremissa`/`Elegibilidade`, `PontoUrgenteItem`, e o mapeamento do gap em
  `_seguro_vida_item`.
- [`pipeline/domain/services/e5_serialization.py`](../../../pipeline/domain/services/e5_serialization.py) —
  `partition_pontos_urgentes` (ranqueados × retidos) e `build_default_tarefas`,
  que projeta **só** os ranqueados.

**Manutenção.** Valor novo em qualquer dos dois eixos = membro no `Literal` +
entrada no `enum` de `config/schemas/e5_analysis.schema.json`
§`pontos_urgentes.items` + linha nesta nota.
