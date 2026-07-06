/**
 * Registry de copy por code (ADR-165 onda 3) — extraído de validation-copy.ts
 * para manter cada arquivo abaixo do limite de 500 linhas (CLAUDE.md).
 *
 * Não importe daqui; importe de `@/lib/validation-copy` (público).
 */

export interface ValidationCopy {
  title: string;
  cardSummary: string;
  description: string;
  whyItMatters?: string;
  suggestedAction: string;
}

export const E16_COPY: Record<string, ValidationCopy> = {
  "e16.pii.unmasked_cpf": {
    title: "Documento exposto na declaração",
    cardSummary: "Número de documento exposto em ${section_label}",
    description:
      "Encontramos um número de documento (CPF) sem máscara em ${section_label}. " +
      "Para sua proteção, ele precisa aparecer apenas com os dígitos do meio (ex: 123.***.**-45).",
    whyItMatters:
      "CPFs visíveis em campos livres podem vazar em logs ou exportações — a LGPD exige mascaramento.",
    suggestedAction: "Mascarar documento",
  },
  "e16.reconcile.ir_pago_divergente": {
    title: "Imposto pago não bate com retenções",
    cardSummary:
      "Imposto pago (R$ ${ir_pago_brl}) difere das retenções em R$ ${diff_brl}",
    description:
      "O imposto pago informado é R$ ${ir_pago_brl}, mas a soma das retenções dos rendimentos " +
      "chega a R$ ${soma_retidos_brl} — uma diferença de R$ ${diff_brl}. Pode haver carnê-leão " +
      "não lançado ou um valor digitado errado.",
    whyItMatters:
      "Quando esses números divergem, a análise de carga tributária e a projeção de restituição saem distorcidas.",
    suggestedAction: "Conferir valores de retenção",
  },
  "e16.imposto.exclusivos_simultaneos": {
    title: "Imposto a pagar e a restituir ao mesmo tempo",
    cardSummary: "Declaração tem imposto a pagar e a restituir simultâneos",
    description:
      "A declaração mostra R$ ${ir_a_pagar_brl} a pagar e R$ ${ir_a_restituir_brl} a restituir " +
      "no mesmo exercício. Pela regra da Receita, apenas um dos dois pode existir — provavelmente " +
      "um deles foi extraído por engano.",
    whyItMatters:
      "Manter os dois zera o cálculo de fluxo de caixa fiscal e quebra o gráfico de carga tributária.",
    suggestedAction: "Revisar imposto apurado",
  },
  "e16.pgbl.deducao_em_simplificado": {
    title: "Dedução de PGBL no modelo simplificado",
    cardSummary: "PGBL com dedução não permitida no modelo simplificado",
    description:
      "Identificamos um pagamento de PGBL com R$ ${valor_dedutivel_brl} marcado como dedutível, " +
      "mas a declaração está no modelo simplificado — esse modelo não aceita deduções de previdência privada.",
    whyItMatters:
      "Se a dedução for considerada, a projeção de restituição fica inflada e a recomendação de aporte sai errada.",
    suggestedAction: "Zerar dedução ou trocar modelo",
  },
  "e16.dependente.idade_acima_do_limite": {
    title: "Dependente acima do limite de idade",
    cardSummary: "${nome} tem ${idade} anos — acima do limite RFB",
    description:
      "O dependente ${nome} está com ${idade} anos. A Receita aceita filhos como dependentes até " +
      "21 anos (ou 24 se cursando ensino superior). Confirme se essa informação ainda vale para o exercício declarado.",
    whyItMatters:
      "Dependente fora do limite mantém a dedução, mas pode gerar malha fina e revisão da declaração.",
    suggestedAction: "Confirmar ou remover dependente",
  },
  "e16.confidence.out_of_range": {
    title: "Indicador de confiança inválido",
    cardSummary: "Indicador de confiança da leitura está inválido",
    description:
      "O nível de confiança da leitura automática chegou em ${confidence}, fora do intervalo " +
      "esperado (0 a 1). Isso costuma indicar um problema de extração — vale revisar a declaração inteira antes de aprovar.",
    whyItMatters:
      "Sem um indicador de confiança válido, não conseguimos sinalizar quando a leitura precisa de revisão extra.",
    suggestedAction: "Revisar declaração completa",
  },
  "e16.contribuinte.exercicio_anterior_a_ano_base": {
    title: "Exercício anterior ao ano-base",
    cardSummary: "Exercício ${exercicio} é anterior ao ano-base ${ano_base}",
    description:
      "A declaração mostra exercício ${exercicio} e ano-base ${ano_base} — o exercício deve " +
      "ser igual ou posterior ao ano-base (normalmente um ano depois). Provavelmente um dos dois foi lido errado do PDF.",
    whyItMatters:
      "Ano-base errado faz a declaração entrar no período fiscal incorreto e quebra o cruzamento com extratos.",
    suggestedAction: "Corrigir ano da declaração",
  },
  "e16.contribuinte.exercicio_distante_de_ano_base": {
    title: "Distância incomum entre exercício e ano-base",
    cardSummary: "Exercício ${exercicio} está distante do ano-base ${ano_base}",
    description:
      "Exercício ${exercicio} e ano-base ${ano_base} costumam diferir em apenas um ano. A diferença " +
      "atual é maior — pode ser um caso real (declaração retroativa) ou erro de leitura. Confirme antes de aprovar.",
    suggestedAction: "Confirmar ano da declaração",
  },
};

