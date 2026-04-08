# Plano de Correção — Etapa E1 (Mapeamento de Membros)
## Pipeline Financeiro Ferreira Campos
## Data: 2026-04-05

---

## CONTEXTO

Revisão detalhada da etapa E1 identificou 12 problemas, dos quais 4 são de severidade ALTA. O E1 é executado por LLM (não é determinístico), o que torna os schemas e instruções precisas ainda mais críticos — sem contrato rígido, cada execução pode gerar outputs diferentes, quebrando etapas downstream.

### Dados de referência para nomes

| Membro  | Nome de solteiro(a)              | Nome de casado(a) (atual)               | Observação                             |
|---------|----------------------------------|------------------------------------------|----------------------------------------|
| David   | David Robert Camargo de Campos   | David Robert Camargo Ferreira Campos     | Documentos pré-casamento usam solteiro |
| Mariana | Mariana Teixeira Ferreira        | Mariana Ferreira Campos                  | Holerite Einstein usa nome de solteira (fiscal) |
| Theo    | —                                | Theo Ferreira Campos                     | Nome único                             |

---

## BLOCO 1 — SCHEMAS FORMAIS (Severidade ALTA)

### 1.1 — Reescrever schema `curriculo-1a_extract.json` (Seção 7.2)

**Problema:** Schema usa chaves em português (`profissao_cargo`, `experiencias`, `formacao`) mas os JSONs reais usam inglês (`profession_current_role`, `professional_experiences`, `education`) — e os dois membros divergem entre si.

**Ação:** Padronizar em **português** (coerente com o resto do pipeline, onde todos os JSONs E3/E4/E5 usam português). Adicionar chaves faltantes. Tornar **todas as chaves obrigatórias** explícitas.

**Schema proposto:**

```json
{
  "tipo": "curriculo",
  "membro": "david | mariana",
  "nome_completo": "Nome como aparece no documento (pode ser solteiro ou casado)",
  "nome_atual": "Nome atual completo (de definitions.md)",
  "profissao_cargo": "Cargo principal atual",
  "experiencias": [
    {
      "empresa": "Nome da empresa",
      "cargo": "Título do cargo",
      "tipo_vinculo": "PJ | CLT | freelance | docencia",
      "data_inicio": "YYYY-MM",
      "data_fim": "YYYY-MM | presente",
      "descricao": "Resumo em 1-2 frases (pode ser vazio)"
    }
  ],
  "formacao": [
    {
      "instituicao": "Nome da instituição",
      "curso": "Nome do curso",
      "grau": "graduacao | pos_graduacao | especializacao | mestrado | doutorado | certificacao",
      "data_conclusao": "YYYY"
    }
  ],
  "certificacoes": [
    {
      "nome": "Nome da certificação",
      "instituicao": "Entidade emissora (se disponível)"
    }
  ],
  "habilidades": ["habilidade1", "habilidade2"],
  "idiomas": [
    {
      "idioma": "Português | Inglês | ...",
      "nivel": "nativo | fluente | avancado | intermediario | basico"
    }
  ]
}
```

**Chaves obrigatórias:** `tipo`, `membro`, `nome_completo`, `nome_atual`, `profissao_cargo`, `experiencias` (≥1), `formacao` (≥1), `idiomas` (≥1).

**Regras especiais:**
- Se o currículo não listar idiomas explicitamente, inferir idioma nativo a partir do idioma do documento. Ex: currículo em português → `{"idioma": "Português", "nivel": "nativo"}`.
- Overlaps temporais entre experiências são **válidos** (ex: David CTO Elo7 + consultant Loft). Não "corrigir".
- `data_inicio`/`data_fim`: se o documento diz "junho de 2019", converter para `2019-06`. Se diz apenas "2019", usar `2019-01`.

---

### 1.2 — Reescrever schema `holerite-1a_extract.json` (Seção 7.2)

**Problema:** Schema usa `membro`, `periodo`, `empresa`, `salario_bruto` etc. JSON real usa `member_name`, `period`, `employer`, `gross_salary`. Também faltam campos relevantes no schema (FGTS, base INSS, grade, dependentes IR).

**Ação:** Manter português, expandir para cobrir todos os campos extraíveis.

**Schema proposto:**

