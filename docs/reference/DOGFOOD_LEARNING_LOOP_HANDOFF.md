# Dogfood Learning Loop — guia do beta tester

> ⚠️ **HISTÓRICO — gate fechado (PASS por decisão do owner, 2026-07-02,
> audit-vault r4).** O ritual de 7 dias não foi executado; o gate técnico
> (11/11 invariantes, PR #202) foi aceito como evidência e o plano
> [CAT_LEARNING_LOOP](../archive/CAT_LEARNING_LOOP-2026-07-08.md) está `done`.
> A premissa "interface só via API/curl" abaixo é da época: a UI mínima (P4)
> shipou em 2026-05-11 (PR #203 — toast + `CreateRuleDialog` + badge "Regra").
> Reutilizar este guia **apenas** se o gate for reaberto (revert_rate alto /
> não-adoção em uso real).

> Você está nos ajudando a validar uma feature do Mathoms antes do
> lançamento. Estimativa: **30 min/dia × 7 dias**, mais 30 min de
> conversa final no dia 7.

> **Versão para o PM conduzir este gate:**
> [docs/reference/DOGFOOD_PM_CHECKLIST.md](DOGFOOD_PM_CHECKLIST.md).
> **Detalhe operacional/técnico (curl, flags, Celery):**
> [docs/reference/RUNBOOK.md §9](RUNBOOK.md).
> **Plano canônico da feature:**
> [docs/archive/CAT_LEARNING_LOOP-2026-07-08.md](../archive/CAT_LEARNING_LOOP-2026-07-08.md).

---

## O que é

O Mathoms organiza seus gastos em categorias automaticamente — "Uber" vira
"Transporte · App", "Padaria do Zé" vira "Alimentação · Compras", e assim
por diante. Esse motor acerta a maioria, mas tem casos óbvios que ele erra
ou não enxerga porque são específicos da sua vida (o boleto da academia
que parece "TED FULANO LTDA", o débito recorrente do clube, o nome curioso
do seu fornecedor de café).

O **learning loop** te deixa criar **regras simples** ("toda vez que tiver
a palavra X na descrição, categoriza como Y"), e essas regras passam a
valer pra você daquele momento em diante. Sua tarefa nesses 7 dias é usar
isso como você usaria de verdade e nos dizer se ajuda — ou se atrapalha.

---

## O que você vai fazer (TL;DR)

1. Importar seu extrato real no Mathoms (12 meses é o ideal — quanto mais
   histórico, mais regra você vai querer criar).
2. Abrir o relatório, identificar categorizações "óbvias mas erradas" que
   te incomodam.
3. Criar **5+ regras** ao longo de 7 dias, em ritmo natural. Não force.
4. Anotar **3-4 reflexões curtas** por dia neste documento (template
   abaixo).
5. No dia 7, responder 3 perguntas-chave e conversar 30 min com o PM.

---

## Setup (10 min, único)

1. **Login** no Mathoms com a conta que o PM te enviou.
2. **Importar extrato** real — peça ao PM para te liberar isso, ou suba
   pelo `/inbox` se você já sabe.
3. **Feature flag**: o PM já liga `learning_loop_enabled` no seu
   workspace antes de você começar. Se aparecer mensagem "feature
   indisponível" ao tentar criar regra, chame o PM — flag não foi
   ligada.

Se travou em qualquer passo: **escreva no diário e chame o PM**. Setup
travado já é um achado.

---

## Como criar uma regra

> Por enquanto a interface é via API (CLI / `curl`). O frontend visual
> entra **depois** deste teste — se ele passar. Você está ajudando a
> decidir se vale gastar o tempo de design e implementação na UX visual.

O PM vai te entregar um arquivo com:

- `API` — endereço base (algo como `https://api.staging.mathoms.ai/v1`)
- `TOKEN` — seu JWT (válido por 7 dias)
- `WS` — seu workspace_id

**Comandos prontos** (cole no terminal substituindo a regra):

```bash
# 1. Pré-visualizar (não cria, só mostra o que aconteceria)
curl -X POST "$API/workspaces/$WS/categorization/rules/preview" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"keyword":"UBER","target_category":"Transporte · App"}'

# 2. Criar (efetiva — meses abertos passam a usar a regra)
curl -X POST "$API/workspaces/$WS/categorization/rules" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"keyword":"UBER","target_category":"Transporte · App","priority":100}'

# 3. Listar regras suas
curl "$API/workspaces/$WS/categorization/rules?enabled=true" \
  -H "Authorization: Bearer $TOKEN"

# 4. Apagar regra (anota antes no diário por que apagou)
curl -X DELETE "$API/workspaces/$WS/categorization/rules/<rule_id>" \
  -H "Authorization: Bearer $TOKEN"
```

Comandos completos (status async, disable etc.) em
[RUNBOOK §9.2](RUNBOOK.md).

**Fluxo recomendado:**

1. Roda o **preview** primeiro — ele te mostra quantas transações vão ser
   afetadas e quantas estão em meses já publicados (não mudam — veja
   *Caveats*).
2. Se o resultado faz sentido → **cria** com a mesma keyword.
3. Abre o relatório no navegador (`/reports/[id]` do seu workspace) e
   confere se a categoria mudou nos meses abertos.

---

## Diário (preencha um bloco destes por dia)

Copie esse bloco 7 vezes e preencha conforme rodam os dias. **Use ranges
de valor (`R$ 2-3 mil`) em vez de valor exato** — nada de número fechado
de salário ou saldo neste diário.

```text
### Dia N (data: ____-__-__)

Regras criadas hoje:
- "..." → "..."     (preview mostrou ~X matches, achei OK?)
- "..." → "..."

Regras revertidas / apagadas hoje:
- "..." motivo: "..."     (autoria categorizou errado depois? mudei de ideia?)

Como você se sentiu hoje (1-2 frases):
>

Confusões / dúvidas (qualquer coisa que travou ou foi não-óbvio):
>

Erros que viu (auto-categorização errada que regra ainda não pegou):
>
```

Não precisa criar regra todo dia. Dia sem regra é dado também — anote
*por que* não criou (não viu nada errado? não teve tempo? sistema travou?).

---

## Pergunta-chave (responda no dia 7, antes da entrevista)

Responda com **SIM / NÃO / TALVEZ + 1-2 frases de justificativa**:

1. **Vou continuar usando regras se a feature ficar disponível?** Por
   quê?
2. **A regra apareceu na primeira categoria certa quando você criou?**
   Cite **2 exemplos** — 1 que funcionou bem, 1 que funcionou mal (ou se
   não tem o ruim, diga isso).
3. **Você criaria uma regra de novo se fosse outro mês?** Quais cenários
   te fariam abrir o terminal de novo?

---

## Coisas para prestar atenção (caveats conhecidos)

Esses são os pontos onde o time já sabe que a feature pode comportar de
forma surpreendente. Se você vir um destes, **reporte no diário** mesmo
que pareça menor:

- **PIX entre cônjuges / contas suas:** regra "PIX → categoria X" pode
  capturar transferências entre suas contas e a do(a) cônjuge — que não
  são despesa, são transferência interna. Se acontecer, anote: data,
  descrição, regra aplicada.
- **Sazonalidade (13º salário, IPVA, IPTU):** padrões mensais só
  aparecem 1×/ano. Em 7 dias você **não vai testar** se a regra "13º
  SALÁRIO" funciona em dezembro. Não invente uso artificial — registre
  no diário se sentiu vontade de criar mas saberia que não veria
  resultado.
- **Mês fechado / publicado:** se você publicou janeiro e cria regra em
  fevereiro, janeiro **não muda** — a regra só vale daquele mês em
  diante. Isso é proposital (ADR-187). O preview deve avisar
  ("X matches em meses fechados, Y em meses abertos"); se não avisa
  claro, **reporte**.
- **Dialog de confirmação:** quando o preview mostra "essa regra vai
  alterar transações em meses abertos", aparece um aviso. Se você
  perceber que está clicando "confirmar" no automático sem ler, **isso é
  um achado importante** — significa que o aviso virou ruído. Anote.
- **Estorno (charge-back / cancelamento):** pares de estorno (compra
  R$ 100 + reembolso −R$ 100) ainda não são detectados. Se a sua regra
  aparecer aplicada num estorno, anote.

---

## Como reportar problemas

- **Bug urgente** (sistema travou, dados sumiram, erro 500 recorrente):
  contate o PM direto pelo canal combinado.
- **Sugestão de UX** (algo que poderia ser mais claro, mais rápido,
  mais óbvio): **anote no diário** — a entrevista do dia 7 vai cobrir.
- **Métrica que não bate** (você criou 6 regras mas o sistema diz que
  tem 4): anote número observado vs número que você esperava, e a hora
  aproximada.

---

## O que **não** fazer

- **Não force casos artificiais** ("vou criar regra X só pra testar o
  sistema"). O teste depende de uso natural — regras artificiais poluem
  a métrica de revert rate.
- **Não publique mês** durante o teste, a menos que essa seja a sua
  rotina normal. Publicação congela retroativos.
- **Não revele valores reais** (R$ 12.345,67) no diário. Use range
  (R$ 10-15 mil) ou apenas "valor alto / médio / baixo".
- **Não convide outras pessoas** para o seu workspace durante o teste.
  Multi-usuário tem comportamentos diferentes que estão fora do escopo
  deste gate.

---

## Após 7 dias — o que você devolve

1. **Este documento preenchido** (7 dias de diário).
2. **Resposta às 3 perguntas-chave** do dia 7.
3. **Lista de regras finais** — pode rodar:
   ```bash
   curl "$API/workspaces/$WS/categorization/rules?enabled=true" \
     -H "Authorization: Bearer $TOKEN" > minhas_regras_finais.json
   ```
   e enviar o arquivo. Indique quais foram revertidas / apagadas e o
   porquê.
4. **Entrevista de 30 min** (Zoom / voz) com o PM no dia 7 ou 8 — pauta
   é o roteiro do PM (ver `DOGFOOD_PM_CHECKLIST.md`).

---

## Como o time avalia (transparência total)

Critério de aprovação do gate (PM mede com SQL + sua entrevista):

- **≥5 regras persistentes** (criadas e não-revertidas no mesmo dia).
- **revert_rate ≤ 30%** — quanto da aplicação automática você teve que
  desfazer manualmente.
- **≥3 regras com ≥3 matches retroativos cada** — sinal de que pegou
  padrão real, não exceção.
- **Sua resposta à pergunta 1** ("vou usar isso?") precisa ser **SIM
  com confiança**.
- **Avaliação subjetiva** do PM: você usaria de verdade, ou disse SIM por
  educação?

Se aprovar → o frontend visual (P4) entra na fila. Sua experiência
informa o design daquela UX.
Se reprovar → o time pausa e revisa **antes** de gastar tempo com
frontend. Sua reprovação é tão útil quanto a aprovação.

Obrigado por dedicar essa semana. Sem você não fechamos esse gate.