export const E1_COPY: Record<string, ValidationCopy> = {
  "e1.members.empty": {
    title: "Nenhum membro identificado",
    cardSummary: "Nenhum membro da família foi identificado",
    description:
      "Não conseguimos extrair nenhum membro da família dos documentos enviados. Verifique se os " +
      "documentos pessoais (RG, CPF, comprovantes) foram processados.",
    suggestedAction: "Revisar documentos enviados",
  },
  "e1.member.invalid_key": {
    title: "Identificador interno inválido",
    cardSummary: "Identificador de membro com formato inválido",
    description:
      "O identificador interno gerado para um membro tem formato inesperado. Isso costuma resolver-se reprocessando.",
    suggestedAction: "Reprocessar membros",
  },
  "e1.member.duplicate_key": {
    title: "Identificador de membro duplicado",
    cardSummary: "Dois membros foram identificados com a mesma chave",
    description:
      "Dois membros foram extraídos com o mesmo identificador. Provavelmente são a mesma pessoa lida duas vezes.",
    suggestedAction: "Mesclar ou separar membros",
  },
  "e1.member.empty_full_name": {
    title: "Nome completo em branco",
    cardSummary: "Membro sem nome completo identificado",
    description:
      "Não foi possível ler o nome completo de um membro nos documentos enviados.",
    suggestedAction: "Adicionar nome manualmente",
  },
  "e1.member.empty_short_name": {
    title: "Nome curto em branco",
    cardSummary: "Membro sem nome de exibição",
    description: "Não foi possível identificar um nome curto de exibição para um dos membros.",
    suggestedAction: "Adicionar nome de exibição",
  },
  "e1.member.unexpected_role": {
    title: "Papel familiar incomum",
    cardSummary: "Papel familiar '${role}' não é padrão",
    description:
      "O papel '${role}' identificado não está entre os padrões (titular, cônjuge, filho, dependente). Pode ser leitura inesperada do documento.",
    suggestedAction: "Ajustar papel familiar",
  },
  "e1.member.invalid_cpf": {
    title: "CPF com formato inesperado",
    cardSummary: "CPF de um membro tem formato inesperado",
    description:
      "O CPF lido para um membro não tem 11 dígitos. Pode ser erro de OCR ou número parcial.",
    suggestedAction: "Conferir CPF",
  },
  "e1.member.invalid_birth_date": {
    title: "Data de nascimento mal formatada",
    cardSummary: "Data de nascimento com formato inesperado",
    description:
      "A data de nascimento de um membro não está no formato esperado (AAAA-MM-DD).",
    suggestedAction: "Corrigir data",
  },
  "e1.account.missing_institution": {
    title: "Instituição financeira não identificada",
    cardSummary: "Conta sem instituição associada",
    description:
      "Uma conta foi extraída sem identificação da instituição financeira. Sem isso, ela não entra na consolidação.",
    suggestedAction: "Indicar instituição",
  },
  "e1.account.non_standard_type": {
    title: "Tipo de conta incomum",
    cardSummary: "Tipo de conta '${account_type}' não é padrão",
    description:
      "O tipo de conta '${account_type}' não está entre os padrões esperados (extrato, cartão, investimento, poupança).",
    suggestedAction: "Ajustar tipo de conta",
  },
  "e1.titular.unknown_key": {
    title: "Titular não está entre os membros",
    cardSummary: "Titular indicado não foi encontrado nos membros",
    description:
      "A declaração indica um titular que não está na lista de membros extraídos. Confirme quem é o titular principal.",
    suggestedAction: "Indicar titular",
  },
  "e1.titular.missing": {
    title: "Sem titular identificado",
    cardSummary: "Nenhum membro foi marcado como titular",
    description:
      "Nenhum dos membros extraídos está marcado como titular da declaração. Confirme quem é o responsável principal.",
    suggestedAction: "Indicar titular",
  },
  "e1.titular.multiple": {
    title: "Mais de um titular identificado",
    cardSummary: "Mais de um membro foi marcado como titular",
    description:
      "Dois ou mais membros estão marcados como titular. Em uma declaração apenas um deve ocupar essa posição.",
    suggestedAction: "Ajustar titular único",
  },
};