```json
{
  "tipo": "holerite",
  "membro": "david | mariana",
  "nome_no_documento": "Nome como consta no holerite (pode ser nome de solteiro/fiscal)",
  "periodo": "YYYY-MM",
  "empresa": "Nome do empregador",
  "estabelecimento": "Unidade/filial (se disponível)",
  "cargo": "Cargo formal",
  "categoria": "Categoria funcional (se disponível)",
  "grade": "Grade/nível (se disponível, ex: P4)",
  "matricula": "ID do funcionário (se disponível)",
  "data_admissao": "YYYY-MM-DD",
  "salario_base_mensal": 0.00,
  "salario_bruto": 0.00,
  "proventos_adicionais": [
    {
      "codigo": "código (se disponível)",
      "descricao": "Descrição do provento",
      "valor": 0.00
    }
  ],
  "descontos": [
    {
      "codigo": "código (se disponível)",
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
  "observacoes": "Notas relevantes (férias no período, 13º, etc.)"
}
```

**Chaves obrigatórias:** `tipo`, `membro`, `periodo`, `empresa`, `cargo`, `salario_bruto`, `descontos` (≥0), `total_descontos`, `salario_liquido`.

**Regras especiais:**
- `nome_no_documento`: preservar exatamente como está no holerite (ex: "Mariana Teixeira Ferreira"). O mapeamento para o membro do pipeline é feito via `membro`, não via nome.
- Se o holerite contiver proventos excepcionais (férias, 13º), registrar em `proventos_adicionais` E mencionar em `observacoes`.

---

### 1.3 — Criar schema formal para `members-1b_unified.json`

**Problema:** Não existe schema. O LLM decide livremente a estrutura. Resultado: chaves ad-hoc como `salary_net_note`, `name_cv`, `employment_type` misturadas sem contrato.

**Schema proposto:**

```json
{
  "tipo": "members_unified",
  "data_geracao": "YYYY-MM-DD",
  "fonte_definitions": true,
  "membros": [
    {
      "id": "david | mariana | theo",
      "nome_atual": "Nome atual completo (casado)",
      "nomes_alternativos": ["Nome de solteiro", "Nome fiscal", "Nome no currículo"],
      "cpf": "XXX.XXX.XXX-XX (de definitions.md)",
      "data_nascimento": "YYYY-MM-DD (de definitions.md)",
      "papel_familia": "Titular | Cônjuge | Filho",
      "empregador_atual": "Nome da empresa ou null",
      "cargo_atual": "Cargo ou null",
      "tipo_vinculo": "PJ | CLT | null (para dependentes)",
      "data_admissao": "YYYY-MM-DD ou null",
      "formacao_maxima": "Descrição da formação mais alta",
      "idiomas": [{"idioma": "...", "nivel": "..."}],
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
        "nota": "Explicação se o líquido estiver atípico (férias, adiantamento, etc.)"
      },
      "documentos_disponiveis": ["curriculo", "holerite", "rg", "cpf"],
      "status_fiscal": "BR | US | BR+US",
      "observacoes": "Notas relevantes"
    }
  ]
}
```

**Regras de consolidação (passo 4 expandido):**

| Conflito | Regra de resolução |
|---|---|
| Nome difere entre docs | `nome_atual` vem do `definitions.md`. Variantes vão em `nomes_alternativos`. |
| Salário difere currículo vs. holerite | Holerite prevalece (fonte primária). |
| Cargo difere currículo vs. holerite | Currículo para descrição rica, holerite para cargo formal. Usar o do currículo em `cargo_atual`. |
| Datas de experiência se sobrepõem | Manter ambas. Overlaps são válidos (consultoria paralela, docência + CLT). |
| Membro sem documentos (ex: Theo) | Incluir com dados do `definitions.md`. Campos sem fonte ficam `null`. `documentos_disponiveis: []`. |
| Múltiplos holerites | Usar o mais recente para `salario`. Mencionar em `nota` se houve variação significativa. |

---

### 1.4 — Criar spec formal para `members-1c_enriched.md`

**Problema:** Formato livre. Pode variar entre execuções.

**Spec proposta — template obrigatório:**

