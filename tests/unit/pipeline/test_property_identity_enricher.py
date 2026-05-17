"""Unit tests for property_identity_enricher (ADR-215 P2)."""

from __future__ import annotations

import pytest

from pipeline.adapters.in_memory_property_identity_resolver import (
    InMemoryPropertyIdentityResolver,
)
from pipeline.domain.services.property_identity_enricher import (
    enrich_imoveis_with_property_ids,
)

WS_ID = "test-workspace-001"


def _build_consolidated(imoveis: list[dict]) -> dict:
    return {"imoveis_consolidados": imoveis, "veiculos_consolidados": []}


class TestEnricher:
    def test_skip_when_no_imoveis(self):
        resolver = InMemoryPropertyIdentityResolver()
        out = enrich_imoveis_with_property_ids({}, resolver, WS_ID)
        assert out == {}
        assert resolver.all() == []

    def test_adds_property_id_to_each_imovel(self):
        resolver = InMemoryPropertyIdentityResolver()
        imoveis = [
            {
                "descricao": "CASA - RUA TASSO DA SILVEIRA, 61 - SP",
                "proprietario": "david_robert",
                "codigo_rfb": "12",
                "ano_referencia": 2024,
            }
        ]
        out = enrich_imoveis_with_property_ids(_build_consolidated(imoveis), resolver, WS_ID)
        entry = out["imoveis_consolidados"][0]
        assert entry["property_id"] is not None
        assert entry["endereco_canonical"] == "tasso silveira 61"
        assert entry["low_confidence"] is False

    def test_same_imovel_across_years_returns_same_property_id(self):
        """Goldens de paridade — descrição varia entre anos, property_id estável."""
        resolver = InMemoryPropertyIdentityResolver()
        imovel_2023 = {
            "descricao": "CASA - RUA TASSO DA SILVEIRA, 61",
            "proprietario": "david_robert",
            "codigo_rfb": "12",
            "ano_referencia": 2023,
        }
        imovel_2024 = {
            "descricao": "Casa - Rua Tasso da Silveira, 61 - São Paulo",
            "proprietario": "david_robert",
            "codigo_rfb": "12",
            "ano_referencia": 2024,
        }
        out1 = enrich_imoveis_with_property_ids(_build_consolidated([imovel_2023]), resolver, WS_ID)
        out2 = enrich_imoveis_with_property_ids(_build_consolidated([imovel_2024]), resolver, WS_ID)
        id_2023 = out1["imoveis_consolidados"][0]["property_id"]
        id_2024 = out2["imoveis_consolidados"][0]["property_id"]
        assert id_2023 == id_2024
        # Cria 1 row em property_identity, não 2.
        assert len(resolver.all()) == 1

    def test_different_titular_same_address_dedupes_to_single_property(self):
        """ADR-215 fix-B2: casal em comunhão declara mesmo imóvel → 1 row."""
        resolver = InMemoryPropertyIdentityResolver()
        imovel_titular = {
            "descricao": "Rua Tasso, 61",
            "proprietario": "david_robert",
            "codigo_rfb": "12",
            "ano_referencia": 2024,
        }
        imovel_conjuge = {
            "descricao": "Rua Tasso, 61",
            "proprietario": "mariana",
            "codigo_rfb": "12",
            "ano_referencia": 2024,
        }
        out = enrich_imoveis_with_property_ids(
            _build_consolidated([imovel_titular, imovel_conjuge]), resolver, WS_ID
        )
        ids = [e["property_id"] for e in out["imoveis_consolidados"]]
        assert ids[0] == ids[1]
        assert len(resolver.all()) == 1

    def test_different_titular_no_endereco_keeps_distinct(self):
        """low_confidence (sem endereço): mantém rows distintas — merge fuzzy é arriscado."""
        resolver = InMemoryPropertyIdentityResolver()
        imovel_t = {
            "descricao": "APTO SEM ENDERECO",
            "proprietario": "david_robert",
            "codigo_rfb": "11",
            "ano_referencia": 2024,
        }
        imovel_c = {
            "descricao": "APTO SEM ENDERECO OUTRO",
            "proprietario": "mariana",
            "codigo_rfb": "11",
            "ano_referencia": 2024,
        }
        out = enrich_imoveis_with_property_ids(
            _build_consolidated([imovel_t, imovel_c]), resolver, WS_ID
        )
        ids = [e["property_id"] for e in out["imoveis_consolidados"]]
        assert ids[0] != ids[1]

    def test_descricao_without_address_yields_low_confidence(self):
        resolver = InMemoryPropertyIdentityResolver()
        imovel = {
            "descricao": "APARTAMENTO COND BARAO DE CAPANEMA APTO 34",
            "proprietario": "david_robert",
            "codigo_rfb": "11",
            "ano_referencia": 2024,
        }
        out = enrich_imoveis_with_property_ids(_build_consolidated([imovel]), resolver, WS_ID)
        entry = out["imoveis_consolidados"][0]
        assert entry["low_confidence"] is True
        assert entry["endereco_canonical"] is None
        assert entry["property_id"] is not None

    def test_missing_codigo_rfb_marks_low_confidence_without_property(self):
        resolver = InMemoryPropertyIdentityResolver()
        imovel = {
            "descricao": "Imóvel legado sem código",
            "proprietario": "david_robert",
            "ano_referencia": 2024,
        }
        out = enrich_imoveis_with_property_ids(_build_consolidated([imovel]), resolver, WS_ID)
        entry = out["imoveis_consolidados"][0]
        assert entry["property_id"] is None
        assert entry["low_confidence"] is True

    def test_idempotent_repeated_calls_dont_duplicate(self):
        resolver = InMemoryPropertyIdentityResolver()
        imovel = {
            "descricao": "Av Paulista, 1500",
            "proprietario": "david_robert",
            "codigo_rfb": "11",
            "ano_referencia": 2024,
        }
        for _ in range(5):
            enrich_imoveis_with_property_ids(_build_consolidated([dict(imovel)]), resolver, WS_ID)
        assert len(resolver.all()) == 1


class TestDBResolver:
    """Smoke test do DBPropertyIdentityResolver com SQLAlchemy em-memória."""

    @pytest.mark.asyncio
    async def test_match_or_create_persists_and_dedupes(self):
        import uuid

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        # Models registram-se ao importar.
        import backend.app.models  # noqa: F401
        from backend.app.core.database import Base
        from backend.app.models import User, Workspace
        from backend.app.services.db_property_identity_resolver import (
            DBPropertyIdentityResolver,
        )
        from pipeline.domain.types.property_identity import PropertyLookupKey

        engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine, future=True)
        s = SessionLocal()

        u = User(
            id=str(uuid.uuid4()),
            email=f"db-resolver-{uuid.uuid4().hex[:8]}@test.com",
            hashed_password="x",
            full_name="Test",
        )
        s.add(u)
        s.flush()
        w = Workspace(id=str(uuid.uuid4()), name="WS", owner_id=u.id)
        s.add(w)
        s.flush()

        resolver = DBPropertyIdentityResolver(session=s)
        lookup = PropertyLookupKey(
            titular_key="david_robert",
            codigo_rfb="12",
            endereco_canonical="tasso silveira 61",
        )
        r1 = resolver.match_or_create(w.id, lookup, 2024, "Casa Tasso 61")
        r2 = resolver.match_or_create(w.id, lookup, 2024, "Casa Tasso 61")
        assert r1.property_id == r2.property_id
        s.close()
