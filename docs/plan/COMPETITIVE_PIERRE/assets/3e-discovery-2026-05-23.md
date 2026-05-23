# Fase 3.E — Discovery output (2026-05-23)

> Artefato derivado do plano canônico [PLAN-competitive-pierre](../_README.md) §3 Fase 3 sub-fase 3.E (Financial Memories surface). Consolida output de 3 especialistas invocados em paralelo: `product-designer` (UX + mockups + decisões D1-D5), `financial-planner` (taxonomia + INV1-5 + gap arquitetural), `product-manager` (sprint placement + KRs).
>
> **Não é fonte de verdade canônica** — é referência de discovery. Decisões finais vivem nas ADRs Proposto (`goal-reserva-emergencia-schema`, `goal-meta-objetivo-schema`, `decision-source-column`, `financial-memories-surface`).

---

## 1. Taxonomia de domínio (financial-planner)

16 fatos em 7 categorias. Distinção primária: declarada (intenção do user) vs derivada (inferida do pipeline). Distinção secundária: casal vs individual.

| # | Fato canônico | Categoria | Origem default | Aggregate de origem | Revisão | Compartilhado-casal? |
|---|---|---|---|---|---|---|
| F1 | Idade e estágio de vida atual | Vida e família | Declarada | `family_members.idade` + derivada DOB | Anual / mudança de etapa | individual |
| F2 | Dependentes (filhos, idosos, pets relevantes) | Vida e família | Declarada | `family_members[]` com flags `dependente_irpf`, `idade` | Anual / nascimento-óbito | sim |
| F3 | Planejamento de filhos (intenção, horizonte) | Vida e família | Declarada | workspace settings (preferível a Goal próprio) | Anual | sim |
| F4 | Regime profissional dominante (CLT / PJ / híbrido / sócio) | Profissional e renda | Declarada | `family_members.regime_profissional` por adulto | Anual / mudança | individual por membro |
| F5 | Estabilidade da renda principal | Profissional e renda | Declarada | `family_members.renda.estabilidade` | Anual / mudança | individual |
| F6 | Tolerância de risco (perfil 1-5) | Patrimônio e risco | **Declarada** (questionário) | `Risk` aggregate ([[ADR-178]]) | Anual ou pós-evento >20% | individual (média ponderada do casal é derivada) |
| F7 | Horizonte de investimento principal | Patrimônio e risco | Declarada | `Goal.if.inputs.horizonte_anos` ou `Risk.horizonte_anos` | Anual | sim |
| F8 | Posição patrimonial líquida atual (PL = ativos − passivos) | Patrimônio e risco | **Derivada** | E5 `analise_financeira.patrimonio.liquido` | A cada relatório | sim |
| F9 | Alocação alvo (7 classes) e desvio atual | Patrimônio e risco | **Mista** — alvo declarado, atual derivada | `Goal` alocacao_alvo v2 ([[ADR-141]]) + E5 derived | Trimestral | sim |
| F10 | Dolarização alvo (% USD/exterior) | Patrimônio e risco | Declarada | `Goal` dolarizacao | Anual / evento cambial | sim |
| F11 | Reserva de emergência alvo (meses de despesa essencial) | Lifestyle e custo de vida | **Declarada com ancoragem metodológica obrigatória** | `Goal` reserva_emergencia (**proposto — não existe**) | Anual | sim |
| F12 | Independência financeira — renda passiva + horizonte | Metas estruturadas | Declarada (renda alvo + horizonte) + Derivada (patrimônio-alvo e aporte) | `Goal` if v2 | Anual | sim |
| F13 | Metas estruturadas (casa, educação, intercâmbio, aposentadoria do cônjuge) | Metas estruturadas | Declarada | `Goal` meta_objetivo (**proposto — não existe**) | Anual / atingida | sim |
| F14 | Regime IRPF + uso de PGBL/VGBL | Fiscal | Derivada com confirmação declarada | E5 `irpf_metadata` ([[ADR-157]]) | Anual (pós-declaração) | individual; agregado se conjunta |
| F15 | Estrutura de proteção (seguros vida/invalidez, plano de saúde longo) | Sucessão e proteção | Declarada | `Risk` aggregate §coverage ([[ADR-178]]) + life-insurance-coverage rules | Anual / mudança de etapa | sim |
| F16 | Plano sucessório explícito (testamento, holding, beneficiários) | Sucessão e proteção | Declarada | `Decision` aggregate ([[ADR-136]]) + workspace settings | Anual / evento familiar | sim |

