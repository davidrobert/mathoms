---
id: ADR-316
type: adr
title: "Aceite de risco de metadados GitHub imutáveis (855 PRs/issues/CI logs)"
status: Proposto
date: "2026-07-08"
relates_to: ["[[PLAN-public-release]]", "[[A34.l21]]"]
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/seguranca
  - area/gtm
---

# ADR-316 — Aceite de risco de metadados GitHub imutáveis

**Status:** Proposto (owner-gated) · **Data:** 2026-07-08 · Gate **G0** do
[[PLAN-public-release]]. Falha cedo (W0) por desenho — ver §Decisão.

## Contexto

O flip público do repo `davidrobert/mathoms` é **in-place** (restrição do
owner — não criar repo novo). A auditoria de 2026-07-08
([audit-2026-07-08.md](../plan/PUBLIC_RELEASE/audit-2026-07-08.md), §3)
identificou **três camadas de contaminação**. O rewrite de histórico
(Onda 3, `git-filter-repo`) resolve as camadas 1 (HEAD) e 2 (histórico de
blobs/mensagens). A **camada 3 — metadados GitHub — é inapagável por *git***
(mas **parcialmente** eliminável via API/Suporte do GitHub — ver §"Mecânica da
camada 3"): são **~855 PRs/issues** (incl. "Security schedule
failure"), mais comentários e logs de CI (retention ~90d) contendo diagnósticos
de dogfood com valores reais e discussão de estratégia competitiva
([[PLAN-competitive-pierre]]).

`git-filter-repo`/BFG operam sobre a árvore de objetos git; PRs/issues/logs
vivem no banco de dados do GitHub, fora do alcance de qualquer reescrita de
histórico. As únicas mitigações reais são **edição/deleção manual via API**
antes do flip **ou** **aceite formal de risco** do owner. Esta ADR trava
essa decisão — e a trava **em W0**, não em W8, porque é aqui que a
restrição in-place pode ser logicamente incompatível com o objetivo
(ver §Decisão, cláusula crítica).

Co-design 2026-07-08 (5 especialistas em paralelo + síntese `senior-cto`).
Duas objeções materiais à restrição in-place foram registradas (§Alternativas
consideradas) — o owner está ciente e decide em §Decisão do owner.

## Mecânica da camada 3 — o que a triagem alcança (e o que não)

Refinamento pós-co-design (probing do owner 2026-07-08): a camada 3 **não é um
bloco monolítico inapagável**. Divide-se em:

- ✅ **Eliminável self-service (UI/API GitHub):** deletar **issues** (admin;
  `gh api -X DELETE /repos/{repo}/issues/{n}` não existe — usar a mutação
  GraphQL `deleteIssue` ou o botão "Delete issue"); editar/deletar **comentários**
  de PR/issue/review; editar **título e corpo** de PR; deletar **runs e logs de
  CI** (`gh api -X DELETE /repos/{repo}/actions/runs/{id}`). Cobre a maior parte
  do T1/T2.
- ❌ **NÃO self-service:** o **PR em si não é deletável** (GitHub só permite
  *fechar* — diferente de issue). Sobrevivem a "casca" do PR, sua **timeline de
  eventos** (incl. **mensagens de commit** exibidas) e os **commits referenciados
  pelo PR**.
- ⚠️ **Caveat que quebra a premissa ingênua "rewrite resolve":** o rewrite de
  histórico da **Onda 3 NÃO purga os commits referenciados por PRs.** O GitHub
  mantém esses commits em cache mesmo depois de órfãos — `/{repo}/pull/{n}/commits/{sha}`
  continua servindo o **conteúdo pré-rewrite** (o PDF, a mensagem com patrimônio
  nominal). Logo, W3 limpa `main`, mas **não** limpa o cache de PR: essa é a parte
  dura da camada 3.
- 🛟 **Rota GitHub Support (mitigação real sem deletar o repo):** após o rewrite,
  abrir ticket pedindo remoção de "sensitive data cached in pull requests /
  dangling commits". É processo documentado que o Support executa — **manual mas
  dependente de terceiro** (timing não garantido; não é instantâneo nem sob seu
  controle).
- 🔒 **Zero-risco 100% sob controle próprio = deletar o repo** (i.e., **Opção 2**,
  repo novo). É o único caminho que purga PRs/issues/logs/cache de commits num
  golpe, sem depender do Support.

Consequência para as opções: a **Opção 1** (in-place) atinge risco *baixo* —
triagem self-service + ticket ao Support — mas **nunca "zero sob seu controle"**;
a **Opção 2** (repo novo) é o único zero-risco imediato e próprio, ao custo
detalhado em [[PLAN-public-release]] §"Objeções registradas".

## Decisão

**Recomendação leading: triagem em tiers + aceite formal do risco residual,
mantendo o flip in-place** — condicionada à cláusula de incompatibilidade
lógica abaixo.

1. **Triagem T1/T2/T3** ([[A34.l21]], Onda 4, `∥` com o rewrite W3):
   - **T1 — PII direta e IP competitivo em metadados de alto risco:** PRs/
     issues/comentários que expõem CPF, endereço, nome de terceiro,
     patrimônio nominal, ou discussão explícita de [[PLAN-competitive-pierre]].
     **Editar via API GitHub ou deletar** o item. Cobertura: 100% dos T1.
   - **T2 — logs de CI de dogfood:** runs de CI que imprimiram valores reais
     em diagnósticos de dogfood. **Expirar retention (~90d) ou deletar os
     runs** — não há reescrita, só remoção.
   - **T3 — resíduo:** metadados de baixo sinal (títulos de PR já editados na
     triagem T1, comentários operacionais sem PII). **Aceite formal de risco
     residual** — rastreável para efeito de LGPD.
   - **T4 — cache de commits de PR (pós-rewrite):** o rewrite W3 deixa os commits
     referenciados por PRs acessíveis em cache (§Mecânica). Após o force-push,
     **abrir ticket ao GitHub Support** pedindo purga de dangling/PR-cached
     commits. Passo da [[A34.l21]]; não sob controle próprio (depende do Support).

2. **CLÁUSULA CRÍTICA DE INCOMPATIBILIDADE LÓGICA (por que é gate G0):** se
   o owner exigir **zero-risco em metadados**, a restrição "flip in-place" é
   **logicamente incompatível** — metadados GitHub não se reescrevem, então
   nenhuma quantidade de trabalho em W1–W3 os zera. Nesse caso a restrição
   deve ser **reaberta para repo público novo** (push do HEAD já saneado,
   sem PRs/issues/logs herdados). Descobrir isso em W8, após gastar W1–W3,
   é desperdício de todo o caminho crítico. Por isso o aceite é **G0**:
   falhar cedo.

3. **Rastreabilidade LGPD:** a decisão textual do owner (assinar T3 **ou**
   reabrir) fica registrada nesta ADR ao flip para `Decidido`, servindo de
   base de accountability caso um titular de dado invoque direito de
   eliminação sobre metadados residuais.

## Alternativas consideradas

- **A — Repo público novo (zera as 3 camadas de uma vez).** Push do HEAD já
  saneado, sem PRs/issues/logs herdados, sem rewrite/bypass de Ruleset/
  triagem de metadados. Arquiteturalmente **superior** para a camada 3.
  **Objeção 1 do co-design (4/5 especialistas):** como o repo privado nunca
  teve tráfego/stars externos, o custo-benefício do in-place é fraco;
  ~30min do owner reconsiderar valem o descarte de W3+W4 inteiros.
  **Rejeitada pela restrição do owner** — reabre apenas se o owner exigir
  zero-risco (cláusula acima).
- **B — Aceitar todo o risco de metadados sem triagem.** Não editar nada;
  flip com os 855 itens intactos. Rejeitada: T1 contém PII direta e IP
  competitivo — dano legal (LGPD) e de negócio ativo; a triagem T1 é barata
  e mecanizável relativamente ao dano evitado.
- **C — Whitepaper público em vez de flip do repo (Objeção 2, GTM).** "Ser
  referência open-source" não é alavanca GTM validada para o ICP (HENRY
  brasileiro que compra seriedade metodológica, não GitHub stars). Público
  que admira ≠ público que paga. Se o objetivo real é *transparência
  metodológica para confiança do cliente*, um whitepaper resolve sem expor
  o motor competitivo inteiro nem herdar 855 metadados. Escopo de
  [[ADR-314]] (escopo público) — registrada aqui como objeção viva ao
  *porquê* do flip.

