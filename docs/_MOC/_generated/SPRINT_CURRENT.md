> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A40

Volta para [`00-INDEX`](../00-INDEX.md).

open · in_progress.

## Open

- [[A40.l10]] — Ordem do plano com critério encodado + pendências acionáveis do dono · priority P1 · área produto · branch `a40-l10-pendencia-do-dono-e-ordem-do-plano`
- [[A40.l102]] — Superfície do gasto pontual: dedup do par publicado sob promessa de unicidade + o que cada superfície declara excluir · priority P2 · área pipeline/frontend · branch `a40-l102-superficie-do-pontual-e-dedup`
- [[A40.l105]] — Aprovação-com-avisos é indistinguível de nunca-ter-pausado no desfecho do run, e é o desfecho que alimenta o banner de qualidade · priority P2 · área pipeline · branch `a40-l105-aprovacao-com-avisos-indistinguivel`
- [[A40.l106]] — O relatório não emite índice de seção algum no mobile: rolagem longa sem navegação, enquanto o desktop emite o índice completo · priority P2 · área frontend · branch `a40-l106-relatorio-sem-indice-no-mobile`
- [[A40.l107]] — A conversão tabela→cartão no mobile é aplicada por componente, não por regra: 11 tabelas largas não convertem, e há um terceiro comportamento não previsto · priority P2 · área frontend · branch `a40-l107-conversao-tabela-cartao-por-componente`
- [[A40.l108]] — Um mesmo ano nomeia o cenário central e o de estresse, enquanto o cenário base do mesmo apêndice é outro · priority P2 · área produto · branch `a40-l108-um-ano-nomeia-cenario-central-e-de-estresse`
- [[A40.l109]] — A lista do card lê o artefato mais recente sob um relatório pinado e imutável · priority P1 · área backend/frontend · branch `a40-l109-lista-le-latest-sob-relatorio-pinado`
- [[A40.l112]] — Imóvel sem classificação nenhuma entra no numerador da concentração pelo `else`, e reclassificar um deles move o KPI de 82 para 0 · priority P2 · área dados/pipeline · branch `a40-l112-imovel-sem-override-cai-no-numerador`
- [[A40.l114]] — O ano de referência é saída crua do LLM, e o total de dívida vira zero quando esse ano não existe em documento nenhum · priority P0 · área pipeline/financial-planning · branch `a40-l114-ano-de-referencia-sem-documento-atras`
- [[A40.l116]] — O guard de autocontradição do parecer erra a seção pela terceira vez, e o teste que o cobre importa a própria constante — cego por construção · priority P1 · área backend · branch `a40-l116-guard-de-liquidez-erra-a-secao-e-o-teste-e-cego`
- [[A40.l117]] — O parecer publica dois números para a mesma coisa, cita a seção errada em 4 de 11 riscos, e o prompt se contradiz sobre ter ferramentas · priority P1 · área backend · branch `a40-l117-parecer-dois-numeros-e-citacao-desorientada`
- [[A40.l118]] — Campo emitido sem consumidor pode carregar valor errado, e o gate de classe mede existência do leitor — nunca a corretude do número · priority P2 · área pipeline/frontend · branch `a40-l118-valor-errado-em-campo-sem-leitor`
- [[A40.l29]] — Editorial do ano de IF: dois anos concorrentes, eixo em quando em vez de quanto, e a faixa sem componente · priority P2 · área frontend/product-design/financial-planning · branch `a40-l29-editorial-do-ano-de-if`
- [[A40.l37]] — A tabela de IR tem três fontes, e uma é hardcoded contra a ADR-135 · priority P2 · área pipeline · branch `a40-l37-tabela-de-ir-tres-fontes`
- [[A40.l39]] — Posição por instituição: o header '31/12' mente para 10 de 16 linhas — separar visão corrente da fiscal · priority P1 · área pipeline/frontend/financial-planning · branch `a40-l39-posicao-visoes-corrente-fiscal`
- [[A40.l41]] — Frescor cross-pool: posição stale de 2025-03 vale R$ 206k no bruto contra IRPF 31/12/2025 de R$ 2,4k · priority P1 · área pipeline/financial-planning · branch `a40-l41-frescor-cross-pool-fonte-inteira`
- [[A40.l48]] — Polaridade de comparação é fixa por métrica, mas cobertura de reserva não é monotônica no alvo · priority P2 · área pipeline · branch `a40-l48-polaridade-de-comparacao-nao-monotonica`
- [[A40.l50]] — Abertos da investigação de exposição cambial: inventário verificado do que não foi atacado · priority P1 · área report/pipeline/financial-planning · branch `a40-l50-abertos-exposicao-cambial`
- [[A40.l51]] — Follow-ups órfãos da A40.l43: o que o co-design achou na vizinhança e ninguém está atacando · priority P1 · área frontend/pipeline/financial-planning · branch `a40-l51-followups-orfaos`
- [[A40.l55]] — Medida de linha no papel: prosa a 100–110 caracteres por linha no A4 · priority P3 · área frontend/report · branch `a40-l55-medida-de-linha-no-papel`
- [[A40.l57]] — O parecer lê o contrato antigo do bloco PGBL: guardrail com predicado morto e âncora que resolve null · priority P2 · área llm/pipeline · branch `a40-l57-parecer-le-contrato-antigo-do-pgbl`
- [[A40.l60]] — Conselho de seguro: cobertura recomendada sem ressalva fiduciária, e uma string que afirma invalidez sem fonte · priority P1 · área pipeline/frontend · branch `a40-l60-ressalva-e-separacao-do-conselho-de-seguro`
- [[A40.l72]] — Guarda de contrato no render: o relatório deixa de fechar 100% sobre payload que viola invariante · priority P1 · área frontend · branch `a40-l72-guarda-de-contrato-no-render`
- [[A40.l75]] — O gate de drift do MSW existe, está fora do CI e compara errado: a ADR-069 afirma uma proteção que nunca rodou · priority P2 · área frontend/testing · branch `a40-l75-msw-drift-gate-inerte`
- [[A40.l76]] — A FK de proveniência do E2 nunca foi populada: o tombstone erra 630 rows e duas ADRs descrevem uma aresta vazia · priority P1 · área pipeline/db · branch `a40-l76-proveniencia-de-artefato-e2`
- [[A40.l85]] — O gate de ancorabilidade roda sobre um corpus que não consegue reproduzir o colapso que ele existe para pegar · priority P1 · área llm/pipeline · branch `a40-l85-corpus-cardinalidade-real`
- [[A40.l86]] — Duas fontes decidem se uma folha é dinheiro: o format declarado no manifest e o palpite pelo nome do campo · priority P2 · área llm/pipeline · branch `a40-l86-duas-fontes-de-monetariedade`
- [[A40.l92]] — A trilha de progresso ignora a polaridade do operador e enche conforme a métrica piora · priority P0 · área frontend/relatorio · branch `a40-l92-polaridade-do-comparador`
- [[A40.l99]] — Cinco ADRs em Proposto com lane fechada declaram decisão que não está em vigor · priority P3 · área dominio · branch `a40-l99-adr-proposta-com-lane-fechada`

## In progress

- [[A40.l113]] — A identidade de imóvel churna entre runs e os dois classificadores falham FECHADOS: residência e imóvel gerador são publicados como zero · priority P0 · área pipeline/financial-planning · branch `a40-l113-identidade-de-imovel-churna-classificador-falha-fechado`
- [[A40.l25]] — Honestidade do cone de IF: precisão de exibição e sigma apresentado como premissa auditada · priority P1 · área pipeline/frontend/financial-planning · branch `a40-l25-honestidade-do-cone-if`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
>
> **Este arquivo não vê ocupação.** Ele deriva do frontmatter, que ninguém
> escreve no pickup: sessão que abriu worktree e ainda não commitou é
> invisível aqui, em `git for-each-ref` e em `gh pr list`. Antes de pegar
> qualquer lane abaixo, rode `python3 dev/lane_pickup.py <id>`.
