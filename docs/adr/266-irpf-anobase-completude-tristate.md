---
id: ADR-266
type: adr
title: "Completude tri-state de ano-base IRPF: completo / provisorio / incompleto / mudanca_estrutural"
status: Decidido
phase: A16
date: "2026-05-23"
relates_to:
  - "[[ADR-157]]"
  - "[[ADR-188]]"
  - "[[ADR-189]]"
  - "[[ADR-194]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 266"
  - "irpf completude"
  - "ano-base completo"
tags:
  - area/pipeline
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - phase/a16
  - status/decidido
  - type/adr
---

## Contexto

[[ADR-157]] estabeleceu o extract IRPF E1.6 e o `IRPFAnalyzer` que agrega KPIs por `ano_base`. O card "Renda Anual Familiar" (`S_IRPF_RENDA`) e o `RendaEvolucaoChart` consomem `irpf_kpis.ano_base` (último ano disponível) para opinar — implícito: o último ano-base sempre é a fonte da verdade.

PR de dedup (`IrpfDeclarationDeduplicator`) acabou de resolver o caso de fragmentação intra-ano (N PDFs do mesmo titular/ano viram 1 winner). Mas há **três regimes distintos** de "ano-base mostrável" que o produto ainda confunde:

1. **Ano fiscalmente fechado e família consolidada** — verdade. Card pode opinar com confiança.
2. **Ano dentro da janela de declaração RFB ou logo após** — prazo de entrega vai até 31/maio de N+1; retificadoras chegam meses depois. Dado é **provisório** mesmo após o prazo: malha fina, retificadora, retificação de pré-preenchida.
3. **Ano com lacuna estrutural** — falta CPF de cônjuge que declarou no ano anterior, OU todas as declarações do ano são shell pós-dedup, OU única declaração é pobre (pj=0 + ir_pago=0 + bruta < piso de isenção). Pode ser:
   - dado faltando (usuário não subiu IRPF do cônjuge);
   - mudança estrutural real (divórcio, óbito, dependente emancipado, aposentadoria).
   O produto **não pode inferir qual** sem confirmação humana.

**Caso real (workspace `1b9f2cf5...`, 2026-05-23):** mesmo pós-dedup, o ano-base 2025 do casal tem:
- 1 vencedor para DAVID -36 (pj=1, iso=2, ir_pago=0)
- 1 shell para DAVID -87 (OCR-collision com -36)
- **Mariana ausente** (presente em 2023 e 2024)

Renda bruta agregada do ano-base 2025 = R$ 5.469,95 — apresentar isso como "Renda Anual Familiar · 2025" no card é informação ativa errada, mesmo sendo o dado correto do que foi entregue.

**Razão de abrir ADR** ([[ADR-188]] policy "ADR Proposto antes de PR P0/P1"): mudança em contrato observável de `irpf_kpis` (4 campos novos no payload E5), schema bump (`config/schemas/e5_analysis.schema.json`), e regra de domínio que vira teste regressivo. Sem ADR, vira lógica espalhada entre analyzer + serializer + card + chart.

## Decisão

### Estados (enum `CompletudeAno`)

| Estado | Significado | UX consequente |
|---|---|---|
| `completo` | Ano fiscalmente fechado **E** continuidade familiar **E** ≥ 1 decl não-shell | Card opina, número grande, sem badge |
| `provisorio` | Prazo RFB ainda aberto (hoje < 1jun de N+1) com ≥ 1 decl não-shell | Card mostra com badge "Provisório — em entrega" (não esconde) |
| `incompleto` | Prazo fechado **mas** continuidade quebrada OU todas declarações são shell pós-dedup | Card pula para último `completo`; banner explica motivo |
| `mudanca_estrutural` | **Reservado** — não atribuído automaticamente. Bool aplicado posteriormente via confirmação humana no console interno (lane futura). Por ora: nunca retornado. |

### Critérios objetivos (na ordem de avaliação)

Dado um ano-base $N$ com as declarações já deduplicadas:

1. **Prazo RFB**: se `hoje < 1º de junho de N+1`, retorna `provisorio` (se houver ≥ 1 decl não-shell) ou `incompleto` (se todas shell ou ano vazio).
2. **≥ 1 decl não-shell**: se todas as declarações de $N$ são shell pós-dedup, retorna `incompleto`. Motivo: "nenhuma declaração com dados de renda".
3. **Continuidade familiar**: seja $C_N$ = conjunto de `cpf_masked` distintos com decl não-shell em $N$. Se existe $N' < N$ com $|C_{N'}| > |C_N|$ E $C_{N'} \not\subseteq C_N$, retorna `incompleto` com motivo "falta declaração de CPF ***-XX (presente em $N'$)".
4. Caso contrário: `completo`.

### API exposta

