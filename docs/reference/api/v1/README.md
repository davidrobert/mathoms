# API v1 — OpenAPI snapshot

Este diretório contém o snapshot **committed** do OpenAPI 3.1 gerado pelo
backend FastAPI. Propósito (ADR-102 · A6f.2):

- **Contrato explícito entre processos.** Clientes em qualquer linguagem
  (Go, TypeScript, Rust, cURL) sabem a shape exata sem ler Python.
- **CI diff.** Se o código introduzir breaking change não-intencional no
  contrato, o teste [test_openapi_snapshot.py](../../../../backend/tests/test_openapi_snapshot.py)
  falha e a PR é barrada.
- **Codegen.** `openapi-typescript`, `orval`, ou qualquer ferramenta
  similar consome este arquivo para gerar clients tipados.

## Como regenerar

Após alterar qualquer endpoint (novo router, novo `response_model`, novo
query param obrigatório...):

```bash
make update-openapi-snapshot
# equivalente a:
# python -c 'import json; from backend.app.main import app; \
#   print(json.dumps(app.openapi(), indent=2, sort_keys=True))' \
#   > docs/reference/api/v1/openapi.json
```

Depois comite o diff. Se não o fizer, `test_openapi_snapshot.py` falhará no CI.

## Política de breaking changes

Mudanças no OpenAPI são classificadas como:

| Tipo | Exemplo | Política |
|------|---------|----------|
| **Aditivo** | Novo endpoint, novo campo opcional | OK; bumpa o snapshot |
| **Aditivo tipado** | Adicionar `response_model` onde não havia | OK; bumpa o snapshot |
| **Breaking** | Remover campo, mudar tipo de campo existente, remover endpoint | Requer ADR + nova versão `/api/v2/` |

A6f.5 (Versioning) ainda não está implementado — por ora, toda mudança
breaking exige ADR antes de merge.

## Arquivos

- `openapi.json` — snapshot atual (OpenAPI 3.1, ordenado por chaves para diff estável).
