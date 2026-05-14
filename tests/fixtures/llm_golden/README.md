# Fixtures LLM (schemas Pydantic)

JSONs versionados usados por `tests/test_llm_golden.py` para garantir que:

- cada saída **parseia** no modelo Pydantic do estágio (`pipeline/llm/schemas/*`);
- os **validators** (`pipeline/llm/validators.py`) aceitam o payload onde existir validador dedicado;
- os **conversores** (`_output_to_*` nos `pipeline/stages/*`) produzem o JSON esperado no workspace.

Não são artefatos de pipeline em `processed/` — são **contratos de teste** alinhados a [ADR-070](../../../docs/DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in). Para **mocks em runtime** (pytest/backend/E2E), ver `backend/tests/fixtures/llm_mock.py`.

| Arquivo | Estágio | Schema | Testes |
| --- | --- | --- | --- |
| `e1_members_output.json` | E1 | `MembersExtractOutput` (`e1_members.py`) | `TestE1GoldenFile` |
| `e15_baseline_output.json` | E1.5 | `BaselinePatrimonialOutput` (`e15_baseline.py`) | `TestE15GoldenFile` |
| `e16_irpf_full_completo.json` | E1.6 | `IRPFFullOutput` (`e16_irpf_full.py`) | `TestE16Goldens` |
| `e16_irpf_full_simplificado.json` | E1.6 | `IRPFFullOutput` (`e16_irpf_full.py`) | `TestE16Goldens` |
| `e16_irpf_full_edge_cases.json` | E1.6 | `IRPFFullOutput` (`e16_irpf_full.py`) | `TestE16Goldens` |
| `e2_llm_extract_output.json` | E2-LLM | `LLMExtractOutput` (`e2_llm_extract.py`) | `TestE2LLMGoldenFile` |

**Quando alterar um JSON:** atualizar o diff no PR; rodar `pytest tests/test_llm_golden.py -q`. Se o schema Pydantic mudar, ajustar o fixture e os asserts em `test_llm_golden.py` no mesmo PR.

**PII:** usar apenas dados claramente fictícios (o repositório já roda `tests/utils/lint_no_real_pii.py` no CI).

## E1.6 — `extract_irpf_full`

Três fixtures sintéticas cobrem o stage `extract_irpf_full` (ADR-157):

- **`e16_irpf_full_completo.json`** — declaração modelo completo com todos os
  blocos preenchidos: 2 fontes PJ (com 13º), 1 PF (carnê-leão de aluguel),
  1 exterior, 2 isentos, 3 exclusiva, 4 pagamentos dedutíveis (incl. PGBL com
  saúde+educação+pensão), 1 dívida, 5 bens & direitos, 2 dependentes
  (1 com CPF, 1 sem). `confidence=1.0`.
- **`e16_irpf_full_simplificado.json`** — modelo simplificado: 1 PJ, isentos
  mínimos, **sem** pagamentos dedutíveis (RFB não aceita no simplificado),
  3 bens, 0 dependentes. PGBL capacidade dedutível deve zerar no analyzer.
- **`e16_irpf_full_edge_cases.json`** — `confidence=0.82` (caminho com
  warnings): 2 rendimentos exterior em moedas distintas (USD + EUR) com
  `data_conversao` distintas; dívida com `valor_inicial == valor_final`
  (ano sem amortização); dependentes mistos (sem CPF + filha universitária
  23 anos, dentro do limite RFB).

**Origem:** 100% sintética — zero PII real. CPFs sempre mascarados como
`***.***.***-XX`; CNPJs são públicos (não-PII por ADR-157 sub-decisão 5);
nomes "Test User", valores realistas mas fictícios. Reconciliação
cross-field (`ir_pago_brl` ≈ Σ retidos PJ + PF) bate com tolerância
0,02 BRL nas três fixtures.

**Para regenerar quando bumpar prompt:**

1. Atualize `pipeline/llm/schemas/e16_irpf_full.py::PROMPT_VERSION` e
   `pipeline/llm/prompts/e16_irpf_full.py` (re-export).
2. Edite os JSONs respeitando o schema (Decimal-string em monetários,
   ISO YYYY-MM-DD em datas, CPFs sempre mascarados).
3. Verifique localmente:
   ```bash
   python3 -c "
   import json
   from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput
   from pipeline.llm.validators import validate_e16_output
   for f in ('completo', 'simplificado', 'edge_cases'):
       p = f'tests/fixtures/llm_golden/e16_irpf_full_{f}.json'
       out = IRPFFullOutput.model_validate(json.load(open(p)))
       r = validate_e16_output(out)
       assert r.valid, r.errors
   "
   ```
4. Rode `pytest tests/test_llm_golden.py::TestE16Goldens -q` e
   `pytest tests/test_extract_irpf_full_stage.py -q`.
