---
id: A40.l80
type: lane
title: "Denominador amputado: metade da carteira não tem dono, o investível a exclui e o bruto a inclui — cinco superfícies medem 'de quanto se sabe o dono'"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l80-denominador-amputado
adrs:
  - "[[ADR-335]]"
  - "[[ADR-340]]"
  - "[[ADR-394]]"
  - "[[ADR-406]]"
  - "[[ADR-412]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
  - area/report
---

# A40.l80 — Denominador amputado (RV8-02 · RV8-03 · RV8-04 · RV8-06 · RV8-10)

> **O primeiro entregável é a DECISÃO, não o código.** O fix aparente é somar um
> termo. A decisão real é *qual base cada número mede*, e ela reabre a
> [[ADR-335]] (§Emenda, autonomia), a [[ADR-340]] (concentração) e o co-design de
> 2026-05-18 que fixou o denominador da banda cambial. Abra **ADR `Proposto`
> antes do PR de implementação** (CLAUDE.md §Política operacional). Co-design
> `financial-planner` (a decisão de domínio) + `data-engineer` (enum/contrato)
> **antes** de escrever o fix.

## Entregue (2026-08-27) — a correção está em `main` e o relatório já mudou

Onze PRs mergeados. **O defeito está corrigido** e o relatório publica o
intervalo em vez do ponto. O que falta são os gates de completude/precisão e a
manchete na capa — e os critérios que os descreviam estavam inexequíveis, ver
§Correções (2026-08-27).

