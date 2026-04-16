# Manual de Operação — Pipeline Financeiro
## Família Ferreira Campos
## Versão: 7.0 — abr/2026

---

## CHANGELOG v1.0 → ... → v6.1 → v7.0

### v6.1 → v7.0

| Mudança | Motivo |
|---|---|
| **Novo: Metas (Goals) via Web UI** | Meta de Independência Financeira configurável via wizard interativo em `/plano/meta-if/wizard` (4 passos). Valores derivados `compute_if_derived` (FV anuidade). Histórico versionado (append-only). ADR-073. |
| **Novo: Plano de Ação via Web UI** | `config/tarefas.md` migrado para entidade `Task` no DB (ADR-074). CRUD completo em `/plano-de-acao` com 3 views (prioridade/prazo/categoria). Dependências explícitas (`parent_task_id`). Transições validadas. Widget "Próximos 7 dias" no Dashboard. |
| **Novo: Sugestões do E5.N** | Pipeline E5.N agora persiste `tarefas_sugeridas` como `TaskSuggestion` no DB. Aprovação/rejeição 1-click em `/plano-de-acao/sugestoes`. Endpoint `POST /task-suggestions` para pipeline escrever via HTTP. |
| **Novo: Anexos em tarefas** | Upload de comprovantes (PDF, imagem) em `/plano-de-acao` drawer. Storage em `task_attachments/{task_id}/`. Endpoint de download com Content-Disposition. |
| **Novo: % executado para aportes** | Parser BRL no título da task (`R$ 20k`, `R$ 1.800`) + match de transações por keywords → barra de progresso mensal no drawer da task. |
| **Novo: Pipeline adapter (ADR-075/077)** | `pipeline_adapter.py` reconstrói `goals.json` e `tarefas.md` a partir do DB. Worker materializa os arquivos no `config_dir` do tenant ANTES de rodar stages → scripts E5/E6 não precisam mudar. |
| **Novo: Feature flags workspace-level** | `FeatureFlag` model com 4 flags (tasks_v2_enabled, task_attachments_enabled, report_tasks_snapshot_enabled, task_deadline_notifications_enabled). Endpoint GET/PUT. |
| **Novo: Worker beat diário** | `scan_all_deadlines` via Celery beat (86400s). Cria notificações para tasks overdue/urgentes/próximas. |
| **Novo: Snapshot imutável no relatório** | `Report.tasks_snapshot_json` copiado automaticamente no `_create_report_from_output`. Endpoint `GET /reports/{id}/tasks` com fallback live para relatórios pré-F8. |
| **Novo: Goal types expandidos** | `APORTE_MENSAL`, `DOLARIZACAO`, `ALOCACAO_ALVO`, `PLANNING_CONTEXT` — cobertura 100% do `goals.json`. Seeds completos para Ferreira Campos. |
| **Deprecação: `config/goals.json` e `config/tarefas.md`** | Marcados para remoção via `cutover_execute.py --apply` após validação de paridade. Backup automático em `_archive/pre-f8-cutover-YYYY-MM-DD/`. Fonte de verdade passa a ser o DB. |
| **Novo: Tenancy lint (CI)** | `scripts/lint/check_workspace_scoping.py` — AST-based, detecta queries sem `workspace_id`. Baseline com 6 violações legadas. Job `tenancy-lint` no CI. |

### v6.0 → v6.1

| Mudança | Motivo |
|---|---|
| **Fix: footer versão 3.1 → 6.1** | Header dizia v6.0 mas footer e Apêndices B/D ainda diziam v3.1. Unificado para v6.1. |
| **Fix: E5.N reclassificado como determinístico no corpo** | Changelog v6.0 promoveu E5.N para determinístico, mas 6+ referências no corpo ainda diziam "LLM" (STAGE E5.N, E-reset, E-reset-from, cascata, tarefas). Corrigidas para refletir `e5n_narrativas.py` como script determinístico. |
| **Fix: validações E6 unificadas para 19 (V1-V19)** | Referências conflitantes: 18, 19 e 20 checagens em diferentes seções. Código real implementa V1-V19. Removido V20 (não implementado em `validate_report()`). Todas as referências agora dizem 19. |
| **Fix: tabela cascata E-reset-from — linha E7 adicionada** | `--from E7` era documentado como valor válido mas não tinha linha na tabela de cascata. |
| **Fix: contagem E4 unified 6 → 7 arquivos** | Apêndice D e checklist não incluíam `fluxo_mensal_detalhado-4_unified.json`, documentado como output obrigatório desde v4.1. |
| **Fix: changelog duplicado `v5.0→v5.1`** | Duas seções com o mesmo heading e conteúdo diferente. Segunda renomeada para `v5.0.1→v5.1 (cont.)`. |
| **Fix: `e2_extract_faturas.py` removido do repositório** | Referências operacionais ainda diziam "deprecated mas funcional". Atualizado para "removido". Referências em changelog preservadas como histórico. |
| **Novo: seção 1.1.2 — Arquivos de config operacionais** | `pipeline.json`, `categorization.json`, `family_members.json`, `passwords.txt`, `milhas.md`, `tarefas.md`, `regras_composicao_patrimonial.md` e schema não estavam documentados nos pré-requisitos. |
| **Fix: casing `PJ_SOURCE_MAPPING` → `pj_source_mapping`** | Manual usava uppercase mas JSON real usa snake_case lowercase. 4 referências operacionais corrigidas. |
| **Fix: changelog reordenado cronologicamente** | Bloco v1.0→v4.1 estava fora de ordem (mistura de ascendente e descendente). Reordenado para mais recente primeiro, consistente com v4.2→v6.0. |
| **Fix: Apêndice D — `(E5)` → `(E6)`** | Output HTML é gerado por E6, não E5. |
| **Fix: formato `[DATE]` documentado na STAGE E6** | Formato `YYYYMMDD` estava apenas no changelog v3.0→v3.1, não na seção operacional do E6. |
| **Fix: referências "E4 JSON" → "E5 analysis JSON"** | 2 referências operacionais usavam "E4" para o artefato `analise_financeira-5_analysis.json` (que é E5). |
| **Fix: E-full-reset intro inclui E7** | Objetivo dizia "até E6" mas pipeline vai até E6-final (após E7-review + E7-apply). |
| **Fix: numeração duplicada seção 5.2** | Dois itens numerados "4." — segundo corrigido para "5.". |
| **Fix: tabelas de parsers "v5.5" → referência genérica** | Versão fixa nos headings substituída por "Parsers de extratos/faturas disponíveis". |
| **Glossário expandido** | 7 termos adicionados: Wall, Tombstone, Parse quality, Cascata, E-full-reset, State file, Determinístico. |

### v5.9 → v6.0

| Mudança | Motivo |
|---|---|
| **Novo: E-full-reset modo `--interactive`** | Pipeline completo agora pode ser orquestrado automaticamente via `--interactive` + `--continue`. O script para em 3 "walls" (etapas LLM: E1+E1.5, E2-llm, E7-review) e retoma com `--continue`. Entre walls, todas as etapas determinísticas rodam automaticamente. |
| **Promoção: E1.5c, E5.N, E7-crossval para determinísticos** | Análise revelou que `e15_consolidate.py`, `e5n_narrativas.py` e `e7_review.py` (sem --apply) são 100% determinísticos (zero chamadas LLM). Removidos de `LLM_STAGES`, adicionados a `DETERMINISTIC_SCRIPTS`. Reduz de 6 para 4 etapas LLM. |
| **Novo: E7 dividido em E7-crossval + E7-review + E7-apply** | E7 era monolítico. Agora: E7-crossval (det.) faz cross-validation, E7-review (LLM) preenche template, E7-apply (det.) aplica refinamentos. Permite automação parcial. |
| **Novo: state file `_scratch/.e_reset_state.json`** | Rastreia progresso do pipeline interativo entre invocações. Inclui etapas concluídas, próxima etapa, e instruções para o agente. Limpo automaticamente ao completar. |
| **Novo: exit code 10** | Pipeline pausado em wall LLM (não é erro). Distingue de exit 0 (sucesso) e exit 1 (falha). |
| **Atualização: EXECUTION_ORDER_FULL** | Nova ordem: E1 → E1.5 → E1.5c → E2-llm → E2-fat → E2-ext → E3 → E4 → E5 → E5.N → E6 → E7-crossval → E7-review → E7-apply → E6-final. |

### v5.8 → v5.9

| Mudança | Motivo |
|---|---|
| **Regra: E-save EXCLUSIVAMENTE manual** | Commits e pushes eram instruídos inline em E-reset, E-reset-from, E-full-reset e Seção 5.1. O operador (LLM) podia interpretar como obrigatório e fazer commits automáticos sem solicitação do usuário. Agora: `e_save.py` é a ÚNICA forma de commit/push, e só é executado quando o operador invoca explicitamente. |
| **Remoção: passos `git add/commit` das etapas** | Passos "Comitar estado atual via Git" e "Comitar resultado" removidos de E-reset (Passos 1 e 5), E-reset-from (Passos 1 e 5), E-full-reset (Passos 1 e 10). Substituídos por nota informando que E-save é manual. |
| **Remoção: `git add/commit` inline da Seção 5.1** | Seção "Versionamento de arquivo" não instrui mais `git add` + `git commit` diretamente. Referencia `e_save.py` como opcional antes da sobrescrita. |
| **Atualização: Seção 4.5.2** | "Fluxo padrão: comitar antes de alterar" reescrita para "Fluxo padrão: salvar estado via E-save", com regra explícita de que nenhuma etapa faz commit automaticamente. |
| **Renumeração de passos** | E-reset: 5→3 passos. E-reset-from: 5→3 passos. E-full-reset: 11→9 passos. Referências internas atualizadas. |

### v5.7.1 → v5.8

| Mudança | Motivo |
|---|---|
| **Fix: e0_route.py — preservar nomes de arquivo** | Rico não era reconhecido como banco (regex `rico(?!_)` bloqueava `rico_*`). Wise perdia sufixo de moeda (BRL/USD). Santander CDB perdia subtipo (di1/di2/prog). QuintoAndar informe perdia sufixo `aluguel`. IRPF com `[mariana]` perdia identificação do membro. Adicionados 12+ patterns específicos ANTES dos genéricos. |
| **Fix: e0_route.py — c6bank carteirarendafixa** | `c6bank_carteirarendafixa` era incorretamente classificado como `cdbdetalhes` pelo regex genérico. Novo pattern específico `carteira.*renda.?fixa` adicionado. |
| **Novo: mapeamento banco→membro (family_members.json)** | Investimentos sem campo `membro` (extratos de posição bancários) ficavam com patrimônio atribuído a `""`. Novo campo `banco_membro` em `family_members.json` mapeia cada instituição ao membro titular. E4 usa como fallback. |
| **Fix: e4_categorize.py — fallback banco→membro** | `build_investimentos_unified()` agora consulta `BANCO_MEMBRO` quando `data.membro` é vazio. Resolve patrimônio zerado no E5 para investimentos pessoais. |
| **Docs: schema baseline_patrimonial no manual** | Exemplo JSON completo do formato esperado por E5 adicionado à seção E1.5. Previne LLM gerar schemas incompatíveis. |

### v5.7 → v5.7.1

| Mudança | Motivo |
|---|---|
| **Fix: E3 dedup generalizada para sufixos após "—"** | C6 Bank PJ: CSV adiciona sufixos descritivos após "—" (ex: "— 13 Salário", "— Salários PJ", "— NF 26") que não existem no PDF. Antes, `_normalize_description_for_dedup()` só removia "— TRANSF ENVIADA/RECEBIDA PIX". Agora remove qualquer sufixo após "—", permitindo dedup correta entre CSV e PDF sobrepostos. Corrige inflação de receita PJ (~100% duplicada). |
| **Fix: e4_categorize.py lê chaves E2 schema** | `build_investimentos_unified()` agora aceita tanto `composicao`/`saldo_atual` (schema E2) quanto `posicoes`/`total` (formato legado). Aceita também `valor_atual` (CDB resumo) além de `valor_total`. |
| **Fix: e5_analyze.py lê declarante.nome** | `_build_members_from_declarations()` agora lê `declarante.nome` quando `membro` está vazio (formato IRPF extract). Também infere `ano_base` do nome do source_file quando ausente, garantindo que a declaração mais recente é usada por membro. |

### v5.6 → v5.7

| Mudança | Motivo |
|---|---|
| **Fix: e5_analyze.py suporta formato E1.5 declarations** | Baseline com `membros` como lista de strings + `declarations[]` agora é corretamente parseado via classificação por grupo IRPF (G01=imóveis, G02=veículos, G03/04/07=investimentos, G06=contas). Fallback defensivo com warning. |
| **Fix: e0_audit.py robusto a JSONs não-dict e 0-byte** | Guard clause em `check_filename_vs_content()` e `check_saldo_gaps()` — skip quando E2/E3 JSON é lista, 0 bytes ou tombstone. Elimina crash `AttributeError: 'list' object has no attribute 'get'`. |
| **Novo: E4 popula investimentos-4_unified.json** | `e4_categorize.py` agora consolida extratos de posição de investimentos do E2 (BTG, Rico, Itaú, C6, Santander). Antes era sempre placeholder vazio `{"dados": []}`. |
| **Novo: E5 patrimônio com fontes mistas** | `analyze_patrimonio()` aceita `investimentos_atuais` (posições de mar/2026). Se disponível: patrimônio = imóveis/veículos IRPF + investimentos atuais. Campo `fonte_investimentos` no JSON indica a fonte usada. |
| **Novo: JSON Schema para baseline E1.5** | `config/schemas/baseline_patrimonial.schema.json` valida o baseline na carga do E4 (best-effort, não bloqueia se jsonschema não instalado). |
| **Novo: tests/test_e5_patrimonio_formats.py** | 6 testes para 4 formatos suportados por `_resolve_members()` + test de posições atuais + edge case baseline vazio. |

### v5.5 → v5.6

| Mudança | Motivo |
|---|---|
| **E0-unlock: suporte a ZIP com senha** | C6 Bank entrega extratos CSV em ZIPs protegidos por senha. Antes, a descompactação era manual. Agora `e0_unlock.py` detecta e descompacta ZIPs (com ou sem senha) automaticamente no inbox, usando as mesmas senhas de `config/passwords.txt`. Após extração, o `.zip` é movido para `inbox_processed/`. |
| **E0-unlock: `--file X.zip` suportado** | Flag `--file` agora aceita arquivos `.zip` além de `.pdf`. |
| **E0-unlock: resumo unificado PDF+ZIP** | Saída do script agora mostra contagem separada de ZIPs e PDFs processados, com resumo de falhas unificado. |

### v5.4 → v5.5

| Mudança | Motivo |
|---|---|
| **Fix: deduplicação cross-tipo Itaú (E3)** | `extratocontapersonnalite` e `extratoconta` do Itaú são a mesma conta bancária exportada por portais diferentes. E3 tratava como contas distintas, causando duplicação de transações (ex: FINANC IMOBILIARIO duplicado jul/25–dez/25, ~R$ 4.300/mês cada). Novo config `account_type_equivalences` em `family_members.json` normaliza tipos equivalentes para agrupamento e deduplicação. |
| **Novo config: `account_type_equivalences`** | Seção em `family_members.json` que mapeia tipos de conta que são aliases da mesma conta bancária. Atual: `extratocontapersonnalite` → `extratoconta`. E3 usa esse mapeamento em `get_account_key()` para agrupar e deduplicar corretamente. |
| **Novo keyword: LUMMA ROBERTA (saude)** | Personal trainer do David. Adicionado em `categorization.json` → `expense_keywords.saude`. |
| **Novo keyword: BELT ACADEMY (educacao)** | Aula de inglês do David. Adicionado em `categorization.json` → `expense_keywords.educacao`. |
| **Novo keyword: HELEN SASAKE TAKAGI (saude)** | Pediatra do Theo. Adicionado em `categorization.json` → `expense_keywords.saude`. |
| **Novo keyword: NEUSA CIMAR TEIXEIRA (suporte_familiar)** | TED mensal de R$ 1.500 para Neusa (sogra). Adicionado em `categorization.json` → `expense_keywords.suporte_familiar` com variantes `NEUSA CIMAR TEIXEIRA` e `NEUSA CIMAR`. |
| **Nota: TV Samsung dez/25 (R$ 18.788)** | Compra de TV nova classificada como `reserva_desejos` (Amazon). Classificação correta — sem alteração necessária. |

### v5.3.1 → v5.4

| Mudança | Motivo |
|---|---|
| **Novo STAGE: `E-full-reset`** | Reprocessamento completo desde E0-unlock/E0-audit até E6. Antes, o operador precisava lembrar a sequência manual de E0-unlock → E0-audit → E0 → E-reset → etapas LLM. Agora há um procedimento documentado passo a passo com ordem das etapas LLM, pontos de re-cascata, e validação final. |
| **E-full-reset: tabela de ordem das etapas LLM** | Documenta a sequência correta: E1 → E1.5 → E2-extratos → re-cascata E3→E6 → E5.N → E6 render. Inclui artefatos gerados por cada etapa. |
| **E-full-reset: re-cascata após E2-extratos** | Explicita que após E2-extratos é necessário `e_reset.py --from E3` antes de E5.N, para que novos extratos sejam reconciliados/categorizados/analisados. |
| **E-full-reset: validação final inclui e0_audit.py** | Passo 8 roda `e0_audit.py` novamente ao final para confirmar que o pipeline não introduziu inconsistências. |

### v5.3 → v5.3.1

| Mudança | Motivo |
|---|---|
| **Fix: tabela V1-V19 inserida no E6.6** | Placeholder `[Keep the existing V1-V18 validation table]` ficou no manual sem conteúdo. Tabela agora completa com 19 checagens (conforme `e6_render.py`). Contagem corrigida: 18→19. |
| **Fix: "E4 JSON" → "E5 analysis JSON" na STAGE E5** | 12+ referências dentro da STAGE E5 diziam "Salvar no E4 JSON" mas o destino real é `analise_financeira-5_analysis.json`. Ambiguidade podia causar roteamento errado. |
| **Fix: changelog v5.1→v5.2 duplicado unificado** | Duas seções `### v5.1 → v5.2` com conteúdos diferentes foram unificadas em uma única. |
| **Fix: referência E5.4/E5.5 → E6.4/E6.5** | Seção 1.1.1 ainda referenciava numeração pré-v4.5. Atualizada para E6.4/E6.5. |
| **Fix: valores hardcoded removidos de exemplos de schema** | ~20 valores monetários reais (Arvo 47.550, patrimônio 2.360.000, etc.) nos exemplos de JSON substituídos por placeholders genéricos com nota indicando que são calculados dinamicamente. |
| **Fix: Selic 14,25% e faixas inconsistentes** | Exemplo de contrafluxo tinha Selic fixa em 14,25% e faixas (13-15%, 10-12%, 6-8%) inconsistentes com critérios (≥12%, 8-12%, <8%). Corrigidos ambos. |
| **Fix: "37 faturas ~8s" → linguagem genérica** | Seção operacional de E2-faturas agora diz "proporcional ao número de faturas (~0,2s por fatura)" em vez de contagem fixa de um ciclo. |
| **Fix: origens PJ/CLT referenciam categorization.json** | Nomes de empresas PJ/CLT nos exemplos agora referenciam `PJ_SOURCE_MAPPING` e `CLT_SOURCE_MAPPING` do `categorization.json` em vez de listar nomes fixos. |
| **Fix: "14 categorias" → "todas as categorias do definitions.md"** | Contagem fixa de categorias de despesa substituída por referência dinâmica ao config. |
| **Fix: e5_analyze.py período fallback dinâmico** | Fallback "2025-01 a 2026-03" substituído por derivação dinâmica a partir de `meses_ordenados` do fluxo mensal. |
| **Fix: e5_analyze.py ONE_TIME_INCOME carregado de config** | Keywords one-time agora carregadas de `categorization.json` (chaves `one_time_income_keywords` e `one_time_income_categories`), com fallback para valores internos. |
| **Fix: e4_categorize.py fallback CLT dinâmico** | Fallback "Einstein (Mariana - CLT)" substituído por primeiro valor do `CLT_SOURCE_MAPPING`, sem string hardcoded. |
| **Fix: report_spec.md período dinâmico** | "Mai/25–Mar/26" substituído por "período dinâmico do fluxo_mensal_detalhado". |

### v5.2 → v5.3

| Mudança | Motivo |
|---|---|
| **Fix: Passo 8 expandido com check de encriptação (8b)** | C6 Global EUR/USD foram roteados encriptados porque Passo 8 só verificava tamanho > 0. PDFs com senha passavam direto. Agora Passo 8 tem sub-etapa 8b que exige `e0_unlock.py` antes do roteamento. |
| **Novo: `e0_unlock.py --check-destinations`** | Varredura pós-roteamento: varre `data/` e `members/` por PDFs encriptados que escaparam e desbloqueia in-place. Recomendado rodar após cada E0.A como safety net. |
| **Regra: NUNCA rotear PDF encriptado** | Formalizada no Passo 8b. PDFs encriptados devem ser desbloqueados no inbox ou enviados para `nao_identificados/`. |

### v5.1 → v5.2

| Mudança | Motivo |
|---|---|
| **Novo script: `scripts/e0_audit.py`** | Auditoria de integridade entre `data/`, `E2_extracts/` e `E3_reconciled/`. 5 checagens: (1) filename vs JSON content mismatch, (2) arquivos órfãos, (3) possíveis duplicatas, (4) cross-reference inbox_log.md, (5) gaps de saldo no E3. Não altera nenhum arquivo — apenas imprime relatório. |
| **Flags:** | `--check 1,3` (checagens específicas), `--json` (saída JSON para scripts). |
| **Uso recomendado** | Rodar `python scripts/e0_audit.py` antes de E-reset para detectar problemas de roteamento que se propagariam pelo pipeline. |
| **Checagem 7: colisão de nomes** | Detecta arquivos no inbox/ que gerariam o mesmo nome destino mas têm conteúdo diferente (hash). Severity ERROR — bloqueia E-reset via e0_audit integrado. |
| **Convenção de sufixo de letra** | Formalizada: quando há colisão de nome, adicionar letra (`a`, `b`, `c`) ao período. Já existia informalmente (Binance, Itaú Personnalité). Agora documentada no E0 Passo 7 e seção de nomenclatura. |
| **E0 Passo 7 expandido** | Agora compara hash antes de decidir: duplicata (ignorar) vs colisão (sufixo de letra). Inclui procedimento de rename do arquivo existente quando necessário. |
| **E-reset: scripts E3/E4/E5 agora retornam exit code 1 em caso de erro** | Antes, erros eram engolidos e o pipeline continuava sobre dados vazios. Agora `e_reset.py` aborta a cascata corretamente. |
| **E5: `TODAY = date.today()` em vez de data hardcodada** | Idades, projeções IF e `ano_if` estavam congelados em 2026-04-05. |
| **E-reset: pre-check de dependências Python** | Verifica `pdfplumber` e `pytz` antes de apagar qualquer artefato. Antes, import faltante causava abort após deleção. |
| **E-reset: limpeza de narrativas no `--from E5.N`** | Nova fase 1.5 remove chave `narrativas` dos JSONs E5, garantindo que E6 não renderize narrativas obsoletas. |
| **E-reset: identificação de faturas por tipo JSON** | Glob de faturas agora inspeciona campo `tipo` no JSON ao invés de padrão no filename. Future-proof para novos bancos. |
| **E-reset: artefatos E1 preservados no full reset** | `members/*-1a_extract.json`, `members-1b_unified.json`, `members-1c_enriched.md` não são mais deletados — E1 é LLM e não pode ser regenerado automaticamente. |
| **E-reset: validação de conteúdo pós-execução** | `validate()` agora verifica JSON parseável e campos obrigatórios não-vazios (`transacoes` em E3, `score`/`patrimonio` em E5), além de existência. |
| **E-reset: mensagem pós-pipeline sugere `e6_render.py` diretamente** | Antes sugeria `e_reset.py --from E6` (indireção desnecessária). |
| **E3: qa_log.md sem acumulação de seções E3** | Seções `## E3 Temporal Gaps` anteriores são removidas antes de escrever nova, evitando crescimento indefinido. |
| **E-reset: aviso para `--clean-only --from E5.N`** | Informa que narrativas são internas ao JSON e que apenas HTML será removido. |

### v5.0.1 → v5.1

| Mudança | Motivo |
|---|---|
| **Fix: E0.A instrução `cp` → `mv`** | Inbox permanecia com 169 arquivos após E0 (80 stubs 0-bytes + 89 renomeados). Manual dizia "copiar" mas o correto é "mover". Inbox deve ficar vazio após E0.A. |
| **Novo: validação de integridade (Passo 8)** | Arquivos de 0 bytes eram roteados sem verificação. Novo passo rejeita arquivos vazios/corrompidos com warning no qa_log. |
| **Novo: tipo `extratocontapersonnalite`** | Tipo não existia na tabela de detecção. Scripts E3 já tratavam, mas LLM podia renomear como `extratoconta` genérico, perdendo a distinção de conta. |
| **Novo: `faturaaluguel[propriedade]` documentado** | Convenção de propriedade colada ao tipo (ex: `faturaaluguelcalixto`) existia nos scripts e arquivos reais mas não no manual. LLM podia inserir underscore separador, quebrando regex do E2. |
| **Novo: regra multi-membro Grupo B** | IRPF/informes de múltiplos membros não tinham convenção documentada. Agora: `[tipo][membro]` colado, titular pode omitir sufixo. |
| **Novo: formato `YYYY` para documentos anuais** | Passo 4 só mencionava `YYYYMM`. Documentos anuais (IRPF, informes) usam `YYYY` na prática. |
| **Novo: nota sobre detecção de JPG** | 5 JPGs no pipeline (Binance, Itaú) não tinham instrução de detecção. Tipo é inferido exclusivamente pelo nome; OCR fica para E2. |
| **Novo: validações V5-V7 no setup** | V5 (inbox vazio), V6 (contagem inbox_processed == inbox_log), V7 (nenhum arquivo 0 bytes nos destinos). Antes: só V1-V4. |
| **Novo: ciclo para faturas de aluguel isoladas** | Tabela 3.2 não cobria cenário de apenas faturas QuintoAndar. Adicionada linha: E2-faturas + E3→E6. |
| **Fix: regra de auditoria inbox_processed** | Esclarecido que apenas arquivo com nome original vai para inbox_processed. Antes: renomeados eram duplicados lá. |
| **Fix E4: origin mapping receita_investimento/receita_resgate** | Ambas caíam no `else` branch e viravam "Outras Receitas" no fluxo. "Rendimentos Financeiros" desaparecia do fluxo mensal. |
| **Fix E4: case-sensitivity C6 Bank "Pagamento"** | `"c6" in norm_banco` falhava após normalize_text() (retorna uppercase). R$16k classificados erroneamente como nao_identificado. |
| **Fix E4: POMPEIA MOTOS reclassificada** | Era `receita_pj` mas é venda da Yamaha MT09 → `receita_venda_ativo`. |
| **Fix E4: BRANDLOVRS no PJ_SOURCE_MAPPING** | Variante de typo no C6 Bank não tinha mapeamento → caía em "Outras Receitas PJ". |
| **Fix E4: RECEB PAGFOR e CAIXA ECONOMICA restringidos** | `RECEB PAGFOR` genérico podia capturar qualquer pagfor como aluguel. `CAIXA ECONOMICA` podia capturar qualquer TED da Caixa como FGTS. |
| **Novo E4: qa_log.md gerado pelo script** | Manual exigia mas script não gerava. Agora `generate_qa_log()` escreve `logs/qa_log.md` com taxa e notas para investigação. |
| **Novo E4: período dinâmico** | Período era hardcoded "2025-01 a 2026-03". Agora calculado a partir das datas reais. |
| **Novo E4: reprocessamento limpo** | Removida lógica `preserve_existing_file` que impedia regeneração de patrimônio/investimentos/seguros em re-runs. |
| **Novo E4: keywords expandidas** | `TED D HBANK` (transferência interna), `AMAZON MKTPL`, `SAMUELABNERSANTOSMARC` (serviços domésticos). |
| **Fix: definitions.md sincronizado com e4_categorize.py** | Keywords `financeiro` divergiam. Referências "E3" corrigidas para "E4". Regras especiais atualizadas. |

### v5.0 → v5.0.1

| Mudança | Motivo |
|---|---|
| **Fix: Santander fallback vencimento validado contra ref_year** | Fatura 202503 gerava `data_vencimento: 2026-03-15` (ano errado). Fallback agora busca data coerente com YYYYMM do filename; se não achar, estima com dia 15 + warning. |
| **Fix: Itaú seção "Lançamentos internacionais" reconhecida** | Transações internacionais (SQSP, etc.) eram perdidas porque "Limites de crédito" na right-column desligava `in_lancamentos` antes de capturá-las. +11 transações recuperadas. |
| **Fix: Itaú `tx_simple` aceita valores negativos** | Estornos/créditos (`valor < 0`) eram descartados pelo filtro `valor > 0`. Agora aceita `valor != 0`. |
| **Fix: output filename robusto** | Regex de renomeação falhava com variantes, gerando duplicatas `*-0_original-2_extract.json`. Agora usa regex único com `-0_original` opcional. |
| **Novo: `validate_parse_result()`** | Pós-parse emite warning e marca `parse_quality` quando resultado é vazio (`empty_result`) ou saldo > 0 sem transações (`missing_transactions`). |
| **Novo: `safe_date()` valida datas** | Impede datas impossíveis como `2026-02-31`. Ajusta dia para último dia do mês com warning. |
| **Novo: guard `ref_month=None`** | `resolve_date` e `resolve_date_ddmm` não crasham mais quando filename não contém YYYYMM. |
| **Novo: `parse_brl` formato contábil** | Suporta `(1.234,56)` como negativo (formato contábil comum em PDFs financeiros). |
| **Convenção: `pagamentos` sempre negativo** | Santander e Itaú agora aplicam `-abs(val)` em pagamentos, alinhando com C6 Carbon. |
| **Warning: arquivos não-renomeados** | Inbox com faturas sem sufixo `-0_original` agora emite `WARN` listando nomes (antes: ignorados silenciosamente). |
| **Fix: QuintoAndar skip-list invertida** | Skip-list ampla descartava itens legítimos contendo nomes de meses. Agora: match do item primeiro, rejeição apenas por descrição exata de header. +1 item recuperado. |
| **Seção 7.1: schema fatura atualizado** | Schema antigo (com `instituicao`, `resumo{}`, `periodo{}`) divergia do output real. Atualizado para schema flat real + novo schema QuintoAndar. LLM fallback agora gera formato compatível com E3. |

### v5.0.1 → v5.1 (cont. — mudanças E3)

| Mudança | Motivo |
|---|---|
| **E3: cleanup de E3_reconciled/ no início** | Script agora remove/tombstona todos os `.json` existentes antes de escrever. Elimina arquivos fantasma `{}` de execuções LLM anteriores que poluíam E4. |
| **E3: arquivos `-0_original` ignorados** | Backups de extratos pré-correção (e.g. `itau_extratoconta_202507-0_original-2_extract.json`) são agora filtrados. Eliminava warnings falsos de saldo e duplicatas espúrias. |
| **E3: deduplicação apenas entre arquivos** | Transações idênticas `(data, valor, descrição)` dentro do MESMO arquivo são preservadas — representam compras legítimas distintas. Dedup opera apenas cross-file. Recuperou ~10 transações perdidas (Amazon, iFood, Dr. Barakat). |
| **E3: periodo de fatura ajustado por datas reais** | Periodo sintetizado a partir de `data_vencimento` é ajustado se transações reais começam antes. Ex: venc=05/05 → synth_inicio=01/04, mas txns começam 28/03 → inicio=28/03. |
| **E3: filenames YYYYMM para todos os tipos** | Contas correntes usavam MMDD (perdia informação de ano). Agora todas usam YYYYMM, consistente com faturas. Ex: `bradesco_extratoconta_BRL_202501_202603-3_reconciled.json`. |
| **E3: `extratocontapersonnalite` reconhecido** | Tipo adicionado ao `TIPO_CANONICAL`. Itaú Personnalité agora é processado corretamente. |
| **E3: saldo None tratado explicitamente** | Arquivos com `saldo_inicial/final=None` (ex: Bradesco poupança) agora usam 0 com warning no log, evitando TypeError downstream. |
| **E3: log explícito para faturas sem `data_vencimento`** | Faturas com vencimento vazio são logadas claramente antes do skip (antes era silencioso). |
| **E3: validação contra baseline patrimonial** | Novo step compara saldos em 31/12 com valores declarados no IRPF. Discrepâncias registradas em `reconciliation.md`. |
| **E3: detecção de gaps temporais** | Gaps > 2 dias entre extratos consecutivos da mesma conta são detectados e registrados em `logs/qa_log.md`. |

