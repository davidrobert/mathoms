---
id: TRACK-irpf-full-schema-goldens
type: track
title: "Track IRPF Full Schema Goldens — fixtures + golden tests byte-byte"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track IRPF Full Schema Goldens — fixtures + golden tests byte-byte

> **Lane ID:** irpf-full-schema-goldens
> **Branch prefix:** `agent/irpf-full-schema-goldens/*`
> **Depende de:** [track_irpf_full_schema.md](irpf-full-schema.md) ✅ mergeada (E1.6 backend em `main` desde 2026-04-30, [ADR-157](../../../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)).
> **Conflita com:** `tests/test_llm_golden.py`, `tests/fixtures/llm_golden/`, `pipeline/llm/prompts/e16_irpf_full.py` (mudança de prompt invalida fixture). Pode rodar paralela ao `track_irpf_full_schema_ui.md`.
> **Onda:** independente.
> **ADR:** **não obrigatória** — fixtures de teste seguem padrão E1.5 já vigente.
> **Supervisão:** **G2 (`data-engineer`)** valida shape do payload sintético + cobertura de edge cases · **G0 (`financial-planner`)** valida que valores fictícios são **realisticamente** distribuídos (não zerar campos críticos para o LLM "trivializar") · **CTO sign-off** se houver fixture real (mesmo anonimizada).

> **Objetivo (1 frase):** garantir regressão byte-byte de extração IRPF (E1.6) com 2 fixtures sintéticas (modelo completo + simplificado) cobrindo edge cases críticos + opcional 1 real anonimizada — sem isso, mudança no prompt LLM passa silenciosa e bug de extração só aparece em produção.

---

## Por que esta lane

### Sintoma

Hoje o stage `extract_irpf_full` tem **22 testes unitários** ([tests/test_irpf_full_schema_unit.py](../../../../tests/test_irpf_full_schema_unit.py)) que cobrem schema/validator/analyzer com payloads sintéticos in-memory. **Não tem golden test** que cubra:

1. Mudança de prompt sem mudança intencional de output (regressão).
2. Mudança de schema Pydantic com perda de campo (regressão).
3. Edge cases reais: rendimento exterior, dependente sem CPF, dívida com ônus, modelo simplificado, 13º duplo.
4. Stage runner end-to-end com `FakeLLMClient` (sem real API key).

ADR-157 §Definition of Done lista golden byte-byte como exigência. **Sem este lane fechada, a DoD da ADR-157 fica aberta.**

### O que falta

1. **`tests/fixtures/llm_golden/e16_irpf_full_completo.json`** — output sintético de 1 declaração modelo completo, com **todos** os blocos preenchidos (rendimentos PJ + PF + exterior + isentos + exclusiva + pagamentos dedutíveis + dependentes + dívidas + bens & direitos).
2. **`tests/fixtures/llm_golden/e16_irpf_full_simplificado.json`** — output sintético modelo simplificado (PGBL deve zerar capacidade no analyzer).
3. **`tests/fixtures/llm_golden/e16_irpf_full_edge_cases.json`** — output com casos extremos (rendimento exterior com `data_conversao`, dependente `cpf_masked: null`, dívida com ônus).
4. **`tests/fixtures/llm_golden/README.md`** — atualizar com nova entrada E1.6 (origem, disclaimer LGPD, instruções de regenerar).
5. **`tests/test_llm_golden.py`** — testes que validam:
   - Cada fixture passa `IRPFFullOutput.model_validate(json)` sem erro.
   - Validator `validate_e16_output` retorna `valid=True` (zero erros) para as 3 fixtures.
   - `IRPFAnalyzer.from_payloads([fixture])` produz KPIs com valores **explicitamente esperados** no teste (não snapshot do retorno).
   - **Cross-lane shape contract:** o output de `_e5_kpis_from_analyzer(analyzer, ano)` ([scripts/e5_analyze.py:3040](../../../../scripts/analyze_finances.py)) tem **exatamente** as 11 chaves consumidas pelo `isIrpfKpis` em [frontend/src/types/irpf.ts](../../../../frontend/src/types/irpf.ts). Adicionar 1 assert que valida `set(kpis.keys()) == {"ano_base", "anos_disponiveis", "renda_anual_familiar_brl", "renda_liquida_familiar_brl", "ir_pago_total_brl", "aliquota_sobre_tributavel_pct", "aliquota_sobre_total_pct", "pgbl_capacidade_dedutivel_brl", "split_trabalho_brl", "split_capital_brl", "evolucao_renda_anos"}` — protege contra drift backend↔frontend (UI omite seção inteira se shape mudar).