## Consequências

- **Risco residual T3 é aceito e nomeado** — não é "resolvido". A dívida é
  explícita e rastreável, não silenciosa.
- **Triagem T1/T2 tem custo de trabalho manual** (edição/deleção via API,
  expiração de retention) e roda `∥` com o rewrite W3 ([[A34.l21]]) — não
  estende o caminho crítico.
- **Se o owner reabrir para repo novo,** W3 (rewrite) e W4 (metadados)
  saem do escopo; o esforço se desloca para push saneado + reconfiguração
  de Ruleset/Actions no repo novo. O plano [[PLAN-public-release]] absorve
  a bifurcação em G0.
- **A cláusula de incompatibilidade converte uma descoberta tardia e cara
  em uma decisão barata e adiantada** — é o ganho central de posicionar o
  aceite em W0.
- **A camada 3 permanece irredutível por git** mesmo com a triagem — a
  varredura ampla dos 855 itens além dos T1 é `should` pós-flip (janela
  A35, P2), não bloqueante do marco de segurança.

## Decisão do owner

> ADR owner-gated. Status permanece `Proposto` até o owner assinar uma das
> opções abaixo. G0 do [[PLAN-public-release]] não libera W1+ sem esta
> decisão.

- [ ] **Opção 1 — Assinar o risco residual T3 e manter o flip in-place.**
      Autorizo a triagem T1/T2 ([[A34.l21]]) e **aceito formalmente o risco
      residual T3** dos metadados GitHub imutáveis, ciente de que a camada 3
      é irredutível por git e rastreável para efeito de LGPD.
- [ ] **Opção 2 — Reabrir a restrição in-place (exijo zero-risco em
      metadados).** Reconheço a incompatibilidade lógica: metadados não se
      reescrevem. O flip migra para **repo público novo** com push do HEAD
      saneado; W3/W4 saem do escopo. Reabrir [[ADR-314]] e [[ADR-315]].

**Objeções registradas (ler antes de assinar):** (1) in-place é
arquiteturalmente inferior a repo novo para a camada 3 (Alternativa A);
(2) open-source não é alavanca GTM validada para o ICP — talvez whitepaper
(Alternativa C, [[ADR-314]]).
