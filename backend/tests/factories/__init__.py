"""Test data factories — F6.5 (sub-fase 6.5F.2).

Por que factories e não pytest fixtures por entidade?
- Overrides parciais sem repetir o setup
- Ergonomia para tests de multi-tenant (criar 2 workspaces ≠ paramétrico)
- Defaults LGPD-safe (CPF placeholder, e-mail @test.com, valores fictícios)
- Composição: `make_workspace` chama `make_user` se `owner` não passado

Convenção:
- Funções `make_*(db, **overrides) -> Model`
- Counters em escopo de processo geram IDs/emails únicos por test run
- Se o test precisar de IDs determinísticos, passe via overrides

Uso típico:

    from backend.tests.factories import make_user, make_workspace, make_member

    async def test_isolation(db):
        u_a = await make_user(db)
        u_b = await make_user(db)
        ws_a = await make_workspace(db, owner=u_a)
        ws_b = await make_workspace(db, owner=u_b)
        await make_member(db, workspace=ws_a, full_name="Pessoa A")
        await make_member(db, workspace=ws_b, full_name="Pessoa B")
        # ... assert que endpoints de A não retornam dados de B

Reset entre tests: `setup_db` autouse fixture já dropa schema.
Counters não precisam reset porque IDs novos vêm do uuid4 do model;
counters só servem para sufixar emails/keys e evitar colisão com unique
constraints quando o mesmo factory é chamado várias vezes no mesmo test.
"""

from .builders import (
    make_bank_account,
    make_category,
    make_document,
    make_llm_config,
    make_member,
    make_notification,
    make_report,
    make_run,
    make_stage_log,
    make_user,
    make_vault_password,
    make_workspace,
    reset_counters,
)

__all__ = [
    "make_bank_account",
    "make_category",
    "make_document",
    "make_llm_config",
    "make_member",
    "make_notification",
    "make_report",
    "make_run",
    "make_stage_log",
    "make_user",
    "make_vault_password",
    "make_workspace",
    "reset_counters",
]