export const E15_COPY: Record<string, ValidationCopy> = {
  "e15.items.empty": {
    title: "Nenhum bem ou direito identificado",
    cardSummary: "Nenhum item patrimonial foi identificado",
    description:
      "Não conseguimos extrair nenhum bem ou direito da declaração. Verifique se a ficha de Bens e Direitos está completa.",
    suggestedAction: "Revisar bens e direitos",
  },
  "e15.item.empty_code": {
    title: "Item sem código",
    cardSummary: "Item ${index} sem código RFB",
    description: "Um item foi extraído sem o código padrão da Receita.",
    suggestedAction: "Adicionar código",
  },
  "e15.item.empty_description": {
    title: "Item sem descrição",
    cardSummary: "Item ${index} sem descrição",
    description: "Um item foi extraído sem texto de descrição.",
    suggestedAction: "Adicionar descrição",
  },
  "e15.item.non_standard_category": {
    title: "Categoria de item incomum",
    cardSummary: "Categoria '${category}' não é padrão",
    description:
      "A categoria '${category}' não está entre as padrão (imóvel, veículo, investimento, conta, poupança, previdência, outros).",
    suggestedAction: "Ajustar categoria",
  },
  "e15.item.missing_member_key": {
    title: "Item sem dono identificado",
    cardSummary: "Item ${index} sem membro associado",
    description:
      "Um item patrimonial foi identificado sem indicação de qual membro da família é o proprietário.",
    suggestedAction: "Associar a um membro",
  },
  "e15.item.invalid_year": {
    title: "Ano-base do item inválido",
    cardSummary: "Item ${index} com ano ${year} fora do esperado",
    description:
      "O ano de referência ${year} de um item está fora da faixa razoável (2000–2100). Pode ser erro de OCR.",
    suggestedAction: "Corrigir ano",
  },
  "e15.totals.assets_mismatch": {
    title: "Total de ativos não bate",
    cardSummary: "Total de ativos divergente da soma dos itens",
    description:
      "O total de ativos declarado (R$ ${total_assets_brl}) não bate com a soma dos itens positivos (R$ ${computed_assets_brl}).",
    whyItMatters:
      "Diferença em totais quebra a consolidação patrimonial e a evolução por ano-base.",
    suggestedAction: "Conferir totais",
  },
  "e15.totals.net_worth_mismatch": {
    title: "Patrimônio líquido não bate",
    cardSummary: "Patrimônio líquido difere de ativos − passivos",
    description:
      "O valor declarado de patrimônio líquido não corresponde a ativos menos passivos.",
    suggestedAction: "Recalcular patrimônio líquido",
  },
  "e15.contribuinte.invalid_reference_year": {
    title: "Ano de referência inválido",
    cardSummary: "Ano de referência da declaração está inválido",
    description:
      "O ano de referência ${reference_year} da declaração está fora do esperado.",
    suggestedAction: "Corrigir ano de referência",
  },
};