```markdown
# Membros — Família [Sobrenome]
## Extração: YYYY-MM-DD

---

## [Nome Atual Completo] ([Nomes Alternativos])

**Perfil:** [Nacionalidade], [idade] anos (nasc. DD/MM/YYYY). [Idiomas].

**Histórico profissional:** [Resumo de 2-3 frases cobrindo tempo de carreira, áreas, progressão].

**Cargo atual:** [Cargo] na [Empresa] ([tipo vínculo]). [Desde MM/YYYY].

**Salário atual ([fonte], [período]):**
- Base mensal: R$ X.XXX,XX
- Bruto no período: R$ X.XXX,XX [notas se houver férias, 13º, etc.]
- Descontos principais: INSS R$ X.XXX,XX | IRRF R$ X.XXX,XX
- [Outras linhas relevantes: FGTS, benefícios]

**Documentação disponível:** [lista].

**Status fiscal:** [BR / US / BR+US]. [Detalhes do regime se relevante].

---
```

**Regras:**
- **Um bloco `---` separado por membro**, na ordem: Titular → Cônjuge → Filhos.
- Para Theo (ou qualquer membro sem documentos): bloco mínimo com perfil e observação "Sem documentos processados neste ciclo".
- **Idade deve ser calculada** a partir de `data_nascimento` do `definitions.md`, não estimada a partir de formatura.
- Salário: se PJ/pró-labore sem holerite, escrever "PJ — valor a confirmar via extratos bancários de [instituição]".

---

## BLOCO 2 — INPUTS E INSTRUÇÕES (Severidade ALTA/MÉDIA)

### 2.1 — Adicionar `config/definitions.md` como input obrigatório do E1

**Problema:** O E1 lista apenas inputs de `members/`. Não instrui o LLM a ler `definitions.md`, que contém CPF, nascimento, papel na família, nomes alternativos, empresa PJ, animais de estimação.

**Ação:** Na seção "Inputs" do STAGE E1, adicionar:

```
- `config/definitions.md` (dados cadastrais: CPF, nascimento, papel, nomes, empresa PJ)
```

E adicionar na "Processing logic" um **passo 0**:

> **0. Carregar dados cadastrais:**
> - Ler `config/definitions.md`
> - Extrair tabela de membros (nome completo, CPF, nascimento, papel)
> - Usar como base para: calcular idades exatas, preencher `nome_atual`, resolver ambiguidades de nome, garantir que todos os membros listados estejam no output (mesmo sem documentos)

---

### 2.2 — Adicionar tabela de nomes no `definitions.md`

**Problema:** O `definitions.md` tem "Mariana Teixeira Ferreira (nome fiscal) / Mariana Ferreira Campos" mas não explica a lógica solteiro/casado nem lista os nomes do David.

**Ação:** Adicionar uma seção no `definitions.md`:

```markdown
## NOMES (SOLTEIRO / CASADO)

| Membro  | Nome de solteiro(a)              | Nome de casado(a) (atual)            | Nome no holerite / IRPF                |
|---------|----------------------------------|--------------------------------------|----------------------------------------|
| David   | David Robert Camargo de Campos   | David Robert Camargo Ferreira Campos | — (PJ, sem holerite CLT)               |
| Mariana | Mariana Teixeira Ferreira        | Mariana Ferreira Campos              | Mariana Teixeira Ferreira (Einstein)   |
| Theo    | —                                | Theo Ferreira Campos                 | —                                      |

> Documentos emitidos antes do casamento podem conter o nome de solteiro(a).
> O holerite do Einstein usa o nome fiscal (solteira) de Mariana.
> Ao encontrar qualquer variante desses nomes, mapear para o `id` do membro correto.
```

---

### 2.3 — Expandir passo 4 com regras de consolidação explícitas

**Problema:** O passo 4 diz apenas "resolver conflitos (e.g., salário)". Um único exemplo é insuficiente para um LLM.

**Ação:** Substituir o passo 4 atual por:

> **4. Consolidar (`members-1b_unified.json`):**
>
> a. Iniciar com os membros de `config/definitions.md` como base (garante que todos apareçam, mesmo sem documentos).
>
> b. Para cada membro, mesclar dados de todos os `-1a_extract.json` correspondentes.
>
> c. Regras de resolução de conflito:
>
> | Campo | Regra |
> |---|---|
> | Nome | `nome_atual` = do `definitions.md`. Variantes dos documentos → `nomes_alternativos`. |
> | Salário | Holerite mais recente prevalece. Se só tem currículo: `null` com nota. |
> | Cargo | Currículo para descrição narrativa. Holerite para cargo formal (código funcional). |
> | Empresa | Holerite prevalece para empregador atual se CLT. Currículo se PJ. |
> | Data admissão | Holerite prevalece (dado formal). |
> | Formação | Unir todas as fontes sem duplicar. Ordenar por data desc. |
> | Overlap de datas | Manter ambas experiências. Overlaps são válidos (trabalho paralelo, docência). |
> | Idiomas | Unir de todas as fontes. Se nenhuma fonte listar, inferir nativo do idioma do currículo. |
> | Membro sem docs | Criar entrada com dados do `definitions.md`. Campos sem fonte = `null`. |
>
> d. Schema: conforme seção 7.2.

