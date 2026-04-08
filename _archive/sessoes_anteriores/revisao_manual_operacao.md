# Revisão do Manual de Operação v5.3
## Inconsistências, Imprecisões e Dados Hardcoded
**Data:** 2026-04-06 | **Revisor:** Claude

---

## 🔴 CRÍTICOS (afetam corretude ou causam falha)

### 1. Placeholder não resolvido na validação E6
**Linha 2023:** `[Keep the existing V1-V18 validation table]`

O manual referencia "18 checagens automáticas" (E6.6) mas a tabela V1-V18 nunca foi incluída — ficou um placeholder de rascunho. Qualquer operador executando E6.6 não tem a lista de validações para conferir.

**Ação:** Inserir a tabela V1-V18 completa ou referenciar o script `e6_render.py` que contém as validações implementadas.

---

### 2. Confusão sistemática "E4 JSON" vs "E5 analysis JSON"
**Linhas 1485, 1502, 1677, 1698, 1714, 1743, 1769, 1778, 1788, 1795, 1802, 1811**

Dentro da STAGE E5 (Análise), o manual diz repetidamente "Salvar no **E4 JSON**" ou "Gerar chave X no **E4 JSON**". Porém o arquivo de destino é `analise_financeira-**5**_analysis.json` (sufixo `-5_`), salvo em `processed/**E5**_analysis/`.

Exemplo (linha 1485): *"Gerar chave `orcamento_prospectivo` no E4 JSON"* → deveria ser "no E5 analysis JSON".

Isso cria ambiguidade: um operador pode achar que deve escrever no output do E4 (que são os `*-4_unified.json`), não no E5.

**Ação:** Substituir todas as referências "E4 JSON" dentro da STAGE E5 por "E5 analysis JSON" ou `analise_financeira-5_analysis.json`.

---

### 3. Changelog v5.1→v5.2 duplicado
**Linhas 17-27 e 70-84**

Existem DUAS seções `### v5.1 → v5.2` no changelog, com conteúdos diferentes. A primeira (linhas 17-27) fala de `e0_audit.py`, colisão de nomes e Passo 7. A segunda (linhas 70-84) fala de exit codes, `TODAY = date.today()`, pre-check de dependências e limpeza de narrativas.

Ambas são mudanças reais mas foram atribuídas à mesma versão.

**Ação:** Renumerar uma delas (provavelmente a das linhas 70-84 deveria ser v5.2→v5.2.1 ou integrada no bloco correto) ou unificar num único bloco.

---

## 🟡 IMPORTANTES (imprecisões que geram confusão)

### 4. Referência obsoleta "E5.4/E5.5" após renumeração
**Linha 388:** *"deve conter os 19 canvas IDs listados em **E5.4/E5.5**"*

Na v4.5, as etapas foram renumeradas (E5→E6). A seção E6 documenta E6.4 e E6.5 como equivalentes ao antigo E5.4/E5.5 (linha 1960-1961). Mas a referência na Seção 1.1.1 ainda usa a numeração antiga.

**Ação:** Trocar "E5.4/E5.5" por "E6.4/E6.5" na linha 388.

---

### 5. Valores monetários hardcoded nos exemplos de schema
**Linhas 1351-1357, 1458-1464, 1597-1603, 1615-1617, 1631-1632**

Os "exemplos" de JSON contêm valores reais de um ciclo específico (Arvo R$47.550, Einstein R$8.500, patrimônio R$2.360.000, etc.). Isso tem dois problemas:

- Operadores podem copiar esses valores como se fossem defaults
- Valores ficam desatualizados a cada ciclo

Exemplos afetados:
| Local | Valor hardcoded |
|-------|-----------------|
| Receitas por mês | Arvo 47550, BrandLovers 10000, Arbitralis 3000, Einstein 8500, Aluguéis 8571, Rendimentos 257 |
| Patrimônio categorias | Imóveis renda 2.360.000, Residência 2.200.000, Investimentos David 860.272 |
| Tabela investível | 3.648.716 |
| Receitas por fonte | Arvo 570.600 (52,3%), Einstein 102.000, Aluguéis 102.852 |
| Renda fixa | 650.000 (52,6%), Fundos 280.000 |

