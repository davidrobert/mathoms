---
id: A40.l5
type: lane
title: "Codegen do view-model + gate de contrato: mata a classe reader-lê-chave-que-ninguém-emite"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l5-contrato-view-model-gate
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/frontend
  - area/dx
---

# A40.l5 — `contrato-view-model-gate` (alavanca estrutural)

> 🔓 **Liberada em 2026-08-07 (decisão do dono).** `planned` → `open`. Não houve
> condição técnica a satisfazer — `depends_on` sempre foi vazio; o que faltava era
> a liberação por-lane que o §Predicado do [`_README`](../_README.md) exige. O
> motivo de liberar agora: esta lane é a **única dona da KR-A** e a porta da
> [[A40.l6]] (KR-D). Encerrar a sprint pelo gate de saída com as duas represadas
> entregaria 2 de 5 KRs jamais tocados — não por escolha, por esquecimento.
>
> ## Decisão do dono, 2026-08-07 — o gate de consumo NÃO alarga o filtro de CI
>
> Fecha o herdado da [[A40.l10]] abaixo (§"o gate cross-stack não dispara"), que
> era a única pendência real desta lane. **Medido em `652aa028`**, e a medição
> corrige a premissa: o buraco é **menor** do que o registro herdado sugere,
> porque os dois gates desta lane rodam sob filtros diferentes.
>
> | Gate | Job | Condição de disparo | Cobre a l5? |
> |---|---|---|---|
> | `dev/check_view_model_contract.py` (sincronia) | *Lint* | `any_code: '**'` + step `pre-commit (all files)` | ✅ **todo PR**, qualquer path |
> | `tsc --noEmit` (consumo) | *Frontend checks* | `filter.frontend` — `frontend/**`, `design-tokens/**`, `config/report_layout.yaml`, o workflow | ❌ escapa em diff de `config/schemas/**` e `tests/fixtures/**` |
>
> **Decisão: o gate de sincronia é o mecanismo que sustenta a KR-A; o `tsc` é
> reforço.** O filtro **não** é alargado. Alargá-lo faria *Frontend checks* rodar
> em todo diff de fixture do pipeline — custo recorrente de Actions (a A40 já tem
> histórico de orçamento estourado por contagem de jobs) para fechar um caso que o
> hook de pre-commit já pega em `--all-files`.
>
> **Consequência que o PR tem de honrar:** `check_view_model_contract.py` nasce
> **hook de pre-commit**, não teste sob `frontend/`. Se nascer como teste do
> Vitest ou do `frontend-checks`, herda o filtro e a decisão acima vira falsa — a
> lane que existe para matar "gate mede produção, não consumo" teria criado outra
> instância dela.
>
> **Não fechado por esta decisão:** o par produtor↔consumidor de fixture cross-stack
> (`tests/fixtures/narrativas/**` lido de dentro de `frontend/`) segue com CI que
> não re-dispara. Continua gatilho `sre-devops`, e continua **não roteado** —
> registrado aqui para não ser relido como resolvido.

## Problema

Quatro achados independentes são **a mesma classe**: consumidor lê chave que o
payload não emite, **sem erro**, caindo em default/fallback silencioso.

| Achado | Consumidor lê | Payload emite |
|---|---|---|
| RV3-09 | `meses_cobertura` | `reserva_emergencia.cobertura_meses` |
| RV3-26 | `goals.trs_pct` | `goals.if_trs` (cai em default **hardcoded**) |
| RV3-12 | `d.valor` / `d.taxa` | `saldo_devedor` / `taxa_juros` |
| RV3-17 | `total_pontuais` | `total_pontuais_janela` existe e não é lido |

> ## ⚠️ Inventário remedido em 2026-08-08 — a tabela acima estava vencida
>
> Antes de codar, remedi os quatro (regra "achado com medição citada se
> remede"). **Dois dos quatro não eram o que a tabela diz**, e a diferença muda
> o desenho do gate — não só o numerador da KR-A:
>
> | Achado | Estado real medido em 2026-08-08 | Consequência |
> |---|---|---|
> | **RV3-09** | ✅ **Real, e pior que "leitura órfã".** O leitor é `pipeline/domain/services/suggestion_rules.py:123` — **Python, não frontend**. `reserva.get("meses_cobertura")` → sempre `None` → `if meses is None: return None`: `rule_reserva_insuficiente` **nunca disparou para nenhum workspace**. Não é campo mal renderizado, é regra de segurança morta | codegen TS **não alcança** este caso |
> | **RV3-26** | ❌ **Já estava corrigido.** `S7IndependenciaSection.tsx:266-267` lê a chave certa e traz o comentário explicando que `goals.trs_pct` não existe e que o `?? 5.0` anterior mascarava | sai do numerador |
> | **RV3-12** | ✅ **Real.** `EndividamentoCard.tsx:77,79` lia `d.valor`/`d.taxa` | tabela de dívidas publicava valor vazio + taxa `"—"` sempre |
> | **RV3-17** | ❌ **Não é leitura órfã.** `fluxoJanela.ts:158` lê `total_pontuais` **de propósito** (D6: base full-period), documentado no próprio arquivo. O que existe é o **inverso** — `total_pontuais_janela` é emitido e não tem leitor —, e isso é escopo da [[A40.l15]] | sai daqui |
>
> **KR-A não parte de 5.** Partia de **2** leituras órfãs reais no momento da
> medição, e as duas foram fechadas (ver §Entregue). Registrar isto importa: a
> próxima lane que citar "5 → 0" estaria contando dois itens que não existem.
>
> ### O codegen especificado no §Escopo não é construível hoje
>
> A l5 propõe gerar `report-analysis.ts` **a partir do schema E5**. Medido:
> **10 dos 35 blocos de topo** de `config/schemas/e5_analysis.schema.json` são
> `{"type": "object"}` **sem `properties`** — entre eles `reserva_emergencia`,
> `goals` e `consumo_consciente`, que são exatamente onde os achados moram.
> Gerar desse schema produziria `reserva_emergencia?: Record<string, unknown>`,
> e o `tsc` continuaria aceitando `d.valor` em silêncio: o gate nasceria
> **verde e inútil**, que é a classe que esta lane existe para matar.
>
> **Pré-requisito, portanto: tipar esses blocos no schema E5 primeiro**
> (contrato entre stages ⇒ gatilho `data-engineer`), e só então o codegen tem
> de onde gerar. Deferido com dono, não silenciado.
>
> ✅ **Co-design rodou em 2026-08-10** — ver §Co-design abaixo. **"10" está
> errado nos dois sentidos**: `section_summaries` já é tipado, mas há **4
> arrays sem `items`** que eu não contei e que desligam o `tsc` do mesmo jeito.
> Superfície real: **11 blocos**. E o gate precisa de uma **terceira perna**
> (`schema × produtor`), senão sincroniza os dois lados errados.
>
> ### O que realmente desligava o `tsc` neste bloco
>
> Não era "o arquivo é escrito à mão" — era **`[key: string]: unknown`** dentro
> de `dividas[]`. Com a index signature, `d.valor` compila mesmo com o tipo
> correto ao lado. São 4 index signatures em `report-analysis.ts`; a de
> `dividas[]` saiu nesta entrega. As outras 3 seguem abertas e são o alvo
> natural da continuação desta lane.

Dispersos, cada um recebe um fix pontual e **o quinto acontece na próxima
release**. `frontend/src/types/report-analysis.ts` é escrito à mão — é a exceção
que escapou ao [[ADR-076]], que já decidiu que codegen é a fonte de verdade para
contratos API↔UI.

RV3-26 tem um agravante que reabre item já fechado: o "aceite cumprido" do RV3-31
(duas taxas de retirada) foi verificado **contra a constante hardcoded**, não
contra o payload. Os números coincidem **por acidente** (ver §Decisões nº 7 do
sprint).

## Escopo

- `dev/codegen_report_analysis.py` (novo, padrão de `dev/codegen_report_layout.py`)
  gerando `frontend/src/generated/report-analysis.ts` a partir do DTO/schema E5.
- Substituir o `types/report-analysis.ts` manual pelo gerado.
- `dev/check_view_model_contract.py` (novo, pre-commit + CI) cruzando schema E5 ×
  tipos do frontend × readers Python.
- Corrigir os 4 readers como **consequência mecânica** do gate.
- **Vem antes** das lanes de correção individual de contrato ([[A40.l6]]).

## Critério de aceite

- KR-A: leituras órfãs conhecidas 5 → 0.
- **Gate de sincronia** no padrão `make update-openapi-snapshot`: regenerar e
  falhar se o commitado divergir.
- **Gate de consumo:** `tsc --noEmit` passa a falhar em leitura de campo não
  declarado — `d.valor` vira erro de compilação, e `frontend-checks` (que já roda
  `tsc --noEmit` em PR) bloqueia.
- Fixtures: **(1)** chave no schema sem consumidor ⇒ falha; **(2)** renomear
  `cobertura_meses`→`meses_cobertura` só no consumidor ⇒ falha (reproduz RV3-09
  exatamente); **(3)** allowlist com razão escrita ⇒ passa.
- RV3-31 re-verificado **contra o payload**, não contra a constante.

## Escopo herdado da [[A40.l4]]

A l4 **shipou** (`6c5d9814`, #1139) e roteou 5 residuais medidos para esta lane,
na coluna Dono de sua §Residual medido. Até este registro (2026-08-05) o handoff
existia no emissor e no §Inventário do [[A40]] —
`rg -n 'autonomia_financeira|ADR-148|renda_passiva_estimada' docs/sprint/A40/`
não batia neste arquivo. Handoff só existe quando a lane de destino o registra
(o par l3→l15 já pratica o padrão):

| Herdado | O que foi medido na l4 |
|---|---|
| ~~**`s1` publica "residência própria de R$ 0,00"**~~ | **Movido para [[A40.l6]]** em 2026-08-05 (decisão do dono, §Pendência nº 6 "Relacionado" do [[A40]]; registrado em [[ADR-356]] §Emenda 2026-08-05): é classe zero-como-valor (RV3-27), o arquivo é `summaries_narrator.py` (pipeline) e a regra já está decidida na §D7 da ADR-356 — não é leitura órfã nem contrato de frontend |
| **Sufixo de changelog da [[ADR-148]] não renderiza em seção nenhuma** | `get_report_data.py:78` usa `SnapshotChangelogConfig()` default, cujo `sections_to_compare` (`M_PL`, `M_TAXA_POUPANCA`, `M_RESERVA_MESES`, `M_AUVP_DESVIO`) não contém nenhum id de seção do layout, e o casamento é por `section_id`. A composição decidida na §D10 é contrato, não preservação de comportamento visível |
| **C11 — `ratios.autonomia_financeira_meses` = 16,72 sem consumidor** | Runway canônico ([[ADR-335]]) calculado e nunca renderizado; o alias colide de nome com cobertura da reserva. É campo do view-model, não de narrativa — nenhum dos 7 destinos entregues o cita |
| **C36 — blocos que não movem decisão** | A parte narrativa (duplicação no empty state da S9) foi corrigida na l4. O que sobra são **cards**: orçamento 44m, premissas 10/10 indisponíveis, checklist de sucessão todo negativo |
| **`renda_passiva_estimada_4pct` cristaliza "4" no nome do campo** | O SWR 4% e o yield-alvo 5% são conceitos distintos sob [[ADR-191]] §Emenda FP-03 e **não se harmonizam**. Um número no nome do campo trava a taxa no contrato — é exatamente o tipo de acoplamento que o codegen desta lane deveria expor |

Os 4 restantes entram no numerador de "leituras órfãs" **se e somente se** o gate
os classificar como tal (o do changelog foi roteado para
[[PLAN-snapshot-changelog-v3]] §Residual W3 em 2026-08-05 — era resíduo daquele
plano). `renda_passiva_estimada_4pct` provavelmente não é órfão (tem consumidor);
é defeito de **contrato**, que é o objeto desta lane. Não presuma que "5 → 0" já
os cobre.

## Escopo herdado da [[A40.l10]] — o gate cross-stack não dispara

Registrado aqui em 2026-08-05 **pelo destino**, na convenção que esta lane já
declara acima. A l10 mediu, ao regravar a fixture de entrega:

| Herdado | O que foi medido na l10 |
|---|---|
| **Mudança na fixture compartilhada Py↔TS não dispara o job que a consome** | `frontend/tests/components/report/sectionSummaryDelivery.test.tsx` lê `../../../../tests/fixtures/narrativas/e5n_delivery.json`, **fora** de `frontend/`. O filtro `filter.frontend` (`.github/workflows/ci.yml`) casa `frontend/**`, `design-tokens/**`, `config/report_layout.yaml` e o workflow — **não** `tests/fixtures/narrativas/**`. Medido: *Frontend checks* saiu `skipping` num PR que regravou a fixture 2×. Quebrar o contrato cross-stack deixaria o CI **verde** |

É a mesma classe desta lane — par produtor↔consumidor existente cujo gate não
fecha —, só que na camada de **disparo** em vez da de contrato. O `tsc --noEmit`
que a l5 quer usar como gate de consumo tem o mesmo problema: só roda quando o
filtro deixa. **Não corrigido na l10 por custo**: acrescentar o path faz
*Frontend checks* rodar em todo diff de fixture do pipeline, e a A40 tem histórico
de orçamento de Actions estourado por contagem de jobs — é decisão com gatilho
`sre-devops`, não carona de PR de narrativa.

## ✅ Parcial entregue em 2026-08-08 — PR #1336 (`845a4041`)

### As 2 leituras órfãs reais, com o gate de consumo ligado

Fecha a metade da lane que era construível sem tocar o schema E5. O codegen
segue aberto pelo pré-requisito medido acima.

**RV3-09 — regra de segurança morta, revivida.** `suggestion_rules.py` passou a
ler `cobertura_meses`. O que sustentava o defeito não era falta de teste: os
três testes de reserva **passavam**, porque a fixture escrita à mão repetia a
mesma crença errada do código. Por isso o teste novo é alimentado pelo
**produtor** — o bloco `reserva_emergencia` do snapshot de dogfood — e não por
dict literal. Prova de mutação: voltar a chave errada derruba **7** testes;
antes derrubava **0**.

**RV3-12 — tabela de dívidas volta a mostrar número.** `EndividamentoCard` lê
`saldo_devedor`/`taxa_juros`, e o tipo passou a espelhar
`e5_analysis.schema.json` **sem** a index signature. Isso liga o *gate de
consumo* que o §Critério de aceite pede, com as duas fixturas exigidas:

| Mutação | Antes | Agora |
|---|---|---|
| card volta a ler `d.valor` | compila | ❌ `TS2339` |
| renomear a chave só no **tipo** (fixture (2) do critério) | compila | ❌ `TS2339` |

**Fixtures E2E estavam ensinando o contrato errado.** `degraded.json`,
`large-values.json` e `long-strings.json` traziam `valor`/`taxa` — o formato
que produtor nenhum emite. Eram elas que faziam o E2E renderizar valores e o
defeito parecer inexistente (o payload real, no snapshot de dogfood, sempre
teve `saldo_devedor`/`taxa_juros`). Corrigidas para o formato do produtor.

**Não entrou:** codegen + gate de sincronia (pré-requisito de schema acima),
as outras 3 index signatures, e a re-verificação do RV3-31 contra o payload.

## 📐 Co-design `data-engineer` — 2026-08-10 (decisão, sem código)

O §Parcial de 2026-08-08 deferiu "tipar os blocos do schema E5 primeiro
(gatilho `data-engineer`)". O co-design rodou. **Corrigiu a medição que a
própria lane registrou** e mudou o desenho em três pontos. Nada foi
implementado nesta data — isto é a decisão, e a ordem de trabalho abaixo é o
que a retomada executa.

### A contagem "10 blocos opacos" está errada nos dois sentidos

| | |
|---|---|
| `section_summaries` **já é tipado** | tem `patternProperties` + `additionalProperties: false` ⇒ gera `Record<string,string>` correto. Sai da fila |
| `previdencia_pgbl` **não tem contrato** | a `description` aponta ADR-277/305 em **prosa**, e o codegen não lê prosa. Eu havia contado como "tem contrato" — refutado |
| `tarefas_status` sai da fila cara | dogfood mostra `{"1": str, "2": str}`; produtor é `build_default_tarefas_status(...) -> dict[str,str]`. É 1 linha de `patternProperties` |
| **subcontei**: 4 arrays sem `items` | `pontos_fortes`, `tarefas`, `alertas`, `diagnostico_comportamental` geram `unknown[]`, que desliga o `tsc` **exatamente como** `Record<string, unknown>` |

**Superfície real: 11 blocos** (7 campo-a-campo + 4 arrays), mais 2 linhas
baratas. O número final "7 campo-a-campo" coincidiu com meu palpite; a
**composição** não, e é ela que dimensiona o trabalho.

### Três correções de desenho

1. **O snapshot de dogfood não pode ser fonte de tipo escalar.** `_normalize`
   em `test_report_view_model_snapshot.py` converte monetário → cents `int` e
   float não-monetário → **string quantizada**. `cobertura_meses: "5.5"` no
   snapshot é `5.5` **float** no wire. Tipar lendo o snapshot escreveria
   `type: "string"` onde é `number` — criando a mesma classe desta lane, na
   dimensão **tipo** em vez de **nome**. O snapshot vale para presença de
   chave, nulabilidade e container; **não** para tipo.
2. **O gate precisa de uma TERCEIRA perna.** `schema × TS` sincroniza os dois
   lados errados se o schema for transcrito do consumidor — e a fixture (2) do
   §Critério de aceite passaria verde. É literalmente o que já mordeu esta lane
   (os 3 testes de reserva passavam porque a fixture repetia a crença errada do
   código). A perna que falta é **`schema × produtor`**, via
   `tests/test_e5_golden_execution.py` sob `MATHOMS_PIPELINE_SCHEMA_MODE=strict`.
3. **"Substituir o `types/report-analysis.ts` manual pelo gerado" é
   infactível** — ~40 exports, e boa parte (`ScoreFullData`, `DashboardData`,
   `AporteItem`…) é **UI-derived**, produzida pelos adapters de
   `components/report/utils/`, sem schema que a descreva. Tentar isso
   literalmente termina reintroduzindo index signature "pra caber". **Decisão:
   dois arquivos** — `generated/report-analysis.ts` (espelho 1:1, zero index
   signature) + o manual encolhido para os tipos de UI.

### Política, já decidida dentro do próprio schema

`$defs.PontoUrgente` traz a decisão com medição citada (#1243): **`required: []`
+ `additionalProperties: false` por bloco**. Artefato antigo em
`pipeline_artifacts` não é revalidado na leitura, então `required` contradiz a
tolerância do leitor. Divergir disso criaria um segundo padrão no mesmo arquivo.

**`additionalProperties` no topo fica `true`** — o payload E5 tem mais de um
escritor (`generate_narratives.py` regrava mergeando), e fechar sem enumerar
todos é verde no dogfood e warn-storm em produção. **Mas o codegen nunca emite
index signature**, independentemente disso: `additionalProperties: true`
significa *"outro stage pode adicionar chave"*, não *"o consumidor pode ler
qualquer coisa"*. Traduzir `true → [key: string]: unknown` reintroduziria o
defeito que o #1336 matou em `dividas[]`.

### Ponteiro podre encontrado

A `description` do topo do schema diz que o flip `warn → strict` é "W6-T01 do
PLATFORM_REVIEW_PLAN.md". Aquele plano foi **arquivado** em 2026-07-08 e o
W6-T01 fechou pela [[A40.l5]]… não: pela A23.l2, **com escopo diferente**
(rebaseline de goldens). **O flip está sem dono hoje.**

### §Deferimento datado — ordem de trabalho, dono: esta lane

Risco de quebrar run de produção é **~zero em PR0–PR4** (modo `warn`; pior caso
é log de drift). O risco aparece só no PR5 — que é o argumento para não juntá-lo.

| | O que faz | Por que nesta ordem |
|---|---|---|
| **PR0** | Inventário: carrega os E5 disponíveis e reporta, por bloco, chaves observadas + tipo Python **antes** da normalização + taxa de presença | Sem isso o aperto é redação, e a correção nº 1 acontece. Se só o dogfood estiver disponível, **declarar como limite** — amostra única não é medição |
| **PR1** | `tarefas_status` → `patternProperties`; `protecao_patrimonial` → `$ref` externo; os 4 arrays ganham `items` | Aditivo, nenhum consumidor muda |
| **PR2** | `consumo_consciente` (o contrato já existe em `@dataclass`), `reserva_emergencia`, `goals` | `goals` por último: `_enrich_goals_with_passive_income` adiciona 7 chaves — tipar pelo input produz contrato incompleto |
| **PR3** | `dev/codegen_report_analysis.py` + gate de sincronia (pre-commit) + gate de opacidade | Só agora o codegen tem de onde gerar |
| **PR4** | `equilibrio_cerbasi`, `orcamento_prospectivo`, `previdencia_pgbl`, `programa_milhas` | `programa_milhas` é `{}` no dogfood: se PR0 confirmar em 100% dos runs, **não tipe** — roteie como candidato a deleção (classe [[ADR-364]]) |
| **PR5** | Proposta `warn → strict`, com o drift medido em mãos + re-adoção do flip órfão | **Outra lane.** ADR própria + gatilho `sre-devops` (blast radius = run de cliente) |

**Marcador de opacidade com polaridade corrigida:** `x-codegen: {opaque: true,
reason, owner}` com razão e dono **obrigatórios**; inválido em bloco que tenha
leitor TS; e **contador monotônico decrescente** (padrão de
`dev/check_code_style_regression.py`), para que opacidade seja dívida com
trajetória em vez de allowlist sem prazo — allowlist falha aberta.

## Guarda anti-regressão

O gate **é** a guarda — única lane cujo entregável principal é impedir a classe
inteira, não corrigir instâncias. Removido o gate, a fixture (2) volta a verde e o
defeito retorna silencioso.
