# Manual de Operação — Pipeline Financeiro
## Família Ferreira Campos
## Versão: 4.0 — abr/2026

---

## CHANGELOG v1.0 → v2.0 → v2.1 → v3.0 → v3.1 → v3.2 → v4.0

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

### v2.0 → v2.1

| Mudança | Motivo |
|---|---|
| **Remoção da separação rígida Cowork/Chat** | Qualquer ambiente (Cowork ou Chat) pode executar qualquer etapa. Execução é agnóstica ao ambiente. |
| **Detecção inteligente de ciclo (SMART CYCLE)** | Ciclos não são mais fixos (quinzenal/trimestral). Pipeline detecta tipos de arquivo e determina quais etapas são necessárias. |
| **Suporte a veículos (XLSX)** | Novo diretório `data/vehicles/` com tipo `dados_veiculos` e padrão `dados_veiculos-0_original.xlsx`. Extração em E1.5. |
| **Documentos pessoais (BR e US)** | Novos tipos em `members/`: RG, CPF, passaporte, visto, certidão, SSN, drivers license, green card. Enriquecem `members-1c_enriched.md`. |
| **Categoria "outros ativos"** | Patrimônio expandido para incluir veículos, ações, criptos, joias, arte — não só imóveis. Arquivo `patrimonio-3_unified.json` (consolidação de TODOS os ativos do IRPF). |
| **Versionamento via Git** | Quando arquivo existente é atualizado (novo CV, novo IRPF): comitar estado atual via Git antes de sobrescrever, re-extrair. Histórico acessível via `git log`. |
| **Tratamento de sobreposição de dados** | E2.5 reconciliação detecta duplicatas por data+amount+description, retém apenas novos. E3/E4 podem ser incrementais. |
| **JSON schemas em apêndice** | Esquemas explícitos para -2_extract.json para cada tipo de documento. Permite execução sem memória prévia. |
| **Seção 4 reescrita como "PIPELINE STAGES"** | Cada estágio descrito independentemente, especificando inputs/outputs/validação. Não mais amarrado a "Momento 1/2" ou "Cowork/Chat". |
| **Diretório `data/vehicles/` adicionado** | Estrutura de diretórios atualizada. Agora 89 arquivos + veículos (se presentes). |
| **Seção "Incremental Updates"** | Nova seção explicando como pipeline trata novos arquivos para períodos existentes, versões atualizadas, e novos tipos de arquivo. |
| **Diagrama visual atualizado** | Apêndice com fluxo revisado refletindo detecção inteligente e processamento agnóstico. |
| **Manual auto-contido** | Instruções explícitas para leitura de PDFs e XLSX. Schemas completos. Uma execução fresca pode rodar tudo do zero lendo apenas este manual. |

### v3.0 → v3.1

| Mudança | Motivo |
|---|---|
| **`[membro]s-1b_unified.json` corrigido para `members-1b_unified.json`** | Nome anterior gerava confusão: LLM criava arquivo por membro ao invés de consolidado único. Alinhado com Apêndice D e estado real do disco. |
| **Contagem canvas IDs corrigida: 18 → 19** | V4 na validação E5.6 dizia 18 mas as tabelas E5.4+E5.5 somam 19 IDs distintos. Nota sobre alias `fluxo_mensal` adicionada. |
| **Contagem chaves JSON top-level corrigida para 14** | Lista explícita das 14 chaves adicionada na validação E5.3 para evitar ambiguidade. |
| **Schemas adicionados: currículo, holerite, seguros, analise_financeira** | Seção 7.2 com schemas formais que faltavam. O schema do E4 (`analise_financeira-4_analysis.json`) é crítico pois é o input principal do E5. |
| **Fórmula do score financeiro especificada** | E4 item 5 agora tem média ponderada de 5 componentes com critérios 0/10 e 10/10, classificação e interpolação linear. |
| **Critérios de tarefas e alertas adicionados** | E4 item 9 (novo) com tabelas de gatilhos para geração de tarefas (12 critérios) e alertas (8 critérios), formatos e prioridades. |
| **Formato de [DATE] especificado** | `YYYYMMDD` sem hífens. Ex: `20260403`. Antes não documentado, causando variação entre execuções. |
| **Tipo `faturacc` esclarecido** | Schema agora usa códigos de roteamento (`faturacarbon`, `faturaunique`, `faturapaoacucar`) em vez de genérico `faturacc`. |
| **Instrução de origem `report_template.html` adicionada** | Nova Seção 1.1.1 explica que o template HTML não é gerado pelo pipeline — deve pré-existir ou ser fornecido pelo usuário. |
| **Nota sobre E1.5 outputs em `E2_extracts/`** | Esclarece por que outputs de E1.5 ficam em `processed/E2_extracts/` (convenção: inputs diretos para E2). |
| **Contagem "6 configs" esclarecida** | Agora especifica "5 em config/ + 1 em life_plan/" para evitar confusão. |

### v3.1 → v3.2

| Mudança | Motivo |
|---|---|
| **Migração para Git** | Versionamento ad-hoc (`output/archive/`, `_v1`, `.bak`, `version_log.md`) substituído por repositório Git. Todas as versões anteriores agora acessíveis via `git log` / `git show`. |
| **Nova Seção 4.5 — Versionamento com Git** | Documenta o que está no Git, fluxo de commits, convenção de mensagens, e como recuperar versões anteriores. |
| **`output/archive/` removido** | Diretório eliminado da estrutura. Git é o archive. |
| **`logs/version_log.md` removido** | Substituído pelo histórico Git. Logs operacionais (inbox, run, qa, divergences, reconciliation) mantidos. |
| **Seção 5.1 reescrita** | Fluxo de atualização de arquivos agora usa `git commit` + sobrescrita em vez de renomear com `_v1`. |
| **E5.6 e E5-regen atualizados** | "Mover para archive" substituído por "comitar via Git antes de sobrescrever". |
| **`.gitignore` adicionado** | Exclui `data/`, `inbox/`, `inbox_processed/`, `.DS_Store`, `.obsidian/`, e backups legados. |

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
| **Categoria "Seguros" adicionada** | `seguros-3_unified.json` agora captura prêmios, coberturas e vencimentos (extraído de faturas e holerites). |
| **Nenhuma contagem hardcoded** | Removidas referências a "89 arquivos", "77 arquivos", etc. Texto agora genérico: "todos os arquivos detectados" ou "varies based on input". |

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

| Sintoma                                           | Onde corrigir                                                          | Depois rodar        |
| ------------------------------------------------- | ---------------------------------------------------------------------- | ------------------- |
| Layout quebrado, CSS errado, JS com bug           | `config/report_template.html`                                          | E5-regen            |
| Label de gráfico errado, texto fixo errado        | `config/report_template.html`                                          | E5-regen            |
| Gráfico não renderiza (canvas não encontrado)     | `config/report_template.html` (verificar IDs canônicos na Seção 4, E5) | E5-regen            |
| Valor de KPI errado, dado numérico incorreto      | `processed/E4_analysis/` (ou E2/E3 se o erro vem de extração)          | E4 + E5             |
| Transação categorizada errada                     | `processed/E3_unified/` ou regras em `config/definitions.md`           | E3 + E4 + E5        |
| Transação faltando ou duplicada                   | `processed/E2_extracts/` ou `E2_reconciled/`                           | E2.5 + E3 + E4 + E5 |
| Texto de seção mal escrito ou análise superficial | E4.N (narrativas) → E4.N + E5                                          | E4.N + E5           |
| Dados de membro errados (nome, cargo)             | `members/members-1c_enriched.md`                                       | E1 + E4 + E5        |
| Meta financeira desatualizada                     | `life_plan/life_plan_goals.md`                                         | E4 + E5             |

