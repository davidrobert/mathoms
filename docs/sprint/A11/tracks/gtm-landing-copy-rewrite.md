---
id: TRACK-gtm-landing-copy-rewrite
type: track
title: "Track GTM Landing Copy Rewrite — Fase 4.B COMPETITIVE_PIERRE (operational skeleton)"
sprint: A11
plan: PLAN-competitive-pierre
status: ready
created_at: "2026-05-08"
consumed_at: null
agent_role: "CEO + product-designer (com revisão gtm-strategist + product-manager)"
relates_to:
  - "[[ADR-183]]"
  - "[[PLAN-competitive-pierre]]"
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/marketing
  - area/strategy
  - phase/a11
  - methodology/positioning
---

# Track GTM Landing Copy Rewrite — Fase 4.B COMPETITIVE_PIERRE (operational skeleton)

> **Lane ID:** `gtm-landing-copy-rewrite`
> **Branch prefix:** `agent/gtm-landing-copy-rewrite/<yyyyMMdd-HHmm>`
> **Depende de:** [[ADR-183]] ✅ mergeado · sister track [competitor-pierre-poc](competitor-pierre-poc.md) (Fase 1) · coordenação com [A11.w5 Frontend + Methodology](../lanes/A11-w5-frontend-methodology.md) (cleanup de terminologia user-facing em curso)
> **Paralelo com:** PR-C (rascunho de copy literal pelo `product-designer`) — paths disjuntos
> **Conflita com:** outra sessão `agent/gtm-landing-copy-rewrite/*` ativa
> **Onda:** independente (GTM, não toca eng produtivo do produto)
> **Sprint:** A11 (lane `A11.competitive-pierre` em [SPRINTS-active](../../../_MOC/SPRINTS-active.md))
> **Time-box:** PR-B (este skeleton) — XS (1-2h). PR-C+PR-D agregados — M-L (10-15 dias entre design + publicação)
> **Owner sugerido:** CEO direto + delegação a `product-designer` (PR-C copy literal) + `gtm-strategist` (revisão sigilo §13.3 e aderência aos pilares)
> **Fonte de verdade das regras:** [CLAUDE.md](../../../../CLAUDE.md) · [docs/reference/COPY_GUIDELINES.md §13](../../../reference/COPY_GUIDELINES.md)

---

## 1. Goal

Reescrever copy da landing pública `mathoms.ai` para reposicionar a marca de "ferramenta de relatórios" para **advisor digital metodológico para o segmento HENRY brasileiro com cônjuge**, ancorada nos 4 pilares narrativos definidos em [[ADR-183]] (P1 hero casal · P2 método estruturado · P3 patrimônio inteiro + fiscal · P4 plano evolutivo).

---

## 2. Escopo

- **Reescrita de copy** da landing `mathoms.ai` contra os 4 pilares de [[ADR-183]] §"Decisão".
- **Materialização do ICP Score Card** ([[ADR-183]] §"ICP Score Card") como qualificador de lead em formulário/CTA da landing.
- **Materialização das 4 anti-personas** ([[ADR-183]] §"Anti-personas") como guardrail editorial — orienta o que **não** entra na landing.
- **Vocabulário público canônico** — toda copy nova respeita as substituições §13.2 do [COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md) e a tabela §"Decisão" da ADR-183.
- **Captura de baseline dos 6 leading indicators** ([[ADR-183]] §"Leading indicators") — analytics da landing (sem PII), métrica de scroll, dwell, taxa trial→primeiro report.
- **Soft launch viável imediato:** publicar P1+P2+P3+P4 sem comparativo competidor e sem narrativa AI conversacional, conforme [[ADR-183]] §"Dependências de gate".

---

## 3. Não-objetivos (escopo explicitamente excluído)