**Ação:** Substituir por placeholders genéricos (`0.00` ou `XXXX`) nos exemplos de schema, ou adicionar nota explícita: *"Valores abaixo são ilustrativos do ciclo abr/25-mar/26 — o script calcula dinamicamente."*

---

### 6. Selic 14,25% hardcoded no exemplo de contrafluxo
**Linha 1719:** `"selic_atual": 14.25`

O valor da Selic no exemplo de JSON está fixo em 14,25%. Embora seja "exemplo", um operador LLM pode copiar esse valor em vez de buscar a Selic vigente.

**Ação:** Substituir por `0.00` com comentário `// buscar Selic vigente do definitions.md ou fonte externa` ou usar placeholder.

---

### 7. "37 faturas" e "~8s" repetidos como fato operacional
**Linhas 140, 143, 1180**

O número de faturas (37) e o tempo de execução (~8s) são de uma execução específica, mas aparecem como instrução operacional genérica. Se o pipeline crescer para 60 faturas, o manual ficará incorreto.

**Ação:** Na seção operacional (linha 1180), substituir por linguagem genérica: *"Tempo de execução: proporcional ao número de faturas (~0,2s por fatura)."* No changelog, manter como referência histórica (está correto lá).

---

### 8. Contagem de cards "17" pode estar desatualizada
**Linha 1988-2005**

A lista de "Cards obrigatórios" contém 17 itens. Porém:
- v4.2 elevou de 13→16
- v4.4 elevou de 16→17

Se um novo card for adicionado no futuro, a lista e o número precisam ser sincronizados. Não há validação automática que confira se o número de cards no template bate com a lista do manual.

**Ação:** Adicionar ao script `e6_render.py` uma constante `EXPECTED_CARD_COUNT` derivada da lista, ou remover a contagem numérica do manual e confiar na lista enumerada.

---

### 9. Nomes de empresas PJ hardcoded como se fossem categorias fixas
**Linhas 1336-1340, 1348**

Os exemplos de origens de receita listam empresas específicas: "Arvo (David - PJ)", "BrandLovers (David - PJ)", "Arbitralis (David - PJ)", "Learn To Fly (David - PJ)". Essas empresas podem mudar — se David trocar de cliente PJ, o manual precisaria ser atualizado.

Na prática o `e4_categorize.py` lê essas origens do `definitions.md`, o que é correto. Mas o manual as apresenta como se fossem fixas.

**Ação:** Deixar claro que os nomes vêm do `definitions.md` e que os exemplos são ilustrativos. Ex: *"Origens PJ: conforme `PJ_SOURCE_MAPPING` em `definitions.md` (ex: Arvo, BrandLovers, etc.)"*

---

### 10. "5 imóveis" hardcoded na tabela de patrimônio
**Linha 1597:** `"Imóveis para renda (5 imóveis)"`

O label inclui a contagem "5 imóveis" como parte da categoria. Se um imóvel for vendido ou comprado, o manual fica incorreto.

**Ação:** Indicar que o número deve ser calculado dinamicamente: *"Imóveis para renda ({N} imóveis)"* onde N = count de imóveis excluindo residência.

---

### 11. Faixas de Selic para contrafluxo com gap
**Linhas 1702-1704:**
- `"alta"` → Selic ≥ 12%
- `"queda"` → Selic entre 8% e 12% (exclusive)
- `"baixa"` → Selic < 8%

Há um gap conceitual: Selic = 12% é "alta" (≥12%) mas não é "queda" (8% a 12% exclusive). Isso está correto. Porém as faixas de texto no JSON dizem:
- `"selic_alta": "13-15%"`
- `"selic_queda": "10-12%"`
- `"selic_baixa": "6-8%"`