### v4.9 → v5.0

| Mudança | Motivo |
|---|---|
| **E1: `config/definitions.md` como input obrigatório** | E1 não consultava dados cadastrais (CPF, nascimento, nomes solteiro/casado, papel). Idades eram estimadas a partir de formatura. Membros sem documentos (Theo) não apareciam no output. |
| **E1: novo passo 0 — carregar dados cadastrais** | LLM agora inicia lendo `definitions.md` para usar como base de verdade para nomes, idades e lista de membros. |
| **E1: schemas 1a formalizados em português** | JSONs reais estavam em inglês e divergiam entre si e do schema. Padronizado: `tipo`, `membro`, `nome_completo`, `nome_atual`, etc. Chaves obrigatórias listadas explicitamente. |
| **E1: schema holerite expandido** | Faltavam campos extraíveis: FGTS, base INSS, grade, matrícula, proventos adicionais, dependentes IR. `nome_no_documento` preserva nome fiscal (pode ser solteira). |
| **E1: novo schema `members-1b_unified.json`** | Antes não havia schema — estrutura era ad-hoc a cada execução. Agora formalizado com `nomes_alternativos[]`, `salario{}` com fonte e nota, e inclusão obrigatória de todos os membros do definitions. |
| **E1: spec formal para `members-1c_enriched.md`** | Template obrigatório com ordem (Titular→Cônjuge→Filhos), idade calculada (não estimada), bloco mínimo para membros sem documentos. |
| **E1: holerites com período no nome do arquivo** | Antes: `[membro]_holerite-1a_extract.json` (único). Agora: `[membro]_holerite_[período]-1a_extract.json` (um por holerite). |
| **E1: tabela de campos por tipo de documento pessoal** | Passo 3 dizia "dados demográficos relevantes" sem especificar. Agora: tabela com campos exatos para RG, CPF, passaporte, visto, certidões, SSN, driver's license, green card. |
| **E1: regras de resolução de conflito expandidas** | Passo 4 tinha 1 exemplo (salário). Agora: tabela com 10 cenários (nome, cargo, empresa, datas, idiomas, múltiplos holerites, membro sem docs, etc.). |
| **E1: validação V1-V5** | Antes: genérica ("chaves obrigatórias vide schema"). Agora: 5 níveis — schema compliance, valores numéricos, consistência 1a→1b, consistência 1b→1c, documentos corrompidos. |
| **E1: regra de idiomas inferidos** | Se currículo não listar idiomas, inferir nativo do idioma do documento. Elimina arrays vazios. |
| **E1: overlaps temporais são válidos** | Instrução explícita para não "corrigir" datas sobrepostas entre experiências. |
| **`definitions.md`: nova seção NOMES (solteiro/casado)** | Tabela com nomes de solteiro e casado de David, Mariana e Theo. Instrução para mapear variantes sem tratar como divergência. |

### v4.8 → v4.9

| Mudança | Motivo |
|---|---|
| **Novo script: `scripts/e_reset.py`** | E-reset e E-reset-from agora são determinísticos. Script unificado para limpeza de artefatos e re-execução automática das etapas determinísticas (E2-faturas, E3, E4, E5, E6). Etapas LLM (E1, E1.5, E2-extratos, E5.N) são puladas com lembrete no console. |
| **Flags disponíveis** | `--from E[N]` (reset parcial), `--dry-run` (preview sem mudanças), `--clean-only` (só apagar artefatos), `--no-validate` (pular validação). |
| **Safety: proteção de arquivos preservados** | Script nunca apaga `inbox_log.md`, `qa_log.md`, `data/`, `members/*-0_original.*`, `config/`, `life_plan/`, `scripts/`. Validação pós-execução verifica presença dos artefatos esperados. |
| **Procedimento E-reset/E-reset-from simplificado** | Passos manuais de `rm -f` substituídos por invocação do script. Git commit antes/depois continua sendo responsabilidade do operador (LLM ou humano). |

### v4.7 → v4.8

| Mudança | Motivo |
|---|---|
| **Novo script: `scripts/e_save.py`** | Commit + push 100% determinístico via Python. Safety check automático (bloqueia `data/`, `inbox/`, `inbox_processed/`), validação de prefixo na mensagem de commit, staging, commit e push em um único comando. Flags: `--dry-run` (preview), `--no-push` (commit local), `--force-add` (ignorar safety). Execução: `python scripts/e_save.py -m "mensagem"`. |
| **Convenção de mensagem validada pelo script** | Mensagens devem usar prefixos padronizados (`pipeline:`, `config:`, `docs:`, `fix:`, `update:`, etc.). Script rejeita mensagens fora da convenção. |
| **Safety check redundante ao `.gitignore`** | Além do `.gitignore`, o script verifica programaticamente que nenhum arquivo de diretórios proibidos está sendo staged. Duas camadas de proteção contra commit acidental de dados sensíveis. |

### v4.6 → v4.7

| Mudança | Motivo |
|---|---|
| **Novo script: `scripts/e2_extract_faturas.py`** | Extração determinística de faturas de cartão de crédito via Python + pdfplumber. Parsers para C6 Carbon, Santander Unique, Itaú Pão de Açúcar e QuintoAndar Aluguel. Faturas desconhecidas geram JSON com `requires_llm_fallback: true` para processamento manual/LLM. |
| **Resolução do problema `transacoes: []` em faturas** | Antes, E2 (LLM) não extraía transações de faturas — 100% dos JSONs de fatura tinham arrays vazios. Agora: 37 faturas → 1.295 transações extraídas deterministicamente. |
| **Impacto esperado em `nao_identificado`** | ~53% de despesas era `nao_identificado` porque extratos bancários só têm "Pagamento de fatura". Com merchant names das faturas (AMAZON BR, PADARIA DANIELA, HOTEL BOOKING.COM, etc.), E4 deve categorizar muito mais. |
| **Arquitetura hybrid: determinístico + fallback LLM** | Router identifica tipo de fatura pelo filename. Se banco/formato é conhecido, usa parser determinístico. Senão, extrai texto bruto com pdfplumber e gera stub para LLM. |
| **Execução:** `python scripts/e2_extract_faturas.py` | Flags: `--dry-run` (preview), `--file ARQUIVO.pdf` (um arquivo). ~8s para 37 faturas. |

### v4.5 → v4.6

| Mudança | Motivo |
|---|---|
| **Novo script: `scripts/e3_reconcile.py`** | E3 reconciliação 100% determinística via Python. Substitui execução LLM para deduplicação, agrupamento por conta e validação de saldos. Suporta faturas (sintetiza `periodo` a partir de `data_vencimento`). Execução: `python scripts/e3_reconcile.py`. |
| **Novo script: `scripts/e4_categorize.py`** | E4 categorização 100% determinística via Python. Keywords hardcoded do `definitions.md` (~14 categorias despesa, 7 receita). Detecção conservadora de transferências internas. Normalização com remoção de acentos. Execução: `python scripts/e4_categorize.py`. |
| **Novo script: `scripts/e5_analyze.py`** | E5 cálculos numéricos 100% determinísticos via Python. Computa patrimônio (bruto/investível/líquido), score (5 componentes, 0-10), rácios, fluxo de caixa, orçamento prospectivo, reserva emergência, endividamento. Preserva chave `narrativas` existente. Execução: `python scripts/e5_analyze.py`. |
| **E-reset-from agora usa scripts** | `E-reset-from E3` executa `e3_reconcile.py → e4_categorize.py → e5_analyze.py → E5.N (LLM) → e6_render.py`. Etapas determinísticas ~5s total (vs. minutos com LLM). |
| **E5.N continua LLM-driven** | Apenas narrativas textuais usam LLM. Todos os cálculos numéricos são determinísticos via `e5_analyze.py`. |

### v4.4 → v4.5

| Mudança | Motivo |
|---|---|
| **Renumeração de etapas: E2.5→E3, E3→E4, E4→E5, E4.N→E5.N, E5→E6** | Numeração sequencial limpa (E1→E1.5→E2→E3→E4→E5→E5.N→E6). Elimina sub-etapa "E2.5" e alinha sufixos de arquivo com número da etapa. |
| **Diretórios renomeados** | `E2_reconciled/`→`E3_reconciled/`, `E3_unified/`→`E4_unified/`, `E4_analysis/`→`E5_analysis/`. |
| **Sufixos de JSON renomeados** | `-3_reconciled`→`-3_reconciled`, `-4_unified`→`-4_unified`, `-5_analysis`→`-5_analysis`. |
| **Scripts renomeados** | `e5_render.py`→`e6_render.py`, `e5_regen.py`→`e6_regen.py`, `analyze_e3_financials.py`→`analyze_e4_financials.py`, `execute_e5.py`→`execute_e6.py`, `generate_e5_report.py`→`generate_e6_report.py`. |
| **Novo comando: E-reset-from** | Reprocessamento parcial a partir de uma etapa específica, limpando artefatos daquela etapa em diante. Evita re-extrair PDFs quando só regras de categorização ou análise mudaram. |
| **E5-regen → E6-regen** | Renomeado para consistência. |

### v4.3 → v4.4

| Mudança | Motivo |
|---|---|
| **Novo card S2: Programa de Milhas — Economia** | Família acumula milhas em múltiplos programas (Livelo, Smiles, Atomos, etc.). Card mostra saldo estimado e economia gerada por resgates no período. Ângulo: economia no fluxo de caixa (S2), não investimento (S3). |
| **Novo input manual: `config/milhas.md`** | Programas de milhas não geram PDFs padronizados. Input manual com saldos e resgates, atualizado a cada ciclo. |
| **Nova chave E4: `programa_milhas`** | E4 lê `config/milhas.md` + `pontos_milhas-4_unified.json` (se existir) e gera bloco com programas, saldos, valores estimados, resgates e economia total. |
| **`e5_render.py` atualizado** | Nova função `build_milhas_card`. Injetada em S2 após Diagnóstico Comportamental. |
| **Cards obrigatórios: 16 → 17** | Lista expandida para incluir card de milhas. Numeração ajustada. |

### v4.2 → v4.3

| Mudança | Motivo |
|---|---|
| **Novo item E4 9: Estratégia de Contrafluxo na Renda Fixa** | Card #12 Contrafluxo (S3) existia no E5 e report_spec mas não tinha lógica de geração no E4. Novo item 9 formaliza: classificar cenário Selic (alta/queda/baixa), ler valores de aporte CDI/IPCA+, gerar `acao_pratica` personalizada. Referência: AUVP/Raul Sena. |
| **Schema E4 atualizado: `investimentos.contrafluxo`** | Chave `investimentos.contrafluxo` adicionada ao schema `analise_financeira-5_analysis.json` com: `cenario_atual`, `selic_atual`, faixas de Selic, `valor_cdi`, `valor_ipca`, `acao_pratica`. |
| **Lista de outputs E4 item 16 expandida** | Linha `investimentos.contrafluxo` adicionada à lista de blocos obrigatórios do JSON de análise. |

### v4.1 → v4.2

| Mudança | Motivo |
|---|---|
| **Novo item E4 1c: Orçamento Prospectivo com legenda obrigatória** | Card "Orçamento Prospectivo" não explicava o que os valores representam. Novo item E4 1c formaliza a geração do bloco `orcamento_prospectivo` com chave `legenda` obrigatória. Card E5 agora exibe texto "Como usar" antes da tabela, informando que são médias mensais e qual o % sobre a receita recorrente. |
| **Novo item E4 6b: Tabelas-resumo por categoria** | Relatórios faltavam tabelas consolidadas com Categoria, Valor (R$) e % do Total. Novo item obriga E4 a gerar blocos `tabela_categorias`, `tabela_receitas` e `tabela_classes` com arrays ordenados por valor decrescente. |
| **3 novos cards obrigatórios E5** | Patrimônio por Categoria (S1), Receitas por Fonte (S1) e Investimentos por Classe (S3). Todos seguem formato padrão: tabela com 3 colunas (Categoria, Valor R$, % do Total). |
| **`e5_render.py` atualizado** | 3 novas funções: `build_patrimonio_categorias_card`, `build_receitas_fonte_card`, `build_investimentos_classe_card`. Injetadas em S1 e S3. |
| **Cards obrigatórios: 13 → 16** | Lista expandida de 13 para 16 cards. Numeração ajustada. |
| **Patrimônio card inclui rodapé** | Linhas "(-) Dívidas" e "PATRIMÔNIO INVESTÍVEL" fora do array principal, como no design de referência. |

### v4.0 → v4.1

| Mudança | Motivo |
|---|---|
| **Novo output E3: `fluxo_mensal_detalhado-4_unified.json`** | Gráfico `receita_despesa_mensal` usava médias planas (`* 12`), não dados reais. Novo JSON detalha receitas por origem nomeada (Arvo, BrandLovers, Arbitralis, Learn To Fly, Einstein, Aluguéis, Rendimentos) e despesas por categoria, mês a mês. |
| **Nova chave E4: `receita_despesa_mensal_detalhado`** | E4 agora monta datasets prontos para Chart.js stacked bar: N datasets de receita (por origem) + N datasets de despesa (por categoria), com arrays de tamanho = número de meses. |
| **E5 `receita_despesa_mensal` usa dados reais** | `e5_render.py` lê `receita_despesa_mensal_detalhado` e gera barras empilhadas com dados mensais reais. Fallback para médias planas se chave ausente (legado). |
| **Schema E4 atualizado** | Chave `receita_despesa_mensal_detalhado` adicionada ao schema `analise_financeira-5_analysis.json`. |

### v3.2 → v4.0

| Mudança | Motivo |
|---|---|
| **Nova sub-etapa E4.N — Narrativas** | Toda geração de texto (perfil da família, summaries, chart contexts/conclusions, cards narrativos) movida de E5 para E4. E4 JSON agora inclui chave `narrativas` com HTML pronto. |
| **E5 reescrita como script Python puro** | `scripts/e5_render.py` substitui execução por LLM. E5 é 100% determinística: mesmos inputs = mesmo output. Tempo de execução: <5 segundos. |
| **Novo schema E4: chave `narrativas`** | Contém `perfil_familia` (left/right HTML), `summaries` (s1-s10), `charts` (19 pares context/conclusion). Documentação completa na seção E4.N. |
| **Canvas IDs canônicos mapeados** | Script usa mapeamento explícito de chart keys para canvas IDs (patrimonio_doughnut → chart-patrimonio-doughnut). Elimina variação de nomes entre execuções. |
| **E5-regen simplificado** | Para mudanças de template: `python scripts/e5_render.py`. Para mudanças de texto: re-rodar E4.N + `python scripts/e5_render.py`. |
| **Scripts legados depreciados** | `execute_e5.py` e `generate_e5_report.py` substituídos por `scripts/e5_render.py`. Mantidos no repositório para referência histórica. |
| **Separação de concerns** | E4 = análise + narrativa (LLM). E5 = renderização pura (script). Debugging mais fácil: erro no texto → E4. Erro no layout → template. Erro nos dados → E2/E3/E4. |

### v3.1 → v3.2

| Mudança | Motivo |
|---|---|
| **Migração para Git** | Versionamento ad-hoc (`output/archive/`, `_v1`, `.bak`, `version_log.md`) substituído por repositório Git. Todas as versões anteriores agora acessíveis via `git log` / `git show`. |
| **Nova Seção 4.5 — Versionamento com Git** | Documenta o que está no Git, fluxo de commits, convenção de mensagens, e como recuperar versões anteriores. |
| **`output/archive/` removido** | Diretório eliminado da estrutura. Git é o archive. |
| **`logs/version_log.md` removido** | Substituído pelo histórico Git. Logs operacionais (inbox, run, qa, divergences, reconciliation) mantidos. |
| **Seção 5.1 reescrita** | Fluxo de atualização de arquivos agora usa `e_save.py` (manual) + sobrescrita em vez de renomear com `_v1`. |
| **E5.6 e E5-regen atualizados** | "Mover para archive" substituído por "comitar via Git antes de sobrescrever". |
| **`.gitignore` adicionado** | Exclui `data/`, `inbox/`, `inbox_processed/`, `.DS_Store`, `.obsidian/`, e backups legados. |

### v3.0 → v3.1

| Mudança | Motivo |
|---|---|
| **`[membro]s-1b_unified.json` corrigido para `members-1b_unified.json`** | Nome anterior gerava confusão: LLM criava arquivo por membro ao invés de consolidado único. Alinhado com Apêndice D e estado real do disco. |
| **Contagem canvas IDs corrigida: 18 → 19** | V4 na validação E5.6 dizia 18 mas as tabelas E5.4+E5.5 somam 19 IDs distintos. Nota sobre alias `fluxo_mensal` adicionada. |
| **Contagem chaves JSON top-level corrigida para 14** | Lista explícita das 14 chaves adicionada na validação E5.3 para evitar ambiguidade. |
| **Schemas adicionados: currículo, holerite, seguros, analise_financeira** | Seção 7.2 com schemas formais que faltavam. O schema do E5 (`analise_financeira-5_analysis.json`) é crítico pois é o input principal do E6. |
| **Fórmula do score financeiro especificada** | E4 item 5 agora tem média ponderada de 5 componentes com critérios 0/10 e 10/10, classificação e interpolação linear. |
| **Critérios de tarefas e alertas adicionados** | E4 item 9 (novo) com tabelas de gatilhos para geração de tarefas (12 critérios) e alertas (8 critérios), formatos e prioridades. |
| **Formato de [DATE] especificado** | `YYYYMMDD` sem hífens. Ex: `20260403`. Antes não documentado, causando variação entre execuções. |
| **Tipo `faturacc` esclarecido** | Schema agora usa códigos de roteamento (`faturacarbon`, `faturaunique`, `faturapaoacucar`) em vez de genérico `faturacc`. |
| **Instrução de origem `report_template.html` adicionada** | Nova Seção 1.1.1 explica que o template HTML não é gerado pelo pipeline — deve pré-existir ou ser fornecido pelo usuário. |
| **Nota sobre E1.5 outputs em `E2_extracts/`** | Esclarece por que outputs de E1.5 ficam em `processed/E2_extracts/` (convenção: inputs diretos para E2). |
| **Contagem "6 configs" esclarecida** | Agora especifica "5 em config/ + 1 em life_plan/" para evitar confusão. |

### v2.1 → v3.0

| Mudança | Motivo |
|---|---|
| **Listas explícitas de arquivos removidas** | Substituídas por regras de detecção genéricas baseadas em padrões (instituição, tipo de documento, período). Pipeline agora funciona com qualquer volume de arquivos desconhecidos. |
| **Categorias de arquivo em vez de enumerações** | GRUPO A-F agora descrevem categorias de padrões (extratos, IRPF, imóveis, veículos, pessoais, referência) com exemplos, não listas completas. |
| **Arquivo renomeado sem versão** | Mudança: `manual_operacao_v2.1.md` → `manual_operacao.md`. Versão agora rastreada internamente no header `## Versão: 3.0`. |
| **"Versão do Prompt" → "Versão Manual Operações"** | Referências em relatórios agora usam nome mais descritivo. Placeholder `{{COVER_VERSAO}}` lê desta versão do manual. |
| **Dashboard → Tático** | Modo de visualização renomeado. Toggle agora é "Estratégico / Tático" em vez de "Estratégico / Dashboard". |
| **Referência a arquivo de prompt removida** | Removida menção a `prompt_planejamento_financeiro_v4_3.md` em GRUPO F. Arquivos de referência são agora apenas: manual e relatórios HTML existentes. |
| **Onboarding de primeira execução** | Adicionada Seção 1.1 com instruções para geração automática de config quando arquivos não existem, usando templates. |
| **Instruções E5 para atualizações de placeholders** | E5 agora especifica que `{{COVER_DATA_HORA}}` e `{{COVER_VERSAO}}` são atualizados a cada geração de relatório; `{{COVER_PERIODO}}` atualizado quando novos arquivos processados. |
| **Categoria "Seguros" adicionada** | `seguros-4_unified.json` agora captura prêmios, coberturas e vencimentos (extraído de faturas e holerites). |
| **Nenhuma contagem hardcoded** | Removidas referências a "89 arquivos", "77 arquivos", etc. Texto agora genérico: "todos os arquivos detectados" ou "varies based on input". |

### v2.0 → v2.1

| Mudança | Motivo |
|---|---|
| **Remoção da separação rígida Cowork/Chat** | Qualquer ambiente (Cowork ou Chat) pode executar qualquer etapa. Execução é agnóstica ao ambiente. |
| **Detecção inteligente de ciclo (SMART CYCLE)** | Ciclos não são mais fixos (quinzenal/trimestral). Pipeline detecta tipos de arquivo e determina quais etapas são necessárias. |
| **Suporte a veículos (XLSX)** | Novo diretório `data/vehicles/` com tipo `dados_veiculos` e padrão `dados_veiculos-0_original.xlsx`. Extração em E1.5. |
| **Documentos pessoais (BR e US)** | Novos tipos em `members/`: RG, CPF, passaporte, visto, certidão, SSN, drivers license, green card. Enriquecem `members-1c_enriched.md`. |
| **Categoria "outros ativos"** | Patrimônio expandido para incluir veículos, ações, criptos, joias, arte — não só imóveis. Arquivo `patrimonio-4_unified.json` (consolidação de TODOS os ativos do IRPF). |
| **Versionamento via Git** | Quando arquivo existente é atualizado (novo CV, novo IRPF): comitar estado atual via Git antes de sobrescrever, re-extrair. Histórico acessível via `git log`. |
| **Tratamento de sobreposição de dados** | E2.5 reconciliação detecta duplicatas por data+amount+description, retém apenas novos. E3/E4 podem ser incrementais. |
| **JSON schemas em apêndice** | Esquemas explícitos para -2_extract.json para cada tipo de documento. Permite execução sem memória prévia. |
| **Seção 4 reescrita como "PIPELINE STAGES"** | Cada estágio descrito independentemente, especificando inputs/outputs/validação. Não mais amarrado a "Momento 1/2" ou "Cowork/Chat". |
| **Diretório `data/vehicles/` adicionado** | Estrutura de diretórios atualizada. Agora 89 arquivos + veículos (se presentes). |
| **Seção "Incremental Updates"** | Nova seção explicando como pipeline trata novos arquivos para períodos existentes, versões atualizadas, e novos tipos de arquivo. |
| **Diagrama visual atualizado** | Apêndice com fluxo revisado refletindo detecção inteligente e processamento agnóstico. |
| **Manual auto-contido** | Instruções explícitas para leitura de PDFs e XLSX. Schemas completos. Uma execução fresca pode rodar tudo do zero lendo apenas este manual. |

### v1.0 → v2.0

| Mudança | Motivo |
|---|---|
| **E0.B (desempacotamento ZIP) removido** | PDFs são PDFs reais, não ZIPs disfarçados. Confirmado no setup inicial (QA-5). |
| **XLSX agora tem extração formal** | `dados_imoveis-0_original.xlsx` contém datas de compra, valores e dados cadastrais — fonte primária de patrimônio imobiliário. |
| **Income Tax processado ANTES de Financial Statements** | Declarações IRPF são o snapshot mais completo do patrimônio e servem de baseline para validar extratos. |
| **Sessão dedicada para IR + Imóveis** | Nova Sessão 4 (E1.5) extrai patrimônio-base antes dos extratos bancários. |
| **Contagem atualizada: 89 arquivos (não 80)** | +7 Bradesco Poupança, +1 holerite Mariana, +1 posição Rico. |
| **Novos tipos: `extratopoupanca`, `holerite`, `investimentosposicao` (Rico)** | Descobertos no primeiro ciclo. |
| **Referências a "(ZIP)" removidas** | Toda menção a `pdftotext`/unzip/manifest.json eliminada. |

---

## VISÃO GERAL

Este documento instrui qualquer ambiente de execução (Cowork, Chat, ou outro) em **TODAS as etapas** do pipeline financeiro da família Ferreira Campos.

O pipeline é **agnóstico ao ambiente**: tanto Cowork quanto Chat podem executar qualquer etapa. A única diferença é o contexto de execução (batch vs. iterativo).

| Situação | O que fazer | Frequência |
|---|---|---|
| **Setup inicial** | Criar estrutura de diretórios + organizar arquivos existentes | Uma vez, antes do primeiro ciclo |
| **Novo arquivo no inbox** | Detectar tipo + rotear para destino correto | Contínuo, conforme chegam |
| **Ciclo inteligente** | Analisar tipos de arquivo recebidos → determinar etapas necessárias → executar pipeline | Variável (quinzenal, trimestral, ou sob demanda) |

---

## ⚠️ REGRA DE OURO — ONDE CORRIGIR O QUÊ

**NUNCA editar diretamente os arquivos em `output/`.** O relatório final é sempre regenerado a partir do template + dados intermediários. Qualquer edição direta no output será sobrescrita no próximo ciclo.

### Diagnóstico rápido

| Sintoma                                           | Onde corrigir                                                          | Depois rodar      |
| ------------------------------------------------- | ---------------------------------------------------------------------- | ----------------- |
| Layout quebrado, CSS errado, JS com bug           | `config/templates/report_template.html`                                          | E6-regen          |
| Label de gráfico errado, texto fixo errado        | `config/templates/report_template.html`                                          | E6-regen          |
| Gráfico não renderiza (canvas não encontrado)     | `config/templates/report_template.html` (verificar IDs canônicos na Seção 4, E6) | E6-regen          |
| Valor de KPI errado, dado numérico incorreto      | `processed/E5_analysis/` (ou E2/E4 se o erro vem de extração)          | E5 + E6           |
| Transação categorizada errada                     | `processed/E4_unified/` ou regras em `config/definitions.md`           | E4 + E5 + E6      |
| Transação faltando ou duplicada                   | `processed/E2_extracts/` ou `E3_reconciled/`                           | E3 + E4 + E5 + E6 |
| Texto de seção mal escrito ou análise superficial | E5.N (narrativas) → E5.N + E6                                          | E5.N + E6         |
| Dados de membro errados (nome, cargo)             | `members/members-1c_enriched.md`                                       | E1 + E5 + E6      |
| Meta financeira desatualizada                     | `life_plan/life_plan_goals.md`                                         | E5 + E6           |

### Regra para o assistente

Quando o usuário pedir para "corrigir algo no relatório", o assistente DEVE:

1. **Diagnosticar a origem** — o erro é de apresentação (template) ou de dados (E1–E5)?
2. **Corrigir no arquivo-fonte** — seguindo a tabela acima
3. **Regenerar o relatório** — rodar E6 ou E6-regen conforme o caso
4. **Nunca editar `output/relatorio_*.html`** — este arquivo é descartável e regenerável

---

## SEÇÃO 1 — PRÉ-REQUISITOS

Antes de executar qualquer etapa, verificar que os seguintes arquivos já existem e estão disponíveis.

### 1.1 — Arquivos de config e primeira execução

#### Cenário A: Arquivos de config JÁ EXISTEM

O Chat já criou os arquivos de configuração previamente. Proceder direto para Seção 2.

#### Cenário B: Arquivos de config NÃO EXISTEM (primeira execução)

Se os arquivos abaixo não existem em `financas-familia/config/`, o pipeline deve:

1. **Detectar a ausência** dos 5 arquivos de config esperados
2. **Perguntar ao usuário** as informações necessárias para gerá-los
3. **Usar templates** em `config/templates/` como base
4. **Gerar cada arquivo** preenchido com as respostas do usuário

**Templates disponíveis:**
```
config/templates/
├── definitions_template.md
├── decisions_template.md
├── methodology_template.md
├── report_spec_template.md
└── source_hierarchy_template.md
```

**Fluxo de onboarding:**
```
Detectou ausência de config → Apresentar menu de configuração inicial
 ↓
Perguntar: "Qual é o nome completo do titular?" → definições
 ↓
Perguntar: "Quais são suas principais prioridades financeiras?" → decisões
 ↓
Perguntar: "Como você prefere categorizar despesas?" → definitions
 ↓
... [repetir para cada config]
 ↓
Preencher templates com respostas → Gerar archivos finais
 ↓
Copiar para financas-familia/config/ → Prosseguir com Seção 2
```

Se template não existir, usar estrutura mínima e solicitar revisão manual depois.

### 1.1.1 — Template de relatório HTML

O arquivo `config/templates/report_template.html` é o template estrutural para o relatório final (E6). Ele contém a estrutura HTML, CSS, JavaScript (Chart.js) e placeholders `{{...}}` que são preenchidos durante E6.

- **Se já existir** em `config/templates/report_template.html`: usar como está (não gerar automaticamente).
- **Se não existir**: solicitar ao usuário. Este arquivo é criado manualmente ou por um designer — o pipeline NÃO o gera automaticamente, apenas o popula.
- **Requisitos mínimos do template:** deve conter os 19 canvas IDs listados em E6.4/E6.5, os placeholders `{{COVER_*}}`, `{{KPI_*}}`, `{{SUMMARY_S*}}`, `{{CONTENT_S*}}`, `{{CONTENT_APP_*}}`, `{{PERFIL_FAMILIA_*}}`, `{{REPORT_DATA_JSON}}` e `{{FOOTER_CONTENT}}`.

### 1.1.2 — Arquivos de config operacionais

Além dos 5 arquivos de config gerados no onboarding, o pipeline depende dos seguintes arquivos operacionais que devem existir em `config/`:

| Arquivo | Descrição | Gerado automaticamente? |
|---|---|---|
| `config/pipeline.json` | Parâmetros operacionais: modelo LLM, limites, tolerâncias, nomes de artefatos | Não — criado manualmente ou copiado de template |
| `config/categorization.json` | Keywords de categorização de receitas/despesas, `pj_source_mapping`, `clt_source_mapping` | Não — curado manualmente |
| `config/family_members.json` | Dados cadastrais da família, `banco_membro`, `account_type_equivalences` | Não — curado manualmente |
| `config/passwords.txt` | Senhas de PDFs e ZIPs protegidos (usado por `e0_unlock.py`) | Não — **NÃO versionado** (`.gitignore`) |
| `config/milhas.md` | Saldos e resgates de programas de milhas (input manual para card S2) | Não — atualizado a cada ciclo |
| `config/tarefas.md` | Backlog curado de tarefas financeiras | Não — atualizado a cada ciclo |
| `config/regras_composicao_patrimonial.md` | Regras canônicas de composição patrimonial | Não — curado manualmente |
| `config/schemas/baseline_patrimonial.schema.json` | JSON Schema para validação do baseline E1.5 | Sim — parte do repositório |

### 1.2 — Localização dos arquivos financeiros

O usuário deve informar o caminho onde estão os arquivos financeiros originais antes do Setup Inicial. Nos ciclos futuros, os arquivos chegam em `/inbox/`.

### 1.3 — Caminho raiz

O usuário informa onde criar `financas-familia/`. Pode ser em Google Drive, pasta local, ou qualquer caminho acessível. Toda referência neste documento usa `financas-familia/` como raiz relativa.

---

## SEÇÃO 2 — SETUP INICIAL

Executar uma única vez para preparar a estrutura de diretórios e organizar todos os arquivos iniciais.

### 2.1 — Criar estrutura de diretórios

Criar a estrutura completa abaixo. Se algum diretório já existir, apenas continuar.

```
financas-familia/
├── inbox/
├── inbox_processed/
├── config/
├── members/
├── life_plan/
├── data/
│   ├── financial_statements/
│   ├── income_tax_br/
│   ├── income_tax_us/
│   ├── real_estate/
│   └── vehicles/
├── processed/
│   ├── E2_extracts/
│   ├── E3_reconciled/
│   ├── E4_unified/
│   └── E5_analysis/
├── output/
└── logs/
```