```python
class IRPFAnalyzer:
    def completude_ano(self, ano: int) -> CompletudeAno: ...
    def completude_motivo(self, ano: int) -> str | None: ...
    def ano_base_default(self) -> int | None: ...
    def anos_completude_por_ano(self) -> dict[int, CompletudeAno]: ...
```

`ano_base_default` retorna o **último ano completo** disponível; fallback: último provisório; fallback: último incompleto; `None` se sem declarações.

### Payload `irpf_kpis` no E5 (4 campos novos)

```json
{
  "irpf_kpis": {
    "ano_base": 2024,                     // já existia (último disponível)
    "ano_base_default": 2024,             // novo: o que o card deve usar
    "ano_base_completude": "completo",    // novo: estado do ano_base_default
    "completude_motivo": null,            // novo: string explicativa quando != completo
    "anos_completude_por_ano": {          // novo: state por ano (para o chart)
      "2023": "incompleto",
      "2024": "completo",
      "2025": "incompleto"
    }
  }
}
```

`ano_base` mantido (último ano com dados). `ano_base_default` é o sinal opinado.

### Não-decisões (out of scope desta ADR)

- **Inferir `mudanca_estrutural`** (separação, óbito). Requer confirmação humana, virá em lane do console interno admin (`ops.mathoms.ai`, plano [INTERNAL_ADMIN](../plan/INTERNAL_ADMIN/_README.md)). Por ora o enum tem o valor reservado mas nunca é retornado pelo analyzer.
- **Retificadora vs original** (qual fragmento é "mais recente"). Já resolvido pelo `tie_break_key` do dedup; ADR-266 só consome o resultado.
- **UX do card**: card vê os 4 campos e decide se opina/avisa/colapsa. ADR separada para microcopy + variantes visuais.

## Consequências

**Positivas:**
- Card e chart deixam de mostrar "última verdade" enquanto há sinal forte de lacuna.
- 4 campos novos viram contrato testável (snapshot OpenAPI atualizado).
- Telemetria: `ano_base_completude` por workspace vira métrica de qualidade de dados.

**Negativas / custos:**
- Casos legítimos (cliente em IF vivendo só de isentos) podem virar falso-positivo de `incompleto`. Mitigação: regra de continuidade familiar; se único declarante de N-1 é o mesmo de N, satisfaz critério 3 mesmo com renda baixa.
- Cliente que entrega declaração só em maio vira `provisorio` brevemente. Não-impactante — banner explica.
- Schema bump exige `make update-openapi-snapshot` no PR de implementação ([[ADR-109]]).

**Risco residual:** se o usuário tem realmente uma lacuna estrutural não confirmada (divórcio recente sem update no Mathoms), `incompleto` aparece como "dado faltando" e o usuário pode achar que precisa subir mais PDF — quando na verdade precisa atualizar a configuração de família. Aceito porque pedir confirmação ativa é mais seguro que silenciosamente "naturalizar" a queda.

## Alternativas consideradas

**A — Boolean simples `completo: bool`.** Rejeitado: colapsa `provisorio` (ano em curso) com `incompleto` (lacuna estrutural), e nega ao usuário a info de que 2025 está em janela legítima de entrega.

**B — Inferir `mudanca_estrutural` automaticamente** (financial-planner alertou). Rejeitado: produto não pode declarar divórcio/óbito por queda de renda. Caso real: 1 cônjuge para de trabalhar para cuidar de filho — queda de 50% YoY é fato, não anomalia. Confirmação humana é obrigatória.

**C — Heurística pura de "renda < 10% do ano anterior"** (sugestão inicial do agente). Rejeitado pelo financial-planner: falso-positivo para aposentado-de-isentos (cliente Perini típico no estágio IF) e ano-sabático legítimo. Critério estrutural (continuidade de CPFs declarando) é mais robusto.

## Implementação

PR2 da lane A16 L2 (irpf-dedup + completude):

1. `pipeline/domain/services/irpf_completude.py` — `CompletudeAno` enum + função pura `compute_completude(decls, ano, today)` testável isolada
2. `IRPFAnalyzer` ganha 4 métodos (`completude_ano`, `completude_motivo`, `ano_base_default`, `anos_completude_por_ano`)
3. `scripts/e5_analyze._e5_kpis_basicos` expõe 4 campos novos em `irpf_kpis`
4. `config/schemas/e5_analysis.schema.json` — bump
5. Snapshot OpenAPI atualizado
6. Testes:
   - Pura: combinações de prazo × continuidade × shell
   - Regressão workspace `1b9f2cf5...`: 2023=incompleto (Mariana sozinha), 2024=completo (casal), 2025=incompleto (Mariana ausente)
   - Edge: workspace sem nenhuma decl, com só 1 ano, com 5 anos mistos
