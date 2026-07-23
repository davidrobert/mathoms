# parse-certify — rubrica de veredito

Critérios de julgamento carregados sob demanda (o `SKILL.md` fica só com o
procedimento). Define o que **completude / corretude / consistência / precisão**
significam por tipo de documento na camada E0→E2, e — o mais importante — **qual
sinal é perda/corrupção silenciosa** (o modo de falha que a skill existe para
caçar). Deriva da certificação de 3 corpora na Sprint A38.

## Os 5 vereditos (fail-closed)

Cada documento recebe **um** veredito. A ordem importa: só sobe para `completo`
quem tem **evidência de fechamento** (checksum que prova que nada faltou). Sem
essa evidência, o teto é `coberto-sem-verificação` — nunca `completo`. Tratar
"parseou e não escalou" como `completo` é a **certificação falsamente-verde**
que esta rubrica proíbe.

| # | Veredito | Definição | É falha? |
|---|---|---|---|
| 1 | `completo` | Parseou **e** o checksum do tipo **existe e fecha** (ver tabela por tipo). | Não |
| 2 | `coberto-sem-verificação-de-soma` | Parseou, não escalou, mas **não há checksum** que prove que fechou (fatura sem gate Σ×total; CDB XLSX/HTML; extrato com saldo derivado). É **dívida de verificação**, não sucesso. | Parcial — reportar |
| 3 | `escalado-honesto` | 0 tx / conservação quebrada / sem parser / dormância **corroborada** → `requires_llm_fallback`/`needs_review` (ADR-342). Corretude > cobertura. | **Não** — é o comportamento correto |
| 4 | `perda/corrupção silenciosa` | Regra anti-falso-positivo abaixo satisfeita. O pior modo: artefato "ok" com dado parcial/errado. | **Sim — P0** |
| 5 | `não-coberto` | Formato sem parser **e** sem escalação. | Sim — candidato a lane |

## Contrato de completude por tipo

Fonte da observação = o parser (via harness). O DB é 2ª camada (persistência),
nunca oráculo de completude — um parcial silencioso é, por construção,
indistinguível de um completo **no artefato final**.

| Tipo | Chave E2 | Checksum que autoriza `completo` | Estado do checksum hoje |
|---|---|---|---|
| Extrato | `transacoes` | `conservacao_verificavel=True` **e** `conservation_gap_cents == 0` | ✅ onde o parser declara `conservacao_verificavel` |
| Fatura | `transacoes` | Σ lançamentos == **`total_compras`** (cents), **nunca** `saldo_atual` | ⚠️ gate WARN existe (`apply_fatura_checksum`), **dormente** até parser setar `total_lancamentos_conferivel` |
| Investimento | `posicoes` + `tipo="cdbresumo"` | Σ `valor_atual` == total de escopo igual às linhas (cents) | ✅ Santander CDB PDF+XLSX, Itaú HTML-XLS (`apply_cdb_checksum`, int cents) |

Onde o checksum **não existe**, a completude é genuinamente **não-verificável no
E2** → veredito máximo `coberto-sem-verificação-de-soma`. Isso não é pessimismo:
é o que separa "provei que fechou" de "parseou algo". A lista de checksums
faltantes vira o backlog da própria skill (§Extensões do harness no SKILL.md).

## Sinais de perda/corrupção silenciosa (regra anti-falso-positivo)

Só marque `perda/corrupção silenciosa` quando **todas**:

1. Harness `status=ok` (parseou sem exceção) **e**
2. Checksum do tipo **passa** ou é **inexistente** mas há sinal de truncamento
   (ver abaixo) **e**
3. Existe `content_hash` casando em `documents` (o doc foi realmente ingerido) **e**
4. O artefato **vivo não-fallback** em `pipeline_artifacts` para `(ws, stage,
   artifact_key)` está ausente / vazio / divergente **e não é stub-superseding**.

