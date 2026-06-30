# Anti-regression bank

Prova que **bugs históricos não voltaram**. Tudo vive consolidado em
**`test_anti_regression_bank.py`** — uma **classe por bug** (`TestBugNNN<Slug>` /
`TestOpNNN<Slug>`), não um arquivo por bug. Cada classe tem docstring com sintoma
original + fix + a assertion que falharia se o fix fosse revertido.

Convenções:

- **Classe por bug:** `TestBug004FallbackCPFLeak`, `TestOp005RouteToDataDir`, etc.
- **Cada test falha SE o fix for revertido** — caso exato que reproduz o bug, não
  asserts genéricos.
- Bug puramente de **frontend** não vira teste-placeholder aqui — fica coberto em
  `frontend/tests/`; só é registrado no catálogo abaixo como `🎯 frontend`.

## Catálogo

Backend coberto por classe em `test_anti_regression_bank.py` (BUG-001/002/003/004/
007/014/015 + OP-001..010); frontend coberto em `frontend/tests/`. BUG-015 também
tem cobertura em `test_serializers_round_trip.py`. Para o status vivo, leia as
classes do arquivo (`rg "^class Test" test_anti_regression_bank.py`) — esta tabela
não duplica o detalhe para não derivar.

| Faixa | Origem | Cobertura |
|---|---|---|
| BUG-001/002/003 | Celery (discovery, sys.path, on_failure) | ✅ classe |
| BUG-004 | CPF leak no fallback de members | ✅ classe |
| BUG-007 | skip_llm respeita tier premium | ✅ classe |
| BUG-014/015 | account label / família sobrenome | ✅ classe (+ serializers round-trip) |
| BUG-005/006/008/011/012 | UI (nav, botão, notif, dead imports) | 🎯 frontend |
| OP-001..010 | parse_args, SystemExit, LLM skip, validation, route_to_data_dir, categorization global, FERNET persist, max_tokens E1.5, tz-aware | ✅ classe |

## Como contribuir

1. Reproduza o bug com uma **classe nova** `TestBugNNN<Slug>` em
   `test_anti_regression_bank.py` que **falha** sem o fix.
2. Aplique o fix no código de produto; o teste passa.
3. Anote a faixa na tabela acima.
