# Runbook — Imagens backend multi-stage (runtime / playwright)

> **ADR:** [[ADR-248]] (Decidido · A20.L1) · **Lane:** [[A20.l1]]
> **Dockerfile:** [`Dockerfile`](../../../Dockerfile) (3 stages, dual target)
> **Audit:** [`dev/audit_backend_image.sh`](../../../dev/audit_backend_image.sh)
> **Owner:** quem tocar `Dockerfile`, `requirements.lock` ou compose de backend.

---

## 1. O modelo mental em uma frase

Um `Dockerfile`, três stages, **dois targets publicáveis**:

```
builder  →  runtime  →  playwright
(wheels)    (worker/    (api — runtime + Chromium)
             beat)
```

`playwright` é **literalmente** `runtime` + uma camada Chromium
(`FROM runtime AS playwright`). Drift entre os dois é impossível por
construção — não existe "deps do worker divergiram dos deps do api".

| Stage | Quem usa | Tem Chromium? | Tem gcc? |
|---|---|---|---|
| `builder` | ninguém (descartado) | não | **sim** (build-essential) |
| `runtime` | `worker`, `beat` | **não** | não |
| `playwright` | `api` (PDF render) | **sim** (~956MB) | não |

**Default target = `playwright`** — `docker build .` sem `--target` produz o
superset seguro (dev local roda tudo, incl. PDF).

---

## 2. Quando trocar de target

| Situação | Target |
|---|---|
| Service renderiza PDF (`pdf_renderer.py` / `/reports/{id}/pdf`) | `playwright` |
| Celery worker, beat scheduler, qualquer coisa sem PDF | `runtime` |
| Dev local (quer rodar tudo sem pensar) | default (= `playwright`) |

Hoje só o `api` renderiza PDF (endpoint síncrono). Se amanhã o render virar
Celery task pesada, **troca-se o `image:`/`target:` do worker para
`playwright`** — zero mudança no `Dockerfile`. Essa opcionalidade é o motivo
da Opção C ([[ADR-248]] §Alternativas).

```bash
docker build --target runtime    -t mathoms-backend:runtime-<sha>    .
docker build --target playwright -t mathoms-backend:playwright-<sha> .
```

Compose:
- **dev** (`docker-compose.dev.yml`): `api → target playwright`,
  `worker/beat → target runtime` (beat reusa o build do worker).
- **prod** (`docker-compose.prod.yml`): publicação por target via GHCR fica
  em [[A20.l4]] (`release-backend.yml`). **Não tocado em L1.**

---

## 3. Como auditar enxutez (os dois invariantes)

O deliverable do dual-target **não é tamanho absoluto** — é que o runtime
não carrega o que não usa. Rode:

```bash
dev/audit_backend_image.sh                       # builda + audita ambos
dev/audit_backend_image.sh runtime-tag pw-tag    # audita tags já buildadas (CI)
```

Os dois invariantes que o script trava (falha = exit 1):

1. **runtime sem `gcc`** — `build-essential` vazou para runtime (P0.3 regrediu)
   se `command -v gcc` achar o binário. Toolchain deve viver só no `builder`.
2. **runtime sem cache `ms-playwright`** — se `/home/mathoms/.cache/ms-playwright`
   existir no runtime, worker/beat carregariam ~956MB de Chromium morto.

Mais smoke (não-invariante, mas sinaliza P0.1): `python -m playwright --version`
funcional no `playwright`, cache `ms-playwright` **presente** no `playwright`,
e heredity (`docker history` contém a layer `playwright install`).

---

## 4. Tamanhos reais (não as metas do draft)

As metas `runtime <450MB` / `playwright <950MB` do draft eram **fisicamente
impossíveis** — corrigidas em [[ADR-248]] §Validação. Medições arm64 (Docker 29.4):

| Target | Tamanho | Componente irredutível |
|---|---|---|
| `runtime` | ~1.09GB | ~652MB de site-packages (cryptography, asyncpg, pandas, anthropic, playwright pip pkg) sobre `python:3.12-slim` |
| `playwright` | ~2.72GB | runtime + ~956MB Chromium + ~228MB libs de sistema |

amd64 é menor. O número depende de arch + dep set — por isso saiu dos
critérios de aceite. **O ganho mensurável é:** build-essential fora do
runtime + worker/beat sem Chromium (~956MB economizados em 2 dos 3 containers).

---

## 5. Armadilhas (já pisadas — não repita)

- **`COPY --from=builder /wheels` + `rm -rf /wheels` NÃO encolhe a imagem.**
  Um `RUN rm` posterior não reclama a layer do `COPY` anterior — ficam ~157MB
  mortos (runtime mediu 1.4GB). Use **BuildKit bind-mount** transitório:
  ```dockerfile
  RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
      pip install --require-hashes --no-index --find-links /wheels -r /app/requirements.lock
  ```
  Requer `# syntax=docker/dockerfile:1.7` no topo.
- **Lockfile é único** (`requirements.lock` na raiz) — superset de
  `requirements.in` + `backend/requirements.in` ([[A20.l10]]). Não há
  `backend/requirements.lock`; não instale `backend/requirements.in` direto.
- **`FROM runtime AS playwright` quebra se você reordenar os stages.** O
  `playwright` precisa do `runtime` já definido acima dele. Comentário inline
  no Dockerfile avisa — preserve.
- **Auditar com `docker history --no-trunc | grep` dá falso-negativo** no
  Docker 29.4 (manifest-list/attestation). Use
  `docker history <tag> --format '{{.CreatedBy}}' | grep ...` (o audit já faz).
- **Para rodar shell/python no container** (entrypoint despacha `api|worker|beat`),
  use `--entrypoint sh` / `--entrypoint python`.

---

## 6. SHA pin (L2) e slimming (follow-up)

- **SHA pin:** [[A20.l2]] trocou o default de `ARG PYTHON_BASE` por
  `python:3.12-slim@sha256:<digest>` + Dependabot Docker — num **único
  ponto**, sem reescrever os 3 `FROM`. Default hoje é SHA-pinado
  (`Dockerfile:17`).
- **`chromium-headless-shell` (~110MB vs ~956MB):** alavanca de slimming do
  target `playwright`. Exige `channel="chromium-headless-shell"` no
  `pdf_renderer.py` — muda comportamento de render, então é **track de
  follow-up separado**, não L1.
