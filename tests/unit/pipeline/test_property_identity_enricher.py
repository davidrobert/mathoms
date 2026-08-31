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
                "descricao": "CASA - RUA EXEMPLO, 100 - SP",
                "proprietario": "david_robert",
                "codigo_rfb": "12",
                "ano_referencia": 2024,
            }
        ]
        out = enrich_imoveis_with_property_ids(_build_consolidated(imoveis), resolver, WS_ID)
        entry = out["imoveis_consolidados"][0]
        assert entry["property_id"] is not None
        assert entry["endereco_canonical"] == "exemplo 100"
        assert entry["low_confidence"] is False

    def test_same_imovel_across_years_returns_same_property_id(self):
        """Goldens de paridade — descrição varia entre anos, property_id estável."""
        resolver = InMemoryPropertyIdentityResolver()
        imovel_2023 = {
            "descricao": "CASA - RUA EXEMPLO, 100",
            "proprietario": "david_robert",
            "codigo_rfb": "12",
            "ano_referencia": 2023,
        }
        imovel_2024 = {
            "descricao": "Casa - Rua Exemplo, 100 - São Paulo",
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
            "descricao": "Rua Exemplo, 100",
            "proprietario": "david_robert",
            "codigo_rfb": "12",
            "ano_referencia": 2024,
        }
        imovel_conjuge = {
            "descricao": "Rua Exemplo, 100",
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

    def test_different_titular_no_endereco_does_not_mint(self):
        """[[ADR-392]]: sem canonical não minta — os dois ficam needs_review."""
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
        entries = out["imoveis_consolidados"]
        assert [e["property_id"] for e in entries] == [None, None]
        assert all(e["needs_review"] is True for e in entries)
        assert resolver.all() == []

    def test_descricao_without_address_yields_needs_review_not_mint(self):
        resolver = InMemoryPropertyIdentityResolver()
        imovel = {
            "descricao": "APARTAMENTO COND EXEMPLO C APTO 34",
            "proprietario": "david_robert",
            "codigo_rfb": "11",
            "ano_referencia": 2024,
        }
        out = enrich_imoveis_with_property_ids(_build_consolidated([imovel]), resolver, WS_ID)
        entry = out["imoveis_consolidados"][0]
        assert entry["low_confidence"] is True
        assert entry["endereco_canonical"] is None
        assert entry["property_id"] is None
        assert entry["needs_review"] is True
        assert resolver.all() == []

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


def make_db_resolver_fixtures():
    """Engine in-memory + sessionmaker + 1 User + 1 Workspace (committed)."""
    import uuid

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import backend.app.models  # noqa: F401
    from backend.app.core.database import Base
    from backend.app.models import User, Workspace

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine, future=True)
    s, uid, wid = SL(), str(uuid.uuid4()), str(uuid.uuid4())
    s.add(User(id=uid, email=f"db-{uuid.uuid4().hex[:8]}@t.co", hashed_password="x", full_name="T"))
    s.add(w := Workspace(id=wid, name="WS", owner_id=uid))
    s.commit()
    return SL, s, w