**Anti-pilha:** custo de vida atual NÃO é fato declarado — é puramente derivado de E5 (média 12m), não pertence a memories sem duplicação suja. Aparece como leitura projetada complementar a F11.

---

## 2. Invariantes metodológicos (financial-planner)

Devem virar **testes de regressão**, não só doc — sem isso INV vira folclore.

| # | Invariante | Razão | Enforcement proposto |
|---|---|---|---|
| INV1 | Reserva de emergência sempre ancorada em fórmula | Valor solto vira wishful thinking; metodologia consagrada exige `meses_alvo × despesa_essencial` | Schema `Goal reserva_emergencia` exige `meses_alvo ∈ [3, 18]`, default 6. Pipeline calcula `despesa_essencial_mensal_brl` de E5. |
| INV2 | Tolerância de risco é declarada, nunca derivada de comportamento | Inferir de comportamento histórico é viés de recência; metodologia exige questionário ex-ante | Pipeline pode **rotular** ("histórico mostra aversão") mas nunca promove a F6. Re-perguntar anual mandatório. |
| INV3 | Meta de IF exige tripla coerência: renda alvo + horizonte + custo de vida alvo na IF | Sem horizonte declarado vira wishful thinking; sem custo de vida alvo, renda passiva perde semântica de poder de compra | Schema `goal.if.v2` já exige os 3. Memories surface não permite card "IF aos 50" sem os 3 campos. |
| INV4 | Holding/sucessão exige beneficiários e estrutura declarados | F16 sem CNPJ/estrutura + sem beneficiários em `family_members[]` é só nome | Renderização: se incompleto, vira CTA "complete sua estrutura sucessória", não fato declarado. |
| INV5 | Alocação-alvo respeita modo de rebalanceamento declarado | F9 carrega `rebalanceamento_modo` ([[ADR-141]]); misturar `por_aporte` com `trigger_5pct` no display = ruído | Memória de alocação exibe próxima ação coerente com modo declarado. |

---

## 3. Anti-padrões — o que memories NÃO captura (financial-planner)

1. **Predições macro do user** ("dólar vai a R$ 8") — palpite, não fato pessoal. Contamina contexto do chat.
2. **Sentimentos sobre mercado** ("pessimista com bolsa BR") — canal correto é re-questionário (F6), não memória solta.
3. **Tickers/ativos preferidos** ("gosto de ITUB4") — Mathoms revisa produto, não opera carteira.
4. **Performance histórica como meta** ("quero 20% ao ano") — retorno não é meta; renda passiva alvo (F12) é.
5. **Comparação com terceiros** ("meu cunhado tem R$ X") — ansiedade comportamental, anti-metodológico.
6. **Memórias que duplicam Decision** ("decidi quitar dívida X") — `Decision` é event-sourced; memories projeta, não cria caminho paralelo.

---

## 4. Decisões UX (product-designer)

| # | Decisão | Resposta |
|---|---|---|
| D1 | Onde mora a superfície? | **Rota dedicada `/workspace/memories`** (opção A). Drawer no relatório conflita com leitura densa; widget em settings sub-categoriza algo que é hero de jornada. |
| D2 | Hierarquia visual derivada↔declarada | **Lista única agrupada por categoria** + bullet glyph (●/◐) + linha de procedência + ação contextual ("Editar" vs "Ver origem/Confirmar/Corrigir"). **NÃO usar 2 colunas** (sugere "declaradas valem mais"). Combina 4 sinais por a11y. |
| D3 | Estado vazio (workspace recém-criado, pipeline já rodou) | CTA primário = "Revisar as N derivadas"; CTA secundário ghost = "Declarar uma memória". Hipótese: confirmar > declarar do zero (menor fricção). |
| D4 | Cônjuge editou recentemente — como aparece? | **Audit trail leve, sem notificação ativa no MVP.** Procedência mostra autor + data; histórico expandível. Notificação ativa é débito v2. |
| D5 | Sinalização "vai pro chat" (Fase 3.C) | **Fica para 3.C, não 3.E MVP.** Toda memória entra implicitamente no contexto do chat; "fixar/desafixar" só faz sentido depois do chat existir. |

