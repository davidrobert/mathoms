# Smoke Test — Runbook Humano

> **Quem executa:** David Robert (owner do projeto)
> **Objetivo:** validação humana end-to-end do produto num workspace real de
> smoke. Protocolo reutilizado por gates que exigem sinal humano — snapshots
> de dogfood (§4.9, gate A26.l5 · [[ADR-282]]/[[ADR-287]]), G-f do
> DATA_LINEAGE e o gate humano do port Go ([[ADR-150]] §Gate humano).
> Checklist automatizado equivalente: [SMOKE_TEST.md](SMOKE_TEST.md).
>
> **Origem:** nasceu como gate A6b.5→A6c ([[ADR-103]]), executado e aprovado
> em 2026-04/05. O conteúdo específico daquele gate (§4.7 cutover disco↔DB,
> decisão A6c) foi arquivado em
> [docs/archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md](../archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md)
> (audit r6, decisão do owner 2026-07-03). A numeração das seções foi
> preservada — docs externos citam §4.9.

---

## 1. Pré-requisitos

```bash
# Redis, Python, Node instalados
docker --version         # ≥ 24
python --version         # ≥ 3.11
node --version           # ≥ 18
npm --version            # ≥ 9

# Dependências Python e Node já instaladas
source .venv/bin/activate
cd frontend && npm install && cd ..
```

---

## 2. Setup — <2 minutos

```bash
# 1. Gerar Fernet key para o smoke (ou usar qualquer valor base64 válido)
export MATHOMS_FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Subir stack
make smoke-up

# 3. Aguardar backend iniciar (health check)
sleep 5 && curl -s http://localhost:8000/health | python -m json.tool

# 4. Seed DB + fixtures
make smoke-seed
```

**Saída esperada do seed:**
```
smoke@mathoms.ai   → workspace Smoke Premium (id: xxxxxxxx…)
viewer@mathoms.ai  → workspace Smoke Free    (id: xxxxxxxx…)
Inbox: 6 fixture(s) copiado(s)
  + c6bank_extratoconta_202501-smoke.csv
  + c6bank_extratoconta_202502-smoke.csv
  + c6bank_extratoconta_202501-smoke_dup.csv
  + nubank_extratoconta_202501-smoke.csv
  + nubank_faturacartao_202501-smoke.csv
  + ambiguous_document-smoke.txt
```

---

## 3. Fixtures — O que adicionar manualmente

Estes arquivos não são gerados automaticamente. Providencie antes de executar
o checklist completo:

| Arquivo a criar | Destino | Cenário |
|-----------------|---------|---------|
| PDF com senha (qualquer PDF protegido por senha) | inbox manual | E0-unlock |
| XLSX de extrato bancário real (Itaú/Santander) | inbox manual | Parser XLSX |
| PDF simulando IRPF (IR 2024/2025 qualquer) | inbox manual | E1.5 LLM |

**Como adicionar arquivos manualmente:**
1. Abra a UI em http://localhost:3000
2. Login como `smoke@mathoms.ai / smoke123`
3. Vá em Documentos → Upload

---

## 4. Checklist de Smoke Test

Marque cada item. Ao final registre a execução (e snapshots de gate) na §5.

### 4.1 Auth + Acesso (5 checks)

- [ ] **A1.1** Registro de novo usuário (`test-new@mathoms.ai / test123`) funciona
- [ ] **A1.2** Login com `smoke@mathoms.ai / smoke123` retorna token
- [ ] **A1.3** Sessão persiste após F5 (reload da página)
- [ ] **A1.4** Login com senha errada retorna 401 com mensagem clara
- [ ] **A1.5** Logout limpa sessão; acesso a rota protegida redireciona para login

### 4.2 Documentos + Classificação (8 checks)