| PR | merge | o quê |
|---|---|---|
| [#1702](https://github.com/davidrobert/mathoms/pull/1702) | `8b2c7a61` | [[ADR-412]] `Proposto` + retrato desta lane |
| [#1705](https://github.com/davidrobert/mathoms/pull/1705) | `a873b42f` | Emenda 1 — a retenção tornava a decisão inalcançável |
| [#1710](https://github.com/davidrobert/mathoms/pull/1710) | `7565c6e6` | PR1 — `BaseFinanceira`, `PapelMembro`, `$defs` |
| [#1713](https://github.com/davidrobert/mathoms/pull/1713) | `be5adfe0` | Emenda 2 — a §D9 mandava afrouxar o que a §D1 fecha |
| [#1727](https://github.com/davidrobert/mathoms/pull/1727) | `e8bd8448` | **PR2 — o núcleo. Move dinheiro.** |
| [#1735](https://github.com/davidrobert/mathoms/pull/1735) | `f2cca647` | PR3a — `atribuicao_investimentos` + razão advisory |
| [#1741](https://github.com/davidrobert/mathoms/pull/1741) | `9fd524ba` | PR3b substrato — schema, 5ª base, predicado único |
| [#1742](https://github.com/davidrobert/mathoms/pull/1742) | `e561e673` | registro do entregue no vault |
| [#1757](https://github.com/davidrobert/mathoms/pull/1757) | `891c2424` | **PR3b produtores — o relatório muda** |
| [#1768](https://github.com/davidrobert/mathoms/pull/1768) | `ac7834b8` | §Correções C11–C15 — os 3 critérios abertos estavam inexequíveis |
| [#1769](https://github.com/davidrobert/mathoms/pull/1769) | `48a97492` | **C14 — a base declarada vira o denominador usado.** Move o payload |

**Os dois sinais opostos do defeito, fechados:** o patrimônio **excluía** a fatia
sem titular do investível sem declarar (regressão do #1550, em que o termo entrou
em `_compute_bruto` e foi esquecido 190 linhas adiante no mesmo PR); a reserva a
**incluía sob rótulo de pessoa** (`_positions_for_member`, "convenção legado").
Morreram os dois resolvers binários sobre domínio ternário, mais um quarto
(`atribuir_por_membro`). O card cambial parou de publicar faixa que o relatório
recusa julgar.

## Falta — o resto do PR4 e o PR5

**Critério de aceite: 3 fechados, 1 parcial, 1 refutado.** ✅ Consistência (bases
publicadas com termos) · ✅ Corretude (intervalo + identidade) · ✅ **Completude**
(o gate morde e cobre **4 de 4** razões — #1782, #1785, #1794, #1795; a 4ª exigiu
unificar o numerador antes, porque rótulo declara denominador) · 🟡 **Precisão** (as duas declarações falsas medidas
foram corrigidas em [#1769](https://github.com/davidrobert/mathoms/pull/1769); falta
fechar `kpi_targets[].base` no schema) · 🟡 **Prova de fecho** — o critério **como escrito** segue
refutado (C16: inerte e de sinal trocado), mas o **substituto** desenhado pelo
`financial-planner` está **2 de 4 entregue** — ver §abaixo.

**O que falta na Completude, nomeado.** O gate (`tests/test_cobertura_de_base.py`)
recompõe `numerador ÷ base declarada` em cents. Cobertas: `concentracao_imobiliaria`
(#1782), `autonomia_financeira_meses` e `piso_autonomia_financeira_meses` (#1785).

| razão | estado | nota |
|---|---|---|
| `ratios.concentracao_imobiliaria` | ✅ #1782 · #1788 | 6ª base `carteira_produtiva_fixa`; o catálogo parou de declarar a homônima 5,6× menor |
| `ratios.autonomia_financeira_meses` | ✅ #1785 | o divisor virou **campo publicado**; recompute fecha dentro de `ratios` |
| `ratios.piso_autonomia_financeira_meses` | ✅ #1785 | declarava base desde o PR3b e nunca fora recomposto |
| `exposicao_cambial.pct_investivel_financeiro` (+ card V2) | ✅ #1794 · #1795 | numerador unificado, base declarada, e o catálogo **lê** a declaração do produtor |

> **Correção de custo (2026-08-28).** As duas linhas anteriores desta tabela estavam
> erradas e foram refutadas por medição: (i) a autonomia **não** era "médio, recompute
> impossível" — o divisor fechava por `fluxo_caixa.janela_12m`, e o que faltava era
> torná-lo self-contained (o cross-bloco erra no fallback de `_resolve_window`); (ii) o
> card V2 **não** é "alto por causa do `extra=forbid`" — esse `model_config` governa a
> **entrada** do DTO, não o crescimento dele; o custo mecânico é 1 campo opcional + 2
> call-sites + `make update-openapi-snapshot`. O custo alto do card é **semântico**, e é
> outro: o numerador está em disputa.

### O substituto da §Prova de fecho — placar (2026-08-28)

O critério original é inerte na perna da magnitude (C16). O `financial-planner` desenhou
quatro predicados medíveis no lugar dele; dois estão em `main`:

| # | predicado | estado |
|---|---|---|
| **P1** | paridade de definição entre os dois produtores do numerador | ✅ [#1794](https://github.com/davidrobert/mathoms/pull/1794) — o card **consome** o `por_moeda` do artefato |
| **P2** | frescor mata a prescrição dimensionada, **nunca** a medida | ✅ [#1803](https://github.com/davidrobert/mathoms/pull/1803) — `alvo_moeda_forte_brl` some com motivo quando há linha `baseline_irpf`; pct e total ficam |
| **P3** | o **sujeito** na capa: com ≥3 prescrições suprimidas pela mesma causa, manchete única com tarefa única | ❌ componente novo — [[ADR-412]] §Emenda E3 já o desenha |
| **P4** | projeção, não pós-LLM: nenhuma label reensina limiar | ✅ #1808 — **zero** labels com régua no manifest inteiro. O #1780 levou de 2 para 1 e o gate media só o bloco cambial; o sobrevivente era o excluído |

> **Correção (2026-08-28) — o "piso" do P4 era auto-atribuição minha.** Escrevi
> nesta tabela que o degrau sobrevivente ficava "por decisão da [[ADR-353]], cujo hint
> manda 'não recalcule'". Medido: a [[ADR-353]] está em **`status: Proposto`** — não há
> decisão —, e `grep -ci recalcul` nela dá **0**. O hint mora em
> `config/prompts/parecer_planejador.yaml:268`, texto que a **própria A40** escreveu na
> l83. Atribuí a uma ADR o que eu mesmo tinha posto no prompt.
>
> O que sobrevive da minha conclusão: a escada 10/30 **tem** dono real — a [[ADR-353]]
> a define e nomeia as constantes `NAO_IDENTIFICADO_PARCIAL_PCT` /
> `NAO_IDENTIFICADO_INSUFICIENTE_PCT`, e o `_CANONICOS` do
> `kpi_target_catalog.py` já declara o **leitor único** por `ref`. Então a
> **instrução** ("leia o veredito do motor, não recalcule") fica.
>
> O que cai: a **régua**. O `yaml:250` soletra `>10%` / `>30%` dentro do label de
> projeção — quarta cópia de uma constante que já tem leitor único declarado, e é
> exatamente o que o P4 proíbe. Logo o P4 **não está no piso**: sai a régua do label,
> fica a instrução: limiar em label de prompt é **input do modelo**, não documentação —
> o defeito é de **projeção**, e eu o reclassifiquei como doutrina alheia.
>
> **Fechado no #1808.** O teste que media o eixo repetia a mesma frase falsa no comentário
> e se escusava do caso por ela — enquanto o critério que ele próprio enunciava (*régua ao
> lado do número cru*) descrevia exatamente o excluído: a label do `nivel` trazia a escada e
> o `share_nao_identificado_pct` era projetado na linha seguinte. Medido antes de mexer:
> **uma única label em todo o manifest** tinha régua, e era essa. O gate deixou de olhar só
> `$.exposicao_cambial.` e passou a varrer o manifest inteiro — recorte escolhido depois de
> conhecer o ofensor não é gate.

**A raiz do P2 era de publicação, não de regra**, e vale para quem pegar o P3: `CaixaDetalhe`
já carregava `fonte="baseline_irpf"`, e `_detalhes_caixa` publicava o **nome da conta**
naquele campo enquanto o schema tinha `nome` vazio ao lado. Procedência que existe a
montante e morre na publicação faz trabalho de contrato parecer trabalho de domínio.

### Decisões dos especialistas (2026-08-28)

Três especialistas revisaram os abertos. Duas premissas minhas caíram, e eles acharam uma
**regressão que o #1782 introduziu** — corrigida no #1788.

**`data-engineer` — o card para de computar, e consome.** Importar `_is_caixa_me` (o que
esta lane prescrevia) **não basta**: o produtor é `_sum_caixa_estrangeiro` = predicado
**+ inferência de moeda**, e a opção ingênua faz **83% da exposição aparecer rotulada
BRL** no `por_moeda`. Decisão: o V2 **consome** `componentes.caixa_fx`, `por_moeda` e
`detalhes` do artefato, e mantém posse só da perna com input read-time. Regra geral:
*superfície read-time só recomputa a perna que tem input read-time.* Isso é o **vão da
§E2** — ela mandou ler o marcador de série e degradar, e não proibiu recomputar o número
que o marcador rotula. **E o predicado já estava decidido:** a [[ADR-245]] §L3 fixou
`moeda` ≡ unidade de medida; o card usá-la como classificador é violação de ADR `Decidido`.
**P0 novo:** a perna de posições do V2 é **código morto** — lê `investimentos.dados`, que
não existe no schema; a superfície read-time não tem conteúdo read-time vivo e ainda ganha
o paint.

**`financial-planner` — o elogio vive; morre a prescrição, e quem a mata é o FRESCOR.**
O argumento de sujeito **não seleciona**: `caixa_total_brl` fica *ao lado* dos baldes de
papel, então **100% do numerador cambial está fora do eixo de titularidade** — um critério
de sujeito reprovaria sempre, em qualquer família. Gate morto. O sujeito pertence à
**capa** (manchete única, §E3), não a regra pós-LLM por item. O que morre por item é a
**prescrição dimensionada** quando há linha de fonte anual no numerador; a medida nunca.
E o erro caro é o oposto do que esta lane supunha: *"você tem 2%"* empurra **compra** de
moeda forte (IOF, spread, evento tributário) para quem já tem 12%; *"você tem 12%,
confirme"* empurra conferência grátis.

**`senior-cto` — flip com escopo, e o gate certo não é banir divisão.** A [[ADR-412]] vai a
`Decidido` com §Escopo do flip datado (#1789), com as duas emendas que ela mesma exigia
([[ADR-335]], [[ADR-394]]). Sobre o `HeroKpiGrid`: **não** proibir divisão em `.tsx` — são
~30 sites, ~20 viram exceção no dia 1, e allowlist de 20 nasce falha-aberta. A classe que
dói é *"consumidor não fabrica fallback de campo publicado"*, ela tem alvo estreito e
**já tem casa** em `dev/check_view_model_contract.py`, que parseia TS. O caso vivo é
`WaterfallIfChart.tsx:40`, que re-deriva `if_pct` — derrotando a §D7 desta própria ADR.

**A regressão que eles acharam (#1788):** `kpi_targets[].base` declarava
`"carteira_produtiva"` — fora do enum, vizinho **5,6× menor** — para o **mesmo**
`observado_path` que o produtor declarava `carteira_produtiva_fixa`. O C14 na entrada que
o #1782 criou para matá-lo.

### A cambial está bloqueada por defeito maior que o rótulo (2026-08-28)

> **Resolvido em 2026-08-28 ([#1794](https://github.com/davidrobert/mathoms/pull/1794)), pela decisão do `data-engineer`.** O card **consome** o
> `por_moeda` do artefato em vez de recomputar — *superfície read-time só recomputa a perna
> que tem input read-time* ([[ADR-412]] §E10). Importar o predicado **não bastava**: o
> produtor é predicado **+ inferência de moeda**, e a opção ingênua faria 83% da exposição
> sair rotulada `BRL`. A fixture era cúmplice — fixava `valor_brl: 0.0` e não trazia
> `por_moeda`, e com ela **nenhum dos 11 testes caía** sobre a divergência de 6×.
> **Resolvido como COBERTURA, não como remoção (#1801).** A perna de posições do card é
> código morto (`_posicoes_do_payload` lê `investimentos["dados"]`, ausente do schema), mas
> **não** foi deletada: é encanamento de uma feature declarada ([[ADR-224]] §5), e o risco
> real — virar híbrido quando a fonte for ligada — já tinha tripwire
> (`test_braco_de_ativos_nao_chega_ao_endpoint...`). O que faltava era o tripwire **nomear a
> decisão**: desde o #1794 a perna de caixa é consumida do artefato, que é **v1**; ligar
> posições soma ao total algo que a v1 exclui, então quem quebrar o teste escolhe entre
> declarar `definicao_versao=2` **com** o de-dup obrigatório da [[ADR-403]] §D4, ou manter a
> perna fora do total. **A terceira opção — somar as duas sob o marcador do produtor — é a
> que não existe**, porque aquele marcador rotula a computação dele, não a do card.

**O E5 e o card read-time divergiam no NUMERADOR.** A linha de caixa em moeda
estrangeira vinda do IRPF (`moeda_estrangeira_irpf`, que nasce com `moeda="BRL"`)
entra no total do E5 e é **descartada** pelo V2 — medido: **12,0% contra 2,0%** no
shape que o próprio produtor constrói. Os dois renderizam o **mesmo badge do mesmo
card**, e o erro é assimétrico no sentido perigoso: o card **subestima** a proteção
cambial da família.

Publicar `base` nesse número seria maquiagem — **o rótulo declara o denominador**, e o
defeito está no numerador. Ordem correta: o card passa a usar o mesmo predicado
`_is_caixa_me` do produtor (não uma segunda regra escrita à mão), e **só então** o
rótulo. Dono: `data-engineer` (contrato entre produtores) — a decisão é qual dos dois
predicados é o certo, não como nomear a base.

**Colateral medido no mesmo lugar:** a fixture de `test_exposicao_cambial_v2_api.py`
fabrica estados que produção não alcança — `carteira_lastro_estrangeiro` nasce
`Cobertura.indeterminado` hardcoded, então **3 de 7 asserções de tier cobrem regime
impossível**, com a suíte verde. Se a divergência acima fosse introduzida hoje, nenhum
dos testes cairia: nenhum alimenta linha `moeda_estrangeira_irpf`.

**Fora do alcance de gate de artefato:** `HeroKpiGrid.tsx` fabrica `financeiro ÷
liquido` no consumidor, sobre uma **quinta** base que nenhum produtor declara. O
docstring do gate declara esse eixo como não-fechado.

> **Leia §Correções (2026-08-27) antes de escrever o PR4/PR5.** Os três critérios
> abertos estavam redigidos de formas que o código mergeado ou a própria
> [[ADR-412]] já tinham tornado inexequíveis — **C11** (Completude enumera número
> publicado, não leitor), **C12** (`motivo` colide com a XOR de `kpi_targets[]`),
> **C13** (a Prova de fecho nomeia superfície que a §D5 proíbe), **C14** (o defeito
> de Precisão é base *declarada* ≠ denominador *usado*) e **C15** (a §E5 já matou o
> ramo "converge os vocabulários"). Construir o gate como o texto original o
> descreve entrega **verde sobre o defeito**.

O que a medição acrescentou e **não pode ser esquecido** (já implementado no
PR3b, mantido aqui como registro do porquê):

- **Supressão por `None` PIORA o relatório.** Medido: `S7IndependenciaSection.tsx:95`
  faz `((goals.if_pct as number) ?? 0).toFixed(1)` e renderiza **"0,0%"**;
  `HeroKpiGrid.reservaQuality` tem *fallback local* e **re-deriva "excelente"**;
  `_liquidez_excessiva` vira falso e **desarma** `neutralize_autocontradicao`,
  libertando o LLM a elogiar a reserva. Morre a **prescrição dimensionada**, nunca
  a descrição — precedente `alocacao_alvo_deviation.suprimir_prescricao`.
- **A supressão se aplica ao OBJETO, não ao dict.** `e5_analyzer_adapter.py:675` e
  `:754` leem o **atributo** de `IFProjection`; suprimir no dict publicado é
  **no-op** nos dois consumidores mais consequentes.
- **A mesma frase de prescrição existe em DOIS produtores** —
  `pontos_urgentes_analyzer.py:246` e `scripts/analyze_finances.py:1219`. Consertar
  só o domain service instala divergência stage↔legado.
- **O cone sai do escopo.** `if_monte_carlo._GATE_IF_PCT_MIN = 0.15` apaga o cone
  inteiro numa banda que o piso atravessa — re-simular no piso **deletaria** o
  artefato que a §Emenda E3 decidiu preservar. **§Deferido datado (2026-08-26)**,
  dono da lane, condição de retomada: antes de qualquer superfície publicar
  intervalo de IF.
- **A manchete é condição do `financial-planner`**: com ≥3 prescrições suprimidas
  pela mesma causa, o relatório promove a causa a **manchete única com tarefa
  única** na capa. Cinco ressalvas espalhadas ensinam que *o relatório está
  quebrado*; uma manchete ensina que *falta um dado da família*.

## Follow-ups nomeados, fora desta lane

- **Emenda datada em [[ADR-406]] §D4** — o rationale (*"razão que não retém é
  descartada no chão"*) está factualmente vencido desde `954f892f` ([[ADR-411]]),
  que pôs `_record_stage_diagnostics` no caminho de sucesso. Sem a emenda, a
  próxima lane reinstala retenção pelo mesmo argumento morto.
- **Caracterizar o E5 em `tests/unit/pipeline/test_validation_block_policy.py`** —
  é o quarto produtor divergente de política de pausa e o único não coberto;
  `valid = not reasons` ignora `BLOCKING_CODES`.
- **✅ FECHADO ([#1799](https://github.com/davidrobert/mathoms/pull/1799)) — `BASE_VERSAO_CORRENTE` nunca bumpado.** O remédio não foi
  bumpar: um escalar **não retro-rotula** (fundiria a janela defeituosa com a correta,
  marcaria todo o corpus como não-corrente e degradaria o card cambial sem corrigir um
  centavo), e aquilo **não foi mudança de significado, foi bug** — a base publicava
  `valor_brl` contradizendo o `termos` ao lado dela. Entraram **G1** (`bases_reproduzem`:
  toda base soma os próprios termos em cents, sem golden e sem rebaseline jamais) e **G2**
  (congela `TERMOS_DA_BASE` por série; termo de base existente exige bump, membro novo
  não). Achado no caminho: `cat2_efetivo` **não era publicado** embora fosse termo de duas
  bases — a promessa da §D1 de auditar "só do payload" era falsa para 2 das 6.
  **Fica aberto, menor:** `_piso_produtivo` (`e5_analyzer_adapter.py:198`) lê `valor_brl`
  cru e poderia exigir reprodução antes de consumir; a semântica da degradação é decisão
  de domínio e não foi inventada aqui. Dono: `data-engineer`.
- ~~**`BASE_VERSAO_CORRENTE` nunca foi bumpado, e um PR desta lane mudou o valor de
  base publicada sem ele**~~ (histórico abaixo, preservado) — a fronteira de série da [[ADR-412]] §D8 existe para impedir
  "híbrido sem rótulo", e foi isso que embarcou. `git log -S` mostra a constante definida
  no #1727 e **nunca mais tocada**; o #1757 (`891c2424`) trocou `_somar_termos` por
  `_valor_da_base`, que resolve referência entre bases — o **valor** das bases derivadas
  (`carteira_produtiva_*`) mudou de significado sob `base_versao: 1`. O remédio **não** é
  acoplar o bump a `len(BaseFinanceira)`: adição de membro é número-neutra (o #1782 é
  prova) e bumpar nela jogaria `serie_corrente()` em `False` no corpus inteiro,
  degradando o card para `indeterminado`. O bump responde a *"o valor de alguma base
  publicada mudou de significado?"* — e a forma barata é congelar em fixture o par
  (termos, valor) por base e reprovar quando um valor se move sem o bump. Dono:
  `data-engineer`. Achado de 2026-08-28.
- **✅ FECHADO (#1800) — `neutralize_autocontradicao` armava em seção que o modelo nunca
  vê.** `_SECAO_LIQUIDEZ` valia `"S4"`; o manifest projeta S1/S2/S3/S7/S8/S9/S10 e a
  reserva é `aligned_with_layout: "S1"`. Com o sinal do E5 **vivo** no golden
  (`avaliacao_liquidity == "Excessiva"`), ele nunca disparou — e a [[ADR-412]] §Emenda E3
  apoiava-se nele para **não** suprimir `avaliacao_liquidity`. A suíte codificava o
  defeito: 4 testes fixavam `"S4"` e passavam. O conserto veio com **gate de classe** — a
  seção em que um guardrail arma tem de ser uma que o manifest projeta —, porque os testes
  agora importam a constante e passariam com qualquer valor. **Não mudou** o seletor
  `(section_id, tema_canonico)`, que o r7 mediu em 2/5 com um falso-positivo: estreitá-lo
  é outra decisão, com dono `prompt-engineer`.
- ~~**`neutralize_autocontradicao` é praticamente inerte em produção**~~ (histórico) — ele arma em
  `(section_id, tema_canonico) == ("S4", "Liquidez")` (`parecer_guardrails_divida.py:159-160`),
  mas o bloco de reserva/liquidez do manifest é `aligned_with_layout: "S1"`
  (`config/prompts/parecer_planejador.yaml`, seção `saude_balanco`) e **S4 é "Real Estate"**
  (`config/report_layout.yaml`). Nenhuma seção projetada ao modelo é rotulada S4, então o par
  só casa se o modelo errar o rótulo. É o guardrail que a [[ADR-412]] §Emenda E3 cita como
  razão para **não** suprimir `avaliacao_liquidity` ("desarma `neutralize_autocontradicao`,
  libertando o LLM a elogiar a reserva") — o argumento se apoia num guardrail que provavelmente
  nunca disparou. Dono: `prompt-engineer`. **Não consertar de raspão**: trocar `S4`→`S1` muda
  quais pontos fortes são removidos, é mudança de comportamento sobre saída de LLM, e o r7 já
  mediu que casar por esse par dá 2/5 com um falso-positivo. Achado de 2026-08-27, ao atacar
  a §Prova de fecho desta lane.
- **`desvio_max_pct` não implementado** — `config/methodology.md:216-217` condiciona
  "realocar excedente" a DUAS condições, e `pontos_fortes_analyzer.py:173` só
  checa uma.

## Correções à lane (2026-08-25 · re-medição no run `d0f6260a`)

> A decisão está fechada em **[[ADR-412]]** (`Proposto`). Esta seção retrata o que
> a re-medição refutou — nada abaixo foi apagado, e onde o texto original diverge,
> **esta seção prevalece**.

**A tese central se sustenta** (fatia órfã = 48,13% de `investimentos.total_financeiro`;
concentração 66,79% → 50,62% na base cheia, delta 16,17 p.p.). O que não reproduziu:

| # | Está escrito | Medido | Leia assim |
|---|---|---|---|
| C1 | "a banda cambial cruzou para **verde**" | `tier == "indeterminado"`. **Verde é estruturalmente inalcançável**: `_tier` (`exposicao_cambial_analyzer.py:133-136`) curto-circuita porque `carteira_lastro_estrangeiro` é fixado `Cobertura.indeterminado` incondicionalmente (`:287-292`) desde o #1568 ([[ADR-403]]) — `_tier_from_pct` é código morto em produção | o **pct** cruzou o limiar verde (12,55% ≥ `THRESHOLD_VERDE_PCT`); quem publicou "faixa verde" foi a **prosa do parecer**, não o campo |
| C2 | "o denominador caiu **44,4%**" | 44,4% é razão **cross-run** (r7→r8) e mistura amputação com crescimento de corpus | **dentro do r8 a amputação é 49,03%** (base atual = 50,97% da cheia). Não são intercambiáveis |
| C3 | "a banda volta de verde para amarelo"; "não conserte a banda de volta para verde" | **inobservável** — sob o fix `tier` não se move, segue `indeterminado` | procure o movimento em `pct_investivel_financeiro` (12,55% → 6,40%) e na prosa do parecer. A ausência de flip em `tier` **não** significa que o fix não pegou |
| C4 | corte "composição × runway" | o corte é **domiciliar × por-pessoa** — reserva e autonomia têm denominador de despesa do **domicílio**, logo querem base cheia | [[ADR-412]] §D0. E **neste caso é somar um termo**: `git log -L` mostra regressão do #1550, não escolha de design |
| C5 | §Raio de explosão | omite o **bloco IF inteiro** (`investivel_efetivo:219` → `if_projector`, cone MC, `cenarios_conjuge`), `exposicao_cambial_v2.py:286` (recomputa no read) e `HeroKpiGrid.tsx:85-88` | autonomia e IF movem **mais** que a concentração |
| C6 | "`kpi_targets[].base` não é honrado pelos produtores" | os 10 targets **têm** `base` preenchida — e ela é **incoerente**: `concentracao_imobiliaria` declara `carteira_produtiva` e `exposicao_cambial` declara `investivel_financeiro` para denominadores que compartilham o mesmo termo amputado | o problema é o **vocabulário** do campo, não o preenchimento. Senão o fix vira "preencher o campo" |
| C7 | RV8-06: "abrir o enum `membro` + terceira `CoberturaMembro`" | `CoberturaStatus(linha.get("status"))` (`:144,236`) levanta `ValueError` em **leitor antigo lendo artefato novo**; e `cobertura_investimentos` particiona **pessoas**, a órfã particiona **dinheiro** | **rejeitado** — eixo separado `patrimonio.atribuicao_investimentos` + `Papel` ternário ([[ADR-412]] §D2/§D5) |
| C8 | §Corretude: identidade da reserva | **já fecha hoje, em 0,00%, sobre o defeito** — fecha *porque* a órfã foi absorvida sob rótulo de membro | gate de soma contra defeito que preserva soma. O predicado que discrimina é **partição por item** |
| C9 | — | **o terceiro resolver não está na lane** — ver §abaixo | driver primário do RV8-06 |
| C10 | §Rastro | [[ADR-394]] §D8 declara denominador de 35 sites em 4 arquivos; `reserva_liquidez.py` não está nele | é o inventário do **regex**, não da classe. Emenda datada devida ao flipar a [[ADR-412]] |

### C9 — o terceiro resolver (achado desta sessão, ausente do texto original)

`reserva_liquidez.py:177-191` (`_positions_for_member`) resolve titularidade por
conta própria, com convenção **invertida** — o docstring `:180` declara: *"sem membro
atribuído → titular (convenção legado)"*. É a afirmação que `atribuir_por_membro`
documenta ter removido (`investimentos_cobertura.py:177`).

Medido executando `_filter_liquid` sobre os itens reais, delta 0,00:

- **58,64%** do que a reserva rotula "titular" é dinheiro sem dono
- `composicao_liquida.investimentos_titular` = **2,42×** `patrimonio.investimentos_titular`
- `cobertura_meses` publica **43,9** contra **25,4** na partição correta — **18,5 meses
  inflados**, sob veredito `avaliacao_liquidity: "Excessiva"` (alvo 18)
- ramo culpado: `elif not membro and member_key == identity.titular_key` (`:189-190`) —
  15 das 18 posições têm `membro` vazio e carregam 68,1% do valor

**Sinal oposto ao do patrimônio:** o patrimônio **exclui** a órfã sem declarar; a
reserva a **inclui sob rótulo de pessoa**. No mesmo payload, a composição publica a
linha "Investimentos sem titular identificado" (16,6% do bruto, maior que os dois
membros nomeados somados) enquanto a reserva chama esse dinheiro de titular. As duas
correções são opostas e precisam ser decididas juntas — uma sozinha reabre a outra.

Um único commit na história (`b1df6d64`, 2026-07-06, A28.l1 #787), **nenhum teste**,
**zero menções no vault**. O gate `dev/check_member_key_substring.py` varre o arquivo
e sai `0` porque identifica a chave pelo **nome da variável**
(`_KEY_SUFFIXES = ("titular_key","conjuge_key")`) e ali ela se chama `member_key` —
verde por 7 semanas sobre instância viva da classe que [[ADR-394]] §D8 fechou.

**Não** troque a substring de `:187` por `matches_member_key` como o fix: com
`membro == ""` a substring é `False`, e **100% do excedente vem do ramo `:189-190`**.
Seria fix mal-mirado com gate verde por cima.

## Correções à lane (2026-08-27 · medição contra `main` `951f4ca8`)

> Segunda re-medição, agora **contra o entregue** (9 PRs em `main`). Nada abaixo
> foi apagado; onde o texto original diverge, esta seção prevalece. Ela toca o
> **§Critério de aceite**, que a seção de 2026-08-25 não alcançava: a tabela
> C1–C10 cobria §Corretude (C8) e `kpi_targets[].base` (C6), nunca §Completude
> nem §Prova de fecho. Os três critérios abertos estavam escritos de formas que o
> código mergeado ou a própria [[ADR-412]] já tinham tornado inexequíveis.

| # | Está escrito | Medido | Leia assim |
|---|---|---|---|
| C11 | §Completude: "gate que **enumera os consumidores** de `investivel_financeiro`" (§Falta e §Critério de aceite) | a [[ADR-412]] §Consequências **já refutou essa formulação por escrito**: *"O critério de Completude escrito na lane fecha só instância… **Não enumere leitores — enumere números publicados**"*, e nomeia três fugas — `investivel_efetivo` (hub do bloco IF), parâmetro renomeado (`if_projector.project(investivel=…)`) e denominador remontado dos termos sem citar o nome | o gate mede **número publicado**, não leitor: *toda razão publicada reproduz ao recomputar numerador ÷ base declarada, em cents*. Escrever o gate como a lane pedia entrega verde sobre o defeito |
| C12 | §Precisão: "`motivo` deixa de ser `null` quando a fatia órfã cruza o piso" | **colide com invariante publicada**: `kpi_targets[]` exige XOR entre `procedencia`+`limiar` e `motivo` (schema §`kpi_targets`), enforçada em `tests/unit/pipeline/test_kpi_target_catalog.py:135` e `tests/test_e5_golden_execution.py:320`. Os dois alvos que importam (`exposicao_cambial`, `concentracao_imobiliaria`) têm `procedencia` — setar `motivo` deixa **dois testes vermelhos** | a ressalva de base precisa de **campo próprio**; `motivo` é "por que este alvo é órfão", não "sobre que base ele foi medido" |
| C13 | §Prova de fecho: "`cobertura_investimentos` contém linha para a fatia órfã" | **superfície proibida** pela [[ADR-412]] §D5 e pela própria C7 desta lane: `cobertura_investimentos[]` particiona **pessoas** e fica fechado em `["titular","conjuge"]`, porque `CoberturaStatus(linha.get("status"))` levanta `ValueError` em leitor antigo lendo artefato novo | o predicado é `patrimonio.atribuicao_investimentos.motivo != null` — eixo irmão que o PR3a já entregou, com piso próprio (`PISO_AGREGADO_PCT = 1.0`) e razão advisory |
| C14 | §Precisão: "`kpi_targets[].base` já existe e **não é honrado pelos produtores**" | os 10 alvos **têm** `base` preenchida (C6 já dizia). O defeito é pior e é outro: **base declarada ≠ denominador usado**. `protecao_cobertura` declara `renda_anual_ativa` e o produtor divide por `renda_anual_liquida_brl` (`protecao_analyzer.py:470`); `_reserva` fixa `despesa_essencial_mensal` no código (`kpi_target_catalog.py:181`) enquanto o produtor publica o discriminador como **dado variável** — `base_denominador ∈ {custo_essencial, despesa_total}` (`reserva_emergencia_calculator.py:333-350`, publicado em `:278`) | em workspace sem categoria essencial documentada, o catálogo declara base essencial sobre denominador de despesa **total**. O valor certo já está no payload, a um `_leaf()` de distância |
| C15 | §Falta: "a §D9 **pede** `kpi_targets[].base` estreitado ao enum… quem pegar decide: converge ou reescreve" | a §D9 foi **reescrita in-place** por `be5adfe0` (#1713) e hoje diz o contrário; a §E5 **já decidiu**: *"Registrar a disjunção é a decisão; convergir, não"*. O ramo "converge" está morto | resta **um** ramo, não dois: reescrever o critério de Precisão. E convergir seria **falso** — `carteira_produtiva` (denominador real `investivel_financeiro + imoveis_investimento` = 73M no dogfood) ≠ `carteira_produtiva_familia` (13M), divergência de 5,6× **com o toggle IF ligado** |

| C16 | §Prova de fecho: "nenhum `pontos_fortes` se apoia em banda cuja base tenha fatia órfã acima do piso" | lida como **magnitude**, a regra é **inerte e de sinal trocado**. O numerador (`caixa_fx`) está nas duas bases (`caixa_total_brl` é termo comum); a base-piso é **estritamente menor**; e o veredito é `>=` numa escada **sem teto** (`_tier_from_pct`). Logo `pct_piso >= pct_cheia` **sempre** — o pct publicado **já é o extremo conservador**, e a fatia órfã só torna um elogio cambial *mais* verdadeiro. A própria lane mediu ao contrário: 12,55% (amputada) → 6,40% (cheia) — **a amputação inflava a banda** | o que sobra é o argumento de **sujeito** ("a exposição de quem"), que não é privativo do câmbio e **não se seleciona por lemma cambial**. E não há corpus: zero `pontos_fortes` de LLM no repo, `PontoForte` sem discriminador estrutural (sem `metrica_key`, sem `TemaCanonico` cambial, cambial mora em S1) — lemma nasceria cego, que foi o que matou `"trajetor"`/`"ritmo"` no guardrail de trajetória |
| C17 | 9 datas desta lane e das ADR-403/412 stampadas **1 e 2 dias à frente** (`2026-08-29`/`2026-08-30` em `amended_at`, em heading de emenda e no placar), com todos os PRs mergeados em `2026-08-27`/`2026-08-28` | `check_adr_amendment_signal` leu o mesmo `amended_at` e ficou **verde**: ele exige que a data do heading **exista** no frontmatter, nunca que ela seja **possível**. Varredura de `docs/**` no mesmo dia: **zero dívida histórica** — os 2 arquivos ofensores eram os da sessão | datas corrigidas para o dia real (por `git blame` do commit que as trouxe) + `dev/check_future_dated_evidence.py` cobrindo `date`/`ship_date`/`amended_at` em todo `docs/**`. A/B contra `origin/main`: reprova os 2 arquivos; verde depois da correção. `date_target` fica fora — alvo de plano não é evidência |
| C18 | o card cambial decidia `empty` **antes** de checar cobertura; o produtor decide o contrário e diz por quê no próprio teste ("sem posições medidas, 'sem exposição' seria afirmação") | com as pernas invertidas, numerador zerado sobre cobertura não apurada saía `empty` — e aí a UI **não degrada**: zera o badge e escreve *"Nenhum ativo com lastro fora do real"*. A supressão do veredito virava **afirmação positiva de ausência** sobre a perna que o produtor recusou fechar, o oposto da §E3. A fixture era o gate outra vez: os dois testes de supressão semeavam R$ 60.000, então `has_data` era sempre `True` e o par `cobertura=indeterminado ∧ total=0` nunca era montado | ordem invertida para casar o produtor + caso de **rota** (endpoint sobre o par) + **tabela-verdade** das 6 combinações — defeito de ordem só se prova varrendo o produto das pernas. Reverter deixa 3 vermelhos. Zero mudança no frontend: `indeterminado` já tinha rótulo e badge |

**A metade a-montante foi entregue** ([#1780](https://github.com/davidrobert/mathoms/pull/1780)): a §D7 mandava o manifest *"parar de reensinar o limiar na label"* e isso nunca fora feito — `parecer_planejador.yaml` entregava `"Tier (verde >=10% / amarelo 5-10% / vermelho <5%)"` ao lado do `pct` cru, e o modelo declarava a faixa sozinho. Era a quarta cópia de um limiar cujo leitor único é `kpi_target_catalog` ([[ADR-399]]). Junto, `atribuicao_investimentos.{motivo,pct_carteira_financeira}` passaram a ser **projetados** — o eixo existia desde o PR3a e o modelo só via o valor em BRL. Labels que reensinam limiar: **2 → 1**.

**PR4 entregue** ([#1782](https://github.com/davidrobert/mathoms/pull/1782)): o gate de
Completude achou defeito no primeiro uso. `ratios.concentracao_imobiliaria` divide por
**73.000.000** e **nenhuma** das 5 bases publicadas continha esse valor — as quatro de
carteira valem 13.000.000, porque `carteira_produtiva_familia` soma `cat2_efetivo` (só
imóveis **geradores**, zera com o toggle off) enquanto a concentração usa cat_2
**completo** e é toggle-independente ([[ADR-340]]). **5,6× sob o mesmo rótulo "carteira
produtiva"** — o RV8-02 um nível acima, como a §"Por que isto não é somar um termo" desta
lane previu. Entrou a 6ª base `carteira_produtiva_fixa`, número-neutra.

**Duas lições do gate, para quem escrever o resto dele.** (1) **A fixture é o gate**: o
golden do dogfood tem `nao_atribuidos = 0` e `cat2_efetivo = 0`, o que faz 4 das 6 bases
valerem o mesmo número — recompute rodado ali passa com **qualquer** base substituída,
inclusive a amputada. A fixture do gate sai com as seis duas-a-duas distintas, e há teste
que verifica isso. (2) **O gate lê a declaração do produtor**, nunca um membro do enum
escrito no teste: a primeira versão fixava o membro e **passava** com a homônima trocada
no produtor — cega exatamente na classe que existe para pegar.

**Agravante de processo, para o closeout:** a formulação refutada em C11 não é
prosa envelhecida — ela foi **reinscrita** em `a28055a7` (#1758, 2026-08-27), dois
dias *depois* da [[ADR-412]] que a refuta. A cláusula de precedência da seção de
2026-08-25 não a alcançava, porque C1–C10 não declarava divergência sobre
§Completude. Quem lesse só o topo do §Falta construiria o gate errado.

**Armadilha do PR4, atualizada:** não é escolher entre convergir e reescrever (C15
matou o primeiro ramo). É que **três** dos vocabulários de "base" coexistem por
decisão declarada — `BaseFinanceira` (eixo de posições), `BaseDaMetaIF`
([[ADR-418]], eixo da meta) e `kpi_targets[].base` (eixo dos alvos, único **aberto**:
`type: string` sem `enum`, enquanto o campo irmão `procedencia` no mesmo bloco já é
enum). Fechar o terceiro contra o vocabulário que os produtores realmente publicam
é o trabalho de Precisão; fundi-lo aos outros dois é o que a §E5 proíbe.

**O §Deferimento da [[ADR-412]] §E6 dispara no PR4.** Ele adia *"decidir se
[reserva e autonomia] são uma base com fallback declarado ou duas bases
distintas"*, com dono desta lane e **condição de retomada: "antes de qualquer
superfície declarar `base` para reserva ou autonomia"** — que é exatamente o que
fechar `kpi_targets[].base` faz (`_reserva` declara `despesa_essencial_mensal`).
A medição de C14 já entrega a resposta: são **duas bases distintas**, e a da
reserva já carrega o fallback **como campo publicado** (`base_denominador ∈
{custo_essencial, despesa_total}`), enquanto a autonomia divide por
`despesa_consumo_brl ÷ n_meses` (ex-aporte, [[ADR-333]], `ratios_calculator.py`).
Formalizar isso é **emenda datada na [[ADR-412]]**, e ela viaja com o PR de código
que declara a base — não antes, senão a ADR decide sobre superfície que não existe.

**Fora do escopo, já com dono:** o segundo produtor que particiona posição por
membro com a convenção invertida — `fonte_precedencia_arbiter.py` (`membro =
_slug(pos.get("membro")) or membro_default`, alimentado com
`membro_default=self._identity.titular_key`) — é da [[A40.l41]], que está `open` e
o nomeia explicitamente. **Não re-homear aqui.**


## Acolhimento — a classe de `is_monetary` não fecha por sufixo (2026-08-27)

> **Escrito do lado que recebe.** Achado do §Ataque da [[A40.l90]] (#1766/#1767),
> roteado para cá por co-design (`data-engineer`, `product-manager`, `senior-cto`):
> esta lane está `open`, é dona assinada de `dev/golden_diff.py` — o comentário que
> instalou o sufixo é literalmente `# A40.l80:` — e **previu esta classe por escrito**
> (*"fechar por instância deixaria o próximo campo de versão nascer com o mesmo bug"*).
> Este é o próximo campo, e ele **não é endereçável por sufixo**.

**Medido contra `main` `1647578f`, com o `_monetary_paths` do próprio teste de
snapshot: 26 de 198 classificações monetárias estão erradas (13,1%), em 9 famílias.**

| path | grandeza real | golden publica |
|---|---|---|
| `kpi_targets.*.limiar` (5) | pct / meses | 50% → `5000`; 18 meses → `1800` |
| `score.valor` (1) | nota 5,9/10 | `590` |
| `score.componentes[].valor` (5) | pct / meses | ×100 |
| `score.breakdown[].valor` (5) | nota 0-10 | ×100 |
| `score.breakdown[].contribuicao` (5) | pontos | `250` = 2,50 pts |
| `investimentos.top_ativos[].posicao` (2) | **ordinal** | rank 1 → `100` |
| `…instituicoes_por_membro[].n_posicoes` (1) | **contagem** | 1 → `100` |
| `ratios.concentracao_imobiliaria` (1) | pct | `8219` |
| `consumo_consciente.equivalente_meses_aporte` (1) | meses | ×100 |

**Por que sufixo não alcança.** `is_monetary` chaveia no *leaf*; a grandeza é **dado**,
não nome. `kpi_targets[].limiar` carrega três unidades no mesmo leaf (`pct`, `meses`,
`pct_aa`). E ler o irmão `unidade` cobre só 5 dos 26: `top_ativos[].posicao` e
`n_posicoes` não têm irmão, `score.componentes[].unidade` está no schema e **não é
emitido** (`None` no payload), e em `parecer_planejador.schema.json` `unidade ∈ {ano, mes}`
é **janela temporal** ao lado de `valor_estimado_brl`, que **é** dinheiro — a regra
fliparia um campo `_brl` para não-monetário, falso-negativo na direção cara.

**Prova mais curta:** o mesmo número, da mesma fonte, sai duas vezes no golden —
`reserva_emergencia.meses_alvo` = `18` (está em `_NON_MONETARY_EXACT`) e
`kpi_targets.reserva_cobertura_meses.limiar` = `1800` (não está).

### O que precede tudo: o golden não tem gate

`dev/check_golden_rebaseline_isolation.py:23` fixa
`_GOLDEN_PREFIX = "tests/fixtures/pipeline_golden/"` — **não cobre**
`backend/tests/snapshots/dogfood_view_model.json`, que é onde `kpi_targets` e `score`
vivem. `golden_diff` **não é invocado em CI nenhum** e
`tests/fixtures/pipeline_golden/rebaseline_manifest.yaml` está **vazio (`[]`)**. Ou seja:
o delta de golden pode viajar no mesmo commit do código que o produziu, sem violar gate.

**Isto é gate de entrada da [[A40.l90]]** (veredito `senior-cto`): ela não pode declarar
"delta de golden declarado" sobre um golden sem disciplina.

### Ordem e amarra

Vai **antes** da [[A40.l89]] e da [[A40.l90]]: toca `dev/`, `config/schemas/**`
(anotação) e `backend/tests/snapshots/` — **não** `pipeline/`/`scripts/`/`backend/app/`,
logo **não muta E5 e não zera o contador de 2 re-runs** do §Gate de saída. O rebaseline é
auditável por construção: todo valor muda de `v` para `v/100`, e isso deve ser o critério
de aceite do PR, não inspeção ocular.

**Forma:** ADR nova `Proposto` (grandeza declarada no contrato, não inferida do nome).
Recusadas: [[ADR-090]] (rege *como* dinheiro se representa, não *quais* campos são) e
[[ADR-399]] (rege procedência do limiar; é produtor de 5 dos 26). **O ID não é alocado
aqui** — quem executar aloca na escrita (`ls docs/adr/ | tail`), pela regra do CLAUDE.md
de nunca reservar ID.

## O fato, medido no r8 (run `d0f6260a`)

`patrimonio.investimentos_nao_atribuidos` é **48,1% de `investimentos.total_financeiro`** —
quase metade da carteira financeira sem titular identificado. E as duas funções
que consomem esse valor discordam **dentro do mesmo arquivo**:

| | `pipeline/domain/services/patrimonio_calculator.py` | inclui `nao_atribuidos`? |
|---|---|---|
| `investivel_financeiro` | `:209-212` | **não** |
| `_compute_bruto` | `:403-416` | **sim** |

O valor está no escopo das duas. A exclusão não é declarada em lugar nenhum —
nenhuma superfície diz ao leitor que a base encolheu.

**Não confie nestes números: re-meça.** Eles vêm do r8 e o corpus muda.
`.venv/bin/python dev/dump_artifact.py --run <run> --stage analyze_finances --key analise_financeira --raw`
e recomponha as razões. Achado com medição citada se re-mede antes de virar fix.

## Por que isto não é "somar um termo em cinco lugares"

**Os consumidores não querem a mesma base.** Esta é a decisão que a lane tem de
fechar, e prescrever "inclui em todo lugar" seria errado:

- **Composição** — `ratios.concentracao_imobiliaria` ([[ADR-340]]) e
  `exposicao_cambial.pct_investivel_financeiro` perguntam *que fração da carteira
  é X*. Excluir a fatia órfã do denominador **infla artificialmente** a fração:
  no r8 a concentração publica 66,8% quando sobre a base cheia dá ~50,6%, e a
  banda cambial cruzou para **verde com o total em ME byte-idêntico ao run
  anterior** — o percentual subiu porque o denominador caiu 44,4%, não porque a
  proteção aumentou. Estes querem a base **cheia**.
- **Runway** — `ratios.autonomia_financeira_meses` ([[ADR-335]] §Emenda)
  pergunta *por quantos meses a família se sustenta*. Incluir dinheiro cujo dono
  o sistema não sabe **infla o fôlego** com ativo que pode não ser sacável pelo
  titular. Este talvez queira a base **certificada** — e talvez queira publicar
  as duas.

Se as duas leituras coexistirem, elas **têm de ser nomeadas**: dois números com
o mesmo rótulo e bases diferentes é o defeito RV8-02 recriado um nível acima.
Hoje já há **quatro** bases distintas para "carteira financeira" no mesmo payload.

## Ordem obrigatória: o vocabulário antes do número

**RV8-06 vem primeiro.** Não dá para publicar ressalva de base nem terceiro balde
de reserva enquanto o vocabulário não tiver célula para "sem dono":

- `cobertura_de_membros` (`pipeline/domain/services/investimentos_cobertura.py:207-222`)
  itera **papéis**, e é chamada em `patrimonio_calculator.py:371-375` só com
  `titular=` e `conjuge=`. O balde órfão que `atribuir_por_membro` (`:179-195`)
  acumula sob chave `""` não tem parâmetro.
- `cobertura_investimentos[].membro` é enum **fechado** em `["titular","conjuge"]`
  (`config/schemas/e5_analysis.schema.json:357-360`).
- `review_reasons_da_cobertura` (`:228`) só projeta `nao_apurado` — com as duas
  linhas em `apurado`/`motivo: null`, nada dispara sobre 48,1% da carteira.

Abrir o enum + emitir a terceira `CoberturaMembro` acima do piso de 0,50% já
decidido na [[ADR-406]] é o que **destrava** RV8-02/03/04/10. Feito isso, a razão
dispara e o run passa a reter — comportamento desejado, mas que precisa de
rollout controlado (há precedente de flag: `cobertura_enforcement_ligado()`).

## Escopo por achado

| Achado | Superfície | O que fecha |
|---|---|---|
| **RV8-06** | `investimentos_cobertura.py:207-222` · `e5_analysis.schema.json:357` | terceira linha de cobertura para a fatia órfã; razão dispara acima do piso |
| **RV8-02** | `patrimonio_calculator.py:209-212` vs `:403-416` | base decidida e **declarada** por consumidor; assimetria intra-arquivo eliminada ou justificada em docstring + ADR |
| **RV8-03** | `exposicao_cambial_analyzer.py` (`_pct_sobre`, `:282-308`) | banda recomputada sobre a base decidida; regra pós-LLM que barra `pontos_fortes` cuja banda dependa de base com fatia órfã acima do piso |
| **RV8-04** | `reserva_emergencia_calculator.py:231` + `reserva_liquidez.py` | terceiro componente em `composicao_liquida`; **nenhum valor sem dono sob rótulo de membro** |
| **RV8-10** | `frontend/src/components/report/utils/visibleCompositionRows.ts:47-51,75-79` | `kind`/estado próprio no produtor; a lacuna sai das fatias do donut e vira anotação |

## Raio de explosão — mapeado, e move a capa

Alterar `investivel_financeiro` move, em cascata: `patrimonio.investivel_efetivo`
(`:219`) · `ratios.autonomia_financeira_meses` · `ratios.concentracao_imobiliaria`
· `exposicao_cambial.pct_investivel_financeiro` **e a banda** ·
`financial_score_calculator` (`concentracao_imobiliaria` é **componente de score**)
· `kpi_target_catalog.py:81-82` · e o valor projetado ao LLM em
`config/prompts/parecer_planejador.yaml:183`.

**Armadilha que vai parecer defeito e não é.** Corrigido o denominador, o
`dev/compare_reviews.py` vai reprovar em massa: a concentração cai ~16 p.p., a
banda cambial volta de verde para amarelo e o score se move. **Isso é a correção,
não regressão** — o r7 já ensinou essa lição (o compare leu correção como
regressão e congelar o baseline teria aprovado a corrupção). Declare os paths
esperados no PR. E **não** "conserte" a banda de volta para verde.

## Critério de aceite

**Corretude** — a identidade da reserva se preserva com o terceiro componente:
`composicao_liquida.{titular + conjuge + sem_titular} + excluido_da_reserva.investimentos_nao_liquidos`
== `patrimonio.{investimentos_titular + investimentos_conjuge + investimentos_nao_atribuidos}`.
Teste em `tests/test_e5_conservation_invariants.py`, tolerância zero.

**Completude** — nenhum consumidor do denominador fica na base antiga por
omissão. Gate: teste que enumera os consumidores de `investivel_financeiro` e
falha se algum não declarar sua base. Consumidor novo nasce obrigado a declarar.

**Consistência** — nenhum par de superfícies do mesmo payload publica o mesmo
conceito sobre bases diferentes sem nomeá-las. Verificação empírica: as quatro
bases de "carteira financeira" hoje existentes viram uma canônica + derivadas
declaradas.

**Precisão** — a base de cada número é **campo**, não prosa: `kpi_targets[].base`
já existe e não é honrado pelos produtores; `motivo` deixa de ser `null` quando a
fatia órfã cruza o piso. Afirmação em prosa envelhece no rebase; campo não.

**Prova de fecho** — o predicado que o r9 vai medir: `cobertura_investimentos`
contém linha para a fatia órfã sempre que ela é > piso; a banda cambial recomputa
sobre a base declarada; e **nenhum** `pontos_fortes` do parecer se apoia em banda
cuja base tenha fatia órfã acima do piso.

## Rebaseline consciente

`backend/tests/test_report_view_model_snapshot.py` e as baselines visuais de print
vão precisar de rebaseline. **Olhe as imagens** — baseline commitada sem olhar já
passou defeito neste repo.

> **Correção (2026-08-28): o hook G-c NÃO cobre este golden.**
> `dev/check_golden_rebaseline_isolation.py:23` fixa
> `_GOLDEN_PREFIX = "tests/fixtures/pipeline_golden/"`, e o snapshot que esta seção
> nomeia vive em `backend/tests/snapshots/` — fora do prefixo, como `dev/snapshots/`.
> Separar o rebaseline do código de produção aqui é **disciplina, não gate**, e a
> frase anterior fez três PRs desta lane (#1769, #1780, #1782) declararem no corpo
> "commit isolado (hook G-c)" como se um gate tivesse enforçado. A separação foi
> feita e está certa; a **atribuição ao hook era falsa**.
> Estender o prefixo é trabalho desta lane — ela é dona assinada de `dev/golden_diff.py`
> (§abaixo) —, mas é **arquivo diferente** (`check_golden_rebaseline_isolation.py`),
> então a rota escrita na [[A40.l89]] (*"estender o prefixo é da [[A40.l80]], dona
> assinada do `golden_diff.py`"*) encadeia dois arquivos distintos. Confirme a
> titularidade antes de pegar. Se algum DTO mudar,
`make update-openapi-snapshot`. Se o manifest do parecer mudar, bump de
`PROMPT_VERSION`.

## Ao abrir a ADR

**Nunca reserve ID.** Aloque na escrita (`ls docs/adr/ | tail -1`) — citar
"ADR-NNN" em prosa para segurar número não funciona e o próximo agente rouba.
Declare supersedência bidirecional se emendar [[ADR-335]] ou [[ADR-340]].

## Rastro

Achados do §r8 de [[PIPELINE-REVIEWS-active]] (run `d0f6260a`, 2026-08-24),
cluster "Denominador amputado". Cru e números de instância em
`storage/<uuid>/reviews/20260824-2235-d0f6260a/` (off-git).
