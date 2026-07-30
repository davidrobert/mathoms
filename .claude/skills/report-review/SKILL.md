---
name: report-review
description: >-
  Julga o RELATÓRIO JÁ ENTREGUE de um workspace (view-model E5 + parecer +
  renderer) sob rubrica de PRODUTO — atende a família? está claro? a recomendação
  nº 1 é a certa? falta algo? — com lentes em paralelo, braço cego, verificação
  adversarial e crítico de completude. Use SEMPRE que o dono pedir para "revisar
  o último relatório" de um workspace, criticar um relatório que já existe,
  avaliar se o relatório serve a família, checar se as recomendações estão certas
  e completas, ou dizer algo como "analisa o relatório do workspace X" — mesmo
  sem a palavra "skill". NÃO dispara run e não custa API de pipeline; se o pedido
  for "rodar o pipeline e analisar", a skill é `pipeline-review`. Recebe o
  workspace por email OU uuid (+ `report_id` opcional).
---

# report-review

Procedimento do **loop principal** (não é um agente) para julgar o **artefato já
entregue** a uma família — o relatório — e produzir um diagnóstico priorizado com
verificação adversarial.

É **análise, não implementação** — não altere código nem abra PR; o entregável é
diagnóstico + tabela priorizada. Deriva do processo que produziu a rodada `r3`
(33 achados sistêmicos) em [[REPORT-REVIEWS-active]].

## Fronteira vs as 3 skills vizinhas

| Skill | Objeto | Dispara run? |
|---|---|---|
| [[parse-certify]] | Ingestão E0→E2, documento-a-documento | não |
| [[ledger-certify]] | Razão E3+E4, no grão transação/posição | não |
| [[pipeline-review]] | **Dispara** um run completo e avalia a saúde da **execução** + o relatório **como saída desse run** (~25 min, ~US$2 de API) | **sim** |
| **`report-review`** (esta) | O **relatório já existente**, sob rubrica de **produto** — mérito para a família, não saúde de execução | **não** (custo zero) |

O encadeamento natural é `pipeline-review` (produz e valida o run) → `report-review`
(julga o mérito do output). A fronteira estável não é o grão — ambas terminam no
relatório — é **"dispara run?"**, uma assimetria de custo de duas ordens de grandeza.

Classe canônica (skill vs. subagente vs. prompt): [[ADR-302]] — 5ª instância, sem ADR
própria. Disciplina de estado durável: [[ADR-343]]. Catálogo humano:
`docs/reference/SKILLS.md`.

## Parâmetros

- **workspace** (obrigatório) — email (ex.: `5@5.com`) ou UUID.
- **report_id** (opcional) — default: o **último** report do workspace. Passe
  explicitamente para revisar um report histórico.
- **run_id** (opcional) — derivado do report; só passe se o vínculo estiver ambíguo.

## Ambiente

Rode no **checkout principal** (onde vivem `.env`/DB/`.venv`), não num worktree —
os scripts importam `backend` e leem `DATABASE_URL`/Fernet do `.env`.

**Antes de despachar qualquer subagente, rode `git pull --ff-only`.** Se a rodada
anterior foi commitada e mergeada, o checkout pode estar atrás e os pareceristas
vão ler um MOC sem a seção que você mandou ler. Isso já matou um painel inteiro.

## Passo 1 — Coleta, captura e índice de conhecidos

1. **Resolver:** `.venv/bin/python .claude/skills/pipeline-review/scripts/resolve_workspace.py <workspace>`
   (script compartilhado; não copie). Guarde `workspace_id` e `latest_report`.
2. **Coletar insumos:** `.venv/bin/python .claude/skills/pipeline-review/scripts/collect_review_inputs.py <workspace_id> <report_id> _scratch/report-review-<slug>-<AAAA-MM-DD>/`
   — escreve `report_data.json`, `parecer.json`, `cross_validation.json`, `run_meta.md`.
3. **Capturar as superfícies renderizadas** (fecha o débito de método da r3 — sem
   isto, toda afirmação de clareza/UX é inferência de código):
   ```
   .venv/bin/python .claude/skills/pipeline-review/scripts/capture_report_render.py <workspace> --out <dir>/render/
   ```
   Exige **frontend de pé**; recusa base-url não-localhost. Produz `screen.txt`,
   `print.txt` (mídia print emulada — o hook lê `matchMedia`, não o query param),
   `report.pdf` **pela função de produção** + `report.txt`, screenshots 1280/390,
   `anchors.json` e `MANIFEST.md` com provenance.
   **Leia `screen.txt`/`report.txt` e os PNGs — nunca dumps de HTML.**
   Se a perna de PDF falhar, isso **é o achado mais forte da rodada**: significa que
   o download do cliente está quebrado. Frontend fora do ar ⇒ declare `clareza-ux`
   sem cobertura, não finja que observou.
4. **Índice de conhecidos** — leia os MOCs de rodadas anteriores
   ([[REPORT-REVIEWS-active]], [[PIPELINE-REVIEWS-active]], [[LEDGER-CERTIFY-active]],
   [[PARSE-CERTIFY-active]]) e monte um índice dos achados **já registrados e
   abertos**. Sem ele a rodada re-descobre o que já está rastreado e infla o placar.

## Passo 2 — Rubrica

As **8 perguntas de produto**, a taxonomia de dimensão/severidade, os vereditos e a
calibração do cético vivem em [`references/rubric.md`](references/rubric.md). Carregue
sob demanda.

## Passo 3 — Lentes em paralelo + braço cego

Uma mensagem, N chamadas (ou um Workflow). Mapa lente → especialista é o mesmo do
§Subagentes do CLAUDE.md, **mais duas peças próprias desta skill**:

- **Lente de design** (`product-designer`) — obrigatória, porque metade das
  perguntas da rubrica é de clareza e usabilidade.
- **Braço cego** — um agente que lê **só os dados determinísticos** (`report_data.json`
  sem o `parecer.json`) e responde sozinho "qual é a recomendação nº 1 e por quê".
  Convergência independente com o parecer é o melhor sinal disponível para a
  pergunta Q6; divergência **é** o achado.

**REGRA DE LEITURA no brief de todo subagente** (aprendida na falha): proíba
explicitamente `storage/` e a leitura de `.json` de payload. O `report_data.json`
tem dezenas de MB; agentes apontados para a pasta se afogam nele e estagnam sem
retornar nada. Dê o caminho de **um** comando de extração (ex.: `sed -n` da seção do
MOC) e no máximo 3-4 arquivos de código.

## Passo 4 — Clusterização com gate de cobertura

Funda os achados das lentes em clusters por `(dimensão, âncora, regra)`.

**Gate obrigatório antes de fechar o passo:** toda lente declarada tem de aparecer no
campo `lentes` de ≥1 cluster, e todo achado vivo precisa de disposição explícita
(clusterizado **ou** descartado com motivo escrito). Na `r3`, uma lente inteira ficou
fora do circuito e 96 de 188 achados evaporaram no merge — a dimensão dela ficou sem
cobertura verificada e ninguém percebeu até o crítico de completude.

## Passo 5 — Verificação adversarial

Um cético por cluster, com a tarefa de **REFUTAR**. Cada um devolve veredito
(`CONFIRMADO` | `PARCIAL` | `REFUTADO`), severidade corrigida, triagem
(`NOVO` | `JÁ-CONHECIDO` | `MEDIÇÃO-DE-CONHECIDO`) e a flag **`inerte_para_usuario`**
— defeito real que não alcança o usuário nesta configuração. Na `r3`, 7 de 44 eram
inertes, e um deles só era inerte **por causa** de outro achado da lista; marcar isso
evita gastar prioridade.

**Calibração (regra dura):** taxa de `REFUTADO` igual a zero é *tripwire do método*,
não sinal de que os achados eram bons. Cético que não consegue refutar tem de declarar
**qual medição faria a refutação**. `PARCIAL` sem rebaixamento medido é smell.

## Passo 6 — Crítico de completude

Um agente que audita **o próprio processo desta rodada**: qual pergunta ficou com
cobertura fraca, que seções do relatório ninguém olhou, que `CONFIRMADO` se apoia em
evidência fraca, que refutação foi escopada e vendida como total, e **qual verificação
barata de 1 comando fecharia o claim pivotal**. Na `r3` ele achou três furos que
valeram mais que vários achados.

## Passo 7 — Fechamento determinístico

Pelo menos **um** claim pivotal tem de ser fechado por medição, não inferência. Rode o
comando que o crítico indicou e reporte o resultado mesmo que ele **derrube** achados
seus — na `r3` isso derrubou três afirmações, uma delas invertendo a direção do erro.

## Passo 8 — Guardrails

- **Zero PII no destino git.** Os `*.json` coletados contêm PII; são insumo local.
  Título de achado com literal monetário ou nome próprio é smell — reescreva como
  defeito. Âncora é `campo.dot.path` ou `arquivo:linha`, **nunca** um valor.
- **Evidência sempre.** Hipótese não confirmada não vira achado.
- **Rotule o que não foi observado.** Afirmação de clareza/usabilidade feita sem a
  captura do Passo 1.3 é *inferência de código* e tem de dizer isso.
- **Artefatos de render são o material mais sensível da rodada** — são o documento
  entregue, com PII já interpolada. Vivem em `storage/<uuid>/reviews/<...>/render/`
  e **nunca** são citáveis no MOC git. Screenshot é o vazamento mais fácil de
  cometer: não cole, não anexe, não descreva conteúdo nominal.

## Passo 9 — Entregável (três destinos · [[ADR-343]])

1. **Working** → `_scratch/report-review-<slug>-<data>/` — efêmero, tudo.
2. **Cru durável (off-git)** → `storage/<uuid>/reviews/<data>-<run8>/SINTESE.md` —
   as 8 perguntas respondidas + tabela priorizada + valores + PII.
3. **Curado canônico (git)** → append de `## rN — ws-<uuid8>-<data>` em
   [`docs/_MOC/REPORT-REVIEWS-active.md`](../../../docs/_MOC/REPORT-REVIEWS-active.md),
   **só achados sistêmicos**, deduplicados. Registre também o **débito de método** da
   rodada — os furos do Passo 6 são o insumo mais reusável que ela produz.

## Critério de aceite da skill

Todas as 8 perguntas respondidas (ou declaradas sem cobertura, com o motivo) · gate de
cobertura do Passo 4 verde · todo cluster com veredito e triagem · ≥1 claim pivotal
fechado por medição · zero PII no destino git · débito de método registrado.

## Armadilhas (aprendidas na execução real)

- **Não aponte subagente para `storage/`.** Foi assim que um painel de 7 morreu:
  cada agente queimou ~300k tokens lendo payload e estagnou sem devolver nada.
- **`git pull` antes de despachar** — pareceristas leem o checkout, não o `origin/main`.
- **Conservação por grupo não detecta duplicação entre grupos.** O razão pode fechar
  em tol-zero com duplicação material presente; conservação é o piso, não a prova.
- **`pipeline_artifacts.content_json` é `{_encrypted, kid, ct}`** — `sqlite3` direto
  não lê; use o harness in-process.
- **Retomada de Workflow não é replay puro:** re-roda ao vivo tudo a partir do
  primeiro agente que falhou, e vereditos podem mudar entre execuções. Útil de
  propósito (dois céticos independentes expõem discordância real), mas não conte com
  idempotência.
