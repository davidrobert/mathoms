#!/usr/bin/env python3
"""Gate executável da rotação Fernet (A34.l3 · ADR-171 · runbook fernet_rotation.md): ``preflight`` recusa rodar com a janela fechada (onde um dry-run daria falso-limpo), ``rotate`` faz dry-run → confirmação → passe real, ``verify`` roda o 2º dry-run e avalia as duas condições do gate G0; nunca imprime material de chave — só contadores, o ``kid`` de 8 chars e nomes de coluna."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# `python3 dev/fernet_rotation_gate.py` põe `dev/` no sys.path, não a raiz —
# sem isto, `import backend.app...` quebra com ModuleNotFoundError (mesmo
# padrão de dev/drill_seed.py e dev/restore_drill.py).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MIN_KEYS_FOR_WINDOW = 2
KID_AUDIT_SQL = """
SELECT content_json->>'kid' AS kid, count(*)
FROM pipeline_artifacts
WHERE content_json->>'_encrypted' = 'true'
GROUP BY 1;
""".strip()


class PreflightError(RuntimeError):
    """Janela de rotação fechada ou vault não configurado."""


# ─── introspecção (lazy: `--help` não pode exigir MATHOMS_FERNET_KEY) ───


def key_window() -> tuple[int, str]:
    """(nº de chaves ativas, kid da primária). O kid é sha256[:8] — fingerprint, não chave."""
    from backend.app.services.security.crypto import _key_id
    from backend.app.services.security.vault import resolve_fernet_keys

    return len(resolve_fernet_keys()), _key_id()


def run_task(dry_run: bool) -> dict:
    """Chama a task em processo (não via broker): report determinístico, sem depender do worker."""
    from backend.app.tasks.rotate_fernet_secrets import rotate_fernet_secrets

    return rotate_fernet_secrets(dry_run=dry_run)


def db_target() -> tuple[str, Path | None]:
    """(alvo sem credencial, caminho do arquivo se sqlite) — absoluto de propósito."""
    # Com um `mathoms.db` na raiz e vários worktrees por perto, "qual arquivo?"
    # é a pergunta que importa; caminho relativo não responde.
    from urllib.parse import urlparse

    from backend.app.core.config import settings

    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        # `sqlite:////abs/path` → urlparse devolve `//abs/path`; tirar UMA barra
        # (lstrip("/") comeria as duas e transformaria o absoluto em relativo).
        raw = parsed.path or ""
        path = Path(raw[1:] if raw.startswith("//") else raw)
        return f"sqlite {path}", path
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.hostname or '?'}{port}/{(parsed.path or '/').lstrip('/') or '?'}", None


def sqlite_problem(path: Path | None) -> str | None:
    """Sqlite ausente ou vazio = quase sempre worktree/diretório errado."""
    # Sintoma traiçoeiro: `rotate` diria "nada a rotacionar" com total
    # confiança sobre um banco que não é o seu.
    if path is None:
        return None
    if not path.exists():
        return (
            f"o arquivo `{path}` NÃO existe. Você provavelmente está rodando de um "
            "worktree ou de outro diretório — rode da raiz do repo que hospeda o "
            "banco do dogfood."
        )
    if path.stat().st_size == 0:
        return f"o arquivo `{path}` está vazio (0 bytes) — não é o banco do dogfood."
    return None


# ─── avaliação pura (testável offline com report sintético) ───


def summarize(report: dict) -> dict[str, int]:
    totals = {"rotated": 0, "skipped": 0, "failed": 0}
    for counts in (report.get("targets") or {}).values():
        for key in totals:
            totals[key] += counts.get(key, 0)
    return totals


def _window_problem(keys_configured: int) -> str | None:
    if keys_configured >= MIN_KEYS_FOR_WINDOW:
        return None
    return (
        f"janela de rotação FECHADA ({keys_configured} chave ativa): com só a chave "
        "atual, valor cifrado com a chave antiga não decifra e é contado como "
        "`skipped` — o report sai limpo sem provar nada (falso-limpo)"
    )


def _failed_problem(totals: dict[str, int]) -> str | None:
    if totals["failed"] == 0:
        return None
    return (
        f"failed={totals['failed']}: há valor que não decifra com NENHUMA chave ativa. "
        "Investigue pelo log (`fernet rotation: artifact undecryptable`, com "
        "artifact_id/kid_stored) — não feche o gate"
    )


def _residue_problem(totals: dict[str, int]) -> str | None:
    if totals["rotated"] == 0:
        return None
    return (
        f"rotated={totals['rotated']} no 2º passe: sobrou coluna na chave antiga. "
        "A task é resumível — rode o passe real de novo até este número zerar"
    )


def evaluate(report: dict, keys_configured: int, expect_idle: bool) -> list[str]:
    """Problemas que impedem o gate de fechar; lista vazia = passou."""
    totals = summarize(report)
    found = [_window_problem(keys_configured), _failed_problem(totals)]
    if expect_idle:
        found.append(_residue_problem(totals))
    return [p for p in found if p]


def format_report(report: dict) -> str:
    lines = [f"{'target':<45}{'rotated':>9}{'skipped':>9}{'failed':>8}"]
    lines.append("-" * 71)
    for target, counts in sorted((report.get("targets") or {}).items()):
        lines.append(
            f"{target[:44]:<45}{counts.get('rotated', 0):>9}"
            f"{counts.get('skipped', 0):>9}{counts.get('failed', 0):>8}"
        )
    totals = summarize(report)
    lines.append("-" * 71)
    lines.append(f"{'TOTAL':<45}{totals['rotated']:>9}{totals['skipped']:>9}{totals['failed']:>8}")
    return "\n".join(lines)


# ─── comandos ───


def _require_real_target() -> str:
    """Mostra QUAL banco será reescrito, antes de qualquer coisa."""
    # Sem gate "local × produção" de propósito: a única instância com dado real
    # é o dogfood local (prod owner-gated, ADR-228 G2/G3), então bloquear alvo
    # local barraria o uso legítimo — engano da 1ª versão deste guard (#1129).
    # O engano que importa é apontar para o banco ERRADO; é isso que se checa.
    target, sqlite_path = db_target()
    print(f"banco alvo:    {target}")
    if sqlite_path and sqlite_path.exists():
        print(f"tamanho:       {sqlite_path.stat().st_size / 1e6:.0f} MB")
    problem = sqlite_problem(sqlite_path)
    if problem:
        raise PreflightError(problem)
    return target


def _require_window() -> tuple[int, str]:
    _require_real_target()
    keys, kid = key_window()
    print(f"chaves ativas: {keys} · kid da primária: {kid}")
    if keys < MIN_KEYS_FOR_WINDOW:
        raise PreflightError(
            "janela FECHADA — abra antes de qualquer dry-run. No `.env`:\n"
            "  MATHOMS_FERNET_KEYS=<chave_nova>,<chave_antiga>\n"
            "(a nova PRIMEIRO), e reinicie o que estiver rodando — API e worker\n"
            "precisam ler o mesmo conjunto de chaves."
        )
    return keys, kid


def cmd_preflight(args) -> int:
    _require_window()
    print("OK — janela aberta. O dry-run agora é confiável.")
    return 0


def cmd_rotate(args) -> int:
    keys, _ = _require_window()
    print("\n── dry-run (nada é escrito) ──")
    report = run_task(dry_run=True)
    print(format_report(report))
    problems = evaluate(report, keys, expect_idle=False)
    if problems:
        return _fail(problems)
    if summarize(report)["rotated"] == 0:
        print("\nNada a rotacionar — tudo já está na chave primária.")
        return 0
    if not args.yes and not _confirm(summarize(report)["rotated"]):
        print("abortado pelo operador.")
        return 1
    print("\n── passe real ──")
    print(format_report(run_task(dry_run=False)))
    print("\nAgora rode `verify` para fechar o gate.")
    return 0


def cmd_verify(args) -> int:
    keys, kid = _require_window()
    report = json.loads(args.report.read_text()) if args.report else run_task(dry_run=True)
    print("\n── 2º dry-run (prova de que nada ficou para trás) ──")
    print(format_report(report))
    problems = evaluate(report, keys, expect_idle=True)
    if problems:
        return _fail(problems)
    print(f"\nGATE OK — failed=0 e rotated=0 com a janela aberta (kid {kid}).")
    print("\nConfirmação para o gate G0 (cole só isto — sem chave, sem valor):")
    totals = summarize(report)
    print(
        f"  rotação Fernet: failed={totals['failed']} rotated={totals['rotated']} "
        f"skipped={totals['skipped']} · 2º passe · kid={kid}"
    )
    print(f"\nIntegridade dos artifacts — rode e confira que só aparece o kid {kid}:\n")
    print(KID_AUDIT_SQL)
    return 0


def _confirm(pending: int) -> bool:
    prompt = f"\nRotacionar {pending} valor(es) agora? Digite 'rotacionar' para confirmar: "
    return input(prompt).strip() == "rotacionar"


def _fail(problems: list[str]) -> int:
    print("\nGATE BLOQUEADO:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight", help="a janela de rotação está aberta?")
    rotate = sub.add_parser("rotate", help="dry-run → confirmação → passe real")
    rotate.add_argument("--yes", action="store_true", help="pula a confirmação interativa")
    verify = sub.add_parser("verify", help="2º dry-run + as duas condições do gate")
    verify.add_argument("--report", type=Path, help="avalia um report JSON já salvo")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    handler = {"preflight": cmd_preflight, "rotate": cmd_rotate, "verify": cmd_verify}[args.cmd]
    try:
        return handler(args)
    except PreflightError as exc:
        return _fail([str(exc)])


if __name__ == "__main__":
    raise SystemExit(main())
