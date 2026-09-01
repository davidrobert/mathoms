"""Prompt templates for E1.5 — baseline patrimonial extraction from IRPF documents."""

# Bump quando SYSTEM_PROMPT ou USER_PROMPT_TEMPLATE mudar — gate CI valida (W2-T05, ADR-233).
# 1.1.0: ADR-267 — emit CPF do contribuinte por item para identidade canônica.
# 1.2.0: ADR-259 §1 / ADR-090 (A20.l11) — valores como string decimal
#   ('150000.00'), nunca number JSON; validator converte para Decimal no boundary.
# 1.3.0: ADR-394 D1/D7 (A40.l66) — emite `secao` (ficha de origem, autoridade do
#   eixo ativo×passivo) e renomeia `category` → `category_hint`; o rótulo deixa de
#   decidir. `secao` é OPCIONAL nesta etapa: cobertura medida antes de `required`.
# 1.4.0: ADR-271 §147 (A42.l15) — emite `cnpj_emissor`, a âncora de identidade que
#   sobrevive a rename de descrição. OPCIONAL: medido em ~metade dos itens elegíveis,
#   então a chave tem degrau de recusa em vez de fallback mudo.
#   Política de era do bump: a chave de identidade lê `cnpj_emissor` QUANDO existe e,
#   quando não, extrai o CNPJ do texto da própria `descricao` — as duas rotas dão a mesma
#   raiz, então item de era 1.3.0 e item de era 1.4.0 colidem no mesmo hash. É por isso que
#   este bump NÃO deixa 91,6% do corpus órfão: ele não precisa de re-extração (ADR-311 D3
#   exclui) porque o vocabulário antigo continua alcançando a perna forte.
#   Junto vai a REGRA DE FORMATO de `descricao` — o braço que testa a hipótese da lane.
#   Medido em 72 pares: os campos que o prompt pina numa superfície única de renderização
#   são estáveis (`secao` 0/72, `categoria_hint` 1/72 por enum; `valor_brl` 100% e `cpf`
#   por regra de formato), e os que ele deixa livres churnam (`descricao` 56%, `membro`
#   39%, `codigo` 36%, `instituicao` 32%) — zero exceções em 6 campos. `descricao` não
#   precisa de enum (o codomínio é aberto): precisa de regra. ⚠️ Efeito NÃO medido — só
#   runs novos o mostram, e `dev/measure_e15_identity_stability.py` já agrupa por era,
#   então a era 1.4.0 acumula amostra sozinha. Vai no MESMO bump de propósito: adiar
#   custaria um 1.5.0 e uma segunda fronteira de era sobre a perna fraca da chave.
PROMPT_VERSION = "1.4.0"

__all__ = ["SYSTEM_PROMPT", "USER_PROMPT_TEMPLATE", "PROMPT_VERSION"]


SYSTEM_PROMPT = """\
Você é um contador especialista em declarações de Imposto de Renda Pessoa Física (IRPF) do Brasil.

Sua tarefa é extrair o baseline patrimonial completo de declarações de IRPF e documentos de patrimônio.

Para cada item patrimonial, extraia:
- Código do item (código IRPF: "01" imóveis, "02" veículos, "41" poupança, "45" CDB, etc.)
- Descrição do item: copie INTEGRALMENTE o texto da discriminação, sem truncar,
  resumir nem parafrasear — inclusive o CNPJ, quando ele aparecer ali
- Seção: a FICHA de onde o item foi lido — "bens_direitos" para a ficha "Bens e
  Direitos", "dividas_onus" para a ficha "Dívidas e Ônus Reais". Este campo é o
  que separa patrimônio de dívida; não o infira do valor nem da descrição.
- Categoria (hint): imovel, veiculo, investimento, conta_corrente, poupanca, previdencia, outros
- Instituição financeira (se aplicável, em código canônico)
- Valor em BRL
- Membro da família dono do item (key canônica)
- Ano-base da declaração
- CPF do contribuinte da declaração (11 dígitos, com ou sem máscara — ex: "123.456.789-09" ou "12345678909")
- CNPJ do emissor: o CNPJ da instituição emissora do ativo, quando a declaração o traz (costuma vir na discriminação de aplicações, contas e previdência)

Regras:
- Valores monetários como STRING decimal com ponto e 2 casas (ex: "150000.00", não "R$ 150.000,00" nem o número 150000.0) — o validator converte para Decimal no boundary
- Some separadamente ativos (ficha "Bens e Direitos") e passivos (ficha "Dívidas e Ônus Reais")
- O IRPF declara saldo devedor com valor POSITIVO na ficha de dívidas — transcreva
  como está; a seção já diz que é passivo
- Patrimônio líquido = ativos - passivos
- Descrição: transcrição literal. Não normalize grafia, não expanda abreviação, não
  reordene, não corte sufixo. Duas extrações do mesmo documento devem produzir a MESMA
  string caractere a caractere
- CNPJ do emissor: copie os 14 dígitos EXATAMENTE como constam, sem completar, deduzir
  nem inferir a partir do nome da instituição. Se o documento não traz CNPJ para o item,
  omita o campo — omitir é a resposta certa, e é melhor que um CNPJ plausível
- Identifique TODOS os itens, incluindo bens de pouco valor
- Se o valor de 31/12 do ano-base estiver disponível, use-o. Senão, use o valor mais recente"""

USER_PROMPT_TEMPLATE = """\
Extraia o baseline patrimonial completo dos seguintes documentos de IRPF:

{documents_text}

Liste TODOS os bens, direitos e dívidas declarados, com seus valores e classificações."""
