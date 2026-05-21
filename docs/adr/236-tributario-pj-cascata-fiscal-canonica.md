---
id: ADR-236
type: adr
title: "Tributário PJ — Cascata Fiscal canônica (cálculo por regime, base PGBL real, inputs derivados ≫ declarados)"
status: Proposto
phase: A17.tributario-pj-cascata
date: "2026-05-20"
relates_to:
  - "[[ADR-143]]"
  - "[[ADR-157]]"
  - "[[ADR-180]]"
  - "[[ADR-097]]"
  - "[[ADR-102]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 236"
  - "Cascata Fiscal PJ"
  - "Tributário PJ canônico"
  - "PGBL base correta"
tags:
  - type/adr
  - status/proposto
  - area/methodology
  - area/pipeline
  - area/persistence
  - area/report
  - methodology/perini
  - methodology/cerbasi
  - methodology/auvp
  - phase/a17
---

## Contexto

Sprint A10.7 ([[A10.7]] / migration `b1a2c3d4e5f7`) adicionou `Workspace.business_profile_json` com Pydantic `BusinessProfile` mínimo: `contador`, `regime` (enum `mei|simples|lucro_presumido|lucro_real`), `holding_prazo_meses`. Intenção declarada: substituir a chave `tributario` do legado `goals.json`.

Sessão 2026-05-20 (workspace dogfood) revelou três problemas em produção no card S8 "Tributário PJ — Cascata Fiscal":

1. **Wiring incompleto** — `backend/app/services/pipeline_adapter.py::build_goals_payload_sync` nunca lê `business_profile_json` nem injeta `bundle["tributario"]`. Migration A10.7 ficou pela metade.

2. **Nomes não casam** — `pipeline/domain/services/narrativas/charts_narrator.py::impostos_pj` (linha ~255) espera `contador_nome`, `regime_obs` (string livre), `holding_avaliacao_prazo` (string) — `BusinessProfile` tem `contador`, `regime` (enum), `holding_prazo_meses` (int).

3. **Texto canned conceitualmente errado** (validação `financial-planner` 2026-05-20):
    - **Mistura Simples × Presumido** — "DAS estimado" (Simples) + "Lucro presumido (32%) define base tributável" (Presumido). PJ não está nos dois regimes.
    - **Base PGBL errada** — texto afirma que `receita_pj × 32% = R$ 60,5k` é base PGBL. **Não é.** Limite 12% PGBL incide sobre **renda tributável PF** (pró-labore + aluguéis + outras tributáveis declaradas na ficha "Rendimentos Tributáveis"). Lucros distribuídos são **isentos** e **não contam** para a base. Sócio com pró-labore mínimo (R$ 1.500/mês) + R$ 40k/mês de lucros isentos tem base PGBL ≈ R$ 18k/ano — limite dedutível ~R$ 2,2k/ano, independente de receita PJ ser R$ 500k ou R$ 5M.
    - **Declaração simplificada anula PGBL** — desconto simplificado (20% até R$ 16.754,34 em 2025) substitui todas deduções legais incluindo PGBL. Card não cruza esse dado.

A presunção 32% que aparece no texto é base de **IRPJ/CSLL no regime Presumido**, conceito completamente independente do limite PGBL. Misturar os dois é confusão metodológica clássica de planejamento amador — exatamente o que Mathoms existe para corrigir.

Referência: Perini "Viver de Renda" cap. previdência privada · AUVP módulo previdência · Cerbasi "Como organizar sua vida financeira" cap. renda variável PJ. Co-design completo (Q1-Q5) registrado em `docs/plan/TRIBUTARIO_PJ/_README.md` §Origem.

## Decisão

Adotar **modelo de domínio expandido + cascata calculada por regime + inputs derivados ≫ declarados + decision triggers parametrizados** com 6 mudanças coordenadas. V1 cobre Simples (Anexo III/V) + Presumido + MEI (>95% da ICP atual); Lucro Real e multi-PJ ficam para V2.

### D1 — `BusinessProfile` expandido + UI captura

