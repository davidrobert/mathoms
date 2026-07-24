---
name: pipeline-review
description: >-
  Roda o pipeline COMPLETO de um workspace no ambiente local e produz uma
  revisão profunda priorizada — da execução E do relatório gerado — com tabela
  de prioridade/dificuldade/risco. Use SEMPRE que o dono pedir para "rodar o
  pipeline e analisar/revisar" um workspace, gerar um relatório novo e criticá-lo,
  revisar a saúde de um run de dogfood, disparar um run completo e avaliar o
  output, ou dizer algo como "entra no workspace X e roda tudo + faz a análise" —
  mesmo sem a palavra "skill". Recebe o workspace por email OU uuid.
---

# pipeline-review

Procedimento do **loop principal** (não é um agente) para: disparar um run
completo do pipeline de um workspace, **confirmar que ficou verde antes de
analisar**, e produzir uma revisão crítica priorizada delegando aos
especialistas do §Subagentes do CLAUDE.md, com verificação adversarial.

É **análise, não implementação** — não altere código nem abra PR; o entregável é
diagnóstico + plano de ataque priorizado. Deriva do processo testado que fechou
o plano [[PLAN-dogfood-report-fix]].

**Fronteira vs [[parse-certify]]:** aqui é o pipeline **inteiro** + o **relatório
final E5→E7**. Certificar a **ingestão E0→E2 documento-a-documento** (cada arquivo
virou artefato correto? a ingestão perdeu dado?) é a skill `parse-certify`.

Classe canônica (skill vs. subagente vs. prompt): [[ADR-302]]. Catálogo humano das
skills do repo: `docs/reference/SKILLS.md`.

## Parâmetros

- **workspace** (obrigatório) — email (ex.: `5@5.com`) ou UUID.
- **skip_llm** (default `false`) — run completo inclui as stages LLM (parecer,
  narrativas). Um run "com LLM" custa API real (~US$1–2) e leva ~25 min; só use
  `skip_llm=true` para um smoke determinístico (o relatório fica incompleto p/ revisão).

## Ambiente

Rode onde os serviços do pipeline estão de pé (API + Celery worker + Redis) e
onde vivem `.env`/DB/`.venv` — tipicamente o **checkout principal**, não um
worktree. Os scripts abaixo importam `backend` e leem `DATABASE_URL`/Fernet do
`.env`, então rode-os **da raiz do repo** com o venv do repo. Descubra o comando
canônico de run em [docs/reference/RUNBOOK.md](../../../docs/reference/RUNBOOK.md)
se `make pipeline-run` não existir mais.

## Passo 1 — Execução & baseline (estabeleça ANTES de analisar)

1. **Resolver + baseline:** `.venv/bin/python .claude/skills/pipeline-review/scripts/resolve_workspace.py <workspace>`.
   Guarde o `workspace_id`, o `latest_report` (para identificar o report NOVO
   depois) e o `latest_run`. Se `active_run` não for `null`, **PARE** — há um run
   em andamento; não dispare outro.
2. **Disparar run completo:** `make pipeline-run WS=<workspace_id> SKIP_LLM=0`.
   Capture o `Run <uuid> disparado` do stdout — esse é o `run_id`. Não use `RESET`
   (destrutivo); um run completo recomputa `FULL_ORDER` e sobrescreve os artifacts.
3. **Aguardar terminal:** o run executa no worker Celery. Faça poll do DB a cada
   ~60–90s até status terminal (não use `sleep` em foreground; rode o loop em
   background e seja notificado):
   ```bash
   for i in $(seq 1 45); do
     ST=$(sqlite3 mathoms.db "SELECT status FROM pipeline_runs WHERE id='<run_id>';")
     [ "$ST" = completed ] || [ "$ST" = failed ] || [ "$ST" = cancelled ] && { echo "$ST"; break; }
     sleep 80
   done
   ```
   (Em Postgres, use `psql`.) **Se `failed`/`cancelled` → PARE**, reporte o
   `failed_at_stage`/`failure_reason`, e não analise um relatório parcial.
4. **Confirmar + achar o report novo:** `completed` → pegue o report deste run:
   `sqlite3 mathoms.db "SELECT id FROM reports WHERE pipeline_run_id='<run_id>';"`.
   Deve ser diferente do `latest_report` do baseline.
5. **Coletar insumos:** `.venv/bin/python .claude/skills/pipeline-review/scripts/collect_review_inputs.py <workspace_id> <report_id> _scratch/pipeline-review-<slug>-<AAAA-MM-DD>/`.
   Isso escreve `report_data.json`, `parecer.json`, `cross_validation.json` e
   `run_meta.md` (status/duração, needs_review por tipo, telemetria LLM). Leia o
   stdout: `CV_falhas` já aponta inconsistências de conservação/consistência.

## Passo 2 — Rubrica (avalie execução E relatório contra todas as lentes)

- **Correção:** números batem; conservação fecha (`cross_validation.json` — os CV
  são os checks de conservação); lineage rastreável. Para caçar de onde vem um
  número sem abrir stages inteiros, use `python3 dev/explain_number.py --field <dot.path> --format llm`.
- **Consistência:** o mesmo valor bate em todas as superfícies (determinístico ↔
  parecer ↔ narrativa ↔ score ↔ UI); moeda/sinal/período coerentes.
- **Completude:** seções vazias, dado faltando, `needs_review` não resolvido.
- **Clareza / UX:** hierarquia, legibilidade, copy, gráfico certo, estados vazios.
- **Solidez financeira:** aderência a metodologias consagradas de planejamento
  patrimonial (reserva, IF, alocação, dívida, proteção); recomendações fazem sentido.
- **Qualidade LLM (parecer + narrativas):** precisão vs os dados, ancoragem/citação,
  alucinação, drift, latência/retries anômalos.
- **Saúde de execução:** duração, custo LLM, reask storms, warnings.

## Passo 3 — Delegação aos especialistas (em PARALELO, com verificação adversarial)

Invoque em **uma mensagem, N chamadas** (ou um Workflow se disponível). Brief
mínimo: os arquivos coletados + a lente + peça **decisão/objeção com evidência**,
não código. Mapa lente → especialista:

| Dimensão | Especialista |
|---|---|
| Conservação, contratos de stage, telemetria, needs_review, colunas mortas | `data-engineer` |
| Solidez de domínio + qualidade das recomendações | `financial-planner` |
| Parecer + narrativas (precisão, citação, alucinação, custo/latência) | `prompt-engineer` |
| Clareza/UX do relatório (componentes React + dados) | `product-designer` |
| Invariantes cross-cutting, gates silenciosos, arquitetura | `senior-cto` |

Cada especialista retorna findings no schema abaixo. **Depois**, verifique cada
finding adversarialmente (um verificador cético por finding que tenta REFUTAR,
re-checando números empiricamente — re-rodar `validate_cross`, re-query DB, recomputar).
Descarte os REFUTED. Este passo mata "plausível mas errado" — foi ele que corrigiu
leads errados na revisão original (ex.: custo de run subcontado).

**Schema de finding:** `id` (prefixo por dimensão), `title`, `severity`
(Crítico|Alto|Médio|Baixo), `category`, `evidence` (`arquivo:linha` OU
`campo.dot.path` OU número concreto), `impact`, `recommendation`, `effort` (S|M|L),
`regression_risk` (Alto|Médio|Baixo), `confidence`.

## Passo 4 — Guardrails

- **Zero PII no entregável:** sem CPF, valores/nomes reais expostos como se fossem
  novos — use papéis (titular/cônjuge) e faixas. Os `*.json` coletados contêm PII
  (dados do próprio workspace); são insumo local, mas **nada de PII vaza para o
  relatório final ou artifact**. Nomes próprios como CHAVE de dict no E5 são um
  smell a reportar, não a reproduzir.
