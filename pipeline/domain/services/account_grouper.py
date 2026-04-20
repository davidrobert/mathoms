"""Account grouping for E3 (Fase 6 foundation · Sessão A1).

Extrai ``get_account_key`` (e3_reconcile.py:245) e ``should_skip_extract``
(e3_reconcile.py:219) em um único service que decide:

1. Se um extrato E2 deve ser ignorado pela reconciliação (``should_skip``).
2. Qual ``AccountKey`` ele recebe — chave usada para agrupar extratos
   sobrepostos da mesma conta antes de deduplicar transações.

A chave é um value object frozen (``AccountKey``), não tuple. Faturas
expressam ``currency=None``, contas usam BRL/USD/EUR/etc.

Toda configuração — equivalences, skip_types, fatura_allowed — é injetada via
``AccountGrouperConfig`` (R9/ISP). Default safe permite uso sem config para
testes pontuais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Defaults — alinhados ao legado (e3_reconcile.py::_init_config)
# =============================================================================


_DEFAULT_SKIP_TYPES: frozenset[str] = frozenset(
    {
        "investimentosposicao",
        "carteirarendafixa",
        "cdbdetalhes",
        "cdbresumo",
        "faturaaluguel",
        "informerendimentos",
        "irpf",
    }
)

_DEFAULT_FATURA_ALLOWED: frozenset[str] = frozenset(
    {"faturacarbon", "faturaunique", "faturapaoacucar"}
)


# =============================================================================
# Value object: chave de agregação
# =============================================================================


@dataclass(frozen=True)
class AccountKey:
    """Identifica unicamente uma conta para agregação cross-arquivo.

    - ``bank``: nome do banco como aparece no extrato (forma livre).
    - ``account_type``: tipo já normalizado via ``account_type_equivalences``.
    - ``currency``: ``None`` para faturas (cartão tem moeda implícita BRL e
      o legado não inclui moeda na chave); preenchido para contas correntes,
      poupanças, contas globais etc.
    """

    bank: str
    account_type: str
    currency: str | None

    @property
    def is_fatura(self) -> bool:
        return self.account_type.startswith("fatura")

    def to_tuple(self) -> tuple:
        """Forma compatível com o legado (``get_account_key`` retornava tuple)."""
        if self.currency is None:
            return (self.bank, self.account_type)
        return (self.bank, self.account_type, self.currency)


# =============================================================================
# Config (R9/ISP — não recebe StageConfig inteiro)
# =============================================================================


@dataclass(frozen=True)
class AccountGrouperConfig:
    """Parâmetros para agrupamento e skip de extratos.

    Sources no legado:
    - ``account_type_equivalences``: ``config/family_members.json``.
    - ``skip_types``: ``config/pipeline.json::reconciliation.skip_types``
      (defaults hardcoded em ``e3_reconcile._init_config``).
    - ``fatura_allowed``: hardcoded no legado em ``should_skip_extract``.
    - ``default_currency``: hardcoded ``"BRL"`` no legado.
    """

    account_type_equivalences: dict[str, str] = field(default_factory=dict)
    skip_types: frozenset[str] = _DEFAULT_SKIP_TYPES
    fatura_allowed: frozenset[str] = _DEFAULT_FATURA_ALLOWED
    default_currency: str = "BRL"

    @classmethod
    def from_pipeline_config(
        cls,
        family: dict | None = None,
        pipeline: dict | None = None,
    ) -> "AccountGrouperConfig":
        family = family or {}
        pipeline = pipeline or {}
        equiv = family.get("account_type_equivalences") or {}
        # Strip linhas de comentário tipo "_comment".
        equiv_clean = {
            str(k): str(v)
            for k, v in equiv.items()
            if not str(k).startswith("_")
        }
        recon = pipeline.get("reconciliation") or {}
        skip_types_raw = recon.get("skip_types")
        skip_types = (
            frozenset(skip_types_raw) if skip_types_raw else _DEFAULT_SKIP_TYPES
        )
        return cls(
            account_type_equivalences=equiv_clean,
            skip_types=skip_types,
        )


# =============================================================================
# Service
# =============================================================================


class AccountGrouper:
    """Decide skip e calcula ``AccountKey`` de um dict E2.

    Stateless além da config. Pode ser instanciado uma vez e reutilizado.
    """

    def __init__(self, config: AccountGrouperConfig | None = None) -> None:
        self._config = config or AccountGrouperConfig()

    # -- Skip --

    def should_skip(self, data: Any) -> bool:
        """Replica ``e3_reconcile.should_skip_extract`` linha por linha.

        Returns ``True`` para:
        - Não-dict.
        - ``tipo`` em ``skip_types`` (direto ou via equivalence).
        - ``tipo`` que começa com ``"fatura"`` mas não está em ``fatura_allowed``.
        """
        if not isinstance(data, dict):
            return True

        tipo = (data.get("tipo") or "").strip()
        if tipo in self._config.skip_types:
            return True

        tipo_equiv = self._config.account_type_equivalences.get(tipo, tipo)
        if tipo_equiv in self._config.skip_types:
            return True

        if tipo.startswith("fatura") and tipo not in self._config.fatura_allowed:
            return True

        return False

    # -- Key --

    def key(self, data: dict) -> AccountKey | None:
        """Retorna ``AccountKey`` ou ``None`` se inválido (sem banco/tipo).

        - Banco lido de ``banco`` ou ``instituicao``.
        - Tipo normalizado via ``account_type_equivalences``.
        - Faturas: ``currency=None`` (não compõe a chave).
        - Contas: moeda lida de ``moeda`` ou ``conta.moeda``; default
          ``BRL`` quando ausente.
        """
        bank = (data.get("banco") or data.get("instituicao") or "").strip()
        tipo = (data.get("tipo") or "").strip()
        if not bank or not tipo:
            return None

        tipo_normalized = self._config.account_type_equivalences.get(tipo, tipo)

        if tipo_normalized.startswith("fatura"):
            return AccountKey(bank=bank, account_type=tipo_normalized, currency=None)

        moeda = (data.get("moeda") or "").strip()
        if not moeda:
            conta = data.get("conta")
            if isinstance(conta, dict):
                moeda = (conta.get("moeda") or "").strip()
        if not moeda:
            moeda = self._config.default_currency

        return AccountKey(
            bank=bank, account_type=tipo_normalized, currency=moeda.upper()
        )

    # -- Convenience --

    def normalize_account_type(self, tipo: str) -> str:
        """Aplica ``account_type_equivalences`` isoladamente."""
        return self._config.account_type_equivalences.get(tipo, tipo)