Qualquer outra combinação cai numa classe benigna (§Divergências esperadas).

Sinais concretos de truncamento (aprendidos em A38 — cada um foi um bug real):

- **`n_tx` plausível mas parcial** — Itaú layout 2026 perdia ~50% das tx com
  `status=ok`. Detecção: `raw_rows_detected` (linhas datadas no texto bruto) ≫
  `n_tx`, sem escalar.
- **0 tx com nota falsa "sem lançamentos"** — C6 Global USD/EUR retornava 0 tx
  com 56–199 linhas reais e marcava dormência. Detecção: `raw_rows_detected > 0`
  com `n_tx == 0` e `escalated=False` → dormância **não-corroborada** (a emenda
  A38.l14 exige saldo sem mudança onde `conservacao_verificavel`).
- **Moeda errada somada** — Wise USD tratado como BRL. Detecção: `moeda`
  divergente do conteúdo/subtipo; valores em escala incoerente.
- **Fatura truncada** — `total_fatura` presente mas Σ itens < total, `status=ok`.
  Detecção: checksum Σ×total (quando o harness passar a emiti-lo).

## Divergências esperadas harness↔DB (benignas — nunca "silenciosa")

O harness roda E0→E2 **isolado** (regex-only, tmpdir, fora do fluxo de
upload/unlock). Rotule, não alarme:

- **Classificação regex-only vs LLM/manual** — harness usa `classify_file` (sem
  LLM); upload usa `classify_document` (regex→LLM<0.8). `doc_type`/`confidence`
  divergem para docs classificados por LLM ou reclassificados à mão.
- **Dedup** — DB tem **≤** contagem do dir (SHA-256 exato bloqueia; fuzzy seta
  `possible_duplicate_of_id`). **Reconcilie por `content_hash`, nunca por
  contagem.** Arquivo no dir ausente do DB com hash casando = deduplicado
  (benigno); ausente **sem** hash casando = investigar.
- **Supersede / incremental (ADR-080 + ADR-342 §Decisão 3)** — o stub
  (`requires_llm_fallback`, `transacoes:[]`) é o estado **correto** de um doc
  escalado. Leia o artefato **vivo não-fallback**; stub = `escalado-honesto`,
  não "vazio=silencioso".
- **Cripto em repouso** — se os originais em `storage/<uuid>/data/` estiverem
  Fernet-encrypted, o harness lê bytes diferentes do que a produção destrancou →
  parse de lixo → falso "silêncio". **Pré-condição:** aponte o harness para
  originais legíveis (destrancados). Confirme o estado-em-repouso antes de
  concluir qualquer silêncio.

## Divergência de tolerância de conservação

O harness usa float `abs(diff) < 0.011`; a produção usa `conservation_gap_cents`
(cents, tolerância zero). Para o veredito ser idêntico ao gate real, **use a
semântica de cents** ao julgar — um gap de 1 centavo é `WARN` na produção, não
`completo`. `conservacao=True` com `conservacao_verificavel=False` é
**tautologia** (saldo derivado), não evidência → teto `coberto-sem-verificação`.

## Cobertura de grupos (v1)

- **No escopo v1:** `financial_statements` (extratos, faturas, investimentos —
  o caminho E0→E2 que o harness exercita).
- **Fora do escopo v1** (cobertos por **outros** stages; rodá-los no harness E2
  os mislabela como falso `não-coberto`): `income_tax_br`/`income_tax_us` (IRPF →
  `extract_baseline`/`extract_irpf_full`), `real_estate`/`vehicles`
  (comprovantes/informes → `extract_comprovantes_bens`). O resolvedor lista os 5
  grupos com `in_scope_v1` (só `financial_statements` é `true`) — os demais
  aparecem para dar visão de cobertura, não para rodar no harness E2. Declarar
  explicitamente como follow-up com harness próprio (checksums de baseline
  patrimonial / total de informe / Σ bens). Nunca certificar o que não se exercita.
