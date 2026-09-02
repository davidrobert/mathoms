---
id: ADR-438
type: adr
title: "Destino de leitura do parecer é derivado pela máquina, não escolhido pela prosa"
status: Proposto
date: "2026-09-02"
phase: A40.l117
tags:
  - type/adr
  - status/proposto
  - area/llm
  - area/backend
relates_to:
  - "[[ADR-153]]"
  - "[[ADR-199]]"
  - "[[ADR-290]]"
  - "[[ADR-296]]"
  - "[[ADR-399]]"
---

# ADR-438 — Destino de leitura do parecer é derivado, não escolhido pela prosa

**Status:** Proposto (A40.l117) · **Data:** 2026-09-02 · **Lane:** [[A40.l117]]

## Decisão

> `section_id` do parecer é **destino de leitura derivado pela máquina**: sai do JSON
> Schema exposto ao modelo via `SkipJsonSchema` e é estampado no pós-LLM por cascata
> determinística **`metrica_key` → raiz-com-sede-única → tema → síntese → `S_parecer`**,
> com os mapas apontando para **card** e a seção resolvida pelo `report_layout.yaml`.

## Contexto

Medido no run `40d1af2a`: **4 de 11 riscos** citavam seção errada, e a S9 — literalmente
*"Riscos e Sucessão — Lacunas de Proteção"* — recebia **0 de 11**, enquanto dois riscos de
proteção apontavam para a seção de imóveis.

O campo não é rótulo. Ele **roteia guardrail** (`parecer_pos_llm_guardrails.py`, o
rebaixamento de confiança de Monte Carlo) e **compõe `thesis_key`**
(`parecer_finalization.py`), que sustenta a janela de respeito ao descarte
([[ADR-290]] B4). Campo que roteia controle, é imutável após inserção ([[ADR-153]] §D1) e
não tem rota de reask ([[ADR-292]]) não pertence ao contrato do modelo — mesmo critério
que já produziu `SkipJsonSchema` em `Metrica.nome/valor_atual/target` ([[ADR-399]] D1).

## Por que NÃO injetar o id no exec context

A alternativa considerada era ensinar o modelo: injetar `[section_id: SN]` no cabeçalho de
cada seção destilada, pelo precedente da [[ADR-399]] (*"quando o valor existe no payload, o
modelo copia"*). **Rejeitada com motivo medido.** O manifest alinha seções por
**proveniência** (`aligned_with_layout`), e imóvel só existe sob `$.patrimonio` e
`$.investimentos` — a injeção ensinaria o modelo a mandar risco de imóvel para S1/S3
quando o destino de leitura é a S4. Trocaria uma classe de erro por outra. A ADR-399 não é
violada: ela não se aplica a campo cuja resposta correta **não está** no exec context.

## Precedência: tema primeiro, âncora como desempate fechado

A âncora é **proveniência**, e proveniência mente para duas classes com viés de direção
fixa: **imóvel** (não há raiz "imóveis" no que o modelo cita) e **denominador** (o item
fala de cobertura e cita o divisor). Por isso ela só desempata dentro de uma **allowlist de
raízes com sede visual única** — critério objetivo e auditável: a raiz é renderizada por
**um** card. Raiz de armazenamento (`$.investimentos`, `$.patrimonio`, `$.ratios`,
`$.fluxo_caixa`) fica fora.

Duas exceções de prefixo fundo, medidas e não inferidas:
`$.investimentos.total_imoveis_investimento` e `.n_imoveis_total` → **S4**, porque
`InvestimentosClasseCard` — o único que exibia esse número — **não é montado em seção
nenhuma** desde A11, e `AlocacaoAtualVsAlvoCard` (S3) declara imóvel físico **fora** da
base que compara. Mandar à S3 mandaria o leitor a uma seção que diz *"isto não está aqui"*.

## O mapa aponta para card, nunca para seção

`tema → card → seção` e `metrica_key → card → seção`, com `card → seção` derivado do
`report_layout.yaml` a cada chamada. Razão empírica e **já ocorrida**: a [[A40.l34]] moveu
teto/capacidade PGBL da S8 para a `S_IRPF_OTIMIZACAO`. Um mapa direto para `section_id`
teria envelhecido calado naquele PR; assim ele quebra ruidosamente quando o card some, e
segue certo quando o card se muda.

`metrica_key` é discriminador **melhor** que a âncora — ela nomeia a **grandeza**, e
destino de leitura é função da grandeza. Por isso a tabela de métrica não precisa da
exceção de imóvel que a rota por âncora precisa.

## Seção oculta é destino morto

Quatro componentes têm early-return (`S4` ← `real_estate`, `S_IRPF_RENDA`/`S_IRPF_OTIMIZACAO`
← `irpf_kpis`, `S_PROTECAO` ← cobertura contratada). Apontar para seção que aquele relatório
não imprime é **pior** que o estado anterior. O destino degrada para a seção viva mais
próxima (S4→S1, S_IRPF_*→S8, S_PROTECAO→S9). Sem payload para julgar, **não degrada** —
ausência de sinal não é sinal.

## `S_PROTECAO` entra no vocabulário do parecer

O layout declara o eixo: **2.5 = o que está contratado; S9 = o que falta**. Um *risco* é
lacuna por definição e vai à S9 — mas `protecao_custo_premio` é **medida do contratado**, e
mandá-la à S9 publicaria o que EXISTE sob o cabeçalho do que FALTA. Ela entra restrita a
`metrica`/`ponto_forte` e segue fora de `VALID_SECTION_IDS`, o vocabulário das regras
determinísticas — que emitem `SuggestionCallout`, renderer que a S_PROTECAO não tem.

## Consequências

1. O guard de Monte Carlo **deixa de conjungir** `section_id`: âncora MC basta por si.
   Enquanto o campo era do modelo, item ancorado em MC rotulado S1/S3 **escapava do
   rebaixamento, calado**.
2. **`thesis_key` move uma vez** por item cujo destino derivado difira do emitido —
   24 de 33 no corpus medido. O dano é estreito (só linha `Descartada` dentro de 90d) e a
   guarda é `dedup_key` (`ws|ancora|acao`), que **não** contém `section_id`.
3. `Ancora.valor_renderizado` e `.label` também saem do contrato — o comentário dizia
   *"escrito pelo finalize"* e nada o enforçava (follow-up da [[A42.l24]], absorvido).
4. **Nenhum tema roteia para a S4**: ela só se alcança pela allowlist, via imóvel. É
   consequência aceita — a alternativa seria inventar um tema "Imóveis" fora da [[ADR-207]].
5. O `SectionId` era copiado à mão em **4 lugares** e só o JSON tinha gate: a suíte passou
   verde com o `Literal` do Python já divergindo. As quatro passam a ser asseridas por
   igualdade de conjunto.

## Alternativas rejeitadas

- **Mapa keyed só em `tema`** — introduz ≥3 destinos errados (manda imóvel e câmbio para a
  carteira financeira).
- **Dar âncora a `PontoForte`/`Metrica`** — nos itens desses tipos o tema acerta 10 de 10;
  pagaria mudança no schema de saída do LLM por zero acerto medido.
- **Encolher o enum** para o que o manifest projeta — quebra o caminho de **leitura**
  (`planner_review_tier_filter.py` reidrata o artefato armazenado), não a migration.