Migration Alembic adiciona campos não-derivados ao `business_profile_json`:

```python
class BusinessProfile(BaseModel):
    # Campos A10.7 (preservados)
    contador: Optional[str] = None
    regime: Optional[Literal["mei", "simples", "lucro_presumido", "lucro_real"]] = None
    holding_prazo_meses: Optional[int] = Field(default=None, ge=0, le=240)

    # Campos A17 (novos — declarados pelo consultor, não derivam de transação/IRPF)
    anexo_simples: Optional[Literal["III", "V"]] = Field(
        default=None,
        description="Anexo do Simples (relevante só quando regime=simples). III: serviços com fator-R≥0,28; V: <0,28.",
    )
    iss_aliquota_pct: Optional[float] = Field(
        default=None, ge=2.0, le=5.0,
        description="Alíquota ISS municipal aplicável ao CNAE principal. 2-5% conforme Lei Complementar 116/2003.",
    )
    cnae_principal: Optional[str] = Field(
        default=None, max_length=10,
        description="CNAE 7-dígitos (formato 'NNNN-N/NN'). Valida Anexo Simples + ISS.",
    )
    tipo_declaracao_ir: Optional[Literal["completa", "simplificada"]] = Field(
        default=None,
        description="Modelo IRPF da pessoa física. Simplificada anula dedução PGBL.",
    )

    model_config = {"extra": "forbid"}
```

UI de captura no console interno (`ops.mathoms.ai`, [[ADR-116]]) — admin operador preenche durante onboarding do workspace. Workspace sem `BusinessProfile` completo renderiza estado "perfil tributário pendente" no card, **não** inventa valores.

**Por que não pedir ao usuário final?** Anexo Simples e ISS exigem conhecimento de CNAE/atividade — fora do escopo do usuário ICP. Captura via consultor durante setup.

### D2 — Inputs derivados do pipeline (não pedidos)

Os valores que **mudam ao longo do tempo** derivam de transações + IRPF, **não** vivem em `BusinessProfile`:

| Campo derivado | Fonte | Como |
|---|---|---|
| `pro_labore_mensal_brl` | E4 (categorize_transactions) | Label nova `pro_labore` em `category_template` — transferência PJ→sócio classificada. Discriminador: origem `account_type=PJ` + destino `member_key=titular_pj`. |
| `lucros_distribuidos_mensal_brl` | E4 | Label nova `lucros_distribuidos` — transferência PJ→sócio que **não** é pró-labore. Resíduo no fluxo. |
| `das_pago_mensal_brl` | E4 | Label nova `das_simples` — débito automático/guia DAS. |
| `folha_pj_mensal_brl` | E4 | Label `folha_pj` — pagamentos a CLT da PJ (não-sócio). |
| `iss_pago_mensal_brl` | E4 | Label nova `iss` (só aplicável em Presumido com ISS destacado). |
| `receita_pj_anual_brl` | E3 (reconcile_transactions) | Soma de créditos PJ na janela 12m móvel. **Já calculado** em `e5n_narrativas.py:374`. |
| `outras_rendas_tributaveis_pf_anual_brl` | E1.6 ([[ADR-157]] `extract_irpf_full`) | Soma da ficha "Rendimentos Tributáveis" do IRPF (aluguéis, salários CLT, RPA, ganhos tributáveis). |
| `fator_r_pct` | Calculator (D3) | `(folha_pj_mensal_brl + pro_labore_mensal_brl) × 12 / receita_pj_anual_brl × 100`. |

**Princípio:** se o pipeline já tem o dado em E3/E4/E1.6, **não pedimos ao consultor**. Reduz fricção de captura + garante consistência interna do relatório (números do card S8 batem com cat_1 patrimonial e com IRPF declarado).

### D3 — Calculator canônico (rules-as-code, ADR-143)

`pipeline/domain/services/tributario/cascata_calculator.py` — módulo novo, puro (sem `fastapi`/`sqlalchemy`/`celery`), recebe value object tipado:

```python
@dataclass(frozen=True)
class CascataInput:
    regime: Literal["mei", "simples", "lucro_presumido", "lucro_real"]
    anexo_simples: Optional[Literal["III", "V"]]
    iss_aliquota_pct: Optional[Decimal]
    tipo_declaracao_ir: Literal["completa", "simplificada"]
    receita_pj_anual: Money
    pro_labore_mensal: Money
    lucros_distribuidos_mensal: Money
    folha_pj_mensal: Money
    das_pago_mensal: Money
    iss_pago_mensal: Money
    outras_rendas_tributaveis_pf_anual: Money

@dataclass(frozen=True)
class CascataOutput:
    # Cascata (camadas, na ordem de apuração)
    receita_bruta: Money
    tributos_federais: Money            # DAS no Simples; PIS+COFINS+IRPJ+CSLL no Presumido
    iss_total: Money                    # 0 no Simples (embutido no DAS); destacado no Presumido
    lucro_contabil_pj: Money            # receita - tributos - custos PJ
    pro_labore_bruto: Money
    inss_patronal: Money                # 20% s/ pró-labore (sem teto)
    inss_empregado: Money               # 11% s/ pró-labore até teto
    irrf_pro_labore: Money              # tabela progressiva
    lucros_distribuidos: Money          # isentos (informativo)
    renda_pf_tributavel_total: Money    # pró-labore tributável + outras tributáveis IRPF
    carga_total_pct: Decimal            # (tributos_federais + iss + inss_patronal + irrf) / receita_bruta

    # PGBL
    pgbl_base_anual: Money              # = renda_pf_tributavel_total (NÃO receita PJ × 32%)
    pgbl_limite_anual: Money            # = pgbl_base * 0.12
    pgbl_aplicavel: bool                # False se tipo_declaracao_ir="simplificada"
    pgbl_motivo_inaplicavel: Optional[str]

    # Fator-R (só relevante regime=simples)
    fator_r_pct: Optional[Decimal]
    fator_r_faixa: Optional[Literal["anexo_iii", "anexo_v", "limite"]]
    fator_r_break_even: Optional[Money]  # quanto subir folha pra mudar faixa

    # Decision triggers (lista; podem ser 0)
    triggers: list[CascataTrigger]

def compute(input: CascataInput) -> CascataOutput: ...
```

**Cobertura V1:**
- ✅ Simples Nacional (Anexo III/V) com fator-R derivado + break-even
- ✅ Lucro Presumido (PIS 0,65% + COFINS 3% + IRPJ 15%/25% sobre presunção 32% + CSLL 9% sobre presunção 32% + ISS destacado)
- ✅ MEI (DAS-MEI fixo + teto R$ 81k)
- ⏸ Lucro Real (V2 — exige escrituração contábil, fora do escopo)
- ⏸ Multi-PJ (V2 — assume 1 PJ/workspace)

**Goldens** em `tests/test_cascata_calculator.py`: 1 por regime + 1 com workspace incompleto (sem `BusinessProfile`). Paridade ±2% com cálculo manual de contador para dogfood workspace `5@5.com`.

### D4 — Adapter + narrator reescrito

`pipeline_adapter.build_goals_payload_sync` chama `cascata_calculator.compute(...)` e injeta no `bundle["tributario"]` formato compatível com narrator novo:

```python
payload["tributario"] = {
    "regime": bp.regime,
    "regime_label": _regime_to_label(bp.regime, bp.anexo_simples),  # "Simples Nacional — Anexo III"
    "cascata": dataclasses.asdict(cascata_output),  # estrutura D3
    "contador_nome": bp.contador,
    "holding_prazo_meses": bp.holding_prazo_meses,
    "_source": "db:business_profile_json + e3/e4/e1.6 derived",
}
```

`charts_narrator.impostos_pj` reescrito — ramifica por `regime`, **sem hard-code** de "32%" ou "Lucro presumido":

```python
"impostos_pj": self._narrate_cascata(M, ctx)  # método novo, ramifica por regime
```

