---
id: MOC-sprint-a43
type: moc
title: "Sprint A43 — Compatibilidade AI-native: Mathoms confiável no ChatGPT, Codex e clientes MCP"
aliases: ["A43", "Sprint A43"]
sprint_status: candidate
date: "2026-08-14"
theme: "ai-client-compatibility"
---

# Sprint A43 — Compatibilidade AI-native: ChatGPT, Codex e clientes MCP

> **Status:** `candidate`. A [[A40]] permanece `current`; a [[A42]] é a
> predecessora operacional desta sprint. As lanes nascem `planned` e não estão
> autorizadas para pickup antes do §Gatilho de promoção.

> **Origem:** avaliação de compatibilidade 2026-08-13, materializada em 2026-08-14,
> sobre código, arquitetura,
> plano [[PLAN-competitive-pierre]] e documentação oficial OpenAI. Veredito:
> Mathoms já usa OpenAI por meio do adapter LiteLLM, mas ainda não oferece uma
> integração nativa comprovada com ChatGPT/Codex — não há servidor MCP, OAuth
> compatível, plugin/skill, contratos externos minimizados ou eval cross-surface.

> **Fonte de verdade:** esta sprint executa a fase de compatibilidade de
> [[PLAN-competitive-pierre]]. Não cria um segundo plano `COMPAT_CHATGPT`; o plano
> existente preserva tese, moats e decisões anteriores, enquanto a A43 possui o
> escopo operacional e os gates de entrega.

## Objective

**Permitir que uma família autorizada consulte o relatório e o plano Mathoms no
ChatGPT e no Codex com a mesma corretude, atualidade, rastreabilidade e separação
entre workspaces do produto — sem copiar JSON, token ou documento bruto.**

O job central é estreito: *“entender o meu relatório Mathoms no cliente de IA que
já uso, com fonte verificável, sem transformar o cliente externo no dono do meu
patrimônio ou da metodologia”*.

## Tese e corte de arquitetura

A compatibilidade é uma **porta de leitura**, não um segundo motor financeiro:

1. **Mathoms continua soberano** sobre cálculo, regras, dados, entitlement,
   autorização e auditoria.
2. **MCP é o boundary vendor-neutral**. Ele chama application use cases/read-models
   tipados; não consulta o banco ad hoc, não faz loopback HTTP e não entra em
   `pipeline/**`.
3. **Plugin OpenAI é um shell fino** — manifesto + skill público mínimo + referência
   ao MCP. A documentação oficial define plugins como composição de skills, MCP e UI
   opcional e recomenda começar pela menor forma que atende o job.
4. **OAuth 2.1 entra no MVP com dado real.** API key e IP allowlist não substituem
   autorização do usuário no ChatGPT. O token é verificado a cada chamada e nunca
   transforma `workspace_id` fornecido pelo modelo em autoridade.
5. **App Mathoms continua funcional sem o canal externo.** Indisponibilidade,
   mudança de termos ou remoção do plugin não degrada pipeline, relatório ou login.

O core deve ser consumível por clientes MCP compatíveis. O compromisso binário da
sprint, porém, é **ChatGPT + Codex (2/2)**; um MCP Inspector e um terceiro cliente
podem servir como testemunhas de portabilidade, sem prometer suporte universal não
testado.

## Definição de compatibilidade

| Dimensão | Prova exigida no fechamento |
| --- | --- |
| **Protocolo** | servidor remoto MCP sobre HTTPS/Streamable HTTP; discovery e schemas passam no Inspector |
| **Identidade** | OAuth 2.1 authorization-code + PKCE S256; issuer, audience, expiry e scopes verificados em toda chamada |
| **Autorização** | sujeito × scope × grant de workspace × membership atual; revogação e remoção de membro mordem na chamada seguinte |
| **Dados** | DTOs externos tipados, limitados e redigidos; zero documento/raw E5/CPF/token/ID interno desnecessário |
| **Produto** | os três jobs centrais funcionam em dois relatórios/runs distintos, com fonte e idade do dado |
| **Superfície** | o mesmo plugin/skill completa o corpus canônico no ChatGPT e no Codex |
| **Operação** | audit, rate limit, correlação, métricas e runbook; falha do canal não afeta o app |
| **Provider OpenAI** | catálogo/preço/smoke refletem a família corrente documentada na data da implementação, sem alias silencioso |

## KRs

Todos os KRs são binários ou têm denominador explícito; não usam percentuais de
adoção incompatíveis com o dogfood N=1.

| KR | Medida | Anti-Goodhart |
| --- | --- | --- |
| **KR-A · conexão real 2/2** | ChatGPT e Codex concluem OAuth e recuperam o relatório atual sem token/JSON manual | gravação/evidência de duas sessões novas; conexão já autenticada não conta |
| **KR-B · corretude rastreável** | ≥9/10 tarefas canônicas corretas; 100% das respostas suportadas trazem fonte + `as_of`; pedidos fora do escopo recusam com segurança | eval usa dois reports/runs; demo congelada em um payload não fecha |
| **KR-C · isolamento** | 0 acesso cross-workspace na matriz negativa; expired/revoked token e membership removida falham na chamada seguinte | teste cria dois tenants-pai reais; trocar apenas o argumento de workspace deve falhar |
| **KR-D · minimização** | 0 ocorrência de CPF, token, texto bruto, documento ou ID interno no resultado e na telemetria | scanner roda sobre sucesso **e** erros; remover campo só do happy path não fecha |
| **KR-E · reversibilidade** | desligar plugin/MCP não altera app, API interna ou pipeline; adapter específico OpenAI não invade domínio | gate de imports + teste do app com MCP disabled |