export const E2LLM_COPY: Record<string, ValidationCopy> = {
  "e2llm.missing.source_file": {
    title: "Arquivo de origem ausente",
    cardSummary: "Arquivo de origem do extrato não foi identificado",
    description:
      "A leitura automática não conseguiu identificar qual arquivo gerou esta extração.",
    suggestedAction: "Reenviar documento",
  },
  "e2llm.missing.institution": {
    title: "Instituição não identificada",
    cardSummary: "Instituição do extrato não foi identificada",
    description: "Não foi possível identificar qual banco ou corretora gerou este documento.",
    suggestedAction: "Indicar instituição",
  },
  "e2llm.empty.no_data": {
    title: "Documento sem dados extraídos",
    cardSummary: "Nenhuma transação ou investimento foi identificado",
    description:
      "O documento foi processado mas nenhuma transação ou investimento foi extraído. Pode ser página em branco ou formato incomum.",
    suggestedAction: "Revisar documento",
  },
  "e2llm.invalid_period_format": {
    title: "Período do extrato malformatado",
    cardSummary: "Período do extrato com formato inesperado: '${period}'",
    description:
      "O período '${period}' do extrato não está no formato AAAAMM esperado.",
    suggestedAction: "Conferir período",
  },
  "e2llm.transaction.invalid_date": {
    title: "Data de transação mal formatada",
    cardSummary: "Transação ${index} com data inválida",
    description:
      "Uma transação tem data '${date}' fora do formato AAAA-MM-DD esperado.",
    suggestedAction: "Corrigir data da transação",
  },
  "e2llm.transaction.empty_description": {
    title: "Transação sem descrição",
    cardSummary: "Transação ${index} sem descrição",
    description: "Uma transação foi extraída sem texto descritivo.",
    suggestedAction: "Adicionar descrição",
  },
  "e2llm.transaction.zero_amount": {
    title: "Transação com valor zero",
    cardSummary: "Transação ${index} com valor zero",
    description: "Uma transação foi extraída com valor zero — pode indicar erro de leitura.",
    suggestedAction: "Conferir valor",
  },
  "e2llm.investment.non_standard_type": {
    title: "Tipo de investimento incomum",
    cardSummary: "Investimento ${index} com tipo não padrão",
    description:
      "Um investimento foi extraído com tipo fora dos padrões esperados.",
    suggestedAction: "Ajustar tipo",
  },
  "e2llm.investment.missing_institution": {
    title: "Investimento sem instituição",
    cardSummary: "Investimento ${index} sem instituição",
    description: "Um investimento foi extraído sem identificação da instituição financeira.",
    suggestedAction: "Indicar instituição",
  },
  "e2llm.investment.non_positive_value": {
    title: "Investimento com valor não positivo",
    cardSummary: "Investimento ${index} com valor zero ou negativo",
    description: "Um investimento foi extraído com valor menor ou igual a zero.",
    suggestedAction: "Conferir valor",
  },
  "e2llm.investment.invalid_applied_date": {
    title: "Data de aplicação mal formatada",
    cardSummary: "Investimento ${index} com data de aplicação inválida",
    description: "A data de aplicação não está no formato AAAA-MM-DD esperado.",
    suggestedAction: "Corrigir data",
  },
  "e2llm.investment.invalid_maturity_date": {
    title: "Data de vencimento mal formatada",
    cardSummary: "Investimento ${index} com data de vencimento inválida",
    description: "A data de vencimento não está no formato AAAA-MM-DD esperado.",
    suggestedAction: "Corrigir data",
  },
};

