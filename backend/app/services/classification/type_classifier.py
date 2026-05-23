"""Document-type detection via regex rules (TypeRule priority matching)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TypeRule:
    """A content-based document-type matcher."""

    code: str
    dest_group: str
    required: tuple[re.Pattern, ...]  # ALL must match
    supporting: tuple[re.Pattern, ...]  # at least one boosts confidence to 1.0
    priority: int = 100  # lower = evaluated first


def _c(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I | re.MULTILINE)


# Priority: specific (IRPF, faturas, poupança) → generic (extrato, fatura)
TYPE_RULES: tuple[TypeRule, ...] = (
    # ---------- IRPF / Receita Federal (most specific first) ----------
    TypeRule(
        code="irpfdeclaracao",
        dest_group="income_tax_br",
        # Aceita as variações mais comuns em PDFs gerados pelo PGD/e-CAC:
        #   "Declaração IRPF 20XX", "Declaração de Ajuste Anual",
        #   "Declaração de Imposto de Renda Pessoa Física",
        #   "DIRPF 20XX", "Modelo Completo/Simplificado".
        # Marcadores de suporte cobrem seções internas (Bens e Direitos,
        # Rendimentos Tributáveis, Dependentes, Resumo, etc.).
        required=(
            # Âncoras estritas — sempre começam por "Declaração" ou por "DIRPF"
            # (sigla exclusiva da declaração). Evita colidir com informes
            # financeiros que só mencionam "IRPF 20XX" como ano-calendário.
            _c(
                r"Declara[çc][ãa]o\s*(?:de\s*)?(?:IRPF|"
                r"de\s*Ajuste\s*Anual|"
                r"de\s*Imposto\s*de\s*Renda|"
                r"Pessoa\s*F[ií]sica)"
                r"|\bDIRPF\s*20\d{2}\b"
            ),
        ),
        supporting=(
            _c(r"Bens\s*e\s*Direitos"),
            _c(r"Rendimentos\s*Tribut[aá]veis"),
            _c(r"Rendimentos\s*Isentos"),
            _c(r"Ano-?[Cc]alend[aá]rio"),
            _c(r"Imposto\s*(a\s*)?(Pagar|Restituir)"),
            _c(r"Dependentes"),
            _c(r"Resumo\s*(da\s*)?Declara[çc][ãa]o"),
        ),
        priority=1,
    ),
    TypeRule(
        code="irpfrecibo",
        dest_group="income_tax_br",
        # Recibos da RFB usam formulações variáveis: alguns dizem "Recibo de Entrega
        # da Declaração de Imposto sobre a Renda da Pessoa Física" (sem a sigla "IRPF"
        # inline), outros "Recibo da Entrega da Declaração IRPF". Aceitamos qualquer
        # combinação "Recibo (de|da) Entrega" próxima a "Declaração", "Imposto (de|sobre a)
        # Renda" ou "IRPF" — incluindo a forma curta "Recibo da Declaração".
        required=(
            _c(
                r"Recibo\s*(?:de|da)\s*Entrega.*"
                r"(?:IRPF|Declara[çc][ãa]o|Imposto\s*(?:de|sobre\s*a)\s*Renda|Pessoa\s*F[ií]sica)"
                r"|Recibo\s*da\s*Declara[çc][ãa]o\s*(?:de\s*)?(?:IRPF|Imposto\s*(?:de|sobre\s*a)\s*Renda)"
                r"|IRPF.*Recibo\s*de\s*Entrega"
            ),
        ),
        supporting=(
            _c(r"N[uú]mero\s*do\s*Recibo"),
            _c(r"Hash\s*do\s*Recibo"),
            _c(r"Modelo\s*(?:Completo|Simplificado)"),
            _c(r"Exerc[ií]cio\s*20\d{2}"),
            _c(r"Recibo\s*da\s*Declara[çc][ãa]o"),
        ),
        priority=1,
    ),
    TypeRule(
        code="informerendimentosaluguel",
        dest_group="income_tax_br",
        # QuintoAndar emite o comprovante anual de rendimentos do locador com o
        # cabeçalho "Comprovante anual de rendimentos de aluguéis" — equivalente
        # ao informe IRPF, mas usa "Comprovante" no lugar de "Informe".
        required=(
            _c(r"Informe.*Rendiment|Comprovante\s*anual\s*de\s*rendimentos"),
            _c(r"Aluguel|Locat[áa]rio|Loca[çc][ãa]o"),
        ),
        supporting=(_c(r"Rendimento\s*(Bruto|L[íi]quido)"),),
        priority=2,
    ),
    # ADR-239 (A18 L1) — CRLV-e (Certificado de Registro e Licenciamento de
    # Veículo eletrônico) DENATRAN. Padrão nacional, marcadores fortes.
    # priority=2 alinhada com informe_previdencia_privada (ambos pré-genérico).
    TypeRule(
        code="crlv_eletronico",
        dest_group="comprovantes",
        required=(
            _c(
                r"DENATRAN|Certificado\s*de\s*Registro\s*e\s*Licenciamento"
                r"|Licenciamento\s*de\s*Ve[ií]culo|CRLV-?e?\b|RENAVAM"
            ),
            _c(r"Placa|CRLV-?e?\b"),
        ),
        supporting=(
            _c(r"Categoria\s*[:\-]?\s*(Particular|Comercial|Aluguel|Oficial)"),
            _c(r"Combust[ií]vel"),
            _c(r"Ano\s*Modelo|Ano\s*Fabrica[çc][ãa]o|Exerc[ií]cio"),
            _c(r"Munic[ií]pio\s*de\s*Emplacamento|UF"),
        ),
        priority=2,
    ),
    # ADR-239 (A18 L2) — Apólice de seguro (auto/residencial/combinada).
    # Marcadores fortes SUSEP/Apólice/Cobertura/CNPJ top-5 seguradoras.
    # priority=2 alinhada com crlv_eletronico + informe_previdencia_privada.
    TypeRule(
        code="apolice_seguro",
        dest_group="comprovantes",
        required=(
            _c(
                r"\bAp[oó]lice\b|\bSUSEP\b"
                r"|Bilhete\s*de\s*Seguro"
                r"|Certificado\s*de\s*Seguro"
                r"|Condi[çc][õo]es\s*Gerais.*Seguro"
            ),
            _c(
                r"Cobertura|Pr[êe]mio\s*(L[ií]quido|Total|Bruto)"
                r"|Limite\s*M[aá]ximo\s*(?:de\s*Indeniza[çc][ãa]o|Garantia)"
                r"|\bLMI\b"
            ),
        ),
        supporting=(
            # Top-5 seguradoras brasileiras (catalog institutions).
            _c(
                r"Porto\s*Seguro|Tokio\s*Marine|Bradesco\s*Seguros"
                r"|Ita[uú]\s*Seguros|Zurich\s*(?:Brasil|Minas)"
                r"|Alianz|Mapfre|HDI\s*Seguros|Liberty\s*Seguros|SulAmerica"
            ),
            _c(r"Vig[êe]ncia\s*(?:de|a\s*partir)|In[ií]cio\s*de\s*Vig[êe]ncia"),
            _c(r"Classe\s*de\s*B[oô]nus|Bonifica[çc][ãa]o"),
            _c(r"Segurado|Estipulante|Beneficia(?:rio|do)|Proponente"),
            _c(r"Corretor|Corretora\s*de\s*Seguros"),
            _c(r"Franquia"),
            _c(r"Ramo\s*SUSEP|C[oó]digo\s*Susep"),
        ),
        priority=2,
    ),
    # ADR-238 (A17 L1) — Informe anual de Previdência Privada (PGBL/VGBL).
    # MAIS específico que ``informerendimentos`` genérico abaixo → priority=2
    # garante evaluação antes. Cobre layouts BrasilPrev / Bradesco Vida /
    # Caixa Vida / Icatu / Mongeral / XP Seguros.
    TypeRule(
        code="informe_previdencia_privada",
        dest_group="income_tax_br",
        required=(
            # Pelo menos um marcador forte de produto previdenciário.
            _c(
                r"\bPGBL\b|\bVGBL\b"
                r"|Previd[êe]ncia\s*Privada\s*(?:Complementar)?"
                r"|Plano\s*Gerador\s*de\s*Benef[ií]cio\s*Livre"
                r"|Vida\s*Gerador\s*de\s*Benef[ií]cio\s*Livre"
            ),
        ),
        supporting=(
            _c(r"Tabela\s*Regressiva|Regime\s*Regressivo|Tributa[çc][ãa]o\s*Definitiva"),
            _c(r"Tabela\s*Progressiva|Regime\s*Progressivo|Tributa[çc][ãa]o\s*Compens[aá]vel"),
            _c(r"Contribui[çc][õo]es\s*(no\s*ano|anuais|do\s*per[ií]odo)"),
            _c(r"Saldo\s*(em\s*31[/-]12|de\s*reserva|acumulado)"),
            _c(r"Certificado|Proposta|Ap[oó]lice|N[uú]mero\s*do\s*Plano"),
            _c(r"BrasilPrev|Bradesco\s*Vida|Caixa\s*Vida|Icatu|" r"Mongeral|XP\s*Seguros"),
        ),
        priority=2,
    ),
    # ADR-238 A17 L2 P2 — informe Financeiro PJ. Cobre dois layouts:
    # (a) Comprovante Lei 9.249/95 (adquirentes Stone/Cielo/Rede com vendas
    #     brutas + retenções IRRF/CSLL/PIS/COFINS) e
    # (b) Demonstrativo de saldo PJ (Stone/C6 PJ: saldo 31/12 + rendimentos
    #     sujeitos à tributação exclusiva).
    # Priority=2 alinhada com previdencia (required exclusivo: marcadores
    # de PJ — Pessoa Jurídica beneficiária ou Comprovante Lei 9.249).
    TypeRule(
        code="informe_financeiro_pj",
        dest_group="income_tax_br",
        required=(
            _c(
                r"Comprovante\s*de\s*Rendimentos\s*Pagos\s*e\s*de\s*Reten[çc][ãa]o"
                r"|Pessoa\s*Jur[ií]dica\s*benefici[áa]ria(?:\s*dos\s*rendimentos)?"
                r"|Lei\s*9[.,]?249"
            ),
        ),
        supporting=(
            _c(
                r"CSLL\s*(?:retid[ao]|recolhid[ao])|PIS\s*(?:retid[ao]|recolhid[ao])"
                r"|COFINS\s*(?:retid[ao]|recolhid[ao])|IRRF\s*(?:retid[ao]|recolhid[ao])"
            ),
            _c(
                r"Stone|Cielo|Rede(?:cred)?|GetNet|PagSeguro|Mercado\s*Pago"
                r"|C6\s*Bank|C6\s*PJ|Banco\s*Origin\s*PJ"
            ),
            _c(r"Simples\s*Nacional|Lucro\s*Presumido|DAS\b|CNAE"),
            _c(
                r"Vendas\s*brutas|Volume\s*processado|TPV|"
                r"Antecipa[çc][ãa]o\s*de\s*receb[íi]veis|MDR"
            ),
            _c(
                r"Saldo\s*em\s*31[/-]12|Tributa[çc][ãa]o\s*Exclusiva|APLICA[ÇC][ÃA]O\s*DE\s*RENDA\s*FIXA"
            ),
            _c(r"Fonte\s*pagadora|Estabelecimento\s*aderente|Estabelecimento\s*contratado"),
        ),
        priority=2,
    ),
    # ADR-238 A17 L3 P2 — informe Financeiro PF (4 quadros RFB + Wise). Priority=2
    # disputa com PJ via required exclusivo: Wise isolado (sem contexto fiscal) NÃO casa.
    TypeRule(
        code="informe_financeiro_pf",
        dest_group="income_tax_br",
        priority=2,
        required=(
            _c(
                r"Informe\s*de\s*Rendimentos\s*Financeiros|Informe\s*Anual\s*de\s*Rendimentos"
                r"|(?:Wise\s*Brasil|Avenue\s*Securities|Nomad\s*Pagamentos|Stake\s*BR)"
                r"[\s\S]{0,200}(?:saldo\s*em\s*moeda\s*estrangeira|conta\s*no\s*exterior"
                r"|Saldo\s*em\s*31[/-]12|moeda:\s*USD)"
            ),
        ),
        supporting=(
            _c(r"Rendimentos\s*Tribut[aá]veis|Quadro\s*1"),
            _c(r"Rendimentos\s*Isentos\s*e\s*N[ãa]o\s*Tribut[aá]veis|Quadro\s*2"),
            _c(r"Tributa[çc][ãa]o\s*Exclusiva|Quadro\s*3"),
            _c(r"Bens\s*e\s*Direitos|Quadro\s*4"),
            _c(r"Pessoa\s*F[íi]sica|titular\s*pessoa\s*f[íi]sica|CPF[\s:]*[\d\*]"),
            _c(r"Ita[úu]|Santander|Caixa\s*Econ|Nubank|PicPay|C6\s*Bank|XP\s*Investimentos|Rico"),
            _c(r"USD|EUR|GBP|moeda\s*estrangeira|conta\s*no\s*exterior|PTAX"),
        ),
    ),
    # Legacy `informerendimentos` (priority=3) deletado em A17 L3 P2 (ADR-238) —
    # `informe_financeiro_pf` (priority=2) subsume. Mapping de compat em
    # `document_classification._map_informe` mantido para dados antigos.
    # ---------- Fatura de aluguel (specific before cartão) ----------
    TypeRule(
        code="faturaaluguel",
        dest_group="financial_statements",
        # "Faturas de aluguel" (plural) é o cabeçalho do PDF do QuintoAndar.
        required=(_c(r"Faturas?\s*de\s*Aluguel|Boleto\s*de\s*Aluguel"),),
        supporting=(_c(r"Locador|Locat[áa]rio|QuintoAndar"),),
        priority=5,
    ),
    # ---------- Fatura de cartão ----------
    TypeRule(
        code="faturaunique",
        dest_group="financial_statements",
        # Dois formatos possíveis do Santander Unique:
        # (a) PDF de fatura: contém "SANTANDER UNIQUE" no cabeçalho.
        # (b) CSV de exportação do app: header exato "data,lançamento,valor"
        #     (3 colunas em português, datas no formato YYYY-MM-DD) — esse
        #     formato é exclusivo do export CSV do Santander Unique e não
        #     contém nenhum marcador institucional explícito.
        required=(
            _c(
                r"SANTANDER\s*UNIQUE|Cart[ãa]o\s*Santander\s*Unique"
                r"|^\ufeff?data,lan[çc]amento,valor\s*$"  # CSV header (Santander Unique app, com/sem BOM)
            ),
        ),
        supporting=(
            _c(r"Total\s*a\s*Pagar"),
            _c(r"Vencimento\s*(da)?\s*Fatura"),
            _c(r"Limite\s*(de)?\s*Cr[eé]dito"),
            _c(r"PAGAMENTO EFETUADO"),  # entrada de pagamento no CSV
            _c(r"\d{4}-\d{2}-\d{2},"),  # data no formato ISO no CSV
        ),
        priority=10,
    ),
    TypeRule(
        code="faturacarbon",
        dest_group="financial_statements",
        # Dois formatos possíveis do C6 Carbon:
        # (a) PDF de fatura: contém "C6 Carbon" no cabeçalho.
        # (b) CSV de exportação: colunas "Valor (em US$)" + "Cotação (em R$)"
        #     na mesma linha — exclusivo do extrato CSV do cartão Carbon.
        required=(_c(r"C6\s*Carbon" r"|Valor\s*\(em\s*US\$\).*Cota[çc][ãa]o\s*\(em\s*R\$\)"),),
        supporting=(
            _c(r"Subtotal\s*deste\s*cart[ãa]o"),
            _c(r"Vencimento\s*da\s*Fatura"),
            _c(r"Total\s*desta\s*Fatura"),
            _c(r"Data\s+de\s+Compra"),  # CSV: coluna de data da transação
            _c(r"Final\s+do\s+Cart[ãa]o"),  # CSV: coluna com 4 últimos dígitos
        ),
        priority=10,
    ),
    TypeRule(
        code="faturapaoacucar",
        dest_group="financial_statements",
        required=(_c(r"P[ãa]o\s*de\s*A[çc][uú]car|Cart[ãa]o\s*Pao\s*de\s*A[çc]ucar"),),
        supporting=(
            _c(r"Total\s*desta\s*fatura"),
            _c(r"Lan[çc]amentos\s*atuais"),
            _c(r"Vencimento"),
        ),
        priority=10,
    ),
    # Santander — cartões que não são "Unique" (Elite, Free, etc.): texto costuma
    # misturar "Cartão de Crédito" + vencimento sem a palavra FATURA na 1ª página.
    TypeRule(
        code="faturasantander",
        dest_group="financial_statements",
        required=(
            _c(r"BANCO\s+SANTANDER|BANCO\s+SANTANDER\s+S\.?\s*A\.?|SANTANDER\s+BRASIL"),
            _c(
                r"(?:\bFATURA\b|Fatura\s+[Dd]igital|Resumo\s+da\s+[Ff]atura|"
                r"Demonstrativo\s+de\s+[Ff]atura|"
                r"Data\s+de\s+[Vv]encimento|Vencimento\s+(?:da\s+)?[Ff]atura|"
                r"Total\s+a\s+Pagar|Total\s+da\s+[Ff]atura|"
                r"Pagamento\s+[Mm][íi]nimo|Limite\s+(?:de\s+)?Cr[eé]dito|"
                r"Cart[ãa]o\s+de\s+Cr[eé]dito)"
            ),
        ),
        supporting=(
            _c(r"R\$\s*[\d\.\s]+|R\$\s*[\d,\.]+"),
            _c(r"Lan[çc]amentos|Compras|Parcelas|rotativo|final\s*\d{4}"),
        ),
        priority=11,
    ),
    # Generic fatura de cartão — um único padrão OR (evita exigir \bFATURA\b + linha
    # financeira ao mesmo tempo, o que falhava em muitos PDFs reais).
    TypeRule(
        code="fatura",
        dest_group="financial_statements",
        required=(
            _c(
                r"(?:"
                r"(?:\bFATURA\b|Fatura\s+[Dd]igital|Demonstrativo\s+da\s+[Ff]atura)"
                r".{0,1200}?"
                r"(?:Total\s*(?:a\s*Pagar|da\s*Fatura|desta\s*Fatura)|"
                r"Vencimento\s*(?:da\s*)?\s*[Ff]atura|Data\s+de\s+[Vv]encimento|"
                r"Limite\s*(?:de\s*)?\s*Cr[eé]dito|Pagamento\s*[Mm][íi]nimo)"
                r"|"
                r"Cart[ãa]o\s+de\s+Cr[eé]dito"
                r".{0,2600}?"
                r"(?:Total\s+a\s*Pagar|Total\s+da\s+[Ff]atura|"
                r"Vencimento\s+(?:da\s+)?[Ff]atura|Data\s+de\s+[Vv]encimento|"
                r"Pagamento\s+[Mm][íi]nimo|Limite\s+(?:de\s+)?Cr[eé]dito|"
                r"\bFATURA\b)"
                r")"
            ),
        ),
        supporting=(
            _c(r"Cart[ãa]o|Cr[eé]dito|Final\s*\d{4}"),
            _c(r"Lan[çc]amentos|Compras|Parcelas|R\$\s*[\d\.,]+"),
        ),
        priority=21,
    ),
    # ---------- Investimentos (CDB, posição, renda fixa) ----------
    TypeRule(
        code="investimentosposicao",
        dest_group="financial_statements",
        required=(_c(r"Posi[çc][ãa]o\s*(Consolidada|de\s*Investimentos|de\s*Carteira)"),),
        supporting=(
            _c(r"Renda\s*Fixa|Renda\s*Vari[aá]vel|Fundos\s*de\s*Investimento"),
            _c(r"Saldo\s*(Total|Consolidado)"),
        ),
        priority=15,
    ),
    TypeRule(
        code="carteirarendafixa",
        dest_group="financial_statements",
        required=(_c(r"Carteira\s*(de\s*)?Renda\s*Fixa"),),
        supporting=(_c(r"Vencimento"), _c(r"Rentabilidade")),
        priority=15,
    ),
    TypeRule(
        code="cdbdetalhes",
        dest_group="financial_statements",
        required=(_c(r"\bCDB\b|Certificado\s*de\s*Dep[oó]sito\s*Banc[aá]rio"),),
        supporting=(
            _c(r"Dispon[ií]vel\s*para\s*Resgate"),
            _c(r"Rentabilidade"),
            _c(r"Vencimento"),
            _c(r"Valor\s*(Total|Aplicado|Bruto)"),
        ),
        priority=18,
    ),
    # ---------- Extratos bancários ----------
    TypeRule(
        code="extratopoupanca",
        dest_group="financial_statements",
        required=(_c(r"Extrato.*Poupan[çc]a|Conta\s*Poupan[çc]a|Caderneta\s*de\s*Poupan[çc]a"),),
        supporting=(_c(r"Rendimento"), _c(r"Saldo\s*Anterior|Saldo\s*Atual")),
        priority=25,
    ),
    TypeRule(
        code="extratocontaglobalusd",
        dest_group="financial_statements",
        required=(
            _c(r"Extrato.*(Global|Internacional)|Account\s*Statement"),
            _c(r"US\$|USD\b|Dollar|D[oó]lar"),
        ),
        supporting=(_c(r"Saldo|Balance"),),
        priority=25,
    ),
    TypeRule(
        code="extratocontaglobaleur",
        dest_group="financial_statements",
        required=(
            _c(r"Extrato.*(Global|Internacional)|Account\s*Statement"),
            _c(r"€|EUR\b|Euro"),
        ),
        supporting=(_c(r"Saldo|Balance"),),
        priority=25,
    ),
    # Bank of America style statement (English)
    TypeRule(
        code="extratocontausd",
        dest_group="financial_statements",
        required=(
            _c(r"Account\s*Statement|Account\s*number"),
            _c(r"Beginning\s*balance|Ending\s*balance"),
        ),
        supporting=(_c(r"Transaction|Deposit|Withdrawal"),),
        priority=28,
    ),
    # Caixa Econômica Federal — "Extrato por período" (texto visível ou via LLM vision).
    # Dois formatos: PDFs com camada de texto (usam razão social ou CEF) e PDFs
    # somente-imagem (classificados pelo LLM via vision — regra usada apenas para
    # validação pós-LLM, não precisa de match regex).
    # Marcadores de suporte cobrem campos canônicos do extrato CEF: "Conta",
    # "Período" e rodapés de serviço "Alô CAIXA" / "SAC CAIXA".
    TypeRule(
        code="extratoconta",
        dest_group="financial_statements",
        required=(_c(r"CAIXA\s*ECON[ÔO]MICA\s*FEDERAL|CEF\b|Al[oô]\s*CAIXA|SAC\s*CAIXA"),),
        supporting=(
            _c(r"Extrato\s*por\s*per[ií]odo|Lan[çc]amentos\s*do\s*dia"),
            _c(r"SALDO\s*(ANTERIOR|DO\s*DIA|ATUAL)"),
            _c(r"Per[ií]odo\s*(dos\s*lan[çc]amentos)?"),
            _c(r"Conta\s*[:\-]?\s*\d"),  # "Conta: 00012345-6"
            _c(r"0800\s*726"),  # central de atendimento CEF
        ),
        priority=27,
    ),
    # Generic extrato de conta corrente (Brazilian).
    # Inclui marcadores específicos do XLS exportado pelo Itaú Internet Banking:
    #   - "Logotipo Itaú" na linha 0 (cabeçalho fixo do XLS do Itaú)
    #   - "lançamento.*saldos (R$)" nos títulos de coluna (linha 8 do XLS)
    # Esses marcadores permitem classificação sem depender da palavra "EXTRATO",
    # que não aparece no formato XLS do Itaú.
    TypeRule(
        code="extratoconta",
        dest_group="financial_statements",
        required=(
            _c(
                r"EXTRATO\s*(DA\s*CONTA|DE\s*CONTA|CORRENTE)?"
                r"|Lan[çc]amentos\s*(da\s*)?Conta"
                r"|Movimenta[çc][õo]es"
                r"|Logotipo\s+Ita[uú]"  # Itaú XLS: cabeçalho fixo linha 0
                r"|lan[çc]amento.*saldos?\s*\(R\$\)"  # Itaú XLS: título da coluna "saldos (R$)"
            ),
        ),
        supporting=(
            _c(r"SALDO\s*(ANTERIOR|DO\s*DIA|DISPON[IÍ]VEL?|FINAL|ATUAL)"),
            _c(r"Ag[êe]ncia\s*[:\-]?\s*\d+.*Conta\s*[:\-]?\s*[\d-]+"),
            _c(r"Per[ií]odo\s*:?\s*\d{2}/\d{2}/\d{4}"),
            _c(r"Atualiza[çc][ãa]o\s*:"),  # Itaú XLS: "Atualização: DD/MM/YYYY"
        ),
        priority=30,
    ),
)


def detect_type_by_content(text: str) -> tuple[TypeRule | None, int, int]:
    """Return (best rule, required_matches, supporting_matches).

    Evaluates rules in priority order. The first rule whose REQUIRED patterns
    all match wins — supporting matches just adjust confidence.
    """
    for rule in sorted(TYPE_RULES, key=lambda r: r.priority):
        req_matches = sum(1 for p in rule.required if p.search(text))
        if req_matches < len(rule.required):
            continue
        sup_matches = sum(1 for p in rule.supporting if p.search(text))
        return rule, req_matches, sup_matches
    return None, 0, 0


def compute_confidence(rule: TypeRule, req: int, sup: int) -> float:
    """All required + ≥1 supporting → 1.0; all required + 0 supporting → 0.85 (≥2 req) or 0.7."""
    if req < len(rule.required):
        return 0.0
    if sup >= 1:
        return 1.0
    return 0.85 if len(rule.required) >= 2 else 0.7
