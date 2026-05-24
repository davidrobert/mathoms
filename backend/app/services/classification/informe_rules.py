"""TypeRules dos 4 informes anuais canônicos (ADR-238 A17 L1-L4) — extraídos de type_classifier.py."""

from __future__ import annotations

import re

from backend.app.services.classification._type_rule import TypeRule


def _c(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.I | re.MULTILINE)


# ADR-238 L1 — Previdência Privada (PGBL/VGBL).
INFORME_PREVIDENCIA_RULE = TypeRule(
    code="informe_previdencia_privada",
    dest_group="income_tax_br",
    required=(
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
        _c(r"BrasilPrev|Bradesco\s*Vida|Caixa\s*Vida|Icatu|Mongeral|XP\s*Seguros"),
    ),
    priority=2,
)

# ADR-238 L2 — Financeiro PJ (Comprovante Lei 9.249/95 + saldo PJ).
INFORME_PJ_RULE = TypeRule(
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
        _c(r"Vendas\s*brutas|Volume\s*processado|TPV|Antecipa[çc][ãa]o\s*de\s*receb[íi]veis|MDR"),
        _c(
            r"Saldo\s*em\s*31[/-]12|Tributa[çc][ãa]o\s*Exclusiva|APLICA[ÇC][ÃA]O\s*DE\s*RENDA\s*FIXA"
        ),
        _c(r"Fonte\s*pagadora|Estabelecimento\s*aderente|Estabelecimento\s*contratado"),
    ),
    priority=2,
)

# ADR-238 L3 — Financeiro PF (4 quadros RFB + Wise multi-moeda).
INFORME_PF_RULE = TypeRule(
    code="informe_financeiro_pf",
    dest_group="income_tax_br",
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
    priority=2,
)

# ADR-238 L4 — Proventos Ações (XP/BTG/Itaúsa).
INFORME_PROVENTOS_RULE = TypeRule(
    code="informe_proventos_acoes",
    dest_group="income_tax_br",
    required=(
        _c(
            r"Relat[óo]rio\s*de\s*Proventos|Informe\s*de\s*Proventos"
            r"|Rendimentos\s*de\s*FII|Aviso\s*aos\s*Acionistas"
            r"|Proventos\s*de\s*A[çc][õo]es"
        ),
    ),
    supporting=(
        _c(r"Dividendo|JCP|Juros\s*sobre\s*Capital\s*Pr[óo]prio|Bonifica[çc][ãa]o"),
        _c(r"Rendimento\s*de\s*FII|Fundo\s*Imobili[áa]rio|FII\b"),
        _c(r"[A-Z]{4,5}[0-9]{1,2}\b"),  # ticker B3 (WEGE3, ITSA4, MXRF11)
        _c(r"XP\s*Investimentos|BTG\s*Pactual|Ita[úu]sa|Bradespar|Rico\s*Corretora"),
        _c(r"CNPJ\s*do\s*Pagador|Fonte\s*Pagadora|Custodiante"),
        _c(r"Data\s*do\s*Pagamento|Data\s*Com|Data\s*Ex"),
    ),
    priority=2,
)


#: Tupla das 4 rules canônicas A17 — ordem preserva tie-breaking quando required overlapping.
A17_INFORME_RULES: tuple[TypeRule, ...] = (
    INFORME_PREVIDENCIA_RULE,
    INFORME_PJ_RULE,
    INFORME_PROVENTOS_RULE,
    INFORME_PF_RULE,
)
