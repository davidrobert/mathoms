"""RV4-45 (A42.l3) — "não consegui medir" tem exit próprio, nunca o 0 de "medi e passou"."""

from __future__ import annotations

import pytest

from dev.de01_finops_parity_audit import (
    _ENV_DB,
    EXIT_INDETERMINADO,
    EXIT_MISMATCH,
    EXIT_OK,
    _env_ausente,
    _run_audit,
    main,
)


def test_o_codigo_de_indeterminado_e_distinto_de_ok_e_de_mismatch() -> None:
    """Ancora o LITERAL. Comparar `main()` contra a própria constante deixava o teste
    passar se alguém redefinisse `EXIT_INDETERMINADO = 0` — foi a mutação que a primeira
    versão deste arquivo NÃO pegou."""
    assert (EXIT_OK, EXIT_MISMATCH, EXIT_INDETERMINADO) == (0, 1, 3)


def test_sem_env_var_a_auditoria_e_indeterminada(monkeypatch: pytest.MonkeyPatch) -> None:
    """O default SQLite CRIA um arquivo vazio: a tabela "não existe", e a auditoria saía
    0 — indistinguível de paridade confirmada. A condição vivia só no docstring."""
    monkeypatch.delenv(_ENV_DB, raising=False)

    assert _env_ausente() is True
    assert main() == 3


def test_com_env_var_a_pre_condicao_deixa_de_ser_indeterminada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(_ENV_DB, "sqlite:///qualquer.db")

    assert _env_ausente() is False


def test_tabela_ausente_no_banco_apontado_tambem_e_indeterminado() -> None:
    """Segundo ramo do mesmo falso-verde: env var certa, banco sem a tabela."""

    class _SemTabela:
        def get_bind(self):
            from sqlalchemy import create_engine

            return create_engine("sqlite://", future=True)

    assert _run_audit(_SemTabela()) == 3