- [ ] **A2.1** Upload de `c6bank_extratoconta_202501-smoke.csv` → status `classified` com tipo `extrato_conta_corrente` e banco `c6bank`
- [ ] **A2.2** Upload do mesmo arquivo novamente → bloqueado com mensagem de duplicata
- [ ] **A2.3** Upload de `c6bank_extratoconta_202501-smoke_dup.csv` (mesmo conteúdo, nome diferente) → `possible_duplicate_of_id` preenchido + `needs_review=true`
- [ ] **A2.4** Upload de `ambiguous_document-smoke.txt` → `needs_review=true`
- [ ] **A2.5** Upload de `nubank_faturacartao_202501-smoke.csv` → tipo `fatura_cartao`
- [ ] **A2.6** Upload de `nubank_extratoconta_202501-smoke.csv` → tipo `extrato_conta_corrente`
- [ ] **A2.7** Reclassificação manual de um documento funciona (muda tipo + banco)
- [ ] **A2.8** Exclusão de um documento (não essencial para pipeline) funciona

### 4.3 Pipeline Full (7 checks)

- [ ] **A3.1** Botão "Processar todos" dispara pipeline → status muda para `running`
- [ ] **A3.2** Progress bar de stages aparece no UI e avança
- [ ] **A3.3** Cada stage E0 → E5 aparece como completed no histórico
- [ ] **A3.4** E5 (análise financeira) completa sem erro
- [ ] **A3.5** Linha de `Report` é criada no DB pós-pipeline e o card aparece em `/reports` (renderer único React — stage E6 removido em ADR-129)
- [ ] **A3.6** Pipeline completa sem erros (status `completed`)
- [ ] **A3.7** Segundo run (incremental) processa apenas documentos novos

### 4.4 LLM Stages — Free Tier (3 checks)

- [ ] **A4.1** Sem `ANTHROPIC_API_KEY` configurada: E1.5, E2-llm, E6-parecer aparecem como `skipped_free_tier` no histórico
- [ ] **A4.2** Banner "Processamento LLM indisponível no plano atual" visível no relatório
- [ ] **A4.3** Pipeline ainda produz relatório útil com stages determinísticos

### 4.5 Relatório Nativo React (8 checks)

- [ ] **A5.1** Relatório abre em `/reports/[id]` sem erro
- [ ] **A5.2** Seção KPIs mostra patrimônio, score, fluxo de caixa
- [ ] **A5.3** Seção Fluxo de Caixa tem gráfico Chart.js renderizando
- [ ] **A5.4** Seção Investimentos lista os investimentos processados
- [ ] **A5.5** Valores monetários formatados em BRL (R$ 1.234,56)
- [ ] **A5.6** Botão "Exportar PDF" / "Download HTML" funciona
- [ ] **A5.7** Linhagem de dados (fontes dos artefatos) aparece com transparência F11
- [ ] **A5.8** Relatório em mobile (viewport <768px) sem overflow

### 4.6 Goals / Plano de Vida (5 checks)

- [ ] **A6.1** Dashboard de metas abre sem erro
- [ ] **A6.2** Criar nova meta (ex: Reserva de Emergência) funciona
- [ ] **A6.3** Meta IF projeta prazo e TRS corretamente com dados do pipeline
- [ ] **A6.4** `life_plan_goals.md` do fixture é reconhecido no workspace
- [ ] **A6.5** Editar/excluir meta funciona

### 4.7 — arquivado (gate A6b: cutover disco↔DB)

> Checks do gate A6b removidos — a coexistência disco↔DB não existe mais
> ([[ADR-212]]). Conteúdo preservado em
> [docs/archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md](../archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md).
> Número de seção mantido para não quebrar citações externas.

### 4.8 Edge Cases (5 checks)

- [ ] **A8.1** Workspace sem nenhum documento → pipeline completa com `skipped: true` em E2+
- [ ] **A8.2** Cancelar pipeline em andamento → status `cancelled`, próximo run aceito
- [ ] **A8.3** Upload de arquivo com extensão não suportada → mensagem de erro clara
- [ ] **A8.4** Upload acima do limite (50MB) → HTTP 413 com mensagem clara
- [ ] **A8.5** Multi-tab: dois browsers com diferentes usuários não interferem

