# Glossário de fórmulas (F11.7)

Referência curta para **número ↔ regra**. Detalhes de implementação vivem no motor E5 e nos scripts do pipeline.

| Conceito | Descrição | Onde no código |
| --- | --- | --- |
| Patrimônio líquido | Ativos consolidados menos passivos explícitos no snapshot. | E5 JSON · `patrimonio` |
| Score do relatório | Índice composto a partir de componentes já normalizados no motor. | E5 JSON · `score` |
| Projeção IF (aportes) | Valor futuro de série de aportes com taxa, inflação e horizonte das metas materializadas. | Metas (`goals.json`) · narrativas E5 |

A UI nativa (`ReportPremissasBlock`) replica um subconjunto desta tabela para tooltips e o bloco “Premissas e como calculamos”.
