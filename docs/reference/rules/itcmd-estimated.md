---
id: RULE-itcmd-estimated
type: domain-rule
concept: "ITCMD estimado por UF (alíquota × patrimônio bruto)"
canonical_adr: "[[ADR-192]]"
enforcer_modules:
  - pipeline/domain/services/protection/itcmd_estimator.py
tags:
  - type/domain-rule
  - area/domain
---

# RULE — ITCMD estimado

**Conceito.** Estimativa de ITCMD (Imposto sobre Transmissão Causa Mortis e Doação) sobre patrimônio bruto declarado, por UF do titular. Alíquota = `aliquota_pct_por_uf[UF]`; ITCMD = `patrimônio_bruto × alíquota / 100`.

**Por quê.** Sucessão sem planejamento expõe a família a ITCMD pago em dinheiro vivo dentro de 60-180 dias (depende da UF) **antes** da partilha — força venda forçada de ativos ilíquidos. Estimativa serve para o cliente dimensionar a reserva sucessória ou avaliar instrumentos (seguro de vida específico para ITCMD, holding familiar, doações em vida com reserva de usufruto). Calculator **não** recomenda instrumentos — sinaliza valor estimado e dispara `RiskInferred` para o cliente discutir com planejador habilitado.

**Doutrina canônica.** Decidida em [ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3 (Sprint A11.W5, S9-T03). Calculator puro (ADR-097 D3 / ADR-111). Tabela de alíquotas é **injetada** pelo adapter — ADR-192 §"Atualizações pós-revisão" exige que thresholds fiscais venham de `fiscal_parameters` (ADR-135) por `effective_date`, **não hardcoded**. Tabela default no populator (`_ITCMD_ALIQUOTAS_DEFAULT_PCT`) é débito documentado para migração à coluna `fiscal_parameters.itcmd_aliquota_por_uf`.

**Enforcer.**
- [`pipeline/domain/services/protection/itcmd_estimator.py`](../../../pipeline/domain/services/protection/itcmd_estimator.py) — `itcmd_estimated(ITCMDInputs) -> ITCMDEstimate`. UF case-insensitive (normaliza para upper); UF não-mapeada degrada graciosamente para 0 com warning textual no rationale. Emite `RiskInferred("sucessorio_itcmd_estimado")` quando ITCMD > R$ 10k.
- Populator app-layer: [`backend/app/services/protection_bundle_populator.py`](../../../backend/app/services/protection_bundle_populator.py) injeta `_ITCMD_ALIQUOTAS_DEFAULT_PCT` (26 estados + DF — 27 UFs) na vigência atual.

**Disclaimer fiduciário.** "Estimativa metodológica baseada em Tabela ITCMD `<UF>` (fiscal_parameters); não constitui recomendação fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. Dados fiscais válidos para `<effective_date>`."

**Fórmula.**

```
itcmd_brl_cents = patrimônio_bruto_brl_cents × aliquota_pct[UF] / 100

dispara_risk    = itcmd_brl_cents > R$ 10k   (impacto material para
                                              motivar planejamento sucessório)
```

**Alíquotas default (referência conservadora, em revisão para `fiscal_parameters`).**

| UF | Alíquota | UF | Alíquota | UF | Alíquota |
|---|---|---|---|---|---|
| AC | 4% | ES | 4% | PE | 8% |
| AL | 4% | GO | 8% | PI | 6% |
| AM | 2% | MA | 7% | PR | 4% |
| AP | 4% | MG | 5% | RJ | 8% |
| BA | 8% | MS | 6% | RN | 6% |
| CE | 8% | MT | 8% | RO | 4% |
| DF | 6% | PA | 4% | RR | 4% |
|   |   | PB | 8% | RS | 6% |
|   |   |   |   | SC | 8% |
|   |   |   |   | SE | 8% |
|   |   |   |   | SP | 4% |
|   |   |   |   | TO | 4% |

Alíquotas reais variam por progressividade (alguns estados aplicam tabela em vez de alíquota linear). Calculator T03 usa alíquota linear como aproximação conservadora — refinamento progressivo entra em ondas futuras quando `fiscal_parameters.itcmd_aliquota_por_uf` (JSON por vigência) for criada.

**Casos de teste.** [tests/pipeline/domain/services/protection/test_itcmd_estimator.py](../../../tests/pipeline/domain/services/protection/test_itcmd_estimator.py) cobre 9 perfis:
- solteiro SP patrimônio zero,
- casado MG 2M (5%),
- expatriado RJ 5M (8%),
- UF desconhecida (degrada para 0),
- UF lowercase (normaliza),
- ITCMD imaterial (< R$ 10k),
- disclaimer presente,
- idempotência,
- patrimônio negativo (zera).

**Metodologias.** Não há doutrina metodológica disputada — a regra é aplicação direta de legislação fiscal estadual. Calculator carrega apenas a abstração computacional + integração com fluxo Mathoms.