Workspace sem `BusinessProfile` completo: narrator retorna `{"context": "Perfil tributário PJ pendente — peça ao seu consultor preencher anexo/CNAE/ISS para ver a cascata fiscal completa.", "conclusion": ""}`. Card UI renderiza estado "pendente" com CTA, não texto inventado.

**Regression test obrigatório:** `tests/test_charts_narrator.py::test_impostos_pj_no_hardcoded_lucro_presumido` — string `"Lucro presumido (32%)"` não pode aparecer no output de nenhum workspace simples.

### D5 — Card UI cascata real (substitui NarrativeChartCard)

`<CascataFiscalCard/>` em `frontend/src/components/report/`, co-design `product-designer` (lane separada, briefing após P3). Substitui o uso de `NarrativeChartCard chartId="impostos_pj"` em `S8PrevidenciaSection`. Conteúdo mínimo V1:

1. **Header:** regime + label completa ("Simples Nacional — Anexo III" / "Lucro Presumido") + badge fator-R quando aplicável.
2. **Cascata** — decomposição em camadas (waterfall ou steps verticais):
    - Receita bruta PJ → R$ X
    - − Tributos federais → R$ Y (% efetivo)
    - − ISS → R$ Z (quando destacado)
    - = Lucro contábil PJ → R$ A
    - − Pró-labore bruto + INSS patronal + IRRF → R$ B
    - = Lucros distribuídos (isentos) → R$ C
    - **Carga total: W%**
3. **Base PGBL** — bloco separado:
    - "Renda tributável PF anual: R$ X (pró-labore + outras rendas tributáveis IRPF)"
    - "Limite dedução PGBL (12%): R$ Y/ano"
    - Flag amarelo se `tipo_declaracao_ir="simplificada"`: "PGBL não dedutível — desconto simplificado escolhido"
4. **Decision triggers** — 0-5 callouts com break-even explícito quando aplicável (D6).
5. **Disclaimer obrigatório** (rodapé sutil): "Valores estimados a partir de movimentações reconhecidas e IRPF processado. Confirme com seu contador antes de qualquer decisão tributária."

A11y AAA, mobile responsive, `<MonetaryValue/>` em todos os valores, design tokens (sem hex literal).

### D6 — Decision triggers canônicos (parametrizados, não pareceres)

V1 implementa 5 gatilhos canônicos validados por `financial-planner` 2026-05-20:

| # | Trigger | Condição | Break-even mostrado | Copy pattern |
|---|---|---|---|---|
| T1 | **Otimização pró-labore × lucros** | `pgbl_aplicavel=True` E `pgbl_base_anual < pgbl_limite_anual_potencial(pro_labore_otimo)` | "Subir pró-labore em R$ X/mês ocuparia limite PGBL de R$ Y/ano, deduzindo R$ Z de IR. Custo INSS patronal adicional: R$ W/mês. Payback: V meses." | "Considere avaliar..." |
| T2 | **Fator-R break-even** | `regime=simples` E (`fator_r_pct < 28%` E `proximidade < 5pp`) OU (`fator_r_pct ≥ 28%` E `margem < 3pp`) | "Subir folha em R$ X/mês manteria Anexo III (alíquota inicial 6%). Migrar para V custaria +9,5pp sobre receita = R$ Y/ano." | "Sinal de atenção:" |
| T3 | **PGBL alíquota-dependente** | `tipo_declaracao_ir="completa"` E `pgbl_aplicavel=True` E `ir_marginal_estimado_pct ≥ 22.5` | "Sua alíquota IR marginal estimada é X%. PGBL é dedutível e oferece tabela regressiva (10% após 10 anos). Considere aporte de R$ Y/ano (12% da base)." | "Oportunidade:" |
| T4 | **Holding ≥3 imóveis alugados** | `>=3` imóveis com `classification=locado` E `receita_aluguel_anual > R$ 60k` | "Você tem N imóveis locados gerando R$ X/ano. PJ-aluguel (Presumido, 11,33% s/ receita) vs PF (até 27,5% IRPF) pode economizar R$ Y/ano. Avalie holding patrimonial com tributarista." | "Considere avaliar..." |
| T5 | **Sublimite estadual Simples** | `regime=simples` E `receita_pj_anual > R$ 3.0M` (80% do sublimite R$ 3.6M) | "Receita PJ projetada de R$ X/ano se aproxima do sublimite estadual R$ 3,6M (após este o estado pode exigir ICMS no Simples). Distância: R$ Y. Janela para planejamento exit: Z meses." | "Sinal de atenção:" |

