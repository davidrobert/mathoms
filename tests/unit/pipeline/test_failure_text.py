"""ADR-441 D2 — `describe_failure`: cadeia que tocou o banco sai por shape, nunca por valor.

As exceções são as reais (SQLAlchemy, psycopg, sqlite3), não fakes: a detecção é pelo
módulo das classes na MRO, e um fake provaria só o fake.
"""

from __future__ import annotations

import inspect
import sqlite3
import sys
import traceback
from types import SimpleNamespace

import psycopg.errors
import pytest
import sqlalchemy.exc
import sqlalchemy.orm.exc
from psycopg.errors import QueryCanceled, StringDataRightTruncation, UniqueViolation
from sqlalchemy import Column, Integer, MetaData, Numeric, String, Table, create_engine, insert
from sqlalchemy.exc import DataError, IntegrityError, PendingRollbackError, StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from pipeline.observability.failure_text import (
    DATABASE_VALUES_OMITTED,
    RedactedDatabaseError,
    as_redacted_exception,
    describe_failure,
    is_database_exception_class,
)

_ENDERECO = "Rua Exemplo, 100"  # sintético, PII-zero
_TITULAR = "maria exemplo"
_VALOR = "R$ 350.000,00"


def _tudo(failure) -> str:
    return failure.message + failure.traceback


def _levantado(exc: BaseException) -> BaseException:
    """A exceção com traceback de verdade — frames são parte do que se mede."""
    try:
        raise exc
    except BaseException as caught:  # noqa: BLE001
        return caught


def _unique_violation() -> IntegrityError:
    orig = UniqueViolation(
        'duplicate key value violates unique constraint "uq_property_identity_key"\n'
        f"DETAIL:  Key (titular_key, endereco_canonical)=({_TITULAR}, {_ENDERECO}) "
        "already exists."
    )
    exc = IntegrityError("INSERT INTO property_identities ...", {"t": _TITULAR}, orig)
    exc.__cause__ = orig
    return exc


def _integrity_error_sqlite() -> StatementError:
    eng = create_engine("sqlite://")
    tabela = Table("identidade", MetaData(), Column("chave", String, primary_key=True))
    tabela.metadata.create_all(eng)
    try:
        for _ in range(2):
            with eng.begin() as conn:
                conn.execute(insert(tabela), {"chave": _ENDERECO})
    except StatementError as exc:
        return exc
    finally:
        eng.dispose()
    raise AssertionError("o INSERT duplicado deveria ter levantado")


class _Base(DeclarativeBase):
    pass


class _Imovel(_Base):
    __tablename__ = "imovel_teste"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    descricao: Mapped[str] = mapped_column(String, unique=True, nullable=True)
    valor = mapped_column(Numeric(14, 2), nullable=True)


def _flush_falho_e_sessao_reusada(**campos) -> tuple[BaseException, BaseException]:
    """Flush que falha, engolido, e a sessão reusada — o padrão da sessão compartilhada.

    Engine COM ``hide_parameters``: o que sobra no texto é o que a D1 não alcança."""
    eng = create_engine("sqlite://", hide_parameters=True)
    _Base.metadata.create_all(eng)
    with Session(eng) as session:
        session.add(_Imovel(id=1, descricao=_ENDERECO))
        session.flush()
        session.add(_Imovel(id=2, **campos))
        with pytest.raises(StatementError) as primeiro:
            session.flush()
        with pytest.raises(PendingRollbackError) as reuso:
            session.add(_Imovel(id=3))
            session.flush()
    eng.dispose()
    return primeiro.value, reuso.value


def test_cadeia_sem_banco_sai_intacta():
    exc = _levantado(ValueError(f"descrição inválida: {_ENDERECO}"))
    failure = describe_failure(exc)
    assert not failure.touched_database
    assert failure.message == str(exc)
    assert failure.traceback == "".join(traceback.format_exception(exc))


def test_bound_parameter_do_orm_nao_sai():
    failure = describe_failure(_integrity_error_sqlite())
    assert failure.touched_database
    assert _ENDERECO not in _tudo(failure)
    assert "[SQL:" not in failure.message
    assert failure.message.endswith(DATABASE_VALUES_OMITTED)
    # Shape do SQLite: só os identificadores do formato fechado de constraint.
    assert "SQLITE_CONSTRAINT_PRIMARYKEY" in failure.message
    assert "unique identidade.chave" in failure.message


def test_bind_processor_ecoa_mesmo_com_hide_parameters_e_nao_sai():
    """O valor vem do ValueError do Python, não do bound parameter: a D1 não alcança."""
    primeiro, reuso = _flush_falho_e_sessao_reusada(valor=_VALOR)
    assert _VALOR in str(primeiro) and _VALOR in str(reuso)  # pré-condição medida
    for exc in (primeiro, reuso):
        failure = describe_failure(exc)
        assert failure.touched_database and _VALOR not in _tudo(failure)


def test_pending_rollback_error_embute_o_original_sem_cadeia():
    _, reuso = _flush_falho_e_sessao_reusada(descricao=_ENDERECO)
    assert reuso.__cause__ is None and reuso.__context__ is None
    failure = describe_failure(reuso)
    assert failure.message.startswith("PendingRollbackError")
    assert "unique imovel_teste.descricao" not in failure.message  # sem `orig`, só o tipo


