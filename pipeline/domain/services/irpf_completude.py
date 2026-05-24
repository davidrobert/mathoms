"""Completude tri-state de ano-base IRPF — ADR-266."""

# Decide se um ano-base é completo/provisorio/incompleto:
# 1. Hoje < 1jun(N+1) → provisorio (se ≥1 não-shell) ou incompleto (tudo shell)
# 2. Todas decls são shell pós-dedup → incompleto
# 3. CPFs de ano N-1 não estão em N (lacuna familiar) → incompleto
# 4. Caso contrário → completo
# `mudanca_estrutural` é reservado para confirmação humana — analyzer nunca retorna.

from __future__ import annotations

import datetime as _dt
from enum import Enum

from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput


class CompletudeAno(str, Enum):
    """Estado do ano-base IRPF para fins de apresentação no relatório."""

    completo = "completo"
    provisorio = "provisorio"
    incompleto = "incompleto"
    mudanca_estrutural = "mudanca_estrutural"  # reservado — só via confirmação humana


def compute_completude(
    decls_by_year: dict[int, list[IRPFFullOutput]],
    ano: int,
    today: _dt.date,
) -> tuple[CompletudeAno, str | None]:
    """Computa estado + motivo para um ano-base, dadas todas declarações por ano."""
    decls = decls_by_year.get(ano, [])
    non_shell = [d for d in decls if not _is_shell_decl(d)]

    if _is_within_rfb_window(ano, today):
        return _provisorio_or_incompleto(non_shell, ano)
    if not non_shell:
        return CompletudeAno.incompleto, "Nenhuma declaração com dados de renda."

    missing_cpf = _find_missing_cpf_from_prior_year(decls_by_year, ano, non_shell)
    if missing_cpf is not None:
        return CompletudeAno.incompleto, _missing_cpf_motivo(missing_cpf, ano)

    return CompletudeAno.completo, None


def _is_within_rfb_window(ano: int, today: _dt.date) -> bool:
    """Prazo final de entrega IRPF: 31/maio de N+1. Após 1jun, ano é fiscalmente fechado."""
    deadline = _dt.date(ano + 1, 6, 1)
    return today < deadline


def _provisorio_or_incompleto(
    non_shell: list[IRPFFullOutput], ano: int
) -> tuple[CompletudeAno, str | None]:
    if non_shell:
        return CompletudeAno.provisorio, f"Ano-base {ano} dentro da janela RFB."
    return CompletudeAno.incompleto, "Nenhuma declaração entregue até agora."


def _is_shell_decl(decl: IRPFFullOutput) -> bool:
    """Declaração-fantasma: todos os blocos de renda+pagamento+bens vazios."""
    return (
        not decl.rendimentos_pj
        and not decl.rendimentos_pf
        and not decl.rendimentos_isentos
        and not decl.rendimentos_tributacao_exclusiva
        and not decl.pagamentos_efetuados
        and not decl.bens_direitos
    )


def _find_missing_cpf_from_prior_year(
    decls_by_year: dict[int, list[IRPFFullOutput]],
    ano: int,
    non_shell_curr: list[IRPFFullOutput],
) -> str | None:
    """CPF que declarou em algum N' < N mas não em N — sinal de lacuna familiar."""
    curr_cpfs = {d.contribuinte.cpf_masked for d in non_shell_curr}
    for prev_ano in sorted((y for y in decls_by_year if y < ano), reverse=True):
        prev_non_shell = [d for d in decls_by_year[prev_ano] if not _is_shell_decl(d)]
        prev_cpfs = {d.contribuinte.cpf_masked for d in prev_non_shell}
        missing = prev_cpfs - curr_cpfs
        if missing:
            return sorted(missing)[0]  # determinístico
    return None


def _missing_cpf_motivo(cpf: str, ano: int) -> str:
    """Mensagem padrão para o motivo de incompleto por CPF ausente."""
    return f"Falta declaração de CPF {cpf} (presente em ano-base anterior)."


def pick_default_year(
    completude_por_ano: dict[int, CompletudeAno],
) -> int | None:
    """Último completo; fallback provisório; fallback incompleto; None se vazio."""
    if not completude_por_ano:
        return None
    for state in (CompletudeAno.completo, CompletudeAno.provisorio, CompletudeAno.incompleto):
        anos = [y for y, s in completude_por_ano.items() if s == state]
        if anos:
            return max(anos)
    return None
