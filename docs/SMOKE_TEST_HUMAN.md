# Smoke Test — Runbook Humano (A6b.5 · ADR-103)

> **Quem executa:** David Robert (owner do projeto)  
> **Objetivo:** Validar end-to-end o sistema antes da remoção do bridge (A6c).  
> **Bloqueante para:** A6c (deletar `MaterializationBridge` + `stage_runner_compat`).  
> **Resultado esperado:** Todos os checks passam → decisão explícita: "Aprovado para A6c" ou "Bloqueado — bug #X".

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

Marque cada item. Ao final registre a decisão na §5.

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
- [ ] **A3.3** Cada stage E0 → E4 aparece como completed no histórico
- [ ] **A3.4** E5 (análise financeira) completa sem erro
- [ ] **A3.5** E6 (relatório HTML) é gerado e aparece na lista de relatórios
- [ ] **A3.6** Pipeline completa sem erros (status `completed`)
- [ ] **A3.7** Segundo run (incremental) processa apenas documentos novos

### 4.4 LLM Stages — Free Tier (3 checks)

- [ ] **A4.1** Sem `ANTHROPIC_API_KEY` configurada: E1.5, E2-llm, E7-review aparecem como `skipped_free_tier` no histórico
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

### 4.7 Cutover DB — Opt-in por Workspace (5 checks — core A6b)

- [ ] **A7.1** `GET /health` retorna `artifact_store_mode: "disk"` por padrão
- [ ] **A7.2** Ativar `use_db_artifacts_override = TRUE` para o workspace smoke:
  ```bash
  sqlite3 mathoms-smoke.db "UPDATE workspaces SET use_db_artifacts_override=1 WHERE name='Smoke Premium';"
  ```
- [ ] **A7.3** Re-rodar pipeline → `GET /health` mostra `artifact_store_mode: "db"` para este workspace
- [ ] **A7.4** Tabela `pipeline_artifacts` no DB tem entradas para o run
- [ ] **A7.5** `python dev/compare_disk_vs_db.py <ws_id> --strict` retorna ≥99% paridade

### 4.8 Edge Cases (5 checks)

- [ ] **A8.1** Workspace sem nenhum documento → pipeline completa com `skipped: true` em E2+
- [ ] **A8.2** Cancelar pipeline em andamento → status `cancelled`, próximo run aceito
- [ ] **A8.3** Upload de arquivo com extensão não suportada → mensagem de erro clara
- [ ] **A8.4** Upload acima do limite (50MB) → HTTP 413 com mensagem clara
- [ ] **A8.5** Multi-tab: dois browsers com diferentes usuários não interferem

---

## 5. Decisão Final

**Data do teste:** _______________

**Executado por:** _______________

**Checks aprovados:** _____ / 46

**Bugs encontrados:**
| ID | Severidade | Descrição | Stack/evidência |
|----|-----------|-----------|-----------------|
|    |           |           |                 |

**Decisão:**

- [ ] ✅ **APROVADO para A6c** — todos os checks P0 passaram, bugs encontrados são P1/P2
- [ ] ❌ **BLOQUEADO** — bug(s) P0 impedem A6c: _______________

**Assinatura (David):** _______________

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

# Forçar reset parcial do pipeline (a partir de E3)
source .venv/bin/activate
MATHOMS_DATABASE_URL=sqlite+aiosqlite:///./mathoms-smoke.db \
MATHOMS_STORAGE_ROOT=_smoke_storage \
python scripts/e_reset.py --from E3 --dry-run
```

### Banco corrompido / estado inconsistente

```bash
make smoke-reset   # Apaga tudo
make smoke-up && make smoke-seed   # Reinicia do zero
```

### compare_disk_vs_db reporta divergência

Divergências **esperadas** (não são bugs):
- `_meta.confidence` / `_meta.notes` em artefatos E2-llm
- `created_at` / `updated_at` (timestamp de escrita diferente entre DB e disco)
- Ordem de listas JSON (transações, investimentos) — E3-E7 são order-insensitive

Divergências **que são bugs**:
- Key presente em disco mas ausente no DB (stage não escreveu via store)
- Conteúdo divergente em campos monetários ou de transações

---

## 7. Após aprovação — A6c

Quando o sinal humano for dado (checkbox §5 marcado ✅), executar:

```bash
# A6c — Remove bridge (somente após aprovação)
python dev/commit.py -m "refactor: remove MaterializationBridge + stage_runner_compat (A6c)"
```

Arquivos a deletar (A6c):
- `pipeline/stage_runner_compat.py`
- `pipeline/materialization_bridge.py`
- `main(root_dir)` legado dos 7 scripts determinísticos

Atualizar docs: ARCHITECTURE §17.3, CHANGELOG, CLAUDE.md.
