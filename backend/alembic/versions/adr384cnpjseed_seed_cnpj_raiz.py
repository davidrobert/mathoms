"""ADR-384: seed de cnpj_raiz no institution_catalog (A40.l40).

Revision ID: adr384cnpjseed
Revises: adr384cnpjraiz
Create Date: 2026-08-12

Valores compilados em 2026-08-12 por pesquisa com dupla derivação
independente (duas rodadas cegas; divergência anula) + âncoras verificadas
em documentos fiscais reais do dogfood (cnpj_emissor dos informes / IRPF).
Correção de valor é SEMPRE migration nomeada com motivo (ADR-384 §4) —
nunca update in-place nem endpoint admin.

Casos com decisão registrada:
- ``rico`` e ``xpinvestimentos`` compartilham a raiz 02332886 — a própria
  Rico documenta que o informe sai no CNPJ da XP CCTVM (incorporação); o
  resolvedor mapeia raiz → CONJUNTO de codes por isso.
- ``wise`` usa 40571694 (Wise Brasil Instituição de Pagamento — é o
  cnpj_emissor que os informes reais carregam), não a corretora de câmbio.
- ``btgdigital`` fica NULL: as duas derivações divergiram (CTVM 43815158 ×
  banco 30306294); retomada quando um informe real do produto aparecer.
- ``bankofamerica`` / ``stake`` / ``interinvestusa`` ficam NULL: conta
  internacional sem entidade BR emissora de informe/extrato PF.
- ``binance`` usa 68757681 (Sim;paul CCVM, entidade BR regulada adquirida
  com aprovação do BC em jan/2025).
- ``sicoob`` usa o Banco Cooperativo (02038232); informes podem sair no
  CNPJ da cooperativa singular do associado — fallback por token cobre.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "adr384cnpjseed"
down_revision: Union[str, Sequence[str], None] = "adr384cnpjraiz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CNPJ_RAIZ_POR_CODE: dict[str, str] = {
    # bancos
    "bradesco": "60746948",
    "c6bank": "31872495",
    "caixa": "00360305",
    "inter": "00416968",
    "itau": "60701190",
    "nubank": "18236120",
    "picpay": "22896431",
    "santander": "90400888",
    # corretoras
    "agora": "74014747",
    "btgpactual": "30306294",
    "genial": "27652684",
    "modal": "05389174",
    "nuinvest": "62169875",
    "pi": "03502968",
    "rico": "02332886",
    "toro": "29162769",
    "warren": "92875780",
    "xpinvestimentos": "02332886",
    # exchange
    "binance": "68757681",
    # cooperativas
    "sicoob": "02038232",
    "sicredi": "01181521",
    # fintechs / contas de pagamento
    "stone": "16501555",
    "wise": "40571694",
    "interpag": "22177858",
    "mercadopago": "10573521",
    "picpayinvest": "07138049",
    # contas internacionais com entidade BR
    "avenue": "61384004",
    "nomad": "34662852",
    # holding pagadora (proventos) — verificada na discriminação do IRPF real
    "itausa": "61532644",
}


# SQL literal (valores são constantes validadas pelo pattern abaixo) — params
# bound renderizam como NULL no modo offline `alembic upgrade --sql`.
def upgrade() -> None:
    for code, raiz in _CNPJ_RAIZ_POR_CODE.items():
        assert code.isascii() and code.replace("_", "").isalnum(), code
        assert len(raiz) == 8 and raiz.isdigit(), raiz
        op.execute(
            sa.text(
                f"UPDATE institution_catalog SET cnpj_raiz = '{raiz}' "
                f"WHERE code = '{code}' AND cnpj_raiz IS NULL"
            )
        )


def downgrade() -> None:
    for code in _CNPJ_RAIZ_POR_CODE:
        op.execute(
            sa.text(f"UPDATE institution_catalog SET cnpj_raiz = NULL WHERE code = '{code}'")
        )