- **Evidência sempre:** `arquivo:linha` / `campo.dot.path` / número. Nada de "parece errado".
- **Verifique antes de reportar:** hipótese não confirmada não vira bug.

## Passo 5 — Entregável (três destinos · [[ADR-343]])

O achado da revisão é de **duas naturezas** e cada uma tem um destino durável
distinto — a bifurcação que mantém o vault PII-free por construção:

- **Sistêmico / defeito** — afirmação sobre o **pipeline** (código, contrato de
  stage, schema, render, prompt, metodologia). Recorre entre runs, PII-free.
- **Instância / dado** — afirmação sobre os números **deste workspace neste
  run**. Não recorre, carrega PII.

Escreva nos três destinos, nesta ordem:

1. **Working** → `_scratch/pipeline-review-<slug>-<data>.md` — o relatório
   completo (todas as naturezas, todas as evidências). Efêmero.
   Estrutura: **premissas → o que rodou (evidência do run) → achados por dimensão
   (severidade + evidência) → TABELA PRIORIZADA → próximos passos**, com critério
   de aceite.
   Tabela priorizada (ordenar por prioridade), colunas:
   `ID · Achado · Dimensão · Severidade · Prioridade (P0–P3) · Dificuldade (S/M/L) · Risco regr. · Fix recomendado · Quem flagou`
2. **Cru durável (off-git)** → `storage/<uuid>/reviews/<ts>-<run8>/synthesis.md`
   — cópia da síntese crua **inclusive achados de instância/dado + PII**. Path
   proibido no git (mesma zona de confiança do DB/artifacts/`certify/`);
   sobrevive entre sessões. (O `--compare`/baseline durável mora no mesmo dir —
   ver §Parâmetros.)
3. **Curado canônico (git)** → **append** de uma seção `## rN — ws-<uuid8>-<data>`
   em [`docs/_MOC/PIPELINE-REVIEWS-active.md`](../../../docs/_MOC/PIPELINE-REVIEWS-active.md)
   com **só os achados sistêmicos/defeito**, deduplicados por `(dimensão,
   evidência-âncora, regra)`. **Commit-safe:** zero literal monetário, zero nome
   próprio; âncora = `campo.dot.path` ou `arquivo:linha`, nunca um valor; o
   **título** tem de ser um defeito, não um dado. Siga a convenção timeless do
   próprio arquivo (cobertura 100%, disposição, cadência anti-zumbi). Ao abrir run
   novo, re-triar o `procede-aberto` da seção anterior.

Resuma no chat (PII-scrubbed). Se o volume justificar, gere também um dashboard
navegável como Artifact (clusters de causa-raiz + a matriz priorizada), sempre
PII-scrubbed.

## Critério de aceite da skill

Run **confirmado verde** (não parcial) + todas as lentes cobertas + toda linha da
tabela com evidência rastreável + **zero PII** vazada + findings sobreviventes à
verificação adversarial.

## Armadilhas (aprendidas na execução real)

- O run leva ~25 min; **confirme o terminal antes de analisar** — analisar um run
  parcial produz achados falsos.
- Telemetria de custo LLM vive em **duas tabelas** (`pipeline_run_costs` +
  `llm_call_log`) e nem toda stage LLM é instrumentada — não conclua custo por uma só.
- Falha de CI que parece de teste mas o step é `cancelled` costuma ser incidente
  de infra do GitHub Actions (fail-fast), não seu código.
- **Nunca** aterrisse achado de **instância/dado** no
  `PIPELINE-REVIEWS-active.md` (git) — é PII. Só defeito sistêmico entra lá;
  dado do workspace fica em `storage/<uuid>/reviews/` ([[ADR-343]]). Título de
  achado com valor monetário ou nome próprio é smell — reescreva como defeito.
