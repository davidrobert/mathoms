---
id: A40.l65
type: lane
title: "A base do PGBL perdeu a âncora de declarante: lê o IRPF mais recente, e o teto de 12% é por CPF"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l65-base-pgbl-sem-ancora-de-declarante
owner: data-engineer
adrs:
  - "[[ADR-236]]"
  - "[[ADR-305]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l65 — `base-pgbl-sem-ancora-de-declarante`

> Aberta em 2026-08-17 no co-design da [[A40.l36]] (`financial-planner`). **A
> l36 é o que torna isto load-bearing** — antes dela o pró-labore ancorava o
> titular; depois, nada ancora.

> ## ⚠️ Ataque medido — 2026-08-24: **o §Critério 3 não é implementável hoje**
>
> Medido contra `main` (`7ed61f04`). Nada implementado — só medição. A lane segue
> `open` e **LIVRE** no `lane_pickup`.
>
> ### O que a lane acerta, verificado
>
> - `_load_irpf_renda_tributavel` → `_read_latest_workspace_artifact`, que ordena
>   por `created_at.desc(), id.desc()` e faz `.first()`
>   ([`tributario_input_builder.py:336`](../../../../backend/app/services/tributario_input_builder.py)).
>   Sem ano, sem dedup, sem declarante. ✅
> - `resolve_ano_base_fiscal` existe e é consumido — mas **só do lado pipeline**:
>   `analyze_finances`, `irpf_analyzer`, `e5_analyzer_adapter`, `protecao_wiring`.
>   `tributario_input_builder` **não está na lista**. Os dois resolvedores são reais. ✅
> - `e16_irpf_full`: `contribuinte` é `$ref` para `$defs/contribuinte`, cujo
>   `required` é `["cpf_masked", "nome", "ano_base", "exercicio", "modelo", "natureza"]`. ✅
>   (Lido no `$ref` não-resolvido o campo *parece* ausente — não é.)
> - `_is_shell_decl` exige **todos** os blocos vazios, então declaração com
>   `pagamentos_efetuados == []` sai `completo`. A anotação de 2026-08-21 no
>   §Fora de escopo continua válida. ✅
>
> ### 1 · O lado S8 não tem ano-base para citar — o critério compara duas ausências
>
> `RendaTributavelPF` publica `total`, `rendimentos_pj_total`, `rendimentos_pf_total`,
> `fontes_pj`, `fontes_pf` — **não existe campo de ano**
> ([`irpf_renda_tributavel.py:19`](../../../../pipeline/domain/services/tributario/irpf_renda_tributavel.py)).
> O bloco `tributario` do `e5_analysis.schema.json` é literalmente `{}` — schema
> vazio, logo nada declara nem valida um ano ali. E no snapshot de dogfood
> (`backend/tests/snapshots/dogfood_view_model.json`) a chave `tributario`
> **não existe**, enquanto `previdencia_pgbl.ano_base` é `null`.
>
> ⇒ Um teste escrito hoje ao §Critério de aceite 3 (*"S8 e Card B citam o mesmo
> ano-base"*) compara `None` com `None` e **passa a vazio**. O campo tem de nascer
> antes do gate. É a classe da [[A40.l77]]: duas superfícies que não publicam os
> mesmos campos não são comparáveis por construção.
>
> ### 2 · Armadilha do homônimo: existe um `ano_base_coberto` no caminho da cascata
>
> `CascataInput` carrega `FinanceiroPJSnapshot.ano_base_coberto`
> ([`cascata_calculator.py:100`](../../../../pipeline/domain/services/tributario/cascata_calculator.py)),
> alimentado em [`tributario_input_builder.py:138`](../../../../backend/app/services/tributario_input_builder.py)
> por `max(s.ano_base for s in summaries)` sobre **informes PJ** — outro corpus,
> outro produtor. Quem implementar o §Critério 3 vai achar um campo com o nome
> exato da resposta e comparar o ano do **informe PJ** contra o ano do IRPF. Fica
> verde e não mede nada.
>
> ### 3 · `resolve_ano_base_fiscal` elege ANO, não artefato — o §Escopo 1 subespecifica
>
> A assinatura é `dict[int, tuple[CompletudeAno, str | None]] → AnoBaseFiscal`: ela
> **elege um ano**, não seleciona uma row. Passar por ela não responde *qual das N
> rows daquele ano* a S8 lê — e o E1.6 produz várias por documento. A medição de
> 2026-08-21 sobre o dogfood (285 versões de 4 documentos, decifradas)
> registrou `rendimentos_pf` oscilando entre **0 e 1 itens** no mesmo documento —
> exatamente uma das duas listas que `extract_renda_tributavel_pf` soma. Logo o
> "dedup" do §Escopo 1 tem de decidir **qual versão**, não só qual ano e qual CPF;
> sem isso a base continua variando entre runs com um único declarante.
>
> ### 4 · §Escopo 1 e §Escopo 2 podem se anular — e o §Critério 2 mente sobre a causa
>
> `pick_default_year` elege **um** ano sobre o corpus inteiro, e
> `anos_base_disponiveis` é a união de `contribuinte.ano_base` de **todos** os
> declarantes ([`irpf_analyzer.py:198`](../../../../pipeline/domain/services/irpf_analyzer.py)).
> O ano eleito é familiar; a base pedida pelo §Escopo 2 é do titular. Se a
> declaração mais recente do titular for de ano diferente do eleito, o par
> (ano familiar, titular) sai **vazio** — e o §Critério 2 registraria isso como
> *"identidade não resolvível"*, quando a identidade resolveu e o **ano** é que não
> casou. Motivo errado é pior que motivo ausente: manda o usuário conferir o CPF.
> A precedência entre os dois eixos é decisão da lane, não detalhe de implementação.
>
> ### 5 · A premissa da lane é verdadeira em código — mas a [[A40.l36]] está `open`
>
> O §Problema diz *"A [[A40.l36]] **fez** a base do PGBL ser o total do IRPF"*, e a
> l36 está `status: open`, sem `ship_pr`. **O código shipou**: `a04fb00f` (#1491)
> renomeou `outras_rendas_tributaveis_pf_anual` → `renda_tributavel_pf_irpf_anual`,
> e hoje `_assemble_input` passa `renda_tributavel_pf_irpf_anual=irpf_total` e
> `_compute_layers` usa esse campo sozinho — pró-labore não entra mais na base.
> A premissa se sustenta; o artefato desatualizado é o `status` da própria l36.
> Quem for verificar pelo frontmatter conclui o contrário.
>
> ### Encaminhamento
>
> Os itens 1 e 2 mudam o §Escopo (o campo de ano na S8 é **pré-requisito** do gate,
> não consequência dele) e os itens 3 e 4 são decisões de domínio antes do código.
> O item 5 é da [[A40.l36]] — flip de `status` + `ship_pr`, não desta lane.

## Problema

A [[A40.l36]] fez a base do PGBL ser o total do IRPF, fonte única. Com isso, a
proveniência do artifact IRPF passou a ser **100% do número publicado** — e ela
tem dois defeitos que antes ficavam mascarados pela parcela de pró-labore.

### 1 · O ano-base não é resolvido

`tributario_input_builder._load_irpf_renda_tributavel` usa
`_read_latest_workspace_artifact(workspace_id, ("extract_irpf_full",))` — a row
**mais recentemente criada por `created_at`**, sem passar por
`resolve_ano_base_fiscal` ([[ADR-305]] D1/D2) e sem dedup.

O resolvedor existe (`pipeline/domain/services/irpf_completude.py`) e é
consumido pelo E5 e pelo Card B. São **dois resolvedores do mesmo corpus** no
mesmo documento: a S8 pode publicar sobre o ano X enquanto o Card B publica
sobre o ano Y — a classe exata que dá nome à [[ADR-375]].

### 2 · O artifact é POR DECLARANTE, e o teto de 12% é por CPF

`e16_irpf_full` tem `contribuinte.cpf_masked` e `ano_base` como `required`. Numa
família com dois declarantes, "o mais recente" é **a declaração de quem foi
processado por último** — que pode ser o cônjuge.

O limite de 12% é **por contribuinte**, não por família. Workspace é família
([docs/reference/tenancy.md](../../../reference/tenancy.md)). Publicar a base de um sobre o nome do outro é erro de identidade,
não de aritmética.

O modelo certo já existe no repo: `pgbl_capacidade_dedutivel` aplica os 12% **por
declaração** e só então soma. Apontar a S8 para `cap.renda_tributavel_anual`
herdaria a agregação familiar e criaria um **segundo modo de inflar** — não é o
caminho.

## Escopo

> **Emendado em 2026-08-24** pelo ataque medido (#1659). Os três itens seguiam na
> ordem em que o defeito foi percebido, não na ordem em que é executável: o item 3
> pressupunha um campo que não existe. Ordem corrigida abaixo; o texto original de
> cada item está preservado.

1. **`_load_irpf_renda_tributavel` passa por `resolve_ano_base_fiscal` e dedup, em
   vez de `created_at`.** ✅ **entregue 2026-08-24** — o eixo do ano deixa de ser a
   ordem de processamento. Ressalva medida: o resolvedor elege **ano**, não
   artefato; com dois declarantes no ano eleito a escolha entre eles continua
   sendo por recência, e isso é o item 2.
2. Âncora de declarante: a base é a do **titular**, resolvido por CPF mascarado
   contra `family_members`. Sem identidade resolvível, a base é ausente — não a
   de quem sobrou.
   - Medido: `NaturezaContribuinte` só tem `titular` e `dependente_titular`, e
     **cada cônjuge é `titular` na própria declaração**. O artefato não sabe quem
     é o titular da família — a resolução por `family_members` não é preferência
     de design, é a única via.
   - Medido: o ano eleito é **familiar** (`anos_base_disponiveis` é a união de
     todos os declarantes). Se a declaração do titular for de ano diferente do
     eleito, o par (ano familiar, titular) sai vazio. Esse caso **não** é falha de
     identidade e não pode sair com o motivo do §Critério 2 — mandaria o usuário
     conferir um CPF que está correto. Precedência entre os dois eixos é decisão
     desta lane.
3. **Pré-requisito do gate: o lado S8 precisa de um ano-base publicável.** Medido:
   `RendaTributavelPF` não tem campo de ano, o bloco `tributario` do
   `e5_analysis.schema.json` é `{}` e o snapshot de dogfood não tem a chave. Sem
   isso o §Critério 3 compara duas ausências.
   - **Armadilha:** `FinanceiroPJSnapshot.ano_base_coberto` já existe no
     `CascataInput` e é alimentado por `max(s.ano_base for s in summaries)` sobre
     **informes PJ**. Usá-lo faz o gate ficar verde medindo outro corpus.
4. Gate: a S8 e o Card B não podem publicar sobre anos-base diferentes no mesmo
   relatório. **Depende do item 3.**

> **Achado da execução do §Escopo 1 (2026-08-24):** passar pelo resolvedor exige
> ler **o corpus**, e aí aparece um segundo eixo de divergência que o §Problema não
> nomeia. `extract_irpf_full` está em `_WORKSPACE_SCOPED_STAGES`, então o E5 lê
> **uma row por `artifact_key`** (`DBArtifactStore._get_latest_in_workspace`). Mas
> a unicidade da tabela é `(pipeline_run_id, stage, artifact_key)` — cada run
> repete as keys, e o E1.6 churna (285 versões de 4 documentos, medidas no dogfood
> em 2026-08-21). Uma leitura ingênua de "todas as rows do workspace" daria à S8 um
> corpus **maior** que o do E5 e reintroduziria a divergência pela porta dos fundos.
> A implementação espelha o `_get_latest_in_workspace`. Medido, porém: isso é
> paridade de corpus e custo, **não** guarda de correção — o dedup de
> `IRPFAnalyzer.from_payloads` já colapsa a duplicata semântica, e não foi possível
> construir caso em que remover o filtro mude o valor publicado.

> **Nota de concepção, medida:** a S8 e o Card B não divergem só no ano — divergem
> no **conceito**. `_build_capacidade_pgbl` usa `irpf.rendimentos_tributaveis(ano)`,
> que soma **todos os declarantes** do ano; a S8 lê **uma** declaração. Um gate de
> igualdade de ano não fecha essa diferença, e igualar os valores exigiria decidir
> antes se a base da S8 é por CPF ou familiar — o que o §Fora de escopo já veda.

## Fora de escopo

- Agregação familiar dos 12% (é por CPF; somar declarações é outro defeito).
- Ausência vs. zero (`sem_irpf_processado` vs. `renda_tributavel_pf_zerada`) —
  `has_renda_tributavel` já é computado e descartado. Follow-up separado.
- **O predicado de completude que alimenta a eleição do ano** (anotado
  2026-08-21 por sessão externa, sem tocar §Escopo nem §Critério de aceite).
  Esta lane torna a âncora determinística **passando pelo** `resolve_ano_base_fiscal`;
  ela não é dona de `irpf_completude.py`. Medido: `_is_shell_decl` exige *todos*
  os blocos vazios, então declaração com `pagamentos_efetuados == []` sai
  `completo` com `nota_degradacao = None` — a âncora fica determinística **sobre
  documento furado**, e cala. A falsificação do limiar está na emenda 2026-08-21
  da [[ADR-266]]; o predicado substituto é da [[A42.l13]]. Sem essa anotação, o
  critério de aceite desta lane passaria com fixture e calaria em produção.

## Critério de aceite

- ~~Dois declarantes no workspace → base do PGBL é a do titular, sempre, e não
  varia com a ordem de processamento.~~ **Parcial desde 2026-08-24:** o **ano** não
  varia mais com a ordem de processamento (§Escopo 1). A escolha **entre
  declarantes do mesmo ano** ainda varia — fecha no §Escopo 2.
- Identidade não resolvível → base ausente com motivo, nunca a de outro CPF. E o
  motivo distingue *"identidade não resolvível"* de *"o titular não declarou no ano
  eleito"* — são causas diferentes e a segunda não é culpa do cadastro.
- Teste que prova que S8 e Card B citam o **mesmo** ano-base. **Só é escrevível
  depois do §Escopo 3** — hoje passaria a vazio comparando dois `None`, e o campo
  homônimo disponível mede informes PJ.