class TestDBResolver:
    """Smoke test do DBPropertyIdentityResolver com SQLAlchemy em-memória."""

    @pytest.mark.asyncio
    async def test_match_or_create_persists_and_dedupes(self):
        from backend.app.services.db_property_identity_resolver import (
            DBPropertyIdentityResolver,
        )
        from pipeline.domain.types.property_identity import PropertyLookupKey

        _SL, s, w = make_db_resolver_fixtures()
        resolver = DBPropertyIdentityResolver(session=s)
        lookup = PropertyLookupKey(
            titular_key="david_robert", codigo_rfb="12", endereco_canonical="exemplo 100"
        )
        r1 = resolver.match_or_create(w.id, lookup, 2024, "Casa Exemplo 100")
        r2 = resolver.match_or_create(w.id, lookup, 2024, "Casa Exemplo 100")
        assert r1.property_id == r2.property_id
        s.close()

    @pytest.mark.asyncio
    async def test_match_or_create_commits_so_parallel_session_sees_row(self):
        """Regressão prod 2026-05-18 run dadb0cd6: sem commit no resolver, INSERT pipeline_artifacts paralelo falhava com `database is locked` (30s busy_timeout)."""
        from sqlalchemy import select

        from backend.app.models import PropertyIdentity
        from backend.app.services.db_property_identity_resolver import (
            DBPropertyIdentityResolver,
        )
        from pipeline.domain.types.property_identity import PropertyLookupKey

        SessionLocal, long_lived, w = make_db_resolver_fixtures()
        resolver = DBPropertyIdentityResolver(session=long_lived)
        lookup = PropertyLookupKey("david_robert", "12", "exemplo 100")
        record = resolver.match_or_create(w.id, lookup, 2024, "Casa Exemplo 100")
        parallel = SessionLocal()
        stmt = select(PropertyIdentity).where(PropertyIdentity.workspace_id == w.id)
        rows = parallel.execute(stmt).scalars().all()
        assert len(rows) == 1 and rows[0].id == record.property_id
        parallel.close()
        long_lived.close()


class TestLowConfidenceSempreTemRazao:
    # `low_confidence` sem razão é sinal que nenhum consumidor enxerga: o operador
    # não o vê na fila, e o LLM do parecer lê o item como se fosse limpo. Eram 8 de
    # 26 itens do corpus violando; a paridade dos call-sites mudos entrou antes
    # desta lane, e este teste é o que impede a regressão.
    #
    # LIMITE: cobre os ramos que o enricher produz hoje. Um quarto sítio que marque
    # `low_confidence` fora dele passa despercebido — o produtor único de razão
    # (`_append_uncanonical_reason`) é o que torna isso improvável, não este teste.
    """Invariante do corpus ([[A40.l111]] critério 7 · [[ADR-272]])."""

    @staticmethod
    def _todos_os_ramos() -> list[dict]:
        """Um item por ramo do enricher que marca `low_confidence`."""
        return [
            # eixo por hint — sem fato, com a declaração provando saber emitir `secao`
            {
                "descricao": "APTO - RUA A, 1",
                "proprietario": "david",
                "codigo_rfb": "11",
                "ano_referencia": 2025,
                "eixo_autoridade": "hint",
                "secao_disponivel": True,
            },
            # sem titular_key
            {
                "descricao": "CASA - RUA B, 2",
                "proprietario": "",
                "codigo_rfb": "12",
                "ano_referencia": 2025,
                "eixo_autoridade": "secao",
            },
            # sem codigo_rfb
            {
                "descricao": "SALA - RUA C, 3",
                "proprietario": "david",
                "codigo_rfb": "",
                "ano_referencia": 2025,
                "eixo_autoridade": "secao",
            },
            # descrição que não canonicaliza → sem endereco_canonical
            {
                "descricao": "",
                "proprietario": "david",
                "codigo_rfb": "13",
                "ano_referencia": 2025,
                "eixo_autoridade": "secao",
            },
        ]

    def test_todo_item_low_confidence_carrega_pelo_menos_uma_razao(self):
        resolver = InMemoryPropertyIdentityResolver()
        out = enrich_imoveis_with_property_ids(
            _build_consolidated(self._todos_os_ramos()), resolver, WS_ID
        )
        mudos = [
            e["descricao"]
            for e in out["imoveis_consolidados"]
            if e.get("low_confidence") and not e.get("review_reasons")
        ]

        assert mudos == [], f"low_confidence sem razão em: {mudos}"

    def test_a_fixture_exercita_de_fato_o_ramo_low_confidence(self):
        """Sem isto, um enricher que nunca marcasse `low_confidence` passaria acima."""
        resolver = InMemoryPropertyIdentityResolver()
        out = enrich_imoveis_with_property_ids(
            _build_consolidated(self._todos_os_ramos()), resolver, WS_ID
        )
        marcados = [e for e in out["imoveis_consolidados"] if e.get("low_confidence")]

        assert len(marcados) == len(self._todos_os_ramos())
