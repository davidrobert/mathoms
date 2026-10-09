"""Texto de exceção pronto para fronteira de persistência ou publicação (ADR-441 D2).

`str(StatementError)` ecoa os bound parameters; o driver Postgres põe a linha no DETAIL
(`Key (...)=(...)`, `Failing row contains (...)`); o bind processor do Python põe o valor
na própria mensagem. Toda fronteira que grava ou publica texto de exceção passa por
``describe_failure``: cadeia que tocou o banco sai por shape — tipo, sqlstate, rótulo e
identificadores de catálogo —, nunca por valor. Cadeia que não tocou sai intacta.

Sem import de sqlalchemy (`pipeline/` não importa ORM): a detecção é pelo módulo das
classes na MRO. Só alcança objeto vivo; texto já achatado em string fica fora.
"""

from __future__ import annotations

import re
import traceback
from dataclasses import dataclass

#: Marcador fixo de todo texto redigido. Contrato com o frontend:
#: `DATABASE_VALUES_OMITTED` em `frontend/src/lib/pipelineErrorMessages.ts`.
DATABASE_VALUES_OMITTED = "valores do banco omitidos"

# Raiz de módulo de toda classe que carrega texto do banco: o ORM (inclui o
# `PendingRollbackError`, que repete o erro original sem cadeia) e os drivers em uso.
_DATABASE_MODULE_ROOTS = frozenset({"sqlalchemy", "psycopg", "asyncpg", "sqlite3"})
# `datatype_name` no `diag` do psycopg, `data_type_name` no erro do asyncpg. Sem
# `schema_name`: é sempre `public` e casava `/schema/` no headline do frontend.
_CATALOG_FIELDS = (
    "constraint_name",
    "table_name",
    "column_name",
    "datatype_name",
    "data_type_name",
)
# Forma de identificador de catálogo. `RAISE ... USING CONSTRAINT = '...'` aceita texto
# livre, então o campo só sai se tiver essa forma.
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_$]{0,62}(?:\.[A-Za-z_][A-Za-z0-9_$]{0,62})?")
_SQLITE_CONSTRAINT = re.compile(
    r"(UNIQUE|NOT NULL|CHECK|FOREIGN KEY) constraint failed"
    r"(?:: ((?:[A-Za-z_]\w*\.)?[A-Za-z_]\w*(?:, (?:[A-Za-z_]\w*\.)?[A-Za-z_]\w*)*))?"
)
_SQLITE_ERRORNAME = re.compile(r"SQLITE_[A-Z_]+")
_SQLSTATE = re.compile(r"[0-9A-Z]{5}")
# Compatibilidade de APRESENTAÇÃO, subordinada à ADR-357: o backend nunca lê o rótulo
# (classe de falha é `reason_class`). Preserva o `/timeout/` de `pipelineErrorMessages.ts`.
_SQLSTATE_LABELS = {
    "57014": "statement timeout",
    "40P01": "deadlock",
    "40001": "serialization failure",
    "55P03": "lock not available",
}
_SQLSTATE_CLASS_LABELS = {"08": "connection exception", "53": "insufficient resources"}
_OMITTED_LINK = "mensagem omitida: a cadeia tocou o banco"
_CAUSE = "\nThe above exception was the direct cause of the following exception:\n\n"
_CONTEXT = "\nDuring handling of the above exception, another exception occurred:\n\n"


@dataclass(frozen=True)
class FailureText:
    """Mensagem + traceback de uma exceção, sem valor do banco quando a cadeia o tocou."""

    message: str
    traceback: str
    touched_database: bool
    sqlstate: str | None = None
    constraint: str | None = None

    def span_attributes(self) -> dict[str, str]:
        """Sobrescreve o que `Span.record_exception` derivaria de `str(exc)`."""
        attrs = {"exception.message": self.message, "exception.stacktrace": self.traceback}
        if self.sqlstate:
            attrs["db.response.status_code"] = self.sqlstate
        return attrs

    def log_fields(self) -> dict[str, str]:
        """Campos value-free para o evento estruturado — o evento é a métrica (ADR-404 D5)."""
        fields = {"db_sqlstate": self.sqlstate, "db_constraint": self.constraint}
        return {k: v for k, v in fields.items() if v}


class RedactedDatabaseError(Exception):
    """Substitui na borda a exceção cuja cadeia tocou o banco — carrega só o shape."""


def describe_failure(exc: BaseException) -> FailureText:
    """Texto de ``exc`` para gravar ou publicar. Nunca levanta."""
    try:
        return _describe(exc)
    except Exception:  # noqa: BLE001 — o sanitizador nunca derruba quem reporta a falha
        name = type(exc).__name__
        return FailureText(message=name, traceback=name, touched_database=True)


def as_redacted_exception(exc: BaseException) -> RedactedDatabaseError | None:
    """Exceção redigida com os frames de ``exc``; None se a cadeia não tocou o banco."""
    failure = describe_failure(exc)
    if not failure.touched_database:
        return None
    return RedactedDatabaseError(failure.message).with_traceback(exc.__traceback__)


