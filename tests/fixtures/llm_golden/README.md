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
| `e2_llm_extract_output.json` | E2-LLM | `LLMExtractOutput` (`e2_llm_extract.py`) | `TestE2LLMGoldenFile` |
| `e7_review_output.json` | E7-review | `E7ReviewOutput` (`e7_review.py`) | `TestE7ReviewGoldenFile` |

**Quando alterar um JSON:** atualizar o diff no PR; rodar `pytest tests/test_llm_golden.py -q`. Se o schema Pydantic mudar, ajustar o fixture e os asserts em `test_llm_golden.py` no mesmo PR.

**PII:** usar apenas dados claramente fictícios (o repositório já roda `tests/utils/lint_no_real_pii.py` no CI).