### Regra para o assistente

Quando o usuário pedir para "corrigir algo no relatório", o assistente DEVE:

1. **Diagnosticar a origem** — o erro é de apresentação (template) ou de dados (E1–E4)?
2. **Corrigir no arquivo-fonte** — seguindo a tabela acima
3. **Regenerar o relatório** — rodar E5 ou E5-regen conforme o caso
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

O arquivo `config/report_template.html` é o template estrutural para o relatório final (E5). Ele contém a estrutura HTML, CSS, JavaScript (Chart.js) e placeholders `{{...}}` que são preenchidos durante E5.

- **Se já existir** em `config/report_template.html`: usar como está (não gerar automaticamente).
- **Se não existir**: solicitar ao usuário. Este arquivo é criado manualmente ou por um designer — o pipeline NÃO o gera automaticamente, apenas o popula.
- **Requisitos mínimos do template:** deve conter os 19 canvas IDs listados em E5.4/E5.5, os placeholders `{{COVER_*}}`, `{{KPI_*}}`, `{{SUMMARY_S*}}`, `{{CONTENT_S*}}`, `{{CONTENT_APP_*}}`, `{{PERFIL_FAMILIA_*}}`, `{{REPORT_DATA_JSON}}` e `{{FOOTER_CONTENT}}`.

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
│   ├── E2_reconciled/
│   ├── E3_unified/
│   └── E4_analysis/
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
3. Copiar para o **diretório de destino** com o **nome final** (sufixo `-0_original` inserido antes da extensão)
4. Se o arquivo de destino já existir, **não sobrescrever** — registrar como duplicata no log

**Regra crítica:** nunca modificar o conteúdo dos arquivos — apenas copiar e renomear.

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
- `santander_cdbdetalhes_202603-0_original.pdf` ← Detalhe CDB Santander março 2026
- `bradesco_extratopoupanca_202602_202603-0_original.pdf` ← Poupança fevereiro-março 2026

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
- `receitafederal_irpfdeclaracao_2024-0_original.pdf` ← IRPF 2024
- `receitafederal_irpfrecibo_2024-0_original.pdf` ← Recibo IRPF 2024
- `quintoandar_informerendimentosaluguel_2025-0_original.pdf` ← Informe aluguel 2025

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

**Passo 2 — Identificar a instituição** pela combinação de nome + conteúdo:

| Padrões no nome | Padrões no conteúdo | Instituição | Entidade |
|---|---|---|---|
| `c6`, `carbon`, `c6bank` | "C6 Bank", "Carbon" | C6 Bank | `c6bank` |
| `itau`, `itaú`, `personnalite`, `paoacucar` | "Itaú", "Personnalité" | Itaú | `itau` |
| `santander`, `unique` | "Santander", "Unique" | Santander | `santander` |
| `bradesco` | "Bradesco" | Bradesco | `bradesco` |
| `btg`, `btgpactual` | "BTG Pactual" | BTG Pactual | `btgpactual` |
| `rico`, `xp` | "Rico", "XP Investimentos" | Rico/XP | `rico` |
| `picpay` | "PicPay" | PicPay | `picpay` |
| `wise` | "Wise", "TransferWise" | Wise | `wise` |
| `bofa`, `bankofamerica` | "Bank of America" | Bank of America | `bankofamerica` |
| `quintoandar`, `quinto_andar` | "QuintoAndar", "GRPQA" | QuintoAndar | `quintoandar` |
| `binance` | "Binance" | Binance | `binance` |
| `receita`, `rfb`, `irpf` | "Receita Federal", "IRPF" | Receita Federal | `receitafederal` |
| `einstein`, `sociedade beneficente` | "Hospital Israelita", "Einstein" | Einstein | — (holerite → `members/`) |

**Passo 3 — Identificar o tipo de documento:**

| Indicadores | Tipo | Código |
|---|---|---|
| "extrato", "lançamentos", "statement" | Extrato conta corrente | `extratoconta` |
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
| "fatura" + "aluguel" | Fatura de aluguel QuintoAndar | `faturaaluguel` |
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
- Se não houver, verificar conteúdo
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

**Passo 7 — Verificar duplicata:**
```bash
ls financas-familia/data/[destino]/[nome_final] 2>/dev/null
```
Se existir → registrar como duplicata e **não sobrescrever**.

**Passo 8 — Executar:**
```bash
# Cópia de auditoria
cp financas-familia/inbox/[nome_original] \
   financas-familia/inbox_processed/[DATA-DE-HOJE]/[nome_original]

# Mover para destino
mv financas-familia/inbox/[nome_original] \
   financas-familia/data/[destino]/[nome_final]
```

**Passo 9 — Arquivos não identificados:**
Se não conseguir identificar depois de analisar nome + conteúdo:
- Registrar em `logs/qa_log.md` como `"arquivo não identificado — aguardando instrução"`
- Mover para `financas-familia/inbox_processed/[DATA]/nao_identificados/[nome_original]`
- Informar o usuário

---

### 3.2 — Determinação do ciclo necessário

Após rotear todos os arquivos, analisar quais tipos foram recebidos e determinar quais etapas executar:

| Arquivos recebidos | Tipo de ciclo | Etapas necessárias |
|---|---|---|
| Apenas extratos de conta corrente + faturas | **E2 rápido** | E2 (extração), E2.5 (reconciliação), E3 (unificação) |
| Extratos novos para períodos já processados | **E2 + E2.5** | Detectar sobreposições, reconciliar apenas deltas |
| Declaração IRPF nova OU XLSX de imóveis | **E1.5 + E2 + E3 + E4 + E5** | Ciclo completo (baseline muda) |
| Novos currículos, holerites, documentos pessoais | **E1 + E1.5 + E2 + E3 + E4 + E5** | Ciclo completo (perfil do membro muda) |
| Novos documentos de veículos (XLSX) | **E1.5 + E3 + E4 + E5** | Patrimônio muda, re-gerar análises |
| Novos documentos pessoais (passaporte, RG, CPF) | **E1 + E3 + E4 + E5** | Enriquecimento do membro, relatório atualizado |
| Documentos US novos (SSN, drivers license, green card) | **E1 + E3 + E4 + E5** | Contexto fiscal US, potencial para T1 |
| Usuário solicita explicitamente ciclo completo | **Full cycle** | E1 + E1.5 + E2 + E2.5 + E3 + E4 + E5 |

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