- ❌ **Escrever copy literal** — escopo do PR-C (`product-designer`, sessão paralela). Este track entrega **estrutura e gates**; a sessão paralela entrega **conteúdo**.
- ❌ **Publicar landing** — escopo do PR-D (CEO + designer + analytics + decisão de stack/CMS).
- ❌ **Decidir stack/CMS** da landing — escopo separado (delegação `build-vs-buy` se vier; até lá `mathoms.ai` continua na infra atual).
- ❌ **Pricing** (free vs trial vs paywall, valores dos tiers) — escopo da Fase 4.C ([[PLAN-competitive-pierre]] §3 Fase 4.C); ADR pendente (`pricing-repositioning-2026`).
- ❌ **Comparativo público com Pierre** — escopo da Fase 4.E; gated por Fase 2 (MCP) live ([[PLAN-competitive-pierre]] §3 Fase 4.E + [[ADR-183]] §"Dependências de gate").
- ❌ **Narrativa "advisor conversacional" / chat hero** — gated por Fase 3 (chat) beta ([[ADR-183]] §"Dependências de gate"); chat NÃO entra como pilar desta ADR (P5 ou refresh do P4 quando chat live).
- ❌ **SEO long-tail / programa de embaixadores / parcerias CFP** — escopos 4.D/4.F separados.

---

## 4. Dependências

| Dependência | Status | Bloqueia |
|---|---|---|
| [[ADR-183]] mergeada como `Proposto` | ✅ #141 (2026-05-08) | PR-B (este track) → habilitado |
| Track materializado em `status: ready` (PR-B) | 🚧 este PR | PR-C (copy literal pelo `product-designer`) |
| Coordenação com [A11.w5](../lanes/A11-w5-frontend-methodology.md) — cleanup de terminologia user-facing | 🚧 lane in_progress (W5 da Sprint A11) | PR-C (vocabulário canônico não pode divergir do cleanup) |
| Fase 2 (MCP) **OU** Fase 3 (chat) **beta visível** | ⬜ pendente — Fase 2/3 ainda em planejamento | **NÃO** bloqueia PR-C/PR-D conforme [[ADR-183]] §"Dependências de gate" — bloqueia apenas comparativo (4.E) e narrativa AI conversacional. Soft launch P1-P4 é viável agora. |
| [[ADR-178]] Risk aggregate user-facing (A11 W3) | ⬜ pendente | P3 perde 50% da prova se atrasar — mitigação: launch P3 com IRPF + balanço; "riscos cobertos" entra em refresh quando Risk live |

**Nota crítica de coordenação:** o reviewer da lane [A11.w5](../lanes/A11-w5-frontend-methodology.md) **deve validar** o vocabulário canônico definido em [[ADR-183]] §"Decisão" antes de o PR-C ir para review. Razão: se PR-C inventa um vocabulário paralelo divergente do cleanup user-facing em curso, o produto fala uma língua e a landing outra — inconsistência reputacional.

---

## 5. Critério de aceite

### 5.1 Para este PR-B (skeleton)

- [ ] Track materializado em `docs/sprint/A11/tracks/gtm-landing-copy-rewrite.md` com `status: ready`.
- [ ] Frontmatter validado por `dev/validate_frontmatter.py` (schema `note-track`).
- [ ] `docs/_MOC/_generated/` regenerado por `dev/build_doc_index.py --inline`.
- [ ] Auditoria sigilo manual via grep: zero ocorrências dos termos proibidos do [§13.1 do COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md) em copy prescritiva (atribuição interna a [[ADR-183]] e a sessões de planejamento permanece §13.4 PERMITIDA).
- [ ] PR-B mergeado em `main` (CI verde — docs-only, hooks pre-commit + frontmatter + links).

### 5.2 Para a lane completa (PR-C + PR-D, fora do escopo deste PR-B)

