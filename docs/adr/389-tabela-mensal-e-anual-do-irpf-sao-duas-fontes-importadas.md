---
id: ADR-389
type: adr
title: "As tabelas mensal e anual do IRPF são duas fontes importadas, não duas escalas de uma"
status: Proposto
phase: A40.l56
date: "2026-08-15"
relates_to:
  - "[[ADR-090]]"
  - "[[ADR-135]]"
  - "[[ADR-375]]"
  - "[[ADR-210]]"
supersedes: []
superseded_by: []
aliases: ["ADR 389", "ir_brackets_anual", "ir_brackets_mensal", "tabela progressiva IRPF"]
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/persistence
  - area/pipeline
  - area/financial-planning
  - phase/a40-l56
---

# ADR-389 — Tabela mensal e anual do IRPF são duas fontes importadas

> Origem: co-design da [[A40.l56]] em 2026-08-15 (`financial-planner` +
> `data-engineer`, divergência fechada por `senior-cto`). Emenda o contrato de
> `ir_brackets` da [[ADR-135]].

## Contexto

`fiscal_parameters.ir_brackets` guarda `upper_brl_cents` em escala **anual** e
`deducao_brl_cents` em escala **mensal**. A migration `e1f2a3b4c5d6` declarou o
mismatch como FLAG e delegou ao "primeiro consumidor" escolher entre reescalar
parcelas ou reescalar faixas.

**Nenhuma das duas opções resolve.** Medido em 2026-08-15: usar a parcela crua
numa fórmula anual erra R$ 4.195,84 sobre base de R$ 40.000; anualizando as
parcelas (×12) a tabela fica contínua a ≤ R$ 0,05 em três fronteiras e abre
degrau de **R$ 11,04** em R$ 26.963,20. A origem é `upper[0]` = R$ 26.963,20
contra `deducao[1] × 12 ÷ 0,075` = R$ 27.110,40 — dois vintages.

Segundo defeito, estrutural: o seed passa **uma única constante**
(`_IR_BRACKETS_PRE_LEI_15270`, `y3z4a5b6c7d8:69`) para 2024, 2025 e 2026. As
faixas de 2025 e 2026 são as de 2024.

## Decisão

### D1 — São duas tabelas, não duas escalas

A RFB publica a **progressiva mensal** (IRRF, antecipação na fonte) e a do
**Anexo IV da IN RFB 1.500/2014** (ajuste anual da DAA). Bases legais e atos de
publicação distintos. A anual **não é ×12 da mensal**, por dois motivos
independentes:

- **transição intra-anual:** em ano com MP no meio, a anual é a mistura
  ponderada por mês — AC2024: `2.112,00×1 + 2.259,20×11 = 26.963,20`;
  AC2025: `2.259,20×4 + 2.428,80×8 = 28.467,20`;
- **arredondamento:** AC2026 não teve transição e ainda assim `908,73 × 12 =
  10.904,76` contra os `10.904,66` publicados — a parcela anual é derivada por
  continuidade sobre os limites anuais, não por soma de parcelas mensais já
  arredondadas.

Logo `26.963,20 ÷ 12` não é "o mensal arredondado": é um número que a RFB nunca
publicou. Derivar uma da outra é exato aritmeticamente e **errado
juridicamente** — foi essa derivação que produziu o degrau de R$ 11,04.

### D2 — As duas são canônicas e importadas; `ir_brackets` morre

A row passa a ter `ir_brackets_anual` e `ir_brackets_mensal`, cada um verbatim
da publicação, **nenhum derivado do outro**, cada um com `source` e
`vigencia_ref` próprios dentro do JSON — `source` de row já provou ser
insuficiente: um único texto cobria 3 anos idênticos e errados.

A escala vai no **container**, não no leaf
(`ir_brackets_mensal.faixas[].upper_brl_cents`): repetir no leaf gagueja dentro
de um container que já desambigua. O que cumpre o precedente da [[A40.l2]]
("sufixo é identidade") é o nome antigo **não resolver** — leitor que diga
`ir_brackets` quebra no import, nunca recebe uma das duas em silêncio.

Cada consumidor passa a ler a tabela que a lei manda: `resolve_faixa_marginal`
sobre a anual (base da DAA), `compute_irrf_mensal` ([[A40.l37]]) sobre a mensal.
O conversor de escala deixa de existir — e conversor que não existe não erra.

### D3 — Três invariantes, nenhum afirmando igualdade entre as tabelas

- **(a) Continuidade intra-tabela**, cada uma independentemente, em toda
  fronteira, tolerância **R$ 0,01**: `upper_i × aliq_{i+1} − ded_{i+1} ==
  upper_i × aliq_i − ded_i`. É identidade algébrica de como a RFB deriva a
  parcela; o resíduo é só arredondamento a cents. R$ 0,05 é 10× o ruído medido e
  deixaria passar erro de um centavo em parcela.
- **(b) Congruência estrutural entre as duas:** mesma cardinalidade, mesma
  sequência de `aliquota_pct`, terminal na mesma posição, `upper` estritamente
  crescente, `ded` não-decrescente. É o que a RFB garante — mesma estrutura de
  faixas em duas periodicidades — e pega tabela copiada, faixa faltando e
  escalas trocadas.
