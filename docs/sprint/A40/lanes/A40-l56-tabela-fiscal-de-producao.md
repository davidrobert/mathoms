---
id: A40.l56
type: lane
title: "A tabela fiscal de produção: a row é internamente inconsistente e nenhum golden a atravessa"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l56-tabela-fiscal-de-producao
owner: data-engineer
adrs:
  - "[[ADR-375]]"
  - "[[ADR-135]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/db
---

# A40.l56 — `tabela-fiscal-de-producao`

> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Nasceu `l50` e foi renumerada no mesmo dia: o #1409 tomou o id em
> paralelo — instância viva da classe que a [[A40.l59]] fecha. Origem: co-design e execução do PR1/PR2 da [[A40.l34]] (§Emenda da
> [[ADR-375]]). Dono: `data-engineer` — os dois itens moram no contrato de
> `fiscal_parameters` e no substrato golden, o mesmo especialista fecha ambos.
> Prioridade herdada da severidade na origem; o `product-manager` repriorisa no
> planejamento se discordar.

## Problema

Dois achados medidos em 2026-08-11/12, sobre o mesmo objeto — a tabela
progressiva de IR que **produção** consome ([[ADR-135]]):

**1. A row de `fiscal_parameters` é internamente inconsistente, e isso bloqueia
a [[ADR-375]] D5.** `deducao_brl_cents` guarda a parcela a deduzir **mensal**
contra faixas **anuais** — mismatch auto-declarado como FLAG na migration
`e1f2a3b4c5d6` (linhas 28-37: *"o primeiro consumidor decide entre (a) reescalar
parcelas para anual ou (b) reescalar brackets para mensal"*). Medido:

- Usar a parcela crua numa fórmula anual erra **R$ 4.195,84** numa base de
  R$ 40.000/ano (faixa de 15%).
- **E o ×12 não fecha**: anualizando, a tabela fica contínua a ≤ R$ 0,05 em três
  fronteiras e abre degrau de **R$ 11,04** em R$ 26.963,20. `upper_brl_cents[0]`
  (R$ 26.963,20) e `deducao_brl_cents[1]` (anualizada ÷ 0,075 = R$ 27.110,40)
  vêm de **vintages diferentes** — nenhuma das duas opções da FLAG resolve.

A economia diferencial `IR(base) − IR(base − aporte)` (D5) **não é
implementável** antes de a row ser reconciliada. Foi por isso que o PR2 da l34
parou na ausência, sem publicar a diferencial.

**2. Nenhum teste de golden atravessa o construtor de produção.**
`PrevidenciaConfig.from_fiscal_parameters` só roda quando `ctx.config_store`
existe ([`analyze_finances.py:2191`](../../../../scripts/analyze_finances.py) e
`:2237`) — e em **todo** caminho de teste ele é `None`. O substrato golden
exercita `from_fiscal` (dict legado) via `write_e5_config(irpf_faixas=...)`. O
falsy-zero do PR1 (#1383) foi corrigido **às cegas do golden**: só unit test
cobre o construtor que produção usa.

## Escopo

1. **Decidir o vintage oficial** da tabela (faixas + parcelas do mesmo
   ano-calendário) — validação de valores é gatilho de `financial-planner`;
   forma da migration é de `data-engineer`.
2. Migration corretiva sobre os 3 anos seedados (2024-2026), com a decisão da
   FLAG registrada onde a FLAG mora.
3. **Teste de continuidade da tabela**: `IR(limite)` pela faixa de baixo ==
   `IR(limite)` pela de cima, a ≤ R$ 0,05, em **toda** fronteira — o teste que
   teria acusado o mismatch no seed original.
4. Fake de `config_store` no substrato golden (ou fixture equivalente) para
   **≥1 execução golden atravessar `from_fiscal_parameters`** com `ir_brackets`
   reais.
5. Declarar o desbloqueio do D5 à [[A40.l34]] (nota datada na [[ADR-375]]).

## Critério de aceite

- Continuidade provada em toda fronteira da tabela vigente, por teste que roda
  em todo PR.
- **Prova por mutação no construtor de produção**: reintroduzir o falsy-zero em
  `from_fiscal_parameters` derruba ≥1 teste que passa pelo caminho golden — hoje
  derruba **zero** goldens.
- A [[ADR-375]] ganha a nota datada de desbloqueio do D5, e a [[A40.l34]] é
  citada como consumidora.

## Colisão declarada

Nenhuma com o PR3 da [[A40.l34]] (hospedagem/frontend). A migration toca
`backend/alembic/versions/` — verificar head antes de abrir.

## Decisão do escopo item 1 — 2026-08-15

> Co-design `financial-planner` + `data-engineer`; divergência de escala fechada
> por `senior-cto` (protocolo anti-loop). Decisão canônica em [[ADR-389]]
> `Proposto`, que emenda a [[ADR-135]].

**A pergunta estava errada.** Não são duas escalas de um objeto: a RFB publica
**duas tabelas** — progressiva mensal (IRRF na fonte) e Anexo IV da IN 1.500/2014
(ajuste anual da DAA) —, e a anual **não é ×12 da mensal**. Em ano de transição
ela é mistura ponderada por mês (AC2024: `2.112,00×1 + 2.259,20×11 = 26.963,20`);
e mesmo em ano limpo diverge por arredondamento (AC2026: `908,73×12 = 10.904,76`
vs `10.904,66` publicado). As duas opções da FLAG estavam erradas porque ambas
derivam — e foi a derivação que abriu o degrau de R$ 11,04.

**Segundo defeito, não previsto pela lane:** o seed passa uma única constante
(`_IR_BRACKETS_PRE_LEI_15270`, `y3z4a5b6c7d8:69`) para os 3 anos. As faixas de
2025 e 2026 são as de 2024. Não é só escala — são valores errados.

### Correções ao escopo escrito

- **Item 2** cresce: a migration corretiva reescreve **duas** tabelas por ano
  (`ir_brackets_anual` + `ir_brackets_mensal`), com `source`/`vigencia_ref` por
  tabela, `regime_completo`/`componentes_ausentes` na row de 2026, e bump de
  `fiscal:v2:` no mesmo PR (o cache é payload-shaped; a `e1f2a3b4c5d6` já pediu
  invalidação manual em comentário e nada aconteceu por 3 meses).
- **Item 3** aperta: tolerância **R$ 0,01**, não R$ 0,05. Recomputadas as 12
  fronteiras dos 3 anos, o desvio máximo é R$ 0,005 — R$ 0,05 é 10× o ruído e
  deixaria passar erro de um centavo em parcela. Somam-se dois invariantes:
  congruência estrutural entre as duas tabelas, e divergência ×12 exigindo
  `motivo` declarado.
- **Item 5** sai **qualificado**: `AC ≤ 2025` desbloqueado; `AC ≥ 2026` segue
  retido. A Lei 15.270/2025 criou um redutor (função do rendimento **bruto**,
  não da base) e o IRPFM, e ambos quebram a diferencial ingênua do D5 — quem tem
  tributável anual ≤ R$ 60.000 já paga zero. Modelá-los é lane e ADR próprias. A
  recusa lê `regime_completo` na row, nunca `if year >= 2026`.

### O §Critério de aceite muda: a mutação do falsy-zero é insatisfazível

Medido: o falsy-zero (`if b.upper_brl_cents`) só morde faixa com `upper == 0`, e
**a tabela real não tem nenhuma** — só o bracket artificial de
`test_a72b_typed_inputs.py:70` a produz. Cumprir o critério ao pé da letra
exigiria semear tabela irreal no golden: mutação implausível, teste-fantasma.

A intenção do critério era provar que ≥1 golden atravessa
`from_fiscal_parameters`. A sonda passa a ser a **mutação de call-site**:

> Trocar `from_fiscal_parameters` por `from_fiscal` no call-site derruba ≥1 golden.

Ela é plausível (é o fallback vivo) e morde forte, porque `from_fiscal` zera
`deducao_brl_cents` incondicionalmente (`previdencia_analyzer.py:77`) —
reintroduz a mesma classe na tabela real. O falsy-zero **permanece coberto** por
unit test com fixture sintética: tabela irreal tem lugar, e o lugar é unit, não
golden.

Condições que autorizaram a troca, e que valem como regra para reescrever
critério de lane: (i) o original é condenado por **medição citada**, não por
dificuldade; (ii) o substituto cobre a **mesma classe**; (iii) o substituto é
**plausível**; (iv) a troca fica como nota datada com o número que a motivou.

## Proveniência: o que está verificado em fonte primária — 2026-08-15

> Fecha o gap nº 1 da síntese do fan-out ("nenhum agente leu ato normativo
> primário"). **Parcialmente.** O que segue distingue o que foi lido na fonte do
> que continua apoiado em portal — a distinção é o entregável, não um detalhe.

### Verificado em ato primário

**O Anexo VII é a tabela progressiva ANUAL.** Lido o PDF do repositório de normas
da RFB (`normas.receita.fazenda.gov.br/sijut2consulta/anexoOutros.action?idArquivoBinario=46090`),
título literal *"ANEXO VII — TABELAS PROGRESSIVAS ANUAIS"*, estruturado por
*"para o exercício de X, ano-calendário de Y"*. Corrige a [[ADR-389]], que citava
o Anexo IV (que é RRA). Anexo II é a mensal.

**Os tetos das faixas 2-4 estão congelados desde o ano-calendário 2016.** O mesmo
documento, item VI, traz `33.919,80 / 45.012,60 / 55.976,16` — idênticos aos de
2024-2026. Só o teto de isenção se move.

**A primeira fronteira não é exata em toda tabela publicada.** AC2016 publica
`22.847,76` / `1.713,58` contra produto exato `1.713,582`. Motivou afrouxar o
invariante para 1 centavo (#1473).

### NÃO verificado em ato primário — limitação declarada

O binário do Anexo VII acessível cobre até **AC2016**; a revisão consolidada
atual não é alcançável pelas vias tentadas (o `link.action` consolidado
redireciona, a notícia da RFB sobre a IN 2.299 responde "Conteúdo Restrito", e a
busca só devolve o mesmo binário antigo).

Portanto **os valores de 2024/2025/2026 não foram lidos no texto do ato**. O que
os sustenta: 3 apurações independentes + 2 lentes adversariais + aritmética
própria + a testemunha in-repo `IRRF_FAIXA_TOPO` (`cascata_calculator.py:47`,
gravada por outra lane sob a mesma MP) + um exemplo oficial da RFB que fecha ao
centavo em `908,73` e só nele. É evidência convergente forte, **não é o ato**.

### Consequência para a migration

- `vigencia_ref` cita o **cabeçalho da norma** (o que a [[ADR-389]] D2 pede:
  verbatim da publicação) e o **ato** (IN RFB 2.174/2024; IN RFB 2.299/2025),
  **sem número de anexo por ano** — a identidade do Anexo VII está verificada em
  geral, mas qual IN inseriu o item de cada ano não. Ausente é melhor que errado.
- `source` registra explicitamente `verificacao: "portal RFB + convergência;
  texto do ato não lido"` por row. A auditoria futura lê o nível de verificação
  no dado, não em prosa de PR.
- **Este é o único item da lane que fica owner-gated:** 3 anos × 5 faixas × 2
  tabelas viram imposto na tela. A conferência humana da tabela final antes do
  merge não é formalidade.

## Escopo item 4 — golden atravessa o construtor de produção (2026-08-15)

Antes desta lane, **zero** goldens passavam por `from_fiscal_parameters`:
`ctx.config_store` era `None` em todo caminho de teste e `analyze_finances` caía
em `from_fiscal` (dict legado). Por isso o falsy-zero do #1383 foi corrigido às
cegas do golden.

**Injeção opt-in.** `run_e3_e4_e5` ganha `config_store` kw-only com default
`None`. Injetar no substrato compartilhado trocaria o construtor em **todos** os
goldens de E5 e forçaria rebaseline geral; o default mantém os existentes no
caminho legado e deixa **um** golden novo exercitar o de produção.

**As tabelas do golden derivam da constante da migration**, via
`fiscal_store_do_seed` — não de literais no teste. Golden com execução real
sobre tabela fantasiada mede a fantasia.

**A fixture é dimensionada para a sonda morder.** `aliquota_fallback` do caminho
legado é 7,5% e a 2ª faixa da tabela real também: com base tributável na faixa
de 7,5% os dois caminhos devolvem o **mesmo** número e o golden passaria verde
sem medir nada. R$ 40.000/ano cai na faixa de 15% → **15,0% (DB) vs 7,5%
(legado)**. O ano vem de `date.today().year`, nunca literal — `{2026: fp}`
passaria hoje e viraria `KeyError` silencioso em 2027, engolido pelo
`except Exception` de `analyze_finances:2163`, devolvendo o golden ao caminho
legado sem falhar.

**Braço de controle explícito.** `test_caminho_legado_devolve_o_fallback` prova
que a mesma fixture NÃO produz 15,0% sem `config_store`. É ele que torna a sonda
falsificável: sem divergência nesta fixture, trocar o construtor não muda nada.

**Sonda de aceite, medida.** Trocar `from_fiscal_parameters` por `from_fiscal`
no call-site de `e5_analyzer_adapter` derruba **2 dos 3** testes — e o braço de
controle sobrevive, como deve, porque ele afirma o caminho legado.