---

### 2.4 — Tratar múltiplos holerites

**Problema:** Nome do output (`[membro]_holerite-1a_extract.json`) sugere arquivo único, mas pode haver múltiplos holerites.

**Ação — duas alternativas (escolher uma):**

**Opção A (recomendada): um arquivo por holerite, com período no nome.**
```
members/mariana_holerite_202602-1a_extract.json
members/mariana_holerite_202603-1a_extract.json
```
- Coerente com o padrão do input (`mariana_holerite_202602-0_original.pdf`)
- O passo 4 consolida todos no `1b_unified`, usando o mais recente para `salario`.

**Opção B: arquivo único com array de períodos.**
```json
{
  "tipo": "holerite",
  "membro": "mariana",
  "periodos": [
    { "periodo": "202602", "salario_bruto": 12086.06, ... },
    { "periodo": "202603", "salario_bruto": 10899.51, ... }
  ]
}
```
- Mais compacto mas diverge do padrão 1:1 input→output.

**Recomendação:** Opção A. Manter o padrão 1 input → 1 extract. Atualizar a seção de outputs para refletir:

```
- `members/[membro]_holerite_[período]-1a_extract.json` (um por holerite)
```

---

## BLOCO 3 — VALIDAÇÃO (Severidade MÉDIA)

### 3.1 — Expandir seção "Validation" do E1

**Problema:** Validação atual é genérica ("chaves obrigatórias vide schema"). Não valida valores nem consistência entre artefatos.

**Ação:** Reescrever para:

> **Validation:**
>
> **V1 — Schema compliance:**
> - Cada `-1a_extract.json` deve conter **todas** as chaves marcadas como obrigatórias no schema 7.2.
> - Nenhum valor obrigatório pode ser `null` ou string vazia (exceto se o schema permitir explicitamente).
>
> **V2 — Valores numéricos (holerites):**
> - `salario_bruto > 0`
> - `salario_liquido > 0`
> - `salario_liquido ≤ salario_bruto`
> - `total_descontos = soma(descontos[].valor)` (tolerância: ±R$0.10 por arredondamento)
>
> **V3 — Consistência 1a → 1b:**
> - Todo `membro` presente em algum `-1a_extract.json` DEVE ter entrada correspondente no `1b_unified`.
> - Todo membro do `definitions.md` DEVE ter entrada no `1b_unified` (mesmo sem documentos).
> - `1b_unified.membros.length ≥ número_de_membros_em_definitions`
>
> **V4 — Consistência 1b → 1c:**
> - Todo membro do `1b_unified` DEVE ter seção no `1c_enriched.md`.
> - Idade no `1c_enriched` deve bater com `data_nascimento` do `definitions.md` (não estimativa).
>
> **V5 — Documentos corrompidos ou vazios:**
> - Se um PDF não puder ser lido (corrompido, protegido por senha, escaneado sem OCR legível): registrar em `qa_log.md` com formato:
>   ```
>   [YYYY-MM-DD] E1 | WARN | Arquivo [nome] não pôde ser processado: [motivo]. Membro [id] terá dados parciais.
>   ```
> - NÃO interromper a execução. Continuar com os documentos disponíveis.

---

## BLOCO 4 — EDGE CASES E ASSERTIVIDADE (Severidade BAIXA→MÉDIA)

### 4.1 — Documentos pessoais (certidões, RG, etc.)

**Problema:** O passo 3 diz "extrair: tipo de documento, número, data de emissão, data de validade, dados demográficos relevantes" — muito vago. "Dados demográficos relevantes" pode significar qualquer coisa para um LLM.

**Ação:** Especificar por tipo de documento:

| Tipo | Campos a extrair |
|---|---|
| RG | numero, orgao_emissor, data_emissao, uf, nome_completo, filiacao (nome dos pais), naturalidade |
| CPF | numero, nome_completo, data_nascimento (se constar) |
| Passaporte | numero, pais_emissor, data_emissao, data_validade, nome_completo, nacionalidade |
| Visto | tipo_visto, pais, numero, data_emissao, data_validade, status |
| Certidão nascimento | nome, data_nascimento, local_nascimento, nome_pai, nome_mae, cartorio, livro_folha |
| Certidão casamento | nomes_conjuges, data_casamento, regime_bens, cartorio |
| SSN | numero (últimos 4 se parcial), nome_completo |
| Driver's license | numero, estado, data_emissao, data_validade, classe |
| Green card | numero, nome_completo, data_emissao, pais_nascimento, categoria |

### 4.2 — Instrução explícita sobre idiomas vazios

**Problema:** Mariana tem `languages: []`. O currículo dela é em português e ela trabalha no Brasil — claramente nativa em português.

**Ação:** Adicionar regra no passo 1:

> Se o currículo não listar seção de idiomas explicitamente, **inferir idioma nativo** a partir do idioma do documento e do país de atuação. Registrar como `{"idioma": "Português", "nivel": "nativo", "fonte": "inferido"}`.

### 4.3 — Instrução sobre overlaps temporais

**Ação:** Adicionar nota no passo 1:

> **NOTA:** Experiências profissionais com datas sobrepostas são válidas e comuns (consultoria paralela a emprego CLT, docência acumulada com cargo hospitalar). NÃO ajustar datas para eliminar overlaps.

---

## BLOCO 5 — CORREÇÃO DOS ARTEFATOS EXISTENTES

Após atualizar o manual, os artefatos já gerados precisam ser regenerados para ficarem em conformidade.

### 5.1 — Re-executar E1 com o manual corrigido

| Arquivo | Ação |
|---|---|
| `david_curriculo-1a_extract.json` | Regenerar com schema português + chaves `tipo`, `membro`, `nome_atual` |
| `mariana_curriculo-1a_extract.json` | Regenerar idem + inferir idioma Português nativo |
| `mariana_holerite-1a_extract.json` | Regenerar (renomear para `mariana_holerite_202602-1a_extract.json`) com schema atualizado |
| `members-1b_unified.json` | Regenerar com schema formal + incluir Theo |
| `members-1c_enriched.md` | Regenerar com template obrigatório + idades exatas + seção Theo |

### 5.2 — Validar impacto downstream

Após regeneração do E1, verificar que:
- E5.N (narrativas) → `perfil_familia.left` no JSON de análise referencia dados corretos dos 3 membros
- E6 (render) → relatório HTML mostra perfil atualizado

Não é necessário re-executar E2→E6 completo, apenas E5.N (narrativas que leem `1c_enriched.md`) e E6.

---

## RESUMO DE MUDANÇAS NO MANUAL

| Seção do manual | Mudança |
|---|---|
| **STAGE E1 — Inputs** | Adicionar `config/definitions.md` |
| **STAGE E1 — Processing logic, passo 0** | Novo: carregar dados cadastrais |
| **STAGE E1 — Processing logic, passo 1** | Regra de idiomas inferidos + nota de overlaps |
| **STAGE E1 — Processing logic, passo 2** | Schema expandido para holerite |
| **STAGE E1 — Processing logic, passo 3** | Tabela de campos por tipo de documento pessoal |
| **STAGE E1 — Processing logic, passo 4** | Reescrever com tabela de resolução de conflitos |
| **STAGE E1 — Outputs** | `[membro]_holerite_[período]-1a_extract.json` |
| **STAGE E1 — Validation** | V1→V5 expandidas |
| **Seção 7.2 — Schemas** | Reescrever currículo, holerite, novo 1b_unified |
| **config/definitions.md** | Nova seção NOMES (solteiro/casado) |

---

## ORDEM DE EXECUÇÃO SUGERIDA

1. Atualizar `config/definitions.md` (adicionar seção NOMES) — 5 min
2. Atualizar `manual_operacao.md` seção E1 + seção 7.2 — 30 min
3. Bump versão manual para v5.0
4. Git commit: `config: E1 schemas formais, definitions nomes, validação expandida`
5. Re-executar E1 com o manual corrigido — ~15 min (LLM)
6. Validar artefatos contra schemas — 5 min
7. Git commit: `pipeline: E1 re-executado com schemas v5.0`
8. Re-executar E5.N + E6 (se narrativas mudaram) — ~5 min