**Tipo:** [E2 rápido / E1.5 + E2 + E3 + E4 + E5 / Full cycle]
**Razão:** [Explicação breve: e.g., "Novo IRPF → baseline muda"]
```

---

## SEÇÃO 4 — PIPELINE STAGES

Cada etapa é descrita de forma agnóstica (não amarrada a Cowork/Chat). Qualquer ambiente pode executar qualquer etapa.

### STAGE E1 — Mapeamento de membros

**Objetivo:** Extrair informações de membros (perfil, experiência, renda) de currículos, holerites e documentos pessoais.

**Inputs:**
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

1. **Para cada currículo (DOCX ou PDF):**
   - Ler o documento (se DOCX, usar DOCX reader; se PDF, usar PDF reader)
   - Extrair: nome completo, profissão/cargo, experiências profissionais (datas, títulos, empresas), formação (cursos, certificações, datas), habilidades, idiomas
   - Salvar em `members/[membro]_curriculo-1a_extract.json`

2. **Para cada holerite:**
   - Ler o PDF
   - Extrair: nome do membro, período, salário bruto, descontos, salário líquido, empresa, cargo, data de admissão
   - Salvar em `members/[membro]_holerite-1a_extract.json`

3. **Para cada documento pessoal (RG, CPF, passaporte, visto, certidões, SSN, drivers license, green card):**
   - Ler o documento (PDF ou JPG usando OCR se necessário)
   - Extrair: tipo de documento, número, data de emissão, data de validade, dados demográficos relevantes
   - Salvar em `members/[membro]_[tipo]-1a_extract.json`

4. **Consolidar para cada membro:**
   - Combinar todos os extratos de todos os membros em `members/members-1b_unified.json`
   - Resolver conflitos de dados (e.g., se currículo e holerite diferem em salário, usar holerite como mais recente)

5. **Gerar documento enriquecido:**
   - Salvar em `members/members-1c_enriched.md` com seção para cada membro listando:
     - Perfil básico (nome, idade estimada, idiomas)
     - Histórico profissional resumido
     - Cargo e empresa atuais
     - Salário atual (de holerite mais recente)
     - Documentação (quais documentos pessoais estão disponíveis)
     - Status fiscal (BR, US, ou ambos)

**Outputs:**
- `members/[membro]_curriculo-1a_extract.json`
- `members/[membro]_holerite-1a_extract.json`
- `members/[membro]_[tipo_documento]-1a_extract.json` (para cada documento pessoal)
- `members/members-1b_unified.json`
- `members/members-1c_enriched.md`

**Validation:**
- Todos os extratos devem ter chaves obrigatórias (vide schema abaixo)
- Nenhum documento pode estar vazio (se arquivo PDF corrompido, registrar em `qa_log.md`)
- Unificado deve ter entradas para todos os membros detectados

---

### STAGE E1.5 — Baseline patrimonial

**Objetivo:** Extrair snapshot de patrimônio e renda de declarações IRPF, informes QuintoAndar e XLSX de imóveis/veículos.

> **Nota sobre diretório de outputs:** Os outputs de E1.5 são salvos em `processed/E2_extracts/` (não em diretório dedicado E1.5) por convenção, pois servem como inputs diretos para E2 e E2.5. O prefixo do sufixo identifica a origem: `-1.5_consolidated` para o baseline, `-2_extract` para os extratos individuais de IRPF/imóveis/veículos.

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

**Outputs:**
- `processed/E2_extracts/receitafederal_irpfdeclaracao_[ano]-2_extract.json` (múltiplos)
- `processed/E2_extracts/receitafederal_irpfrecibo_[ano]-2_extract.json` (múltiplos)
- `processed/E2_extracts/quintoandar_informerendimentosaluguel_[ano]-2_extract.json` (múltiplos)
- `processed/E2_extracts/dados_imoveis-2_extract.json`
- `processed/E2_extracts/dados_veiculos-2_extract.json` (se houver)
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`
- `logs/divergences.md` (se houver divergências)

**Validation:**
- Baseline consolidado deve conter: membros identificados, ano-base da declaração, bens totais, renda total
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

1. **Para cada extrato de conta (CC, PJ, Global, Poupança):**
   - Ler o PDF (se JPG, usar OCR)
   - Extrair: saldo inicial, saldo final, número da conta, período coberto, tipo de moeda
   - Extrair TODAS as transações: data, descrição, débito/crédito, saldo após
   - **NÃO categorizar transações** — apenas extrair fidedignamente
   - Salvar em `processed/E2_extracts/[banco]_extrato*-2_extract.json`

2. **Para cada fatura de cartão:**
   - Ler o PDF
   - Extrair: saldo anterior, compras, juros, pagamentos, saldo atual, data de vencimento
   - Extrair TODAS as transações: data, descrição, valor, categoria (se houver), parcelação
   - **NÃO categorizar** — manter como no documento
   - Salvar em `processed/E2_extracts/[banco]_fatura*-2_extract.json`

3. **Para cada posição de investimento:**
   - Ler o PDF
   - Extrair: data da posição, saldo em reais (ou moeda), composição (ações, fundos, títulos, etc.), rentabilidade acumulada, valores com data de aquisição
   - **Para ações (product_type = "Acao"):** extrair obrigatoriamente `quantity`, `unit_price`, `issuer`. Se `applied_value` não estiver disponível (comum em posições Rico), marcar como `null` e adicionar `pm_note` explicando a ausência.
   - **Reconciliação de PM (preço médio):** Cruzar quantidade com IRPF do ano-base anterior. Se quantidade atual ≠ quantidade IRPF, PM não pode ser estimado (requer notas de corretagem B3/CEI). Se quantidade for idêntica, PM pode ser estimado como `valor_irpf / quantidade`.
   - Salvar em `processed/E2_extracts/[banco]_investimentosposicao_[período]-2_extract.json`

4. **Para cada carteira de renda fixa / CDB:**
   - Ler o PDF
   - Extrair: tipo de produto, valor aplicado, data de aplicação, taxa, vencimento, saldo atual
   - Salvar em `processed/E2_extracts/[banco]_cdb*-2_extract.json`

5. **Para cada fatura de aluguel (QuintoAndar):**
   - Ler o PDF
   - Extrair: propriedade, período, renda bruta, descontos, líquido, data de pagamento
   - Salvar em `processed/E2_extracts/quintoandar_faturaaluguel_*-2_extract.json`

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

### STAGE E2.5 — Reconciliação por conta

**Objetivo:** Consolidar múltiplos extratos da mesma conta, remover duplicatas de períodos sobrepostos, verificar completude.