def _describe(exc: BaseException) -> FailureText:
    database_links = [e for e in _every_link(exc) if _is_database_exception(e)]
    if not database_links:
        text = "".join(traceback.format_exception(exc))
        return FailureText(message=str(exc), traceback=text, touched_database=False)
    origin = _driver_origin(database_links)
    sqlstate = _sqlstate(origin)
    identifiers = _identifiers(origin)
    return FailureText(
        message=_shape_message(exc, origin, sqlstate, identifiers),
        traceback=_frames_only(exc, set()),
        touched_database=True,
        sqlstate=sqlstate,
        constraint=dict(identifiers).get("constraint"),
    )


def _every_link(exc: BaseException) -> list[BaseException]:
    """Cada elo, inclusive o contexto suprimido: `raise X(f"{e}") from None` é lavagem."""
    seen: dict[int, BaseException] = {}
    pending = [exc]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen[id(current)] = current
        pending.extend(l for l in (current.__cause__, current.__context__) if l is not None)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
    return list(seen.values())


def _is_database_exception(exc: BaseException) -> bool:
    return is_database_exception_class(type(exc))


def is_database_exception_class(cls: type) -> bool:
    """A classe (ou um ancestral) vem do ORM ou de um driver de banco."""
    return any((c.__module__ or "").split(".", 1)[0] in _DATABASE_MODULE_ROOTS for c in cls.__mro__)


def _driver_origin(database_links: list[BaseException]) -> BaseException:
    """O erro do driver (``.orig`` do wrapper do ORM), que carrega sqlstate e catálogo."""
    candidates = [getattr(link, "orig", None) or link for link in database_links]
    with_code = [c for c in candidates if _sqlstate(c) or _sqlite_errorname(c)]
    return (with_code or candidates)[-1]


def _sqlstate(origin: BaseException) -> str | None:
    code = getattr(origin, "sqlstate", None)
    return code if isinstance(code, str) and _SQLSTATE.fullmatch(code) else None


def _sqlite_errorname(origin: BaseException) -> str | None:
    name = getattr(origin, "sqlite_errorname", None)
    return name if isinstance(name, str) and _SQLITE_ERRORNAME.fullmatch(name) else None


def _identifiers(origin: BaseException) -> list[tuple[str, str]]:
    """(campo, nome) de catálogo: `diag` do psycopg, atributos do asyncpg, ou SQLite."""
    source = getattr(origin, "diag", None) or origin
    found = [(f.removesuffix("_name"), getattr(source, f, None)) for f in _CATALOG_FIELDS]
    named = [(k, v) for k, v in found if isinstance(v, str) and _IDENTIFIER.fullmatch(v)]
    return named or _sqlite_identifiers(origin)


def _sqlite_identifiers(origin: BaseException) -> list[tuple[str, str]]:
    first = origin.args[0] if origin.args else None
    match = _SQLITE_CONSTRAINT.fullmatch(first) if isinstance(first, str) else None
    if match is None or match.group(2) is None:
        return []
    return [(match.group(1).lower(), name) for name in match.group(2).split(", ")]


def _shape_message(exc, origin, sqlstate, identifiers) -> str:
    head = type(exc).__name__
    if type(origin).__name__ != head:
        head = f"{head}: {type(origin).__name__}"
    details = [d for d in (_label(sqlstate), _code(origin, sqlstate)) if d]
    details += [f"{kind} {name}" for kind, name in identifiers]
    bracket = f" [{'; '.join(details)}]" if details else ""
    return f"{head}{bracket} — {DATABASE_VALUES_OMITTED}"


def _label(sqlstate: str | None) -> str | None:
    if sqlstate is None:
        return None
    return _SQLSTATE_LABELS.get(sqlstate) or _SQLSTATE_CLASS_LABELS.get(sqlstate[:2])


def _code(origin: BaseException, sqlstate: str | None) -> str | None:
    return f"sqlstate {sqlstate}" if sqlstate else _sqlite_errorname(origin)


def _frames_only(exc: BaseException, seen: set[int]) -> str:
    """Traceback na semântica do Python — frames de cada elo, tipo no cabeçalho, sem mensagem."""
    if id(exc) in seen:
        return ""
    seen.add(id(exc))
    own = _frames_block(exc) + _group_members(exc, seen)
    if exc.__cause__ is not None:
        return _frames_only(exc.__cause__, seen) + _CAUSE + own
    if exc.__context__ is not None and not exc.__suppress_context__:
        return _frames_only(exc.__context__, seen) + _CONTEXT + own
    return own


def _frames_block(exc: BaseException) -> str:
    frames = "".join(traceback.StackSummary.extract(traceback.walk_tb(exc.__traceback__)).format())
    header = "Traceback (most recent call last):\n" if frames else ""
    return f"{header}{frames}{_qualified_name(type(exc))}: <{_OMITTED_LINK}>\n"


def _group_members(exc: BaseException, seen: set[int]) -> str:
    if not isinstance(exc, BaseExceptionGroup):
        return ""
    return "".join(f"\n[membro do grupo]\n{_frames_only(m, seen)}" for m in exc.exceptions)


def _qualified_name(cls: type) -> str:
    module = cls.__module__
    return cls.__qualname__ if module in (None, "builtins") else f"{module}.{cls.__qualname__}"
