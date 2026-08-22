---
id: A40.l75
type: lane
title: "O gate de drift do MSW existe, está fora do CI e compara errado: a ADR-069 afirma uma proteção que nunca rodou"
sprint: A40
status: open
priority: P2
branch_slug: a40-l75-msw-drift-gate-inerte
adrs:
  - "[[ADR-069]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/frontend
  - area/testing
---

# A40.l75 — `msw-drift-gate-inerte`

> **Aberta em 2026-08-21**, no closeout do #1618 (decisão do dono). Origem:
> ao declarar as 129 requests órfãs do MSW, a camada 2 do `lane-closeout`
> encontrou a [[ADR-069]] — que **já decidiu** o mecanismo que teria pego o
> drift corrigido ali, e cujo enforcement nunca foi ligado.

## Problema

A [[ADR-069]] (`Decidido`, 2026-04-15) escolheu "manual + lint CI" para manter
`frontend/tests/mocks/handlers.ts` em sincronia com o backend, e lista entre as
consequências:

> ✅ Lint CI cobre "drift" — novo endpoint no backend sem handler → CI falha

O `CHG-2026-04-15-F65-MSW-SYNC-LINT` registra `frontend/scripts/msw-lint.mjs`
como entregue. **Três coisas medidas em 2026-08-21 contradizem isso:**

1. **Não está no CI nem no `package.json`.** `rg -l "msw-lint" .github/
   frontend/package.json` → nenhum hit. A própria ADR condicionava:
   *"Ativar em CI após primeiro baseline"*. O baseline nunca saiu.
2. **A comparação não casa nada.** Contra o snapshot commitado:

   ```bash
   cd frontend && node scripts/msw-lint.mjs --spec ../docs/reference/api/v1/openapi.json
   ```

   → `219 endpoint(s) backend SEM handler MSW` **e** `75 handler(s) MSW sem
   endpoint backend`. São **todos** os 219 e **todos** os 75 — 100% de
   falso-positivo nos dois sentidos, não drift real.
3. **A causa está numa promessa que a função não cumpre.** O comentário na
   L40 diz *"Normaliza: remove `${API}` prefix se string contém template"*,
   mas `normalizeUrl` (L49-52) só faz `:param` → `{param}`. A saída imprime
   `GET ${API}/auth/register` com o prefixo literal — por isso nenhum handler
   casa com path nenhum do OpenAPI.

O baseline é **impossível de produzir** com a ferramenta como está, o que
explica por que a ativação nunca aconteceu. Enquanto isso a ADR segue
`Decidido` afirmando uma proteção que não existe: o próximo agente que a ler
vai acreditar que o CI cobre drift de handler.

### O custo já foi pago uma vez, medido

O #1618 corrigiu 129 requests órfãs do MSW em 7 arquivos. Duas delas eram
exatamente a classe que a ADR-069 nomeia — *"handlers com URL que não existe no
OpenAPI"*:

- `config.test.tsx` sobrescrevia `/api/v1/config/llm/tier`, rota pré-escopo de
  workspace. **Nunca casava**, e o teste seguia verde porque assertava só o
  outro endpoint.
- `handlers.ts` mantém defaults da mesma era, que o cliente não chama mais:
  `/vault/passwords` (L133), `/config/members` (L172), `/config/llm/tier`
  (L268). Aparentam cobertura e não casam nada.

## Escopo

1. **Consertar a normalização** do `msw-lint.mjs` — os dois lados têm de
   chegar à mesma forma canônica (prefixo `/api/v1` + `{param}`). Teste do
   próprio script antes: hoje ele não tem nenhum.
2. **Produzir o baseline** e ligar no CI. Sobre a fonte do spec: o snapshot
   `docs/reference/api/v1/openapi.json` já é versionado e mantido por
   `make update-openapi-snapshot` ([[ADR-109]]) — usá-lo evita a dependência
   de backend UP que a própria ADR-069 listou como risco (⚠️ *"Depende de
   backend estar UP"*). Sem backend, o script já sai com código 2, então o
   fail-closed está correto e não precisa mudar.
3. **Limpar os defaults mortos** de `handlers.ts` — o inventário exato sai do
   passo 1, não da inspeção manual.
4. **Emendar a [[ADR-069]]** com o que a medição mostrou (`amended_at` +
   blockquote de sinal, padrão [[ADR-027]]), ou registrar §Deferimento datado
   se o dono decidir não ligar o gate.

## Critério de aceite

- `node scripts/msw-lint.mjs --spec <snapshot>` sai **0** num `main` limpo, e
  o número de achados é `0`, não "todos".
- Mutação que prova o gate: adicionar handler para rota inexistente **ou**
  remover um handler de rota viva → o script sai ≠ 0 e nomeia a rota certa.
  Sem essa mutação o gate não está medido, só ligado
  ([[ADR-302]] §medição por mutação).
- O passo 3 não pode ser feito antes do passo 1: limpar `handlers.ts` "no
  olho" cega o gate que deveria provar a limpeza.
- A ADR-069 deixa de afirmar cobertura de CI que não existe.

## Fora de escopo

- Trocar a estratégia por codegen — a alternativa (A) foi considerada e
  rejeitada na ADR-069; reabrir isso exige ADR nova, não esta lane.
- Adicionar handler default para as 219 rotas de backend sem mock. O
  `onUnhandledRequest: "error"` é a polaridade certa e o #1618 a preservou de
  propósito; o lado "backend sem handler" do lint provavelmente precisa nascer
  como **aviso**, não erro, sob pena de exigir 219 mocks que ninguém usa.
