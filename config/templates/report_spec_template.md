# Report Spec — Pipeline {{NOME_FAMILIA}}
## Versão: 1.0 — {{DATA_CRIACAO}}

---

## ESPECIFICAÇÕES TÉCNICAS

- **Formato:** Um único arquivo .html autocontido
- **Bibliotecas via CDN:**
  - Chart.js 4.4.0
  - chartjs-plugin-datalabels 2.2.0
  - Turndown.js 7.1.3 (HTML→Markdown export)
  - Google Fonts (Inter + Plus Jakarta Sans)

---

## DESIGN SYSTEM

### Fontes
- **Títulos e KPIs:** Plus Jakarta Sans
- **Corpo:** Inter

### Modo dual
- Modo Estratégico: análise completa com 10 seções + 5 apêndices
- Modo Tático: acompanhamento operacional com 6 seções (T1-T6)

### Tema
- Suporte a Light/Dark/System (padrão: System)

### Seções colapsáveis
- Todas as seções são colapsáveis com animação suave

---

## CABEÇALHO (COVER HERO)

- Badge "RELATÓRIO CONFIDENCIAL"
- 4 meta-cards: Família, Período de Referência, Data e Hora de Geração, Versão Manual Operações
- 8 KPI cards principais

---

## REGRAS DE GERAÇÃO

- `{{COVER_DATA_HORA}}` deve ser atualizado a cada geração do relatório
- `{{COVER_VERSAO_MANUAL}}` deve ler a versão do manual_operacao.md
- `{{COVER_PERIODO}}` deve ser atualizado quando novos arquivos financeiros são processados
- Nenhum dado financeiro deve estar hardcoded no template

---

## SISTEMA DE EXPORTAÇÃO

### Export Markdown
- Turndown.js converte HTML→Markdown
- Filtra por data-mode do modo ativo
- Substitui canvas por placeholder [Gráfico: nome]

### Export PDF
- window.print() com CSS otimizado para impressão