- **(c) Divergência ×12 declarada, não tolerada:** se `|anual − 12 × mensal| >
  R$ 1,00` numa faixa, a row exige `motivo` explícito (`"transição MP X"`,
  `"arredondamento"`). Divergência **sem motivo falha**. O drift deixa de ser
  inevitabilidade estrutural e vira erro de import nomeado.

### D4 — Completude do regime é dado, não `if` no consumidor

A row de AC2026 recebe as tabelas progressivas corretas — elas existem e estão
certas **enquanto passo progressivo** — mais `regime_completo: false` e
`componentes_ausentes: ["redutor_lei_15270", "irpfm"]`.

A Lei 15.270/2025 (vigente para rendimentos pagos a partir de 01/01/2026) não
alterou faixas nem parcelas; criou um **redutor** aplicado depois do imposto da
tabela e função do rendimento **bruto** (não da base de cálculo), e a tributação
mínima de altas rendas. Nenhum dos dois é faixa, e ambos quebram a diferencial
ingênua `IR(base) − IR(base − aporte)` do D5 da [[ADR-375]]: quem tem tributável
anual ≤ R$ 60.000 já paga zero, e acima de R$ 600.000 o mínimo absorve a
redução. Modelá-los é lane e ADR próprias.

O D5 recusa **lendo a row**, nunca por `if year >= 2026` — o seam fica no dado,
onde a próxima mudança de lei já encontra o lugar dela.

### D5 — Cache é payload-shaped; o namespace versiona junto

`fiscal_cache.py` serializa o payload inteiro sob `fiscal:y={year}` com TTL 1h.
Renomear campo muda o shape, e leitor pós-deploy contra cache pré-deploy recebe
faixas vazias por até uma hora — que hoje levanta `TabelaProgressivaInvalida` ou
cai no `aliquota_fallback = 7,5%`.

A chave passa a `fiscal:v2:y={year}`, com a versão como constante de módulo
ligada ao shape, mais `schema_version` no payload e mismatch tratado como miss.
O argumento é histórico, não teórico: a `e1f2a3b4c5d6` **já escreveu**
"invalidar `fiscal:y=...` no Redis de produção" num comentário em 2026-05, e
nada aconteceu em 3 meses. Runbook é promessa; chave em código é estrutura.

## Alternativas rejeitadas

- **Reescalar parcelas para anual (opção (a) da FLAG):** produz o degrau de
  R$ 11,04 — é a derivação que causou o defeito.
- **Reescalar faixas para mensal (opção (b) da FLAG):** mesma classe na direção
  oposta; perde a anual publicada, que nenhum ×12 reconstrói.
- **Guardar só uma e derivar a outra:** ambas as direções são juridicamente
  lossy, porque são duas publicações independentes.
- **Nova vigência em vez de UPDATE in-place:** o eixo `effective_from` modela
  "a lei mudou", não "nosso seed estava errado"; e `get_for_period` levanta com
  ≥2 rows no mesmo período.
- **CHECK constraint sobre o array JSON:** não é expressável portavelmente, e
  gate que roda em Postgres e não no SQLite dos testes não roda onde o dev está.
- **JSON Schema em `config/schemas/`:** aquele diretório valida artefato de
  pipeline; não há hook no read path de `fiscal_parameters`.

## Consequências

- Manutenção anual dobra — duas tabelas por ano-calendário. Aceitável em 3 rows
  globais.
- `ir_brackets` some do código não-migration; o rename tem raio pequeno
  (`fiscal_parsers.py`, `config.py`, `previdencia_analyzer.py`, model, 3 testes).
- `fiscal_parsers.py:52` (`int(raw.get("deducao_brl_cents") or 0)`) passa a
  **levantar** em chave ausente: é a falha-aberto que tornou os zeros do seed
  original invisíveis por um ano.
- O desbloqueio do D5 à [[A40.l34]] sai **qualificado** — `AC ≤ 2025` liberado,
  `AC ≥ 2026` retido pelo `regime_completo`.

## Não-objetivos

- Modelar o redutor da Lei 15.270/2025 ou o IRPFM.
- Resolver vigência **intra-anual** (row por período com leitor que resolve por
  data). Hoje o leitor recusa ≥2 rows no mesmo período; a condição de retomada é
  a primeira MP que altere a tabela no meio do ano-calendário.
- Semear AC2027: a tabela não está publicada, e row ausente é sinal correto —
  row copiada é o bug que esta ADR conserta.

## Critério de aceite

- As 3 rows têm as duas tabelas, **distintas entre si por ano**, com `source` e
  `vigencia_ref` citando publicação e data de consulta.
- Os três invariantes de D3 rodam em todo PR sobre a constante da migration, e
  um espelho marcado `migration` ([[ADR-210]]) valida as rows do DB Alembic.
- Teste que prova que os 3 anos **diferem entre si** — o seed atual passaria
  calado nos demais se copiasse uma tabela correta três vezes.
- `rg 'ir_brackets\b'` limpo fora de `backend/alembic/versions/`.
- Bump de `fiscal:v2:` no mesmo PR do rename; se separados, o rename espera o
  bump, nunca o contrário.
- ≥1 golden atravessa `from_fiscal_parameters`, e a mutação de call-site
  `from_fiscal_parameters → from_fiscal` o derruba.
