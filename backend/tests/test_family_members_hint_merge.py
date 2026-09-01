"""Merge do hint de IRPF no `family_members.json` (A40.l96 · [[ADR-430]] §2)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.models  # noqa: F401
from backend.app.core.database import Base
from backend.app.core.security import hash_password
from backend.app.models.family_member import (
    BankAccount,
    FamilyMember,
    WorkspaceIrpfSuggestionDismissal,
)
from backend.app.models.pipeline_artifact import PipelineArtifact
from backend.app.models.pipeline_run import PipelineRun
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.services.config_materializer import serialize_family_members

sync_engine = create_engine("sqlite://", echo=False)
SyncTestSession = sessionmaker(bind=sync_engine)


@pytest.fixture(autouse=True)
def setup_sync_db():
    Base.metadata.create_all(sync_engine)
    yield
    Base.metadata.drop_all(sync_engine)


@pytest.fixture
def db():
    session = SyncTestSession()
    yield session
    session.close()


@pytest.fixture
def workspace(db) -> Workspace:
    user = User(email="hint@test.com", hashed_password=hash_password("x"), full_name="Hint")
    db.add(user)
    db.flush()
    ws = Workspace(name="Hint WS", owner_id=user.id)
    db.add(ws)
    db.commit()
    return ws


def _seed_titular(db, ws_id: str, *, key: str, short_name: str) -> FamilyMember:
    m = FamilyMember(
        workspace_id=ws_id,
        key=key,
        full_name=short_name + " Souza",
        short_name=short_name,
        role="titular",
        order=0,
    )
    db.add(m)
    db.flush()
    return m


def _seed_e1_artifact(db, ws_id: str, contas: list[dict]) -> None:
    """ADR-371: a row-pai do FK (pipeline_run) é materializada, não inventada."""
    run = PipelineRun(id="run-hint-1", workspace_id=ws_id, status="completed")
    db.add(run)
    db.flush()
    db.add(
        PipelineArtifact(
            workspace_id=ws_id,
            pipeline_run_id=run.id,
            stage="extract_members",
            artifact_key="members",
            content_json={"membros": {}, "contas": contas},
        )
    )
    db.commit()


def _conta_e1(member_key: str, inst: str, num: str | None = None) -> dict:
    return {
        "member_key": member_key,
        "institution_code": inst,
        "account_type": "extratoconta",
        "account_number_raw": num,
        "agency": None,
        "is_joint": False,
        "co_titulares": [],
    }


class TestMergeIrpfHints:
    """O pipeline funde exatamente os hints que a UI ofereceria — nem mais, nem menos."""

    def test_workspace_sem_curadoria_deixa_de_publicar_carteira_sem_dono(self, db, workspace):
        # O defeito da lane: `bank_accounts` vazio fazia o E4 receber mapa vazio
        # e o relatório afirmar que a carteira não tem dono.
        _seed_titular(db, workspace.id, key="rafael_souza", short_name="Rafael")
        db.commit()
        assert (serialize_family_members(workspace.id, db) or {}).get("contas") is None

        _seed_e1_artifact(db, workspace.id, [_conta_e1("rafael", "itau", "12345-6")])
        result = serialize_family_members(workspace.id, db)
        assert len(result["contas"]) == 1
        assert result["contas"][0]["origem"] == "irpf_hint"

    def test_chave_curta_do_e1_vira_canonica_no_merge(self, db, workspace):
        _seed_titular(db, workspace.id, key="rafael_souza", short_name="Rafael")
        db.commit()
        _seed_e1_artifact(db, workspace.id, [_conta_e1("rafael", "itau")])
        result = serialize_family_members(workspace.id, db)
        assert result["contas"][0]["member_key"] == "rafael_souza"

    def test_conta_ja_curada_nao_entra_duas_vezes(self, db, workspace):
        m = _seed_titular(db, workspace.id, key="rafael_souza", short_name="Rafael")
        db.add(
            BankAccount(
                member_id=m.id,
                workspace_id=workspace.id,
                institution_code="itau",
                account_type="extratoconta",
                account_number="12345-6",
            )
        )
        db.commit()
        _seed_e1_artifact(db, workspace.id, [_conta_e1("rafael", "itau", "12345-6")])
        result = serialize_family_members(workspace.id, db)
        assert len(result["contas"]) == 1, "match exato: a curada vence, o hint não duplica"
        assert result["contas"][0].get("origem", "curada") == "curada"

    def test_conta_recusada_pelo_usuario_nao_ressuscita(self, db, workspace):
        # ADR-229 §3: a tabela de dismissals É o registro do "não" do usuário.
        _seed_titular(db, workspace.id, key="rafael_souza", short_name="Rafael")
        db.commit()
        _seed_e1_artifact(db, workspace.id, [_conta_e1("rafael", "itau", "12345-6")])
        row = db.query(PipelineArtifact).one()
        db.add(
            WorkspaceIrpfSuggestionDismissal(
                workspace_id=workspace.id,
                irpf_year=row.created_at.year - 1,
                institution_code="itau",
                account_number_norm="123456",
            )
        )
        db.commit()
        assert (serialize_family_members(workspace.id, db) or {}).get("contas") is None

    def test_chave_nao_resolvivel_preserva_o_bruto_em_vez_de_sumir(self, db, workspace):
        """Descartar o hint fabricaria atribuição FALSA — ver A40.l96 §Achados do PR2c."""
        # `davi` tem 4 chars e o short_name difere: cai abaixo de
        # `_MIN_SUBSTRING_LEN`. Preservado, a instituição fica com 2 chaves
        # distintas e vira `ambiguous`; descartado, viraria singleton e seria
        # atribuída ao membro errado.
        _seed_titular(db, workspace.id, key="rafael_souza", short_name="Rafael")
        db.commit()
        _seed_e1_artifact(
            db,
            workspace.id,
            [_conta_e1("rafael", "itau", "111"), _conta_e1("davi", "itau", "222")],
        )
        result = serialize_family_members(workspace.id, db)
        chaves = {c["member_key"] for c in result["contas"]}
        assert chaves == {"rafael_souza", "davi"}, "o não-resolvível sobrevive como bruto"

    def test_sem_artefato_e1_o_blob_nao_muda(self, db, workspace):
        m = _seed_titular(db, workspace.id, key="rafael_souza", short_name="Rafael")
        db.add(
            BankAccount(
                member_id=m.id,
                workspace_id=workspace.id,
                institution_code="itau",
                account_type="extratoconta",
            )
        )
        db.commit()
        result = serialize_family_members(workspace.id, db)
        assert len(result["contas"]) == 1
        assert "origem" not in result["contas"][0]


# =============================================================================
# Hook de lag pós-E1 ([[ADR-430]] §5)
# =============================================================================


class TestRefreshFamilyMembersOverride:
    """`config_overrides` congela uma vez por run — sem reinjeção o hint atrasa um run."""

    def _ctx(self, overrides):
        from types import SimpleNamespace

        return SimpleNamespace(config_overrides=overrides)

    def test_reinjeta_apos_extract_members(self, monkeypatch):
        from backend.app.tasks import pipeline_task as pt

        monkeypatch.setattr(pt, "SyncSessionLocal", lambda: _FakeSession())
        monkeypatch.setattr(
            "backend.app.services.pipeline.pipeline_adapter._family_members_override",
            lambda ws, db: {"membros": {}, "contas": [{"institution_code": "itau"}]},
        )
        ctx = self._ctx({"family_members.json": {"membros": {}}})
        pt._refresh_family_members_override(ctx, "ws-1", "extract_members")
        assert len(ctx.config_overrides["family_members.json"]["contas"]) == 1

    def test_nao_reinjeta_em_outro_stage(self, monkeypatch):
        from backend.app.tasks import pipeline_task as pt

        monkeypatch.setattr(pt, "SyncSessionLocal", lambda: _FakeSession())
        ctx = self._ctx({"family_members.json": {"membros": {}}})
        pt._refresh_family_members_override(ctx, "categorize_transactions", "x")
        assert "contas" not in ctx.config_overrides["family_members.json"]

    def test_tolera_contexto_sem_overrides(self, monkeypatch):
        from backend.app.tasks import pipeline_task as pt

        monkeypatch.setattr(pt, "SyncSessionLocal", lambda: _FakeSession())
        pt._refresh_family_members_override(self._ctx(None), "ws-1", "extract_members")


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