Confirmar ao usuário mostrando a listagem de diretórios criados.

### 2.2 — Copiar os arquivos de config

Copiar os 5 arquivos de config que foram gerados previamente (ou onboarded em 1.1):

```bash
cp [origem]/methodology.md     financas-familia/config/
cp [origem]/definitions.md     financas-familia/config/
cp [origem]/decisions.md       financas-familia/config/
cp [origem]/source_hierarchy.md financas-familia/config/
cp [origem]/report_spec.md     financas-familia/config/
cp [origem]/life_plan_goals.md financas-familia/life_plan/
```

### 2.3 — Organizar os arquivos originais (E0.A)

Para cada arquivo que o usuário fornece:

1. Copiar para `inbox_processed/[DATA-DE-HOJE]/` com o **nome original** (auditoria)
2. **Detectar o tipo** usando regras da Seção 3 (instituição, tipo de documento, período)
3. **Validar integridade:** verificar que o arquivo tem tamanho > 0 bytes. Arquivos vazios ou < 1KB devem ser registrados em `qa_log.md` como `WARN | Arquivo [nome] vazio ou corrompido ([tamanho] bytes) — NÃO roteado` e **NÃO movidos** para o destino.
4. **Mover** (não copiar) para o **diretório de destino** com o **nome final** (sufixo `-0_original` inserido antes da extensão). Após o move, o arquivo NÃO deve permanecer no inbox.
5. Se o arquivo de destino já existir, **não sobrescrever** — registrar como duplicata no log

**Regras críticas:**
- Nunca modificar o conteúdo dos arquivos — apenas mover e renomear.
- Apenas o arquivo com o **nome original** deve existir em `inbox_processed/` (auditoria). O arquivo renomeado NÃO é copiado para `inbox_processed/`.
- Ao final de E0.A, o inbox deve estar **vazio** (exceto arquivos não identificados, que vão para `inbox_processed/[DATA]/nao_identificados/`).

#### GRUPO A — `data/financial_statements/` — Extratos e faturas

**Padrão de detecção:**
- Instituições: C6 Bank, Itaú, Santander, Bradesco, BTG Pactual, Rico, PicPay, Wise, Bank of America, Binance
- Tipos: extratos de conta (CC, PJ, Global), poupança, faturas de cartão, posições de investimento, CDBs, faturas de aluguel

**Convenção de nomenclatura:**
```
[instituição]_[tipo]_[período]-0_original.[extensão]
```

**Exemplos:**
- `c6bank_extratoconta_202603-0_original.pdf` ← Extrato C6 março 2026
- `itau_faturapaoacucar_202601-0_original.pdf` ← Fatura Pão de Açúcar janeiro 2026
- `itau_extratocontapersonnalite_202505_202603-0_original.pdf` ← Extrato Itaú Personnalité (sub-variante de conta)
- `santander_cdbdetalhes_202603-0_original.pdf` ← Detalhe CDB Santander março 2026
- `bradesco_extratopoupanca_202602_202603-0_original.pdf` ← Poupança fevereiro-março 2026
- `quintoandar_faturaaluguelcalixto_202602-0_original.pdf` ← Fatura aluguel QuintoAndar (propriedade Calixto)
- `quintoandar_faturaaluguelmajorfreire_202602-0_original.pdf` ← Fatura aluguel QuintoAndar (propriedade Major Freire)

**Nota sobre sub-variantes e propriedades:** Quando o tipo de conta ou propriedade é relevante, o identificador é **colado ao tipo** sem underscore separador (ex: `extratocontapersonnalite`, `faturaaluguelcalixto`). O underscore seguinte separa o período: `[instituição]_[tipo][variante]_[período]-0_original.[ext]`.

**Nota sobre sufixo de letra (colisão de nomes):** Quando dois ou mais arquivos **distintos** (hashes diferentes) gerariam o mesmo nome destino, adicionar uma letra ao final do período: `a`, `b`, `c`, etc. Formato: `[instituição]_[tipo]_[período][letra]-0_original.[ext]`. Exemplo: `binance_extratoconta_202603a-0_original.jpg`, `binance_extratoconta_202603b-0_original.jpg`. O sufixo é transparente para o pipeline — E2 preserva no JSON e E3 faz merge automático.

**Destino:** `data/financial_statements/[nome_final]`

---

#### GRUPO B — `data/income_tax_br/` — Declarações de imposto e informes de renda

**Padrão de detecção:**
- Tipos: declarações IRPF, recibos IRPF, informes de rendimento (QuintoAndar)

**Convenção de nomenclatura:**
```
[instituição]_[tipo]_[ano ou período]-0_original.[extensão]
```

**Exemplos:**
- `receitafederal_irpfdeclaracao_2024-0_original.pdf` ← IRPF 2024 (David, titular — sem sufixo de membro)
- `receitafederal_irpfdeclaracaomariana_2024-0_original.pdf` ← IRPF 2024 Mariana
- `receitafederal_irpfrecibo_2024-0_original.pdf` ← Recibo IRPF 2024
- `receitafederal_irpfrecibomariana_2024-0_original.pdf` ← Recibo IRPF 2024 Mariana
- `quintoandar_informerendimentosaluguel_2025-0_original.pdf` ← Informe aluguel 2025
- `quintoandar_informerendimentosaluguelmariana_2025-0_original.pdf` ← Informe aluguel 2025 Mariana

**Regra multi-membro:** Quando há declarações/informes de mais de um membro, o nome do membro é colado ao tipo (sem underscore separador): `[instituição]_[tipo][membro]_[período]-0_original.[ext]`. O titular (David) pode omitir o sufixo; todos os demais membros devem incluí-lo.

**Destino:** `data/income_tax_br/[nome_final]`

---

#### GRUPO C — `data/real_estate/` — Dados de imóveis (XLSX)

**Padrão de detecção:**
- Nome contém "imovel", "real_estate", ou arquivo é XLSX em contexto imobiliário
- Conteúdo: endereço, data de compra, valor, financiamento

**Convenção de nomenclatura:**
```
dados_imoveis-0_original.xlsx
```

**Exemplo:**
- `dados_imoveis-0_original.xlsx` ← Planilha com dados de todos os imóveis

**Destino:** `data/real_estate/[nome_final]`

---

#### GRUPO D — `data/vehicles/` — Dados de veículos (XLSX)

**Padrão de detecção:**
- Nome contém "veiculo", "vehicles", "carro", ou arquivo é XLSX em contexto automotivo
- Conteúdo: marca, modelo, ano, placa, data de aquisição, valor

**Convenção de nomenclatura:**
```
dados_veiculos-0_original.xlsx
```

**Exemplo:**
- `dados_veiculos-0_original.xlsx` ← Planilha com dados de veículos

**Destino:** `data/vehicles/[nome_final]`

---

#### GRUPO E — `members/` — Documentos pessoais e profissionais

**Padrão de detecção:**
- Tipos: currículos (DOCX, PDF), holerites, RG, CPF, passaporte, visto, certidões, documentos US (SSN, drivers license, green card)
- Nome contém nome do membro + tipo de documento

**Convenção de nomenclatura:**
```
[nome_membro]_[tipo]-0_original.[extensão]
```

**Exemplos:**
- `david_curriculo-0_original.docx` ← CV David
- `mariana_holerite_202602-0_original.pdf` ← Holerite Mariana fevereiro 2026
- `david_rg-0_original.pdf` ← RG David
- `mariana_passaporte-0_original.pdf` ← Passaporte Mariana
- `david_green_card-0_original.pdf` ← Green Card David (documento US)

**Destino:** `members/[nome_final]`

---

#### GRUPO F — NÃO MOVER (Referência)

Arquivos que não pertencem ao pipeline e devem ser mantidos em local seguro:
- Manual de operações atual (`financas-familia/config/manual_operacao.md`)
- Relatórios HTML gerados existentes

**Ação:** Ignorar durante roteamento. Mantidos no local original; Git rastreia o histórico de alterações.

---

### 2.4 — Gerar logs do setup

**`logs/inbox_log.md`:**

```markdown
# Inbox Log — Pipeline Ferreira Campos

## Setup inicial — [DATA-DE-HOJE] — [N] arquivos

### Resumo

| Métrica | Valor |
|---|---|
| Total processados | [N] |
| Movidos com sucesso | [N] |
| Duplicatas ignoradas | [N] |
| Erros | [N] |
| data/financial_statements/ | [N] |
| data/income_tax_br/ | [N] |
| data/real_estate/ | [N] |
| data/vehicles/ | [N] |
| members/ | [N] |
| Não movidos | [N] |

### Detalhamento

| # | Nome original | Nome final | Destino | Status |
|---|---|---|---|---|
| 1 | [nome_original] | [nome_final] | data/financial_statements/ | ✅ |
| 2 | [nome_original] | [nome_final] | members/ | ✅ |
| ... | ... | ... | ... | ... |
```

**`logs/run_log.md`:**

```markdown
# Run Log — Pipeline Ferreira Campos

## E0.A — Organização — Setup inicial — [DATA-DE-HOJE]

### Resumo

| Métrica | Valor |
|---|---|
| Arquivos processados | [N] |
| PDFs | [N] |
| XLSX | [N] |
| DOCX | [N] |
| Outras extensões | [N] |

### Detalhamento

| Arquivo | Tipo detectado | Destino | Status |
|---|---|---|---|
| [nome] | [tipo] | [destino] | ✅ OK |
| ... | ... | ... | ... |
```

---

### 2.5 — Verificações finais do setup

Executar os comandos abaixo e reportar os resultados:

```bash
# V1 — Contagem por diretório
echo "financial_statements:" && ls financas-familia/data/financial_statements/ 2>/dev/null | wc -l
echo "income_tax_br:"        && ls financas-familia/data/income_tax_br/ 2>/dev/null | wc -l
echo "real_estate:"          && ls financas-familia/data/real_estate/ 2>/dev/null | wc -l
echo "vehicles:"             && ls financas-familia/data/vehicles/ 2>/dev/null | wc -l
echo "members:"              && ls financas-familia/members/ 2>/dev/null | wc -l
echo "config:"               && ls financas-familia/config/ 2>/dev/null | wc -l
echo "life_plan:"            && ls financas-familia/life_plan/ 2>/dev/null | wc -l

# V2 — Todos os arquivos têm sufixo correto
find financas-familia/data/ financas-familia/members/ -type f 2>/dev/null \
  | grep -v "\-0_original\."

# V3 — Auditoria intacta
ls financas-familia/inbox_processed/[DATA-DE-HOJE]/ 2>/dev/null | wc -l

# V4 — Logs gerados
ls financas-familia/logs/ 2>/dev/null

# V5 — Inbox vazio (todos os arquivos devem ter sido movidos)
echo "inbox residual:" && find financas-familia/inbox/ -type f 2>/dev/null | wc -l
# Esperado: 0. Se > 0, listar arquivos restantes como erro.

# V6 — Contagem inbox_processed == contagem inbox_log
echo "inbox_processed (apenas nomes originais):" && \
  find financas-familia/inbox_processed/[DATA-DE-HOJE]/ -type f 2>/dev/null | wc -l
# Esperado: igual ao "Total processados" no inbox_log.md.
# inbox_processed deve conter APENAS arquivos com nome original (auditoria), NÃO renomeados.

# V7 — Nenhum arquivo de 0 bytes nos diretórios de destino
find financas-familia/data/ financas-familia/members/ -type f -empty 2>/dev/null
# Esperado: nenhum resultado. Arquivos vazios indicam problema na cópia/download original.
```

---

### 2.6 — Mensagem final do setup

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SETUP INICIAL CONCLUÍDO — [DATA]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Estrutura criada            ✅
  Configs copiados            ✅  (5 em config/ + 1 em life_plan/)
  Arquivos organizados        ✅  [N] movidos · [N] duplicatas
  Logs gerados                ✅  (3 arquivos)

  Próximos passos:
  1. Novos arquivos vão para financas-familia/inbox/
  2. Pipeline detectará tipos e rotará automaticamente
  3. Executar etapas conforme necessário

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## SEÇÃO 3 — DETECÇÃO INTELIGENTE DE CICLO (SMART CYCLE)

A partir do setup, toda vez que novos arquivos chegam em `/inbox/`, o pipeline detecta os tipos de arquivo e determina quais etapas executar.

### 3.1 — Algoritmo de detecção

Para cada novo arquivo em `/inbox/`:

**Passo 1 — Detectar tipo real:**
```bash
file [arquivo]
```

> **Nota sobre arquivos JPG/PNG:** Para imagens, o conteúdo não pode ser inspecionado como texto (requer OCR, que será feito em E2). A detecção de tipo e instituição é feita **exclusivamente pelo nome do arquivo**. Rotear normalmente com base no nome; o OCR será aplicado na etapa E2.

**Passo 2 — Identificar a instituição** pela combinação de nome + conteúdo:

| Padrões no nome                             | Padrões no conteúdo                                            | Instituição     | Entidade                  |
| ------------------------------------------- | -------------------------------------------------------------- | --------------- | ------------------------- |
| `c6`, `carbon`, `c6bank`                    | "C6 Bank", "Carbon"                                            | C6 Bank         | `c6bank`                  |
| `itau`, `itaú`, `personnalite`, `paoacucar` | "Itaú", "Personnalité"                                         | Itaú            | `itau`                    |
| `santander`, `unique`                       | "Santander", "Unique"                                          | Santander       | `santander`               |
| `bradesco`                                  | "Bradesco"                                                     | Bradesco        | `bradesco`                |
| `btg`, `btgpactual`                         | "BTG Pactual"                                                  | BTG Pactual     | `btgpactual`              |
| `rico`, `xp`                                | "Rico", "XP Investimentos"                                     | Rico/XP         | `rico`                    |
| `picpay`                                    | "PicPay"                                                       | PicPay          | `picpay`                  |
| `wise`                                      | "Wise", "TransferWise"                                         | Wise            | `wise`                    |
| `bofa`, `bankofamerica`                     | "Bank of America"                                              | Bank of America | `bankofamerica`           |
| `quintoandar`, `quinto_andar`               | "QuintoAndar", "GRPQA", "GRPQA Ltda.", "Grpqa", "SISPAG GRPQA" | QuintoAndar     | `quintoandar`             |
| `binance`                                   | "Binance"                                                      | Binance         | `binance`                 |
| `receita`, `rfb`, `irpf`                    | "Receita Federal", "IRPF"                                      | Receita Federal | `receitafederal`          |
| `einstein`, `sociedade beneficente`         | "Hospital Israelita", "Einstein"                               | Einstein        | — (holerite → `members/`) |

**Passo 3 — Identificar o tipo de documento:**

| Indicadores | Tipo | Código |
|---|---|---|
| "extrato", "lançamentos", "statement" | Extrato conta corrente | `extratoconta` |
| "extrato" + "Personnalité" ou conta Personnalité | Extrato conta Personnalité | `extratocontapersonnalite` |
| "extrato" + "PJ", "pessoa jurídica", CNPJ | Extrato conta PJ | `extratocontapj` |
| "global", "USD" | Extrato conta global USD | `extratocontaglobalusd` |
| "global", "EUR" | Extrato conta global EUR | `extratocontaglobaleur` |
| "poupança", "caderneta", "savings" | Extrato poupança | `extratopoupanca` |
| "fatura", "carbon" | Fatura C6 Carbon | `faturacarbon` |
| "fatura", "unique" | Fatura Santander Unique | `faturaunique` |
| "fatura", "pão de açúcar" | Fatura Itaú Pão de Açúcar | `faturapaoacucar` |
| "posição", "carteira", "investimentos" | Posição de investimentos | `investimentosposicao` |
| "renda fixa", "CDB" | Carteira renda fixa | `carteirarendafixa` |
| "CDB", "detalhe" + número | Detalhe CDB Santander | `cdbdetalhes` |
| "resumo" + CDB | Resumo CDB | `cdbresumo` |
| "fatura" + "aluguel" | Fatura de aluguel QuintoAndar | `faturaaluguel[propriedade]` (ex: `faturaaluguelcalixto`, `faturaaluguelmajorfreire`) |
| "informe", "rendimentos" | Informe de rendimentos | `informerendimentos` |
| "declaração", "IRPF" | Declaração IRPF | `irpfdeclaracao` |
| "recibo", "entrega" + IRPF | Recibo IRPF | `irpfrecibo` |
| "currículo", "resume", "CV" | Currículo | `curriculo` |
| "holerite", "contracheque", "folha de pagamento" | Holerite | `holerite` |
| "RG", "Registro Geral", "identidade" | RG | `rg` |
| "CPF", "pessoa física" | CPF | `cpf` |
| "passaporte" | Passaporte | `passaporte` |
| "visto" | Visto | `visto` |
| "certidão", "nascimento" | Certidão de nascimento | `certidao_nascimento` |
| "certidão", "casamento" | Certidão de casamento | `certidao_casamento` |
| "SSN", "Social Security" | Social Security Number (US) | `ssn` |
| "drivers", "driver's", "carteira de motorista" | Carteira de motorista (US) | `drivers_license` |
| "green card", "resident" | Green Card (US) | `green_card` |
| "Dados_Imoveis", "imóveis" (XLSX) | Dados de imóveis | `dados_imoveis` |
| "veículos", "vehicles", "carros" (XLSX) | Dados de veículos | `dados_veiculos` |

**Passo 4 — Extrair o período:**
- Padrão preferencial: `YYYYMM` ou `YYYYMM_YYYYMM` no nome
- Para documentos anuais (IRPF, informes de rendimentos): usar apenas `YYYY` como período (ex: `receitafederal_irpfdeclaracao_2024-0_original.pdf`)
- Se não houver período no nome, verificar conteúdo
- Para arquivos sem período identificável, usar `[AAAAMMDD]` (data de hoje) e registrar em `qa_log.md`

**Passo 5 — Determinar diretório de destino:**

| Tipo de documento | Diretório |
|---|---|
| Extratos de conta, faturas, posições de investimento, CDBs | `data/financial_statements/` |
| Declarações IRPF, recibos, informes de rendimento | `data/income_tax_br/` |
| Planilhas de imóveis | `data/real_estate/` |
| Planilhas de veículos | `data/vehicles/` |
| Currículos, holerites, documentos pessoais | `members/` |
| Documentos fiscais US (Form 1040, FBAR) | `data/income_tax_us/` |

**Passo 6 — Construir nome final:**
```
[entidade]_[tipo]_[periodo]-0_original.[ext]
```

Exemplos:
- `Extrato_Março_2026.pdf` → `itau_extratoconta_202603-0_original.pdf`
- `FATURA_CARBON_ABR2026.pdf` → `c6bank_faturacarbon_202604-0_original.pdf`
- `Bradesco_Extrato_01_03_2026.pdf` → `bradesco_extratoconta_202601_202603-0_original.pdf`
- `01.02.2026_28.02.2026.pdf` → `mariana_holerite_202602-0_original.pdf`
- `RG_David_2024.pdf` → `david_rg-0_original.pdf`
- `Dados_Veiculos_2026.xlsx` → `dados_veiculos-0_original.xlsx`

**Passo 7 — Verificar duplicata e colisão de nome:**
```bash
ls financas-familia/data/[destino]/[nome_final] 2>/dev/null
```
Se o arquivo destino **já existir**, comparar hashes:
- **Hash idêntico** (mesmo conteúdo) → registrar como `DUPLICATA IGNORADA` no inbox_log e **não mover**.
- **Hash diferente** (conteúdo distinto, mesmo nome) → **COLISÃO**. Aplicar sufixo de letra:
  1. Se o arquivo existente NÃO tem sufixo de letra, renomeá-lo adicionando `a` ao período: `bradesco_extratoconta_202603-0_original.pdf` → `bradesco_extratoconta_202603a-0_original.pdf`
  2. Nomear o novo arquivo com a próxima letra: `bradesco_extratoconta_202603b-0_original.pdf`
  3. Registrar a colisão e resolução no inbox_log.

**Convenção de sufixo de letra:** Quando múltiplos arquivos distintos compartilham o mesmo `[instituição]_[tipo]_[período]`, adicionar uma letra ao final do período: `a`, `b`, `c`, etc. Exemplos reais no pipeline: `binance_extratoconta_202603a` (screenshot página 1), `binance_extratoconta_202603b` (screenshot página 2), `itau_extratocontapersonnalite_202603a` e `202603b` (extratos parciais do mesmo mês).

O sufixo de letra é transparente para o pipeline downstream: E2 preserva o sufixo no nome do JSON, e E3 faz merge natural das transações de mesma conta.

**Passo 8 — Validar integridade antes de mover:**

**8a. Verificar tamanho:**
```bash
# Verificar tamanho do arquivo
stat -c %s financas-familia/inbox/[nome_original]
```
Se tamanho == 0 bytes (ou < 1KB para PDFs):
- Registrar em `logs/qa_log.md`: `[DATA] E0 | WARN | Arquivo [nome_original] vazio ou corrompido ([tamanho] bytes) — NÃO roteado`
- **NÃO mover** para o destino
- Manter no inbox para investigação manual

**8b. Verificar encriptação (PDFs) e descompactar ZIPs:**
Desbloquear PDFs protegidos e extrair ZIPs com senha **antes** de rotear:
```bash
python scripts/e0_unlock.py          # Desbloqueia PDFs + extrai ZIPs no inbox
python scripts/e0_unlock.py --dry-run # Apenas lista status, sem alterar
python scripts/e0_unlock.py --file X.zip  # Processa um ZIP específico
```
Para PDFs encriptados:
- Tentar desbloquear com senhas de `config/passwords.txt`
- Se desbloqueado: substituir o original pela versão sem senha e prosseguir roteamento
- Se nenhuma senha funcionar: registrar em `qa_log.md` e mover para `nao_identificados/`
- **NUNCA rotear um PDF encriptado para os diretórios de destino** — E2 falhará na extração

Para ZIPs protegidos (ex: CSVs do C6 Bank):
- Tentar descompactar com senhas de `config/passwords.txt`
- Se extraído: conteúdo fica no inbox/ para roteamento normal; `.zip` vai para `inbox_processed/`
- Se nenhuma senha funcionar: registrar em `qa_log.md`; ZIP permanece no inbox para investigação

**Validação pós-roteamento (recomendado):**
```bash
python scripts/e0_unlock.py --check-destinations
```
Varre `data/` e `members/` por PDFs encriptados que escaparam e desbloqueia in-place.

**Passo 9 — Executar:**
```bash
# Cópia de auditoria (apenas nome original, NÃO renomeado)
cp financas-familia/inbox/[nome_original] \
   financas-familia/inbox_processed/[DATA-DE-HOJE]/[nome_original]

# Mover para destino (inbox fica vazio após esta etapa)
mv financas-familia/inbox/[nome_original] \
   financas-familia/data/[destino]/[nome_final]
```

> **Atenção:** O comando é `mv` (mover), NÃO `cp`. Após E0, o inbox deve estar vazio. Se o arquivo permanecer no inbox após o move, investigar o motivo.

**Passo 10 — Arquivos não identificados:**
Se não conseguir identificar depois de analisar nome + conteúdo:
- Registrar em `logs/qa_log.md` como `"arquivo não identificado — aguardando instrução"`
- Mover para `financas-familia/inbox_processed/[DATA]/nao_identificados/[nome_original]`
- Informar o usuário

### 3.1.1 — Script automatizado: `e0_route.py`

O roteamento descrito nos Passos 1-10 acima é implementado pelo script `scripts/e0_route.py`, que pode ser executado de forma standalone ou integrado ao `e_reset.py`.

**Arquitetura de duas camadas:**
- **Camada 1 (determinística):** Classificação por regex sobre o nome do arquivo. Cobre ~95% dos casos usando as tabelas de instituição (Passo 2) e tipo de documento (Passo 3) compiladas em `INSTITUTION_PATTERNS` e `DOC_TYPE_PATTERNS`.
- **Camada 2 (LLM fallback):** Para arquivos que a Camada 1 não consegue classificar, o script extrai ~2000 caracteres do conteúdo e consulta Claude (via API Anthropic) para classificação. Se a confiança for >= 70%, o arquivo é roteado automaticamente. Caso contrário, vai para `nao_identificados/`.

**Uso standalone (CLI):**
```bash
python scripts/e0_route.py                  # Roteia tudo (regex + LLM)
python scripts/e0_route.py --dry-run        # Apenas mostra o que faria
python scripts/e0_route.py --no-llm         # Apenas regex, sem fallback LLM
python scripts/e0_route.py --file X.pdf     # Roteia um arquivo específico
```

### 3.1.2 — Classificação via web (upload no backend)

O upload web (`POST /api/documents/upload`) usa um classificador **content-first** que **não depende do nome do arquivo** — bancos exportam arquivos com nomes arbitrários e frequentemente incorretos.

**Arquitetura de três camadas (content-first):**

| Camada | Método | Threshold | Ação |
|--------|--------|-----------|------|
| 1 | Regex sobre **conteúdo extraído** (`content_classifier.py`) | confidence >= 0.8 | Aceita classificação |
| 2 | LLM fallback (`classify_by_llm`) via Anthropic API | confidence >= 0.7 | Aceita classificação |
| 3 | Fallback | confidence < 0.7 | `doc_type=other`, `needs_review=true` |

- **Camada 1** extrai texto (primeiras 3 páginas do PDF via pdfplumber, primeiras 20 linhas do XLSX/CSV) e aplica marcadores de conteúdo por banco (cabeçalhos, CNPJ, razão social) e tipo (FATURA + vencimento, EXTRATO + saldo anterior, CDB + rentabilidade, IRPF + declaração, etc.).
- **Camada 2** requer `anthropic` SDK (`pip install anthropic`) e `ANTHROPIC_API_KEY` no env do FastAPI. Custo: ~$0,005 por documento ambíguo.
- `_map_doc_type()` converte códigos de tipo específicos (ex: `faturaunique`, `extratocontabrl`, `cdbdetalhesdi1`) para a enum `DocumentType` via prefixo semântico.

**Dedupe no upload:**
- **Exato:** SHA-256 do conteúdo → partial unique index `(workspace_id, content_hash)`. Mesmo conteúdo = rejeitado.
- **Fuzzy:** se outro documento no mesmo workspace tem o mesmo `(doc_type, bank_code, period)` mas hash diferente → `possible_duplicate_of_id` aponta para o existente, `needs_review=true`. Não bloqueia — UI exibe para o usuário decidir.

**Scripts operacionais (em `backend/app/scripts/`):**
```bash
.venv/bin/python -m backend.app.scripts.reclassify_documents --dry-run     # Preview
.venv/bin/python -m backend.app.scripts.reclassify_documents --apply       # Reclassifica todos
.venv/bin/python -m backend.app.scripts.backfill_content_hash --apply      # Backfill SHA-256
.venv/bin/python -m backend.app.scripts.reset_documents --apply            # Wipe DB + storage
```

**Integração com e_reset.py:**
O `e_reset.py` executa `e0_route.route_all()` automaticamente como **Fase 0.5** (após unlock e auditoria, antes da limpeza de artefatos). Para pular: `--no-route`.

**Dependências:**
- `pdfplumber` — para extrair texto de PDFs (Camada 2)
- `xlrd` — para ler XLS do Itaú e Santander (Camada 2)
- `openpyxl` — para ler XLSX (Camada 2)
- `anthropic` — SDK Python para chamadas à API Claude (Camada 2, opcional)
- `ANTHROPIC_API_KEY` — variável de ambiente necessária para Camada 2

**Exit codes:**
- `0` — sucesso total
- `1` — erro fatal (inbox não encontrado, arquivo não encontrado)
- `2` — sucesso parcial (há arquivos não identificados)

---

### 3.2 — Determinação do ciclo necessário

Após rotear todos os arquivos, analisar quais tipos foram recebidos e determinar quais etapas executar:

| Arquivos recebidos | Tipo de ciclo | Etapas necessárias |
|---|---|---|
| Apenas extratos de conta corrente + faturas de cartão | **E2 rápido** | E2 (extração), E3 (reconciliação), E4 (unificação) |
| Apenas faturas de aluguel QuintoAndar | **E2-faturas + E3→E6** | E2-faturas, E3, E4, E5, E5.N, E6 (afeta receita de aluguel e fluxo de caixa) |
| Extratos novos para períodos já processados | **E3 + E4** | Detectar sobreposições, reconciliar apenas deltas |
| Declaração IRPF nova OU XLSX de imóveis | **E1.5 + E2 + E3 + E4 + E5 + E6** | Ciclo completo (baseline muda) |
| Novos currículos, holerites, documentos pessoais | **E1 + E1.5 + E2 + E3 + E4 + E5 + E6** | Ciclo completo (perfil do membro muda) |
| Novos documentos de veículos (XLSX) | **E1.5 + E3 + E4 + E5 + E6** | Patrimônio muda, re-gerar análises |
| Novos documentos pessoais (passaporte, RG, CPF) | **E1 + E3 + E4 + E5 + E6** | Enriquecimento do membro, relatório atualizado |
| Documentos US novos (SSN, drivers license, green card) | **E1 + E3 + E4 + E5 + E6** | Contexto fiscal US, potencial para T1 |
| Usuário solicita explicitamente ciclo completo | **Full cycle** | E1 + E1.5 + E2 + E3 + E4 + E5 + E5.N + E6 |

---

### 3.3 — Gerar logs após roteamento

Atualizar `logs/inbox_log.md` (append):

```markdown
## Ciclo [DATA] — [N] arquivos recebidos

### Resumo

| Métrica | Valor |
|---|---|
| Arquivos detectados | [N] |
| Roteados com sucesso | [N] |
| Duplicatas ignoradas | [N] |
| Não identificados | [N] |
| financial_statements/ | [N] |
| income_tax_br/ | [N] |
| real_estate/ | [N] |
| vehicles/ | [N] |
| members/ | [N] |

### Ciclo determinado

**Tipo:** [E2 rápido / E1.5 + E2 + E3 + E4 + E5 + E6 / Full cycle]
**Razão:** [Explicação breve: e.g., "Novo IRPF → baseline muda"]
```

---

## SEÇÃO 4 — PIPELINE STAGES

Cada etapa é descrita de forma agnóstica (não amarrada a Cowork/Chat). Qualquer ambiente pode executar qualquer etapa.

### STAGE E1 — Mapeamento de membros

**Objetivo:** Extrair informações de membros (perfil, experiência, renda) de currículos, holerites e documentos pessoais, consolidar em JSON unificado e gerar documento enriquecido em Markdown.

**Inputs:**
- `config/definitions.md` **(obrigatório)** — dados cadastrais: nomes (solteiro/casado), CPF, nascimento, papel na família, empresa PJ, animais de estimação
- `members/[membro]_curriculo-0_original.[docx/pdf]`
- `members/[membro]_holerite_[período]-0_original.pdf`
- `members/[membro]_rg-0_original.[pdf/jpg]`
- `members/[membro]_cpf-0_original.pdf`
- `members/[membro]_passaporte-0_original.pdf`
- `members/[membro]_visto-0_original.pdf`
- `members/[membro]_certidao_nascimento-0_original.pdf`
- `members/[membro]_certidao_casamento-0_original.pdf`
- Documentos US: `members/[membro]_ssn-0_original.pdf`, `members/[membro]_drivers_license-0_original.pdf`, `members/[membro]_green_card-0_original.pdf`

**Processing logic:**

0. **Carregar dados cadastrais:**
   - Ler `config/definitions.md`.
   - Extrair tabela MEMBROS DA FAMÍLIA (nome completo, CPF, nascimento, papel) e tabela NOMES (solteiro/casado).
   - Estes dados são a **fonte de verdade** para: idades exatas (calcular a partir de `nascimento`), `nome_atual`, resolução de ambiguidades de nome entre documentos, e garantia de que todos os membros listados estejam no output — mesmo os que não possuem documentos em `members/`.