**Copy patterns obrigatórios (limite CRC):**
- ✅ "Considere avaliar..." / "Sinal de atenção:" / "Oportunidade:"
- ❌ "Você deve..." / "Recomendamos..." / "O melhor regime é..."
- ✅ Disclaimer obrigatório em todo card: "Valores estimados — confirme com seu contador."
- ❌ Cálculo de imposto devido específico para o ano-calendário (linha CRC: requer contador).

**Folclore explicitamente rejeitado** (não vira trigger):
- ❌ "Holding patrimonial > R$ X de patrimônio" — gatilho real é sucessão multi-herdeiro + ITCMD estadual, não patrimônio absoluto. T4 cobre o caso comum (>3 alugados); resto fica V2.
- ❌ "Anuiza receita via lucros isentos no teto Simples" — teto Simples é faturamento, não distribuição. Confusão clássica.

**Telemetria** estruturada (zero PII fiscal — só categorias):
- `mathoms.tributario.cascata_rendered` — `regime`, `has_complete_profile`, `triggers_count`
- `mathoms.tributario.trigger_shown` — `trigger_code` (T1-T5), `regime`
- `mathoms.tributario.profile_incomplete` — `missing_fields`
- **Nunca:** valores monetários, nome de PJ, CNPJ, receita_pj_anual.

## Alternativas consideradas

- **(B) Hot-fix mínimo — só conectar `business_profile_json` no adapter + traduzir enums + remover frase do PGBL no narrator.** Rejeitada: o card continua sem "cascata fiscal" real. Conserta strings (N1+N2) mas mantém N3. Usuário (2026-05-20) escolheu solução completa em vez do hot-fix. Card mentiroso em prod ~2 semanas — trade-off aceito.

- **(C) Esconder o card via `report_layout.yaml` até V1 shippar.** Rejeitada na mesma sessão. Usuário priorizou progresso visível para outros usuários (workspaces não-dogfood não viam o problema; remover regrediria expectativa).

- **(D) Pedir todos os valores derivados (pro_labore, lucros, folha) ao consultor em form.** Rejeitada: triplica fricção de captura + cria inconsistência (consultor digita pró-labore R$ X, pipeline reconcilia transferência R$ Y, qual ganha?). Princípio "derivado ≫ declarado" mantém número do card = número do extrato.

- **(E) Suportar Lucro Real no V1.** Rejeitada: Lucro Real exige escrituração contábil (LALUR, depreciações, ajustes IRPJ) — Mathoms não tem essa data nem deveria ter (linha CRC). V2 quando ICP de cliente Lucro Real materializar.

- **(F) Multi-PJ no V1.** Rejeitada: complica `BusinessProfile` (vira coleção) + classifier E4 (`member_key` precisa de `pj_id`) sem ICP atual para justificar. Quando segundo workspace com 2 PJs aparecer, abrir ADR follow-up.

- **(G) Decision triggers em YAML (rules-engine externa).** Rejeitada: viola [[ADR-143]] (methodology = code). Regras tributárias mudam com legislação — diff em Git é audit-trail; YAML editável em prod é foot-gun. Triggers vivem em `cascata_calculator.py`.

- **(H) Renderer HTML server-side dedicado para o card.** Rejeitada: viola [[ADR-129]] (renderer HTML server-side descontinuado; React é renderer único). `<CascataFiscalCard/>` é componente React normal.

- **(I) Cache de cascata em DB (`workspace_tributario_snapshot`).** Rejeitada V1: cascata é projeção pura de inputs já persistidos (`business_profile_json` + E3/E4/E1.6 artifacts). Recomputar é ~5ms; cache adiciona invalidation complexity. Considerar V2 se latência virar problema.