### 4.9 Override v2 flag-ON (6 call-sites — A26.l4 · ADR-282)

> `override_natural_key_v2_enabled` é default **True** pós-flip (A26.l4). Estes checks
> exercitam os 6 consumidores do `OverrideMatchIndex` sob v2 e alimentam o gate da M2
> (A26.l5): `v1_fallback == 0` **com** `v2_match >= 1` por ≥1 sprint.

- [ ] **A9.1** Criar override de categoria numa transação → persiste com `natural_key_hash`
      preenchido (`create_override`, match v2 sem duplicar linha drifted)
- [ ] **A9.2** Deletar o override → some da transação após reprocesso (`delete_override` casa via v2)
- [ ] **A9.3** Preview de regra de categorização → transações-alvo corretas (`rule_preview_service`)
- [ ] **A9.4** Promover override em regra (learning loop) → regra aplica no reprocesso
      (`categorization_learning_loop` + `_apply_engine`)
- [ ] **A9.5** Reprocessar E4 → aparece `AuditAction.override_v2_dualread_snapshot` no
      `audit_log` com `v1_fallback_count=0` e `v2_match_count>=1`:
      `sqlite3 mathoms.db "SELECT details FROM audit_log WHERE action='override.v2_dualread_snapshot' ORDER BY created_at DESC LIMIT 1;"`
- [ ] **A9.6** Snapshot datado do gate (janela de observação ≥1 sprint): anotar
      `v1_fallback/v2_match/divergence` desta rodada na seção 5 — evidência do gate da l5

---

## 5. Registro de execuções e snapshots de gate

Toda rodada (completa ou parcial) registra uma linha. Snapshots de gate
(ex.: A9.6 — `v1_fallback/v2_match/divergence` do gate A26.l5) entram na
coluna de evidência. **Sem PII** — contagens e IDs de run apenas.

| Data | Escopo (seções) | Checks OK | Evidência / snapshot | Bugs (ID + severidade) | Decisão |
|------|-----------------|-----------|----------------------|------------------------|---------|
|      |                 |           |                      |                        |         |

> Formato original de decisão do gate A6c preservado no
> [archive](../archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md).

---

## 6. Troubleshooting

### Backend não sobe

```bash
# Ver logs
cat _smoke_pids/api.log | tail -50

# Verificar se porta 8000 está ocupada
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
make smoke-down && make smoke-up
```

### Celery worker não processa tasks

```bash
cat _smoke_pids/worker.log | tail -50

# Verificar Redis
docker compose -f docker-compose.smoke.yml ps
redis-cli ping
```

### Pipeline trava em stage X

```bash
# Ver log do worker em tempo real
make smoke-logs

# Forçar reset parcial do pipeline (a partir de reconcile_transactions).
# Pós-ADR-212 PR1b: scripts/e_reset.py deletado. Use service-layer
# `reset_workspace_from_stage` direto via console interno (ADR-116) ou
# Python shell para dry-run em smoke test.
source .venv/bin/activate
MATHOMS_DATABASE_URL=sqlite+aiosqlite:///./mathoms-smoke.db \
python -c "
import asyncio
from backend.app.core.database import AsyncSessionLocal
from backend.app.services.internal_ops import reset_workspace_from_stage

async def main():
    async with AsyncSessionLocal() as db:
        result = await reset_workspace_from_stage(
            db,
            workspace_id='<WORKSPACE_UUID>',
            from_stage='reconcile_transactions',
            actor='smoke-test',
            preview=True,
        )
        print(result)

asyncio.run(main())
"
```

### Banco corrompido / estado inconsistente

```bash
make smoke-reset   # Apaga tudo
make smoke-up && make smoke-seed   # Reinicia do zero
```

> Troubleshooting do gate A6b (`compare_disk_vs_db`) e o passo pós-aprovação
> A6c foram arquivados junto com a §4.7 — ver
> [archive](../archive/SMOKE_TEST_HUMAN_A6B_GATE-2026-07-03.md).