1. **Para cada currículo (DOCX ou PDF):**
   - Ler o documento (se DOCX, usar DOCX reader; se PDF, usar PDF reader).
   - Extrair conforme **schema `curriculo-1a_extract.json`** (Seção 7.2): `tipo`, `membro`, `nome_completo` (como no documento), `nome_atual` (do definitions), `profissao_cargo`, `experiencias[]`, `formacao[]`, `certificacoes[]`, `habilidades[]`, `idiomas[]`.
   - **Idiomas:** se o currículo não listar seção de idiomas, inferir idioma nativo a partir do idioma do documento e do país de atuação. Ex: currículo em português + atuação no Brasil → `{"idioma": "Português", "nivel": "nativo", "fonte": "inferido"}`.
   - **Overlaps temporais:** experiências com datas sobrepostas são válidas e comuns (consultoria paralela a emprego CLT, docência acumulada com cargo hospitalar). NÃO ajustar datas para eliminar overlaps.
   - **Datas:** se o documento diz "junho de 2019", converter para `2019-06`. Se diz apenas "2019", usar `2019-01`. "Present" / "presente" / "atual" → `"presente"`.
   - Salvar em `members/[membro]_curriculo-1a_extract.json`.

2. **Para cada holerite:**
   - Ler o PDF.
   - Extrair conforme **schema `holerite-1a_extract.json`** (Seção 7.2): `tipo`, `membro`, `nome_no_documento` (preservar exatamente como está, pode ser nome de solteira), `periodo`, `empresa`, `estabelecimento`, `cargo`, `categoria`, `grade`, `matricula`, `data_admissao`, `salario_base_mensal`, `salario_bruto`, `proventos_adicionais[]`, `descontos[]`, `total_descontos`, `salario_liquido`, `data_credito`, `fgts{}`, `inss_base`, `dependentes_ir`, `observacoes`.
   - **Mapeamento nome→membro:** o `nome_no_documento` pode ser nome de solteiro(a) (ex: "Mariana Teixeira Ferreira"). Usar a tabela NOMES do `definitions.md` para mapear ao `id` correto do membro. Nunca tratar como divergência — é esperado.
   - **Proventos excepcionais:** se o holerite contiver férias, 13º ou adiantamento, registrar em `proventos_adicionais[]` E mencionar em `observacoes`.
   - Salvar em `members/[membro]_holerite_[período]-1a_extract.json` (um arquivo **por holerite**, com o período no nome).

3. **Para cada documento pessoal (RG, CPF, passaporte, visto, certidões, SSN, drivers license, green card):**
   - Ler o documento (PDF ou JPG usando OCR se necessário).
   - Extrair campos conforme tabela abaixo:

   | Tipo | Campos a extrair |
   |---|---|
   | RG | `numero`, `orgao_emissor`, `data_emissao`, `uf`, `nome_completo`, `filiacao` (nome dos pais), `naturalidade` |
   | CPF | `numero`, `nome_completo`, `data_nascimento` (se constar) |
   | Passaporte | `numero`, `pais_emissor`, `data_emissao`, `data_validade`, `nome_completo`, `nacionalidade` |
   | Visto | `tipo_visto`, `pais`, `numero`, `data_emissao`, `data_validade`, `status` |
   | Certidão nascimento | `nome`, `data_nascimento`, `local_nascimento`, `nome_pai`, `nome_mae`, `cartorio`, `livro_folha` |
   | Certidão casamento | `nomes_conjuges`, `data_casamento`, `regime_bens`, `cartorio` |
   | SSN | `numero` (últimos 4 se parcial), `nome_completo` |
   | Driver's license | `numero`, `estado`, `data_emissao`, `data_validade`, `classe` |
   | Green card | `numero`, `nome_completo`, `data_emissao`, `pais_nascimento`, `categoria` |

   - Todos os JSONs devem conter adicionalmente: `tipo` (código do documento), `membro` (id), `nome_no_documento` (exatamente como consta).
   - Salvar em `members/[membro]_[tipo]-1a_extract.json`.

4. **Consolidar (`members-1b_unified.json`):**
   - **a.** Iniciar com a lista de membros de `config/definitions.md` como base — garante que todos apareçam, mesmo os que não possuem documentos em `members/`.
   - **b.** Para cada membro, mesclar dados de todos os `-1a_extract.json` correspondentes.
   - **c.** Seguir o **schema `members-1b_unified.json`** (Seção 7.2).
   - **d.** Regras de resolução de conflito:

   | Campo | Regra |
   |---|---|
   | Nome | `nome_atual` = do `definitions.md`. Variantes encontradas nos documentos → `nomes_alternativos[]`. |
   | Salário | Holerite mais recente prevalece. Se há apenas currículo: `salario` = `null` com `nota` explicativa. |
   | Cargo | Currículo para descrição narrativa, holerite para cargo formal (código funcional). `cargo_atual` = o do currículo (mais descritivo). |
   | Empresa | Holerite prevalece para empregador atual se CLT. Currículo prevalece se PJ. |
   | Data admissão | Holerite prevalece (dado formal). |
   | Formação | Unir todas as fontes sem duplicar. Ordenar por data descendente. |
   | Overlaps de datas | Manter ambas experiências — overlaps são válidos (trabalho paralelo, docência + CLT). |
   | Idiomas | Unir de todas as fontes. Se nenhuma fonte listar, inferir nativo do idioma do currículo. |
   | Membro sem documentos | Criar entrada com dados do `definitions.md`. Campos sem fonte = `null`. `documentos_disponiveis: []`. |
   | Múltiplos holerites | Usar o mais recente para `salario`. Se houve variação significativa entre períodos, mencionar em `nota`. |

5. **Gerar documento enriquecido (`members-1c_enriched.md`):**
   - Seguir o **template obrigatório** abaixo. Ordem dos membros: Titular → Cônjuge → Filhos.
   - Template por membro:

   ```markdown
   ## [Nome Atual Completo] ([Nomes Alternativos se houver])

   **Perfil:** [Nacionalidade], [idade] anos (nasc. DD/MM/YYYY). [Idiomas].

   **Histórico profissional:** [Resumo 2-3 frases: anos de carreira, áreas, progressão].

   **Cargo atual:** [Cargo] na [Empresa] ([tipo vínculo]). [Desde MM/YYYY].

   **Salário atual ([fonte], [período]):**
   - Base mensal: R$ X.XXX,XX
   - Bruto no período: R$ X.XXX,XX [nota se férias, 13º, etc.]
   - Descontos principais: INSS R$ X.XXX,XX | IRRF R$ X.XXX,XX
   - [Outras linhas relevantes: FGTS, benefícios]

   **Documentação disponível:** [lista de documentos processados].

   **Status fiscal:** [BR / US / BR+US]. [Detalhes regime se relevante].
   ```

   - **Idade:** calcular a partir de `data_nascimento` do `definitions.md`, NUNCA estimar a partir de formatura.
   - **Membros sem documentos (ex: Theo):** bloco mínimo — perfil básico do `definitions.md` + nota "Sem documentos processados neste ciclo".
   - **Salário PJ sem holerite:** escrever "PJ — valor a confirmar via extratos bancários de [instituição]".

**Outputs:**
- `members/[membro]_curriculo-1a_extract.json` (um por currículo)
- `members/[membro]_holerite_[período]-1a_extract.json` (um por holerite, com período no nome)
- `members/[membro]_[tipo_documento]-1a_extract.json` (um por documento pessoal)
- `members/members-1b_unified.json`
- `members/members-1c_enriched.md`

**Validation:**

V1 — **Schema compliance:**
- Cada `-1a_extract.json` deve conter **todas** as chaves obrigatórias do schema correspondente (Seção 7.2).
- Nenhum valor obrigatório pode ser `null` ou string vazia (exceto quando o schema permite explicitamente).

V2 — **Valores numéricos (holerites):**
- `salario_bruto > 0`
- `salario_liquido > 0`
- `salario_liquido ≤ salario_bruto`
- `total_descontos ≈ soma(descontos[].valor)` (tolerância: ±R$0,10 por arredondamento)

V3 — **Consistência 1a → 1b:**
- Todo `membro` presente em algum `-1a_extract.json` DEVE ter entrada correspondente no `1b_unified`.
- Todo membro do `definitions.md` DEVE ter entrada no `1b_unified` (mesmo sem documentos).
- `membros.length ≥ número_de_membros_em_definitions`

V4 — **Consistência 1b → 1c:**
- Todo membro do `1b_unified` DEVE ter seção no `1c_enriched.md`.
- Idade no `1c_enriched` deve bater com `data_nascimento` do `definitions.md`.

V5 — **Documentos corrompidos ou vazios:**
- Se um PDF/JPG não puder ser lido (corrompido, protegido por senha, escaneado sem OCR legível): registrar em `qa_log.md`:
  ```
  [YYYY-MM-DD] E1 | WARN | Arquivo [nome] não pôde ser processado: [motivo]. Membro [id] terá dados parciais.
  ```
- NÃO interromper a execução. Continuar com os documentos disponíveis.

---

### STAGE E1.5 — Baseline patrimonial

**Objetivo:** Extrair snapshot de patrimônio e renda de declarações IRPF, informes QuintoAndar e XLSX de imóveis/veículos.

> **Nota sobre diretório de outputs:** Os outputs de E1.5 são salvos em `processed/E2_extracts/` (não em diretório dedicado E1.5) por convenção, pois servem como inputs diretos para E2 e E3. O prefixo do sufixo identifica a origem: `-1.5_consolidated` para o baseline, `-2_extract` para os extratos individuais de IRPF/imóveis/veículos.

**Inputs:**
- `data/income_tax_br/receitafederal_irpfdeclaracao_[ano]-0_original.pdf` (múltiplos anos)
- `data/income_tax_br/receitafederal_irpfrecibo_[ano]-0_original.pdf`
- `data/income_tax_br/quintoandar_informerendimentosaluguel_[ano]-0_original.pdf`
- `data/real_estate/dados_imoveis-0_original.xlsx`
- `data/vehicles/dados_veiculos-0_original.xlsx` (se presente)

**Processing logic:**

1. **Para cada declaração IRPF:**
   - Ler o PDF
   - Extrair **TODOS os bens e direitos** com valores (imóveis, investimentos, contas bancárias, empresas, criptos, joias, arte, veículos) — com datas de aquisição quando disponíveis
   - Extrair **TODAS as fontes de renda**: PJ, CLT, aluguéis, rendimentos financeiros, outros
   - Extrair **dívidas**: financiamentos, empréstimos, outros ônus
   - Extrair **pagamentos dedutíveis**: saúde, educação, previdência
   - Guardar valores em 31/12 do ano-base e do ano anterior para calcular variação
   - Salvar em `processed/E2_extracts/receitafederal_irpfdeclaracao_[ano]-2_extract.json`

2. **Para cada recibo IRPF:**
   - Ler o PDF
   - Extrair: imposto total, data de entrega, situação (aceita/pendente)
   - Salvar em `processed/E2_extracts/receitafederal_irpfrecibo_[ano]-2_extract.json`

3. **Para cada informe QuintoAndar:**
   - Ler o PDF
   - Extrair: ano-base, renda bruta de aluguéis por propriedade, descontos, líquido
   - Salvar em `processed/E2_extracts/quintoandar_informerendimentosaluguel_[ano]-2_extract.json`

4. **Para o XLSX de imóveis:**
   - Ler as abas do XLSX
   - Extrair para cada imóvel: endereço, data de compra, valor de compra, vendedor, financiamento (banco, juros, prazo), situação atual (aluguel, próprio)
   - Salvar em `processed/E2_extracts/dados_imoveis-2_extract.json`

5. **Para o XLSX de veículos (se presente):**
   - Ler as abas do XLSX
   - Extrair para cada veículo: marca, modelo, ano, placa, data de aquisição, valor de aquisição, situação (próprio, financiado)
   - Salvar em `processed/E2_extracts/dados_veiculos-2_extract.json`

6. **Consolidar baseline patrimonial:**
   - Combinar todos os extratos IRPF em `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`
   - Cruzar com dados do XLSX de imóveis para enriquecer com datas de compra e financiamentos
   - Cruzar com dados do XLSX de veículos (se houver)
   - Destacar **divergências**: se um imóvel está no IRPF mas não no XLSX (ou vice-versa), registrar
   - Salvar divergências em `logs/divergences.md`

**Schema do baseline_patrimonial-1.5_consolidated.json:**

O baseline DEVE seguir este formato exato (validado por `config/schemas/baseline_patrimonial.schema.json`):

```json
{
  "pipeline_stage": "E1.5_Baseline_Patrimonial",
  "data_processamento": "2026-04-09",
  "membros": ["david", "mariana"],
  "anos_base": [2023, 2024],
  "declarations": [
    {
      "membro": "david",
      "ano_base": 2024,
      "bens_direitos": [
        {
          "grupo": "G01",
          "codigo": "01",
          "descricao": "Apartamento Rua X",
          "situacao_anterior": 450000.00,
          "situacao_atual": 450000.00
        }
      ],
      "dividas": [],
      "rendimentos": {
        "tributaveis": [],
        "isentos": []
      }
    }
  ],
  "imoveis_xlsx": [],
  "veiculos_xlsx": [],
  "divergencias": []
}
```

Campos obrigatórios: `pipeline_stage`, `data_processamento`, `declarations` (array de objetos com `membro`, `ano_base`, `bens_direitos`). O campo `membros` aceita lista de strings ou objetos com `nome`. Grupos IRPF para E5: G01=imóveis, G02=veículos, G03/G04/G07=investimentos, G06=contas bancárias.

**Outputs:**
- `processed/E2_extracts/receitafederal_irpfdeclaracao_[ano]-2_extract.json` (múltiplos)
- `processed/E2_extracts/receitafederal_irpfrecibo_[ano]-2_extract.json` (múltiplos)
- `processed/E2_extracts/quintoandar_informerendimentosaluguel_[ano]-2_extract.json` (múltiplos)
- `processed/E2_extracts/dados_imoveis-2_extract.json`
- `processed/E2_extracts/dados_veiculos-2_extract.json` (se houver)
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`
- `logs/divergences.md` (se houver divergências)

7. **Consolidar chaves para E5 (determinístico):**
   - Executar: `python scripts/e15_consolidate.py`
   - Este script enriquece o baseline com chaves consolidadas (`imoveis_consolidados`, `veiculos_consolidados`, `investimentos_consolidados`, `dividas`, `patrimonio_por_ano`) derivadas das `declarations` e `imoveis_xlsx`/`veiculos_xlsx`
   - Faz cross-match IRPF ↔ XLSX por keywords, número de apartamento e data de compra (±7 dias)
   - Imóveis XLSX sem match IRPF são adicionados com flag `fonte: xlsx_only`
   - DEVE ser executado após a etapa LLM e antes de E3/E5

**Validation:**
- Baseline consolidado deve conter: membros identificados, ano-base da declaração, bens totais, renda total
- Baseline DEVE passar validação do JSON Schema em `config/schemas/baseline_patrimonial.schema.json`
- Baseline DEVE conter chaves consolidadas (executar `python scripts/e15_consolidate.py` se ausentes)
- Todos os imóveis devem ter cruzamento IRPF <→ XLSX
- Divergências devem ser documentadas e resolvidas antes de E2

---

### STAGE E2 — Extração de extratos financeiros

**Objetivo:** Extrair transações, saldos e posições de investimento de extratos de conta, faturas e posições.

**Inputs:**
- `data/financial_statements/[banco]_extratoconta_[período]-0_original.[pdf/jpg]`
- `data/financial_statements/[banco]_extratocontapj_[período]-0_original.pdf`
- `data/financial_statements/[banco]_extratocontaglobal[moeda]_[período]-0_original.pdf`
- `data/financial_statements/[banco]_extratopoupanca_[período]-0_original.pdf`
- `data/financial_statements/[banco]_faturacarbon_[período]-0_original.pdf`
- `data/financial_statements/[banco]_faturaunique_[período]-0_original.pdf`
- `data/financial_statements/[banco]_faturapaoacucar_[período]-0_original.pdf`
- `data/financial_statements/[banco]_investimentosposicao_[período]-0_original.pdf`
- `data/financial_statements/[banco]_carteirarendafixa_[período]-0_original.pdf`
- `data/financial_statements/[banco]_cdbdetalhes_[período]-0_original.pdf`
- `data/financial_statements/[banco]_cdbresumo_[período]-0_original.pdf`
- `data/financial_statements/quintoandar_faturaaluguel_[propriedade]_[período]-0_original.pdf`
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json` (referência)

**Processing logic:**

> **Arquitetura modular (v5.10):** Todos os formatos determinísticos (extratos, faturas, CDBs)
> são processados por um CLI unificado `e2_extract.py`, com parsers organizados por banco em
> `scripts/e2/banks/`. Investimentos, IRPF e informes de rendimentos continuam via LLM.
> Novo banco = novo arquivo em `scripts/e2/banks/<banco>.py`.
>
> **Scripts legados:** `e2_extract_extratos.py` e `e2_extract_faturas.py` foram removidos.
> Use exclusivamente `e2_extract.py` para todos os processamentos.

#### E2 determinístico (unificado — v5.10)

**Execução:**
```bash
python scripts/e2_extract.py                  # Processa tudo (extratos + faturas + CDBs)
python scripts/e2_extract.py --extratos-only  # Apenas extratos bancários
python scripts/e2_extract.py --faturas-only   # Apenas faturas de cartão
```
O script é 100% determinístico (zero LLM) para bancos conhecidos. Usa pdfplumber para extração
de texto e tabelas de PDFs, e parser CSV nativo para formatos exportados do internet banking.
Mesmos inputs = mesmos outputs.

**Estrutura modular:**
```
scripts/e2/
  common.py       — utilities compartilhadas (parse_brl, safe_date, config, etc.)
  registry.py     — auto-discovery de parsers por banco, routing por filename
  validation.py   — validação pós-parse (extratos e faturas)
  banks/
    c6bank.py     — extrato CSV/PDF, conta PJ, global USD/EUR, fatura Carbon CSV/PDF
    itau.py       — extrato XLS/PDF, Personnalité, CDB HTML-XLS, fatura PdA CSV/PDF
    santander.py  — extrato XLS/PDF, CDB XLSX, fatura Unique CSV/PDF
    bradesco.py   — extrato conta, poupança
    btg.py        — extrato conta
    rico.py       — extrato conta
    wise.py       — extrato conta USD/BRL
    bankofamerica.py — extrato conta (formato US)
    picpay.py     — extrato conta
    quintoandar.py — fatura aluguel
```

**Opções CLI:**
- `--dry-run` — mostra o que seria processado sem gravar arquivos
- `--file <caminho>` — processa apenas um arquivo específico (PDF, CSV, XLS, XLSX)
- `--output-dir <caminho>` — diretório de saída (padrão: `processed/E2_extracts/`)
- `--quiet` — suprime output de debug
- `--extratos-only` — apenas extratos bancários
- `--faturas-only` — apenas faturas de cartão

**Parsers de extratos disponíveis:**

| Banco | Tipo | Método | Obs |
|-------|------|--------|-----|
| C6 Bank | `extratoconta` | CSV | ZIP-protected, BOM UTF-8, 7 colunas |
| C6 Bank | `extratocontapj` | CSV | Mesmo formato de C6 Conta CSV |
| C6 Bank | `extratoconta` | TABLE | Multi-página, ~670 rows/tabela (PDF) |
| C6 Bank | `extratocontapj` | TABLE | Mesmo formato de C6 Conta (PDF) |
| C6 Bank | `extratocontaglobalusd` | TABLE | Valor com prefixo moeda (US$) |
| C6 Bank | `extratocontaglobaleur` | TABLE | Valor com prefixo moeda (€) |
| Itaú | `extratoconta` | TABLE | Muitas mini-tabelas (1 row cada) |
| Itaú | `extratocontapersonnalite` | TABLE | Mesmo formato de Itaú Conta |
| PicPay | `extratoconta` | TABLE | Tabelas perfeitas 5 colunas |
| Bradesco | `extratoconta` | REGEX | Multi-linha, 14+ páginas |
| Bradesco | `extratopoupanca` | REGEX | Screenshot do app, texto extraível |
| Santander | `extratoconta` | REGEX | Linhas completas com docto 6 dígitos |
| BTG Pactual | `extratoconta` | REGEX | Saldo Inicial/Final explícitos |
| Rico | `extratoconta` | REGEX | Dividendos/JCP, data Liq + Mov |
| Wise | `extratocontausd` | REGEX | Transação+data em linhas alternadas |
| Wise | `extratocontabrl` | REGEX | Mesmo formato Wise USD |
| Bank of America | `extratoconta` | REGEX | Formato US (MM/DD/YY), USD |

**Suporte a CSV (C6 Bank):**
O C6 Bank permite exportar extratos em CSV via internet banking. Os arquivos são entregues em ZIP
protegido por senha (senhas em `config/passwords.txt`). Após descompactação e renomeação no E0,
o CSV segue o mesmo pipeline dos PDFs. O formato CSV tem vantagens sobre PDF: parsing mais preciso
(sem ambiguidade de tabelas OCR), valores decimais exatos, e menor tempo de processamento.

Estrutura do CSV C6:
- Header: nome do banco, agência/conta, data de geração, período
- Colunas: Data Lançamento, Data Contábil, Título, Descrição, Entrada(R$), Saída(R$), Saldo do Dia(R$)
- Encoding: UTF-8 com BOM
- Separador decimal: ponto (formato US)
- Naming: `c6bank_extratoconta[pj]_YYYYMM_YYYYMM-0_original.csv`

**Validation gate integrada:**
O script inclui validação automática pós-extração:
- Rejeita (ERROR) JSONs com 0 transações quando o arquivo fonte tem conteúdo significativo
  (>500 chars/bytes para PDF/CSV, exceto contas explicitamente sem movimentação)
- Detecta transações com valor None
- Detecta possíveis duplicatas intra-arquivo
- Registra notas em cada JSON para auditoria

**Lógica de roteamento:**
1. Identifica banco e tipo pelo nome do arquivo (padrão: `[banco]_extrato*_[período]-0_original.{pdf,csv}`)
2. CSV tem prioridade sobre PDF quando ambos existem para o mesmo banco/tipo
3. Despacha para o parser determinístico correspondente (CSV, TABLE ou REGEX)
4. Se banco desconhecido → gera JSON com `"requires_llm_fallback": true`

#### E2-extratos-llm (LLM fallback — apenas bancos sem parser)

Para bancos sem parser determinístico ou arquivos marcados com `requires_llm_fallback`:

1. **Para cada extrato de conta (CC, PJ, Global, Poupança):**
   - Ler o PDF (se JPG, usar OCR)
   - Extrair: saldo inicial, saldo final, número da conta, período coberto, tipo de moeda
   - Extrair TODAS as transações: data, descrição, débito/crédito, saldo após
   - **NÃO categorizar transações** — apenas extrair fidedignamente
   - Salvar em `processed/E2_extracts/[banco]_extrato*-2_extract.json`

2. **Para cada posição de investimento:**
   - Ler o PDF
   - Extrair: data da posição, saldo em reais (ou moeda), composição (ações, fundos, títulos, etc.), rentabilidade acumulada, valores com data de aquisição
   - **Para ações (product_type = "Acao"):** extrair obrigatoriamente `quantity`, `unit_price`, `issuer`. Se `applied_value` não estiver disponível (comum em posições Rico), marcar como `null` e adicionar `pm_note` explicando a ausência.
   - **Reconciliação de PM (preço médio):** Cruzar quantidade com IRPF do ano-base anterior. Se quantidade atual ≠ quantidade IRPF, PM não pode ser estimado (requer notas de corretagem B3/CEI). Se quantidade for idêntica, PM pode ser estimado como `valor_irpf / quantidade`.
   - Salvar em `processed/E2_extracts/[banco]_investimentosposicao_[período]-2_extract.json`

3. **Para cada carteira de renda fixa / CDB:**
   - Ler o PDF
   - Extrair: tipo de produto, valor aplicado, data de aplicação, taxa, vencimento, saldo atual
   - Salvar em `processed/E2_extracts/[banco]_cdb*-2_extract.json`

#### E2-faturas (determinístico — incluído em e2_extract.py)

> **Nota (v5.10+):** Faturas agora são processadas pelo CLI unificado `e2_extract.py`.
> Scripts legados (`e2_extract_faturas.py`, `e2_extract_extratos.py`) foram removidos.
>
> ```bash
> python scripts/e2_extract.py --faturas-only
> ```

**Parsers de faturas disponíveis:**

| Banco | Tipo | Função | Obs |
|-------|------|--------|-----|
| C6 Bank | `faturacarbon` | `parse_c6_carbon_csv()` | CSV: separador `;`, 9 colunas, multi-cartão, forex USD |
| C6 Bank | `faturacarbon` | `parse_c6_carbon()` | PDF: multi-página, multi-cartão (David/Sonia) |
| Santander | `faturaunique` | `parse_santander_unique()` | Multi-titular (David/Rubens/Sonia), forex USD |
| Itaú | `faturapaoacucar` | `parse_itau_paoacucar()` | Layout duas colunas (pdfplumber merge), parceladas futuras |
| QuintoAndar | `faturaaluguel` | `parse_quintoandar()` | Aluguel com itens discriminados |

**Suporte a CSV (C6 Faturas):**
O C6 Bank permite exportar faturas em CSV via internet banking. Os arquivos são entregues em ZIP
protegido por senha. O formato CSV tem vantagens sobre PDF: parsing mais preciso,
categoria de compra já classificada pelo banco, e identificação explícita de cartão/titular.

Estrutura do CSV de fatura C6:
- Separador: ponto-e-vírgula (;)
- Colunas: Data de Compra, Nome no Cartão, Final do Cartão, Categoria, Descrição, Parcela, Valor (em US$), Cotação (em R$), Valor (em R$)
- Compras internacionais: US$ e cotação preenchidos
- Pagamentos: valor negativo em R$
- Naming: `c6bank_faturacarbon_YYYYMM-0_original.csv`

**Lógica de roteamento:**
1. Identifica banco e tipo pelo nome do arquivo (padrão: `[banco]_fatura*_[período]-0_original.{pdf,csv}`)
2. CSV tem prioridade sobre PDF quando ambos existem para o mesmo banco/tipo
3. Despacha para o parser determinístico correspondente
4. Se banco desconhecido → gera JSON com `"requires_llm_fallback": true` e preview do texto extraído para processamento manual/LLM posterior

**Para cada fatura de cartão (parsers determinísticos):**
   - Extrair: saldo anterior, compras, pagamentos, saldo atual, data de vencimento
   - Extrair TODAS as transações: data, descrição, valor, cartão (identificação do titular)
   - Para transações em moeda estrangeira: extrair `forex.moeda_original` e `forex.valor_original`
   - Para IOF: marcar `tipo_lancamento: "iof"`
   - Para parceladas futuras (Itaú): extrair em `compras_parceladas_futuras[]`
   - **NÃO categorizar** — manter como no documento
   - Salvar em `processed/E2_extracts/[banco]_fatura*-2_extract.json`

**Para cada fatura de aluguel (QuintoAndar):**
   - Extrair: propriedade, período, itens discriminados (aluguel, condomínio, IPTU, taxa adm, etc.)
   - Salvar em `processed/E2_extracts/quintoandar_faturaaluguel_*-2_extract.json`

#### Validação cruzada (ambos)

6. **Validação cruzada com baseline:**
   - Para cada saldo final de conta, comparar com valores declarados no IRPF (em 31/12/ano-base)
   - Se houver discrepância > 5%, registrar em `logs/divergences.md`
   - Se houver conta não declarada, registrar como potencial descoberta

**Outputs:**
- `processed/E2_extracts/[arquivo original]-2_extract.json` para cada arquivo processado
- `logs/divergences.md` (atualizado com divergências de saldos)

**Validation:**
- Cada extrato deve ter chaves obrigatórias (vide schema abaixo)
- Transações devem ter data e valor
- Nenhuma categorização (apenas extração)
- Arquivos corrompidos/ilegíveis devem ser registrados em `qa_log.md`

---

### STAGE E3 — Reconciliação por conta

**Objetivo:** Consolidar múltiplos extratos da mesma conta, remover duplicatas de períodos sobrepostos, verificar completude.

**Execução determinística:**
```bash
python scripts/e3_reconcile.py
```
O script é 100% determinístico (zero LLM). Mesmos inputs = mesmos outputs. Tempo de execução: ~2s.