- **(J) Modelo completo de holding (gatilhos sucessão + ITCMD + PJ-aluguel + imóveis improdutivos).** Rejeitada V1: requer dados de membros familiares (idade, herdeiros) + ITCMD por UF + classificação fiscal de cada imóvel. Lane separada V2. V1 cobre T4 (caso ICP comum: >3 alugados).

## Consequências

**Positivas**

- ✅ Card S8 deixa de mostrar texto canned conceitualmente errado em produção.
- ✅ Base PGBL canônica (= renda tributável PF) — alinhada com Perini/AUVP. Mathoms para de propagar a confusão metodológica de "receita PJ × 32% = base PGBL" que circula em material amador.
- ✅ Inputs derivados (E3/E4/E1.6) ≫ declarados — número do card S8 bate com cat_1 patrimonial e com IRPF declarado. Sem inconsistência interna.
- ✅ Rules-as-code (ADR-143) preservado — fórmula da cascata vive em `cascata_calculator.py` + docstring + ADR-236. Diff em Git é audit-trail metodológico.
- ✅ Pattern reutilizável — `<CascataFiscalCard/>` pode virar template para outros cards de decomposição (ex.: cascata da reserva, cascata de aportes).
- ✅ Decision triggers parametrizados expõem trade-off (break-even em R$/meses), não veredito — copy "considere avaliar" respeita linha CRC sem virar inútil.

**Negativas**

- ⚠️ Schema `BusinessProfile` cresce de 3 para 7 campos. Mitigação: todos opcionais (workspace incompleto degrada graciosamente); UI captura no console interno (consultor preenche, não o usuário final).
- ⚠️ Classifier E4 ganha 5 labels novas (`pro_labore`, `lucros_distribuidos`, `das_simples`, `folha_pj`, `iss`) — complexity de category template. Mitigação: labels têm discriminador estrutural (`account_type=PJ`, `member_key=titular_pj`) que reduz ambiguidade.
- ⚠️ Cascata calculator é ~400 linhas com 4 regimes — testabilidade exige goldens robustos. Mitigação: 1 golden por regime + paridade com contador real do dogfood (`5@5.com`).
- ⚠️ V1 não cobre Lucro Real nem multi-PJ — workspaces avançados ficam sem card. Mitigação: estado "regime não suportado" + CTA suporte; V2 documentado.
- ⚠️ Reforma tributária / PEC dividendos pode quebrar cascata. Mitigação: ADR documenta gatilho de revisão; schema evolution previsível.

**Riscos**

| Risco | P | Mitigação |
|---|---|---|
| Classifier E4 confunde pró-labore com salário CLT do cônjuge | P1 | Discriminador estrutural: origem `account_type=PJ` + destino `member_key=titular_pj`. Teste com workspace multi-membro. |
| Workspace sem IRPF processado — base PGBL = 0 mesmo com renda real | P2 | Estado UI explícito "renda tributável PF não detectada — sem IRPF processado"; CTA upload IRPF. Não infere base PGBL de pró-labore só (sub-estima quando há aluguéis). |
| Fator-R cai por sazonalidade (férias coletivas) e gera trigger T2 falso | P2 | Janela 12m móvel suaviza; copy "fator-R móvel 12m" deixa premissa explícita; threshold de "proximidade < 5pp" só dispara T2 se persiste 3m. |
| LGPD: telemetria de carga tributária vaza | P0 | Telemetria só registra `regime`, `trigger_code`, `event_type` — nunca `receita_pj_anual`, `pro_labore_mensal`, ou nome PJ/CNPJ. Gate em `backend/app/core/logging.py` (denylist). |
| Decision trigger T1 ("subir pró-labore") mal-calibrado gera dívida fiscal | P0 | Copy patterns ADR-236 §D6 obrigatórios + disclaimer + threshold conservador (T1 só dispara se base PGBL < 80% do limite potencial). Não recomenda subir além do break-even IR/INSS. |
| Workspace com `regime=lucro_real` (fora do escopo V1) vê card vazio sem explicação | P2 | Estado UI explícito "Lucro Real — cascata em desenvolvimento (V2)" + CTA suporte. Não invento. |
| Folclore "holding patrimonial > R$ X" volta via PR de algum agente | P2 | T4 documenta condição real (>3 alugados + R$ X receita); gate em `tests/test_cascata_calculator.py::test_no_holding_trigger_by_absolute_patrimonio`. |
| Adapter regression — `bundle["tributario"]` chega com shape errado e narrator quebra | P1 | Pydantic model `TributarioBundleSection` valida shape no boundary; `tests/test_pipeline_adapter.py::test_tributario_section_shape`. |
| Card mentiroso em produção ~2 semanas até P4 shipping | P1 | Aceito pelo usuário 2026-05-20 (escolha de solução completa sem hot-fix). Mitigação: P1-P4 priorizados sobre P5/P6 cosméticos. |