- [ ] PR-C: copy literal rascunhada pelo `product-designer` passa em `dev/check_sigilo_terms.py` (zero hits) **E** vocabulário canônico [[ADR-183]] respeitado **E** A11.w5 reviewer ✅.
- [ ] PR-D: landing live em `mathoms.ai` com analytics capturando os 6 leading indicators de [[ADR-183]] §"Leading indicators".
- [ ] **PR-D — coleta de sinal i18n (piggyback gratuito):** formulário "notify me" / "early access" da landing captura campo `preferred_language` com 3 opções (`pt-BR`, `en`, `es`). Dashboard mensal expõe contagem por idioma — alimenta Gatilho A do plano [[PLAN-i18n]] §10. Sem custo adicional de eng (é só mais um campo no form). Sem esse campo, Gatilho A de [[PLAN-i18n]] vira não-mensurável.
- [ ] 30-60 dias pós-launch: ≥ 4 dos 6 leading indicators em sinal positivo. Se < 4: refresh narrativo com `product-designer` antes de promover [[ADR-183]] a `Decidido`.
- [ ] PR-E: flip [[ADR-183]] de `Proposto` → `Decidido (Sprint XX.Y)` com `phase:` registrada.

---

## 6. Priorização

### 6.1 RICE (primário)

| Componente | Valor | Justificativa |
|---|---|---|
| **Reach** | ~1.500 | Visitantes HENRY-fit únicos da landing reescrita em janela de 60 dias pós-launch. Estimativa conservadora: 300-1.000/mês orgânico + paid push leve. Mathoms é early-stage; reach cresce com 4.D (conteúdo) e 4.F (parcerias). |
| **Impact** | 3 (high) | Reposicionamento de marca afeta **toda** signup downstream + pricing perception (fundamento para 4.C tier R$ 99-149) + qualificação ICP. Multiplicador para 4.D/4.E/4.F. |
| **Confidence** | 0.8 | Pilares decididos pelo CEO ([[ADR-183]]); capability live para todos os 4 pilares (validado em [[ADR-183]] §"Dependências de gate"); leading indicators codificados; soft launch viável imediato. Risco residual: P3 dependência de [[ADR-178]] user-facing (mitigado). |
| **Effort** | 0.7 PM | PR-B XS (~0.01 PM) + PR-C M (~0.3 PM designer) + PR-D M-L (~0.4 PM CEO+designer+analytics+CMS). Total ~14-21 dias úteis distribuídos. |

**RICE = (1500 × 3 × 0.8) / 0.7 ≈ 5.143 pts** — top-tier de priorização. Comparável à priorização de iniciativas brand-wide; justificado pelo multiplicador downstream em 4.C/4.D/4.E + janela competitiva de 12-18 meses ([[PLAN-competitive-pierre]] §2 P5).

### 6.2 WSJF (secundário, sanity check)

- **Business Value:** 8/10 — habilita tier R$ 99-149 (fundamento de revenue); sem reposicionamento, mass-market positioning perpetua percepção de "ferramenta", não advisor.
- **Time Criticality:** 9/10 — Pierre cresceu 165k usuários em 8 meses sob backing CloudWalk ([[PLAN-competitive-pierre]] §1); janela de execução 12-18 meses (P5).
- **Risk Reduction / Opportunity Enablement:** 7/10 — destrava 4.C (pricing), 4.D (conteúdo), 4.E (SEO), 4.F (parcerias). Bloqueador downstream.
- **Cost of Delay** = 8 + 9 + 7 = **24**.
- **Job Size** = 5/10 (~0.7 PM agregado).

**WSJF = 24 / 5 = 4.8** — top-tier, alinhado com RICE.

---