Essas faixas (13-15%, 10-12%, 6-8%) não cobrem 8-10% nem 12-13% nem >15% nem <6%. São inconsistentes com a definição ≥12/8-12/<8.

**Ação:** Alinhar as faixas textuais com a definição: `"selic_alta": "≥12%"`, `"selic_queda": "8-12%"`, `"selic_baixa": "<8%"`.

---

## 🟢 MENORES (melhorias de clareza)

### 12. `cenario_cambial` → `chart-cenarios-cambiais` (singular→plural)
**Linha 1979:** O chart key é `cenario_cambial` (singular) mas o canvas ID é `chart-cenarios-cambiais` (plural). Embora funcione (o mapeamento é explícito), a inconsistência de singular/plural pode confundir ao debugar.

### 13. Referência "E4.N" na seção E5.N
**Linha 266 (changelog v4.0):** Descreve "Nova sub-etapa E4.N — Narrativas" mas após renumeração (v4.5) esta etapa se tornou E5.N. A referência no changelog está correta historicamente, mas a seção operacional (linha 1847) já usa "E5.N". Sem problema funcional.

### 14. "14 categorias" de despesa no orçamento prospectivo
**Linha 1485:** *"14 categorias"* — esse número pode mudar se categorias forem adicionadas/removidas no `definitions.md`. Já que o script lê categorias dinamicamente, o manual não precisa fixar o número.

**Ação:** Substituir "14 categorias" por "todas as categorias do `definitions.md`".

### 15. Keywords one-time income hardcoded no script
O `e5_analyze.py` tem keywords como "kiwify" hardcoded para identificar receitas one-time. Deveria vir do `definitions.md` ou `categorization.json` para manter a single source of truth.

### 16. Fallback "Einstein (Mariana - CLT)" hardcoded no e4_categorize.py
A função `get_clt_origin()` retorna uma string hardcoded. Se Mariana mudar de empregador, o script precisa ser editado — deveria ler do `definitions.md`.

### 17. Regras especiais duplicadas entre script e config
As regras para NATHALIACASADE→alimentação e ABDO MOHAMED→saúde estão tanto no `e4_categorize.py` quanto no `definitions.md`. Idealmente estariam apenas no config.

### 18. Data range "Mai/25-Mar/26" hardcoded no report_spec.md
O `report_spec.md` contém referências ao período específico "Mai/25–Mar/26" que deveria ser derivado dinamicamente dos dados do E4.

---

## Resumo por Tipo

| Tipo | Qtd | Exemplos |
|------|-----|----------|
| **Placeholder não resolvido** | 1 | Tabela V1-V18 |
| **Confusão de nomenclatura (E4/E5)** | 12+ ocorrências | "Salvar no E4 JSON" dentro do E5 |
| **Changelog duplicado** | 1 | v5.1→v5.2 aparece 2x |
| **Referência obsoleta pós-renumeração** | 1 | E5.4/E5.5 → E6.4/E6.5 |
| **Valores monetários hardcoded em exemplos** | ~20 valores | Receitas, patrimônio, investimentos |
| **Contagens hardcoded** | 4 | 37 faturas, 14 categorias, 5 imóveis, 17 cards |
| **Faixas numéricas inconsistentes** | 1 | Selic contrafluxo |
| **Dados hardcoded em scripts** | 4 | "Einstein (Mariana - CLT)", kiwify, ABDO MOHAMED, data range |

---

## Recomendação Geral

O manual é excepcionalmente detalhado e bem estruturado — o nível de documentação é raro e valioso. Os problemas encontrados são majoritariamente de **manutenção**: valores de um ciclo específico que se infiltraram nas instruções genéricas, e referências que não foram atualizadas após renumerações.

A correção mais impactante seria resolver a **confusão E4/E5 JSON** (item 2), pois afeta a compreensão de toda a STAGE E5 por qualquer novo operador. A segunda prioridade seria o **placeholder V1-V18** (item 1), que deixa uma lacuna operacional real.