6. **`tests/test_extract_irpf_full_stage.py`** — stage test com `FakeLLMClient` (em [tests/fakes/llm.py](../../../../tests/fakes/llm.py)) que devolve a fixture; assertiva: `store.read("extract_irpf_full", key)` == fixture (byte-byte com `prompt_version` consistente).
7. **(Opcional) Real anonimizada** — declaração real do dev/usuário com **todos** os CPFs trocados por `***.***.***-99/88/77`, valores multiplicados por fator aleatório, nomes substituídos. Nome de arquivo: `tests/fixtures/llm_golden/e16_irpf_real_anon_2024.json`. **Decisão de incluir é do CTO** (LGPD edge case).

---

## Regras inegociáveis

1. **Zero CPF/CNPJ real** nas fixtures — validator `validate_e16_output` rejeita CPF não-mascarado em `notes`/`descricao`/`fonte` (ADR-157 sub-decisão 5). CI vai falhar antes de mergear.
2. **`prompt_version: "e16-v1.0.0"`** explícito no payload da fixture — quando bumpar prompt, fixture detecta. Se mudar, regenerar **conscientemente** com `pytest --update-goldens` (se existir; senão, manual).
3. **Decimal-string em todos os monetary fields** — fixture deve seguir o wire ADR-090 (string com até 2 casas, regex `^-?\d+(\.\d{1,2})?$`). Sem float, sem int direto.
4. **Reconciliação cross-field deve passar** nas fixtures: `imposto_apurado.ir_pago_brl ≈ sum(rendimentos_pj.ir_retido_brl) + sum(rendimentos_pf.ir_recolhido_brl)` com tolerância 0,02 BRL.
5. **Valores realistas mas fictícios:** salário entre R$ 50k–500k/ano (faixas alta classe média / alto patrimônio), IR coerente com tabela RFB, dependentes < 5, dívidas opcionais.
6. **Nada de `confidence: 1.0` em todas** — pelo menos 1 fixture com `confidence: 0.85` para testar o caminho de "ok mas com avisos".
7. **`FakeLLMClient` não chama API real** — instalar em `tests/fakes/llm.py` (já existe) com método `set_response_for(stage, fixture)`.
8. **Goldens são commited** em `tests/fixtures/llm_golden/` (não gitignored); **não** versionar PDFs reais.

---

## Entregáveis

### A. Fixtures sintéticas

**`e16_irpf_full_completo.json`** — payload modelo completo cobrindo:
- 2 fontes pagadoras PJ (CLT principal + bonus); 1 PF (aluguel recebido R$ 30k/ano).
- 1 rendimento exterior (USD, com `data_conversao` 2024-12-15).
- Isentos: lucros distribuídos (cód 09 R$ 25k), FGTS (cód 04 R$ 5k).
- Exclusiva: 13º (cód 11), JCP (cód 10), aplicações financeiras (cód 12).
- Pagamentos: PGBL (cód 36), saúde (cód 10), educação (cód 11 com `teto_aplicado: true`), pensão (cód 30).
- 2 dependentes (filho 8 anos com CPF, filho 4 anos com `cpf_masked: null`).
- 1 dívida (financiamento imobiliário).
- 5 bens (imóvel, veículo, conta corrente, CDB, previdência VGBL).
- `confidence: 1.0`, `prompt_version: "e16-v1.0.0"`.

**`e16_irpf_full_simplificado.json`** — modelo simplificado:
- 1 fonte PJ.
- Isentos minimal.
- **NÃO** deve ter pagamentos dedutíveis (simplificado não usa) — mas se LLM extraiu, validator avisa (caso de teste para o warning).
- 0 dependentes.
- 3 bens.

