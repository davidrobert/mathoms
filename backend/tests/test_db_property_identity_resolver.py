"""Tests — ``DBPropertyIdentityResolver`` (ADR-215 P2 + ADR-225 §2 loose-match)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models import PropertyIdentity, User, Workspace
from backend.app.services.db_property_identity_resolver import (
    DBPropertyIdentityResolver,
)
from pipeline.domain.types.property_identity import PropertyLookupKey


@pytest.fixture
def sync_db(tmp_path):
    db_file = tmp_path / "test_dbpir.db"
    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_workspace(factory, ws_id: str | None = None) -> Workspace:
    ws_id = ws_id or str(uuid.uuid4())
    with factory() as s:
        user = User(
            id=str(uuid.uuid4()),
            email=f"u-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        s.add(user)
        s.flush()
        ws = Workspace(id=ws_id, name="Test WS", owner_id=user.id)
        s.add(ws)
        s.commit()
        s.refresh(ws)
        return ws


def _build_property(ws: Workspace, **kw) -> PropertyIdentity:
    canonical = kw.get("endereco_canonical", "exemplo 100")
    return PropertyIdentity(
        id=str(uuid.uuid4()),
        workspace_id=ws.id,
        titular_key=kw.get("titular_key", "david_robert"),
        codigo_rfb=kw.get("codigo_rfb", "12"),
        endereco_canonical=canonical,
        first_seen_year=2023,
        descricao_sample=kw.get("descricao", "CASA - RUA EXEMPLO, 100"),
        low_confidence=canonical is None,
        created_at=datetime.now(timezone.utc),
    )


def _seed_property(factory, ws: Workspace, **kw) -> PropertyIdentity:
    with factory() as s:
        prop = _build_property(ws, **kw)
        s.add(prop)
        s.commit()
        s.refresh(prop)
        return prop


def _new_lookup(**kw) -> PropertyLookupKey:
    return PropertyLookupKey(
        titular_key=kw.get("titular_key", "david_robert"),
        codigo_rfb=kw.get("codigo_rfb", "12"),
        endereco_canonical=kw.get("endereco_canonical", "exemplo 100"),
    )


def _resolve(factory, workspace_id, lookup, descricao="X", year=2024):
    with factory() as session:
        resolver = DBPropertyIdentityResolver(session=session)
        return resolver.match_or_create(
            workspace_id=workspace_id,
            lookup=lookup,
            first_seen_year=year,
            descricao_sample=descricao,
        )


class TestStrictMatch:
    """Comportamento original ADR-215 P2 — match exato preservado."""

    def test_reuses_when_codigo_and_canonical_match(self, sync_db):
        ws = _seed_workspace(sync_db)
        existing = _seed_property(sync_db, ws, codigo_rfb="12", endereco_canonical="exemplo 100")
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            record = resolver.match_or_create(
                workspace_id=ws.id,
                lookup=PropertyLookupKey(
                    titular_key="david_robert",
                    codigo_rfb="12",
                    endereco_canonical="exemplo 100",
                ),
                first_seen_year=2024,
                descricao_sample="CASA -X",
            )
            assert record.property_id == existing.id


class TestLooseMatchCrossCodigoRFB:
    """ADR-225 §2 — loose-match cobre cross-fonte mesma propriedade."""

    def test_reuses_row_with_different_codigo_rfb(self, sync_db):
        ws = _seed_workspace(sync_db)
        existing = _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="exemplo 320")
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            record = resolver.match_or_create(
                workspace_id=ws.id,
                lookup=_new_lookup(codigo_rfb="01", endereco_canonical="exemplo 320"),
                first_seen_year=2024,
                descricao_sample="Apt QuintoAndar 894",
            )
            assert record.property_id == existing.id
            assert record.codigo_rfb == "11"  # first-write-wins

    def test_first_write_wins_preserva_codigo_mais_antigo(self, sync_db):
        ws = _seed_workspace(sync_db)
        existing = _seed_property(sync_db, ws, codigo_rfb="01", endereco_canonical="exemplo 2192")
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            record = resolver.match_or_create(
                workspace_id=ws.id,
                lookup=_new_lookup(codigo_rfb="11", endereco_canonical="exemplo 2192"),
                first_seen_year=2024,
                descricao_sample="APTO - AV EXEMPLO 2192",
            )
            assert record.property_id == existing.id
            assert record.codigo_rfb == "01"  # preserva invariante E5

    def test_strict_match_precede_loose(self, sync_db):
        ws = _seed_workspace(sync_db)
        row_loose = _seed_property(sync_db, ws, codigo_rfb="01", endereco_canonical="paulista 1500")
        row_strict = _seed_property(
            sync_db, ws, codigo_rfb="11", endereco_canonical="paulista 1500"
        )
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            record = resolver.match_or_create(
                workspace_id=ws.id,
                lookup=_new_lookup(codigo_rfb="11", endereco_canonical="paulista 1500"),
                first_seen_year=2024,
                descricao_sample="X",
            )
            assert record.property_id == row_strict.id
            assert record.property_id != row_loose.id


class TestLooseMatchDoesNotCrossWorkspaces:
    """Garantia de tenancy — loose-match não vaza entre workspaces."""

    def test_workspaces_isolated(self, sync_db):
        ws1 = _seed_workspace(sync_db)
        ws2 = _seed_workspace(sync_db)
        _seed_property(sync_db, ws1, codigo_rfb="11", endereco_canonical="paulista 1500")
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            record = resolver.match_or_create(
                workspace_id=ws2.id,
                lookup=PropertyLookupKey(
                    titular_key="x",
                    codigo_rfb="01",
                    endereco_canonical="paulista 1500",
                ),
                first_seen_year=2024,
                descricao_sample="Y",
            )
            # ws2 não vê row do ws1 — insere nova.
            assert record.workspace_id == ws2.id


# Inverte o contrato da ADR-225 §3 (emendada em 2026-08-11): a ausência de
# canonical inseria row nova a cada run, e o backfill que "cuidaria disso" era
# revertido pelo run seguinte.
class TestLowConfidenceInserts:
    """endereco_canonical=None agrupa por amostra bruta byte-exata (ADR-385)."""

    def test_same_descricao_reuses_identity_when_canonical_is_none(self, sync_db):
        ws = _seed_workspace(sync_db)
        lookup = _new_lookup(titular_key="x", codigo_rfb="12", endereco_canonical=None)
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            r1 = resolver.match_or_create(ws.id, lookup, 2023, "CASA Bairro Exemplo")
            r2 = resolver.match_or_create(ws.id, lookup, 2024, "CASA Bairro Exemplo")
            assert r1.property_id == r2.property_id
            assert r1.low_confidence is True and r2.low_confidence is True

    def test_different_descricao_still_inserts(self, sync_db):
        ws = _seed_workspace(sync_db)
        lookup = _new_lookup(titular_key="x", codigo_rfb="12", endereco_canonical=None)
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            r1 = resolver.match_or_create(ws.id, lookup, 2023, "CASA Bairro Exemplo")
            r2 = resolver.match_or_create(ws.id, lookup, 2024, "TERRENO Outro Bairro")
            assert r1.property_id != r2.property_id

    def test_empty_descricao_never_matches_another_empty(self, sync_db):
        """Guard A3: descricao_sample é nullable — vazio não é identidade."""
        ws = _seed_workspace(sync_db)
        lookup = _new_lookup(titular_key="x", codigo_rfb="12", endereco_canonical=None)
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            r1 = resolver.match_or_create(ws.id, lookup, 2023, "")
            r2 = resolver.match_or_create(ws.id, lookup, 2024, "")
            assert r1.property_id != r2.property_id

    def test_descricao_integra_sobrevive_sem_truncagem(self, sync_db):
        """Guard A4: a coluna guarda a descrição-fonte íntegra — truncar muda identidade."""
        ws = _seed_workspace(sync_db)
        lookup = _new_lookup(titular_key="x", codigo_rfb="12", endereco_canonical=None)
        longa = "CASA " + ("descricao cartorial generica " * 20)
        assert len(longa) > 255
        with sync_db() as session:
            resolver = DBPropertyIdentityResolver(session=session)
            r1 = resolver.match_or_create(ws.id, lookup, 2023, longa)
            row = session.get(PropertyIdentity, r1.property_id)
            assert row.descricao_sample == longa


class TestFuzzyMatchCanonicalProximity:
    """ADR-265 — fuzzy lookup por proximidade numérica (3º nível da cascata)."""

    def test_caso_real_founder_funde_via_fuzzy(self, sync_db):
        # IRPF cod=11 'exemplo 190' reusa row do comprovante cod=01
        # 'exemplo 186' — mesmo apto 34.
        ws = _seed_workspace(sync_db)
        existing = _seed_property(
            sync_db,
            ws,
            codigo_rfb="01",
            endereco_canonical="exemplo 186",
            descricao="Apartamento - Praça Exemplo, 186 - Ap 34",
        )
        record = _resolve(
            sync_db,
            ws.id,
            _new_lookup(codigo_rfb="11", endereco_canonical="exemplo 190"),
            descricao="APTO 34 - PRACA EXEMPLO 190",
        )
        assert record.property_id == existing.id
        assert record.codigo_rfb == "01"  # invariante E5

    def test_strict_e_loose_precedem_fuzzy(self, sync_db):
        # Quando existe row com canonical exato, fuzzy não é alcançado.
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="01", endereco_canonical="exemplo 186")
        exact = _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="exemplo 190")
        record = _resolve(
            sync_db,
            ws.id,
            _new_lookup(codigo_rfb="11", endereco_canonical="exemplo 190"),
            descricao="APTO 34 EXEMPLO 190",
        )
        assert record.property_id == exact.id

    def test_fuzzy_nao_atravessa_workspaces(self, sync_db):
        ws1 = _seed_workspace(sync_db)
        ws2 = _seed_workspace(sync_db)
        _seed_property(sync_db, ws1, codigo_rfb="01", endereco_canonical="exemplo 186")
        record = _resolve(
            sync_db,
            ws2.id,
            PropertyLookupKey(titular_key="x", codigo_rfb="11", endereco_canonical="exemplo 190"),
            descricao="APTO 34 EXEMPLO 190",
        )
        assert record.workspace_id == ws2.id  # insere nova, não vê row do ws1

    def test_fuzzy_rejeita_quando_delta_grande(self, sync_db):
        ws = _seed_workspace(sync_db)
        existing = _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="paulista 1500")
        record = _resolve(
            sync_db,
            ws.id,
            _new_lookup(codigo_rfb="11", endereco_canonical="paulista 1490"),
            descricao="EDIFICIO X - PAULISTA 1490",
        )
        assert record.property_id != existing.id  # Δ=10 > K=4

    def test_fuzzy_rejeita_complemento_divergente(self, sync_db):
        ws = _seed_workspace(sync_db)
        existing = _seed_property(
            sync_db,
            ws,
            codigo_rfb="11",
            endereco_canonical="paulista 100",
            descricao="APTO 51 - PAULISTA 100",
        )
        record = _resolve(
            sync_db,
            ws.id,
            _new_lookup(codigo_rfb="11", endereco_canonical="paulista 102"),
            descricao="APTO 34 - PAULISTA 102",
        )
        assert record.property_id != existing.id  # complementos 51 vs 34 divergem

    def test_fuzzy_ignora_canonicals_com_prefixo_forte(self, sync_db):
        ws = _seed_workspace(sync_db)
        _seed_property(sync_db, ws, codigo_rfb="11", endereco_canonical="mat:453527")
        record = _resolve(
            sync_db,
            ws.id,
            _new_lookup(codigo_rfb="11", endereco_canonical="mat:453528"),
        )
        assert record.endereco_canonical == "mat:453528"  # fuzzy não casa em mat:
