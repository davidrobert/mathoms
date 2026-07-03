---
id: FAQ-cascata-fiscal-pj
type: doc
title: "FAQ — Como o Mathoms calcula a cascata fiscal PJ e a base PGBL"
date: "2026-05-21"
tags:
  - area/methodology
  - area/report
  - type/doc
  - audience/produto
  - methodology/perini
  - methodology/auvp
  - methodology/cerbasi
---

# Cascata Fiscal PJ — perguntas frequentes

Estas respostas explicam o card **Tributário PJ — Cascata Fiscal** (seção S8 do relatório premium). A cascata mostra como a receita da sua PJ se decompõe em tributos federais, ISS, custos com pró-labore e lucros distribuídos, com a carga total efetiva e os pontos onde planejamento pode mudar o resultado.

## Como o Mathoms calcula a cascata fiscal?

A cascata é projeção de inputs já presentes no seu workspace — **não** pede ao consultor o que o pipeline já sabe.

**Inputs declarados** (preenchidos pelo consultor no console interno, [[ADR-116]]):

- `regime` — MEI · Simples · Lucro Presumido · Lucro Real.
- `anexo_simples` (III/V) e `iss_aliquota_pct` — quando `regime=simples` ou `lucro_presumido`.
- `cnae_principal` — valida Anexo + ISS.
- `tipo_declaracao_ir` (completa/simplificada) — define se PGBL é dedutível.

**Inputs derivados do pipeline** (já calculados, não pedidos novamente):

| Valor | De onde vem |
| --- | --- |
| `receita_pj_anual` | Soma de créditos PJ reconciliados em E3 (janela 12m móvel) |
| `pro_labore_mensal` | Label `pro_labore` em E4 — transferência PJ→sócio com keyword `PRO-LABORE` |
| `lucros_distribuidos_mensal` | Label `lucros_distribuidos` em E4 — crédito PJ→sócio que não é pró-labore |
| `das_pago_mensal` | Label `das_simples` em E4 — débito com `DAS` ancorado |
| `folha_pj_mensal` | Label `folha_pj` em E4 — débito de salário/folha com proxy PJ-side |
| `iss_pago_mensal` | Label `iss` em E4 — débito com `ISS` ancorado |
| `outras_rendas_tributaveis_pf_anual` | Soma de `rendimentos_pj[].rendimentos_tributaveis_brl` + `rendimentos_pf[].valor_brl` do IRPF processado (E1.6, [[ADR-157]]) |

O calculator ([pipeline/domain/services/tributario/cascata_calculator.py](../../pipeline/domain/services/tributario/cascata_calculator.py)) é puro (sem DB, sem HTTP) — recebe um `CascataInput` tipado e devolve um `CascataOutput` com as camadas e os 5 decision triggers V1 ([[ADR-236]] §D6).

**Princípio:** se o pipeline já tem o número (extrato, fatura, IRPF), o card mostra esse número. Se faltar input declarado, o card mostra estado "perfil tributário pendente" com CTA para o consultor preencher — **não** inventa valor.

**Limites conhecidos da V1:**

- Cobre Simples (Anexos III/V), Lucro Presumido e MEI. **Lucro Real** ainda não é suportado (exige escrituração contábil completa — V2).
- Assume 1 PJ por workspace. Multi-PJ entra em V2.
- `folha_pj` depende de `pj_source_mapping` populado e ≥1 receita PJ observada. Sem essas precondições, a label é omitida e o pipeline emite warning tipado `FolhaPJProxyUnavailable`.

## Por que o limite PGBL no Mathoms é diferente do que outras planilhas falam?

Material amador frequentemente afirma que **base PGBL = `receita_pj × 32%`**. **Está errado.**

A base PGBL é a soma da ficha **"Rendimentos Tributáveis"** do IRPF da pessoa física:

```
base_pgbl_anual = pro_labore_anual_tributavel
                + outras_rendas_tributaveis_pf_anual  (aluguéis, juros tributáveis, etc.)
```

**Lucros distribuídos são isentos** — não entram. **Receita da PJ não entra direto.** O pró-labore só entra na parte que aparece na ficha de rendimentos tributáveis do IRPF (líquido de INSS empregado).

A confusão com **32%** vem de outro lugar: é a **presunção de lucro** do regime Lucro Presumido para serviços, base de IRPJ/CSLL na PJ. Conceito completamente independente do limite PGBL.

**Consequência prática:** sócio com pró-labore de R$ 1.500/mês e R$ 40k/mês de lucros isentos tem base PGBL ≈ R$ 18k/ano. Limite dedutível: 12% × R$ 18k ≈ **R$ 2,2k/ano**, independente de a receita PJ ser R$ 500k ou R$ 5M.

**Quando o PGBL fica zero mesmo com renda real:**

- Você escolheu **declaração simplificada** no IRPF (desconto simplificado de 20% substitui todas deduções legais, inclusive PGBL).
- O Mathoms ainda **não processou seu IRPF** (sem o extract E1.6, base = 0). Faça upload do IRPF na aba Inbox.

**Quando aparece um decision trigger sobre PGBL:**

- O **T3** (PGBL alíquota-dependente) sinaliza oportunidade quando sua alíquota IR marginal é ≥ 22,5% E o limite PGBL ainda não está ocupado. O card mostra o limite (R$ Y/ano) — não o aporte que você deve fazer. A decisão final passa pelo seu contador.
- O **T1** (otimização pró-labore × lucros) considera **subir pró-labore** apenas até o ponto em que o limite PGBL fica ocupado, com payback explícito vs. custo INSS patronal adicional. **Não** recomenda subir pró-labore para reduzir IR de forma genérica — isso seria caro em INSS e Mathoms não recomenda sem o break-even fechar.

Referências: Perini *Viver de Renda* (cap. previdência privada) · AUVP (módulo previdência: PGBL só em declaração completa + IR marginal ≥ 22,5% + horizonte > 10 anos) · Cerbasi *Como organizar sua vida financeira* (cap. renda variável PJ).

## Sobre os 5 decision triggers (T1-T5)

Cada trigger aparece quando uma condição quantitativa é satisfeita e mostra o **break-even** explícito — a janela onde a decisão muda de sinal. Copy obrigatório segue padrão CRC: "considere avaliar", "sinal de atenção", "oportunidade" — nunca "recomendamos" ou "você deve".

| # | Trigger | Quando aparece |
| --- | --- | --- |
| T1 | Otimização pró-labore × lucros | Base PGBL atual < 80% do limite potencial com pró-labore ajustado |
| T2 | Fator-R próximo do break-even | Simples Anexo III/V com fator-R em zona de transição |
| T3 | PGBL alíquota-dependente | Declaração completa + IR marginal estimado ≥ 22,5% |
| T4 | Holding patrimonial — 3+ imóveis alugados | ≥ 3 imóveis locados E receita aluguel ≥ R$ 90k/ano |
| T5 | Sublimite estadual Simples | Receita PJ projetada > R$ 2,88M (80% do sublimite de R$ 3,6M) |

**Folclore que o Mathoms NÃO faz:**

- ❌ "Recomendar holding por patrimônio absoluto" — o gatilho real é sucessão multi-herdeiro + ITCMD estadual; patrimônio total **não** é critério V1.
- ❌ "Anuizar receita via lucros isentos no teto do Simples" — teto do Simples é faturamento, não distribuição. Confusão clássica de planejamento amador.

## Telemetria do card é segura para LGPD?

Sim. Os 3 eventos `mathoms.tributario.cascata_rendered`, `mathoms.tributario.trigger_shown` e `mathoms.tributario.profile_incomplete` registram **apenas categorias enumeradas** — regime (MEI/Simples/Presumido/Real), código do trigger (T1-T5), lista de campos faltantes. **Nunca** valor monetário, CNPJ, razão social ou identificador de membro.

Defesa em profundidade: o formatter JSON ([backend/app/core/logging.py](../../backend/app/core/logging.py)) mascara qualquer chave monetária via denylist substring (`receita_pj`, `pro_labore`, `lucros_distribuidos`, `pgbl_base`, etc.). Gate empírico em [tests/test_telemetria_lgpd.py](../../tests/test_telemetria_lgpd.py).

## Disclaimer

> Os valores do card são estimativas a partir das movimentações reconhecidas no seu workspace e do seu IRPF processado. **Confirme com seu contador antes de qualquer decisão tributária.** Mathoms é ferramenta de planejamento patrimonial; não substitui contabilidade nem aconselhamento profissional regulamentado pelo CRC.

## Referências

- [ADR-236](../adr/236-tributario-pj-cascata-fiscal-canonica.md) — Decisão arquitetural completa
- [ADR-157](../adr/157-schema-irpf-completo-stage-extract-irpf-full.md) — Stage E1.6 que extrai IRPF integral (base PGBL)
- [ADR-143](../adr/143-docsmethodology-e-rules-as-code-sprint-a76.md) — Methodology = code
- [Sprint A16](../sprint/A16/_README.md) — Lanes L1 nu_proprietario + L2 cascata fiscal
- Perini "Viver de Renda" — cap. previdência privada
- AUVP — módulo previdência
- Cerbasi "Como organizar sua vida financeira" — cap. renda variável PJ