**`e16_irpf_full_edge_cases.json`** — casos extremos:
- 1 fonte PJ com 13º bruto declarado.
- 2 rendimentos exterior (USD + EUR) com `data_conversao` distintas.
- Dependente `cpf_masked: null` + outro com idade limite (filho universitário 23 anos).
- Dívida com `valor_inicial_brl == valor_final_brl` (não amortizou no ano).
- `confidence: 0.82` (teste do caminho "ok mas com warnings").

### B. README atualizado

`tests/fixtures/llm_golden/README.md` ganha seção:

```markdown
## E1.6 — extract_irpf_full

Fixtures: completo / simplificado / edge_cases.

Origem: 100% sintética (zero PII real). CPFs `***.***.***-99/88/77`,
nomes "Test User", valores realistas mas fictícios.

Para regenerar quando bumpar prompt:
- atualize `pipeline/llm/prompts/e16_irpf_full.py::PROMPT_VERSION`
- rode `pytest tests/test_llm_golden.py::TestE16Goldens` com flag de update
  (ou edite o JSON manualmente respeitando schema)
- valide via `python -c "import json; from pipeline.llm.schemas.e16_irpf_full
  import IRPFFullOutput; IRPFFullOutput.model_validate(json.load(open(F)))"`
```

### C. Tests

`tests/test_llm_golden.py` ganha classe:

```python
class TestE16Goldens:
    @pytest.mark.parametrize("fixture", ["completo", "simplificado", "edge_cases"])
    def test_fixture_validates_against_schema(self, fixture):
        path = Path("tests/fixtures/llm_golden") / f"e16_irpf_full_{fixture}.json"
        data = json.loads(path.read_text())
        IRPFFullOutput.model_validate(data)  # no raise

    @pytest.mark.parametrize("fixture", ["completo", "simplificado", "edge_cases"])
    def test_fixture_passes_validator(self, fixture):
        # validate_e16_output retorna valid=True (errors vazios)
        ...

    def test_completo_kpis_match_expected(self):
        # IRPFAnalyzer produz valores explícitos esperados
        # renda_anual_familiar(2024) == Decimal("XXX")
        ...
```

### D. Stage runner test (FakeLLMClient)

`tests/test_extract_irpf_full_stage.py`:

```python
def test_stage_with_fake_llm_persists_golden(tmp_path):
    fixture = load_fixture("e16_irpf_full_completo.json")
    fake = FakeLLMClient(response=IRPFFullOutput.model_validate(fixture))
    ctx = build_test_context(tmp_path, fake_llm=fake, with_irpf_pdf=True)

    result = extract_irpf_full.run(ctx)
    assert result["success"]
    persisted = ctx.get_artifact_store().read("extract_irpf_full", "irpfdeclaracao_test")
    # Compara byte-byte (modulo prompt_version + validation block)
    assert persisted["contribuinte"] == fixture["contribuinte"]
    assert persisted["rendimentos_pj"] == fixture["rendimentos_pj"]
    # ...
