---
id: ADR-337
type: adr
title: "Rótulo de exibição sem PII para ativos — sanitização na fonte E5 (React + prompt)"
status: Decidido
date: "2026-07-15"
amended_at: ["2026-08-19", "2026-08-24"]
relates_to:
  - "[[ADR-332]]"
  - "[[ADR-319]]"
  - "[[ADR-216]]"
  - "[[ADR-356]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
  - area/report
---

# ADR-337 — Rótulo de exibição sem PII para ativos

> **Emendada em 2026-08-19** — a [[A40.l6]] materializa o critério 4 (gate de PII
> no view-model) que o corpo original enunciou e ninguém implementou, e estende
> a sanitização de `top_ativos[].nome` para as descrições de imóvel e dívida que
> o relatório exporta. Ver §Emenda 2026-08-19.

> Cluster **PD-02** (P0, + subsume **H1**) da onda R2 do PLAN-dogfood-report-fix.
> Co-desenho `codesign-review-wave` (product-designer + senior-cto + red-team, 2026-07-15).

## Contexto

`investimentos.top_ativos[].nome` carrega a **descrição cartorial crua** do ativo — matrícula,
IPTU, endereço e, em ≥1 linha, o **CPF de um terceiro** (vendedor do imóvel) **não mascarado**.
Esse campo é lido por **duas** superfícies:

1. o card React `Top15AtivosCard.tsx:201` (`{r.nome}` verbatim) — quebra o layout e expõe PII ao
   dono do relatório;
2. o **prompt do parecer** (`config/prompts/parecer_planejador.yaml:147` lê `$.top_ativos[*]`) —
   **egresso de PII de terceiro para um LLM de terceiro**, fora do boundary do tenant. Este é o
   vetor de **maior** risco (LGPD), e não estava coberto pela proposta original de PD-02 (só UI).

Investimentos ainda aparecem com rótulo genérico `"Investimento"` + `instituicao=""`.

## Decisão

**Sanitizar `top_ativos[].nome` na FONTE E5** (`top_ativos_analyzer`/payload E5) — um **boundary
único** que subsume a superfície React (esta ADR) **e** a do prompt (irmã [[ADR-332]]). Regras:

1. Rótulo derivado, **granularidade estrita na fonte**: `imóvel → classe` **apenas** (padrão
   [[ADR-332]], sem bairro); `investimento → classe + instituição` (ou classe se instituição
   ausente). O valor monetário é preservado intacto.
2. **Nenhum** CPF/CNPJ/matrícula/IPTU/endereço de terceiro chega ao payload E5 — a string PII é
   removida **na origem**, não mascarada na UI.
3. Enriquecimento de display (ex.: bairro/cidade) é **downstream**, só na projeção view-model/React,
   **nunca** upstream do input do prompt (senão vaza localização adicional ao LLM).
4. O gate PII-scan (existente para o superset público, [[ADR-319]]) é **estendido** ao view-model
   **e ao contexto efetivo do LLM** (distiller + saída de tools sobre `top_ativos`).

## Rationale

PII de terceiro é PII mesmo no relatório da própria família — e o egresso a um LLM de terceiro
sai do tenant, o pior vetor. Sanitizar na fonte é o único ponto que cobre React **e** prompt sem
duplicar lógica; mascarar só na UI deixaria o prompt vazando. Granularidade estrita na fonte
respeita a decisão deliberada da [[ADR-332]] de não dar localização ao LLM.

## Alternativas consideradas

- **Sanitizar só na UI (React).** Rejeitada: o prompt continua egressando PII de terceiro (H1
  aberto) — não fecha o gate de PII de beta.
- **Mascarar (não remover) o CPF.** Rejeitada: a descrição cartorial inteira é ruído + risco;
  derivar um rótulo curto resolve legibilidade **e** privacidade de uma vez.
- **Enriquecer com bairro/cidade na fonte** (proposta de display). Rejeitada na fonte: daria mais
  PII de localização ao LLM que a [[ADR-332]] proíbe; fica só no view-model.

## Consequências

- Muda o **input** do prompt do parecer → cache pode invalidar. Exige **prova**: (a) rótulo
  estável (texto idêntico entre runs) ⇒ neutralidade; ou (b) orçar 1 eval, coordenado com a lane
  paralela de parecer (manifest 1.8→1.9). Não presumir "zero eval".
- Bump: `schema_e5` aditivo (campo `top_ativos[].nome` normalizado) — batelado no bump único da
  onda R2.1 (âncora [[ADR-338]]).
- Owner confirma que o CPF é de terceiro (evidência sugere sim) e o grau do rótulo de imóvel no
  **display**.

## Critério de aceite (4 lentes)

- **Completude** — nenhum slot (view-model) nem o `exec_context` do LLM emite CPF/CNPJ/matrícula/
  IPTU/endereço; cobre `top_ativos[].nome` e o distiller.