**Inputs:**
- TODOS os `processed/E2_extracts/*-2_extract.json` (exceto `-0_original`, baseline, dados_imoveis e tipos não-transacionais)
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json` (para validação cruzada)

**Regras de filtragem de inputs:**
- Arquivos `-0_original-2_extract.json` são **sempre ignorados** (backups de versões anteriores à correção LLM)
- Tipos ignorados: `investimentosposicao`, `carteirarendafixa`, `cdbdetalhes`, `cdbresumo`, `faturaaluguel`, `informerendimentos`, `irpf`
- Faturas aceitas: `faturacarbon`, `faturaunique`, `faturapaoacucar` (demais tipos `fatura*` são ignorados)
- Tipos de conta reconhecidos: `extratoconta`, `extratocontapj`, `extratocontapersonnalite`, `extratopoupanca`, `extratocontaglobal`, `extratocontaglobalusd`, `extratocontaglobaleur`

**Processing logic:**

0. **Cleanup do diretório E3_reconciled/:**
   - Antes de processar, remove (ou tombstona) todos os `.json` existentes no diretório de output
   - Garante que arquivos fantasma de execuções anteriores (LLM ou script) não poluam o resultado

1. **Para cada conta identificada (e.g., "Itaú Personnalité PF", "C6 Bank USD"):**
   - Agrupar todos os extratos dessa conta em ordem cronológica
   - Chave de agrupamento: `(banco, tipo, moeda)` para contas correntes; `(banco, tipo)` para faturas
   - **Normalização de tipo:** Antes de agrupar, o tipo é normalizado via `account_type_equivalences` de `config/family_members.json`. Atualmente: `extratocontapersonnalite` → `extratoconta`, pois ambos são extratos da mesma conta Itaú exportados por portais diferentes (Personnalité vs. regular). Sem essa normalização, transações como FINANC IMOBILIARIO apareciam duplicadas.
   - Para faturas sem campo `periodo`: sintetizar a partir de `data_vencimento` (1º dia do mês anterior até vencimento), ajustando `periodo.inicio` para a data da transação mais antiga se esta for anterior ao valor sintetizado
   - Faturas com `data_vencimento` vazio e sem transações: skip com log explícito. Com transações: derivar periodo das datas reais
   - Para períodos sobrepostos (detectar por datas):
     - Buscar duplicatas por regra: **data + valor + descrição** = mesma transação
     - **Deduplicação apenas entre arquivos diferentes** — transações idênticas dentro do mesmo arquivo são mantidas (representam compras legítimas distintas, ex: 3 compras na Amazon no mesmo dia)
     - Ao encontrar duplicata cross-file, manter as transações do arquivo com mais ocorrências daquela assinatura
   - Detectar gaps temporais entre extratos consecutivos (> 2 dias) e registrar em `logs/qa_log.md`
   - Compilar lista de TODAS as transações de forma consolidada

2. **Validação de saldos:**
   - Pegar saldo inicial do extrato mais antigo (se `None`, usar 0 com warning)
   - Comparar saldo final de cada extrato com saldo inicial do próximo
   - Se houver diferença > R$0.01, registrar discrepância em `logs/reconciliation.md`

3. **Validação contra baseline:**
   - Se há IRPF para 31/12 de ano anterior, comparar saldo nessa data com baseline
   - Se há IRPF para 31/12 de ano-base, comparar saldo em 31/12 com baseline
   - Registrar variações esperadas vs. inesperadas em `logs/reconciliation.md`

4. **Gerar arquivo consolidado por conta:**
   - Formato do nome: `processed/E3_reconciled/[banco]_[tipo_conta]_[moeda]_[YYYYMM]_[YYYYMM]-3_reconciled.json` (contas correntes) ou `[banco]_[tipo_conta]_[YYYYMM]_[YYYYMM]-3_reconciled.json` (faturas, sem moeda)
   - Conteúdo: todas as transações deduplicated, saldos validados, datas de cobertura completas, lista de fontes

**Outputs:**
- `processed/E3_reconciled/[banco]_[tipo]_[YYYYMM]_[YYYYMM]-3_reconciled.json` para cada conta
- `logs/reconciliation.md` com resumo de cada conta, deduplicações, warnings de saldo e baseline
- `logs/qa_log.md` com gaps temporais detectados (append)

**Validation:**
- Cada account reconciliado deve ter saldo inicial, transações deduplicated, saldo final
- Nenhuma transação de arquivos diferentes deve aparecer mais de uma vez (intra-arquivo preservadas)
- Gaps temporais devem ser documentados em `qa_log.md`
- Saldos devem bater (ou divergência documentada)
- Saldos `None` convertidos para 0 com warning no log

---

### STAGE E4 — Enriquecimento e unificação

**Objetivo:** Categorizar transações, consolidar por tipo (receita, despesa, investimento, patrimônio), enriquecer com contexto.

**Execução determinística:**
```bash
python scripts/e4_categorize.py
```
O script é 100% determinístico (zero LLM). Keywords hardcoded do `definitions.md`. Normalização com remoção de acentos (NFD). Detecção conservadora de transferências internas (investimentos, pagamentos de fatura, PIX entre contas familiares). Tempo de execução: ~2s.

**Inputs:**
- `processed/E3_reconciled/*-3_reconciled.json` (todos)
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`
- `processed/E2_extracts/dados_imoveis-2_extract.json`
- `processed/E2_extracts/dados_veiculos-2_extract.json` (se houver)
- `config/definitions.md` (categorização e regras)
- `config/source_hierarchy.md` (prioridade de fontes)

**Processing logic:**

1. **Para cada transação reconciliada:**
   - Aplicar regras de categorização (usar `definitions.md`, seção "REGRAS DE CATEGORIZAÇÃO POR KEYWORDS")
   - Para despesas: usar match parcial case-insensitive das keywords listadas por categoria. Se mais de uma regra casar, usar a mais específica (match mais longo). Keywords cobrem ~95% das transações de cartão de crédito.
   - Atribuir categoria: receita, despesa, investimento, transferência, pagamento de dívida, etc.
   - Registrar subcategoria (e.g., "despesa → saúde", "receita → PJ")
   - Se não conseguir categorizar via keywords NEM por contexto, deixar como "não identificado" e registrar em `qa_log.md`
   - **META:** `nao_identificado` deve representar <10% do total de transações de despesa. Se ultrapassar, revisar e expandir as regras de keywords em `definitions.md`.

2. **Consolidar por categoria:**
   - Gerar `processed/E4_unified/receitas-4_unified.json`: agrupado por fonte (PJ, CLT, aluguéis, rendimentos financeiros, etc.)
   - Gerar `processed/E4_unified/despesas-4_unified.json`: agrupado por subcategoria (alimentação, saúde, educação, seguros, etc.)
   - Gerar `processed/E4_unified/investimentos-4_unified.json`: consolidar posições de investimento por tipo
   - Gerar `processed/E4_unified/pontos_milhas-4_unified.json`: se houver cartões com acúmulo de pontos

2b. **Gerar breakdown mensal por origem (CRÍTICO para gráfico `receita_despesa_mensal`):**
   - Gerar `processed/E4_unified/fluxo_mensal_detalhado-4_unified.json`
   - **Receitas:** Para cada transação de receita categorizada no item 1, identificar a **origem nomeada** usando as REGRAS DE CATEGORIZAÇÃO DE RECEITAS em `definitions.md` e agregar valor por mês (YYYY-MM).
    - Origens PJ: usar subcategoria conforme `pj_source_mapping` em `config/categorization.json` (ex: "Arvo (David - PJ)", etc.). Conta esperada: C6 PJ.
    - Origem CLT: conforme `clt_source_mapping` em `config/categorization.json` (ex: "Einstein (Mariana - CLT)"). Conta esperada: Poupança Bradesco.
     - Aluguéis: "Aluguéis" (QuintoAndar via GRPQA + diretos).
     - Rendimentos: "Rendimentos Financeiros" (rendimentos de poupança, CDB, fundos, dividendos).
     - Outras: agrupar como "Outras Receitas".
   - **Despesas:** Para cada transação de despesa categorizada no item 1, agregar valor por mês (YYYY-MM) e por **categoria de despesa** (usando as categorias do `definitions.md`: alimentação, saúde, moradia, educação, transporte, etc.).
   - **Estrutura do JSON:**
     ```json
     {
       "periodo": "YYYY-MM a YYYY-MM",
       "meses_ordenados": ["YYYY-MM", "YYYY-MM", "..."],
       "receitas": {
         "origens": ["[origens PJ conforme pj_source_mapping do categorization.json]", "[CLT conforme clt_source_mapping]", "Aluguéis", "Rendimentos Financeiros", "Outras Receitas"],
         "por_mes": {
           "YYYY-MM": {
             "[Origem PJ 1]": 0.00,
             "[Origem CLT]": 0.00,
             "Aluguéis": 0.00,
             "Rendimentos Financeiros": 0.00,
             "Outras Receitas": 0.00,
             "_total": 0.00
           }
         }
       },
       "despesas": {
         "categorias": ["[categorias conforme definitions.md]"],
         "por_mes": {
           "YYYY-MM": {
             "[categoria]": 0.00,
             "_total": 0.00
           }
         }
       }
     }
     ```
   > **Nota:** Os nomes das origens de receita PJ e CLT vêm de `pj_source_mapping` e `clt_source_mapping` em `config/categorization.json`. As categorias de despesa vêm de `config/definitions.md`. Todos os valores são calculados dinamicamente a partir dos dados do período.
   - **Validação:** Para cada mês, `receitas.por_mes[mes]._total` deve ser consistente com `receitas-4_unified.json` e `despesas.por_mes[mes]._total` com `despesas-4_unified.json`.
   - **⚠️ IMPORTANTE:** Este JSON é a fonte de verdade para o gráfico `receita_despesa_mensal`. Sem ele, o gráfico usa médias planas (incorreto).

3. **Consolidar patrimônio:**
   - Gerar `processed/E4_unified/patrimonio-4_unified.json` consolidando:
     - Imóveis: usar `dados_imoveis-2_extract.json` + IRPF (valor declarado em 31/12)
     - Veículos: usar `dados_veiculos-2_extract.json` se houver
     - Investimentos: consolidar posições de investimento
     - Contas bancárias: saldos em 31/12 (ou data mais recente)
     - Criptos, joias, arte: extratos do IRPF (se houver)
     - Empresas/cotas: extratos do IRPF
     - Dívidas: consolidar do IRPF
   - Total patrimonial = bens totais - dívidas

4. **Consolidar seguros:**
   - Gerar `processed/E4_unified/seguros-4_unified.json` consolidando:
     - Seguros de vida, imóvel, auto, saúde
     - Extraídos de: faturas, holerites, declarações IRPF
     - Campos: tipo de seguro, prêmio mensal/anual, cobertura, data de vencimento, situação

5. **Enriquecimento com contexto:**
   - Adicionar nomes dos membros (de E1)
   - Adicionar contexto de períodos (de baseline)
   - Adicionar anotações de divergências resolvidas

6. **Gerar qa_log para transações não identificadas:**
   - Lista de transações que não foram categorizadas com motivo
   - Salvar em `logs/qa_log.md` para revisão manual

**Outputs:**
- `processed/E4_unified/receitas-4_unified.json`
- `processed/E4_unified/despesas-4_unified.json`
- `processed/E4_unified/investimentos-4_unified.json` ← **NOVO v5.7: consolidado de posições de investimento do E2 (antes era placeholder vazio)**
- `processed/E4_unified/patrimonio-4_unified.json`
- `processed/E4_unified/seguros-4_unified.json`
- `processed/E4_unified/pontos_milhas-4_unified.json`
- `processed/E4_unified/fluxo_mensal_detalhado-4_unified.json` ← **NOVO v4.1: breakdown mensal por origem (receitas) e por categoria (despesas)**
- `logs/qa_log.md` (transações não identificadas)
- `config/definitions.md` (atualizado com novas regras descobertas)

**Validation:**
- Todas as transações devem estar em exatamente uma categoria
- Total de receitas == soma de receitas-4_unified.json
- Total de despesas == soma de despesas-4_unified.json
- Patrimônio em 31/12 deve ser consistente com baseline IRPF

---

### STAGE E5 — Análise

**Objetivo:** Gerar análises de fluxo de caixa, rácios, evolução patrimonial, tax planning.

**Execução determinística (cálculos numéricos):**
```bash
python scripts/e5_analyze.py
```
O script computa todos os blocos numéricos do `analise_financeira-5_analysis.json` (patrimônio, goals, fluxo_caixa, ratios, score, orçamento prospectivo, reserva emergência, endividamento, PGBL, pontos fortes/urgentes, consumo consciente, comportamento). Preserva chave `narrativas` existente. Tempo de execução: ~1s.

**E5.N (narrativas) é determinístico** — executar `python scripts/e5n_narrativas.py` para gerar os textos narrativos após os cálculos numéricos estarem prontos.

**Inputs:**
- `processed/E4_unified/*-4_unified.json` (todos)
- `processed/E4_unified/fluxo_mensal_detalhado-4_unified.json` ← **v4.1: breakdown mensal por origem/categoria (alimenta gráfico `receita_despesa_mensal`)**
- `config/report_spec.md` (especificação de relatório)
- `life_plan/life_plan_goals.md`
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`

**Processing logic:**

1. **Fluxo de caixa:**
   - Total recebido = receitas-4_unified.json
   - Total desembolsado = despesas-4_unified.json
   - Fluxo líquido = recebido - desembolsado
   - Variação de patrimônio = fluxo líquido + inflação ajustada

1b. **Fluxo de caixa mensal detalhado (CRÍTICO — alimenta gráfico `receita_despesa_mensal`):**
   - Input: `processed/E4_unified/fluxo_mensal_detalhado-4_unified.json`
   - Gerar chave `receita_despesa_mensal_detalhado` no E5 analysis JSON (`analise_financeira-5_analysis.json`) com a estrutura abaixo:
     ```json
     "receita_despesa_mensal_detalhado": {
       "labels": ["mmm/YY", "mmm/YY", "..."],
       "receita_datasets": [
         {"label": "[Origem PJ 1]", "data": [0.00, "..."]},
         {"label": "[Origem CLT]", "data": [0.00, "..."]},
         {"label": "Aluguéis", "data": [0.00, "..."]},
         {"label": "Rendimentos Financeiros", "data": [0.00, "..."]},
         {"label": "Outras Receitas", "data": [0.00, "..."]}
       ],
       "despesa_datasets": [
         {"label": "[Categoria 1]", "data": [0.00, "..."]},
         {"label": "[Categoria 2]", "data": [0.00, "..."]},
         "..."
       ],
       "totais_receita": [0.00, "..."],
       "totais_despesa": [0.00, "..."]
     }
     ```
   > **Nota:** Labels e datasets são gerados dinamicamente. Origens de receita conforme `categorization.json`. Categorias de despesa conforme `definitions.md`.
   - Cada array `data` tem exatamente N elementos (um por mês no período).
   - `totais_receita[i]` = soma de todos `receita_datasets[*].data[i]`.
   - `totais_despesa[i]` = soma de todos `despesa_datasets[*].data[i]`.
   - **⚠️ O E5 render script usa esta chave para montar o gráfico stacked. Se ausente, E5 faz fallback para médias planas (comportamento legado, mas INCORRETO).**

1c. **Orçamento Prospectivo (OBRIGATÓRIO — alimenta card 6 do E5):**
   - Input: `despesas-4_unified.json`
   - Agrupar despesas por categoria (usando categorias do `definitions.md`) e calcular a **média mensal** de cada categoria no período analisado.
   - Gerar chave `orcamento_prospectivo` no E5 analysis JSON com:
     - `categorias`: objeto `{categoria: valor_media_mensal}` (todas as categorias do `definitions.md`)
     - `total`: soma das médias mensais
     - `media_mensal`: igual a `total` (valor explícito para clareza)
     - `variacao_pct`: variação % do total em relação ao período anterior (se disponível)
     - `legenda`: string HTML com texto explicativo para o leitor do relatório. **Fórmula:**
       ```
       "Média mensal dos gastos dos últimos {N} meses, por categoria. Use como referência para planejar o orçamento dos próximos meses. Compare cada categoria com o total e identifique onde há espaço para otimizar. Total de R$ {total}/mês = {pct}% da receita recorrente."
       ```
       Onde `{N}` = número de meses no período, `{total}` = `media_mensal` formatado, `{pct}` = `(media_mensal / receita_recorrente_mensal) × 100` arredondado a 0 casas.
   - **⚠️ A chave `legenda` é OBRIGATÓRIA. O E5 injeta esse texto no card antes da tabela. Sem ela, o card fica sem contexto para o leitor.**

1d. **Programa de Milhas (OBRIGATÓRIO — alimenta card 9 do E5):**
   - Input primário: `config/milhas.md` (input manual com saldos e resgates)
   - Input secundário (se existir): `processed/E4_unified/pontos_milhas-4_unified.json` (dados extraídos de faturas de cartão)
   - Para cada programa listado em `milhas.md`, extrair: `programa`, `titular`, `saldo_pontos`, `valor_estimado_brl`, resgates no período com `valor_equivalente_brl`.
   - Se `pontos_milhas-4_unified.json` existir, usar para complementar/validar dados de acúmulo de pontos via faturas.
   - Gerar chave `programa_milhas` no E5 analysis JSON com:
     - `programas`: array de objetos `{programa, titular, saldo_pontos, valor_estimado_brl, economia_periodo_brl}`
       - `economia_periodo_brl` = soma dos `valor_equivalente_brl` de todos os resgates do programa no período
     - `total_valor_estimado_brl`: soma de todos `valor_estimado_brl`
     - `total_economia_periodo_brl`: soma de todos `economia_periodo_brl`
     - `total_pontos_resgatados`: soma de todos pontos usados em resgates no período
   - **⚠️ Se `config/milhas.md` não existir ou estiver zerado, gerar bloco com arrays vazios e totais = 0. O card E5 exibe mensagem "Nenhum programa de milhas cadastrado."**

2. **Rácios financeiros:**
   - Taxa de poupança **recorrente** = (receitas_recorrentes - despesas_totais) / receitas_recorrentes
     - ⚠️ **RECEITAS RECORRENTES** = excluir receitas one-time (rescisões, Kiwify, vendas de ativos, restituições extraordinárias)
     - ⚠️ **DESPESAS TOTAIS** = pessoais + PJ (DAS, impostos) + financiamentos — não apenas despesas-4_unified
     - ⚠️ Salvar AMBOS os valores no E5 analysis JSON: `taxa_poupanca_recorrente_pct` (KPI principal) e `taxa_poupanca_total_pct` (informativo)
     - O KPI do relatório DEVE exibir a taxa RECORRENTE como valor principal, e a projetada como subtítulo
   - Taxa de endividamento = dívidas / patrimônio bruto
   - Cobertura de despesas = patrimônio / (despesas anuais) = meses de cobertura
   - Rentabilidade = (investimentos) / (patrimônio) = %

3. **Evolução patrimonial:**
   - Comparar patrimônio atual vs. ano anterior (de IRPF)
   - Calcular crescimento: (patrimônio_atual - patrimônio_ano_anterior) / patrimônio_ano_anterior
   - Decompor crescimento: contribuições (depósitos) vs. rentabilidade

4. **Tax planning:**
   - Total de IR a pagar (de recibo IRPF)
   - Alíquota efetiva = IR pagos / renda tributável
   - Identificar oportunidades: deduções não utilizadas, contribuições a PGBL, opções de regime tributário

5. **Saúde financeira e Score:**
   - Comparar contra goals de life_plan
   - Validar cenários: "Como estamos progredindo para goal X?"
   - **Fórmula do Score Financeiro (obrigatória):**
     - O score é uma média ponderada de 5 componentes, cada um pontuado de 0 a 10:

     | Componente | Peso | Critério 10/10 | Critério 0/10 |
     |---|---|---|---|
     | Taxa de poupança recorrente | 2.0 | ≥ 50% | ≤ 0% (déficit) |
     | Cobertura de despesas (meses) | 1.5 | ≥ 24 meses | ≤ 3 meses |
     | Taxa de endividamento | 1.5 | ≤ 5% | ≥ 50% |
     | Progresso IF (% da meta) | 2.0 | ≥ 80% | ≤ 5% |
     | Diversificação (categorias ≥ 5% do patrimônio) | 1.0 | ≥ 5 categorias | ≤ 1 categoria |

     - `score.valor = Σ(componente_i × peso_i) / Σ(peso_i)`, arredondado a 1 decimal
     - **Classificação:** 0-2 = "Crítico", 2-4 = "Atenção", 4-6 = "Regular", 6-8 = "Bom", 8-10 = "Excelente"
     - Interpolar linearmente entre critérios. Ex: taxa poupança 25% → score 5.0 para esse componente
     - Salvar componentes individuais em `score.componentes[]` para transparência

6. **Visão patrimonial consolidada:**
   - Construir tabela patrimonial seguindo as regras canônicas de `config/regras_composicao_patrimonial.md`
   - Cada categoria deve ser rastreável até a fonte no baseline (E3)
   - Resumo das categorias:

   | Categoria | Fórmula / Fonte | Notas |
   |---|---|---|
   | Residência própria | IRPF David → imóvel Tasso da Silveira `valor_31_12_ano_base` | Sempre 1 imóvel, valor IRPF |
   | Imóveis investimento | SUM(ALL imoveis ALL members) − Residência | **Inclui imóveis David E Mariana** (Major Freire, Benedito Calixto, Leonardo da Vinci, Living Concept, Living Wish) |
   | Investimentos David | baseline `investimentos[]` + `contas_bancarias[]` de tipo investimento | Fundos + CDB + RDB + RF + contas corretora. Hashdex fica aqui (fundo regulado FIC FIM). Ver tabela de matching em `regras_composicao_patrimonial.md` |
   | Investimentos Mariana | baseline `investimentos[]` + `contas_bancarias[]` de tipo investimento | Mesma regra que David. Atualmente: BTG fundos/CDBs/CRAs |
   | Criptoativos | Binance extracts (saldo em BRL) | Crypto direta (BTC, ETH, ADA etc.), NÃO inclui fundos crypto regulados |
   | Caixa + Moeda Estrangeira | Bruto − (todas as categorias acima) − Veículos | **RESIDUAL.** Deve conter apenas CC puras + moeda estrangeira. Se > 5% do bruto → warning em qa_log |
   | Veículos | SUM(ALL veiculos ALL members) | Soma de todos os veículos de todos os membros |

   **Fórmulas obrigatórias (E4 `patrimonio.*`):**

   ```
   patrimonio.bruto         = baseline David.total_bens + baseline Mariana.total_bens
   patrimonio.investivel    = patrimonio.bruto − Residência − Veículos
   patrimonio.liquido       = patrimonio.bruto − patrimonio.dividas
   goals.if_pct             = patrimonio.investivel / goals.if_meta × 100
   goals.if_gap             = goals.if_meta − patrimonio.investivel
   ```

   **Invariantes de validação (MUST pass):**
   - `patrimonio.investivel < patrimonio.bruto` (SEMPRE — se violar, há erro de cálculo)
   - Soma das categorias da tabela = `patrimonio.bruto` (exato, sem centavos de diferença)
   - Soma dos percentuais = 100,0%
   - `goals.if_pct = patrimonio.investivel / goals.if_meta × 100` (calcular, nunca hardcodar)
   - `goals.if_gap = goals.if_meta − patrimonio.investivel` (calcular, nunca hardcodar)
   - Nenhum valor no E5 analysis JSON deve ser copiado do life_plan; o E5 CALCULA e o life_plan é ATUALIZADO com o resultado

6b. **Tabelas-resumo por categoria (OBRIGATÓRIO — alimentam cards de visão geral no relatório):**
   - Para cada dimensão abaixo, gerar um bloco no E5 analysis JSON com array de objetos `{categoria, valor, pct}` ordenado por valor decrescente, mais um `total`:

   **i. Patrimônio por categoria** (`patrimonio.tabela_categorias`):
   - Fonte: item 6 acima (visão patrimonial consolidada)
   - Categorias: Residência própria, Imóveis para renda, Investimentos David, Investimentos Mariana, Caixa + Moeda Estrangeira, Veículos, Criptoativos (Binance)
   - `total` = `patrimonio.bruto`
   - Linhas de rodapé (fora do array, mas no mesmo bloco):
     - `dividas` = `patrimonio.dividas` (com label "(-) Dívidas")
     - `investivel` = `patrimonio.investivel` (com label "PATRIMÔNIO INVESTÍVEL (excl. residência + veículos)")
   - **Validação:** soma dos `valor` do array == `patrimonio.bruto` (exato). Soma dos `pct` == 100,0%.
   - Estrutura JSON:
     ```json
     "patrimonio": {
       "tabela_categorias": [
         {"categoria": "Imóveis para renda ({N} imóveis)", "valor": 0.00, "pct": 0.0},
         {"categoria": "Residência própria ([endereço])", "valor": 0.00, "pct": 0.0},
         {"categoria": "Investimentos [Membro]", "valor": 0.00, "pct": 0.0},
         "..."
       ],
       "tabela_dividas": 0.00,
       "tabela_investivel": 0.00
     }
     ```
   > **Nota:** Valores, contagem de imóveis ({N}) e endereço da residência são calculados dinamicamente a partir do baseline patrimonial. O label "({N} imóveis)" deve refletir a contagem real excluindo residência.

   **ii. Receitas por fonte** (`fluxo_caixa.tabela_receitas`):
   - Fonte: `receitas-4_unified.json` agrupado por origem (PJ por empresa, CLT, aluguéis, rendimentos financeiros, outras)
   - `total` = soma de todas as receitas do período
   - Cada `pct` = `valor / total × 100`
   - Estrutura JSON:
     ```json
     "fluxo_caixa": {
       "tabela_receitas": [
         {"categoria": "[Origem conforme categorization.json]", "valor": 0.00, "pct": 0.0},
         "..."
       ]
     }
     ```

   **iii. Investimentos por classe** (`investimentos.tabela_classes`):
   - Fonte: `investimentos-4_unified.json` agrupado por classe de ativo (Renda Fixa, Fundos Multimercado, Ações/ETFs, Previdência, Criptoativos, Caixa)
   - `total` = soma de todos os investimentos
   - Cada `pct` = `valor / total × 100`
   - Estrutura JSON:
     ```json
     "investimentos": {
       "tabela_classes": [
         {"categoria": "[Classe de ativo]", "valor": 0.00, "pct": 0.0},
         "..."
       ]
     }
     ```

   **Regra geral para todas as tabelas-resumo:**
   - Ordenar por `valor` decrescente
   - Arredondar `pct` a 1 casa decimal
   - Soma dos `pct` DEVE ser exatamente 100,0% (ajustar o maior item se necessário para fechar arredondamento)
   - Incluir emojis nos labels de patrimônio conforme exemplo do relatório (🏠, 🏢, 📊, 💰, 🚗, ₿)

7. **Consumo consciente — análise de gastos pontuais:**
   - Varrer `despesas-4_unified.json` e identificar todas as transações individuais ≥ R$ 2.000 que NÃO sejam recorrentes (ex: aluguel, seguros, financiamento, mensalidades)
   - Classificar cada uma como **pontual** (compra única, presente, procedimento médico eletivo, eletrônico, viagem não-orçada, etc.)
   - Montar lista dos top gastos pontuais do período com os campos exatos abaixo
   - **IMPORTANTE — a chave do array DEVE ser `itens` (NÃO usar `top_gastos_pontuais` ou outro nome):**
     ```json
     "consumo_consciente": {
       "itens": [
         {
           "descricao": "Câmbio (viagem internacional)",
           "conta_cartao": "Itaú PF",
           "mes": "2025-04",
           "valor": 17456.46,
           "categoria": "viagem",
           "observacao": "Compra de dólares para viagem"
         }
       ],
       "total_pontuais": 0.00,
       "equivalente_meses_aporte": 0.0,
       "folga_mensal": 0.00,
       "folga_pct": 0.0,
       "teto_sugerido": 0.00,
       "analise": "texto livre de análise"
     }
     ```
   - Cada item em `itens` DEVE conter: `descricao`, `conta_cartao`, `mes`, `valor`, `categoria`, `observacao`
   - Calcular:
     - `consumo_consciente.total_pontuais` = soma dos gastos pontuais identificados
     - `consumo_consciente.equivalente_meses_aporte` = total_pontuais / aporte_mensal_IF (de life_plan)
     - `consumo_consciente.folga_mensal` = receita_recorrente − despesas_recorrentes (sem pontuais)
     - `consumo_consciente.folga_pct` = folga_mensal / receita_recorrente × 100
     - `consumo_consciente.teto_sugerido` = despesas_recorrentes × 1.15 (margem 15% para pontuais diluídos)
   - Se não houver gastos pontuais ≥ R$ 2.000 no período, gerar o bloco mesmo assim com `itens: []` e uma nota positiva em `analise`
   - Salvar no E5 analysis JSON no bloco `consumo_consciente`

8. **Diagnóstico de Comportamento Financeiro (OBRIGATÓRIO):**
   - Varrer os dados unificados (E3) e extratos (E2) para detectar padrões comportamentais recorrentes.
   - **Regras de detecção (verificar todas — incluir no output apenas as que forem positivas):**

   | Padrão | Regra de Detecção | Fonte de Dados |
   |---|---|---|
   | **Cheque especial recorrente** | Saldo negativo em qualquer conta corrente PF em ≥ 3 meses do período, enquanto há liquidez disponível em outras contas/investimentos | `despesas-4_unified.json` (saldos mensais), `investimentos-4_unified.json` |
   | **Gastos grandes sem planejamento** | Soma de transações pontuais ≥ R$2.000 (não recorrentes) em janela de 2 meses consecutivos > R$20.000, sem provisão prévia (conta reserva ou categoria "reserva de desejos") | `despesas-4_unified.json` (transações individuais), `consumo_consciente.itens` |
   | **Impostos pagos de forma irregular** | DAS pago em lotes irregulares (não mensal), OU carnê-leão com meses zerados quando há renda de aluguel, OU IRRF não retido em fonte que deveria reter | `despesas-4_unified.json` (transações com categoria "impostos"), `receitas-4_unified.json` (aluguéis) |
   | **Aluguéis não reinvestidos** | Renda de aluguéis entra em conta corrente e não há transferência correspondente para conta de investimento no mesmo mês ou mês seguinte | `receitas-4_unified.json` (aluguéis), `despesas-4_unified.json` (transferências para investimento) |
   | **Cartão de crédito parcelado excessivo** | Soma de parcelas ativas em cartão de crédito > 30% da receita recorrente mensal | `despesas-4_unified.json` (transações parceladas) |
   | **Receitas PJ misturadas com PF** | Receitas da PJ sendo usadas diretamente para despesas pessoais sem pró-labore formal | `receitas-4_unified.json`, `despesas-4_unified.json` (cruzamento PJ/PF) |

   - **Para cada padrão detectado, gerar:**
     - `padrao`: nome do padrão (ex: "Cheque especial recorrente")
     - `evidencia`: texto descritivo com dados concretos dos extratos (valores, meses, contas)
     - `mudanca_sugerida`: recomendação prática e específica de automatização
   - **Se NENHUM padrão for detectado**, gerar o bloco com array vazio e nota positiva: "Nenhum padrão comportamental de risco identificado — excelente disciplina financeira."
   - **Tom:** Não julgar. Padrões são hábitos formados pela praticidade. O objetivo é automatizar o fluxo.
   - Salvar no E5 analysis JSON no bloco `diagnostico_comportamental[]`

9. **Estratégia de Contrafluxo na Renda Fixa (OBRIGATÓRIO):**
   - Determinar o cenário de juros atual com base na Selic vigente (buscar em `definitions.md` ou input do ciclo):
     - `"alta"` → Selic ≥ 12%
     - `"queda"` → Selic entre 8% e 12% (exclusive)
     - `"baixa"` → Selic < 8%
   - Ler os valores de aporte mensal em CDI e IPCA+ de `life_plan/life_plan_goals.md` ou `config/definitions.md`
   - Montar tabela de cenários com 3 linhas (alta, queda, baixa), cada uma com: faixa de Selic, ação recomendada, justificativa
   - Marcar qual cenário é o "(AGORA)" com base na classificação acima
   - Gerar `acao_pratica`: texto personalizado com recomendação concreta baseada em:
     - Status da reserva de emergência (de `reserva_emergencia`)
     - Valores atuais de aporte CDI/IPCA+
     - Cenário de juros vigente
     - Exemplo para Selic alta: "Após a reserva de emergência atingir 12 meses (R$ Xk), redirecionar R$ Yk dos Cofrinhos: R$ Zk para manutenção + R$ Wk para Tesouro IPCA+ 2035/2040 (travando IPCA+N%). Aproveitar o momento de Selic alta para travar taxas reais excelentes antes do ciclo virar."
   - **Referência metodológica:** Raul Sena / AUVP — princípio do contrafluxo: comprar o que o mercado está evitando, pois é onde estão as melhores taxas
   - Salvar no E5 analysis JSON no bloco `investimentos.contrafluxo` com a estrutura:
     ```json
     "investimentos": {
       "contrafluxo": {
         "cenario_atual": "alta | queda | baixa",
         "selic_atual": 0.00,
         "selic_alta": "≥12%",
         "selic_queda": "8-12%",
         "selic_baixa": "<8%",
         "valor_cdi": 0.00,
         "valor_ipca": 0.00,
         "acao_pratica": "[texto personalizado — ver regras acima]"
       }
     }
     ```
   > **Nota:** `selic_atual` deve ser obtida de `definitions.md` ou fonte externa atualizada a cada ciclo. `valor_cdi` e `valor_ipca` vêm de `life_plan_goals.md`. As faixas textuais devem ser consistentes com os critérios de classificação (≥12%, 8-12%, <8%).
   - **⚠️ Este bloco alimenta o card obrigatório #12 (Contrafluxo) no E5. Se ausente, E5 gera card genérico (fallback educacional), mas o card personalizado é SEMPRE preferível.**

10. **Reserva de Emergência (OBRIGATÓRIO):**
    - Calcular a despesa mensal média (de `despesas-4_unified.json`, últimos N meses do período)
    - Levantar a liquidez imediata: soma de CDB liquidez diária + Tesouro Selic + poupança + saldo em conta corrente (de `investimentos-4_unified.json` e `patrimonio-4_unified.json`)
    - **Critério de inclusão na reserva:** Apenas ativos com liquidez D+0 ou D+1 e sem volatilidade relevante. Incluem-se: CDB liquidez diária, Tesouro Selic, poupança, contas remuneradas (PicPay, Nubank etc.) e saldos em conta corrente. **Não se incluem:** CDB com vencimento fixo, LCI/LCA com carência, CRA/CRI, fundos de ações, fundos multimercado com D+30+, ações, criptomoedas ou imóveis.
    - Calcular 3 níveis:
      - `minimo_6m` = despesa_mensal × 6 (Perini — mínimo absoluto)
      - `conforto_9m` = despesa_mensal × 9 (recomendação para família com dependentes)
      - `conservador_12m` = despesa_mensal × 12 (Cerbasi — famílias com renda variável)
    - Classificar status de cada nível: "✅ Coberto" (liquidez ≥ valor), "⚠ Parcial" (liquidez ≥ 80% do valor), "❌ Abaixo" (liquidez < 80%)
    - Detalhar a composição da liquidez em `composicao_liquida{}`: para cada ativo incluído, registrar chave, valor e prazo de resgate (D+0, D+1). Incluir `total_liquido` e `cobertura_meses` (= total_liquido / despesa_mensal).
    - Gerar recomendação baseada no nível atingido
    - O card E5 DEVE exibir: (1) tabela de 3 níveis com coluna de liquidez atual, (2) tabela de composição (Componente | Valor | Liquidez/Resgate), (3) rodapé explicativo dos critérios de inclusão.
    - Salvar no E5 analysis JSON no bloco `reserva_emergencia`

10b. **Reserva de Oportunidade (OBRIGATÓRIO):**
    - **Pré-requisito:** Só calcular se reserva de emergência atingir pelo menos o nível `conforto_9m` (status "✅ Coberto" ou "⚠ Parcial"). Caso contrário, gerar bloco com `status: "Aguardando emergência"` e recomendação de priorizar a reserva de emergência.
    - Calcular meta: entre 5% e 15% do patrimônio investível (usar 10% como padrão; ajustar se `definitions.md` definir outro percentual)
    - Levantar saldo atual: ativos de liquidez D+1 a D+90 que **excedam** o valor da reserva de emergência (nível `conforto_9m`)
      - Candidatos: CDB liquidez D+1 a D+90, Tesouro Selic (parcela excedente), fundos DI com resgate curto
      - **Não incluir** ativos já contabilizados na reserva de emergência
    - Classificar status:
      - "✅ Montada" (saldo ≥ meta)
      - "⚠ Parcial" (saldo ≥ 50% da meta)
      - "🔧 Montar" (saldo < 50% da meta ou inexistente)
    - Detalhar composição (quais ativos, valores, liquidez de cada um)
    - Gerar tabela comparativa Emergência × Oportunidade:

      | Aspecto | Reserva de Emergência | Reserva de Oportunidade |
      |---|---|---|
      | **Objetivo** | Cobrir despesas em caso de perda de renda ou imprevisto | Capturar oportunidades pontuais de investimento ou compra |
      | **Quando montar** | Imediatamente — prioridade nº 1 | Após emergência coberta (nível conforto 9 meses) |
      | **Meta** | 6 a 12× despesa mensal | 5% a 15% do patrimônio investível |
      | **Onde manter** | Liquidez D+0: poupança, CDB liquidez diária, Tesouro Selic | Liquidez D+1 a D+90: CDB curto prazo, Tesouro Selic (excedente), fundo DI |
      | **Quando usar** | Emergências reais: desemprego, doença, reparo urgente | Oportunidades com margem de segurança: queda de mercado >15%, imóvel abaixo do preço, desconto à vista >10%, aporte tático em renda variável |
      | **Reposição** | Repor imediatamente após uso | Repor em até 3–6 meses após uso |
      | **Rentabilidade** | Irrelevante — prioridade é liquidez | Pode buscar CDI+ desde que liquidez ≤ 90 dias |

    - Gerar recomendação personalizada baseada no status e na composição atual
    - Salvar no E5 analysis JSON no bloco `reserva_oportunidade`

11. **Endividamento (OBRIGATÓRIO):**
    - Levantar todas as dívidas ativas: financiamentos, consórcios, parcelas de cartão, empréstimos, cheque especial
    - Para cada dívida: descrição, saldo devedor, parcela mensal, taxa de juros, data término, ação recomendada
    - Calcular: `total_dividas`, `pct_divida_patrimonio` = total_dividas / patrimonio.bruto × 100
    - Classificar: "Livre de Dívidas" (0%), "Controlado" (<10%), "Atenção" (10-30%), "Crítico" (>30%)
    - Gerar recomendação geral (prioridade de quitação, avalanche vs bola de neve)
    - Se não houver dívidas, gerar bloco com `dividas: []` e classificação "Livre de Dívidas"
    - Salvar no E5 analysis JSON no bloco `endividamento`

12. **Previdência PGBL (OBRIGATÓRIO):**
    - Calcular renda tributável anual (pró-labore David + CLT Mariana + aluguéis tributáveis)
    - Limite PGBL anual = 12% da renda tributável
    - Aporte mensal atual: buscar em `despesas-4_unified.json` (transferências para previdência) ou `definitions.md`
    - Economia de IR anual = aporte_anual × alíquota_marginal (27,5% para esta faixa)
    - Projeção de acumulação em 10/15/20 anos com taxa real de 6% a.a. (juros compostos)
    - Renda mensal projetada = acumulado × 4% / 12 (regra dos 4%)
    - Status de portabilidade (se o fundo atual é adequado)
    - Salvar no E5 analysis JSON no bloco `previdencia_pgbl`

13. **Pontos Fortes (OBRIGATÓRIO):**
    - Varrer TODOS os outputs anteriores (E1 a E4) e identificar 5-7 destaques positivos
    - Critérios: taxa poupança acima de 20%, diversificação, ausência de dívidas, patrimônio crescente, disciplina de aporte, proteção patrimonial, planejamento
    - Para cada ponto: `{titulo, descricao}` — título curto + descrição com dados concretos
    - Tom: celebrativo e motivacional
    - Salvar no E5 analysis JSON no bloco `pontos_fortes[]`

14. **Pontos Urgentes (OBRIGATÓRIO):**
    - Varrer TODOS os outputs anteriores e identificar 5-7 ações críticas priorizadas por impacto
    - Critérios: dívidas de juros alto, impostos irregulares, reserva insuficiente, seguros vencidos, documentos expirados, oportunidades fiscais perdidas
    - Para cada ponto: `{prioridade, acao, impacto, prazo}` — numerado por urgência
    - Tom: direto e acionável, sem ser alarmista
    - Salvar no E5 analysis JSON no bloco `pontos_urgentes[]`

15. **Equilíbrio Presente × Futuro — Cerbasi (OBRIGATÓRIO):**
    - Calcular proporção gastos-presente vs investimentos-futuro:
      - `pct_presente` = despesas_totais / receita_recorrente × 100
      - `pct_futuro` = aportes_investimentos / receita_recorrente × 100
    - Classificar: "Equilibrado" (futuro 20-40%), "Pendendo para Futuro" (>40%), "Pendendo para Presente" (<20%), "Desequilibrado" (<10% ou >50%)
    - Gerar análise contextualizada (fase de vida da família, dependentes, plano migratório)
    - Gerar recomendação baseada no framework Cerbasi
    - Salvar no E5 analysis JSON no bloco `equilibrio_cerbasi`

16. **Gerar arquivo de análise:**
   - Salvar em `processed/E5_analysis/analise_financeira-5_analysis.json` com:
     - Fluxo de caixa (período)
     - Rácios (todos)
     - Evolução patrimonial (absoluta e %)
     - Alíquota efetiva de IR
     - Saúde vs. goals
     - **Visão patrimonial com todas as categorias e patrimônio investível**
     - **Orçamento prospectivo (bloco `orcamento_prospectivo` com categorias, total, media_mensal e `legenda` — ver item 1c)**
     - **Consumo consciente (bloco `consumo_consciente` com itens, totais e métricas)**
     - **Diagnóstico comportamental (bloco `diagnostico_comportamental[]` com padrões, evidências e mudanças)**
     - **Estratégia de contrafluxo (bloco `investimentos.contrafluxo` com cenário Selic, ação prática e valores de aporte — ver item 9)**
     - **Reserva de emergência (bloco `reserva_emergencia` com 3 critérios: 6m, 9m, 12m — ver item 10)**
     - **Reserva de oportunidade (bloco `reserva_oportunidade` com meta, composição, tabela comparativa e gatilhos de uso — ver item 10b)**
     - **Endividamento (bloco `endividamento` com relação dívida/patrimônio — ver item 11)**
     - **Previdência PGBL (bloco `previdencia_pgbl` com benefício fiscal e projeção — ver item 12 abaixo)**
     - **Pontos fortes (bloco `pontos_fortes[]` — ver item 13 abaixo)**
     - **Pontos urgentes (bloco `pontos_urgentes[]` — ver item 14 abaixo)**
     - **Equilíbrio Cerbasi (bloco `equilibrio_cerbasi` — ver item 15 abaixo)**
     - **Tarefas (bloco `tarefas[]` com n, t, p, e) e `tarefas_status`**
     - **Alertas (bloco `alertas[]` com tipo, titulo, descricao)**
   - O schema completo está na Seção 7.2 (`analise_financeira-5_analysis.json`)

**Outputs:**
- `processed/E5_analysis/analise_financeira-5_analysis.json`

**Validation:**
- Fluxo de caixa deve reconciliar com mudança de patrimônio
- Rácios devem estar em range esperado (e.g., endividamento < 50%)
- Crescimento patrimonial deve bater com contribuições + rentabilidade
- **`patrimonio.investivel` DEVE ser menor que `patrimonio.bruto`**
- **Soma das categorias patrimoniais DEVE igualar `patrimonio.bruto`**

---

### STAGE E5.N — Narrativas (Determinístico)

**Objetivo:** Gerar todos os textos analíticos e narrativos necessários para o relatório. Executada deterministicamente via `python scripts/e5n_narrativas.py`, após todos os cálculos estarem completos.

**Execução:**
```bash
python scripts/e5n_narrativas.py
```
O script é 100% determinístico (zero LLM). Mesmos inputs = mesmos outputs.

**Inputs:**
- `processed/E5_analysis/analise_financeira-5_analysis.json` (dados completos do E5)
- `members/members-1c_enriched.md` (dados dos membros)
- `life_plan/life_plan_goals.md` (metas, plano internacional, NCLEX)
- `config/report_spec.md` (regras de formatação e design)
- `config/definitions.md` (categorias, entidades)

**Output:** Nova chave `narrativas` adicionada ao E5 analysis JSON (`analise_financeira-5_analysis.json`) com a seguinte estrutura:

| Sub-chave | Conteúdo | Formato |
|---|---|---|
| `perfil_familia.left` | Parágrafos 1-4: titular, cônjuge, filho(s), pets | HTML (`<p>` em prosa narrativa) |
| `perfil_familia.right` | Parágrafos 5-7: plano de vida, meta IF, patrimônio | HTML (`<p>` em prosa narrativa) |
| `summaries.s1` a `s10` | Summary de cada seção do relatório | Texto puro (1-2 frases) |
| `charts.{chart_key}.context` | Contexto explicativo do gráfico | Texto puro (1-2 frases) |
| `charts.{chart_key}.conclusion` | Conclusão/insight acionável do gráfico | Texto puro (1-2 frases) |

**19 chart keys obrigatórias em `charts`:**
`patrimonio_doughnut`, `waterfall_if`, `receita_bar`, `despesas_doughnut`, `receita_despesa_mensal`, `score_gauge`, `alocacao_atual`, `alocacao_alvo`, `top15_ativos`, `yield_imoveis`, `custos_f1f2`, `cenario_cambial`, `projecao_if`, `renda_passiva`, `impostos_pj`, `riscos_bubble`, `decisoes`, `cenarios_mariana`, `viagens`

**Regras de geração:**
- Perfil: 7 parágrafos de prosa em `<p>`. SEM tabelas, bullets, `<strong>Label:</strong>`. Ordem: titular, cônjuge, filho(s), pets, plano de vida, meta IF, patrimônio. **Limite de 300 caracteres (texto puro, sem HTML) por parágrafo.** Validado em E5.N (V_PERFIL_MAX_CHARS) e truncado defensivamente em E6.
- Summaries: Factuais, com dados numéricos. Ex: "Patrimônio bruto de R$ 3,5M com 72% investível."
- Charts: Context = o que o gráfico mostra. Conclusion = insight acionável.
- Todos os textos em português brasileiro.

**Regras de formatação monetária (OBRIGATÓRIAS em TODOS os textos gerados):**
- Valores em milhões: `R$ X,YM` (vírgula como separador decimal, sufixo `M`). Ex: `R$ 3,5M`, `R$ 7,2M`.
- Valores em milhares: `R$ XXk` ou `R$ XX,Yk`. Ex: `R$ 20k`, `R$ 77,7k`.
- **PROIBIDO:** `KM` como sufixo (ex: `R$ 2,3KM` ← ERRADO). `K` e `M` são mutuamente exclusivos.
- **PROIBIDO:** Ponto como separador decimal em texto narrativo (ex: `R$ 7.2M` ← ERRADO, usar `R$ 7,2M`).
- **PROIBIDO:** Espaço entre sufixos (ex: `R$ 2,3k M` ← ERRADO).
- O E5 possui validação V19 que rejeita o relatório se encontrar esses padrões inválidos.

**Validação E5.N (DEVE passar antes de avançar para E6):**
- [ ] Chave `narrativas` presente no JSON
- [ ] `perfil_familia.left` e `perfil_familia.right` presentes e não-vazios
- [ ] `summaries` contém 10 chaves (s1 a s10), todas não-vazias
- [ ] `charts` contém 19 chaves, cada uma com `context` e `conclusion` não-vazios
- [ ] Perfil é HTML com `<p>` (sem `<table>`, `<ul>`, `<li>`)
- [ ] Cada parágrafo do `perfil_familia` tem ≤ 300 caracteres (texto puro sem tags HTML)
- [ ] Nenhum texto contém `KM` como sufixo monetário, ponto decimal em `R$`, ou espaço entre `k` e `M`

#### E5.N — Enriquecimento de Tarefas (v5.3+)

**Fluxo híbrido (curado + determinístico):**
1. `config/tarefas.md` → E5 (parser determinístico) → `tarefas[]` no JSON (formato `{n, t, p, e, categoria, ref}`)
2. E5.N (`e5n_narrativas.py`, determinístico) lê `tarefas[]` + dados financeiros → pode adicionar `tarefas_sugeridas[]` ao JSON

**Input para enriquecimento:**
- `tarefas[]` já parseado do E5 JSON
- `config/decisions.md` (decisões confirmadas + pendências)
- `config/tarefas.md` (backlog curado — fonte da verdade)
- Dados financeiros do E5 JSON (score, ratios, reserva, endividamento, patrimônio)
- `life_plan/life_plan_goals.md`

**Output adicional:** Chave `tarefas_sugeridas` no E5 JSON:
```json
"tarefas_sugeridas": [
  {
    "t": "Descrição da tarefa sugerida",
    "motivo": "Dado financeiro que motivou a sugestão",
    "p": "alta|media|baixa"
  }
]
```

**Regras para sugestão de novas tarefas:**
- O LLM pode sugerir tarefas NÃO presentes no `tarefas.md` com base em:
  - Métricas que pioraram desde o ciclo anterior
  - Deadlines próximos (ex: IRPF, DAS)
  - Oportunidades detectadas nos dados (ex: spread de CDB, rebalanceamento)
- Tarefas sugeridas aparecem em bloco separado no Apêndice E ("Tarefas Sugeridas pela Análise")
- O titular decide se inclui no `tarefas.md` do próximo ciclo — sugestões NUNCA entram automaticamente no backlog curado

**Manutenção do `config/tarefas.md`:**
- Atualizar a cada ciclo: marcar `feito`, adicionar novas, ajustar prazos
- Manter numeração estável (#) entre ciclos para tracking
- Tarefas `feito` ficam 1 ciclo no arquivo, depois vão para "Concluídas"
- Formato: `| # | Tarefa | Categoria | Prazo | Status | Ref |`
- Categorias: Invest. | Orçamento | Tributário | Seguros | Imóveis | Financeiro | Plan. EUA | Jurídico | Sucessório | Pipeline
- Prioridades: S (Essencial) | R (Recomendada) | O (Opcional) — definidas por seção do arquivo

---

### STAGE E6 — Relatório HTML (Determinístico)

**Objetivo:** Renderizar o relatório HTML final a partir do template + E5 JSON (dados + narrativas). Execução 100% determinística via script Python — sem LLM.

**Comando:**
```
python scripts/e6_render.py
```

**Inputs:**
- `config/templates/report_template.html` ← template com placeholders `{{...}}`
- `processed/E5_analysis/analise_financeira-5_analysis.json` ← dados + narrativas
- `config/manual_operacao.md` ← versão do manual
- `config/definitions.md` ← categorias de despesa

**Output:** `output/relatorio_financeiro_ferreira_campos_[DATE].html` (onde `[DATE]` = `YYYYMMDD` sem hífens, ex: `20260413`)

**O que o script faz (6 fases):**

| Fase | Equivalente antigo | O que faz |
|---|---|---|
| E6.1 | E5.1 (Cover/KPIs) | Substitui `{{COVER_*}}`, `{{KPI_*}}`, `{{NOME}}`, `{{FOOTER_CONTENT}}` |
| E6.2 | E5.2 (Perfil) | Injeta `narrativas.perfil_familia.left/right` |
| E6.3 | E5.3 (JSON) | Monta report-data JSON (20 chaves, 19 charts) por mapeamento de dados |
| E6.4 | E5.4 (S1-S5) | Gera HTML das seções com charts (canvas IDs canônicos) + cards obrigatórios |
| E6.5 | E5.5 (S6-S10+Apps) | Gera HTML das seções restantes + apêndices |
| E6.6 | E5.6 (Validação) | Roda 19 checagens automáticas |

**Mapeamento de canvas IDs (chart key → canvas ID):**

| Chart key (narrativas/JSON) | Canvas ID (HTML) | Seção |
|---|---|---|
| `patrimonio_doughnut` | `chart-patrimonio-doughnut` | S1 |
| `waterfall_if` | `chart-waterfall-if` | S1 |
| `receita_bar` | `chart-receita-bar` | S2 |
| `despesas_doughnut` | `chart-despesas-doughnut` | S2 |
| `receita_despesa_mensal` | `chart-receita-despesa-mensal` | S2 |
| `score_gauge` | `chart-score-gauge` | S2 |
| `alocacao_atual` | `chart-alocacao-atual` | S3 |
| `alocacao_alvo` | `chart-alocacao-alvo` | S3 |
| `top15_ativos` | `chart-top15-ativos` | S3 |
| `yield_imoveis` | `chart-yield-imoveis` | S4 |
| `custos_f1f2` | `chart-custos-f1f2` | S5 |
| `cenario_cambial` | `chart-cenarios-cambiais` | S6 |
| `projecao_if` | `chart-projecao-3cenarios` | S7 |
| `renda_passiva` | `chart-renda-passiva` | S7 |
| `impostos_pj` | `chart-impostos-pj` | S8 |
| `riscos_bubble` | `chart-bubble-riscos` | S9 |
| `decisoes` | `chart-top5-decisoes` | S10 |
| `cenarios_mariana` | `chart-mariana-cenarios` | App E |
| `viagens` | `chart-viagens` | App E |

**Cards obrigatórios (gerados pelo script a partir de dados E4):**
1. **Patrimônio por Categoria (S1)** — tabela Categoria | Valor (R$) | % do Total + rodapé Dívidas e Patrimônio Investível
2. **Receitas por Fonte (S1)** — tabela Categoria | Valor (R$) | % do Total por origem de receita
3. Reserva de Emergência (S1) — 3 níveis
4. Reserva de Oportunidade (S1) — meta, status, tabela comparativa, gatilhos de uso
5. Endividamento (S1) — dívidas + % patrimônio
6. Orçamento Prospectivo (S2) — 14 categorias (tabela Categoria | Valor R$ | % do Total) + legenda "Como usar" obrigatória (ver regra abaixo)
7. Consumo Consciente (S2) — gastos pontuais
8. Diagnóstico Comportamental (S2) — padrões
9. **Programa de Milhas — Economia (S2)** — tabela Programa | Saldo (pts) | Valor Est. (R$) | Economia no Período (R$). Input manual: `config/milhas.md` ← **NOVO v4.4**
10. **Investimentos por Classe (S3)** — tabela Categoria | Valor (R$) | % do Total por classe de ativo
11. KPIs Rentabilidade + Tabela 3.1 (S3)
12. Estratégia Aporte 3.2 (S3)
13. Contrafluxo (S3)
14. Previdência PGBL (S7)
15. Pontos Fortes (S10)
16. Pontos Urgentes (S10)
17. Equilíbrio Cerbasi (S10)

**Regra de legenda — Card "Orçamento Prospectivo" (card 6):**

O card DEVE conter, **antes da tabela**, um parágrafo explicativo (`<p class="card-legend">`) com os seguintes elementos:
1. **O que os valores representam:** média mensal dos gastos realizados nos últimos 12 meses, agrupados por categoria.
2. **Para que serve:** referência (baseline) para planejar o orçamento dos próximos meses.
3. **Como usar:** comparar o total com a receita recorrente e identificar categorias com peso desproporcional.
4. **Dado de contexto:** incluir o % do total em relação à receita recorrente mensal (ex: "Total de R$ 31.831/mês = 41% da receita recorrente").

Texto-modelo (adaptar com dados reais de cada período):
```html
<p class="card-legend">Média mensal dos gastos dos últimos 12 meses, por categoria. Use como referência para planejar o orçamento dos próximos meses. Compare cada categoria com o total e identifique onde há espaço para otimizar. Total de R$ XX.XXX/mês = YY% da receita recorrente.</p>
```

O E4 DEVE gerar a chave `orcamento_prospectivo.legenda` com o texto já montado (usando valores calculados de `media_mensal`, `receita_recorrente` e o percentual). O E5 render script injeta esse texto no card antes da tabela.

**Validação E6.6 (19 checagens automáticas — V1 a V19):**

| Check | Nome | Critério |
|---|---|---|
| V1 | Placeholders resolvidos | Nenhum `{{...}}` restante fora de comentários HTML |
| V2 | JSON válido | `report-data` JSON parseia sem erro |
| V3 | 19 datasets de gráficos | `charts` no JSON contém 19 chaves |
| V4 | 19 canvas IDs | HTML contém 19 `<canvas id="chart-...">` |
| V5 | 9+ seções | HTML contém 9+ `id="secao-N"` |
| V6 | 5 apêndices | HTML contém 5 `id="apendice-[a-e]"` |
| V7 | Cards obrigatórios presentes | Todos os cards listados na seção E6 existem no HTML |
| V8 | COVER_DATA_HORA | Contém padrão de data/hora válido |
| V9 | COVER_VERSAO | Contém número de versão válido |
| V10 | Perfil é prosa narrativa | `perfil_familia` contém `<p>`, sem `<table>`, `<ul>`, `<li>` |
| V11 | KPIs consistentes com E5 | Valores de KPI no HTML batem com JSON |
| V12 | Imóveis estimados > 0 | `patrimonio.imoveis_estimado > 0` |
| V13 | Orçamento com categorias | `orcamento_prospectivo` tem 14+ categorias |
| V14 | HTML > 100KB | Tamanho do HTML > 100KB (relatório completo) |
| V15 | CSS: sem inline margin | Nenhum `margin-top`/`margin-bottom` inline no HTML |
| V16 | CSS: .card-title primeiro filho | Todo `.card` tem `.card-title` como primeiro filho |
| V17 | CSS: sem hex hardcoded | Nenhuma cor hexadecimal hardcoded no HTML (usar variáveis CSS) |
| V18 | CSS: tr.total-row | Linhas de total usam classe `tr.total-row` |
| V19 | Formato monetário válido | Nenhum `KM`, `k M` separado, nem ponto decimal em `R$` (ver regras E5.N) |

> **Nota:** O limite de 300 caracteres por parágrafo do `perfil_familia` é validado em E5.N (V_PERFIL_MAX_CHARS) e truncado defensivamente em `_truncate_perfil_paragraphs` no E6, mas não constitui um check numerado na `validate_report()`.

**Se qualquer validação falhar:** O script imprime qual checagem falhou. Corrigir na fonte:
- Texto errado → re-rodar E5.N
- Dados errados → corrigir E2/E3/E4/E5
- Layout/CSS → corrigir template

---

### STAGE E6-regen — Regeneração rápida do relatório

**Objetivo:** Regenerar o relatório quando houve mudança no template ou nos dados, sem reprocessar E0→E4.

**Quando usar:**
- Alteração no CSS, layout ou JS do template → `python scripts/e6_render.py`
- Ajuste nos textos narrativos → re-rodar E5.N + `python scripts/e6_render.py`
- Correção de dados → re-rodar E5 (ou E4+E5) + `python scripts/e6_render.py`

**Processo:**
1. (Opcional) Salvar estado via `python scripts/e_save.py -m "mensagem"` se desejar preservar versão anterior
2. Rodar `python scripts/e6_render.py`
3. Verificar que as 19 validações passam

---

### STAGE E7 — Review & Refine (LLM — pós-relatório)

**Objetivo:** Realizar uma revisão holística do relatório completo usando a persona e abordagem definidas em `config/methodology.md`. Retroalimenta as narrativas geradas pelo pipeline, detectando inconsistências entre seções e refinando textos, análises, cards, lista de tarefas e prioridades com base na visão completa do relatório.

**Quando usar:**
- Após qualquer execução completa do pipeline que inclua E5.N + E6
- Quando narrativas individuais precisam ser revisadas no contexto do relatório inteiro
- Quando suspeitar de contradições entre seções (ex: score vs. diagnóstico, fluxo vs. IF)
- Quando a lista de tarefas precisa ser re-priorizada com base na análise holística

**Quando NÃO usar:**
- Narrativas ainda não foram geradas (E5.N não executado) — executar E5.N primeiro
- Apenas template/CSS mudou — usar E6-regen
- Dados subjacentes precisam ser corrigidos — corrigir E2→E5 antes

**Pré-condição:** E5 JSON deve conter a chave `narrativas` (summaries + charts). E6 render deve ter gerado o HTML.

**Procedimento (4 sub-passos):**

**9a — Cross-validation determinística:**
```bash
python scripts/e7_review.py                # Roda 14 checks + gera template
python scripts/e7_review.py --dry-run      # Preview (nenhuma mudança)
```
O script executa 14 verificações automáticas:

| Check | Descrição |
|---|---|
| CV1 | Score formula: nota × peso = score reportado |
| CV2 | Patrimônio: soma composição = bruto |
| CV3 | Fluxo: receita − despesa = fluxo líquido |
| CV4 | Taxa poupança recorrente vs dados |
| CV5 | IF meta × TRS = renda mensal projetada |
| CV6 | Progresso IF vs patrimônio investível |
| CV7 | Taxa endividamento vs patrimônio bruto |
| CV8 | Cobertura reserva emergência |
| CV9 | Completude de summaries (s1-s10) |
| CV10 | Completude de charts (context + conclusion) |
| CV11 | Estrutura de tarefas |
| CV12 | Diagnóstico comportamental presente |
| CV13 | Classificação do score (label vs valor) |
| CV14 | Formato monetário nas narrativas |

Resultado: `processed/E7_review/e7_review_template.json` com findings + template para refinamentos.

**9b — Review holístico (LLM):**
A LLM lê:
1. O review template gerado em 9a
2. O relatório HTML completo em `output/`
3. A persona e abordagem em `config/methodology.md`

E preenche o review JSON com:
- `refinements.summaries`: summaries refinados (apenas os que precisam de ajuste)
- `refinements.charts`: chart context/conclusion refinados
- `refinements.perfil_familia`: perfil atualizado (se necessário)
- `refinements.tarefas_reorder.new_order`: nova ordem de prioridade (lista de números)
- `refinements.strategic_insights.insights`: insights da visão holística
- `refinements.inconsistencies_found.items`: inconsistências detectadas além dos CV checks

**9c — Aplicar refinamentos:**
```bash
python scripts/e7_review.py --apply review.json --dry-run   # Preview
python scripts/e7_review.py --apply review.json              # Aplicar
```

**9d — Re-render final:**
```bash
python scripts/e6_render.py
```

**Artefatos gerados:**
- `processed/E7_review/e7_review_template.json` — template com cross-validation results
- Chave `review_metadata` no E5 JSON — metadata do review aplicado
- Chave `narrativas.strategic_insights` no E5 JSON — insights holísticos
- `output/*.html` — relatório final refinado (após E6-final)

#### Schema: Review Template (output de `e7_review.py`)

O template gerado pelo passo 9a tem a seguinte estrutura. Chaves prefixadas com `_` são instruções para a LLM e são ignoradas pelo script.

```jsonc
{
  "metadata": {
    "timestamp": "ISO-8601",              // string — gerado automaticamente
    "e7_version": "1.0",                  // string — versão do schema
    "persona_summary": "..."              // string — primeiros 200 chars da persona (methodology.md)
  },
  "cross_validation": {
    "total_checks": 14,                   // int — total de CVs executados
    "passed": 12,                         // int — quantos passaram
    "failed": 2,                          // int — quantos falharam
    "issues": [                           // array — apenas os que falharam
      {
        "check_id": "CV4",                // string — identificador (CV1-CV14)
        "name": "Taxa poupança recorrente vs dados",  // string
        "severity": "error",              // "error" | "warning" | "info"
        "passed": false,                  // bool
        "details": "Calculada: -37.4%, reportada: 19.8%",  // string
        "sections": ["fluxo_caixa"]       // string[] — seções afetadas
      }
    ],
    "all_results": [/* mesma estrutura, todos os 14 */]
  },
  "refinements": {
    "_instructions": "...",               // string — ignorada pelo script
    "summaries": {
      "_instructions": "...",             // string — ignorada
      // LLM preenche: "s1": "texto refinado", "s3": "texto refinado", ...
    },
    "charts": {
      "_instructions": "...",             // string — ignorada
      // LLM preenche: "chart_key": {"context": "...", "conclusion": "..."}, ...
    },
    "perfil_familia": {
      "_instructions": "...",             // string — ignorada
      // LLM preenche: "left": "...", "right": "..."
    },
    "tarefas_reorder": {
      "_instructions": "...",             // string — ignorada
      "new_order": []                     // int[] — LLM preenche com números de tarefas
    },
    "strategic_insights": {
      "_instructions": "...",             // string — ignorada
      "insights": []                      // string[] — LLM preenche
    },
    "inconsistencies_found": {
      "_instructions": "...",             // string — ignorada
      "items": []                         // object[] — LLM preenche (formato livre)
    }
  },
  "current_state": {
    "_note": "...",                        // string — read-only snapshot
    "summary_keys": ["s1", "s2", ...],    // string[] — chaves existentes
    "chart_keys": ["chart1", ...],        // string[] — chaves existentes
    "total_tarefas": 15,                  // int
    "tarefas_alta_prioridade": [...],     // object[] — tarefas com p="alta"
    "score": 2.9,                         // float | null
    "score_label": "Atenção",             // string | null
    "patrimonio_bruto": 0,               // float | null
    "patrimonio_investivel": 0,           // float | null
    "fluxo_liquido": 591400              // float | null
  }
}
```

#### Schema: Review JSON (input de `--apply`)

O JSON que a LLM produz e que é validado por `validate_review()` antes da aplicação. Apenas os campos preenchidos serão aplicados; campos ausentes ou com `_instructions` são ignorados.

```jsonc
{
  "metadata": {                           // opcional — propagado para review_metadata no E5
    "timestamp": "ISO-8601",              // string
    "e7_version": "1.0",                  // string
    "persona": "...",                     // string — campo livre
    "reviewer_note": "..."                // string — campo livre
  },
  "refinements": {                        // OBRIGATÓRIO — validação falha sem esta chave
    "summaries": {                        // opcional — apenas summaries a alterar
      // "s1": string,                    // DEVE ser string não-vazia
      // "s2_fluxo_caixa": string,        // chave = nome do summary no E5
      // ...                              // chaves com "_" são ignoradas
    },
    "charts": {                           // opcional — apenas charts a alterar
      // "chart_key": {                   // DEVE ser dict
      //   "context": string,             // opcional — string não-vazia
      //   "conclusion": string           // opcional — string não-vazia
      // }
      // chaves com "_" são ignoradas
    },
    "perfil_familia": {                   // opcional
      // "left": string,                  // texto coluna esquerda do perfil
      // "right": string                  // texto coluna direita do perfil
    },
    "tarefas_reorder": {                  // opcional
      "new_order": [3, 1, 5, 2, 4]       // int[] — números das tarefas na nova ordem
                                          // tarefas omitidas são adicionadas ao final
    },
    "strategic_insights": {               // opcional
      "insights": [                       // string[] — DEVE ser lista de strings
        "Insight 1...",
        "Insight 2..."
      ]
    },
    "inconsistencies_found": {            // opcional
      "items": [                          // object[] — formato livre
        {
          "tipo": "Narrativa vs Dados",   // sugerido mas não validado
          "localizacao": "Seção 2",       // sugerido mas não validado
          "descricao": "...",             // sugerido mas não validado
          "correcao": "..."               // sugerido mas não validado
        }
      ]
    }
  },
  // Campos extras (não processados por --apply, mas úteis para auditoria):
  "cross_validation_fixes": { ... },      // opcional — notas sobre fixes de CV
  "task_reprioritization": { ... }        // opcional — justificativa de reordenação
}
```

#### Regras de validação (`validate_review()`)

| Campo | Regra | Erro se violada |
|---|---|---|
| `refinements` | DEVE existir como chave top-level | `Missing 'refinements' key` |
| `refinements.summaries.*` | Cada valor DEVE ser `string` não-vazia | `summaries.{k} must be a string` / `is empty` |
| `refinements.charts.*` | Cada valor DEVE ser `dict` com `context` e/ou `conclusion` como `string` | `charts.{k} must be a dict` / `.context must be a string` |
| `refinements.perfil_familia.left\|right` | Se presente, DEVE ser `string` | `perfil_familia.{side} must be a string` |
| `refinements.tarefas_reorder.new_order` | Se presente, DEVE ser `list[int]` | `must be a list of integers` |
| `refinements.strategic_insights.insights` | Se presente, DEVE ser `list[str]` | `must be a list of strings` |

**Atenção — armadilhas conhecidas:**
- **summaries como dict:** Se a LLM retornar summaries com estrutura aninhada (ex: `{"current_issue": "...", "refined_text": "..."}` em vez de `string`), a validação falha. Normalizar antes de aplicar.
- **strategic_insights como dict:** Se a LLM retornar insights como `[{"titulo": "...", "descricao": "..."}]` em vez de `["string"]`, a validação falha. Extrair `descricao` ou concatenar antes de aplicar.
- **Chaves com underscore:** Chaves prefixadas com `_` (ex: `_instructions`) são silenciosamente ignoradas tanto na validação quanto na aplicação.

#### Efeitos do `--apply` no E5 JSON

Após `e7_review.py --apply review.json`, o E5 JSON é modificado in-place:

| Operação | Destino no E5 JSON |
|---|---|
| Summaries refinados | `narrativas.summaries.{key}` — substitui texto anterior |
| Charts refinados | `narrativas.charts.{key}.context` e/ou `.conclusion` |
| Perfil família | `narrativas.perfil_familia.left` e/ou `.right` |
| Reordenação de tarefas | `tarefas[]` — re-indexado com `n` sequencial |
| Strategic insights | `narrativas.strategic_insights` — array de strings |
| Inconsistências | `narrativas.inconsistencies_review` — array de objects |
| Review metadata | `review_metadata` — timestamp, versão, changes aplicadas |

O `--strip` remove: `review_metadata`, `narrativas.strategic_insights`, `narrativas.inconsistencies_review`. Summaries e charts refinados **não** são revertidos (já substituíram os originais).

**Limpeza:**
```bash
python scripts/e7_review.py --strip              # Remove dados de review do E5 JSON
python scripts/e_reset.py --from E7              # Reset E7 + re-render E6
```

**Tempo estimado:** ~5 min (cross-validation ~2s + LLM review ~4 min + apply + render ~30s)

---

### STAGE E-reset — Reprocessamento completo do zero

**Objetivo:** Apagar todos os artefatos gerados pelo pipeline (E2→E6) e re-executar o processamento completo a partir dos arquivos originais já roteados em `data/`. Artefatos E1 (`members/*-1a_extract.json`, `members-1b_unified.json`, `members-1c_enriched.md`) são **preservados** porque E1 é LLM-driven e não pode ser regenerado automaticamente.

**Quando usar:**
- Mudança estrutural no manual, definitions, methodology ou report_spec que afeta múltiplas etapas
- Suspeita de dados corrompidos ou inconsistentes nos JSONs intermediários
- Atualização significativa de regras de categorização, membros ou life plan que invalida todo o processamento anterior
- Após correção de bug que afetou etapas anteriores e propagou erro para frente

**Quando NÃO usar:**
- Apenas template/CSS mudou → usar E6-regen
- Apenas novos extratos chegaram → usar fluxo normal E0 + ciclo incremental
- Apenas uma etapa específica precisa ser refeita → usar `E-reset-from`

**Procedimento:**

> Nota: todos os comandos nesta seção assumem working directory = `financas-familia/`.

**Passo 1 — Preview (opcional mas recomendado):**
```bash
python scripts/e_reset.py --dry-run
```

**Passo 2 — Executar reset completo:**
```bash
python scripts/e_reset.py
```

O script automaticamente:
- Apaga artefatos gerados (E2→E6 JSONs, HTML, logs operacionais, `__pycache__`)
- Preserva `data/`, `members/*-0_original.*`, artefatos E1 (`*-1a_extract.json`, `*-1b_unified.json`, `*-1c_enriched.md`), `config/`, `life_plan/`, `inbox_processed/`, `logs/inbox_log.md`, `logs/qa_log.md`
- Verifica dependências Python (pdfplumber, pytz) **antes** de apagar qualquer artefato
- Executa etapas determinísticas: `e2_extract.py` → `e3_reconcile.py` → `e4_categorize.py` → `e5_analyze.py` → `e5n_narrativas.py` → `e6_render.py`
- Pula etapas LLM (E1, E1.5, E2-llm) com lembrete no console
- Valida presença dos artefatos esperados ao final

**Passo 3 — Executar etapas LLM pendentes:**
O script informa quais etapas LLM precisam ser executadas manualmente (E1, E1.5, E2-llm).

> **Nota:** Nenhuma etapa do pipeline faz commit ou push automaticamente. Quando desejar salvar o estado, execute `python scripts/e_save.py -m "mensagem"` manualmente.

**Flags disponíveis:**
| Flag | Efeito |
|---|---|
| `--dry-run` | Mostra o que seria feito sem executar nenhuma mudança |
| `--clean-only` | Apenas apaga artefatos, não re-executa o pipeline |
| `--no-validate` | Pula validação pós-execução |

**Validation:**
- O script valida presença **e conteúdo** dos artefatos E3/E4/E5/E6 (JSON parseável, campos obrigatórios não-vazios)
- Executar checklist V1–V19 do E6 (Seção 4, STAGE E6)
- Comparar com relatório anterior (disponível no histórico Git) para confirmar que não houve perda de dados

---

### STAGE E-reset-from — Reprocessamento parcial

**Objetivo:** Reprocessar o pipeline a partir de uma etapa específica, limpando artefatos daquela etapa em diante. Mais rápido que E-reset pois preserva etapas anteriores intactas.

**Sintaxe:** `python scripts/e_reset.py --from E[N]` onde N é a etapa inicial.

**Valores válidos para `--from`:** E2-faturas, E3, E4, E5, E5.N, E6, E7.

**Quando usar:**
- Novo parser de fatura ou correção em parser existente → `--from E2-faturas`
- Mudança em `definitions.md` (regras de categorização) → `--from E4`
- Mudança em `report_spec.md` ou `life_plan_goals.md` → `--from E5`
- Mudança em narrativas ou textos analíticos → `--from E5.N`
- Mudança no template HTML/CSS → `--from E6` (equivalente a E6-regen)

**Procedimento:**

> Nota: todos os comandos nesta seção assumem working directory = `financas-familia/`.

**Passo 1 — Preview (opcional mas recomendado):**
```bash
python scripts/e_reset.py --from E[N] --dry-run
```

**Passo 2 — Executar reset parcial:**
```bash
python scripts/e_reset.py --from E[N]
```

O script automaticamente:
- Apaga artefatos da etapa escolhida em diante (cascata)
- Quando E5.N está na cascata, **limpa a chave `narrativas`** dos JSONs E5 (garante que narrativas velhas não passem para E6)
- Verifica dependências Python antes de apagar artefatos
- Executa etapas determinísticas na sequência correta (incluindo E5.N via `e5n_narrativas.py`)
- Valida artefatos ao final (existência + conteúdo JSON)

**Referência de cascata (o que o script apaga e executa):**

| `--from` | Apaga | Executa |
|---|---|---|
| `E2-faturas` | Faturas E2 (por tipo, não filename) + E3 + E4 + E5 + E6 + logs | e2_extract --faturas-only → e3 → e4 → e5 → e5n → e6 |
| `E3` | E3 + E4 + E5 + E6 + logs | e3 → e4 → e5 → e5n → e6 |
| `E4` | E4 + E5 + E6 + logs | e4 → e5 → e5n → e6 |
| `E5` | E5 + E6 | e5 → e5n → e6 |
| `E5.N` | narrativas do E5 JSON + E6 | e5n → e6 |
| `E6` | E6 | e6 |
| `E7` | E7 artefatos (review template, review metadata, strategic insights) + E6 | e7_review (crossval) → (E7-review LLM) → e7_review --apply → e6 |

**Passo 3 — Executar etapas LLM pendentes (se houver):**
O script informa quais etapas LLM precisam ser executadas manualmente (apenas E7-review quando `--from E7`).

> **Nota:** Nenhuma etapa do pipeline faz commit ou push automaticamente. Quando desejar salvar o estado, execute `python scripts/e_save.py -m "mensagem"` manualmente.

**Validation:** Mesma do E-reset (checklist V1–V19 do E6), comparando com relatório anterior via Git.

---

### STAGE E-full-reset — Reprocessamento completo desde E0 (unlock + audit + pipeline inteiro)

**Objetivo:** Executar o ciclo completo do pipeline desde a verificação de integridade dos PDFs (E0-unlock, E0-audit) até o relatório final refinado (E6-final, após E7-review + E7-apply), incluindo todas as etapas LLM e determinísticas. É o "nuclear option" — reconstrói tudo do zero a partir dos originais em `data/`.

**Quando usar:**
- Reprocessamento completo solicitado explicitamente pelo usuário
- Suspeita de PDFs corrompidos ou encriptados que escaparam para `data/`
- Mudança estrutural profunda (novo membro, reestruturação de contas, novo banco) que invalida E1 em diante
- Primeira execução após migração de versão major do pipeline
- Após correção de bug em E0-unlock ou E0-audit que pode ter permitido dados ruins

**Quando NÃO usar:**
- Artefatos E1 estão corretos e apenas etapas E2→E6 precisam ser refeitas → usar `E-reset`
- Apenas uma etapa específica precisa ser refeita → usar `E-reset-from`
- Apenas template/CSS mudou → usar `E6-regen`

**Diferença para E-reset:** E-reset preserva artefatos E1 e não roda E0-unlock/E0-audit. E-full-reset move **todos** os arquivos de `data/` e `members/` de volta para `inbox/`, permitindo re-roteamento completo, e re-executa **todas** as etapas LLM (E1, E1.5, E2-llm, E7-review).

#### Modo interativo (recomendado)

O modo `--interactive` orquestra o pipeline completo automaticamente, parando apenas nas 3 etapas que realmente precisam de intervenção do agente LLM ("walls"). Etapas que antes eram classificadas como LLM mas são 100% determinísticas (E1.5c, E5.N, E7-crossval) agora rodam automaticamente.

**Sequência de execução:**

```
Fase 0: Move inbox + unlock + audit + route (automático)
  ↓
WALL 1: [E1 + E1.5] — agente extrai dados de membros + baseline IRPF
  ↓ --continue
E1.5c (automático) → ...
  ↓
WALL 2: [E2-llm] — agente extrai investimentos/CDBs sem parser
  ↓ --continue
E2-fat → E2-ext → E3 → E4 → E5 → E5.N → E6 → E7-crossval (automático)
  ↓
WALL 3: [E7-review] — agente preenche template de review holístico
  ↓ --continue
E7-apply → E6-final → Validação (automático) → PIPELINE COMPLETO
```

**Comandos:**

```bash
# Passo 1: Iniciar pipeline interativo
python scripts/e_reset.py --move-to-inbox --interactive --dry-run  # Preview
python scripts/e_reset.py --move-to-inbox --interactive            # Executa até Wall 1

# Passo 2: Agente LLM executa E1 + E1.5 (mapeamento de membros + baseline IRPF)
# ... (criar members/*-1a_extract.json, members-1b_unified.json, baseline_patrimonial, etc.)

# Passo 3: Retomar — roda E1.5c, para na Wall 2
python scripts/e_reset.py --continue

# Passo 4: Agente LLM executa E2-llm (investimentos, CDBs, IRPF sem parser)
# ... (criar processed/E2_extracts/*-2_extract.json para tipos sem parser)

# Passo 5: Retomar — roda E2→E3→E4→E5→E5.N→E6→E7-crossval, para na Wall 3
python scripts/e_reset.py --continue

# Passo 6: Agente LLM preenche review template
# ... (ler processed/E7_review/e7_review_template.json, salvar em _scratch/e7_review_filled.json)

# Passo 7: Retomar — roda E7-apply + E6-final + validação → COMPLETO
python scripts/e_reset.py --continue
```

O state file (`_scratch/.e_reset_state.json`) rastreia o progresso entre invocações. É limpo automaticamente ao completar o pipeline.

Exit code 10 = pipeline pausado em wall LLM (não é erro).

> **Nota:** Se desejar preservar o estado atual antes do full-reset, execute `python scripts/e_save.py -m "pre-full-reset: snapshot [DATA]"` manualmente antes do Passo 1.

#### Modo manual (legado)

Para execução manual passo-a-passo sem o modo interativo:

**Passo 1 — Mover arquivos de data/ e members/ → inbox/ (re-roteamento):**
```bash
python scripts/e_reset.py --move-to-inbox --dry-run   # Preview: listar o que seria movido
python scripts/e_reset.py --move-to-inbox --clean-only # Executar: mover + limpar artefatos (sem re-executar pipeline)
```
> **Nota:** Se desejar preservar o estado atual antes do full-reset, execute `python scripts/e_save.py -m "pre-full-reset: snapshot [DATA]"` manualmente antes deste passo.
O script move todos os arquivos de `data/` (financial_statements, income_tax_br, etc.) e os originais de `members/` (`*-0_original.*`) de volta para `inbox/`. Artefatos E1 em `members/` (extract, unified, enriched) são removidos. A estrutura de diretórios em `data/` é preservada (vazia).

**Passo 2 — E0-unlock: Verificar e desbloquear PDFs encriptados + descompactar ZIPs:**
```bash
python scripts/e0_unlock.py --dry-run          # Preview: listar status de todos os PDFs e ZIPs
python scripts/e0_unlock.py                     # Executar: desbloquear PDFs + extrair ZIPs no inbox
```
Se PDFs encriptados forem encontrados sem senha válida, registra em `qa_log.md` e move para `nao_identificados/`.
ZIPs extraídos com sucesso são movidos para `inbox_processed/`; conteúdo extraído fica no inbox para roteamento.

**Passo 3 — E0-audit: Auditoria de integridade:**
```bash
python scripts/e0_audit.py
```
Analisar o relatório. As 7 checagens são:
1. Filename vs JSON content mismatch
2. Arquivos órfãos
3. Possíveis duplicatas
4. Cross-reference inbox_log.md
5. Gaps de saldo no E3
6. *(reservada)*
7. Colisão de nomes (severity ERROR — bloqueia continuação)

**Se houver ERRORs:** corrigir antes de prosseguir. Erros de colisão de nomes se propagam por todo o pipeline.
**Se apenas WARNs:** registrar em `qa_log.md` e prosseguir com cautela.

**Passo 4 — E0: Roteamento de TODOS os arquivos do inbox/:**
Agora que todos os arquivos estão de volta no `inbox/`:
- Executar o algoritmo de detecção (Seção 3.1) para **cada** arquivo
- Verificar tamanho (Passo 8a) e encriptação (Passo 8b)
- Copiar para `inbox_processed/[DATA]/` e mover para `data/`
- Atualizar `logs/inbox_log.md`

**Passo 5 — Etapas LLM pré-extração (execução manual, nesta ordem):**

| Ordem | Etapa | O que fazer | Artefatos gerados |
|---|---|---|---|
| 5a | **E1** | Mapeamento de membros (currículos, docs pessoais) | `members/*-1a_extract.json`, `members-1b_unified.json` |
| 5b | **E1.5** | Baseline patrimonial (IRPF, XLSX imóveis/veículos) | `members-1c_enriched.md`, `E2_extracts/*-1.5_*.json` |
| 5c | **E2-extratos-llm** | Extração LLM de investimentos, CDBs, informes (apenas tipos sem parser determinístico) | `E2_extracts/*-2_extract.json` |

> **Nota (v5.5):** Extratos bancários (conta corrente, poupança, global, PJ) agora são processados deterministicamente no Passo 6. A etapa 5c é apenas para tipos sem parser: `investimentosposicao`, `carteirarendafixa`, `cdbdetalhes`, `cdbresumo`, `informerendimentos`, `irpf`.

**Passo 6 — Etapas determinísticas completas (E2-faturas + E2-extratos + E3→E6):**
```bash
python scripts/e2_extract.py                        # E2 unificado (extratos + faturas + CDBs)
python scripts/e2_extract.py --faturas-only          # E2 apenas faturas
python scripts/e2_extract.py --extratos-only         # E2 apenas extratos
python scripts/e_reset.py --from E3                 # Cascata E3→E4→E5→E6
```
O script unificado `e2_extract.py` é 100% determinístico, com validation gate que rejeita extrações com 0 transações quando o PDF contém texto significativo.

**Passo 7 — Narrativas e render inicial:**

| Ordem | Etapa | O que fazer | Artefatos gerados |
|---|---|---|---|
| 7a | **E5.N** | Narrativas analíticas (`python scripts/e5n_narrativas.py` — determinístico) | Chave `narrativas` nos JSONs E5 |
| 7b | **E6 render** | `python scripts/e6_render.py` | `output/*.html` (versão pré-review) |

**Passo 8 — E7: Review holístico pós-relatório:**

Após o primeiro render do relatório, a LLM realiza uma revisão holística usando a persona e abordagem definidas em `config/methodology.md`. Esta etapa retroalimenta as narrativas geradas, detectando inconsistências entre seções e refinando textos, análises, cards, lista de tarefas e prioridades.

| Ordem | Etapa | O que fazer | Artefatos gerados |
|---|---|---|---|
| 8a | **E7 cross-validation** | `python scripts/e7_review.py` (determinístico) | `processed/E7_review/e7_review_template.json` |
| 8b | **E7 review (LLM)** | LLM lê template + relatório HTML + methodology.md, preenche refinamentos | Review JSON (`_scratch/e7_review_filled.json`) |
| 8c | **E7 apply** | `python scripts/e7_review.py --apply _scratch/e7_review_filled.json` | E5 JSON atualizado com refinamentos + metadata |
| 8d | **E6-final render** | `python scripts/e6_render.py` | `output/*.html` (versão final refinada) |

O sub-passo 8a executa 14 verificações determinísticas de consistência (score formula, patrimônio composition, fluxo aritmética, taxa poupança, IF coherence, etc.). Qualquer falha é reportada para a LLM corrigir durante o review.

No sub-passo 8b, a LLM utiliza a persona de "Consultor financeiro especialista em independência financeira" para:
- Detectar contradições entre seções (ex: fluxo de caixa diz "poupança saudável" mas IF diz "ritmo insuficiente")
- Refinar narrativas com visão holística do relatório completo
- Re-priorizar tarefas baseado em insights que emergem da visão completa
- Gerar insights estratégicos que não ficaram claros nas análises individuais

> **Nota:** O E7 é limitado a uma única passagem de review (sem recursão) para evitar loops. Se refinamentos significativos forem necessários, rodar `python scripts/e_reset.py --from E7` para repetir.

**Passo 9 — Validação final:**
- Executar checklist V1–V19 do E6 (Seção 4, STAGE E6)
- Comparar com relatório anterior via `git diff` para confirmar que não houve perda de dados
- Verificar que `e0_audit.py` não reporta novos ERRORs:
```bash
python scripts/e0_audit.py
```

**Resumo de tempo estimado:**

| Fase | Tipo | Tempo estimado |
|---|---|---|
| Move data/+members/ → inbox/ | Determinístico | ~5s |
| E0-unlock + E0-audit + E0-route | Determinístico | ~10s |
| E1 + E1.5 (LLM) | LLM — Wall 1 | ~5–10 min |
| E1.5c consolidate | Determinístico | ~1s |
| E2-llm (investimentos, CDBs, IRPF) | LLM — Wall 2 | ~3–5 min |
| E2-faturas + E2-extratos + E3→E5 | Determinístico | ~60s |
| E5.N narrativas + E6 render | Determinístico | ~30s |
| E7-crossval | Determinístico | ~5s |
| E7-review (LLM) | LLM — Wall 3 | ~5 min |
| E7-apply + E6-final render | Determinístico | ~15s |

---

### STAGE E-save — Commit e push para remote (EXCLUSIVAMENTE MANUAL)

**Execução:** `python scripts/e_save.py -m "mensagem"` | Flags: `--dry-run` (preview), `--no-push` (commit local)

**⚠️ REGRA ABSOLUTA: E-save é a ÚNICA forma de fazer commit/push neste projeto.**
- Nenhum outro script do pipeline (E0 a E7, E-reset, E-reset-from, E-full-reset) faz `git add`, `git commit` ou `git push`.
- E-save NUNCA é chamado automaticamente por outro script.
- E-save só é executado quando o operador (humano ou LLM) invoca explicitamente o comando.
- O assistente (LLM) NÃO deve executar E-save por conta própria — apenas quando o usuário solicitar.

**Quando usar:**
- Após qualquer execução bem-sucedida do pipeline (E1→E6, E-reset, E-reset-from, E-full-reset)
- Após edição significativa de configs (manual, definitions, methodology, milhas, etc.)
- Após correção de bugs em scripts ou templates
- Em qualquer momento que o estado atual represente um "ponto bom" que vale preservar
- Antes de operações destrutivas (reset, full-reset) se desejar preservar o estado atual

**Pré-condição:** Alterações já feitas e validadas. Não executar E-save com trabalho incompleto ou erros conhecidos.

**O script faz automaticamente:**
1. Verifica que está dentro do repositório Git
2. Valida a mensagem de commit contra a convenção de prefixos (Seção 4.5.3)
3. Lista arquivos alterados no console
4. Safety check: bloqueia se detectar arquivos em `data/`, `inbox/` ou `inbox_processed/` (proteção redundante ao `.gitignore`)
5. `git add -A` (staging)
6. `git commit -m "[mensagem]"`
7. `git push origin main` (a menos que `--no-push`)
8. Mostra os últimos 3 commits para confirmação

**Exemplos de uso:**

```bash
# Após pipeline completo
python scripts/e_save.py -m "pipeline: ciclo mar/2026 — relatório gerado"

# Após alteração em config (sem push, só commit local)
python scripts/e_save.py -m "config: definitions.md — nova keyword restaurante" --no-push

# Preview: ver o que seria comitado sem alterar nada
python scripts/e_save.py -m "docs: manual v4.8 — comando E-save" --dry-run

# Após correção em script
python scripts/e_save.py -m "fix: e4_categorize.py — normalização acentos"

# Após reprocessamento parcial
python scripts/e_save.py -m "pipeline: re-run E3→E6 — novas regras categorização"
```

**Convenção de mensagens (prefixos válidos):**

| Situação | Prefixo | Exemplo |
|---|---|---|
| Pipeline executado | `pipeline:` | `pipeline: ciclo mar/2026 — relatório gerado` |
| Alteração em config | `config:` | `config: definitions.md — nova keyword` |
| Atualização do manual | `docs:` | `docs: manual v4.8 — comando E-save` |
| Correção em script | `fix:` | `fix: e4_categorize.py — normalização` |
| Arquivo atualizado | `update:` | `update: david_curriculo — CV atualizado` |
| Pré-substituição | `pre-update:` | `pre-update: david_curriculo antes de substituição` |
| Re-extração | `E2:` | `E2: re-extração C6 jan-mar/26` |
| Refatoração | `refactor:` | `refactor: extrair helpers comuns` |

> **Se o push falhar** por divergência com o remote, o script orienta: `git pull --rebase origin main` e depois rodar E-save novamente.

---

## SEÇÃO 4.5 — VERSIONAMENTO COM GIT

O pipeline usa Git como sistema de controle de versão. Todos os arquivos de texto (configs, JSONs processados, scripts, logs, templates, relatórios) são versionados. Arquivos binários financeiros originais (PDFs, imagens em `data/`) são excluídos via `.gitignore`.

### 4.5.1 — O que está no Git (e o que não está)

| No Git | Fora do Git (.gitignore) |
|---|---|
| `config/` (manual, definitions, methodology, etc.) | `data/` (PDFs originais ~21MB, imutáveis) |
| `processed/` (JSONs E2-E4) | `inbox/` (arquivos temporários em trânsito) |
| `output/` (relatório HTML atual) | `inbox_processed/` (auditoria de entrada) |
| `logs/` (inbox_log, run_log, qa_log, etc.) | `.DS_Store`, `.obsidian/` |
| `scripts/` (e3_reconcile.py, e4_categorize.py, e5_analyze.py, e6_render.py, e6_regen.py, e_reset.py, e_save.py) | `*.bak`, `*_backup.*`, `*_prev.*` |
| `members/` (currículos, documentos pessoais) | |
| `life_plan/` | |

### 4.5.2 — Fluxo padrão: salvar estado via E-save

**REGRA: Nenhuma etapa do pipeline (E0 a E7, E-reset, E-reset-from, E-full-reset) faz commit ou push automaticamente.** Commits e pushes são realizados EXCLUSIVAMENTE pelo operador (humano ou LLM) invocando manualmente:

```bash
python scripts/e_save.py -m "mensagem"
```

Quando desejar preservar o estado antes de uma operação destrutiva (reset, sobrescrita de arquivo), execute E-save manualmente antes de prosseguir.

### 4.5.3 — Convenção de mensagens de commit

| Situação | Exemplo de mensagem |
|---|---|
| Relatório gerado (E6) | `E6: relatório 2026-04-04` |
| Regeneração de template (E6-regen) | `E6-regen: novo layout aplicado` |
| Arquivo atualizado (Seção 5.1) | `update: david_curriculo — CV atualizado` |
| Pré-substituição | `pre-update: david_curriculo antes de substituição` |
| Re-extração após novo extrato | `E2: re-extração C6 jan-mar/26` |
| Correção no template | `fix: template — ajuste CSS gráfico receita` |
| Alteração no manual | `docs: manual v3.1 — migração para Git` |

### 4.5.4 — Recuperar versão anterior

```bash
# Ver histórico de um arquivo
git log --oneline -- output/relatorio_financeiro_ferreira_campos_20260404.html

# Restaurar uma versão anterior para inspeção
git show <hash>:output/relatorio_financeiro_ferreira_campos_20260404.html > /tmp/versao_anterior.html

# Comparar duas versões
git diff <hash1> <hash2> -- processed/E5_analysis/analise_financeira-5_analysis.json
```

### 4.5.5 — Segurança

- O `.gitignore` garante que PDFs financeiros e dados sensíveis **nunca** entrem no Git
- Se o repositório for hospedado no GitHub, usar **repositório privado**
- O `e_save.py` inclui safety check automático que bloqueia commit de arquivos em `data/`, `inbox/` e `inbox_processed/`

---

## SEÇÃO 5 — TRATAMENTO DE ARQUIVOS ATUALIZADOS (Incremental Updates)

Quando um arquivo existente é substituído por versão nova, seguir este protocolo:

### 5.1 — Versionamento de arquivo

Quando arquivo com mesmo nome chega no inbox (e.g., novo `david_curriculo-0_original.docx`):

1. **(Opcional) Salvar estado atual via E-save:**
   Se desejar preservar o estado antes da substituição, execute manualmente:
   ```bash
   python scripts/e_save.py -m "pre-update: david_curriculo antes de substituição por versão nova"
   ```

2. **Sobrescrever com o novo arquivo:**
   ```bash
   cp financas-familia/inbox/[nome_novo] \
      financas-familia/members/david_curriculo-0_original.docx
   ```

3. **Re-executar etapa relevante:**
   - Se currículo → re-executar E1
   - Se holerite → re-executar E1
   - Se IRPF → re-executar E1.5
   - Se XLSX imóvel/veículo → re-executar E1.5
   - Se extrato de conta → re-executar E2

> **Nota:** Para recuperar a versão anterior: `git log --oneline -- members/david_curriculo-0_original.docx` e depois `git show <hash>:members/david_curriculo-0_original.docx > versao_anterior.docx`

---

### 5.2 — Sobreposição de dados (mesmo período, arquivos novos)

Quando extratos novos chegam para períodos já processados (e.g., novo extrato C6 para jan-mar/26):

1. **Detectar sobreposição:**
   - Comparar período do novo arquivo com extratos já existentes
   - Se overlapping → marcar para reconciliação

2. **Executar E2 novamente:**
   - Extrair do novo arquivo

3. **Executar E3 novamente:**
   - Reconciliar com novo conjunto de transações
   - Detectar duplicatas por data+valor+descrição
   - Manter apenas novas transações

4. **Executar E4 novamente:**
   - Re-categorizar com novo conjunto de transações
   - Gerar novos -4_unified.json

5. **Registrar em reconciliation.md:**
   ```markdown
   | Data | Conta | Arquivo novo | Período | Duplicatas | Novas transações |
   |---|---|---|---|---|---|
   | [data] | c6bank_global_usd | c6bank_extratocontaglobalusd_202602_202603_updated.pdf | 202601_202603 | 47 | 3 |
   ```

---

### 5.3 — Novos tipos de documento nunca vistos antes

Quando um arquivo de tipo completamente novo chega (e.g., primeira planilha de veículos):

1. **Analisar e classificar:**
   - Verificar nome + conteúdo
   - Adicionar novo tipo à tabela de detecção (Seção 3)
   - Rotar para diretório apropriado

2. **Executar E1.5 novamente:**
   - Extrair dados do novo tipo
   - Incorporar em baseline patrimonial
   - Possível impacto em E3/E4 se patrimônio mudar

3. **Registrar em qa_log:**
   ```markdown
   | [DATA] | Novo tipo de documento | dados_veiculos-0_original.xlsx | Detectado e rotado para data/vehicles/ |
   ```

---

## SEÇÃO 6 — LEITURA DE ARQUIVOS

Este manual é auto-contido e permite execução sem memória prévia. Para isso, aqui estão as instruções explícitas para ler cada tipo de arquivo:

### 6.1 — Leitura de PDFs

**Ferramenta:** Use um leitor de PDF que extrai texto fidedignamente.

**Método:**
1. Abrir PDF em leitor nativo (Adobe Reader, Chrome, Python pdfplumber)
2. Navegar por cada página
3. Extrair tabelas manualmente ou com OCR (se necessário)
4. Preservar estrutura: valores monetários, datas, nomes, descritivos

**NÃO descomprimir PDFs como ZIPs** — eles são documentos legítimos.

### 6.2 — Leitura de XLSX

**Ferramenta:** Use um leitor de planilhas (Excel, Google Sheets, Python openpyxl).

**Método:**
1. Abrir XLSX em leitor nativo
2. Verificar todas as abas (não apenas a primeira)
3. Extrair cabeçalhos de coluna
4. Extrair dados linha por linha
5. Preservar tipos: datas como datas, moedas como moeda

**Para E1.5 (IRPF):**
Se IRPF for em formato XLSX (alguns órgãos disponibilizam), seguir método acima.

### 6.3 — Leitura de DOCX

**Ferramenta:** Use leitor de DOCX (Word, Google Docs, Python python-docx).

**Método:**
1. Abrir DOCX
2. Extrair texto preservando estrutura (parágrafos, listas, tabelas)
3. Se houver tabelas, extrair como estruturado

### 6.4 — Leitura de JPG (OCR)

**Ferramenta:** Use OCR (Tesseract, Google Vision, Claude Vision).

**Método:**
1. Carregar imagem
2. Aplicar OCR
3. Extrair texto
4. Se OCR falhar parcialmente, registrar em qa_log.md com página e razão

---

## SEÇÃO 7 — JSON SCHEMAS PARA -2_EXTRACT.JSON

Cada -2_extract.json deve seguir um schema específico. Aqui estão os schemas esperados para cada tipo de documento:

### 7.1 — Banco de dados de padrões

**Extrato de conta corrente:**
```json
{
  "tipo": "extratoconta",
  "instituicao": "[banco]",
  "conta": {
    "numero": "[número]",
    "tipo": "corrente | poupança | pj",
    "moeda": "BRL | USD | EUR",
    "agencia": "[agência]"
  },
  "periodo": {
    "data_inicio": "YYYY-MM-DD",
    "data_fim": "YYYY-MM-DD"
  },
  "saldos": {
    "saldo_inicial": { "valor": 0.00, "data": "YYYY-MM-DD" },
    "saldo_final": { "valor": 0.00, "data": "YYYY-MM-DD" }
  },
  "transacoes": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "[descrição conforme documento]",
      "tipo": "débito | crédito",
      "valor": 0.00,
      "saldo_apos": 0.00
    }
  ],
  "total_periodo": {
    "total_debitos": 0.00,
    "total_creditos": 0.00,
    "saldo_liquido": 0.00
  }
}
```

**Fatura de cartão de crédito (C6, Santander, Itaú):**

> **Nota (v4.9.1+):** Schema atualizado para refletir o output real de `e2_extract.py`.
> Campos `forex`, `tipo_lancamento`, `cartoes`, `compras_parceladas_futuras` e `parse_quality` são opcionais.
> O campo `pagamentos` é SEMPRE negativo por convenção (reduz saldo da fatura).
> Se o LLM processar faturas fallback, deve gerar JSON neste formato (não no formato antigo com `instituicao`/`resumo`).

```json
{
  "banco": "C6 Bank | Santander | Itaú",
  "tipo": "faturacarbon | faturaunique | faturapaoacucar",
  "cartao": "Carbon | Unique | Pão de Açúcar",
  "titular": "NOME COMPLETO DO TITULAR",
  "moeda": "BRL",
  "data_vencimento": "YYYY-MM-DD",
  "saldo_anterior": 0.00,
  "total_compras_nacionais": 0.00,
  "total_compras_internacionais": 0.00,
  "total_compras": 0.00,
  "pagamentos": -0.00,
  "saldo_atual": 0.00,
  "limite_total": 0.00,
  "parse_quality": "ok | empty_result | missing_transactions",
  "transacoes": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "[conforme documento]",
      "valor": 0.00,
      "cartao": "[identificação do cartão/titular]",
      "parcela": "3/12",
      "forex": {
        "moeda_original": "USD | EUR",
        "valor_original": 0.00,
        "cotacao": 0.00
      },
      "tipo_lancamento": "iof"
    }
  ],
  "cartoes": [
    { "cartao": "[nome]", "subtotal": 0.00 }
  ],
  "compras_parceladas_futuras": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "[estabelecimento]",
      "valor": 0.00,
      "cartao": "[titular (final NNNN)]",
      "parcela": "2/12"
    }
  ]
}
```

**Fatura de aluguel (QuintoAndar):**

```json
{
  "banco": "QuintoAndar",
  "tipo": "faturaaluguel",
  "propriedade": "[nome curto da propriedade]",
  "moeda": "BRL",
  "periodo_referencia": "YYYY-MM",
  "total_recebido": 0.00,
  "data_recebimento": "YYYY-MM-DD",
  "endereco": "[endereço completo]",
  "parse_quality": "ok | empty_result",
  "itens": [
    { "descricao": "[item discriminado]", "valor": 0.00 }
  ]
}
```

**Posição de investimentos:**
```json
{
  "tipo": "investimentosposicao",
  "instituicao": "[instituição]",
  "data_posicao": "YYYY-MM-DD",
  "moeda": "BRL | USD",
  "total_aplicado": 0.00,
  "saldo_atual": 0.00,
  "rentabilidade": {
    "valor": 0.00,
    "percentual": 0.00
  },
  "composicao": [
    {
      "tipo_produto": "ação | fundo | título | CDB | cripto | outro",
      "nome": "[nome]",
      "quantidade": 0.00,
      "valor_unitario": 0.00,
      "valor_total": 0.00,
      "percentual_carteira": 0.00,
      "rentabilidade_instrumento": 0.00
    }
  ]
}
```

**Declaração IRPF:**
```json
{
  "tipo": "irpfdeclaracao",
  "ano_base": 2024,
  "declarante": {
    "nome": "[nome]",
    "cpf": "XXX.XXX.XXX-XX"
  },
  "data_declaracao": "YYYY-MM-DD",
  "bens_direitos": [
    {
      "tipo": "imovel | veiculo | acao | criptoativo | conta_bancaria | aplicacao | empresa | outro",
      "descricao": "[descrição]",
      "valor_31_12_ano_anterior": 0.00,
      "valor_31_12_ano_base": 0.00,
      "localidade": "[localidade se aplicável]"
    }
  ],
  "rendimentos": [
    {
      "tipo": "pj | clt | aluguel | financeiro | dividendo | outro",
      "valor_bruto": 0.00,
      "valor_liquido": 0.00,
      "fonte": "[fonte]"
    }
  ],
  "dívidas_ônus": [
    {
      "tipo": "financiamento | emprestimo | outro",
      "descricao": "[descrição]",
      "valor": 0.00
    }
  ],
  "deducoes": [
    {
      "tipo": "saude | educacao | previdencia | outro",
      "valor": 0.00
    }
  ],
  "totalizadores": {
    "bens_totais": 0.00,
    "renda_tributavel": 0.00,
    "imposto_devido": 0.00,
    "imposto_pago": 0.00,
    "saldo": 0.00
  }
}
```

**Dados de imóveis (XLSX):**
```json
{
  "tipo": "dados_imoveis",
  "imoveis": [
    {
      "endereco": "[endereço completo]",
      "localidade": "[cidade, estado]",
      "data_compra": "YYYY-MM-DD",
      "valor_compra": 0.00,
      "vendedor": "[nome]",
      "financiamento": {
        "banco": "[banco]",
        "juros_ano": 0.00,
        "prazo_meses": 0,
        "valor_financiado": 0.00,
        "valor_entrada": 0.00
      },
      "situacao_atual": "proprio | alugado | venda | outro",
      "observacoes": "[anotações]"
    }
  ]
}
```

**Dados de veículos (XLSX):**
```json
{
  "tipo": "dados_veiculos",
  "veiculos": [
    {
      "marca": "[marca]",
      "modelo": "[modelo]",
      "ano": 2024,
      "placa": "[placa]",
      "data_aquisicao": "YYYY-MM-DD",
      "valor_aquisicao": 0.00,
      "situacao": "proprio | financiado",
      "financiamento": {
        "banco": "[banco]",
        "juros": 0.00,
        "prazo_meses": 0,
        "valor_financiado": 0.00
      },
      "observacoes": "[anotações]"
    }
  ]
}
```

**Documento pessoal (RG, CPF, Passaporte, etc.):**
```json
{
  "tipo": "rg | cpf | passaporte | visto | certidao_nascimento | certidao_casamento | ssn | drivers_license | green_card",
  "membro": "[nome do membro]",
  "numero": "[número do documento]",
  "data_emissao": "YYYY-MM-DD",
  "data_validade": "YYYY-MM-DD | null",
  "dados_demograficos": {
    "nome_completo": "[nome]",
    "data_nascimento": "YYYY-MM-DD",
    "naturalidade": "[localidade]",
    "nacionalidade": "[país]"
  },
  "status": "válido | vencido | pendente",
  "observacoes": "[anotações]"
}
```

**Baseline patrimonial consolidado:**
```json
{
  "tipo": "baseline_patrimonial",
  "data_consolidacao": "YYYY-MM-DD",
  "membros": [
    {
      "nome": "[nome]",
      "cpf": "XXX.XXX.XXX-XX",
      "ano_base": 2024,
      "bens": {
        "imoveis": [
          {
            "descricao": "[endereço]",
            "valor_irpf": 0.00,
            "valor_compra": 0.00,
            "data_compra": "YYYY-MM-DD",
            "fonte": "irpf | xlsx | ambos"
          }
        ],
        "veiculos": [
          {
            "descricao": "[marca modelo]",
            "valor_irpf": 0.00,
            "valor_aquisicao": 0.00,
            "data_aquisicao": "YYYY-MM-DD"
          }
        ],
        "investimentos": [
          {
            "tipo": "[tipo]",
            "valor": 0.00
          }
        ],
        "criptos": 0.00,
        "contas_bancarias": 0.00,
        "outros": 0.00
      },
      "total_bens": 0.00,
      "dividas": 0.00,
      "patrimonio_liquido": 0.00,
      "divergencias": [
        {
          "descricao": "[descrição]",
          "tipo": "imovel_não_irpf | imovel_não_xlsx | valor_discrepante",
          "detalhes": "[detalhes]"
        }
      ]
    }
  ]
}
```

### 7.2 — Schemas adicionais (E1, E3, E4)

**Currículo (`[membro]_curriculo-1a_extract.json`):**

Chaves obrigatórias: `tipo`, `membro`, `nome_completo`, `nome_atual`, `profissao_cargo`, `experiencias` (≥1), `formacao` (≥1), `idiomas` (≥1).

```json
{
  "tipo": "curriculo",
  "membro": "david | mariana",
  "nome_completo": "[nome como aparece no documento — pode ser solteiro ou casado]",
  "nome_atual": "[nome atual completo, do definitions.md]",
  "profissao_cargo": "[cargo principal atual]",
  "experiencias": [
    {
      "empresa": "[nome da empresa]",
      "cargo": "[título do cargo]",
      "tipo_vinculo": "PJ | CLT | freelance | docencia",
      "data_inicio": "YYYY-MM",
      "data_fim": "YYYY-MM | presente",
      "descricao": "[resumo 1-2 frases, pode ser vazio]"
    }
  ],
  "formacao": [
    {
      "instituicao": "[nome da instituição]",
      "curso": "[nome do curso]",
      "grau": "graduacao | pos_graduacao | especializacao | mestrado | doutorado | certificacao",
      "data_conclusao": "YYYY"
    }
  ],
  "certificacoes": [
    {
      "nome": "[nome da certificação]",
      "instituicao": "[entidade emissora, se disponível]"
    }
  ],
  "habilidades": ["[habilidade1]", "[habilidade2]"],
  "idiomas": [
    {
      "idioma": "[Português | Inglês | ...]",
      "nivel": "nativo | fluente | avancado | intermediario | basico",
      "fonte": "documento | inferido"
    }
  ]
}
```

> **Nota:** Se o currículo não listar idiomas, inferir nativo a partir do idioma do documento (ex: PT-BR → `{"idioma": "Português", "nivel": "nativo", "fonte": "inferido"}`). Overlaps de datas entre experiências são válidos — não ajustar.

---

**Holerite (`[membro]_holerite_[período]-1a_extract.json`):**

Chaves obrigatórias: `tipo`, `membro`, `nome_no_documento`, `periodo`, `empresa`, `cargo`, `salario_bruto`, `descontos`, `total_descontos`, `salario_liquido`.

```json
{
  "tipo": "holerite",
  "membro": "david | mariana",
  "nome_no_documento": "[nome exato como consta no holerite — pode ser nome de solteira]",
  "periodo": "YYYY-MM",
  "empresa": "[nome do empregador]",
  "estabelecimento": "[unidade/filial, se disponível]",
  "cargo": "[cargo formal]",
  "categoria": "[categoria funcional, se disponível]",
  "grade": "[grade/nível, se disponível — ex: P4]",
  "matricula": "[ID do funcionário, se disponível]",
  "data_admissao": "YYYY-MM-DD",
  "salario_base_mensal": 0.00,
  "salario_bruto": 0.00,
  "proventos_adicionais": [
    {
      "codigo": "[código, se disponível]",
      "descricao": "[descrição do provento]",
      "valor": 0.00
    }
  ],
  "descontos": [
    {
      "codigo": "[código, se disponível]",
      "descricao": "INSS | IRRF | adiantamento | seguro_vida | refeicao | ferias | outro",
      "valor": 0.00
    }
  ],
  "total_descontos": 0.00,
  "salario_liquido": 0.00,
  "data_credito": "YYYY-MM-DD (se disponível)",
  "fgts": {
    "base": 0.00,
    "depositado": 0.00
  },
  "inss_base": 0.00,
  "dependentes_ir": 0,
  "observacoes": "[notas relevantes — férias no período, 13º, adiantamento, etc.]"
}
```

> **Nota:** `nome_no_documento` pode diferir do `nome_atual` do membro (ex: holerite Einstein usa nome de solteira "Mariana Teixeira Ferreira"). O mapeamento nome→membro é feito pela tabela NOMES do `definitions.md`, não pelo nome no documento. Um arquivo por holerite, com período no nome do arquivo.

---

**Members unified (`members-1b_unified.json`):**

Chaves obrigatórias por membro: `id`, `nome_atual`, `papel_familia`, `documentos_disponiveis`. Demais campos podem ser `null` se não houver fonte.

```json
{
  "tipo": "members_unified",
  "data_geracao": "YYYY-MM-DD",
  "fonte_definitions": true,
  "membros": [
    {
      "id": "david | mariana | theo",
      "nome_atual": "[nome atual completo — casado — do definitions.md]",
      "nomes_alternativos": ["[nome de solteiro]", "[nome fiscal]", "[nome no currículo se diferir]"],
      "cpf": "XXX.XXX.XXX-XX (de definitions.md, ou null se não disponível)",
      "data_nascimento": "YYYY-MM-DD (de definitions.md)",
      "papel_familia": "Titular | Cônjuge | Filho",
      "empregador_atual": "[nome da empresa ou null]",
      "cargo_atual": "[cargo ou null]",
      "tipo_vinculo": "PJ | CLT | null",
      "data_admissao": "YYYY-MM-DD ou null",
      "formacao_maxima": "[descrição da formação mais alta]",
      "idiomas": [
        {"idioma": "...", "nivel": "...", "fonte": "documento | inferido"}
      ],
      "experiencias": [
        {
          "empresa": "...",
          "cargo": "...",
          "tipo_vinculo": "PJ | CLT | docencia | freelance",
          "data_inicio": "YYYY-MM",
          "data_fim": "YYYY-MM | presente"
        }
      ],
      "salario": {
        "bruto": 0.00,
        "liquido": 0.00,
        "periodo_referencia": "YYYY-MM",
        "fonte": "holerite | extrato | estimativa",
        "nota": "[explicação se líquido atípico — férias, adiantamento, etc.]"
      },
      "documentos_disponiveis": ["curriculo", "holerite", "rg", "cpf"],
      "status_fiscal": "BR | US | BR+US",
      "observacoes": "[notas relevantes]"
    }
  ]
}
```

> **Nota:** Membros sem documentos (ex: Theo) são incluídos com dados do `definitions.md` e campos sem fonte = `null`. A lista de `membros` deve conter **todos** os membros do `definitions.md`, nunca menos.

---

**Seguros (-4_unified.json):**
```json
{
  "tipo": "seguros_unified",
  "periodo_referencia": "YYYY-MM a YYYY-MM",
  "seguros": [
    {
      "tipo_seguro": "vida | residencial | auto | saude | dental | viagem | responsabilidade_civil | outro",
      "seguradora": "[nome]",
      "membro_titular": "[nome]",
      "premio_mensal": 0.00,
      "premio_anual": 0.00,
      "cobertura_principal": "[descrição da cobertura]",
      "valor_cobertura": 0.00,
      "data_inicio_vigencia": "YYYY-MM-DD",
      "data_fim_vigencia": "YYYY-MM-DD",
      "situacao": "ativa | vencida | cancelada",
      "fonte": "holerite | fatura_cartao | irpf | documento_apolice",
      "observacoes": "[notas]"
    }
  ],
  "totais": {
    "premio_mensal_total": 0.00,
    "premio_anual_total": 0.00,
    "quantidade_seguros_ativos": 0
  }
}
```

**Análise financeira (-5_analysis.json):**
```json
{
  "tipo": "analise_financeira",
  "data_geracao": "YYYY-MM-DD",
  "periodo_dados": "YYYY-MM a YYYY-MM",

  "fluxo_caixa": {
    "receita_total": 0.00,
    "receita_recorrente": 0.00,
    "receita_one_time": 0.00,
    "receita_recorrente_mensal": 0.00,
    "despesa_total": 0.00,
    "despesa_recorrente_mensal": 0.00,
    "fluxo_liquido": 0.00,
    "receitas_por_fonte": {
      "pj": 0.00,
      "clt": 0.00,
      "alugueis": 0.00,
      "rendimentos_financeiros": 0.00,
      "outros": 0.00
    },
    "despesas_por_categoria": {
      "[categoria]": 0.00
    },
    "receita_despesa_mensal_detalhado": {
      "labels": ["mmm/YY", "..."],
      "receita_datasets": [
        {"label": "[Origem conforme categorization.json]", "data": [0.00, "..."]},
        "..."
      ],
      "despesa_datasets": [
        {"label": "[Categoria conforme definitions.md]", "data": [0.00, "..."]},
        "..."
      ],
      "totais_receita": [0.00, "..."],
      "totais_despesa": [0.00, "..."]
    }
  },

  "racios": {
    "taxa_poupanca_recorrente_pct": 0.0,
    "taxa_poupanca_total_pct": 0.0,
    "taxa_endividamento_pct": 0.0,
    "cobertura_despesas_meses": 0,
    "rentabilidade_pct": null,
    "aliquota_efetiva_ir_pct": 0.0
  },
  // REGRA rentabilidade_pct: DEVE ser calculado a partir de dados reais de performance
  // extraídos dos relatórios das corretoras (valor aplicado vs valor atual por ativo).
  // Se dados indisponíveis → null (NUNCA inventar/estimar).
  // Quando disponível → calcular retorno ponderado por valor de cada posição.
  // O relatório exibe "N/D" + alerta amarelo quando null.

  "patrimonio": {
    "bruto": 0.00,
    "liquido": 0.00,
    "investivel": 0.00,
    "dividas": 0.00,
    "imoveis_estimado": 0.00,
    "categorias": [
      {
        "nome": "Residência própria | Imóveis investimento | Investimentos David | Investimentos Mariana | Criptoativos | Caixa + Moeda Estrangeira | Veículos",
        "valor": 0.00,
        "pct_bruto": 0.0,
        "fonte": "[descrição da fonte]"
      }
    ],
    "evolucao": {
      "patrimonio_ano_anterior": 0.00,
      "patrimonio_atual": 0.00,
      "crescimento_pct": 0.0,
      "crescimento_contribuicoes": 0.00,
      "crescimento_rentabilidade": 0.00
    }
  },

  "goals": {
    "if_meta": 0.00,
    "if_trs": 0.0,
    "if_pct": 0.0,
    "if_gap": 0.00,
    "prazo_anos_realista": 0,
    "david_idade_if": 0,
    "renda_passiva": {
      "meta_mensal": 0.00,
      "atual_mensal": 0.00
    }
  },

  "orcamento_prospectivo": {
    "categorias": {
      "[categoria]": 0.00
    },
    "total": 0.00,
    "media_mensal": 0.00,
    "variacao_pct": 0.0,
    "legenda": "Média mensal dos gastos dos últimos {N} meses, por categoria. Use como referência para planejar o orçamento dos próximos meses. Compare cada categoria com o total e identifique onde há espaço para otimizar. Total de R$ {total}/mês = {pct}% da receita recorrente."
  },

  "score": {
    "valor": 0.0,
    "max": 10,
    "classificacao": "Crítico | Atenção | Regular | Bom | Excelente",
    "componentes": [
      {
        "nome": "[nome do componente]",
        "valor": 0.0,
        "peso": 0.0,
        "contribuicao": 0.0
      }
    ]
  },

  "consumo_consciente": {
    "itens": [
      {
        "descricao": "[descrição]",
        "conta_cartao": "[banco/cartão]",
        "mes": "YYYY-MM",
        "valor": 0.00,
        "categoria": "[viagem|investimento|saúde|educação|eletrônico|presente|outro]",
        "observacao": "[nota]"
      }
    ],
    "total_pontuais": 0.00,
    "equivalente_meses_aporte": 0.0,
    "folga_mensal": 0.00,
    "folga_pct": 0.0,
    "teto_sugerido": 0.00,
    "analise": "[texto livre de análise dos gastos pontuais]"
  },

  "diagnostico_comportamental": [
    {
      "padrao": "[nome do padrão]",
      "evidencia": "[texto com dados concretos]",
      "mudanca_sugerida": "[recomendação prática]"
    }
  ],

  "programa_milhas": {
    "programas": [
      {
        "programa": "[nome do programa]",
        "titular": "[nome do membro]",
        "saldo_pontos": 0,
        "valor_estimado_brl": 0,
        "economia_periodo_brl": 0
      }
    ],
    "total_valor_estimado_brl": 0,
    "total_economia_periodo_brl": 0,
    "total_pontos_resgatados": 0
  },

  "investimentos": {
    "contrafluxo": {
      "cenario_atual": "alta | queda | baixa",
      "selic_atual": 0.00,
      "selic_alta": "≥12%",
      "selic_queda": "8-12%",
      "selic_baixa": "<8%",
      "valor_cdi": 0.00,
      "valor_ipca": 0.00,
      "acao_pratica": "[texto personalizado baseado no cenário + status reserva emergência + valores de aporte]"
    }
  },

  "reserva_oportunidade": {
    "pre_requisito_ok": true,
    "meta_pct_patrimonio_investivel": 10.0,
    "meta_valor": 0.00,
    "saldo_atual": 0.00,
    "pct_atingido": 0.0,
    "status": "Montada | Parcial | Montar | Aguardando emergência",
    "composicao": [
      {
        "ativo": "[nome do ativo]",
        "valor": 0.00,
        "liquidez": "D+0 | D+1 | D+30 | D+90"
      }
    ],
    "quando_montar": "Após reserva de emergência coberta (nível conforto_9m)",
    "onde_manter": "CDB liquidez D+1 a D+90, Tesouro Selic (parcela excedente), fundos DI",
    "quando_usar": [
      "Queda de mercado > 15%",
      "Imóvel abaixo do preço de avaliação",
      "Desconto à vista > 10%",
      "Aporte tático em renda variável"
    ],
    "recomendacao": "[texto gerado]"
  },

  "tarefas": [
    {
      "n": 1,
      "t": "[título da tarefa]",
      "p": "alta | media | baixa",
      "e": "[explicação / contexto]"
    }
  ],
  "tarefas_status": {
    "1": "pendente | feito | vencido"
  },

  "alertas": [
    {
      "tipo": "critico | atencao | info",
      "titulo": "[título]",
      "descricao": "[detalhes]"
    }
  ]
}
```

---

## APÊNDICE A — DIAGRAMA VISUAL DO PIPELINE

```
                    Novos arquivos no inbox
                              |
                              v
                   [E0] ROTEAMENTO AUTOMÁTICO
                    (Detecção + Classificação)
                              |
                  ____________|____________
                 |            |           |
                 v            v           v
        Somente  +  IRPF/XLSX/  +  Somente
        extratos    CVs/Docs      novos
        de conta                  tipos
                 |            |           |
                 v            v           v
              [E2]       [E1.5]+[E2]   [E1.5]
            rápido      ciclo        detectar
                       completo
                 |            |           |
                 +____________|___________+
                              |
                              v
                        [E2] Extração
                  (Transações + Posições)
                              |
                              v
                       [E3] Reconciliação
                    (Duplicatas + Validação)
                              |
                              v
                       [E4] Enriquecimento
                    (Categorização + Unificação)
                              |
                              v
                     [E5 + E5.N] Análise
              (Rácios + Evolução + Narrativas)
                              |
                              v
                       [E6] Relatório
                       (HTML final)
                              |
                              v
                        output/relatorio.html
```

---

## APÊNDICE B — ROADMAP DE FEATURES FUTURAS

| Feature | Descrição | Impacto |
|---|---|---|
| **Integração bancária (API)** | Conectar direto com APIs de bancos para extração automática de extratos | Elimina manual upload de PDFs |
| **Reconciliação inteligente com IA** | Detectar categorização correta automaticamente usando ML | Reduz qa_log.md |
| **Projeções de cenários** | "E se eu economizar X a.a.?" | Complementa life_plan |
| **Integração com Declaração IRPF 2.0** | RFB iniciou plataforma digital — potencial integração | Baseline mais automatizado |
| **Suporte a criptomoedas (blockchain)** | Conectar com exchanges para posições reais | Complementa dados IRPF |
| **Comparativos com benchmarks** | Rácios vs. média Brasil/renda similar | Análise contextualizada |
| **Alertas automáticos** | "Alerta: despesa anormal com categoria X" | Monitoramento contínuo |

---

## APÊNDICE C — GLOSSÁRIO

| Termo | Definição |
|---|---|
| **Baseline patrimonial** | Snapshot completo de patrimônio e renda extrado de declarações IRPF + documentos cadastrais, servindo como referência para validar extratos |
| **Duplicata** | Transação que aparece em múltiplos extratos (períodos sobrepostos) — detectada por data+valor+descrição |
| **Enriquecimento** | Adição de contexto (categorização, fonte, data, membro responsável) a dados brutos |
| **Extração (-2_extract.json)** | Leitura fidedigna de um documento em JSON estruturado, sem categorização |
| **Reconciliação (-3_reconciled.json)** | Consolidação de múltiplos extratos de uma mesma conta, deduplicando períodos sobrepostos |
| **Unificação (-4_unified.json)** | Agregação de dados reconciliados por tipo (receita, despesa, etc.) com categorização completa |
| **Análise (-5_analysis.json)** | Derivação de métricas: fluxo, rácios, crescimento, alíquota, saúde vs. goals |
| **SMART CYCLE** | Detecção automática de tipos de arquivo → determinação de etapas necessárias (vs. ciclos fixos quinzenal/trimestral) |
| **Versionamento** | Salvar estado atual via `e_save.py` (manual) antes de substituir arquivo. Histórico acessível via `git log -- [caminho/do/arquivo]` |
| **Divergência** | Inconsistência detectada entre fontes (e.g., saldo IRPF vs. saldo extrato, imóvel em IRPF mas não em XLSX) |
| **QA Log** | Registro de itens não automatizáveis — requerem revisão/instrução manual antes de continuação |
| **Wall** | Ponto de parada no modo interativo (`--interactive`) onde o pipeline aguarda intervenção do agente LLM. Existem 3 walls: E1+E1.5, E2-llm, E7-review. Exit code 10 indica pausa em wall. |
| **Tombstone** | JSON vazio (`{}`) ou marcador de arquivo removido, usado pelo E3 para sinalizar que um arquivo reconciliado anterior foi invalidado |
| **Parse quality** | Campo de validação nos JSONs E2 (`ok`, `empty_result`, `missing_transactions`) que indica a qualidade da extração determinística |
| **Cascata** | Re-execução automática de etapas downstream quando uma etapa anterior é reprocessada. Ex: `--from E3` causa cascata E3→E4→E5→E5.N→E6 |
| **E-full-reset** | Reprocessamento nuclear do pipeline inteiro desde E0 até E6-final, incluindo re-roteamento de todos os arquivos e todas as etapas LLM |
| **State file** | Arquivo `_scratch/.e_reset_state.json` que rastreia o progresso do pipeline interativo entre invocações de `--continue` |
| **Determinístico** | Etapa 100% reproduzível via script Python, sem chamadas a LLM. Mesmos inputs = mesmos outputs |

---

## APÊNDICE D — ESTRUTURA FINAL DE DIRETÓRIOS

```
financas-familia/
├── inbox/                                 (arquivos chegam aqui)
├── inbox_processed/
│   └── [DATA-DE-HOJE]/                   (cópia de auditoria dos originais)
│       ├── nao_identificados/            (se houver)
│       └── [arquivos originais...]
├── config/
│   ├── methodology.md
│   ├── definitions.md
│   ├── decisions.md
│   ├── source_hierarchy.md
│   ├── report_spec.md
│   ├── templates/                        (novo em v3.0)
│   │   ├── definitions_template.md
│   │   ├── decisions_template.md
│   │   ├── methodology_template.md
│   │   ├── report_spec_template.md
│   │   └── source_hierarchy_template.md
│   └── manual_operacao.md                (v3.0: sem versão no filename)
├── members/
│   ├── david_curriculo-0_original.docx    (versões anteriores no histórico Git)
│   ├── mariana_curriculo-0_original.pdf
│   ├── mariana_holerite_202602-0_original.pdf
│   ├── david_rg-0_original.pdf           (quando chegar)
│   ├── [membro_documento-0_original.*]   (novos documentos pessoais)
│   ├── david_curriculo-1a_extract.json
│   ├── mariana_curriculo-1a_extract.json
│   ├── mariana_holerite-1a_extract.json
│   ├── [membro_documento-1a_extract.json]
│   ├── members-1b_unified.json
│   └── members-1c_enriched.md
├── life_plan/
│   └── life_plan_goals.md
├── data/
│   ├── financial_statements/             (todos os arquivos -0_original)
│   │   ├── [banco]_[tipo]_[período]-0_original.pdf
│   │   ├── [banco]_[tipo]_[período]-0_original.jpg
│   │   └── [novos arquivos conforme chegam]
│   ├── income_tax_br/                    (todos os arquivos -0_original)
│   │   ├── receitafederal_irpfdeclaracao_2024-0_original.pdf
│   │   ├── receitafederal_irpfdeclaracaomariana_2024-0_original.pdf
│   │   ├── quintoandar_informerendimentos*.pdf
│   │   └── [novos IRPF/informes conforme chegam]
│   ├── income_tax_us/                    (vazio no início, documentos US quando chegarem)
│   │   └── [formulários IRS, FBAR, W-2, etc]
│   ├── real_estate/                      (arquivo XLSX)
│   │   └── dados_imoveis-0_original.xlsx  (versões anteriores no histórico Git)
│   └── vehicles/                         (vazio no início, dados de veículos quando chegarem)
│       └── dados_veiculos-0_original.xlsx (quando primeiro chegar)
├── processed/
│   ├── E2_extracts/                      (outputs de E1.5 e E2)
│   │   ├── receitafederal_irpfdeclaracao_2024-2_extract.json
│   │   ├── [todos os -2_extract.json de cada documento]
│   │   ├── dados_imoveis-2_extract.json
│   │   ├── dados_veiculos-2_extract.json (quando E1.5 processar)
│   │   ├── baseline_patrimonial-1.5_consolidated.json
│   │   └── [múltiplos arquivos]
│   ├── E3_reconciled/                    (outputs de E3)
│   │   ├── itau_personnalite_pf_202505_202603-3_reconciled.json
│   │   ├── c6bank_global_usd_202505_202603-3_reconciled.json
│   │   ├── bradesco_conta_corrente_202501_202603-3_reconciled.json
│   │   ├── [um arquivo por conta identificada]
│   │   └── [tipicamente 8-12 arquivos]
│   ├── E4_unified/                       (outputs de E4)
│   │   ├── receitas-4_unified.json
│   │   ├── despesas-4_unified.json
│   │   ├── investimentos-4_unified.json
│   │   ├── patrimonio-4_unified.json
│   │   ├── seguros-4_unified.json
│   │   ├── pontos_milhas-4_unified.json
│   │   ├── fluxo_mensal_detalhado-4_unified.json
│   │   └── [exatamente 7 arquivos]
│   └── E5_analysis/                      (outputs de E5)
│       └── analise_financeira-5_analysis.json
├── output/
│   └── relatorio_financeiro_ferreira_campos_[DATE].html (E6 — versões anteriores no histórico Git)
├── logs/
│   ├── inbox_log.md                      (roteamento de todos os ciclos)
│   ├── run_log.md                        (execução de cada etapa)
│   ├── reconciliation.md                 (detalhes de deduplicação E3)
│   ├── divergences.md                    (inconsistências detectadas)
│   └── qa_log.md                         (itens não automatizáveis, requerem instrução)
└── .gitignore                            (exclui data/, inbox/, inbox_processed/)
```

---

## APÊNDICE E — CHECKLIST DE EXECUÇÃO

### Setup inicial
- [ ] Estrutura de diretórios criada
- [ ] 5 arquivos de config copiados em `config/` + 1 `life_plan_goals.md` em `life_plan/` (ou onboarded)
- [ ] Arquivos iniciais organizados e renomeados
- [ ] Auditoria em inbox_processed/
- [ ] Logs gerados (inbox_log.md, run_log.md)
- [ ] Repositório Git inicializado com commit inicial

### Primeiro ciclo completo (E1 até E6)
- [ ] E1: members-1c_enriched.md gerado
- [ ] E1.5: baseline_patrimonial-1.5_consolidated.json gerado
- [ ] E2: todos os -2_extract.json gerados
- [ ] E3: todos os -3_reconciled.json gerados
- [ ] E4: 7 arquivos -4_unified.json gerados (incluindo seguros e fluxo_mensal_detalhado)
- [ ] E5: analise_financeira-5_analysis.json gerado com chave narrativas
- [ ] E5.N: narrativas geradas (perfil, summaries, charts)
- [ ] E6: relatorio_financeiro_*.html gerado
- [ ] Logs atualizados

### Ciclos recorrentes
- [ ] Novos arquivos no inbox detectados e roteados
- [ ] Tipo de ciclo determinado (E2 rápido / E1.5 completo / full)
- [ ] Etapas relevantes executadas
- [ ] Relatório atualizado

---

**Versão 6.1 — Abril 2026**
**Autor: Pipeline Financeiro Ferreira Campos**
**Última atualização: 13 abr 2026**
