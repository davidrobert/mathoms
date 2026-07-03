# Dogfood Learning Loop — checklist do PM

> ⚠️ **HISTÓRICO — gate fechado (PASS por decisão do owner, 2026-07-02,
> audit-vault r4).** Não executar este roteiro: o dogfood ritual foi
> dispensado, o gate técnico (11/11) foi aceito como evidência e o pós-gate
> prescrito abaixo já foi superado (P4 shipou sem track em 2026-05-11,
> PR #203). Reutilizar **apenas** se o gate for reaberto (revert_rate alto /
> não-adoção em uso real).

> Roteiro operacional do PM para conduzir o gate dogfood do
> [A12.cat-learning-loop](../plan/CAT_LEARNING_LOOP/_README.md).
> Pareia com o guia entregue ao tester:
> [docs/reference/DOGFOOD_LEARNING_LOOP_HANDOFF.md](DOGFOOD_LEARNING_LOOP_HANDOFF.md).
> Detalhe técnico/curl/flags: [docs/reference/RUNBOOK.md §9](RUNBOOK.md).

Premissa: o tester pode ser CEO, cônjuge, sócio, beta tester de
confiança. Critério é **ter extrato real + 7d de disponibilidade**, não
job title.

---

## Antes de começar (D-1)

- [ ] **Friendly user identificado** e topa contribuir os 7d + entrevista.
- [ ] **Workspace real** do tester provisionado (não dev/staging
      compartilhado — workspace dedicado com dados próprios dele).
- [ ] **Gate técnico passou** — `_scratch/dogfood_gate_a12_report.md` (ou
      equivalente) com PASS. **Gate humano só roda depois**; nunca em
      paralelo. Pré-req documentado em RUNBOOK §9.
- [ ] **Feature flag** `learning_loop_enabled=true` ativada **no
      workspace dele**:
      ```python
      from backend.app.services.feature_flags_service import set_flag
      await set_flag(ws_id, "learning_loop_enabled", True, db=db)
      ```
      Default global continua `False`.
- [ ] **Celery worker** com `--concurrency=1` (RUNBOOK §9.1).
- [ ] **Redis** disponível (status async + idempotency).
- [ ] **Token JWT** com validade ≥ 8 dias gerado e entregue.
- [ ] **Walkthrough síncrono (15 min)** explicando: o que é, o que
      esperar, como abrir diário, como reportar bug urgente. Não pular
      este passo — economiza 2-3 ping-pongs no dia 2.
- [ ] **`DOGFOOD_LEARNING_LOOP_HANDOFF.md` enviado** + arquivo com `API`
      / `TOKEN` / `WS` preenchido.
- [ ] **Canal de bug urgente** combinado (WhatsApp / Slack / Telegram —
      o que ele já usa). Não força ferramenta nova no tester.
- [ ] **Data oficial do D0** registrada (`gate dogfood A12 — D0 =
      YYYY-MM-DD`) na lane do plano canônico.

---

## Durante (check-ins curtos)

Não polua o tester com check-in diário. **3 toques** em 7 dias é o
suficiente para detectar bloqueio cedo sem virar babá.

### Dia 2 (manhã)

- [ ] Tester criou **≥1 regra**? Se não: bloqueado em setup, login,
      flag, token? **Desbloqueie hoje** — D2 sem regra = D7 sem dados.
- [ ] Diário tem entrada do D1?
- [ ] Algum bug urgente reportado em outro canal?

### Dia 4 (qualquer hora)

- [ ] Olhar diário até aqui — sinais positivos (criou regra, comentou
      que ajudou) vs negativos (criou e reverteu, reclamou de aviso,
      ignorou feature).
- [ ] Rodar queries SQL (§Métricas) para ter número parcial.
- [ ] Se `revert_rate > 50%` no D4: **mensagem amistosa** ao tester
      perguntando o que está confundindo. Não rode entrevista cedo.

### Dia 6 (final do dia)