---

## 5. Mockups baixa fidelidade (product-designer)

### Mockup 1 — `/workspace/memories` (tela principal)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AppShell sidebar │  Memórias                                                │
│ ─────────────────│  Isto sabemos sobre vocês — confira, corrija, evolua.    │
│  Início          │                                                          │
│  Documentos      │  ┌─────────┬─────────┬─────────┬─────────┐               │
│  Relatórios      │  │ Todas   │ Decla-  │ Deriva- │ Precisa │   [+ Nova]    │
│  Plano           │  │   28    │ radas 9 │ das 19  │ revisão │               │
│ ►Memórias        │  └─────────┴─────────┴─────────┴─────────┘    3          │
│  Configurações   │                                                          │
│                  │  Filtros:  [ Categoria ▾ ] [ Origem ▾ ] [ Autor ▾ ]      │
│                  │                                                          │
│                  │  ┌──────────────────────────────────────────────────┐    │
│                  │  │ PATRIMÔNIO E METAS                          (8)  │    │
│                  │  ├──────────────────────────────────────────────────┤    │
│                  │  │ ●  Meta Independência Financeira                 │    │
│                  │  │    R$ 4.200.000  até 2038                        │    │
│                  │  │    Declarada por Ana · 12/mar/2026     [Editar]  │    │
│                  │  │                                                  │    │
│                  │  │ ◐  Aporte mensal estimado                        │    │
│                  │  │    R$ 7.450 /mês (média 4 meses)                 │    │
│                  │  │    Derivada de extratos · set—dez/2025           │    │
│                  │  │    [Ver origem]  [Confirmar]  [Corrigir]         │    │
│                  │  │                                                  │    │
│                  │  │ ●  Perfil de risco                               │    │
│                  │  │    Moderado-arrojado                             │    │
│                  │  │    Declarada por Bruno · 02/fev/2026   [Editar]  │    │
│                  │  └──────────────────────────────────────────────────┘    │
│                  │                                                          │
│                  │  ┌──────────────────────────────────────────────────┐    │
│                  │  │ FAMÍLIA                                     (4)  │    │
│                  │  ├──────────────────────────────────────────────────┤    │
│                  │  │ ●  Casal — Ana e Bruno (titulares)               │    │
│                  │  │ ●  Dependentes — Helena (8), Pedro (5)           │    │
│                  │  │ ◐  Renda combinada bruta                         │    │
│                  │  │    R$ 38.500 /mês  ·  Derivada do IRPF 2024      │    │
│                  │  │    [Ver origem]  [Atualizar]                     │    │
│                  │  └──────────────────────────────────────────────────┘    │
│                  │                                                          │
│                  │  ┌──────────────────────────────────────────────────┐    │
│                  │  │ DECISÕES ATIVAS                            (11)  │    │
│                  │  └──────────────────────────────────────────────────┘    │
│                  │                                                          │
│                  │  ┌──────────────────────────────────────────────────┐    │
│                  │  │ FISCAL E TRIBUTÁRIO                         (5)  │    │
│                  │  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

Legenda visual:
  ●  bullet sólido = memória declarada (cor primária)
  ◐  bullet meia-lua = memória derivada (cor neutra com borda)