def test_detail_do_postgres_nao_sai_e_o_sqlstate_sai():
    failure = describe_failure(_levantado(_unique_violation()))
    assert _TITULAR not in _tudo(failure) and _ENDERECO not in _tudo(failure)
    assert failure.message.startswith("IntegrityError: UniqueViolation [sqlstate 23505")
    assert failure.sqlstate == "23505"


class _ComDiag(UniqueViolation):
    """`diag` é property da classe no psycopg: só uma subclasse o substitui."""

    diag = SimpleNamespace(
        constraint_name="uq_property_identity_key",
        table_name=_ENDERECO,  # forma de valor, não de identificador: não sai
        schema_name="public",
    )


def test_catalogo_sai_so_com_forma_de_identificador_e_sem_schema():
    failure = describe_failure(_ComDiag("x"))
    assert "constraint uq_property_identity_key" in failure.message
    assert failure.constraint == "uq_property_identity_key"
    assert _ENDERECO not in failure.message
    # `public` casava `/schema/` no headline do frontend (ADR-068).
    assert "schema" not in failure.message and "public" not in failure.message


@pytest.mark.parametrize("campo", ["constraint_name", "table_name", "column_name", "datatype_name"])
def test_tripwire_os_campos_lidos_existem_no_diagnostic_do_psycopg(campo):
    assert hasattr(psycopg.errors.Diagnostic, campo)


def test_rotulo_por_sqlstate_preserva_o_timeout():
    failure = describe_failure(DataError("SELECT 1", None, QueryCanceled("canceling ...")))
    assert "statement timeout" in failure.message
    assert "sqlstate 57014" in failure.message


def _reexportada_da_stdlib(cls: type) -> bool:
    raiz = cls.__module__.split(".")[0]
    return raiz in sys.stdlib_module_names and raiz != "sqlite3"


def _classes_de_excecao(*modulos) -> set[type]:
    """Exportadas pelos módulos; reexport da stdlib (`asyncio.CancelledError`) fica fora."""
    return {
        obj
        for mod in modulos
        for _, obj in inspect.getmembers(mod, inspect.isclass)
        if issubclass(obj, BaseException) and not _reexportada_da_stdlib(obj)
    }


def test_toda_classe_exportada_pelo_orm_e_pelos_drivers_e_detectada():
    """Igualdade de conjunto, não amostra (ADR-435): exportadas ⊆ detectadas."""
    exportadas = _classes_de_excecao(sqlalchemy.exc, sqlalchemy.orm.exc, psycopg.errors, sqlite3)
    assert len(exportadas) > 200  # psycopg.errors sozinho tem centenas — zero é leitura vazia
    assert {c for c in exportadas if not is_database_exception_class(c)} == set()


def test_erro_de_dominio_from_db_herda_a_redacao_e_preserva_o_tipo():
    try:
        try:
            raise _unique_violation()
        except IntegrityError as db_exc:
            raise RuntimeError(f"falha ao gravar: {db_exc}") from db_exc
    except RuntimeError as exc:
        failure = describe_failure(exc)
    assert failure.touched_database
    assert _ENDERECO not in _tudo(failure)
    assert failure.message.startswith("RuntimeError: UniqueViolation")


def test_from_none_nao_e_opt_out():
    """`raise X(f"{e}") from None` é indistinguível de mensagem segura: redige igual."""
    try:
        try:
            raise _unique_violation()
        except IntegrityError as db_exc:
            raise RuntimeError(f"imóvel já identificado: {db_exc}") from None
    except RuntimeError as exc:
        failure = describe_failure(exc)
    assert failure.touched_database
    assert _ENDERECO not in _tudo(failure)
    assert failure.message.startswith("RuntimeError: UniqueViolation")


def test_membro_de_exception_group_conta():
    grupo = _levantado(ExceptionGroup("lote", [_levantado(_unique_violation())]))
    failure = describe_failure(grupo)
    assert failure.touched_database and _ENDERECO not in _tudo(failure)


def test_traceback_mantem_os_frames_e_perde_as_mensagens():
    def _resolve_identidade():
        raise _unique_violation()

    try:
        _resolve_identidade()
    except IntegrityError as exc:
        failure = describe_failure(exc)
    assert "_resolve_identidade" in failure.traceback
    assert "sqlalchemy.exc.IntegrityError" in failure.traceback
    assert "duplicate key" not in failure.traceback


def test_nunca_levanta():
    class _DiagQuebrado(StringDataRightTruncation):
        @property
        def diag(self):
            raise RuntimeError("diag indisponível")

    failure = describe_failure(_DiagQuebrado("x"))
    assert failure.touched_database
    assert failure.message == "_DiagQuebrado"


def test_cadeia_ciclica_termina():
    a, b = ValueError("a"), ValueError("b")
    a.__context__, b.__context__ = b, a
    assert describe_failure(a).message == "a"


def test_excecao_redigida_mantem_frames_e_nao_carrega_a_original():
    exc = _levantado(_unique_violation())
    redigida = as_redacted_exception(exc)
    assert isinstance(redigida, RedactedDatabaseError)
    assert redigida.__traceback__ is exc.__traceback__
    texto = "".join(traceback.format_exception(redigida))
    assert _ENDERECO not in texto and _TITULAR not in texto
    assert as_redacted_exception(_levantado(ValueError("x"))) is None