**Inputs:**
- TODOS os `processed/E2_extracts/*-2_extract.json` (multitude)
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`

**Processing logic:**

1. **Para cada conta identificada (e.g., "Itaú Personnalité PF", "C6 Bank USD"):**
   - Agrupar todos os extratos dessa conta em ordem cronológica
   - Para períodos sobrepostos (detectar por datas):
     - Buscar duplicatas por regra: **data + valor + descrição** = mesma transação
     - Manter apenas uma cópia
     - Registrar qual extrato foi fonte de verdade
   - Preencher gaps: se há gap entre dois extratos, registrar em `qa_log.md`
   - Compilar lista de TODAS as transações de forma consolidada

2. **Validação de saldos:**
   - Pegar saldo inicial do extrato mais antigo
   - Aplicar transações em ordem cronológica
   - Comparar saldo final calculado com saldo final reportado
   - Se houver diferença, registrar discrepância em `logs/reconciliation.md`

3. **Validação contra baseline:**
   - Se há IRPF para 31/12 de ano anterior, comparar saldo nessa data com baseline
   - Se há IRPF para 31/12 de ano-base, comparar saldo em 31/12 com baseline
   - Registrar variações esperadas vs. inesperadas

4. **Gerar arquivo consolidado por conta:**
   - Nome: `processed/E2_reconciled/[banco]_[tipo_conta]_[período_total]-2_reconciled.json`
   - Conteúdo: todas as transações deduplicated, saldos validados, datas de cobertura completas

**Outputs:**
- `processed/E2_reconciled/[banco]_[tipo_conta]_[período_total]-2_reconciled.json` para cada conta
- `logs/reconciliation.md` com resumo de cada conta e deduplicações

**Validation:**
- Cada account reconciliado deve ter saldo inicial, transações deduplicated, saldo final
- Nenhuma transação deve aparecer mais de uma vez
- Gaps devem ser documentados
- Saldos devem bater (ou divergência documentada)

---

### STAGE E3 — Enriquecimento e unificação

**Objetivo:** Categorizar transações, consolidar por tipo (receita, despesa, investimento, patrimônio), enriquecer com contexto.

**Inputs:**
- `processed/E2_reconciled/*-2_reconciled.json` (todos)
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
   - Gerar `processed/E3_unified/receitas-3_unified.json`: agrupado por fonte (PJ, CLT, aluguéis, rendimentos financeiros, etc.)
   - Gerar `processed/E3_unified/despesas-3_unified.json`: agrupado por subcategoria (alimentação, saúde, educação, seguros, etc.)
   - Gerar `processed/E3_unified/investimentos-3_unified.json`: consolidar posições de investimento por tipo
   - Gerar `processed/E3_unified/pontos_milhas-3_unified.json`: se houver cartões com acúmulo de pontos

3. **Consolidar patrimônio:**
   - Gerar `processed/E3_unified/patrimonio-3_unified.json` consolidando:
     - Imóveis: usar `dados_imoveis-2_extract.json` + IRPF (valor declarado em 31/12)
     - Veículos: usar `dados_veiculos-2_extract.json` se houver
     - Investimentos: consolidar posições de investimento
     - Contas bancárias: saldos em 31/12 (ou data mais recente)
     - Criptos, joias, arte: extratos do IRPF (se houver)
     - Empresas/cotas: extratos do IRPF
     - Dívidas: consolidar do IRPF
   - Total patrimonial = bens totais - dívidas

4. **Consolidar seguros:**
   - Gerar `processed/E3_unified/seguros-3_unified.json` consolidando:
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
- `processed/E3_unified/receitas-3_unified.json`
- `processed/E3_unified/despesas-3_unified.json`
- `processed/E3_unified/investimentos-3_unified.json`
- `processed/E3_unified/patrimonio-3_unified.json`
- `processed/E3_unified/seguros-3_unified.json`
- `processed/E3_unified/pontos_milhas-3_unified.json`
- `logs/qa_log.md` (transações não identificadas)
- `config/definitions.md` (atualizado com novas regras descobertas)

**Validation:**
- Todas as transações devem estar em exatamente uma categoria
- Total de receitas == soma de receitas-3_unified.json
- Total de despesas == soma de despesas-3_unified.json
- Patrimônio em 31/12 deve ser consistente com baseline IRPF

---

### STAGE E4 — Análise

**Objetivo:** Gerar análises de fluxo de caixa, rácios, evolução patrimonial, tax planning.

**Inputs:**
- `processed/E3_unified/*-3_unified.json` (todos)
- `config/report_spec.md` (especificação de relatório)
- `life_plan/life_plan_goals.md`
- `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json`

**Processing logic:**

1. **Fluxo de caixa:**
   - Total recebido = receitas-3_unified.json
   - Total desembolsado = despesas-3_unified.json
   - Fluxo líquido = recebido - desembolsado
   - Variação de patrimônio = fluxo líquido + inflação ajustada

2. **Rácios financeiros:**
   - Taxa de poupança **recorrente** = (receitas_recorrentes - despesas_totais) / receitas_recorrentes
     - ⚠️ **RECEITAS RECORRENTES** = excluir receitas one-time (rescisões, Kiwify, vendas de ativos, restituições extraordinárias)
     - ⚠️ **DESPESAS TOTAIS** = pessoais + PJ (DAS, impostos) + financiamentos — não apenas despesas-3_unified
     - ⚠️ Salvar AMBOS os valores no E4: `taxa_poupanca_recorrente_pct` (KPI principal) e `taxa_poupanca_total_pct` (informativo)
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
   - Construir tabela patrimonial com as categorias abaixo, cada uma rastreável até a fonte:

   | Categoria | Fórmula / Fonte | Notas |
   |---|---|---|
   | Residência própria | IRPF David → imóvel Tasso da Silveira `valor_31_12_ano_base` | Sempre 1 imóvel, valor IRPF |
   | Imóveis investimento | (Total imóveis E4) − Residência | Inclui Major Freire (XLSX, não IRPF) |
   | Investimentos David | baseline `investimentos[]` (TODOS, inclui Hashdex) | Hashdex é fundo regulado FIC FIM, não crypto direta |
   | Investimentos Mariana | baseline `investimentos[]` (BTG) | Todos CDB/CRA/Fundos BTG |
   | Criptoativos | Binance extracts (saldo em BRL) | Crypto direta (BTC, ETH, ADA etc.), não inclui fundos crypto regulados |
   | Caixa + Moeda Estrangeira | Bruto − (todas as categorias acima) − Veículos | Valor residual; inclui contas bancárias + USD + outros |
   | Veículos | baseline `veiculos[]` sum | Soma dos 3 veículos IRPF |

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
   - Nenhum valor no E4 deve ser copiado do life_plan; o E4 CALCULA e o life_plan é ATUALIZADO com o resultado

7. **Consumo consciente — análise de gastos pontuais:**
   - Varrer `despesas-3_unified.json` e identificar todas as transações individuais ≥ R$ 2.000 que NÃO sejam recorrentes (ex: aluguel, seguros, financiamento, mensalidades)
   - Classificar cada uma como **pontual** (compra única, presente, procedimento médico eletivo, eletrônico, viagem não-orçada, etc.)
   - Montar lista dos top gastos pontuais do período, com: descrição, cartão/conta, mês, valor, observação curta
   - Calcular:
     - `consumo_consciente.total_pontuais` = soma dos gastos pontuais identificados
     - `consumo_consciente.equivalente_meses_aporte` = total_pontuais / aporte_mensal_IF (de life_plan)
     - `consumo_consciente.folga_mensal` = receita_recorrente − despesas_recorrentes (sem pontuais)
     - `consumo_consciente.folga_pct` = folga_mensal / receita_recorrente × 100
     - `consumo_consciente.teto_sugerido` = despesas_recorrentes × 1.15 (margem 15% para pontuais diluídos)
   - Se não houver gastos pontuais ≥ R$ 2.000 no período, gerar o bloco mesmo assim com `itens: []` e uma nota positiva ("Nenhum gasto pontual relevante — disciplina excelente")
   - Salvar no E4 analysis JSON no bloco `consumo_consciente`

8. **Diagnóstico de Comportamento Financeiro (OBRIGATÓRIO):**
   - Varrer os dados unificados (E3) e extratos (E2) para detectar padrões comportamentais recorrentes.
   - **Regras de detecção (verificar todas — incluir no output apenas as que forem positivas):**

   | Padrão | Regra de Detecção | Fonte de Dados |
   |---|---|---|
   | **Cheque especial recorrente** | Saldo negativo em qualquer conta corrente PF em ≥ 3 meses do período, enquanto há liquidez disponível em outras contas/investimentos | `despesas-3_unified.json` (saldos mensais), `investimentos-3_unified.json` |
   | **Gastos grandes sem planejamento** | Soma de transações pontuais ≥ R$2.000 (não recorrentes) em janela de 2 meses consecutivos > R$20.000, sem provisão prévia (conta reserva ou categoria "reserva de desejos") | `despesas-3_unified.json` (transações individuais), `consumo_consciente.itens` |
   | **Impostos pagos de forma irregular** | DAS pago em lotes irregulares (não mensal), OU carnê-leão com meses zerados quando há renda de aluguel, OU IRRF não retido em fonte que deveria reter | `despesas-3_unified.json` (transações com categoria "impostos"), `receitas-3_unified.json` (aluguéis) |
   | **Aluguéis não reinvestidos** | Renda de aluguéis entra em conta corrente e não há transferência correspondente para conta de investimento no mesmo mês ou mês seguinte | `receitas-3_unified.json` (aluguéis), `despesas-3_unified.json` (transferências para investimento) |
   | **Cartão de crédito parcelado excessivo** | Soma de parcelas ativas em cartão de crédito > 30% da receita recorrente mensal | `despesas-3_unified.json` (transações parceladas) |
   | **Receitas PJ misturadas com PF** | Receitas da PJ sendo usadas diretamente para despesas pessoais sem pró-labore formal | `receitas-3_unified.json`, `despesas-3_unified.json` (cruzamento PJ/PF) |

   - **Para cada padrão detectado, gerar:**
     - `padrao`: nome do padrão (ex: "Cheque especial recorrente")
     - `evidencia`: texto descritivo com dados concretos dos extratos (valores, meses, contas)
     - `mudanca_sugerida`: recomendação prática e específica de automatização
   - **Se NENHUM padrão for detectado**, gerar o bloco com array vazio e nota positiva: "Nenhum padrão comportamental de risco identificado — excelente disciplina financeira."
   - **Tom:** Não julgar. Padrões são hábitos formados pela praticidade. O objetivo é automatizar o fluxo.
   - Salvar no E4 analysis JSON no bloco `diagnostico_comportamental[]`

10. **Reserva de Emergência (OBRIGATÓRIO):**
    - Calcular a despesa mensal média (de `despesas-3_unified.json`, últimos N meses do período)
    - Levantar a liquidez imediata: soma de CDB liquidez diária + Tesouro Selic + poupança + saldo em conta corrente (de `investimentos-3_unified.json` e `patrimonio-3_unified.json`)
    - Calcular 3 níveis:
      - `minimo_6m` = despesa_mensal × 6 (Perini — mínimo absoluto)
      - `conforto_9m` = despesa_mensal × 9 (recomendação para família com dependentes)
      - `conservador_12m` = despesa_mensal × 12 (Cerbasi — famílias com renda variável)
    - Classificar status de cada nível: "✅ Coberto" (liquidez ≥ valor), "⚠ Parcial" (liquidez ≥ 80% do valor), "❌ Abaixo" (liquidez < 80%)
    - Detalhar a composição da liquidez (quais ativos formam a reserva)
    - Gerar recomendação baseada no nível atingido
    - Salvar no E4 JSON no bloco `reserva_emergencia`

11. **Endividamento (OBRIGATÓRIO):**
    - Levantar todas as dívidas ativas: financiamentos, consórcios, parcelas de cartão, empréstimos, cheque especial
    - Para cada dívida: descrição, saldo devedor, parcela mensal, taxa de juros, data término, ação recomendada
    - Calcular: `total_dividas`, `pct_divida_patrimonio` = total_dividas / patrimonio.bruto × 100
    - Classificar: "Livre de Dívidas" (0%), "Controlado" (<10%), "Atenção" (10-30%), "Crítico" (>30%)
    - Gerar recomendação geral (prioridade de quitação, avalanche vs bola de neve)
    - Se não houver dívidas, gerar bloco com `dividas: []` e classificação "Livre de Dívidas"
    - Salvar no E4 JSON no bloco `endividamento`

12. **Previdência PGBL (OBRIGATÓRIO):**
    - Calcular renda tributável anual (pró-labore David + CLT Mariana + aluguéis tributáveis)
    - Limite PGBL anual = 12% da renda tributável
    - Aporte mensal atual: buscar em `despesas-3_unified.json` (transferências para previdência) ou `definitions.md`
    - Economia de IR anual = aporte_anual × alíquota_marginal (27,5% para esta faixa)
    - Projeção de acumulação em 10/15/20 anos com taxa real de 6% a.a. (juros compostos)
    - Renda mensal projetada = acumulado × 4% / 12 (regra dos 4%)
    - Status de portabilidade (se o fundo atual é adequado)
    - Salvar no E4 JSON no bloco `previdencia_pgbl`

13. **Pontos Fortes (OBRIGATÓRIO):**
    - Varrer TODOS os outputs anteriores (E1 a E4) e identificar 5-7 destaques positivos
    - Critérios: taxa poupança acima de 20%, diversificação, ausência de dívidas, patrimônio crescente, disciplina de aporte, proteção patrimonial, planejamento
    - Para cada ponto: `{titulo, descricao}` — título curto + descrição com dados concretos
    - Tom: celebrativo e motivacional
    - Salvar no E4 JSON no bloco `pontos_fortes[]`

14. **Pontos Urgentes (OBRIGATÓRIO):**
    - Varrer TODOS os outputs anteriores e identificar 5-7 ações críticas priorizadas por impacto
    - Critérios: dívidas de juros alto, impostos irregulares, reserva insuficiente, seguros vencidos, documentos expirados, oportunidades fiscais perdidas
    - Para cada ponto: `{prioridade, acao, impacto, prazo}` — numerado por urgência
    - Tom: direto e acionável, sem ser alarmista
    - Salvar no E4 JSON no bloco `pontos_urgentes[]`

15. **Equilíbrio Presente × Futuro — Cerbasi (OBRIGATÓRIO):**
    - Calcular proporção gastos-presente vs investimentos-futuro:
      - `pct_presente` = despesas_totais / receita_recorrente × 100
      - `pct_futuro` = aportes_investimentos / receita_recorrente × 100
    - Classificar: "Equilibrado" (futuro 20-40%), "Pendendo para Futuro" (>40%), "Pendendo para Presente" (<20%), "Desequilibrado" (<10% ou >50%)
    - Gerar análise contextualizada (fase de vida da família, dependentes, plano migratório)
    - Gerar recomendação baseada no framework Cerbasi
    - Salvar no E4 JSON no bloco `equilibrio_cerbasi`

16. **Gerar arquivo de análise:**
   - Salvar em `processed/E4_analysis/analise_financeira-4_analysis.json` com:
     - Fluxo de caixa (período)
     - Rácios (todos)
     - Evolução patrimonial (absoluta e %)
     - Alíquota efetiva de IR
     - Saúde vs. goals
     - **Visão patrimonial com todas as categorias e patrimônio investível**
     - **Consumo consciente (bloco `consumo_consciente` com itens, totais e métricas)**
     - **Diagnóstico comportamental (bloco `diagnostico_comportamental[]` com padrões, evidências e mudanças)**
     - **Reserva de emergência (bloco `reserva_emergencia` com 3 critérios: 6m, 9m, 12m — ver item 10 abaixo)**
     - **Endividamento (bloco `endividamento` com relação dívida/patrimônio — ver item 11 abaixo)**
     - **Previdência PGBL (bloco `previdencia_pgbl` com benefício fiscal e projeção — ver item 12 abaixo)**
     - **Pontos fortes (bloco `pontos_fortes[]` — ver item 13 abaixo)**
     - **Pontos urgentes (bloco `pontos_urgentes[]` — ver item 14 abaixo)**
     - **Equilíbrio Cerbasi (bloco `equilibrio_cerbasi` — ver item 15 abaixo)**
     - **Tarefas (bloco `tarefas[]` com n, t, p, e) e `tarefas_status`**
     - **Alertas (bloco `alertas[]` com tipo, titulo, descricao)**
   - O schema completo está na Seção 7.2 (`analise_financeira-4_analysis.json`)

**Outputs:**
- `processed/E4_analysis/analise_financeira-4_analysis.json`

**Validation:**
- Fluxo de caixa deve reconciliar com mudança de patrimônio
- Rácios devem estar em range esperado (e.g., endividamento < 50%)
- Crescimento patrimonial deve bater com contribuições + rentabilidade
- **`patrimonio.investivel` DEVE ser menor que `patrimonio.bruto`**
- **Soma das categorias patrimoniais DEVE igualar `patrimonio.bruto`**

---

### STAGE E4.N — Narrativas

**Objetivo:** Gerar todos os textos analíticos e narrativos necessários para o relatório. Executada pelo LLM como última sub-etapa do E4, após todos os cálculos estarem completos.

**Inputs:**
- `processed/E4_analysis/analise_financeira-4_analysis.json` (dados completos do E4)
- `members/members-1c_enriched.md` (dados dos membros)
- `life_plan/life_plan_goals.md` (metas, plano internacional, NCLEX)
- `config/report_spec.md` (regras de formatação e design)
- `config/definitions.md` (categorias, entidades)

**Output:** Nova chave `narrativas` adicionada ao E4 JSON com a seguinte estrutura:

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
- Perfil: 7 parágrafos de prosa em `<p>`. SEM tabelas, bullets, `<strong>Label:</strong>`. Ordem: titular, cônjuge, filho(s), pets, plano de vida, meta IF, patrimônio.
- Summaries: Factuais, com dados numéricos. Ex: "Patrimônio bruto de R$ 3,5M com 72% investível."
- Charts: Context = o que o gráfico mostra. Conclusion = insight acionável.
- Todos os textos em português brasileiro.

**Validação E4.N (DEVE passar antes de avançar para E5):**
- [ ] Chave `narrativas` presente no JSON
- [ ] `perfil_familia.left` e `perfil_familia.right` presentes e não-vazios
- [ ] `summaries` contém 10 chaves (s1 a s10), todas não-vazias
- [ ] `charts` contém 19 chaves, cada uma com `context` e `conclusion` não-vazios
- [ ] Perfil é HTML com `<p>` (sem `<table>`, `<ul>`, `<li>`)

---

### STAGE E5 — Relatório HTML (Determinístico)

**Objetivo:** Renderizar o relatório HTML final a partir do template + E4 JSON (dados + narrativas). Execução 100% determinística via script Python — sem LLM.

**Comando:**
```
python scripts/e5_render.py
```

**Inputs:**
- `config/report_template.html` ← template com placeholders `{{...}}`
- `processed/E4_analysis/analise_financeira-4_analysis.json` ← dados + narrativas
- `config/manual_operacao.md` ← versão do manual
- `config/definitions.md` ← categorias de despesa

**Output:** `output/relatorio_financeiro_ferreira_campos_[DATE].html`

**O que o script faz (6 fases):**

| Fase | Equivalente antigo | O que faz |
|---|---|---|
| E5.1 | E5.1 (Cover/KPIs) | Substitui `{{COVER_*}}`, `{{KPI_*}}`, `{{NOME}}`, `{{FOOTER_CONTENT}}` |
| E5.2 | E5.2 (Perfil) | Injeta `narrativas.perfil_familia.left/right` |
| E5.3 | E5.3 (JSON) | Monta report-data JSON (20 chaves, 19 charts) por mapeamento de dados |
| E5.4 | E5.4 (S1-S5) | Gera HTML das seções com charts (canvas IDs canônicos) + cards obrigatórios |
| E5.5 | E5.5 (S6-S10+Apps) | Gera HTML das seções restantes + apêndices |
| E5.6 | E5.6 (Validação) | Roda 18 checagens automáticas |

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
1. Reserva de Emergência (S1) — 3 níveis
2. Endividamento (S1) — dívidas + % patrimônio
3. Orçamento Prospectivo (S2) — 14 categorias
4. Consumo Consciente (S2) — gastos pontuais
5. Diagnóstico Comportamental (S2) — padrões
6. KPIs Rentabilidade + Tabela 3.1 (S3)
7. Estratégia Aporte 3.2 (S3)
8. Contrafluxo (S3)
9. Previdência PGBL (S7)
10. Pontos Fortes (S10)
11. Pontos Urgentes (S10)
12. Equilíbrio Cerbasi (S10)

**Validação E5.6 (18 checagens — mesma do manual anterior):**
[Keep the existing V1-V18 validation table]

**Se qualquer validação falhar:** O script imprime qual checagem falhou. Corrigir na fonte:
- Texto errado → re-rodar E4.N
- Dados errados → corrigir E2/E3/E4
- Layout/CSS → corrigir template

---

### STAGE E5-regen — Regeneração rápida do relatório

**Objetivo:** Regenerar o relatório quando houve mudança no template ou nos dados, sem reprocessar E0→E3.

**Quando usar:**
- Alteração no CSS, layout ou JS do template → `python scripts/e5_render.py`
- Ajuste nos textos narrativos → re-rodar E4.N + `python scripts/e5_render.py`
- Correção de dados → re-rodar E4 (ou E3+E4) + `python scripts/e5_render.py`

**Processo:**
1. Comitar versão anterior via Git
2. Rodar `python scripts/e5_render.py`
3. Verificar que as 18 validações passam

---

### STAGE E-reset — Reprocessamento completo do zero

**Objetivo:** Apagar todos os artefatos gerados pelo pipeline (E2→E5) e re-executar o processamento completo a partir dos arquivos originais já roteados em `data/`.

**Quando usar:**
- Mudança estrutural no manual, definitions, methodology ou report_spec que afeta múltiplas etapas
- Suspeita de dados corrompidos ou inconsistentes nos JSONs intermediários
- Atualização significativa de regras de categorização, membros ou life plan que invalida todo o processamento anterior
- Após correção de bug que afetou etapas anteriores e propagou erro para frente

**Quando NÃO usar:**
- Apenas template/CSS mudou → usar E5-regen
- Apenas novos extratos chegaram → usar fluxo normal E0 + ciclo incremental
- Apenas uma etapa específica precisa ser refeita → re-executar somente essa etapa

**Procedimento:**

**Passo 1 — Comitar estado atual via Git (preservar histórico):**
```bash
cd financas-familia
git add -A
git commit -m "pre-reset: snapshot antes de reprocessamento completo [DATA]"
```

**Passo 2 — Apagar artefatos gerados (E1→E5):**
```bash
# E2/E2.5/E3/E4 — JSONs intermediários em processed/ (subpastas)
rm -f financas-familia/processed/E2_extracts/*.json
rm -f financas-familia/processed/E2_reconciled/*.json
rm -f financas-familia/processed/E3_unified/*.json
rm -f financas-familia/processed/E4_analysis/*.json

# E1 — Intermediários de membros (os -0_original são preservados)
rm -f financas-familia/members/*-1a_extract.json
rm -f financas-familia/members/members-1b_unified.json
rm -f financas-familia/members/members-1c_enriched.md

# E5 — Relatório HTML em output/
rm -f financas-familia/output/relatorio_financeiro_ferreira_campos_*.html

# Logs operacionais (serão regenerados pelo pipeline)
rm -f financas-familia/logs/run_log.md
rm -f financas-familia/logs/reconciliation.md
rm -f financas-familia/logs/divergences.md

# Summaries de execução anteriores (artefatos temporários)
rm -f financas-familia/E3_ANALYSIS_SUMMARY.md
rm -f financas-familia/E5_EXECUTION_SUMMARY.md
rm -f financas-familia/E2_PROCESSING_SUMMARY.txt
rm -f financas-familia/E2_TARGET_FILES_MANIFEST.txt
```

**Passo 3 — Preservar (NÃO apagar):**
- `data/` — arquivos originais já roteados com sufixo `-0_original` (E0 já foi feito)
- `members/*-0_original.*` — documentos pessoais originais (currículos, holerites, RG, etc.)
- `inbox_processed/` — auditoria de entrada (histórico de roteamento)
- `logs/inbox_log.md` — registro de todos os ciclos de roteamento
- `logs/qa_log.md` — itens pendentes de instrução do usuário
- `config/` — manual, definitions, methodology, template, report_spec, report_template.html
- `life_plan/` — dados de objetivos e plano de vida
- `scripts/` — scripts Python de execução (se houver)

**Passo 4 — Re-executar pipeline completo:**
Executar na ordem: **E1 → E1.5 → E2 → E2.5 → E3 → E4 → E5**

(E0 não precisa ser re-executado — os arquivos já estão organizados em `data/` com nomes finais.)

**Passo 5 — Comitar resultado:**
```bash
cd financas-familia
git add -A
git commit -m "E-reset: reprocessamento completo [DATA]"
```

**Validation:**
- Verificar que `processed/` contém os JSONs esperados (E2, E3, E4)
- Verificar que `output/` contém o novo relatório HTML
- Executar checklist V1–V18 do E5 (Seção 4, STAGE E5)
- Comparar com relatório anterior (disponível no histórico Git) para confirmar que não houve perda de dados

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
| `scripts/` (e5_regen.py, etc.) | `*.bak`, `*_backup.*`, `*_prev.*` |
| `members/` (currículos, documentos pessoais) | |
| `life_plan/` | |

### 4.5.2 — Fluxo padrão: comitar antes de alterar

Antes de qualquer operação que sobrescreva um arquivo existente (novo relatório, arquivo atualizado, re-extração), o pipeline deve:

1. `git add [arquivos afetados]`
2. `git commit -m "[contexto]: [descrição curta]"`
3. Executar a alteração

### 4.5.3 — Convenção de mensagens de commit

| Situação | Exemplo de mensagem |
|---|---|
| Relatório gerado (E5) | `E5: relatório 2026-04-04` |
| Regeneração de template (E5-regen) | `E5-regen: novo layout aplicado` |
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
git diff <hash1> <hash2> -- processed/E4_analysis/analise_financeira-4_analysis.json
```

### 4.5.5 — Segurança

- O `.gitignore` garante que PDFs financeiros e dados sensíveis **nunca** entrem no Git
- Se o repositório for hospedado no GitHub, usar **repositório privado**
- Antes de qualquer `git push`, verificar com `git status` que nenhum arquivo sensível está staged

---

## SEÇÃO 5 — TRATAMENTO DE ARQUIVOS ATUALIZADOS (Incremental Updates)

Quando um arquivo existente é substituído por versão nova, seguir este protocolo:

### 5.1 — Versionamento de arquivo

Quando arquivo com mesmo nome chega no inbox (e.g., novo `david_curriculo-0_original.docx`):

1. **Comitar estado atual via Git:**
   ```bash
   cd financas-familia/
   git add members/david_curriculo-0_original.docx
   git commit -m "pre-update: david_curriculo antes de substituição por versão nova"
   ```

2. **Sobrescrever com o novo arquivo:**
   ```bash
   cp financas-familia/inbox/[nome_novo] \
      financas-familia/members/david_curriculo-0_original.docx
   ```

3. **Comitar a nova versão:**
   ```bash
   git add members/david_curriculo-0_original.docx
   git commit -m "update: david_curriculo — CV atualizado com nova experiência"
   ```

4. **Re-executar etapa relevante:**
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
   - Executar E2.5 novamente
   - Detectar duplicatas por data+valor+descrição
   - Manter apenas novas transações

3. **Executar E3 novamente:**
   - Re-categorizar com novo conjunto de transações
   - Gerar novos -3_unified.json

4. **Registrar em reconciliation.md:**
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

**Fatura de cartão de crédito:**

> **Nota:** O campo `tipo` no schema abaixo usa o valor genérico `faturacc`. Na prática, o nome do arquivo segue o código de roteamento específico da Seção 3 (ex: `faturacarbon`, `faturaunique`, `faturapaoacucar`). Ao gerar o extract JSON, usar o código de roteamento como `tipo` (ex: `"tipo": "faturacarbon"`), não o genérico.

```json
{
  "tipo": "faturacarbon | faturaunique | faturapaoacucar",
  "instituicao": "[banco]",
  "cartao": {
    "nome": "[nome cartão]",
    "tipo": "credit | debit",
    "ultimos_digitos": "0000"
  },
  "periodo": {
    "data_inicio": "YYYY-MM-DD",
    "data_fim": "YYYY-MM-DD",
    "data_vencimento": "YYYY-MM-DD"
  },
  "resumo": {
    "saldo_anterior": 0.00,
    "compras_nacionais": 0.00,
    "compras_internacionais": 0.00,
    "juros": 0.00,
    "taxa_mensal": 0.00,
    "pagamentos_efetuados": 0.00,
    "saldo_atual": 0.00
  },
  "transacoes": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "[descrição]",
      "valor": 0.00,
      "categoria": "[categoria conforme documento ou em branco]",
      "parcelas": "1/1 | 2/3 | etc"
    }
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

**Currículo (-1a_extract.json):**
```json
{
  "tipo": "curriculo",
  "membro": "[nome do membro]",
  "nome_completo": "[nome]",
  "profissao_cargo": "[cargo principal]",
  "experiencias": [
    {
      "empresa": "[nome da empresa]",
      "cargo": "[título]",
      "data_inicio": "YYYY-MM",
      "data_fim": "YYYY-MM | presente",
      "descricao": "[resumo]"
    }
  ],
  "formacao": [
    {
      "instituicao": "[nome]",
      "curso": "[nome do curso]",
      "grau": "graduacao | pos_graduacao | mestrado | doutorado | certificacao",
      "data_conclusao": "YYYY"
    }
  ],
  "habilidades": ["[habilidade1]", "[habilidade2]"],
  "idiomas": [
    {
      "idioma": "[nome]",
      "nivel": "nativo | fluente | avancado | intermediario | basico"
    }
  ]
}
```

**Holerite (-1a_extract.json):**
```json
{
  "tipo": "holerite",
  "membro": "[nome do membro]",
  "periodo": "YYYY-MM",
  "empresa": "[nome da empresa]",
  "cargo": "[cargo]",
  "data_admissao": "YYYY-MM-DD",
  "salario_bruto": 0.00,
  "descontos": [
    {
      "descricao": "INSS | IRRF | vale_transporte | plano_saude | outro",
      "valor": 0.00
    }
  ],
  "total_descontos": 0.00,
  "salario_liquido": 0.00,
  "beneficios": [
    {
      "descricao": "[nome do benefício]",
      "valor": 0.00
    }
  ]
}
```

**Seguros (-3_unified.json):**
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

**Análise financeira (-4_analysis.json):**
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
    }
  },

  "racios": {
    "taxa_poupanca_recorrente_pct": 0.0,
    "taxa_poupanca_total_pct": 0.0,
    "taxa_endividamento_pct": 0.0,
    "cobertura_despesas_meses": 0,
    "rentabilidade_pct": 0.0,
    "aliquota_efetiva_ir_pct": 0.0
  },

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
        "observacao": "[nota]"
      }
    ],
    "total_pontuais": 0.00,
    "equivalente_meses_aporte": 0.0,
    "folga_mensal": 0.00,
    "folga_pct": 0.0,
    "teto_sugerido": 0.00
  },

  "diagnostico_comportamental": [
    {
      "padrao": "[nome do padrão]",
      "evidencia": "[texto com dados concretos]",
      "mudanca_sugerida": "[recomendação prática]"
    }
  ],

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
                      [E2.5] Reconciliação
                    (Duplicatas + Validação)
                              |
                              v
                       [E3] Enriquecimento
                    (Categorização + Unificação)
                              |
                              v
                       [E4] Análise
                 (Rácios + Evolução Patrimonial)
                              |
                              v
                       [E5] Relatório
                       (HTML final)
                              |
                              v
                        output/relatorio.html
```

---

## APÊNDICE B — ROADMAP DE FEATURES FUTURAS (v3.1+)

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
| **Reconciliação (-2_reconciled.json)** | Consolidação de múltiplos extratos de uma mesma conta, deduplicando períodos sobrepostos |
| **Unificação (-3_unified.json)** | Agregação de dados reconciliados por tipo (receita, despesa, etc.) com categorização completa |
| **Análise (-4_analysis.json)** | Derivação de métricas: fluxo, rácios, crescimento, alíquota, saúde vs. goals |
| **SMART CYCLE** | Detecção automática de tipos de arquivo → determinação de etapas necessárias (vs. ciclos fixos quinzenal/trimestral) |
| **Versionamento** | Comitar estado atual via Git antes de substituir arquivo. Histórico acessível via `git log -- [caminho/do/arquivo]` |
| **Divergência** | Inconsistência detectada entre fontes (e.g., saldo IRPF vs. saldo extrato, imóvel em IRPF mas não em XLSX) |
| **QA Log** | Registro de itens não automatizáveis — requerem revisão/instrução manual antes de continuação |

---

## APÊNDICE D — ESTRUTURA FINAL DE DIRETÓRIOS (v3.1)

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
│   ├── E2_reconciled/                    (outputs de E2.5)
│   │   ├── itau_personnalite_pf_202505_202603-2_reconciled.json
│   │   ├── c6bank_global_usd_202505_202603-2_reconciled.json
│   │   ├── bradesco_conta_corrente_202501_202603-2_reconciled.json
│   │   ├── [um arquivo por conta identificada]
│   │   └── [tipicamente 8-12 arquivos]
│   ├── E3_unified/                       (outputs de E3)
│   │   ├── receitas-3_unified.json
│   │   ├── despesas-3_unified.json
│   │   ├── investimentos-3_unified.json
│   │   ├── patrimonio-3_unified.json
│   │   ├── seguros-3_unified.json
│   │   ├── pontos_milhas-3_unified.json
│   │   └── [exatamente 6 arquivos]
│   └── E4_analysis/                      (outputs de E4)
│       └── analise_financeira-4_analysis.json
├── output/
│   └── relatorio_financeiro_ferreira_campos_[DATE].html (E5 — versões anteriores no histórico Git)
├── logs/
│   ├── inbox_log.md                      (roteamento de todos os ciclos)
│   ├── run_log.md                        (execução de cada etapa)
│   ├── reconciliation.md                 (detalhes de deduplicação E2.5)
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

### Primeiro ciclo completo (E1 até E5)
- [ ] E1: members-1c_enriched.md gerado
- [ ] E1.5: baseline_patrimonial-1.5_consolidated.json gerado
- [ ] E2: todos os -2_extract.json gerados
- [ ] E2.5: todos os -2_reconciled.json gerados
- [ ] E3: 6 arquivos -3_unified.json gerados (incluindo seguros)
- [ ] E4: analise_financeira-4_analysis.json gerado
- [ ] E5: relatorio_financeiro_*.html gerado
- [ ] Logs atualizados

### Ciclos recorrentes
- [ ] Novos arquivos no inbox detectados e roteados
- [ ] Tipo de ciclo determinado (E2 rápido / E1.5 completo / full)
- [ ] Etapas relevantes executadas
- [ ] Relatório atualizado

---

**Versão 3.1 — Abril 2026**
**Autor: Pipeline Financeiro Ferreira Campos**
**Última atualização: 4 abr 2026**