Health metrics, não KRs: tool-call success ≥95%; p95 do servidor <1 s sem tempo do
modelo; funil `auth_started → auth_completed → first_valid_answer`; erros por
tool/scope; idade do relatório; zero payload financeiro em logs/traces.

## Escopo funcional do MVP

Três jobs, modelados por resultado do usuário — não por espelho da API interna:

1. **Resumo atual:** localizar o relatório publicado/corrente e devolver resumo
   patrimonial minimizado, `as_of`, qualidade/degradações e deep link para Mathoms.
2. **Plano e decisões:** listar decisões ativas e próximos passos publicados, com
   status, prioridade e origem, sem mutar estado.
3. **Explicar um número:** explicar um indicador publicado usando valor canônico,
   unidade, período, seção e fontes já materializadas; nunca recalcular no cliente.

Os nomes finais das tools são decididos na [[A43.l3]], após o contrato do job. A
intenção inicial é `get_report_summary`, `get_active_decisions` e
`explain_published_metric`; `list_reports` pode existir como locator paginado se o
usuário tiver mais de um relatório.

## Lanes (9)

| Lane | Entrega | Prio | Onda | Depende de |
| --- | --- | --- | --- | --- |
| [[A43.l1]] | ADR do boundary MCP + ameaça reversa + rebaseline do plano | P1 | 0 | — |
| [[A43.l2]] | Decisão build-vs-buy de OAuth/IdP + consentimento e scopes | P1 | 0 | — |
| [[A43.l3]] | Contratos externos/read-models minimizados + corpus de 10 tarefas | P1 | 1 | [[A43.l1]] |
| [[A43.l4]] | Core MCP remoto read-only com três jobs | P1 | 2 | [[A43.l3]] |
| [[A43.l5]] | OAuth 2.1 e autorização workspace-scoped com revogação | P0 | 2 | [[A43.l2]], [[A43.l4]] |
| [[A43.l6]] | Audit, rate limit, SLO, redaction e runbook do canal | P1 | 3 | [[A43.l4]], [[A43.l5]] |
| [[A43.l7]] | Plugin/skill universal mínimo para ChatGPT e Codex | P1 | 3 | [[A43.l4]], [[A43.l5]] |
| [[A43.l8]] | Certificação cross-surface + matriz adversarial + kill switch | P0 | 4 | [[A43.l6]], [[A43.l7]] |
| [[A43.l9]] | Currentness OpenAI: catálogo, preços, smoke e política de upgrade | P2 | 1 | — |

**Capacidade:** nove lanes, cinco ondas. Onda 2 é serial no caminho crítico:
[[A43.l4]] entrega o servidor sintético/local e [[A43.l5]] autoriza dado real. Não há
atalho “API key temporária em produção”; API key só pode existir num spike isolado com
fixture sintética e nunca fecha lane.

## Ondas

### Onda 0 — decisões que evitam retrabalho

[[A43.l1]] e [[A43.l2]] rodam em paralelo. A primeira decide boundary, deployment,
trust model e saída; a segunda decide IdP/bridge com TCO, LGPD e custo de migração.
Ambas precisam estar mergeadas antes de código produtivo. O JWT interno não vira
authorization server por extensão oportunista.

### Onda 1 — contrato antes do transporte

[[A43.l3]] define os três jobs, DTOs, limites, `as_of`, fontes, falhas e corpus golden.
[[A43.l9]] é independente: certifica o uso da OpenAI como provider sem acoplar o MCP
ao modelo corrente. “Modelo mais novo” não é sinônimo de compatibilidade ChatGPT.

### Onda 2 — servidor e identidade

[[A43.l4]] implementa o core MCP sobre ports/read-models. [[A43.l5]] adiciona OAuth,
grant de workspace, scopes e revogação. Nenhuma conexão externa recebe dado real antes
da matriz de autorização da l5 ficar verde.

### Onda 3 — operação e distribuição privada

[[A43.l6]] torna o canal operável sem registrar payload; [[A43.l7]] empacota a mesma
capacidade para ChatGPT e Codex. UI customizada não entra: structured result + resposta
do modelo bastam para os jobs do MVP.

### Onda 4 — prova, não demonstração

[[A43.l8]] executa o corpus em duas superfícies, dois relatórios e dois tenants, testa
falhas e documenta desligamento. Só ela autoriza o rótulo **compatível**.

## Gatilho de promoção a `current`

Evento, não calendário:

1. [[A40]] está `done` pelo próprio gate de dois re-runs; e
2. [[A42]] está `done` após `parse-certify` r3 + `ledger-certify` r5; e
3. não existe P0/P1 aberto que afete algum campo exposto pelos três jobs; e
4. o owner autoriza o spend/contrato do IdP escolhido ou restringe a sprint a spike
   sintético; e
5. existe parecer jurídico/privacidade suficiente para definir se dados reais podem
   alcançar o plano ChatGPT usado no piloto.

ADRs/docs da Onda 0 podem ser escritos antes da promoção, mas implementação produtiva
não compete com A40/A42. A [[A41]] não bloqueia o MVP read-only: passa a bloquear chat
interno ou nova chamada LLM server-side, ambos fora do escopo.

## Gate de fechamento

A43 só vira `done` quando:

1. KR-A..E estão verdes e evidenciados no `_README`/changelog da sprint.
2. O corpus de 10 tarefas passa no ChatGPT e no Codex sobre dois reports/runs.
3. A matriz negativa cobre, no mínimo: sem token; token expirado; issuer errado;
   audience errado; scope ausente; workspace trocado; membership removida; relatório
   inexistente; payload grande; tentativa de prompt injection; revogação; rate limit.
4. Cada tool declara input/output/falhas, é read-only e tem limites explícitos.
5. Audit registra `actor_id`, `workspace_id`, client/channel, tool, status, latência e
   correlation id — nunca valor financeiro, argumento livre ou resultado.
6. Runbook cobre deploy, rollback, revogação global, indisponibilidade do IdP/OpenAI,
   incidente cross-tenant e rotação de credenciais.
7. Plugin/MCP podem ser desabilitados por configuração sem deploy e sem afetar o app.
8. PRs de código estão mergeados por squash em `origin/main`, com CI verde no merge.

## Fora do escopo / Won't now

- escrita/criação/aceite de Decision ou Suggestion;
- `query_transactions`, busca livre/bulk de transações ou export de raw E5;
- PDF/documentos/IRPF/CPF e conteúdo de upload como tool result;
- UI customizada, chat first-party, histórico conversacional ou memories surface;
- Custom GPT, catálogo público, registry público ou promessa de suporte universal;
- substituir LiteLLM ou migrar todos os prompts para Responses API;
- regras-as-code, prompts de produção ou nomes de metodologistas dentro do skill;
- MCP compondo o SLO do produto principal.

Publicação universal é MMP posterior: exige beta convidado, DPA/transferência/
retenção decididos, termos/privacy/support e nova decisão explícita de go-live.

## Riscos e resposta

| Risco | Resposta/gate |
| --- | --- |
| vazamento cross-tenant | grant bound a workspace + membership revalidada + matriz 2-tenant |
| egress de patrimônio para conversa externa | DTO mínimo, consentimento, `as_of`, scanner anti-PII e piloto restrito |
| lock-in OpenAI | core MCP vendor-neutral; shell OpenAI sem regra de domínio; app fallback |
| churn do protocolo/SDK | versão pinada, contract tests e atualização deliberada |
| hallucination do host | tool retorna fatos estruturados + fonte; não delega cálculo ao modelo |
| indisponibilidade de cliente/IdP | timeout/circuit breaker, kill switch e canal opcional |
| skill vaza método proprietário | instrução pública mínima; gate [[ADR-207]]/[[ADR-319]] |
| sprint vira plataforma conversacional | Won't now e três jobs fechados; expansão exige nova priorização |

## Referências oficiais verificadas em 2026-08-14

- [Arquitetura de plugins](https://developers.openai.com/plugins/concepts/plugins) —
  ChatGPT e Codex compartilham diretório; plugin combina skill, MCP e UI opcional.
- [Definição de tools](https://developers.openai.com/plugins/plan/tools) — contratos
  orientados ao job, inputs/outputs/auth/falhas e separação read/write.
- [Autenticação](https://developers.openai.com/plugins/build/auth) — OAuth 2.1,
  authorization-code, PKCE S256, metadata e verificação por request.
- [Empacotamento](https://developers.openai.com/plugins/build/plugins) — manifesto
  `.codex-plugin/plugin.json`, skill e referências MCP.
- [Segurança e privacidade](https://developers.openai.com/plugins/guides/security-privacy)
  — least privilege, consentimento, minimização e proteção contra prompt injection.
- [Conectar e testar](https://developers.openai.com/plugins/deploy/connect-chatgpt) —
  developer mode, conexão do MCP e verificação antes de publicar.
- [Catálogo de modelos](https://developers.openai.com/api/docs/models) — fonte
  temporal para a [[A43.l9]]; o sprint não congela “latest” em prosa.

## Relações

- Plano canônico: [[PLAN-competitive-pierre]].
- Trust do payload exposto: [[PLAN-report-trust]], [[A40]], [[A42]].
- Auth/portabilidade: [[ADR-109]], [[ADR-170]].
- DNS/deployment: [[ADR-108]].
- Observabilidade/stateless: [[ADR-110]], [[ADR-111]].
- Prompt injection e sigilo: [[ADR-175]], [[ADR-207]], [[ADR-319]].