## Gates

- **Migration Alembic** — `business_profile_json` ganha 4 chaves novas (Pydantic `extra=forbid` enforça). Workspace existente fica com novos campos `None` até consultor preencher. Downgrade reversível.
- **Endpoint PATCH** `/workspaces/{id}/business-profile` — `response_model=BusinessProfileResponse` ([[ADR-102]] R18). `make update-openapi-snapshot` commitado.
- **`cascata_calculator.compute(input: CascataInput) -> CascataOutput`** puro em `pipeline/domain/services/tributario/` — sem imports `fastapi`/`sqlalchemy`/`celery` ([[ADR-097]] boundary). `dev/check_pipeline_boundaries.py` enforça.
- **4 goldens** em `tests/test_cascata_calculator.py` — Simples-III, Simples-V, Presumido, workspace_incompleto. Paridade ±2% com contador real (dogfood `5@5.com`) — gate manual.
- **Regression test no narrator** — `tests/test_charts_narrator.py::test_impostos_pj_no_hardcoded_lucro_presumido` garante string "Lucro presumido (32%)" sumiu do output.
- **5 decision triggers** com break-even computado (não copy genérico). `tests/test_cascata_calculator.py::test_triggers_break_even_computed`.
- **Telemetria** registrada em `backend/app/core/logging.py` com denylist de PII fiscal (gate em `tests/test_telemetria_lgpd.py::test_tributario_no_money_in_logs`).
- **UI A11y AAA** — `<CascataFiscalCard/>` passa axe-core (zero violations) + Lighthouse ≥ 95.
- **Mobile** — cards stackam, fator-R badge wrap, callouts full-width.
- **Dogfood** — 2 famílias confirmam: (a) números batem com IRPF/DAS real, (b) decision triggers fazem sentido sem virar "recomendação". Gate antes do P6 flip ADR.
- **FAQ produto** — entrada nova sobre "como calcular cascata fiscal" + "por que PGBL diferente do que outras planilhas falam" (linkado da ADR).
- **Disclaimer obrigatório** — `<CascataFiscalCard/>` renderiza "Valores estimados — confirme com seu contador" no rodapé.

## Implementação

Lane **`A17.tributario-pj-cascata`** planejada para Sprint A17 (próxima a abrir pós-A15 done; A11 e A12 `paused`). ~9d eng em ~2 semanas calendário. Plano canônico: [`docs/plan/TRIBUTARIO_PJ/_README.md`](../plan/TRIBUTARIO_PJ/_README.md).

| # | PR | Effort | Gate principal |
|---|---|---|---|
| P1 | Migration + Pydantic + UI captura console interno | ~1d | Schema migration verde + form valida com Pydantic `extra=forbid` |
| P2 | Classifier E4 (5 labels novas) + integração E1.6 | ~2d | Dogfood E4 classifica 100% transferências PJ→sócio; cruza IRPF |
| P3 | `cascata_calculator.py` (4 regimes V1) + 4 goldens + triggers | ~2d | Paridade ±2% com contador real do dogfood `5@5.com` |
| P4 | Adapter + narrator reescrito + regression test "Lucro presumido" | ~1d | Card produção deixa de mostrar texto errado; bundle["tributario"] shape válido |
| P5 | `<CascataFiscalCard/>` UI + a11y + mobile + co-design product-designer | ~2d | A11y AAA; mobile responsive; copy revisado por `financial-planner` |
| P6 | Cutover + telemetria + flip ADR + FAQ produto | ~1d | Telemetria entrega; flip → `Decidido (A17.tributario-pj-cascata)` |