## 7. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **P3 perde 50% da prova se [[ADR-178]] Risk aggregate atrasar em A11 W3** ([[ADR-183]] §"Consequências › Negativas") | M | M | Launch P3 com IRPF + balanço completos como prova suficiente; "riscos cobertos" entra em refresh quando Risk live na UI. PR-C deve preparar copy de P3 com 2 variantes (com/sem Risk). |
| **P1 hero não-negociável** ([[ADR-183]] §"Consequências › Negativas") — risco de PR-C tentar promover P2/P3/P4 ao topo por estética | B | A | PR-C briefing explícito: P1 é hero **fixo**, P2-P4 são reforços. Reviewer (`gtm-strategist`) bloqueia se hierarquia for invertida. |
| **4 pilares = 4 mensagens** — risco de diluição visual ([[ADR-183]] §"Consequências › Negativas") | M | M | PR-C entrega hierarquia visual explícita: P1 dominante, P2-P4 secundários. `product-designer` aplica grid editorial; revisão CEO antes de PR-D. |
| **Vocabulário canônico desrespeitado por PR-C** — risco de copy reintroduzir termos §13.1 ou inventar vocábulo divergente de A11.w5 | B | A (legal/IP) | Hook `dev/check_sigilo_terms.py` cobre frontend (não cobre `docs/_marketing/` se materializado — débito aberto §13.5 do COPY_GUIDELINES). PR-C briefing **obriga** rodar grep manual sobre toda copy nova; reviewer A11.w5 ✅ antes de PR-C ir para review. |
| **Sem hero conversacional** — concorrente comunica AI-conversacional como hero ([[ADR-183]] §"Consequências › Negativas"); pode soar "atrasado" para visitante AI-nativo | M | B | Aceito por design — ICP Mathoms não compra novelty AI, compra seriedade metodológica. Anti-persona "Curioso AI-nativo / hobbyista" ([[ADR-183]] §"Anti-personas") explicitamente fora de escopo. |
| **ICP scorecard é hipótese inicial** — pesos/thresholds não validados contra cohort histórico ([[ADR-183]] §"Consequências › Negativas") | A | B | Rotular como hipótese até segunda iteração. Refinar após Fase 4.A (entrevistas qualitativas) entregar 10-15 transcrições. PR-D não bloqueia em ICP perfeito; melhoria iterativa. |
| **Capacidade CEO/designer indisponível em A11** — track ready mas sem pickup | A | B | `status: ready` é discoverable; `product-manager` slota PR-C/PR-D em A12 ou janela disponível. PR-B (este) é independente e fecha o débito de skeleton imediatamente. |

---

## 8. Sequência operacional (mapa do plano `competitive-pierre`)

| Ordem | Owner | Entregável | Status | Gate de saída |
|---|---|---|---|---|
| **PR-A** | orquestrador `senior-cto` | [[ADR-183]] mergeada como `Proposto` | ✅ #141 (2026-05-08) | merge em `main`, status `Proposto` |
| **PR-B** (este) | `product-manager` | Track skeleton `gtm-landing-copy-rewrite.md` referenciando [[ADR-183]] | 🚧 este PR | track materializado em `status: ready`; sprint placement A11; índices regenerados |
| **PR-C** (paralelo a este) | `product-designer` | Rascunho de copy literal contra os 4 pilares + ICP card + anti-personas — em sessão paralela rodando agora; paths disjuntos a este PR | ⬜ rodando | copy revisada com `gtm-strategist` (auditoria sigilo §13.3) **+** A11.w5 reviewer **+** CEO sign-off |
| **PR-D** | CEO + `product-designer` | Publicação da landing reescrita em `mathoms.ai`; hook `sigilo-terms` expandido para `docs/_marketing/**` se materializado; analytics de leading indicators configurado | ⬜ pendente | landing live; analytics ativo; baseline dos 6 indicators capturado |
| **PR-E** | orquestrador | Flip [[ADR-183]] `Proposto` → `Decidido (Sprint XX.Y)` quando 4.B publica e ≥ 4/6 indicators ≥ 30 dias positivos | ⬜ pendente | data de flip + Sprint registrada no frontmatter |

---

## 9. Estimativa

- **PR-B (este):** **XS** (1-2 horas) — skeleton de track em markdown + frontmatter + atualização de índices.
- **PR-C (escopo do `product-designer`, sessão paralela):** **M** (5-7 dias úteis) — copy literal de 4 pilares + ICP card UI + anti-personas internalizadas + revisão `gtm-strategist` + sign-off CEO.
- **PR-D (escopo CEO + designer + eventual `build-vs-buy` para CMS/stack):** **M-L** (5-10 dias úteis) — produção visual, decisão CMS/stack se houver, integração de analytics, smoke humano em 3-5 visitantes-cobaia, baseline de leading indicators.