- **Corretude** — rótulo classe-only na fonte; valor monetário idêntico ao pré-fix.
- **Consistência** — mesmo abstrator em React e prompt; granularidade de display só downstream.
- **Precisão** — teste com regex de PII zero-hit em `top_ativos[].nome` **e** no contexto do
  distiller; neutralidade de prompt provada ou 1 eval orçado.

## Emenda 2026-08-19 — critério 4 no view-model (A40.l6)

O critério 4 do corpo original ("gate PII-scan estendido ao view-model") não
tinha artefato: o sanitizer do parecer cobre egresso a LLM, o lint de
[[ADR-319]] cobre o git, e `top_ativos[].nome` é classe-only. Restava o
view-model servido em `/reports/[id]/data` interpolando `descricao` cartorial
em `real_estate.imoveis[]`, `excluded_properties[]` e
`endividamento.dividas[]` — o PDF é a mesma rota ([[ADR-129]]).

**O que esta emenda decide:**

1. A descrição cartorial é **redigida na serialização** (`result_to_payload`,
   `DividaItem.to_dict`) antes de entrar no artefato E5 / view-model.
2. A UI lê o rótulo curto (`endereco_canonical` ou classe), nunca a descrição
   crua.
3. O gate `scan_view_model_pii` varre campos `descricao`/`detalhe`, cita o
   dot-path ofensor e **não** reproduz o match. Fixture sintética com
   identificador + matrícula + endereço ⇒ hits; `keys=frozenset()` ⇒ vazio
   (prova de mutação).
4. Valor de imóvel `0` no card é ausência (`—`), não "o bem vale zero"
   ([[ADR-356]] D7). O `s1` omite a parcela de residência quando o valor é 0.

## Emenda 2026-08-24 — o item 2 contradizia a decisão 2, e o gate era cego (A40.l6)

> **Sinal:** a emenda de 2026-08-19 foi medida no §Ataque da [[A40.l6]] e dois
> dos seus quatro itens estavam errados. Esta emenda os corrige; os itens 1 e 4
> seguem válidos como escritos.

**O que a medição mostrou.** `endereco_canonical` não é rótulo curado: é
`canonicalize(descricao)`, uma cascata que devolve `mat:<matrícula>`,
`qa:<código>` ou `iptu:<inscrição>` quando a descrição não tem logradouro. O
item 2 da emenda anterior, portanto, **autorizava exibir matrícula como rótulo
do imóvel** — exatamente o que a decisão 2 do corpo proíbe. E o item 3 fixava o
gate numa allowlist de chave (`descricao`/`detalhe`), que não alcança o campo
que a UI passou a renderizar: a mesma string dá 4 hits em `descricao` e **0** em
`endereco_canonical`.

**O que esta emenda decide:**

1. **O predicado do gate é o VALOR, não o nome do campo.**
   `scan_view_model_pii` varre **toda string** do payload. Allowlist de chave
   não sobrevive a mudança de render, e foi assim que a PII atravessou. Custo
   medido: 631 strings nas 6 fixtures de relatório, 2 hits, zero
   falso-positivo.
2. **A UI lê `endereco_display`**, campo que o E5 publica **apenas** quando o
   valor passa no próprio gate. Cascata cartorial (`mat:`/`iptu:`/`qa:`) e
   qualquer resto com PII ⇒ `null` ⇒ o card cai para o rótulo de classe.
   `endereco_canonical` **não viaja** no payload do relatório.
3. **Endereço próprio da família, na forma minimizada, é exceção escrita e
   escopada.** A decisão 1 do corpo ("imóvel → classe apenas") vale para
   `top_ativos[].nome`, cujo consumidor é o prompt do parecer. O card de
   imóveis não é lido por LLM nenhum (medido: `parecer_planejador.yaml` não
   referencia `real_estate`), e a família precisa reconhecer a própria linha na
   tabela. O que **nunca** é publicado é identidade-para-transacionar —
   matrícula, inscrição municipal, CPF/CNPJ de terceiro; `imobiliaria_cnpj` sai
   do payload, seguindo o padrão que `extract_informe_aluguel` já usa
   (`imobiliaria_cnpj_present: bool`).
4. **Redação também na LEITURA.** `get_report_data` redige o payload servido.
   Redigir só no produtor deixa exposto todo artefato **já gravado**, e o
   relatório re-renderiza artefato armazenado. Escrita e leitura usam a mesma
   função — duas definições de PII divergiriam.
5. **A prova de mutação muta o gate.** A anterior passava `keys=frozenset()`,
   isto é, mutava o argumento do chamador sem exercitar regex nenhuma. E o
   gate ganhou chamador: o payload de `result_to_payload` em `tests/`, o lint
   público sobre as fixtures commitadas (com os 2 waivers de endereço
   queimados) e a spec renderizada `reports/pii-cartorial.@critical.spec.ts`,
   que assere ausência no DOM **e** na camada de texto do PDF.