```

### Mockup 2 — Edit inline (Goal: Meta IF)

```
┌──────────────────────────────────────────────────────────────────┐
│  Editar memória  ·  Meta Independência Financeira      [Cancelar]│
├──────────────────────────────────────────────────────────────────┤
│  ⓘ  Editar aqui cria uma nova versão da meta no Plano.           │
│     A versão anterior fica no histórico.                         │
│                                                                  │
│  Valor-alvo                                                      │
│  ┌────────────────────────────────────────────┐                  │
│  │ R$  4.200.000,00                           │  (mono)          │
│  └────────────────────────────────────────────┘                  │
│                                                                  │
│  Ano-alvo                                                        │
│  ┌────────────────────────────────────────────┐                  │
│  │ 2038                                       │                  │
│  └────────────────────────────────────────────┘                  │
│                                                                  │
│  Premissa de retorno real                                        │
│  ┌────────────────────────────────────────────┐                  │
│  │ 6,0 % ao ano                               │                  │
│  └────────────────────────────────────────────┘                  │
│                                                                  │
│  ─────────────────────────────────────────────────────           │
│  Histórico                                                       │
│   ─ 12/mar/2026 · Ana · meta R$ 4.200.000 / 2038 (atual)         │
│   ─ 04/jan/2026 · Bruno · meta R$ 3.800.000 / 2036               │
│                                                                  │
│                                       [Cancelar]  [Salvar nova]  │
└──────────────────────────────────────────────────────────────────┘
```

### Mockup 3 — Estado vazio inicial

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Memórias                                                                   │
│  Isto sabemos sobre vocês — confira, corrija, evolua.                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │   ┌──┐                                                              │    │
│  │   │░░│   Já reunimos 14 informações dos seus documentos.            │    │
│  │   └──┘                                                              │    │
│  │                                                                     │    │
│  │   São pontos de partida — patrimônio, renda, fiscal —               │    │
│  │   que extraímos dos extratos, faturas e do IRPF de 2024.            │    │
│  │                                                                     │    │
│  │   Confirme, corrija ou complemente. Você e seu cônjuge também       │    │
│  │   podem declarar memórias novas que o pipeline ainda não sabe.      │    │
│  │                                                                     │    │
│  │      [ Revisar as 14 derivadas → ]    [ Declarar uma memória ]      │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Research questions (product-designer) — 3.A interview script

Entrevistar: 3 HENRY com ≥1 relatório + 1 que abandonou setup + 1 cônjuge não-titular (validar P2/ADR-183 P1).

**Bloco A — Mental model de "memória"**

1. "Se o Mathoms te dissesse 'isto sabemos sobre vocês', o que **você espera** ver listado? Me dá 5 itens em ordem de relevância."
2. "Hoje, onde no Mathoms você sente que 'falta uma página' que junte essas coisas?"

**Bloco B — Confiança em derivada vs declarada**

3. "Suponha duas linhas: (a) 'Aporte mensal: R$ 8.000 — vocês informaram em set/2025' e (b) 'Aporte mensal: R$ 7.450 — calculamos a partir dos seus extratos'. Qual você confiaria mais? Por quê?"
4. "Em (b), qual informação adicional te faria confiar tanto quanto em (a)?"
5. "Você editaria a linha (b)? O que **espera** que aconteça quando salvar?"

**Bloco C — Cônjuge e jornada**

6. "Se seu cônjuge editou um item há 3 dias, o que você espera ver quando abrir esta página?"
7. "Imagina que a tela está vazia hoje, mas o pipeline já rodou e tem 12 itens derivados. Qual o **primeiro** botão você clicaria?"

**Bloco D — Ligação com chat e abandono**

8. "Se sua próxima conversa com o copiloto Mathoms só puder usar 5 dessas memórias como contexto, quais você marcaria?"

---

## 7. Anti-patterns de execução (product-designer)

1. **"Mural de post-its"** — texto livre não-ancorado. MVP **proíbe** memória fora de Goal/Decision/family/workspace.
2. **"Edit em ilha"** — formulário que parece independente do aggregate; user edita Meta IF aqui e a tela de Plano não muda. Mitigação: modal abre `GoalForm` por baixo, header declara o efeito, histórico visível.
3. **"Memória como brinquedo de IA"** — copy gamificada, ícones de cérebro, animação de pulse. Viola ADR-183 anti-persona. Tom: relatório de auditoria leve, não notebook de IA.

---

## 8. Pré-requisitos arquiteturais (senior-cto consolidando designer + planner)

**3 ADRs Proposto exigidas ANTES da ADR `financial-memories-surface`:**

| ADR | Origem | Razão | Tamanho estimado |
|---|---|---|---|
| `goal-reserva-emergencia-schema` | financial-planner INV1, F11 | Hoje `reserva_emergencia` é threshold em `goals.json` rules-as-code ([[ADR-177]]), não Goal por workspace. Sem schema próprio, F11 não tem casa canônica. Schema deve impor `meses_alvo ∈ [3, 18]`, default 6, ligado a `despesa_essencial_mensal_brl` (derivado de E5). | Leve (~100 linhas + schema JSON) |
| `goal-meta-objetivo-schema` | financial-planner F13 | Casa, educação, intercâmbio, aposentadoria-do-cônjuge hoje viram `Decision` ou nada. Memória de "quero comprar casa em 5 anos" não tem onde aterrissar. Schema genérico: `tipo`, `custo_brl`, `data_alvo`, `prioridade`, `prazo_metodologico` (curto/médio/longo). | Leve (~120 linhas + schema JSON) |
| `decision-source-column` | product-designer pergunta de bloqueio | Decisão sobre `source: user_declared | user_confirmed | system_derived` em `Decision` aggregate. Sem isso, ação "Confirmar" da derivada vira escrita opaca; quebra audit log e anti-pattern #2. Investigar primeiro se já existe — se sim, fechar a ADR como "rastreabilidade já existente, documentar"; se não, adicionar coluna + migration. | Leve (~80 linhas) |

**Sequência operacional:**

1. Investigar `Decision` aggregate hoje → ADR `decision-source-column` (Proposto ou "no-op documentação").
2. Em paralelo: ADR `goal-reserva-emergencia-schema` + ADR `goal-meta-objetivo-schema` (planner pode delegar a si mesmo via brief curto).
3. Após as 3 mergeadas: ADR `financial-memories-surface` pode consumir aggregates canônicos com confiança.
4. Track `financial-memories-surface.md` materializado por `product-manager` quando A20 abrir.

**NÃO abrir** `WorkspaceFact` aggregate v2 — abstração prematura. Confirmado por planner; só revisitar se aparecer fato sem casa.

---

## 9. Pergunta de bloqueio resolvida (senior-cto)

Designer perguntou: "**`Decision` aggregate (ADR-136) hoje expõe `source: user_declared | user_confirmed | system_derived` no domínio?**"

**Resposta senior-cto (2026-05-23):** débito conhecido. ADR `decision-source-column` (pré-requisito acima) responde isso. Primeira ação do owner do track `financial-memories-surface` é abrir a ADR investigando o schema atual de `Decision`. Não bloqueia 3.A discovery (que pode rodar sem o source resolvido); bloqueia apenas o PR de implementação 3.E.

---

## 10. Sprint placement (product-manager)

- **3.E entra como `candidate` A20** (próxima slot pós-A19), condicional ao gate de saída de A19 + fechamento de 3.A com taxonomy aprovada.
- **3.A pode começar AGORA** (este artefato + taxonomia do planner = output 3.A pronto; falta validação com 3-5 dogfood via research questions §6).
- **Não preempta** A17 (`current`, ADR-238) nem A18/A19 (`candidate` com ADRs Proposto 239/240). Eng saturada por ~6-8 semanas.
- **Coordenação A18:** CRLV/apólices/FIPE introduz memórias derivadas novas. 3.E não merge antes de A18 done.
- **Coordenação A19:** S_PROTECAO projeta estado patrimonial no relatório; coordenar com `information-architect` antes do PR de 3.E para evitar duplicar narrativa "isto sabemos sobre você".

---

## Referências

- [PLAN-competitive-pierre §3 Fase 3](../_README.md)
- [[ADR-073]] Goals como entidade versionada
- [[ADR-136]] Decision aggregate event-sourced
- [[ADR-141]] Alocação alvo v2 (7 classes)
- [[ADR-157]] IRPF parser completo
- [[ADR-177]] Thresholds metodológicos
- [[ADR-178]] Risk aggregate
- [[ADR-183]] Landing positioning pillars