- [ ] Confirmar entrevista do D7 (horário, link Zoom / voz).
- [ ] Reler diário inteiro → preparar perguntas específicas do roteiro
      do D7 com base no que o tester já anotou.
- [ ] Rodar queries finais e ter número antes da entrevista (não
      durante).

---

## Métricas a coletar (D7 manhã)

Workspace_id do tester preenchido em `$WS`. Roda no banco do ambiente
onde o dogfood corre (staging dedicado ou prod com workspace isolado).

```sql
-- 1. Regras persistentes (criadas e não-deletadas)
SELECT COUNT(*) AS persistent_rules
FROM categorization_rules
WHERE workspace_id = :ws AND deleted_at IS NULL;

-- 2. Total de aplicações automáticas (denominador do revert_rate)
SELECT COALESCE(SUM(applied_count), 0) AS total_applies
FROM categorization_rules
WHERE workspace_id = :ws AND deleted_at IS NULL;

-- 3. revert_rate (manual edits que reverteram a categoria sugerida)
SELECT
  COALESCE(SUM(revert_count_manual_edit), 0) AS reverts,
  COALESCE(SUM(applied_count), 0) AS applies,
  CASE WHEN SUM(applied_count) > 0
    THEN ROUND(SUM(revert_count_manual_edit) * 100.0 / SUM(applied_count), 1)
    ELSE NULL
  END AS revert_rate_pct
FROM categorization_rules
WHERE workspace_id = :ws AND deleted_at IS NULL;

-- 4. Regras com ≥3 matches retroativos cada
SELECT COUNT(*) AS rules_with_3plus_matches
FROM categorization_rules
WHERE workspace_id = :ws
  AND deleted_at IS NULL
  AND applied_count >= 3;

-- 5. Detalhe (para olhar caso a caso na entrevista)
SELECT id, keyword, target_category, applied_count,
       revert_count_manual_edit, created_at, deleted_at
FROM categorization_rules
WHERE workspace_id = :ws
ORDER BY created_at;
```

Salve o resultado em `_scratch/dogfood_a12_results_<YYYY-MM-DD>.md` (não
commitar — dados sensíveis).

---

## Dia 7 — entrevista (30 min, Zoom / voz)

**Setup:** câmera off ou on, escolha do tester. Grave **só** se ele
autorizar. Tenha o diário aberto + resultado das métricas.

### Roteiro (5 perguntas, ordem importa)

1. **"Vou continuar usando se virar feature pública?"** — escuta longa,
   não interrompa, deixe ele divagar.
   - SIM com confiança + cenários concretos = ✅
   - SIM com hesitação ou "acho que sim" = ⚠️
   - NÃO ou "talvez" ou "se mudasse X" = ❌

2. **"Quando você criou regra, a categoria certa apareceu logo?"** —
   peça **2 exemplos concretos**: 1 que funcionou, 1 que não.
   - 1 bom + 1 ruim = saudável (tester crítico, sinal positivo)
   - Só bons (sem nenhum ruim) = pode estar puxando dados pra agradar;
     re-pergunte: "nenhum momento em que ficou frustrado?"
   - Só ruins = extração de keyword tem problema; **pausa P4** mesmo
     que outras métricas passem