```

### E. (Opcional) Fixture real anonimizada

`tests/fixtures/llm_golden/e16_irpf_real_anon_2024.json` — **só com CTO sign-off**:
- Declaração de quem committa (dev) processada localmente.
- CPFs trocados, nomes substituídos, valores multiplicados por fator (≠1, decidido na PR).
- Disclaimer no header: "Este JSON é derivado de declaração real anonimizada. Origem documentada em PR #X. Não distribuir."
- Test só assertiva schema + validator + analyzer — não compara byte-byte vs fixture sintética.

---

## Subagentes obrigatórios

| Gate | Quando | Subagente | O que aprovar |
|---|---|---|---|
| **G2** | Antes de codar fixtures | `data-engineer` | Cobertura de edge cases (eu vi todos os enums?), shape consistente com schema, ausência de PII residual. |
| **G0** | Antes de PR | `financial-planner` | Valores realisticamente distribuídos (não zerar tudo), 13º coerente, alíquota efetiva entre 7,5%–27,5%, dependentes plausíveis. |
| **CTO** | **Apenas se incluir fixture real anon** | `senior-cto` | LGPD edge case, decisão de versionar arquivo. |
| **G3** | Antes de PR | `senior-cto` (review) | TS de testes, ausência de `MagicMock` inline (preferir fakes nomeados — CLAUDE.md), clareza dos asserts. |

---

## Sequência de commits sugerida

```
1. test(fixtures): IRPF full schema goldens — completo + simplificado + edge_cases sintéticos
2. test(pipeline): TestE16Goldens em test_llm_golden.py (3 cenários × 3 asserts: schema/validator/analyzer)
3. test(pipeline): test_extract_irpf_full_stage.py com FakeLLMClient
4. docs(fixtures): README atualizado com seção E1.6 + instruções de regen
5. (opcional, se CTO ok) test(fixtures): real anonimizada + disclaimer
6. docs(changelog): A8.2 sub-lane goldens ✅ + entrada CHANGELOG datada
```

---

## Definition of Done

- [ ] G2 (`data-engineer`) sign-off em PR comment
- [ ] G0 (`financial-planner`) validou valores (transcrição em PR)
- [ ] `pre-commit run --all-files` passa
- [ ] `pytest tests -q` passa (incluindo todos os testes E1.6 novos)
- [ ] Validator `validate_e16_output` retorna `valid=True` para as 3 fixtures sintéticas
- [ ] Stage test (FakeLLMClient) passa byte-byte
- [ ] Nenhuma das fixtures tem CPF/CNPJ não-mascarado em campo livre
- [ ] Cross-lane shape: assert que `_e5_kpis_from_analyzer` produz **exatamente** as 11 chaves esperadas pelo `isIrpfKpis` ([frontend/src/types/irpf.ts](../../../../frontend/src/types/irpf.ts)) — protege a UI de regressão silenciosa (sections omitidas)
- [ ] PR mergeada em `main` com CI verde
- [ ] BACKLOG A8.2 marca sub-lane `irpf-full-schema-goldens` ✅

---

## Riscos / pontos de atenção

1. **Snapshot lock-in.** Goldens byte-byte tornam refactor de prompt doloroso. Mitigação: separar "schema/validator/analyzer goldens" (estáveis) de "prompt golden" (regenerável). Stage test compara só campos estruturais; não comparar `notes` ou outras strings que LLM varia.
2. **Mudança de prompt sem update de fixture** — `prompt_version` no payload detecta. Quando bumpar prompt, regenerar conscientemente.
3. **Fixture sintética não pega bug real do LLM** — não substitui validação em produção. Adicione TODO: smoke run com 1 PDF real anonimizado quando dev tiver tempo.
4. **CPF não-mascarado em fixture sintética** — fácil esquecer. Validator anti-PII no CI bloqueia, mas confirme manualmente com `grep -E '\d{3}\.\d{3}\.\d{3}-\d{2}' tests/fixtures/llm_golden/e16_*.json` antes de commit.
5. **Volume da fixture** — o JSON do "completo" tende a ficar grande (>200 linhas). OK; é fixture, não código de runtime.
6. **`FakeLLMClient` precisa suportar Instructor + Pydantic** — verificar [tests/fakes/llm.py](../../../../tests/fakes/llm.py) e estender se necessário (provavelmente já tem `set_output_for(stage, model_instance)` ou similar).

---

## Referências

- [ADR-157](../../../DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full) §Definition of Done — golden byte-byte exigida
- Goldens existentes: [tests/fixtures/llm_golden/](../../../../tests/fixtures/llm_golden) (E1, E1.5, E2-LLM, E7-review)
- Padrão de stage test: [tests/test_llm_stages_per_stage.py](../../../../tests/test_llm_stages_per_stage.py)
- `FakeLLMClient`: [tests/fakes/llm.py](../../../../tests/fakes/llm.py)
- Validator + reconcile: [pipeline/llm/validators.py::validate_e16_output](../../../../pipeline/llm/validators.py)
- Shape canônico consumido pela UI: [frontend/src/types/irpf.ts::IrpfKpis](../../../../frontend/src/types/irpf.ts) + emissor [scripts/e5_analyze.py::_e5_kpis_from_analyzer](../../../../scripts/analyze_finances.py) (lane `irpf-full-schema-ui`, mergeada 2026-04-30)
