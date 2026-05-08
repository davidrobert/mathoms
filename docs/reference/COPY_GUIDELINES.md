# Copy Guidelines — Mathoms

> Diretriz canônica de **tom de voz**, **terminologia financeira** e
> **microcopy** do Mathoms. Aplica a todo texto user-facing: UI da app,
> relatório `/reports/[id]`, e-mails transacionais, mensagens de erro,
> PDFs exportados e copy comercial pública.
>
> **Não aplica** a documentação técnica interna (`docs/`, ADRs,
> CHANGELOG, READMEs de pacote), logs estruturados (`mathoms.*`) e
> comentários de código — esses ficam fora do escopo.
>
> **Última revisão:** 2026-04-27.

---

## 1. Tom de voz

| Eixo | Mathoms é | Mathoms **não** é |
| --- | --- | --- |
| Postura | Sério, confiável, calmo | Gamificado, infantil, "amigão" |
| Densidade | Direto e denso, mas legível | Verboso, "explicador", redundante |
| Pessoa | Segunda pessoa de respeito ("você") | "Tu", "vocês", "a gente", "nós" no lugar do usuário |
| Promessas | Mostra fatos extraídos do dado real | Promete retorno, garante meta, "vai te deixar rico" |
| Incerteza | Premissa declarada explicitamente | Esconde hipótese atrás de número exato |

Princípios codificados em
[.claude/agents/product-designer.md](../.claude/agents/product-designer.md)
("Tom: sério, confiável, legível — não gamificado, não infantil"):
**não duplicar**, citar quando precisar reforçar.

### 1.1 Como tratar incerteza

Tudo que projeta o futuro carrega premissa. Sempre declare a premissa
**antes** ou **junto** do número:

- ✅ "Projeção 2035 com retorno real de 6% a.a. (premissa base)."
- ✅ "Renda passiva estimada — IGPM 4%/ano, DY ações 5–8%, DY FIIs 9%."
- ❌ "Em 2035 você terá R$ 4,2 milhões."
- ❌ "Sua renda passiva será R$ 18.500 por mês."

Disclaimers obrigatórios estão em
[config/methodology.md](../config/methodology.md) §Disclaimers. Não
remover por concisão.

### 1.2 Vocativo

- **"Você"** sempre. Plural ("vocês") só quando o contexto for
  explicitamente familiar e plural — ex.: "vocês vão precisar revisar
  juntos a meta de IF".
- **Nunca:** "o usuário", "o cliente", "o titular" como vocativo direto.
  Esses termos ficam só em texto descritivo de terceira pessoa
  (relatório, e-mails para o planejador).
- **"A família"** é aceito quando o relatório fala da unidade familiar
  como sujeito ("Patrimônio total da família: R$ X").

---

## 2. Terminologia financeira canônica

> Este glossário é a fonte de verdade. Quando `config/methodology.md`,
> `config/report_layout.yaml` ou `docs/methodology/definitions.md` divergir,
> abrir PR em **um** desses para alinhar — ver §11 Hierarquia.
>
> Gera, em F12.6b, `config/i18n_glossary.yaml` com as traduções
> normativas para os 9 demais locales (ver
> [plan/I18N/_README.md §6.2](plan/I18N/_README.md)).

| Termo canônico | Definição (1 linha) | Capitalização | Abreviação aceita | Sinônimos a **evitar** |
| --- | --- | --- | --- | --- |
| **Independência Financeira** | Patrimônio que gera renda passiva suficiente para cobrir despesas vitalícias via TRS | Title Case em headings, "independência financeira" em corpo | `Indep. Financeira` em label compacto · `IF` **só em apêndice/glossário** ou em variável técnica (`gap_if`, `meta_if`) | `IF` em label de KPI; `aposentadoria`; `liberdade financeira` |
| **Reserva de emergência** | Valor líquido em ativos resgatáveis em D+0/D+1 para cobrir 3–24 meses de despesas | minúsculo em corpo; Title Case em card title | — | `colchão`, `fundo de emergência`, `reserva de proteção` |
| **Patrimônio líquido** | Soma de ativos − passivos (dívidas) | minúsculo em corpo | — | `total`, `valor total`, `riqueza` |
| **Patrimônio bruto** | Soma de todos os ativos sem deduzir dívidas | minúsculo em corpo | — | `patrimônio total` (ambíguo) |
| **Patrimônio investível** | Termo umbrella — **prefira as 3 formas precisas abaixo** quando o contexto importar (score, IF, projeção). | minúsculo em corpo | — | `capital`, `investido` |
| **Patrimônio investível financeiro** | `cat_3 + cat_4 + cat_5 + cat_6` — apenas ativos financeiros líquidos. **Métrica canônica para `progresso_if`** — alinhada ao padrão consagrado de planejamento patrimonial brasileiro (atribuição interna admitida; ver §13). | minúsculo em corpo | — | — |
| **Patrimônio investível total** | `bruto − cat_1 − cat_7` — exclui residência principal e veículos. Inclui imóveis de investimento. Métrica retro-compat. | minúsculo em corpo | — | — |
| **Patrimônio investível efetivo** | `investivel_financeiro + (cat_2 if workspace.imoveis_no_if else 0)` — métrica usada de fato no score `progresso_if` (ver [ADR-142](DECISIONS.md#adr-142--toggle-imoveis_no_if-em-pipelinejson--invariante-anti-dupla-contagem)). | minúsculo em corpo | — | — |
| **Aporte** | Valor mensal direcionado a investimentos para compor o número da IF | minúsculo em corpo | — | `contribuição`, `poupança`, `economia` |
| **Aporte programado / DCA** | Aporte automático recorrente (Dollar-Cost Averaging) | minúsculo em corpo | `DCA` aceito após primeira menção | `compra programada` |
| **Score financeiro** | Nota 0–10 ponderada por 5 critérios (poupança, cobertura, endividamento, IF, diversificação) | minúsculo em corpo; "Score Financeiro" em card title | — | `nota geral`, `health score` |
| **Taxa de poupança** | (Receita − Despesa) / Receita, calculada em base recorrente | minúsculo em corpo | — | `taxa de economia` |
| **Fatura** | Demonstrativo de cartão de crédito com vencimento mensal | minúsculo em corpo | — | `extrato do cartão` (errado) |
| **Extrato** | Demonstrativo de movimentações de conta corrente, poupança ou investimento | minúsculo em corpo | — | `histórico` (genérico demais) |
| **Boleto** | Título de cobrança bancária com código de barras | minúsculo em corpo | — | `cobrança`, `pagamento` |
| **Despesa** | Saída de caixa do período (passado/realizado) | minúsculo em corpo | — | `gasto` (em contexto contábil), `custo` |
| **Gasto** | Sinônimo coloquial de despesa — **aceito em copy de UI** quando "despesa" soar técnico demais | minúsculo em corpo | — | — |
| **Custo** | Reservado para PJ / empresa (custo do serviço, custo fixo). **Não usar** em finanças pessoais | — | — | "custo de vida" → use "despesas mensais" |
| **Gap IF** | Distância entre patrimônio investível atual e o número da IF | minúsculo em corpo | — | `falta`, `déficit` |
| **Meta IF** | Valor-alvo do número da IF | minúsculo em corpo; "Meta de Independência Financeira" em hero | — | `objetivo`, `target` |
| **Prazo IF** | Anos restantes até atingir a meta no cenário base | minúsculo em corpo | — | `tempo`, `ETA` |
| **TRS** | Taxa de Retirada Segura (Safe Withdrawal Rate); Mathoms usa 4–5% como base | maiúsculo (sigla) | `TRS` é a forma; expandir só na primeira menção e no apêndice | `SWR`, `taxa de saque` |
| **Trinity Study** | Estudo histórico que fundamenta a TRS de 4% | Title Case | — | — |
| **PGBL / VGBL** | Planos de previdência privada (Plano Gerador / Vida Gerador de Benefício Livre) | maiúsculo (sigla) | — | "previdência" sozinho (ambíguo) |
| **Renda fixa** | Classe de ativos com remuneração contratada (CDB, LCI, Tesouro, debêntures) | minúsculo em corpo | `RF` só em label de gráfico | — |
| **Renda variável** | Classe de ativos com retorno não-contratado (ações, ETFs, FIIs) | minúsculo em corpo | `RV` só em label de gráfico | — |
| **FII** | Fundo de Investimento Imobiliário | maiúsculo (sigla); plural `FIIs` | — | `fundo imobiliário` (aceito em prosa, mas FII no card) |
| **REIT** | Real Estate Investment Trust (equivalente americano do FII) | maiúsculo (sigla); plural `REITs` | — | — |
| **Alocação contracíclica** | Estratégia de renda fixa que se adapta ao ciclo da Selic — Selic↑ → prioriza prefixados; Selic↓ → prioriza IPCA+ longos. Captura prêmio de marcação a mercado em ativos de duração média/longa. | minúsculo em corpo; "Alocação Contracíclica" em card title | — | `contrafluxo` (origem branded — ver §13); `contracorrente` |
| **CDI / Selic / IPCA+** | Indexadores de renda fixa | maiúsculo (sigla) | — | — |
| **Carnê-leão** | Recolhimento mensal de IRPF sobre rendimentos isentos/sem retenção (aluguéis) | minúsculo, com hífen | — | `carne-leão` (sem hífen, errado) |
| **Holerite** | Demonstrativo de pagamento CLT | minúsculo em corpo | — | `contracheque` (regional) |

### 2.1 Eixos de produto (legado F11.1c, preservado)

Convivem dois eixos no produto que não devem se misturar:

| Termo | Quando usar |
| --- | --- |
| **Mês / período** | Dados operacionais do pipeline (extratos, transações consolidadas, relatório "deste mês"). |
| **Projeção** | Cenários futuros (IF, metas, simulações) — não confundir com saldo já realizado. |
| **Patrimônio alvo** | Objetivo de longo prazo nas metas; distinto do PL do snapshot atual. |
| **Plano / Meu Plano** | Eixo estratégico (metas, tarefas de vida, cofre de contexto). |
| **Documentos → Pipeline → Relatório** | Eixo operacional do período. |

Rotas: `/plano` e fluxos de meta = estratégico; `/documents`,
`/pipeline`, `/reports`, `/dashboard` = operacional do período.

### 2.2 Termos com decisão pendente — registrar aqui ao decidir

Quando uma decisão terminológica nova surgir, adicione linha aqui com
`@yyyy-mm-dd` antes de propagar para outros docs.

---

## 3. Capitalização

Regra geral: **Title Case nos títulos de seção/card; minúsculo no
corpo**. Português usa menos Title Case que inglês — não capitalizar
artigos, preposições, conjunções no meio do título.

| Contexto | Regra | Exemplo |
| --- | --- | --- |
| Título de seção (H1/H2 do relatório) | Title Case | "Patrimônio — Estrutura e Composição" |
| Título de card (`.card-title`) | Title Case | "Reserva de Emergência" |
| Label de KPI | Title Case curto | "Patrimônio Líquido" |
| Subtítulo, descrição | Sentence case | "Soma dos ativos menos as dívidas." |
| Corpo de texto longo | Sentence case | "O patrimônio líquido reflete..." |
| Botão | Sentence case, verbo no infinitivo | "Atualizar análise", "Baixar PDF" |
| Sigla | Sempre em caixa alta | `IRPF`, `CDI`, `TRS`, `IPCA+` |

### 3.1 Decisão IF / Indep. Financeira / Independência Financeira

Conflito histórico entre `config/report_spec.md` ("usar Independência
Financeira ou Indep. Financeira, NÃO 'IF' nos labels") e uso geral em
GAPS / PLAN / código. **Decisão canônica:**

| Contexto | Forma | Exemplo |
| --- | --- | --- |
| Headings de seção e título de card | **Independência Financeira** | "S7 — Independência Financeira" |
| Label de KPI hero (≤24 chars úteis) | **Indep. Financeira** | "Meta Indep. Financeira: R$ 4,2 mi" |
| Corpo de texto, prosa | **independência financeira** | "...para atingir a independência financeira em 2035..." |
| Variável técnica, glossário, ID de chart | `IF` | `gap_if`, `meta_if`, `if_projector`, `chart-waterfall-if` |
| Apêndice A (glossário) | `IF` listado como sigla com expansão | "**IF** — Independência Financeira (ver Seção 7)" |
| Banner curtíssimo / mobile (<320px) | `IF` aceito como fallback | "Prazo IF: 12 anos" |

**Não use** `IF` em hero KPI desktop, em copy de produto comercial,
em e-mail transacional, em estado vazio. A sigla é sempre o último
recurso.

---

## 4. Formato monetário

### 4.1 BRL (padrão)

- Formato: `R$ 1.234,56`
- Espaço entre símbolo e número: **NBSP** (` `) — preserva em
  quebra de linha.
- Separador de milhar: `.` (ponto)
- Separador decimal: `,` (vírgula)
- Casas decimais: **2** sempre, mesmo zero (`R$ 0,00`).
- Negativo: **hífen + espaço** antes do símbolo, em **vermelho** (token
  `var(--semantic-loss)`). Sinal e cor sempre juntos (a11y — daltônicos).
  - ✅ `-R$ 1.234,56`
  - ❌ `(R$ 1.234,56)` (parênteses são padrão US, evitar)
  - ❌ `R$ -1.234,56` (sinal entre símbolo e número confunde leitura)
- Positivo com destaque (delta): **`+`** prefixado, em verde (`var(--semantic-gain)`).
  - `+R$ 1.234,56`

Renderização única via `<MonetaryValue/>`. Nunca formatar à mão.

### 4.2 Compact (KPIs, hero, cards de síntese)

Use `compact` quando o valor sai do card em desktop ou viola
hierarquia visual. Sempre acompanhar de `title="R$ 1.234.567,89"`
com valor completo.

| Faixa | Forma | Exemplo |
| --- | --- | --- |
| < R$ 10.000 | Completa | `R$ 1.234,56` |
| R$ 10 mil – R$ 999 mil | `R$ 12,3 mil` ou completa em tabela | KPI hero: `R$ 850 mil` |
| R$ 1 mi – R$ 999 mi | `R$ 1,2 mi` | `R$ 4,2 mi` |
| ≥ R$ 1 bi | `R$ 1,2 bi` | — |

Ranges em compact: travessão `—` (não hífen). `R$ 1 mi — R$ 5 mi`.
**Não** abreviar com `R$ 1k–10k` — `k` quebra leitura em PT-BR e
mistura sistemas. Use `mil` / `mi` / `bi`.

### 4.3 Zero vs. dado ausente (regra crítica em fintech)

- **Zero real** → `R$ 0,00` (preto/cinza neutro, NÃO em verde/vermelho).
- **Dado ausente / não aplicável** → `—` (travessão em cinza,
  `text-muted-foreground`).

Diferenciar visualmente é obrigatório (a11y + clareza). `<MonetaryValue
value={null} />` já renderiza `—`; nunca substituir por `R$ 0,00`
quando o dado simplesmente não foi capturado.

### 4.4 USD

- Formato: `US$ 1,234.56` (separador de milhar `,`, decimal `.`).
- Símbolo `US$` (não `$` cru — ambíguo com Real em copy PT-BR).
- Mesma regra de NBSP, sinal e ausência.
- Em narrativa que mistura BRL+USD, sempre etiquetar: `R$ 5.800 (US$
  1.000 a R$ 5,80/USD)`.

### 4.5 Arredondamento

- Em **dado bruto** (transação, fatura, extrato): preservar centavos.
- Em **agregados** (KPI, card de síntese): half-up para 2 decimais.
- Em **compact** (`mi`, `mil`): 1 decimal (`R$ 4,2 mi`).
- **Nunca** usar `float` para arredondar (ADR-090) — `Money.brl()` /
  `Decimal`. Arredondamento é responsabilidade do backend; UI apenas
  formata.

---

## 5. Datas e períodos

| Contexto | Formato | Exemplo |
| --- | --- | --- |
| Prosa, copy de UI | `mês de YYYY` (mês por extenso, minúsculo) | "Em abril de 2026, a família..." |
| Label compacto, eixo de gráfico | `MMM/YY` | `abr/26` |
| Header de tabela densa | `YYYY-MM` | `2026-04` |
| Cabeçalho de período | `mmm/yyyy` (3 letras) | `abr/2026` |
| Range de datas em prosa | `de A a B` | "de janeiro a abril de 2026" |
| Range em label / título de card | travessão **`—`** (em-dash, não hífen) | `jan/26 — abr/26` |
| Data exata (timestamp visível) | `dd/mm/yyyy HH:mm` | `27/04/2026 14:32` |
| ISO em metadata, atributo HTML, JSON | `YYYY-MM-DD` | `2026-04-27` |

**Aceito também** `abril/2026` (forma longa em label médio) — mas
preferir `abril de 2026` em prosa. **Nunca** misturar separadores
no mesmo doc (`abr-26` e `abr/26` no mesmo card é erro).

---

## 6. Voz e estilo

### 6.1 Voz ativa preferida

- ✅ "Atualizamos sua análise."
- ❌ "Sua análise foi atualizada."
- ✅ "Você precisa enviar o extrato de março."
- ❌ "É necessário que seja enviado o extrato de março."

### 6.2 Sem gerundismo

- ❌ "Estaremos enviando o relatório."
- ✅ "Enviaremos o relatório." / "O relatório fica pronto em 5 min."
- ❌ "Vamos estar processando seus documentos."
- ✅ "Estamos processando seus documentos."

### 6.3 Sem jargão de implementação em UI

UI fala a língua do produto, não do código. O usuário não sabe o
que é "stage", "pipeline", "artefato".

| Jargão técnico | Copy de UI |
| --- | --- |
| ❌ "Executar pipeline E0→E5" | ✅ "Atualizar análise" |
| ❌ "Stage E2 falhou" | ✅ "Não conseguimos ler o extrato do C6" |
| ❌ "Reconciliar artefatos" | ✅ "Conferir transações duplicadas" |
| ❌ "LLM extrai dados via fallback" | ✅ "Análise inteligente quando o formato muda" |
| ❌ "Roteamento E0" | ✅ "Classificação automática" |
| ❌ "Schema validation falhou" | ✅ "Encontramos um campo inesperado neste documento" |
| ❌ "BYOK" em label de produto | ✅ "Use sua própria chave de IA" (BYOK só em doc técnica) |

Termos do pipeline (`E0`, `E5`, `stage`) ficam em telas internas do
console operacional (`ops.mathoms.ai`) — não em
`app.mathoms.ai` cliente.

### 6.4 Concisão e ordem

- Pergunta-chave de cada copy: "o que decido depois de ler?". Se a
  resposta é "nada", a copy é decorativa — corte.
- Frases curtas (≤20 palavras). Quebre antes de subordinada.
- Resultado primeiro, contexto depois: ✅ "Você gastou R$ 4.200 com
  alimentação — 12% acima do teto de março." ❌ "Ao analisar suas
  transações de cartão, observamos que..."

---

## 7. Erros, vazios, confirmações

### 7.1 Mensagem de erro = causa + ação

Fórmula: **`<O que aconteceu>. <O que fazer agora>.`**

- ❌ "Erro 500" / "Internal Server Error" / "Algo deu errado"
- ❌ "Não foi possível processar a requisição"
- ✅ "Não conseguimos ler o PDF do C6. Tente reenviar — se persistir,
  o formato pode ter mudado."
- ✅ "A chave da Anthropic expirou. Atualize em **Configurações →
  Provedores de IA**."
- ✅ "Não encontramos o extrato de março/2026. Envie o PDF em
  **Documentos → Adicionar**."

Nunca expor códigos internos (`stage E3 raised ReconciliationError`)
ao usuário final. Logue em `mathoms.*` e mostre causa traduzida.

### 7.2 Empty state ensina

Vazio é ponto de partida, não fim de jornada. Cada empty state tem 3
elementos:

1. **Diagnóstico** — por que está vazio.
2. **Próximo passo** — o que fazer agora, com CTA.
3. **Tempo estimado** (quando útil) — quanto demora.

Exemplo:

> **Nenhum relatório gerado ainda.**
> Envie ao menos um extrato e uma fatura para sua primeira análise.
> Leva cerca de 5 minutos.
> [Adicionar documentos →]

❌ "Sem dados." / "Lista vazia." / "Nada por aqui."

### 7.3 Confirmação destrutiva é explícita

Verbo no infinitivo do que vai acontecer + consequência mensurável.

- ❌ "Tem certeza?" / "Quer continuar?"
- ✅ "Apagar o relatório de **abril de 2026**? Esta ação remove 312
  transações categorizadas e não pode ser desfeita."
- ✅ "Reprocessar este documento? Categorizações manuais feitas
  depois do envio inicial serão perdidas."

Botão de confirmação repete o verbo: "Apagar relatório", não "OK".

### 7.4 Sucesso é específico

- ❌ "Pronto!" / "Sucesso!"
- ✅ "Análise atualizada. 47 transações novas categorizadas."
- ✅ "PDF salvo em Downloads."

---

## 8. Inclusão e neutralidade

- **Composição familiar:** o produto trata família como unidade
  fiscal/patrimonial — pode ter 1 pessoa, casal, filhos, pais
  dependentes. Não assumir casal heterossexual.
  - ✅ "membros da família", "cônjuge", "dependente"
  - ✅ "responsáveis financeiros", "titulares"
  - ❌ "marido e esposa", "papai e mamãe"
  - ❌ "pai de família" como sinônimo de titular
- **Cônjuge:** termo neutro padrão. "Esposa/marido" só em copy onde o
  usuário **já preencheu** explicitamente o gênero (ex.: relatório que
  consome `family_members.json`).
- **Estado civil:** evitar prescrever. Se o produto perguntar, oferecer
  opções neutras ("solteiro(a)", "casado(a) ou união estável",
  "outro").
- **Concordância:** prefira plural neutro ou reformulação à barra
  `(o/a)` quando possível.
  - ✅ "responsáveis pelo aporte" (plural neutro)
  - Aceitável: "titular(a)" se a alternativa ficar artificial
  - ❌ "o/a esposo/a do(a) titular"

---

## 9. Anti-padrões proibidos

| ❌ Proibido | Por quê | ✅ Substituir por |
| --- | --- | --- |
| **Emoji em label de KPI / título de card / categoria** | Quebra a11y (screen reader lê "carinha sorrindo"); reduz autoridade do produto fintech | Ícone Lucide ou SVG dedicado com `aria-label` (componente `<IconBadge>` planejado em REPORT_PREMIUM_PLAN Fase 3 — quando entrar, vira primitivo canônico). |
| **Emoji em copy de produto sério** | Idem | Texto + ícone semântico |
| **Exclamação em copy de produto** ("Pronto!", "Uau!", "Ótimo!") | Tom infantil; produto financeiro fala calmo | Frase declarativa: "Análise atualizada." |
| **"Ops!"**, **"Putz"**, **"Eita"** em erro | Coloquial demais para fintech | "Não conseguimos..." + ação |
| **Métaforas de gamificação** ("conquistou", "level up", "streak") | Conflita com seriedade financeira | Linguagem direta: "atingiu a meta", "12 meses seguidos" |
| **Inglês cru sem tradução**: "dashboard", "insights", "feedback" em copy de UI PT-BR | Mathoms é PT-BR primário; reservar inglês para termos sem tradução boa | "painel", "análise", "comentário" |
| **Caps lock em frase** | Grita; a11y lê letra por letra em screen reader | Use peso (`font-bold`) ou cor |
| **"Clique aqui"** como label de link | Sem contexto; falha WCAG 2.4.4 | Verbo + objeto: "Baixar relatório", "Ver fatura" |
| **Promessa de retorno** ("vai render X%", "garante R$ Y") | Risco regulatório (CVM); falso em produto que só consolida | "Projeção com base em premissa Z (revisar anualmente)" |
| **"Em breve"** sem data | Compromisso vazio | Data ou "previsto para [trimestre/ano]" ou simplesmente omitir o item |

**Nota sobre emojis em `config/`:** alguns YAML do produto carregam
emojis em código de categoria (`📈 Aporte IF`, `🟰 Impostos`,
`▶ Folga livre`) — esses **devem** virar `<IconBadge>` em fase de
cleanup separada (lane `copy-emoji-cleanup`, P2). Não enumerar todos
aqui.

---

## 10. Onde aplica

| Superfície | Aplica? | Notas |
| --- | --- | --- |
| `app.mathoms.ai` (UI cliente) | ✅ Total | Inclui modais, toasts, erros, vazios |
| Relatório `/reports/[id]` | ✅ Total | Inclui PDF exportado via Playwright |
| `mathoms.ai` (landing) | ✅ Total | Copy comercial deve passar pela mesma régua |
| E-mails transacionais | ✅ Total | Mesmo formato monetário, mesma capitalização |
| `ops.mathoms.ai` (console interno) | ⚠️ Parcial | Pode usar termos do pipeline (`stage`, `E5`) — leitor é staff. Tom segue o mesmo. |
| `docs/**`, ADRs, RUNBOOK | ❌ | Documentação técnica usa jargão livre |
| Logs `mathoms.*` (JSON) | ❌ | Locale-agnostic, formato fixo |
| Comentários de código | ❌ | Vide CLAUDE.md §Comentários |

---

## 11. Hierarquia de fontes (resolução de conflito)

Em ordem decrescente de autoridade quando dois docs divergirem:

1. **Decisão de produto (ADR ou docs/PRODUCT.md)** — se uma ADR
   define um termo, ele ganha.
2. **Este documento (`COPY_GUIDELINES.md`)** — fonte de verdade
   para tom, terminologia e formato.
3. **`config/methodology.md`** — fonte de verdade para metodologia
   e regras financeiras consagradas de planejamento patrimonial
   brasileiro. Conflito de *nome* perde para o §2 deste guia;
   conflito de *fórmula* vence sempre. Atribuição direta a autores
   /metodologias-pilar é admitida internamente (config rationale,
   docstrings, ADRs) — **proibida em copy user-facing** (§13).
4. **`config/report_layout.yaml`** — labels canônicos do relatório.
   Atualizar para alinhar com §2 quando divergir.
5. **`docs/methodology/definitions.md`** — definições operacionais (categorias,
   instituições, regras de roteamento). Atualizar idem.
6. **Código** — último recurso; mudança de label sem atualizar §2
   é débito de copy.

Sempre que descobrir conflito, abrir PR no nível mais alto que cobrir
o problema (de cima para baixo).

---

## 12. Como contribuir

1. Mudança de termo / regra de formato: **PR com diff em
   `docs/reference/COPY_GUIDELINES.md`** + sincronização nos docs derivados
   (§11). Aprovação: **product-designer** (revisor) +
   **financial-planner** (quando termo afetar metodologia).
2. Mudança grande de tom (ex.: adicionar `tu` em algum contexto):
   abrir ADR — afeta produto inteiro.
3. Termo novo descoberto em PR de feature: linha nova no §2 com
   `@yyyy-mm-dd` antes de mergear o feature, mesmo que provisória.
4. Conflito não-resolvido: abrir issue marcando ambos os agentes
   acima.

---

## 13. Sigilo de fontes metodológicas (LEGAL/IP — bloqueante)

Mathoms baseia-se em metodologias consagradas de planejamento
patrimonial brasileiro, mas **não tem licença/autorização** das obras,
marcas pessoais ou cursos dos autores que as codificaram. Toda copy
user-facing (escopo de §10 col. ✅) **DEVE** evitar atribuição direta —
uso público sem licença é violação de marca pessoal/curso e cria
dependência reputacional não-sustentável (sinaliza "advisor terceirizado"
em vez de "metodologia própria validada").

Política e racional consolidados em
[.claude/agents/gtm-strategist.md](../../.claude/agents/gtm-strategist.md)
§"Princípios inegociáveis › Sigilo de fontes metodológicas".

### 13.1 Termos proibidos em superfície pública

Não use em UI cliente, relatório `/reports/[id]`, e-mail transacional,
PDF exportado, landing `mathoms.ai`, blog, social, materiais de
imprensa, pitch deck, comparativo competitivo, ToS / privacy policy:

- **Nomes próprios:** "Bruno Perini", "Gustavo Cerbasi", "Raul Sena"
- **Marcas / canais / cursos:** "Viver de Renda", "AUVP", "Equilíbrio
  Financeiro", "Casais Inteligentes"
- **Endossos atribuídos:** "baseado em [autor]", "metodologia [marca]",
  "estilo [autor]", "[autor] recomenda"
- **Capturas, citações, frases atribuídas** (mesmo parafraseadas
  reconhecíveis)

### 13.2 Substituições canônicas

| Em vez de (proibido público) | Use |
| --- | --- |
| "Metodologia AUVP / Perini / Cerbasi" | "Metodologia consagrada de planejamento patrimonial brasileiro" / "Padrão de mercado de wealth management" / "Regras estruturadas que planejadores CFP aplicam" |
| "Contrafluxo AUVP" / "Contrafluxo" | "Alocação contracíclica" / "Estratégia adaptativa à curva de juros" |
| "Independência financeira (Perini)" | "Independência financeira" (conceito é genérico — não atribuir) |
| "Viver de Renda" | "Patrimônio gerador de renda" / "Renda passiva sustentada" |
| "Estilo Cerbasi para casal" | "Planejamento patrimonial do casal" / "Decisão financeira a quatro mãos" |
| "Equilíbrio Financeiro (Cerbasi)" | "Equilíbrio entre presente e futuro" / "Balanço presente-futuro" |
| "Visão Cerbasi" (em alíquota / IRPF) | "Visão sobre renda total" / "Alíquota sobre renda total declarada" |

### 13.3 Auditoria obrigatória antes de mergear

Antes de mergear PR que toque superfície user-facing (§10 col. ✅):

```bash
grep -i -E 'perini|cerbasi|auvp|raul[ _]sena|bruno[ _]perini|gustavo[ _]cerbasi|viver[ _]de[ _]renda|equil[ií]brio[ _]financeiro|casais[ _]inteligentes' <arquivos>
```

Resultado ≠ vazio em arquivo user-facing = **bloqueia merge**. CI gate
automatizado é débito explícito (lane `sigilo-grep-ci-gate`, P1) — até
entrar, é responsabilidade do reviewer.

### 13.4 Atribuição interna (PERMITIDA)

Em código, docstrings, type names, ADRs, planos `docs/plan/*`,
briefings de agente (`.claude/agents/financial-planner.md`,
`.claude/agents/gtm-strategist.md`), `config/scoring.json` `_comment`,
`config/methodology.md`, CLAUDE.md, CHANGELOG, este próprio doc em
seções de rationale/hierarquia: **atribuição é PERMITIDA** — é como o
time raciocina sobre domínio.

ADR-143 (methodology = code) consolida o padrão: regra vive em
docstring co-localizada com enforcer; nome do autor ajuda a discutir
trade-offs internamente sem nunca virar prescrição pública. Class
names como `EquilibrioCerbasiAnalyzer`, ids internos como
`equilibrio_cerbasi`, e variantes técnicas como `tone="cerbasi"`
**permanecem** — só não devem aparecer como string user-facing.

### 13.5 Débitos rastreados

Cleanup do legado contaminado é P0 separado deste guide:

- **Frontend:** `frontend/src/components/report/sections/ApendicesSections.tsx`
  (bios de autores em apêndice do relatório), `cards/ContrafluxoCard.tsx`,
  `cards/EquilibrioCerbasiCard.tsx`, `cards/IrpfSplitTrabalhoCapitalCard.tsx`
  (caption "Métrica Perini"), `charts/AliquotaDualGauge.tsx` (title
  "RFB e Cerbasi"), `sections/S7IndependenciaSection.tsx` (tooltip
  "5% Perini"). Track sugerido: `report-sigilo-frontend-cleanup`.
- **CI gate:** automatizar §13.3 como hook pre-commit + gate em CI.
  Track sugerido: `sigilo-grep-ci-gate`.
- **Drift doc-vs-code:** após esta entrada, §2 prescreve "Alocação
  contracíclica" mas frontend ainda renderiza "Contrafluxo" (em
  `ContrafluxoCard.tsx`); resolvido no track `report-sigilo-frontend-cleanup`.

### 13.6 Fim da regra

Esta regra perdura **até existir contrato de licenciamento explícito**,
registrado em ADR. Sem isso, nenhuma exceção — nem em pitch para
investidor, nem em comparativo competitivo, nem em material para
imprensa especializada.