3. **"Você criaria uma regra de novo se fosse outro mês?"** — explora
   cenário hipotético.
   - SIM com cenários específicos ("quando vier 13º", "se mudar de
     gestora") = ✅
   - "Talvez, depende" = ⚠️
   - NÃO ou silêncio = ❌

4. **"O que te frustrou mais? Onde travou?"** — pergunta aberta. Cale
   a boca por 10s mesmo se ele pausar. Esse silêncio puxa o
   reclame-mais.

5. **"Se você pudesse mudar UMA coisa antes do frontend visual entrar,
   o que seria?"** — input direto pro product-designer no P4.

Anote textualmente as respostas das perguntas 1, 3 e 5. Parafraseando
perde nuance.

---

## Critério de aceite final (PASS / PARTIAL / FAIL)

Marca os 5 critérios:

| # | Critério | Source |
|---|----------|--------|
| 1 | ≥5 regras persistentes | SQL #1 |
| 2 | revert_rate ≤ 30% | SQL #3 |
| 3 | ≥3 regras com ≥3 matches | SQL #4 |
| 4 | "Vou continuar?" — SIM com confiança | Pergunta 1 |
| 5 | "Faria de novo?" — SIM com cenário | Pergunta 3 |

**Cortes:**

- **5 de 5** → **PASS** clean → P4 frontend inicia, sem ressalva.
- **4 de 5** → **PASS condicional** → P4 inicia, *com* nota da
  ressalva. Ressalva vira input no design brief do `product-designer`.
- **3 de 5** → **PARTIAL** → senta com `product-designer` antes de
  iniciar P4. Decisão: ajustar escopo P4 ou repetir gate com tester
  diferente em 14d.
- **≤2 de 5** → **FAIL** → reabre P2/P3 (extração de keyword é o
  candidato mais provável). ADR-189 Proposto se mudar invariante.
  Próximo gate em 30d com tester novo.

**Override do PM (subjetivo, mas exigido):** mesmo com 5/5 numéricos, se
você sentiu na entrevista que o tester usava por obrigação ou que
respondeu SIM por gentileza, **rebaixe para PARTIAL** e justifique no
relatório. O número não substitui leitura humana.

---

## Pós-gate (D8-D10)

- [ ] Salvar resultado consolidado em `_scratch/dogfood_a12_outcome.md`
      (PASS / PARTIAL / FAIL + métricas + 3 quotes da entrevista, sem
      PII).
- [ ] **Atualizar lane** [`docs/sprint/A12/lanes/cat-learning-loop.md`]
      (ou path equivalente) §Status com resultado e link para o relatório.
- [ ] **Plano canônico**
      [`docs/plan/CAT_LEARNING_LOOP/_README.md`](../plan/CAT_LEARNING_LOOP/_README.md):
      marca gate ✅ / ⚠️ / ❌ e data.
- [ ] **CHANGELOG**: 1 entrada (`docs(a12): gate dogfood — PASS / PARTIAL
      / FAIL — YYYY-MM-DD`).
- [ ] **Se PASS ou PASS condicional:** criar track
      `cat-learning-loop-p4-frontend.md` e abrir lane no próximo sprint.
      Anexar ao track: as 3 ressalvas da entrevista + a resposta da
      pergunta 5.
- [ ] **Se PARTIAL:** abrir ADR `Proposto` se houve aprendizado
      arquitetural (ex.: "preview precisa de prévia de impacto retroativo
      por mês, não só total"). 1 rodada com `product-designer`, depois
      decidir: P4 com escopo ajustado vs gate de novo.
- [ ] **Se FAIL:** track de "retomada P2/P3" + ADR-189 Proposto se
      invariante muda. Próximo tester (≠ deste) já cogitado.
- [ ] **Mensagem de obrigado** ao tester com link pro changelog que
      registra a participação dele. Fecha o loop social — você vai
      precisar de tester de novo em V2.

---

## Anti-padrões a evitar

- **Rodar gate dogfood antes do gate técnico passar.** Tester reclamando
  de bug que script automatizado pegaria = desperdício do crédito social
  dele.
- **Mais de 1 tester em paralelo na primeira rodada.** Você precisa
  conversar fundo com 1 pessoa, não fazer survey com 5. Tester #2
  entra **depois** que o ciclo do #1 fechou (se FAIL).
- **Entrevista cancelada / postergada.** O número não dá o veredito
  sozinho — entrevista é parte do critério, não opcional. Se ele faltar
  no D7, reagenda em ≤48h; se faltar de novo, gate falha por dados
  incompletos, não por culpa do produto.
- **PM faz a entrevista e codifica no mesmo dia.** Espace ≥24h —
  releitura no dia seguinte muda interpretação de pelo menos 1 ponto em
  metade dos gates.