**Total agregado da lane completa:** **L** (~14-21 dias úteis distribuídos entre 3-4 owners; wall-clock 3-5 semanas com paralelismo CEO+designer+revisores).

---

## 10. Coordenação com A11.w5 (Frontend + Methodology)

A lane [A11.w5 Frontend + Methodology](../lanes/A11-w5-frontend-methodology.md) está reescrevendo terminologia user-facing dentro do produto (`/reports/[id]`, app shell). Em paralelo, PR-C entrega copy literal da landing.

**Risco se não coordenar:** produto fala "Independência Financeira" enquanto landing fala "Liberdade Patrimonial" (inventado) — usuário troca de mensagem entre canais → reduz confiança, dilui marca.

**Protocolo de coordenação:**

1. **Vocabulário canônico fixo:** [[ADR-183]] §"Decisão" lista as substituições obrigatórias. Tanto A11.w5 quanto PR-C **devem** ler essa tabela como fonte de verdade.
2. **Reviewer A11.w5 valida PR-C antes de review final.** Antes de PR-C ir para review do CEO, owner da lane A11.w5 confere que vocabulário não diverge do cleanup em curso. Reciprocamente, A11.w5 pode citar [[ADR-183]] §"Decisão" como input para o cleanup de terminologia user-facing.
3. **Falha modo "vocabulário paralelo":** se PR-C inventar termo não listado em [[ADR-183]] §"Decisão" nem em [§2 do COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md), o termo entra em §2.2 ("Termos com decisão pendente") com PR antes de virar copy live.

---

## 11. Notas de execução para `product-designer` (consumidor de PR-C)

> Este bloco é briefing direto para a sessão paralela do `product-designer` que entrega PR-C. Mantido aqui para que PR-C tenha pointer único para input estratégico.

### 11.1 Inputs canônicos (ler nesta ordem)

1. **[[ADR-183]] §"Decisão"** — 4 pilares + capability ancorada por pilar. Hierarquia P1 > P2 > P3 > P4 é **fixa**.
2. **[[ADR-183]] §"ICP Score Card"** — qualificador de lead. Materializa como formulário/widget que o visitante vê (ou usa como filtro silencioso de qualificação no CRM).
3. **[[ADR-183]] §"Anti-personas"** — guardrail editorial. Tudo na landing **deve** repelir as 4 anti-personas (linguagem, exemplos, tom, valores).
4. **[[ADR-183]] §"Decisão" Vocabulário público canônico** — tabela de substituições obrigatórias.
5. **[§13 do COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md)** — sigilo metodológico. **Zero** menção pública de termos proibidos §13.1.
6. **[§1-§7 do COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md)** — tom de voz, terminologia financeira canônica, capitalização, monetário, datas, voz/estilo, erros/vazios.

### 11.2 Output esperado de PR-C (não-vinculante; fechado em sessão própria)

- Hero P1 (casal) — headline + subhead + CTA primária.
- Sections P2/P3/P4 — headline + subhead + 1-2 evidências (não atribuídas) por seção.
- ICP Score Card materializado como widget ou formulário curto (8 atributos × 3 níveis de [[ADR-183]] §"ICP Score Card").
- Anti-personas internalizadas como guardrail editorial (não publicadas como tal — orientam o que **não** entra).
- Métricas de baseline dos 6 leading indicators ([[ADR-183]] §"Leading indicators") com plano de captura (analytics, sem PII).

### 11.3 Gates editoriais antes de submit

Rodar o enforcer canônico — fonte única de regex em `dev/check_sigilo_terms.py`:

```bash
# Sigilo automatizado — cobre `frontend/src/(app|components)/**/*.{ts,tsx}`
# por default. Para copy em surface não coberta pelo hook (ex.: futuro
# `docs/_marketing/`, transcripts de pitch, exports do CMS), passar
# explicitamente os arquivos:
python3 dev/check_sigilo_terms.py <arquivos da copy>
# expected: exit 0 (zero hits)
```

