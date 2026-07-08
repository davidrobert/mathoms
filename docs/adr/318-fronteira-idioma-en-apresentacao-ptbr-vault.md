---
id: ADR-318
type: adr
title: "Fronteira de idioma — apresentação pública EN vs vault canônico PT-BR"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[ADR-130]]", "[[PLAN-i18n]]", "[[A34.l23]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/docs
  - area/gtm
---

# ADR-318 — Fronteira de idioma: apresentação pública EN vs vault canônico PT-BR

**Status:** Proposto (owner-gated) · **Data:** 2026-07-08 · Gate **G0** do
[[PLAN-public-release]]. Ativa a cláusula condicional já escrita em
[[PLAN-i18n]] §11 (Pós-launch) — **não** emenda [[ADR-130]]. Habilita a
Onda 7 ([[A34.l23]]).

## Contexto

Tornar o repo público exige artefatos de apresentação de audiência-de-repo:
`README`, `CONTRIBUTING`, `LICENSE`, `SECURITY`, `CODE_OF_CONDUCT`. A norma
de mercado open-source é EN — a audiência global de GitHub lê EN, e um
`README` em PT-BR estreitaria a superfície de descoberta que o flip busca.

Mas o repo carrega uma invariante forte: **doc canônico é 100% PT-BR** (regra
do CLAUDE.md §"Planos → docs/"; vault de ADR/plan/sprint/reference em PT-BR
com wikilinks Obsidian, gates `validate_frontmatter`/`check_doc_links`).
Introduzir superfície EN **sem traçar a fronteira** erode essa invariante por
osmose: convida tradução gradual de ADRs, mistura idiomas no mesmo bucket, e
transforma "docs em PT-BR" numa regra ambígua que gates não conseguem
enforçar. É o mesmo risco de escopo que o plano combate na PII — deixar uma
brecha aberta e apostar na disciplina.

Além disso, "docs em EN" pode ser lido erroneamente como **sinal de mercado**:
que o Mathoms passou a mirar clientes lusófonos-globais ou anglófonos. Isso
colide com [[ADR-130]], que governa i18n de **produto** (locales do app) em
estado `paused` com gate de demanda. **es e pt-PT não são necessários para
executar este plano** — são matéria de produto, não de apresentação do repo.
A fronteira precisa separar explicitamente **idioma da
apresentação do repo** de **idioma/mercado do produto**.

Co-design 2026-07-08 (`gtm-strategist` + `information-architect`, síntese
`senior-cto`). Consenso: a decisão não é "traduzir ou não" — é **onde a
fronteira cai e o que ela NÃO sinaliza**.

## Decisão

1. **Superfície EN = APENAS apresentação pública** (audiência-de-repo):
   `README.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md`,
   `CODE_OF_CONDUCT.md` na raiz e `.github/`. Escritos em EN, com disclaimer
   de dogfood e narrativa metodológica genérica ([[ADR-183]], sem atribuição
   nominal Perini/Cerbasi/AUVP — cross-check com o gate de sigilo de W2).

2. **Vault permanece PT-BR** (artefato de trabalho interno): `docs/adr/`,
   `docs/plan/`, `docs/sprint/`, `docs/reference/`, `docs/agent_prompts/`,
   `docs/_MOC/`. Nenhuma tradução, nenhum idioma misto. Gates de doc
   (`validate_frontmatter`, `check_doc_links`, `check_adr_anchors`) seguem
   assumindo PT-BR + frontmatter YAML + wikilinks `[[X]]`.

3. **Isto ativa a cláusula condicional já escrita em [[PLAN-i18n]] §11**
   (Pós-launch) — "documentação técnica em EN apenas se hire internacional
   ou open-source" — cuja pré-condição (repo público) agora se realiza. A
   cláusula vive no PLAN-i18n, não no [[ADR-130]] atômico; ativá-la **não
   emenda ADR-130** (nenhuma decisão de produto-i18n muda). `relates_to`, não `amends`.

4. **Produto-i18n permanece `paused` e fora do escopo deste plano:** os locales
   de app (governados pelo [[PLAN-i18n]]) só destravam por sinal de mercado, não
   por este flip. **es e pt-PT não são necessários para executar o PUBLIC_RELEASE**;
   docs-EN de **apresentação** não é reativação de produto-i18n nem sinal de mercado.

5. **Fronteira mecanizável:** a Onda 7 ([[A34.l23]]) reconcilia a superfície
   EN com [[PLAN-i18n]] e cross-linka; qualquer arquivo EN novo fora da
   allowlist de apresentação é desvio a revisar. A distinção é
   path-baseada (raiz/`.github/` de apresentação vs `docs/**` de vault),
   portanto auditável por grep.

## Alternativas consideradas

- **A — README/docs de apresentação em PT-BR** (sem superfície EN): preserva
  a invariante trivialmente, mas estreita a descoberta global que motiva o
  flip. Rejeitada: contradiz o objetivo de audiência-de-repo.
- **B — traduzir o vault inteiro para EN**: máxima legibilidade externa, mas
  dobra o custo de manutenção de ~300 docs, quebra Obsidian/wikilinks
  refactor-friendly, e não serve ICP nenhum (o vault é substrato de trabalho
  interno, não vitrine). Rejeitada: custo desproporcional, zero retorno.
- **C — superfície EN sem fronteira formal** (deixar orgânico): é o status
  que a ADR existe para prevenir. Erode a invariante por osmose e reabre a
  ambiguidade "docs são PT-BR?". Rejeitada: exatamente o anti-padrão.
- **D — incluir pt-PT na fronteira** ("referência lusófona global"):
  confunde "internacional" com "lusófono". EN já resolve audiência-de-repo;
  pt-PT só faria sentido para audiência-de-**produto** residente-PT, que não
  é o ICP. Rejeitada (unânime no co-design, alinhada à decisão GTM).

## Consequências

- **Positivo:** superfície pública legível globalmente sem custo de tradução
  do vault; invariante "vault é PT-BR" fica **mais** nítida (agora com
  fronteira explícita), não menos; gate de idioma vira path-baseado e
  auditável; nenhum sinal de mercado espúrio emitido.
- **Custo:** manutenção de ~5 arquivos de apresentação em EN em paralelo à
  evolução do produto (drift README↔realidade é o risco corrente). Contido:
  são poucos arquivos, de baixa cadência de mudança.
- **Risco de contaminação de escopo:** a fronteira precisa ser reforçada por
  revisão — um `docs/adr/NNN.md` em EN passaria os gates atuais (que não
  checam idioma). Mitigação: convenção documentada + allowlist path-baseada
  na Onda 7; enforcement mecânico de idioma é follow-up P2, não bloqueante.
- **Sem link rot:** nenhum `id`/filename/wikilink muda; o grafo do vault fica
  intacto (mesma garantia da anonimização in-body da Onda 1).

## Decisão do owner

Esta ADR é **owner-gated** (gate G0). Status permanece `Proposto` até o owner
marcar as opções abaixo; o PR de flip da decisão muda para `Decidido (A34)`.

**Fronteira de idioma:**

- [ ] Aprovado como escrito — EN só na apresentação pública; vault PT-BR.
- [ ] Ajustar allowlist de apresentação (especificar quais arquivos).
- [ ] Rejeitar (apresentação também em PT-BR — Alternativa A).

**Confirmação de que docs-EN NÃO sinaliza intenção de mercado PT:**

- [ ] Confirmado — docs-EN de apresentação é audiência-de-repo, não sinal de
      mercado. Produto-i18n (`paused`) e pt-PT (fora) permanecem inalterados.
- [ ] Reabrir — há sim intenção de mercado a discutir (escala para
      `gtm-strategist`; **fora** do escopo deste plano de flip).
