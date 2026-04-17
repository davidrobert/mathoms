# Template — atualização de incidente em andamento

**Status sugerido na status page:** Identified / Monitoring / Em mitigação (conforme ferramenta)

---

## Texto para usuários (copiar e ajustar)

**Atualização — {{INCIDENT_ID}}**

**Situação:** {{RESUMO_UMA_FRASE}}

**Impacto atual:** {{QUEM_AINDA_AFETA}}

**Mitigação / workaround:** {{PASSOS_QUE_USUARIO_PODE_TENTAR_OU_NENHUM}}

**Próxima atualização:** {{ETA_NEXT_UPDATE}}

---

## Exemplo preenchido (fictício)

**Atualização — INC-2026-04-17-001**

**Situação:** identificamos contenção na fila Redis; estamos escalando o worker e limpando jobs presos.

**Impacto atual:** novos processamentos podem continuar lentos até concluirmos a mitigação.

**Mitigação / workaround:** evite iniciar vários pipelines ao mesmo tempo; se um run ficar mais de 45 minutos sem progresso, cancele e tente novamente após 15 minutos.

**Próxima atualização:** em 45 minutos ou ao estabilizar, o que ocorrer primeiro.
