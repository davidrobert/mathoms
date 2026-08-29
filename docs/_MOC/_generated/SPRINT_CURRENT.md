> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A40

Volta para [`00-INDEX`](../00-INDEX.md).

open · in_progress.

## Open

- [[A40.l10]] — Ordem do plano com critério encodado + pendências acionáveis do dono · priority P1 · área produto · branch `a40-l10-pendencia-do-dono-e-ordem-do-plano`
- [[A40.l29]] — Editorial do ano de IF: dois anos concorrentes, eixo em quando em vez de quanto, e a faixa sem componente · priority P2 · área frontend/product-design/financial-planning · branch `a40-l29-editorial-do-ano-de-if`
- [[A40.l37]] — A tabela de IR tem três fontes, e uma é hardcoded contra a ADR-135 · priority P2 · área pipeline · branch `a40-l37-tabela-de-ir-tres-fontes`
- [[A40.l39]] — Posição por instituição: o header '31/12' mente para 10 de 16 linhas — separar visão corrente da fiscal · priority P1 · área pipeline/frontend/financial-planning · branch `a40-l39-posicao-visoes-corrente-fiscal`
- [[A40.l41]] — Frescor cross-pool: posição stale de 2025-03 vale R$ 206k no bruto contra IRPF 31/12/2025 de R$ 2,4k · priority P1 · área pipeline/financial-planning · branch `a40-l41-frescor-cross-pool-fonte-inteira`
- [[A40.l46]] — Resíduos do bloco de identidade (perfil): baseline de print não provada + variant feature sem o DNA do mockup · priority P2 · área frontend · branch `a40-l46-residuos-perfil-identidade`
- [[A40.l48]] — Polaridade de comparação é fixa por métrica, mas cobertura de reserva não é monotônica no alvo · priority P2 · área pipeline · branch `a40-l48-polaridade-de-comparacao-nao-monotonica`
- [[A40.l50]] — Abertos da investigação de exposição cambial: inventário verificado do que não foi atacado · priority P1 · área report/pipeline/financial-planning · branch `a40-l50-abertos-exposicao-cambial`
- [[A40.l51]] — Follow-ups órfãos da A40.l43: o que o co-design achou na vizinhança e ninguém está atacando · priority P1 · área frontend/pipeline/financial-planning · branch `a40-l51-followups-orfaos`
- [[A40.l55]] — Medida de linha no papel: prosa a 100–110 caracteres por linha no A4 · priority P3 · área frontend/report · branch `a40-l55-medida-de-linha-no-papel`
- [[A40.l57]] — O parecer lê o contrato antigo do bloco PGBL: guardrail com predicado morto e âncora que resolve null · priority P2 · área llm/pipeline · branch `a40-l57-parecer-le-contrato-antigo-do-pgbl`
- [[A40.l60]] — Conselho de seguro: cobertura recomendada sem ressalva fiduciária, e uma string que afirma invalidez sem fonte · priority P1 · área pipeline/frontend · branch `a40-l60-ressalva-e-separacao-do-conselho-de-seguro`
- [[A40.l72]] — Guarda de contrato no render: o relatório deixa de fechar 100% sobre payload que viola invariante · priority P1 · área frontend · branch `a40-l72-guarda-de-contrato-no-render`
- [[A40.l75]] — O gate de drift do MSW existe, está fora do CI e compara errado: a ADR-069 afirma uma proteção que nunca rodou · priority P2 · área frontend/testing · branch `a40-l75-msw-drift-gate-inerte`
- [[A40.l76]] — A FK de proveniência do E2 nunca foi populada: o tombstone erra 630 rows e duas ADRs descrevem uma aresta vazia · priority P1 · área pipeline/db · branch `a40-l76-proveniencia-de-artefato-e2`
- [[A40.l80]] — Denominador amputado: metade da carteira não tem dono, o investível a exclui e o bruto a inclui — cinco superfícies medem 'de quanto se sabe o dono' · priority P0 · área pipeline/financial-planning/report · branch `a40-l80-denominador-amputado`
- [[A40.l85]] — O gate de ancorabilidade roda sobre um corpus que não consegue reproduzir o colapso que ele existe para pegar · priority P1 · área llm/pipeline · branch `a40-l85-corpus-cardinalidade-real`
- [[A40.l86]] — Duas fontes decidem se uma folha é dinheiro: o format declarado no manifest e o palpite pelo nome do campo · priority P2 · área llm/pipeline · branch `a40-l86-duas-fontes-de-monetariedade`
- [[A40.l92]] — A trilha de progresso ignora a polaridade do operador e enche conforme a métrica piora · priority P0 · área frontend/relatorio · branch `a40-l92-polaridade-do-comparador`
- [[A40.l94]] — Folga mensal reclassifica gasto pontual realizado como sobra recuperável · priority P0 · área pipeline/financial-planning · branch `a40-l94-folga-reclassifica-gasto-realizado`
- [[A40.l95]] — Numerador da concentração imobiliária inclui bem que o motor declara não-gerador · priority P0 · área pipeline/financial-planning · branch `a40-l95-numerador-de-concentracao-inclui-nao-gerador`
- [[A40.l96]] — Tabela de maiores ativos atribui titular a valor que o sistema declara órfão · priority P0 · área pipeline/frontend/financial-planning · branch `a40-l96-titular-atribuido-a-posicao-orfa`

## In progress

- [[A40.l25]] — Honestidade do cone de IF: precisão de exibição e sigma apresentado como premissa auditada · priority P1 · área pipeline/frontend/financial-planning · branch `a40-l25-honestidade-do-cone-if`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
>
> **Este arquivo não vê ocupação.** Ele deriva do frontmatter, que ninguém
> escreve no pickup: sessão que abriu worktree e ainda não commitou é
> invisível aqui, em `git for-each-ref` e em `gh pr list`. Antes de pegar
> qualquer lane abaixo, rode `python3 dev/lane_pickup.py <id>`.