Flip ADR-236 → `Decidido (A17.tributario-pj-cascata)` no merge do P6.

## Follow-ups V2 (fora do escopo V1)

- **Lucro Real** — exige LALUR + depreciações + ajustes IRPJ. Cliente avançado tipicamente já tem contabilidade própria; Mathoms entra como overlay de planejamento. ADR follow-up quando ICP materializar.
- **Multi-PJ por workspace** — `BusinessProfile` vira coleção; classifier E4 precisa de `pj_id`. ADR quando segundo workspace 2-PJ aparecer.
- **Holding patrimonial — gatilhos completos** — sucessão multi-herdeiro, ITCMD por UF, PJ-aluguel formal vs informal, imóveis improdutivos. Lane separada com co-design `financial-planner` profundo (Perini cap. holding).
- **Reforma tributária / PEC dividendos** — quando aprovar, lucros distribuídos viram tributáveis em camada nova. Schema evolution previsível.
- **Comparativo Simples vs Presumido vs MEI no card** — V1 mostra apenas regime atual + cascata. V2 mostra simulação "se você migrasse para X". Decision-support poderoso, mas roça linha CRC — exige co-design adicional com `financial-planner` + revisão jurídica.
- **Cache `workspace_tributario_snapshot`** — se latência virar problema (cascata recomputa a cada render).
- **Banner soft de regime sub-ótimo** — quando trigger T2 (fator-R) ou T5 (sublimite) dispara consistentemente 6+ meses, banner no console interno alerta consultor. Telemetria mantém zero PII fiscal.
- **Renderização cascata como timeline anual** — comparar 2024 vs 2025 vs 2026 (anos fiscais), mostrar drift. Reusa pattern de `irpf_snapshots` ([[ADR-229]]).

## Referências

- **[[A10.7]]** — lane de origem do `BusinessProfile` minimal + migration `b1a2c3d4e5f7`.
- **[[ADR-143]]** — rules-as-code (methodology = code + docstring + ADR canônica).
- **[[ADR-157]]** — `extract_irpf_full` E1.6 (fonte de renda tributável PF para base PGBL).
- **[[ADR-180]]** — `GoalsBundle` (estende com nova subchave `tributario`).
- **[[ADR-097]]** — boundary pipeline↔backend (calculator puro; adapter injeta dados DB).
- **[[ADR-102]]** R18 — endpoint JSON exige `response_model` (PATCH `/business-profile`).
- **[[ADR-129]]** — renderer HTML server-side descontinuado (card é React, sem exceção).
- **[[ADR-186]]** — override sticky (consultor preenche `BusinessProfile`; não é sobrescrito por re-classificação).
- **[[ADR-229]]** — pattern `artifact → suggestion endpoint → card` (V2 cascata snapshots reusa).
- **Co-design 2026-05-20** — `financial-planner` (Q1-Q5: cascata canônica, base PGBL = renda tributável PF não receita × 32%, inputs derivados ≫ declarados, 5 triggers canônicos vs folclore, limites CRC + copy patterns).
- **Perini** "Viver de Renda" cap. previdência privada — base PGBL = renda tributável PF.
- **AUVP** módulo previdência — PGBL só em declaração completa + IR marginal ≥ 22,5% + horizonte >10 anos.
- **Cerbasi** "Como organizar sua vida financeira" cap. renda variável PJ — otimização pró-labore × lucros isentos.
- **Diagnóstico:** sessão 2026-05-20, workspace dogfood — card S8 com lacunas literais ("enquadrada no  ("), texto canned errado ("Lucro presumido 32% define base PGBL"), `bundle["tributario"]` nunca propagado.
