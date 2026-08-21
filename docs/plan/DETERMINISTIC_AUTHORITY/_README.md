---
id: PLAN-deterministic-authority
type: plan
title: "Autoridade determinística sobre rótulo de LLM — remediação r6 (baseline, fan-out, dado do casal, render)"
status: draft
created_at: 2026-08-17
last_review: 2026-08-17
sprint_origem: A40
sprint_atual: A40
sprints_envolvidas: [A40, A42]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-343]]"
relates_to:
  - "[[PLAN-pipeline-review-r2]]"
  - "[[PLAN-report-trust]]"
tags:
  - type/plan
  - status/draft
  - area/pipeline
  - area/backend
---

# Autoridade determinística sobre rótulo de LLM — remediação r6

> Origem: skill `pipeline-review` ([[ADR-343]]), run `7b64b6c7` (executor
> `origin/main` f724438f + #1482), registrado em [[PIPELINE-REVIEWS-active]] §r6
> (PR #1489). 23 achados sistêmicos + 1 positivo. Cru + baseline off-git:
> `storage/1b9f2cf5-…/reviews/20260816-1947-7b64b6c7/` (PII).
> Co-design 2026-08-17: 7 lentes (PM · IA · CTO · DE · FP · PE · PD) +
> crítico de completude; 6 conflitos fechados pela regra anti-loop
> (senior-cto arbitra). Este `_README` é a síntese pós-co-design.

## Tese

Onde existe **fato verificável fora do LLM** — código de catálogo RFB, sinal do
valor, seção do documento, CPF, catálogo server-side de limiares — **o fato
decide; a saída do LLM é hint em vocabulário fechado**. O r6 provou o custo da
inversão: 1 rótulo flipado atravessou consolidador, E5, CV, parecer e render sem
que nenhuma camada o segurasse, e o compare cross-run foi o único detector.
As quatro dimensões do pedido mapeiam assim:

| Dimensão | O que fecha | Gate mensurável |
|---|---|---|
| Corretude | Ondas 1+2 (roteamento por fato + balanço de fan-out) | golden 0a red→green **+ prova por mutação** (flipar `categoria` de item negativo ⇒ baldes byte-idênticos) |
| Consistência | invariante entre-agregados (4a, escrito RED na Onda 0) + conservação POR EIXO + strict no baseline | teste 4a verde só pós-Onda 1; drift do schema = 0 por ≥7 dias antes do flip |
| Completude | Onda 3 (dado do casal; zero≠não-medido) + export honesto (REPORT_TRUST) | fixtures red→green: cônjuge nunca publica 0 sem ressalva; doc pulado vira `needs_review` nomeado |
| Precisão | temp 0 + seed em `extract_*` (cauda da Onda 1) + telemetria por tentativa ([[A42.l7]]) | **KR-0** (gate de saída): 2 runs consecutivos do mesmo corpus com compare = **0 FAIL HARD** não-explicado — comparador pinado, `corpus_grew` desligado, **cache de extração OFF** no run de verificação |

## Fronteira

- **[[PLAN-pipeline-review-r2]]** — dono de RV2-* remanescentes; a Onda 5 daqui
  **não reabre** o desenho de RV2-01 (catálogo KPI, §Onda C de lá) — registra a
  dependência e cede o desenho.
- **[[A42]]** — [[A42.l4]], [[A42.l6]] e [[A42.l7]] são donas das superfícies
  `validate_cross`, `SCHEMA_BY_STAGE`/retenção e `llm_call_log`. Este plano
  **não abre PR nelas**; disposição por lane em §Roteamento.
- **[[PLAN-report-trust]]** — casa das lanes de render (7a/7e e o resíduo de
  export de [[A40.l22]]); a tese de lá ("o relatório não pode afirmar precisão
  que os dados não sustentam") é a Onda 7 daqui.
- **[[TRACK-property-identity-cross-era]]** — casa da reconciliação de órfãs
  (4b-ii) e do backfill de supersessão.
- Sprint-casa das lanes MVP: **A40**, pela exceção nomeada do §Critério de
  admissão (cláusula 2) da A42 — precedente [[A40.l58]]/[[A40.l5]] com FK
  `plan:`. Este plano é **caminho crítico do gate de saída da A40** (2 re-runs
  completos consecutivos sem P0/P1 novo): r5 e r6 abriram P0 em runs
  consecutivos, logo o contador não pode iniciar e a A42 não promove — é o
  argumento de cost-of-delay que prioriza este plano sobre as lanes `open` da
  A40.

## Critério de admissão

Entra: achado da §r6 roteado para este plano em §Roteamento. **Não entra, ainda
que P0**: superfície com dono vivo (vai por §Roteamento ao dono); achado novo de
runs futuros (r7+) — entra na re-triagem do registro e **só migra para cá se
algo sair** (cap: nada entra sem sair). Done por **re-execução** (KR-0), nunca
por burn-down de tabela.

## Princípios de execução

1. **Estabilizar antes de gatear.** Gate sobre sistema instável mede ruído e
   ensina a ignorá-lo. Nenhum compare-como-gate antes da Onda 1.
2. **Fato > hint.** Hierarquia de autoridade na classificação de baseline:
   catálogo RFB (grupo do código) > mapa `(secao, codigo)` > **sinal do valor
   como veto/desempate (suficiente, não necessário)** > `categoria_hint`.
   Agregado emitido por LLM **nunca** sobrescreve soma determinística.
3. **Enforcement sob doutrina [[ADR-357]]/[[ADR-358]].** Todo ponto novo de
   enforcement entra WARN-first com **taxa de disparo medida sobre os payloads
   r5+r6 e declarada na ADR** antes do flip; default é **rebaixa/declara**
   (warning tipado + `review_reason` + superfície), nunca reter/abortar;
   kill-switch de 1 env var provado por teste. Estado terminal de unidade não
   processada é `degraded` + `needs_review` — não run vermelho.
4. **Correção antes de custo.** Cache/pin de extração ([[ADR-307]] nos
   call-sites `extract_*`) só depois da Onda 1 — pin antes congela extração
   errada.
5. **Rebaseline consciente.** Commit de rebaseline **isolado dentro do PR do
   fix** (`dev/check_golden_rebaseline_isolation.py`), diff valor-a-valor via
   `dev/golden_diff.py --manifest`, sinal ↑/↓/= declarado, **uma janela de
   rebaseline por onda** e fila serializada compartilhada com as lanes A40 em
   voo (migrations idem — precedente A42.l7×A40.l19).
6. **1 lane = 1 seam = 1 branch**; sub-itens são PRs dentro da lane. Lanes de
   ondas não-MVP nascem `planned`/`blocked` com `depends_on` por wikilink.

## Roteamento achado→dono (disposição escrita antes do primeiro pickup)

| Achado §r6 | Casa | Disposição |
|---|---|---|
| RV6-01, RV6-02, RV6-03 | **este plano · Onda 1** | lanes MVP (L1 seam + L2 guarda E5) |
| RV6-04, RV6-05 | **este plano · Onda 3** | lane MVP (L3 dado do casal) + produtor `gap_qualitativo` |
| RV6-06 | este plano (simetrização `minimum:0` + flip strict dos 2 schemas de baseline) · [[A42.l6]] **cede o eixo dos 2 schemas** e mantém retenção/`SCHEMA_BY_STAGE` (incl. 1-liner RV4-23) | tripartite escrita: plano ↔ l6 ↔ [[A40.l58]] (que mantém `mode_overrides`/kill-switch como infra) |
| RV6-07 | este plano · **critério de aceite da Onda 1** (teste RED na Onda 0) | não é onda própria |
| RV6-08, RV6-09 | este plano · Onda 5 — **bloqueada** pela dependência do catálogo KPI ([[PLAN-pipeline-review-r2]] §Onda C, RV2-01) | fora do MVP; item novo: entrega do catálogo com dono DE+FP |
| RV6-10 | este plano · Onda 2 (lane própria; **paralela desde o dia 0**) | [[A42.l4]] **não amplia** (preserva a disjunção declarada); ganha citação da ADR-B + re-prioridade P1 no frontmatter |
| RV6-11, RV6-18 | **[[A42.l7]]** promovida individualmente (porta nível-lane da A42: reparentar `sprint: A40` + `git mv`), consumidor datado = RV6-18 + [[ADR-173]] sobre piso | #1482 mergeia com claim corrigido ("reduz p50; não elimina timeout") |
| RV6-12 | este plano · Onda 2 (ladder [[ADR-081]] no E1.5) | — |
| RV6-13 | **re-medição na Onda 0** (pós-sweep 2026-08-12 da track; [[ADR-324]] §Emenda revogou premissa) → confirmado o buraco, 4b-i (estanca-sangramento) mergeia imediatamente; 4b-ii via [[TRACK-property-identity-cross-era]] com `dev/backfill_property_supersession.py` **após** re-consolidação limpa pós-Onda 1 | chave de match **sem ano** (`titular_key`+`codigo_rfb`+corroboração de valor; ano é atributo, [[ADR-274]]) |
| RV6-14, RV6-15, RV6-21 | este plano · Onda 3 (fora do MVP, exceto onde indicado) | tripwire re-discriminado por **data-base**, não magnitude |
| RV6-16 | 7a como **lane do [[PLAN-report-trust]] dentro do MVP** (guard de runtime em módulo próprio; coordenação declarada com [[A40.l5]], que é gate estático tsc); supressor do ponto forte alimentado **exclusivamente** pelo warning tipado da Onda 1 (fio único, no produtor `pontos_fortes_analyzer`) | anti-decisão: **não criar 5º banner**; violação **não incrementa** `signals.count` |
| RV6-17 | **[[A40.l6]]** (dona do gate de PII do view-model, critério 4 da [[ADR-337]]) — 7f **estende** o escopo do gate para `patrimonio.composicao[].categoria` + `endividamento.dividas[].descricao`; a chave composta de `por_fonte_detalhado` segue com [[PLAN-pipeline-review-r2]] (RV2-07) | — |
| RV6-19 | este plano · **cauda da Onda 1** (temp/seed é pré-requisito de medir o prompt novo; mesma janela de rebaseline) | "destrava cache" corrigido: temp 0 é pré-condição; `use_cache` é opt-in por call-site (6c) |
| RV6-20 | **re-roteado ao produtor**: `hasRealProtectionInputs` já considera apólices (shipado #1476, [[A40.l35]]) — o 7c do draft era no-op; o defeito real é o `protection_bundle_populator` ignorar a fonte documental `protecao_patrimonial` ([[ADR-240]]). Item produtor-side na Onda 3 · **entregue 2026-08-19** pela [[A40.l73]] ([[ADR-395]]), 5 PRs — o re-roteamento estava certo: o `#1476` era no-op por construção, os 4 sinais do predicado saíam do mesmo bundle | lição: re-medir contra `main` antes de abrir lane de render |
| RV6-22 | resíduo de export da **[[A40.l22]]** via [[PLAN-report-trust]]: contagem server-side no payload **+ 3º estado visível no export + catch → `não apurado`** (as 3 pernas; 2/3 do tri-state já existem — `run_outcome` e `mayAssertCleanQuality`) | — |
| RV6-23 | 7e como lane do [[PLAN-report-trust]] dentro do MVP (enabler puro, sem copy): `visibleCompositionRows()` único decidindo **explicitamente o negativo** (3 casos: negativo/zero-confirmado/ausente) | — |
| RV6-24 | §Baseline e verificação (abaixo) | r6 **não** é baseline |

Backfill da coluna Trilha da §r6 com o wikilink deste plano: mesmo PR desta
abertura (convenção 3 do registro).

## MVP — "o relatório não publica número que o sistema sabe estar errado, e não afirma zero onde não mediu"

Onda 0 (inteira) + Onda 1 (inteira) + Onda 3 itens 3a/3b + lanes 7a/7e no
[[PLAN-report-trust]]. Todo o resto nasce `planned`/`blocked`.

## Ondas

### Onda 0 — instrumento e curadoria (S · antes de qualquer fix)

- **0a. Golden que reprova o r6**: caso novo em
  `tests/test_e15c_golden_execution.py` (substrato `main_with_store` +
  `InMemoryArtifactStore`), marcado `@pytest.mark.xfail(strict=True)` nomeando a
  lane que o desmarca. Fixture sintética PII-free: item com categoria de ativo e
  valor negativo (mesmo código RFB de um imóvel legítimo do fixture) + `resumo`
  contando o montante no passivo. 5 asserts (sinal; destino em `dividas[]` com
  `fonte`/`ano_ref`/`tipo`; conservação **por eixo**; `review_reason` tipado;
  validação strict) + **teste-irmão que prova que a conservação líquida nasce
  VERDE** sobre o mesmo payload (o cancelamento exato é a assinatura do bug).
- **0b. Teste 4a RED** (aceite da Onda 1): `patrimonio.imoveis_investimento ≡
  imoveis_geradores + imoveis_nao_geradores ≡
  goals.alocacao_alvo.derived.imoveis_fisicos_brl`, cents, tolerância zero.
- **0c. Re-medição RV6-13** contra `main` pós-sweep (decide 4b-i vs item da
  track) e **contagem de órfãs atual**.
- **0d. Fila serializada** de migrations e rebaselines (dono por janela),
  coordenada com A40 em voo; **orçamento de verificação**: checkpoints de
  re-run (~25 min/1 run pago cada) com manifesto dos PRs incluídos por
  checkpoint — sem isso, fixes paralelos caem na mesma janela e o efeito não é
  atribuível.
- **0e. Registro**: linha em [[PLANS-active]] §Olhar primeiro; backfill Trilha
  §r6; disposição tripartite RV6-06 escrita.

#### 0a/0b — entregue 2026-08-17 (medido, não estimado)

`tests/test_e15c_golden_execution.py` ganhou **5 casos** `xfail(strict=True)` —
um por assert, não um teste com 5 asserts: com um só, o primeiro a falhar esconde
os outros quatro e a lane perde o sinal de progresso parcial. Os 4 primeiros
nomeiam a [[A40.l66]]; o do schema nomeia a [[A40.l67]].

Números do payload sintético (cents, tolerância zero, ano-ref 2024):

| Medida | Hoje | Declarado no `resumo` | Veredito |
|---|---|---|---|
| Σ ativos | 400.000,00 | 600.000,00 | **RED** (Δ −200k) |
| Σ passivos | 0,00 | 200.000,00 | **RED** (Δ −200k) |
| Líquido (A − P) | 400.000,00 | 400.000,00 | **VERDE** |

O par é o achado: a dívida foi **subtraída do ativo** em vez de somada ao
passivo, os dois somatórios ficam devendo o mesmo montante, e o líquido — sendo a
diferença entre eles — não acusa nada. Daí o teste-irmão
`..._conservacao_liquida_nasce_verde_sobre_o_payload_defeituoso` (controle
permanente) e o
`..._o_cancelamento_exato_e_a_assinatura_do_bug` (datado; a [[A40.l66]] o
**deleta**, não relaxa).

Confirmado de passagem: `validate_dict` do payload contra `baseline_patrimonial`
devolve `True` — não há `minimum` nos baldes de ativo (alvo do 1e). O golden mede
`iter_errors` direto porque o retorno de `validate_dict` depende do modo (warn
devolve `True` mesmo inválido) e um assert mode-dependente seria verde local e
vermelho só no CI.

**0b — 4a** vive em arquivo próprio (`tests/test_e5_invariante_entre_agregados.py`;
em `test_e5_conservation_invariants.py` estouraria o teto de 500 linhas) com
**guard anti-vacuidade**: sobre corpus limpo os três produtores concordam em
600.000,00, e só no payload r6 divergem — `imoveis_investimento` = 450.000,00 e
`imoveis_fisicos_brl` = 600.000,00, porque o `PatrimonioCalculator` **soma** o
negativo e `_aggregate_carteira` o **descarta** (`if valor > 0`,
`alocacao_alvo_deviation.py:186`). Sem o guard, o RED seria indistinguível de
invariante que nunca valeu.

#### 0c — RV6-13 re-medido contra `main`: **o buraco está ABERTO** (2026-08-17)

**Consequência: a lane 4b-i entra** (§Onda 4), nas condições já escritas lá. O
item **não** vira nota pontual na [[TRACK-property-identity-cross-era]] — a track
segue dona só da reconciliação das órfãs (4b-ii).

A linha que decide é `backend/app/services/db_property_identity_resolver.py:44`:
falhada a cascata de match, o `_insert_row` é **incondicional**. Não há ramo que
inspecione `endereco_canonical is None` para abortar, levantar ou marcar
`needs_review`. A prova de que o INSERT é *desenhado* para aceitar canonical
ausente está na linha 68 — `low_confidence=lookup.endereco_canonical is None`: o
campo existe para **carimbar** a ausência, não para recusá-la. No enricher
(`property_identity_enricher.py`), o único early-continue (`:38-42`) é sobre
`titular_key`/`codigo_rfb`; o retorno de `canonicalize` (`:44`) não é checado e o
`None` entra direto no `PropertyLookupKey`, que o tipa como `Optional[str]`.

Verificado por três caminhos independentes, incluindo uma lente adversarial
instruída a refutar (falhou nas quatro frentes: guarda de call-site, caminho
alternativo de INSERT, guarda atrás de flag, guarda que o relatório teria negado):

- **Execução do write-path real** contra SQLite com `PRAGMA foreign_keys=ON`:
  descrição que canonicaliza para `None` ⇒ identidade criada, `endereco_canonical`
  NULL no DB, `low_confidence=1`, **sem exceção e sem `needs_review`**. A row
  sobrevive a `session.rollback()` — o `commit()` da linha 80 é eager.
- **Regrowth medido** — um imóvel, três IRPFs, variação de grafia que qualquer
  re-extração produz (espaço à direita, caixa): **3 identidades**. É o mecanismo
  que repõe as órfãs depois de qualquer sweep.
- **O piso da [[ADR-385]] §Decisão 4 não fecha isto, por desenho.** O 4º nível da
  cascata casa `codigo_rfb` + `descricao_sample` **byte-exata**; a própria ADR o
  chama de "piso para a classe futura, não o fix do passivo". Os testes que o
  cobrem afirmam o INSERT como correto — a classe chama-se
  `TestLowConfidenceInserts`.

Correção factual que ficou pendente na [[ADR-324]] §Emenda: a premissa revogada
estava errada por **dois** motivos, não um. Além de as órfãs agora agruparem pelo
4º nível, o argumento `_identity_key → None` já era falso —
`imoveis_dedup.py:314-322` retorna `("pid", …)` **antes** de olhar canonical, e o
enricher sempre anexa um `property_id` às entries órfãs.

**Não medido nesta onda** (e o veredito não depende disso): a contagem 19 rows /
6 órfãs / 2 criadas na janela do run é do registro §r6 e não foi reconferida
contra o DB de dogfood — exigiria o storage off-git com PII. A contagem importa
para dimensionar 4b-ii, não para decidir 4b-i. Nenhum backfill foi rodado nesta
onda, conforme o escopo.

#### 0d — fila serializada e orçamento de verificação

**Regra da fila.** Uma janela de rebaseline por onda, **um dono por janela**.
Quem detém a janela declara no PR: commit de rebaseline isolado
(`dev/check_golden_rebaseline_isolation.py`), diff valor-a-valor via
`dev/golden_diff.py --manifest` e sinal ↑/↓/= por campo. Migrations seguem a
mesma disciplina (precedente A42.l7 × A40.l19). Quem for pegar uma lane fora
desta fila e precisar rebaselinar **espera a janela fechar** — sem isso, dois
fixes caem no mesmo diff e nenhum dos dois é atribuível.

| # | Janela | Dono | Pode rebaselinar | Abre quando |
|---|---|---|---|---|
| J1 | Seam determinístico | [[A40.l66]] | goldens E1.5c/E5 afetados pelo roteamento; snapshot do view-model | ~~imediatamente~~ · **FECHADA 2026-08-18** (l66 `shipped`, sem rebaseline necessário) |
| J2 | Guarda | [[A40.l67]] | `baseline_patrimonial` + schema irmão | ~~J1 fechada~~ · **FECHADA 2026-08-18 sem consumir rebaseline** (`golden_diff` de `aa53d5bf~1`×`aa53d5bf`: 2 campos `new`, zero `value_delta`, sinal **=**). O flip strict saiu daqui — ver §Deferimentos |
| J3 | Balanço de fan-out | [[A40.l68]] | contrato de retorno do stage (sem golden monetário) | independente — **não** disputa J1/J2 |
| J4 | Cobertura por membro | [[A40.l69]] | baldes de investimento por membro + snapshot do view-model | ~~J2 fechada~~ · **FECHADA 2026-08-19** — 2 rebaselines aditivos (`cobertura_investimentos`, `investimentos_nao_atribuidos`), zero `value_delta` nos dois. Sinal `=` **no golden**, que é inerte para o 3b: a fixture não tem posição órfã. O efeito monetário está provado por unidade e aparece no re-run do dogfood |

**Coordenação com a A40 em voo.** 23 lanes estão `open`/`in_progress`/`blocked`
na sprint, quase todas sob [[PLAN-report-trust]]. As que declaram efeito em valor
publicado — e portanto podem colidir com J1/J2 — confirmam no pickup se o diff
delas toca golden monetário; se tocar, entram na fila atrás da janela vigente. A
[[A40.l58]] é o caso nomeado: ela mantém `mode_overrides` como infra e o flip de
schema desta onda é J2, logo as duas **não** podem estar abertas na mesma janela.

**Orçamento de verificação.** Cada checkpoint é 1 run completo do corpus, ~25 min,
**com extração paga** (o cache fica OFF: com hit, o compare mede o cache e não o
pipeline). Manifesto de PRs por checkpoint é obrigatório — sem ele o delta não é
atribuível a nenhum fix.

| Checkpoint | Quando | Runs pagos | Manifesto |
|---|---|---|---|
| CP-0 | já existe | 0 | baseline **por dimensão**: r4 (`82b30303`) para composição, r5 (`0a040a22`) para o resto. **r6 não entra** |
| CP-1 | J1 fechada | 1 | PRs da [[A40.l66]] |
| CP-2 | J2 fechada | 1 | PRs da [[A40.l67]] (+ [[A40.l68]] se já mergeada) |
| CP-3 | gate de saída | 2 | KR-0 exige **2 runs consecutivos** do mesmo corpus, comparador pinado, `corpus_grew` desligado |

Total do MVP: **4 runs pagos**. O custo em US$ por run não está medido — a
telemetria por tentativa é da [[A42.l7]]; o CP-1 é a primeira oportunidade de
registrá-lo, e quem o rodar anota o número aqui.

#### 0e — registro: as três pernas escritas (2026-08-17)

Item 0e cumprido nas suas três pernas, cada uma verificável onde vive:

| Perna | Onde | Evidência |
|---|---|---|
| linha em [[PLANS-active]] §Olhar primeiro | `docs/_MOC/PLANS-active.md` | linha da tabela §Olhar primeiro |
| backfill da Trilha §r6 | [[PIPELINE-REVIEWS-active]] §r6 | todo RV6-* carrega `plano: [[PLAN-deterministic-authority]]` na coluna Trilha |
| disposição tripartite RV6-06 | plano ↔ [[A42.l6]] ↔ [[A40.l58]] | §Roteamento aqui + §Coordenação declarada nas duas lanes |

Antes disto a disposição estava escrita **só deste lado** — as outras duas lanes
não sabiam que tinham cedido ou recebido superfície, que é como duas sessões
abrem PR no mesmo eixo.

**Com isto a Onda 0 está inteira** (0a/0b golden + 4a RED · 0c re-medição RV6-13 ·
0d fila e orçamento · 0e registro), que é a metade do gate do MVP declarado em
§MVP. A [[A40.l66]] (J1) está `open` e ocupada; a [[A40.l67]] segue `blocked` por
ela, por desenho.

**Tensão encontrada ao escrever — e o contraditor que a primeira escrita errou:**
o §Escopo da [[A40.l58]] trata do flip **global** de `schema_validation.mode`,
enquanto §Anti-decisões deste plano diz *"NÃO subir `schema_validation.mode`
global — só per-schema com janela medida"*. A primeira redação enquadrou isto
como *plano × lane* e ofereceu "emendar o plano" como saída. **Está errado:** quem
decidiu o eixo é a [[ADR-284]] (`Decidido`, 2026-06-09) e o runbook
[`schema_validation_strict_flip.md`](../../reference/runbooks/schema_validation_strict_flip.md)
(*"nunca global de uma vez"*); o §Anti-decisões daqui só **repete** essa doutrina.
Os encaminhamentos, com a barra corrigida, estão na própria l58 — superar o
global exige supersedure/emenda da ADR-284, não emenda deste plano. A escolha é
do `sre-devops`, dono de lá. Enquanto não houver decisão, vale a regra da fila:
l58 e [[A40.l67]] não abrem na mesma janela (J2 é da l67).

#### Lanes do MVP abertas (2026-08-17)

[[A40.l66]] (`open`, P0, seam — itens 1a/1b/1c), [[A40.l67]] (`blocked` por l66,
P0, guarda E5 — itens 1d/1e) e [[A40.l68]] (`planned`, P1, balanço de fan-out —
Onda 2, paralela desde o dia 0). Ids a partir de `l66` porque a `A40.l65` já
existe em PR aberto (#1491) — `SPRINT_CURRENT` não vê lane que só existe em
branch. Só a l66 nasce `open`: `dev/check_lane_status_predicate.py` reprova
`open` com dependência pendente, e a l67 depende dela.

**2026-08-17 (2º ciclo)** — [[A40.l69]] (`blocked` por l66+l67, P0, cobertura de
investimentos por membro — itens 3a/3b, RV6-04). Fecha o último P0 do MVP que não
é do seam. Nasce `blocked` por dois motivos independentes: a regra unificadora
que o 3a consome é decidida na ADR-A (aberta pela l66), e a lane precisa de
janela de rebaseline (J4, atrás da J2). **Não abre ADR nova** — 3a está na
cobertura declarada da ADR-A e 3b é a [[ADR-267]], já `Decidido`.

Medido ao escrever a lane (contra `main` @ `0bb4ba55`), e é o que a torna P0: o
caminho de investimentos **nunca chama** `resolve_by_cpf` — o único call-site de
produção é `consolidate_baseline.py:410` (E1.5c) — e o artefato de posições não
tem onde carregar CPF (`e2_llm_artifact.schema.json:32` declara `membro`, não
`cpf`). No miss do resolver, `investments_consolidator.py:324` **preserva o slug
bruto**, e `patrimonio_calculator.py:315-327` soma ao **titular** tudo que não
casa por substring. O zero do cônjuge não é um valor medido: é um valor que foi
para a outra pessoa. A varredura por substring em chave de membro tem **31
call-sites** em 4 arquivos — o analyzer do RV6-14 é um deles, não o conjunto.

### Onda 1 — seam determinístico (P0 · MVP · 2 lanes)

**L1 (seam extração/consolidação) — ✅ `shipped` 2026-08-18 ([[A40.l66]], 5 PRs):**
- 1a. Predicado de dívida deixa de conjuncionar com o rótulo: função pura
  `classify_baseline_item(codigo, valor_cents, categoria_hint, catalogo)` em
  `pipeline/domain/services/` (VO de config tipado, warnings [[ADR-097]] D1).
  **Autoridade primária: catálogo RFB** *(⚠️ ENTREGUE com outra ordem —
  [[ADR-394]] D1/D2 põe `secao` em primeiro e deixa o catálogo só para o
  subtipo, por `(ano_base, secao, codigo)`; `codigo` sozinho mediu 0%)* —
  estender o substrato existente
  (`pipeline/llm/rfb_codes.py`, YAML versionado por ano-base com fail-fast e
  runbook anual) com os grupos de bens/direitos e dívidas/ônus. Sinal negativo
  = **veto suficiente** (nunca necessário — o IRPF declara saldo devedor
  positivo na seção de dívidas). Divergência fato×hint → warning tipado +
  `review_reason`, nunca silêncio. Ramo de dívida passa a carimbar
  `fonte`/`ano_referencia`/`tipo` (hoje só o ramo de imóvel carimba).
- 1b. Contrato E1.5a: `categoria` → **`categoria_hint`** (opcional, string
  livre, usado só no warning); campo derivado server-side fechado em enum;
  `secao` entra **OPTIONAL na etapa 1** (prompt emite + taxa de emissão
  medida), `required` só com cobertura 100% comprovada — nunca no PR que o
  introduz (re-validação de histórico dispara re-extração, [[ADR-261]] Tier 3).
  Bump `e15_baseline` 1.2.0→1.3.0 cobrindo o schema irmão. Conservação por
  seção **dentro do E1.5a** (`Σ itens ≡ total_liabilities/assets`, por ano).
  Boundary tolerante: enum desconhecido → `needs_review` no item, resto do
  documento extraído (anti reask-storm, precedente [[ADR-292]]).
- 1c. Conservação intra-artefato no E1.5c, **por eixo e por ano** (cents int,
  tolerância zero): generalizar o ramo `pj_skipped>0` que **já desliga** o
  override do `resumo` (o fix é majoritariamente deleção — **mas 1a vem antes:
  medido em §Ataque da [[A40.l66]], `total_passivos ≡ Σ|negativos|` em 7/7, logo
  hoje o override mascara o defeito nos totais e deletá-lo primeiro piora r6**);
  determinístico
  ganha; divergência → `review_reason` + stage `degraded` ([[ADR-357]]), nunca
  raise que mata o relatório. Contrato de `review_reasons` no artefato E1.5c
  (hoje só `extract_baseline` projeta).
- Cauda da L1, mesma janela de rebaseline: `temperature=0.0` + seed explícito
  nos call-sites `extract_*` (kwarg, sem bump) + gate que falha em call-site
  novo sem o kwarg. Claim honesto: reduz variância; **não** torna extração
  idempotente.

**L2 (guarda de publicação E5) — 1d ✅ `shipped` 2026-08-18 (#1534); 1e parcial: schema entregue (#1529), flip strict é critério temporal:**
- 1d. Nenhum dos 7 baldes [[ADR-145]] < 0 — com **rota de reclassificação
  antes da guarda**: negativo legítimo (cheque especial, conta margem)
  reclassifica determinístico para dívida de curto prazo e **publica**; só o
  negativo que sobrevive vira warning tipado + `needs_review`. Regra
  unificadora (na ADR-A): **prescrição exige cobertura; descrição admite
  ressalva** — cobertura incompleta ⇒ `next_aporte_classe=None` +
  `desvio_max_pct=None` + `motivo_supressao` (~~campos já `Optional`~~ —
  **`motivo_supressao` não existia**; nasceu no #1534, e `AlocacaoDerived` tem
  `additionalProperties: false`, logo declará-lo no schema não era opcional),
  sem suprimir o resto do relatório. *Entregue com um balde a mais que o
  escrito:* o par derivado `imoveis_geradores`/`imoveis_nao_geradores` entrou
  porque é o **único** negativo publicado do corpus (r6, −125.381,88) e não é um
  dos 7 baldes [[ADR-145]] — a guarda literal passaria verde sobre o run que a
  motivou.
- 1e. Simetrização do contrato: `patternProperties` `^(31_12_)?\d{4}$` com
  `minimum:0` nos 3 baldes de ativo do `baseline_patrimonial.schema.json`
  (**sem** fechar `additionalProperties` — os resolvers leem 3 formas de
  chave); flip `mode_overrides` para strict dos 2 schemas de baseline é o
  **último passo da Onda 1**, com gate medido: drift = 0 por ≥7 dias de
  dogfood, número citado no PR do flip.

**Saída da Onda 1 (gate de conclusão):** re-run do corpus + **republicação do
relatório do dogfood com o delta declarado ao dono** (G2 do
[[PLAN-report-trust]]) — score, dívidas e "ponto forte" corrigidos no artefato
que o leitor guarda; e **cura do estado durável** (artefatos do run corrompido
+ decisão sobre as rows de identidade mintadas, com 0c).

### Onda 2 — balanço de fan-out (P1 · paralela desde o dia 0)

- 2a. Invariante `queued ≡ processed + errors + skipped(motivo)` no
  `extract_with_llm`, com **resultado tipado na extração de texto**
  (`texto | falha_de_leitor(motivo)` — o `.xls` medido é "leitor ausente", não
  "texto vazio": `text_extractor.py` lava a exceção do leitor). Skip →
  `review_reason` nomeando o documento; `success` exige balanço fechado;
  formato sem extrator falha no E0. Mora no contrato de retorno do stage
  (stage log/`validation`), **não** em JSON Schema (com `processed=0` não há
  payload para o hook pós-write validar). Denominador **enumerado** (lista
  declarada de stages fan-out) — prova por mutação: remover o leitor de um
  formato ⇒ motivo "leitor ausente" + doc em `needs_review` + balanço fecha.
- 2b. Ladder [[ADR-081]] no E1.5: `confidence < 0,7` → `review_reason` +
  `degraded` — WARN-first com budget medido (§Enforcement).

### Onda 3 — dado do casal + tripwires (3a/3b ✅ `shipped` 2026-08-19 pela [[A40.l69]], 5 PRs; resto planned)

3a e 3b vivem na [[A40.l69]] (`blocked` por l66+l67) — são o mesmo seam: a
atribuição de investimento por membro. 3c–3f seguem sem lane.

- 3a. Eleição de `fonte_investimentos` **por membro** com predicado de
  cobertura; **campo próprio `cobertura_investimentos[]`**
  (status/fonte/frescor/motivo — **não** sobrecarregar `pl_ressalva`,
  [[ADR-346]]); **3 estados**: `apurado` · `zero_apurado` (zero com fonte — é
  o caminho de saída da ressalva) · `nao_apurado` (null + ressalva +
  `needs_review`, **nunca 0,0**); prescrição suprimida enquanto `nao_apurado`
  (regra unificadora da ADR-A). Fallback para baseline IRPF é a fase 2 (pós
  Onda 1, para não herdar roteamento sujo).
- 3b. Identidade de membro por **CPF** antes de qualquer agrupamento
  ([[ADR-267]]; slug de LLM nunca é chave) + **varredura de matching por
  substring** além do analyzer (ex.: `patrimonio_resolvers` casa
  `conjuge_key in kl`) + gate proibindo match por substring em chave de membro.
- 3c. ✅ **Entregue em 2026-08-19** pela [[A40.l73]] ([[ADR-395]] `Decidido`),
  fora do MVP declarado por autorização do dono. Produtor `gap_qualitativo`
  reconciliado com `irpf_kpis.dependentes` (determinístico, #1576); **e** o
  produtor do `protection_bundle` consumindo a fonte documental
  `protecao_patrimonial` ([[ADR-240]]) — o vazio da S9 era do produtor, não do
  render (re-roteamento do 7c confirmado). PRs: #1549 (lane + ADR) · #1554
  (canal `categorias_somente_no_documento`) · #1560 (retenção no populator +
  `actual` nulo deixa de virar `0,00`) · #1564 (S9 de vazio para **parcial**)
  · #1576 (metade (i) + `pontos_urgentes` lendo o mesmo estado).
  A regra decidida: extração é **hint**, o número tem produtor único
  (cadastro), as fontes nunca somam, e documento vigente em categoria sem
  cadastro ativo é contraprova de inventário — `missing_data`, nunca gap sobre
  zero. Residual PE (regra de precedência entre fontes contraditórias no
  prompt) segue **item próprio da Onda 5**, sequenciado depois deste e **não
  tocado** aqui.
- 3d. Cenário do cônjuge: gate [[ADR-167]] e extrator lendo a **mesma fonte
  por papel**; `fator_reduzido` derivado (`1 − renda_conjuge/renda_familiar`,
  com piso); inelegível → **omitir o bloco** e a concentração de renda em
  fonte única aparece como linha de risco (omissão não pode ler como "sem
  risco").
- 3e. Tripwire fluxo×estoque re-discriminado por **coerência de data-base**
  (estoque sem `ano_ref`/data-base, ou data-base fora da janela do fluxo ⇒
  `needs_review` interno), **não** por magnitude ×12 — a razão ~2× do r6 é
  indistinguível de financiamento saudável em fase final. Canal de DADO
  (needs_review, operador) separado do canal de DOMÍNIO (alerta ao usuário).
  Cláusula run-a-run vive no substrato de snapshot changelog
  ([[ADR-148]]/[[ADR-190]]), não no E5 (E5 permanece função pura do corpus).
- 3f. Reserva: histerese com **assimetria protetiva invertida** — promove ao
  alvo maior na 1ª observação acima do limiar (com ressalva), rebaixa só após
  2 ciclos abaixo da banda; perfil `indefinido_por_cobertura` quando a fatia
  de renda não classificada ≥15-20% (mantém alvo vigente + ressalva, nunca
  flipa); "ciclo anterior" = snapshot **publicado**. Dependência declarada:
  estender o substrato de changelog para entrada **categórica**
  (perfil X→Y com causa nomeada) — hoje `ChangelogEntry` só suporta delta
  numérico e não cobre `meses_alvo`/`perfil_renda`.

### Onda 4 — identidade durável (gated por 0c)

- 4a. — absorvido como aceite da Onda 1 (ver 0b).
- 4b-i. `endereco_canonical=None` **não cria identidade** — condicional
  **resolvida em 0c (2026-08-17): o buraco está aberto em `main`**, logo o item
  entra. Match `(titular_key, codigo_rfb)` + corroboração de valor (**ano é
  atributo**, nunca chave); sem match → `needs_review`. Mergeia imediatamente
  (dano durável é contínuo), sem esperar 1b. O ponto exato a fechar é o
  `_insert_row` incondicional em `db_property_identity_resolver.py:44`; o fake
  `InMemoryPropertyIdentityResolver` precisa da mesma regra (o 4º nível da
  [[ADR-385]] nunca foi portado para ele). Lane: [[A40.l70]].
- 4b-ii. Reconciliação das órfãs via [[TRACK-property-identity-cross-era]]
  (`dev/backfill_property_supersession.py`, idempotente, dry-run com diff
  revisado), **só após** re-consolidação limpa pós-Onda 1 — para não eleger
  como âncora um pid nascido do run corrompido.

### Onda 5 — parecer (bloqueada pelo catálogo KPI · fora do MVP)

Ordem interna: (5-zero) estender o report do eval + fixture holdout com a
patologia r6 (balde negativo/endividamento colapsado) — instrumento antes de
mexer; E1.5a ganha eval próprio junto de 1b (hoje só fixture estática. (5c-tel)
publicar **duas razões** server-side sem gate — cobertura
(`1 − sem_ancora/total`) e correção (`verified/(verified+failed)`) — flip para
enforcement só com ≥20 gerações de produção medidas e ADR própria. (5a)
catálogo de targets: **fonte única** dos limiares metodológicos
(`config/scoring.json`; valores do FP, mecanismo do PE); modelo emite
`target_id`; `narrative_hints` do manifesto citam `target_id` em vez de repetir
número em prosa; `ancoras[]` no schema de `metricas[]`; conjunto canônico por
tier; bump parecer 2.2.0→2.3.0. (5b) gate pré-LLM **consome o warning tipado
de 1d** (sem |Δ|-vs-run-anterior — estado cross-run no caminho do parecer
contraria o princípio 1); resposta = confiança rebaixada + nota metodológica,
sem bloquear geração. (5d-resto) `use_cache` opt-in nos call-sites `extract_*`
(a chave do `response_cache` já hasheia o prompt — é o content-hash do antigo
"6c"); regra dura: mudança de shape em `pipeline/llm/schemas/*` bumpa o
PROMPT_VERSION irmão. **Um** run de eval após 5a+5b+5c atrás de um único
`prompt_version` (~US$29, cap vigente; 1 bump de manifesto por onda — cada
bump invalida o cache Redis e re-paga geração por workspace). Cada item
declara o **delta de custo/token** que introduz.

### Onda 7 — render (lanes no [[PLAN-report-trust]]; 7a/7e no MVP)

**Lanes abertas 2026-08-17 (2º ciclo):** 7e é a [[A40.l71]] (`open` — não depende
do seam) e 7a é a [[A40.l72]] (`blocked` por [[A40.l66]]). As duas nascem com
`plan: PLAN-report-trust` e entram na §Ondas de lá; a FK aponta para a casa que
as executa, não para este plano que as origina.

O `blocked` da 7a tem causa mecânica, não de sequenciamento: o supressor do ponto
forte é **fio único** a partir do warning tipado da Onda 1. Sem o warning, a única
forma de suprimir "Endividamento Mínimo" seria re-derivar o defeito no render —
uma segunda fonte de verdade sobre o mesmo fato, que é a classe que este plano
fecha.

Re-medido contra `main` antes de abrir (lição do RV6-20, que morreu de ser
no-op): as duas superfícies **estão como o r6 as descreveu**. O
`reportContractGuards.ts` que já existe é módulo de **leitura** (`readScoreData`,
`readRealEstateData`…), não avalia invariante e não tem onde reportar violação —
o guard da 7a é módulo próprio. E os dois predicados da composição seguem
divergentes: `PatrimonioDoughnutChart.tsx:23-25` filtra `valor > 0` (some com
zero **e** negativo) enquanto `PatrimonioCategoriasCard.tsx:21-23` só esconde
`"Residência"` zero — casando pela **string renderizada**, o que desliga a
exceção da [[ADR-215]] P5 em silêncio se a copy mudar.

Sequência por dependência: (0) decisão de copy dos 3 estados do banner +
decisão sobre o **estoque publicado** (define a copy do 7a); (1) PR backend
`needs_review` count no payload + snapshot OpenAPI; (2) 7e (enabler sem copy);
(3) 7a+7d-frontend **juntos** (mesmo trio
`ReportDataQualityBanner`/`dataQualitySignals`/CleanBar — um rebaseline visual,
uma rodada print+a11y); (4) 7f via [[A40.l6]]. Transversal obrigatório da onda:
gate declarado por PR (`frontend-print-visual` é label-gated — rodar
explicitamente), PNG inspecionado no runner Linux antes de commitar baseline,
contraste dos estados novos nos 2 temas (par `-on-tint`; `NAMED_PAIRS` quando o
gate não alcança), estados novos adicionados aos specs de a11y por seção.
Aceites-chave: violação de contrato renderiza estado `error` **sem**
incrementar `signals.count` e **sem** `data-testid="data-quality-clean"`;
export com contagem indisponível mostra "não apurado", nunca CleanBar.

## §Enforcement (doutrina [[ADR-358]] G1 — item a item antes de qualquer flip)

| Ponto | Default | Budget medido (r5+r6) antes do flip | Kill-switch |
|---|---|---|---|
| 1c conservação E1.5c | degraded + review_reason | obrigatório | env var |
| 1d guarda de sinal E5 | reclassifica → publica; sobrevivente → needs_review | obrigatório | env var |
| 1e strict baseline | warn ≥7 dias, drift=0 medido | obrigatório | `mode_overrides` |
| 2a balanço fan-out | skipped(motivo) + needs_review; success=false só com balanço aberto | obrigatório | env var |
| 2b ladder E1.5 | degraded, nunca abort | obrigatório | env var |
| 5c verified_ratio | telemetria (2 razões); flip só pós-produção | ≥20 gerações | ADR própria |
| 5b sanidade pré-LLM | rebaixa confiança + nota | obrigatório | env var |

## ADRs a abrir (forma [[ADR-345]] — ID alocado na escrita, nunca em prosa)

- **ADR-A = [[ADR-394]]** (`Proposto`, 2026-08-18) — "Fato determinístico é
  autoridade; saída de LLM é hint em vocabulário fechado." Hierarquia catálogo RFB > (secao, codigo) > sinal
  (veto suficiente) > hint; agregado LLM nunca sobrescreve soma determinística;
  regra "prescrição exige cobertura, descrição admite ressalva"; local canônico
  dos invariantes (domain service puro; adapter converte; store não conhece
  semântica). Cobre 1a/1b/1c/1d/3a.
- **ADR-B = [[ADR-393]]** (`Proposto`, 2026-08-18) — "Contrato de balanço de
  stage fan-out." `queued ≡ processed +
  errors + skipped(motivo)`, 3 estados + piso por identificador declarado,
  resultado tipado do leitor. **Nenhuma emenda à [[ADR-342]]** (escopo distinto;
  decisão CTO no co-design). Cobre 2a; [[A42.l4]] a cita sem mudar de escopo.

## Baseline e verificação

- **r6 (`7b64b6c7`) está CORROMPIDO — não usar como baseline de compare** (esta
  linha é a marcação git-durável; o dir off-git tem a cópia).
- Baseline **por dimensão**: baldes de patrimônio/dívida → r4 (`82b30303`,
  último pré-zero do cônjuge é r4 para composição; r5 também carrega os 4 FAIL
  do cônjuge desde r4 — campo a campo declarado no compare); demais dimensões →
  r5 (`0a040a22`).
- **KR-0 (gate de saída do plano = gate da A40, deliberadamente o mesmo
  predicado):** 2 runs consecutivos do mesmo corpus, compare com **0 FAIL HARD
  não-explicado**, comparador pinado, `corpus_grew` desligado, cache de
  extração **OFF** no run de verificação (senão o hit mede o cache, não o
  pipeline). Prova por mutação é gate de **task** (aceite de 1a/1c), não KR.

## Anti-decisões

- NÃO subir `schema_validation.mode` global — só per-schema com janela medida.
- NÃO compare-como-gate de pipeline antes da Onda 1 (detector ≠ preventor).
- NÃO pin/cache de extração antes da Onda 1.
- NÃO "consertar" RV6-05 no prompt do parecer (treinaria a não citar payload).
- NÃO interpolar o degrau da reserva (histerese com assimetria protetiva).
- NÃO corrigir só o prompt E1.5a sem 1a (a classe volta no próximo flip).
- NÃO criar 5º banner no relatório (reusar `ReportDataQualityBanner` com
  estado de severidade novo; enumeração da [[A40.l22]]).
- NÃO ampliar [[A42.l4]] nem emendar [[ADR-342]].
- NÃO fechar `additionalProperties` nos `valores_31_12` (3 formas de chave
  vivas nos resolvers).

## Critério de done

KR-0 verde + MVP mergeado + republicação do relatório dogfood com delta
declarado + disposições de §Roteamento executadas (l7 promovida; l4 re-priorizada;
l6/l58 com disposição tripartite; 7a/7e/7d no REPORT_TRUST; 4b-ii na track).
Achado novo de r7+ **não** reabre este plano (vai à re-triagem do registro).
`last_review` datado a cada revisão; ao fechar, arquivar em
`docs/archive/DETERMINISTIC_AUTHORITY-<data>.md` + entrada no README do archive.

## Deferimentos datados

- **2026-08-21 · Kill-switch da cobertura por membro restaura só metade.**
  Re-roteado da [[A40.l69]], que fechou `shipped` hospedando-o. `valor_publicavel`
  (`investimentos_cobertura.py`) **não** consulta `cobertura_enforcement_ligado()`
  — só `motivo_supressao_por_cobertura` consulta. Com `MATHOMS_E5_COBERTURA_MEMBRO=0`
  o balde continua `null` e **some a razão que o explica**: o freio deixa o produto
  pior que ligado ou desligado. Não é escopo novo — o §Enforcement da l69 prometeu
  "kill-switch de 1 env var, provado por teste", e o docstring de
  `cobertura_enforcement_ligado` **afirma** *"`0` desliga a ressalva e a supressão,
  não o campo"*, contrato que o código não cumpre. A [[ADR-394]] §Emenda 2026-08-18
  já decidiu a regra: *"kill-switch que não restaura o comportamento anterior não é
  kill-switch"*. Condição de retomada: **o próximo PR que tocar
  `investimentos_cobertura.py`** — não "no primeiro incidente", porque kill-switch
  meio-funcional é o que se descobre durante o incidente.
- **2026-08-21 · Colapso cross-ano no consolidador, gateado por re-medição.**
  Re-roteado da [[A40.l69]]. Entre dois runs de 2026-08-12 com input idêntico, os
  itens do cônjuge foram de 26 para 9, e o survivor ficou keyed no ano **velho** —
  viola o contrato da [[ADR-274]] (chave em ano-base 31/12, não exercício).
  **O número é de 2026-08-12 e decide a prioridade: re-meça `Σ valor` antes e
  depois do colapso antes de registrar escopo.** Se os 17 itens carregam valor, é
  P0 e vira lane própria; se são duplicatas colapsadas com chave errada, é P2 de
  rotulagem. Prioridade sem esse número é opinião. Condição de retomada: a
  re-medição, ou o próximo PR que toque `consolidate_baseline`.
- **2026-08-21 · Trava anti-dupla-contagem do cônjuge dependente + válvula
  declarada para domicílio sem investimentos.** Re-homeados da [[ADR-394]]
  §Emenda 2026-08-19 (c), que os declarava com `dono: [[A40.l69]]` — lane que
  fechou `shipped`. O texto e as condições de retomada permanecem lá; esta entrada
  é a rota viva. Resumo: a trava exige `dependentes`/`declarante` no artefato do
  E1.5c, que hoje **não os carrega** (medido) — é mudança de contrato do produtor;
  a válvula exige um workspace real com membro genuinamente sem investimentos.
- **2026-08-21 · `enrich_alocacao_with_deviation` recebe o patrimônio como kwarg
  com default.** Re-roteado da [[A40.l67]], que o hospedava com dono
  `senior-cto` — papel de revisor, não rota de trabalho. Call-site que omitir
  `patrimonio=` publica a prescrição sobre cobertura possivelmente incompleta e
  **passa verde**. Re-medido em `5f73b116` (a função mudou de arquivo desde o
  achado): `alocacao_derived_enricher.py:15-21`, default persiste, 3 call-sites
  de teste omitem. Nenhum call-site de produção exposto — o risco é o próximo.
  Condição de retomada: call-site novo do enricher, ou a lane de render 7a/7e ao
  consumir `motivo_supressao`.
- **2026-08-18 · Flip de `mode_overrides` para strict re-homeado da [[A40.l67]]
  para a [[A40.l58]].** Ele estava na §Critério de aceite da l67 e era
  **inexequível ali**: o §Roteamento RV6-06 acima já atribui `mode_overrides` e o
  kill-switch à l58, e a §Coordenação da l67 declara que ela não abre PR naquela
  superfície. Critério inexequível não adia entrega — esconde, e este travava a
  [[A40.l69]] (último P0 do MVP) por uma dependência que o trabalho real já
  satisfez. Escopo: `strict` nos 2 schemas de baseline via `mode_overrides`,
  nunca global (§Anti-decisões). Condição de retomada: **drift = 0 por ≥7 dias de
  dogfood, número citado no PR do flip** — temporal por construção. A
  simetrização que o torna executável shipou em #1529.
- **2026-08-17 · E1.5a × E1.6 extraem o mesmo IRPF com contratos diferentes**
  (E1.6 já separa `bens_direitos`/`dividas` por seção — a duplicação estrutural
  é a causa remota de 1b). Dono: senior-cto. Condição de retomada: Onda 1
  mergeada + medição de custo de unificação dos extratores. **Revisar a condição:**
  §Ataque da [[A40.l66]] mediu `E1.6.dividas_onus` = 6 em **7/7** runs contra o
  rótulo do E1.5a flipando em 5/7 — a seção que 1a precisa já existe, estável, uma
  etapa depois no `FULL_ORDER`; o deferimento pode estar no caminho crítico da
  Onda 1, não atrás dela.
- **2026-08-17 · Split do registro** `PIPELINE-REVIEWS-active` (~72KB; sem gate
  de tamanho para MOC editorial). Dono: information-architect. Condição:
  próximo run (r7) antes de abrir a seção.
- **2026-08-17 · Frontmatter stale do [[PLAN-pipeline-review-r2]]**
  (`sprint_atual: A39`). Dono: PM na próxima curadoria de PLANS-active.