/** Reasons de reconciliação (E3) projetadas de ReviewReason (ADR-272/ADR-308).
 * Codes são `ReviewReasonCode` (família cross-stage), não `e3.*`. */
export const REVIEW_REASON_COPY: Record<string, ValidationCopy> = {
  "extract.missing_required_field": {
    title: "Instituição não identificada",
    cardSummary: "Documento sem banco ou corretora identificável",
    description:
      "Não foi possível dizer de qual banco ou corretora este documento veio. " +
      "Sem essa informação, ele fica de fora da consolidação das suas contas.",
    whyItMatters:
      "Documentos sem instituição não entram no patrimônio nem no fluxo de caixa — os totais do relatório ficam menores do que a realidade.",
    suggestedAction: "Indicar a instituição",
  },
  "dedup.sentinel_period": {
    title: "Período do documento fora do esperado",
    cardSummary: "Período lido não corresponde a datas plausíveis",
    description:
      "O período lido neste documento não bate com um intervalo de datas plausível. " +
      "Costuma ser leitura errada da capa do extrato ou fatura — confira o mês de referência.",
    whyItMatters:
      "Com o período errado, as transações caem no mês errado e distorcem o fluxo de caixa.",
    suggestedAction: "Conferir o período",
  },
  "domain.balance_gap": {
    title: "Saldo não continua entre extratos",
    cardSummary: "Saldo final de um extrato difere do inicial do seguinte",
    description:
      "O saldo final de um extrato não bate com o saldo inicial do extrato seguinte da mesma conta. " +
      "Pode faltar um extrato no meio, ou um dos documentos foi lido com erro.",
    whyItMatters:
      "Descontinuidade de saldo indica movimentações não capturadas — o fluxo de caixa do período pode estar incompleto.",
    suggestedAction: "Conferir a sequência de extratos",
  },
  "domain.temporal_gap": {
    title: "Período sem extrato",
    cardSummary: "Há dias sem cobertura entre dois extratos da mesma conta",
    description:
      "Existe um intervalo de dias sem nenhum extrato entre dois documentos da mesma conta. " +
      "Provavelmente falta enviar o extrato desse período.",
    whyItMatters:
      "Meses sem extrato aparecem com movimentação zerada e puxam as médias do relatório para baixo.",
    suggestedAction: "Enviar o extrato que falta",
  },
  "domain.anachronic_transaction": {
    title: "Transações fora do período",
    cardSummary: "Transações muito anteriores ao período foram descartadas",
    description:
      "Algumas transações deste documento têm datas muito anteriores ao período dele e foram " +
      "descartadas por segurança. Costuma ser saldo anterior ou lançamento retroativo lido como transação.",
    whyItMatters:
      "Se as datas estiverem certas e o descarte for indevido, uma parte da movimentação fica de fora.",
    suggestedAction: "Conferir as datas no documento",
  },
  "domain.baseline_divergence": {
    title: "Saldo difere da declaração",
    cardSummary: "Saldo do extrato em 31/12 difere do declarado no IRPF",
    description:
      "O saldo deste extrato em 31/12 não bate com o valor declarado no imposto de renda para a mesma conta. " +
      "Um dos dois pode estar desatualizado ou ter sido lido com erro.",
    whyItMatters:
      "A declaração é a referência do patrimônio inicial — divergências propagam para a evolução patrimonial.",
    suggestedAction: "Conferir extrato e declaração",
  },
};

export const LEGACY_COPY: ValidationCopy = {
  title: "Item identificado pelo sistema",
  cardSummary: "Item para revisar nesta etapa",
  description:
    "O sistema sinalizou um item nesta etapa que ainda não tem descrição amigável. " +
    "Veja o detalhe técnico abaixo e revise a fonte se necessário.",
  suggestedAction: "Ver detalhes",
};