Para auditoria ad-hoc do repo inteiro: `python3 dev/check_sigilo_terms.py --all`. Padrões detectados, exclusões e racional em [§13.3 do COPY_GUIDELINES](../../../reference/COPY_GUIDELINES.md).

---

## 12. Fora de escopo — pointer para destinos corretos

| Pergunta | Onde resolver |
|---|---|
| "Que CMS / stack usar para a landing reescrita?" | PR-D + (eventualmente) novo track com delegação `build-vs-buy` |
| "Tier free ou trial 30d? R$ 99 ou R$ 149?" | Fase 4.C — abrir track `gtm-pricing-repositioning.md` + ADR `pricing-repositioning-2026` ([[PLAN-competitive-pierre]] §5) |
| "Comparativo público com Pierre?" | Fase 4.E — gated por Fase 2 (MCP) live |
| "Hero conversacional / chat na landing?" | Fora de escopo desta ADR; entra como P5 ou refresh do P4 quando Fase 3 (chat) beta |
| "Programa de embaixadores CFP / contadores?" | Fase 4.F — track separado, owner CEO + comercial |
| "SEO long-tail sobre keywords Pierre?" | Fase 4.E (parcial — não ataca, só diferencia factualmente) |
| "Pesquisa de segmento qualitativa (10-15 entrevistas HENRY)?" | Fase 4.A — track [`gtm-segment-research.md`](../../A11/tracks/) (a criar; em paralelo desde dia 1) |

---

## 13. Definição de feito (deste PR-B)

1. Arquivo `docs/sprint/A11/tracks/gtm-landing-copy-rewrite.md` materializado com frontmatter válido pelo schema `note-track`.
2. `docs/_MOC/_generated/SPRINT_CURRENT.md` regenerado e contém a entrada do novo track na sprint A11.
3. `docs/_MOC/_generated/PLAN_*` (se aplicável) regenerado consistente.
4. Pre-commit verde nos arquivos staged: `validate_frontmatter`, `check_doc_filename_id`, `check_doc_links`, demais hooks padrão.
5. Auditoria sigilo manual via grep: zero ocorrências de termos §13.1 em copy prescritiva (atribuição interna a [[ADR-183]] dentro deste track e do plano `competitive-pierre` permanece §13.4 PERMITIDA).
6. PR-B aberto contra `main` com `--squash --auto`; CI verde (docs-only — sem suíte pytest exigida).
7. Merge confirmado: `gh pr view <N> --json mergeCommit,mergedAt` retorna data de merge; `git log origin/main --oneline` mostra o commit-merge.

---

## 14. Referências

### Internas

- [[ADR-183]] — Pilares narrativos da landing (origem desta lane)
- [[PLAN-competitive-pierre]] — plano canônico (§3 Fase 4.B + §8.2 sugere este track)
- [competitor-pierre-poc.md](competitor-pierre-poc.md) — sister track (Fase 1 do mesmo plano)
- [A11.w5 lane](../lanes/A11-w5-frontend-methodology.md) — coordenação de vocabulário user-facing
- [docs/reference/COPY_GUIDELINES.md](../../../reference/COPY_GUIDELINES.md) — fonte de verdade de tom + terminologia + sigilo §13
- [docs/reference/ARCHITECTURE.md §18](../../../reference/ARCHITECTURE.md) — URLs canônicas (landing fica em `mathoms.ai`)
- [.claude/agents/gtm-strategist.md](../../../../.claude/agents/gtm-strategist.md) — briefing do reviewer de PR-C
- [.claude/agents/product-designer.md](../../../../.claude/agents/product-designer.md) — briefing do executor de PR-C
- [.claude/agents/product-manager.md](../../../../.claude/agents/product-manager.md) — briefing do papel deste PR-B

### Sprint placement

- [SPRINTS-active](../../../_MOC/SPRINTS-active.md) — lane `A11.competitive-pierre` declarada
- [Sprint A11 _README](../../A11/_README.md) — contexto da sprint corrente
