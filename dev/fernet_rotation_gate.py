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
LOCAL_HOSTS = frozenset({"", "localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal"})
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


def db_target() -> str:
    """`host:porta/database` do alvo — sem usuário nem senha. Só para o operador
    enxergar em QUAL banco está mexendo antes de escrever."""
    from urllib.parse import urlparse

    from backend.app.core.config import settings

    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        return f"sqlite:{(parsed.path or '').rsplit('/', 1)[-1] or 'memória'}"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.hostname or '?'}{port}/{(parsed.path or '/').lstrip('/') or '?'}"


def looks_local(target: str) -> bool:
    """Alvo que quase certamente NÃO é produção (sqlite ou host de loopback)."""
    if target.startswith("sqlite:"):
        return True
    return target.split(":")[0].split("/")[0] in LOCAL_HOSTS


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


def _require_prod_target(allow_local: bool) -> str:
    """Mostra o banco alvo ANTES de qualquer coisa — a l3 é sobre o dado de
    produção, e rodar no laptop responde a pergunta errada em silêncio."""
    target = db_target()
    print(f"banco alvo:    {target}")
    if looks_local(target) and not allow_local:
        raise PreflightError(
            f"o alvo `{target}` parece LOCAL, não produção.\n"
            "A l3 pergunta se a chave vazada ainda decifra dado vivo — no seu\n"
            "laptop isso não significa nada. Rode dentro do container do worker\n"
            "(console do Coolify no serviço do worker, ou `docker exec`).\n"
            "Se você realmente quer rodar contra este banco, passe --allow-local."
        )
    return target


def _require_window(allow_local: bool = False) -> tuple[int, str]:
    _require_prod_target(allow_local)
    keys, kid = key_window()
    print(f"chaves ativas: {keys} · kid da primária: {kid}")
    if keys < MIN_KEYS_FOR_WINDOW:
        raise PreflightError(
            "janela FECHADA — abra antes de qualquer dry-run:\n"
            "  MATHOMS_FERNET_KEYS=<chave_nova>,<chave_antiga>\n"
            "em backend E worker, com redeploy síncrono (runbook §2)."
        )
    return keys, kid


def cmd_preflight(args) -> int:
    _require_window(args.allow_local)
    print("OK — janela aberta. O dry-run agora é confiável.")
    print(
        "\nAtenção: esta é a env que ESTE processo vê. Rode o script no mesmo\n"
        "container do worker, ou confirme que backend e worker compartilham a\n"
        "mesma MATHOMS_FERNET_KEYS (deploy assimétrico = decrypt fail intermitente)."
    )
    return 0


def cmd_rotate(args) -> int:
    keys, _ = _require_window(args.allow_local)
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
    keys, kid = _require_window(args.allow_local)
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
    # `--allow-local` vive num parser PAI herdado por cada subcomando: definido
    # só no topo, `preflight --allow-local` falharia com "unrecognized
    # arguments" e exigiria `--allow-local preflight`, que ninguém digita.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--allow-local",
        action="store_true",
        help="permite alvo local (drill/staging); por padrão só roda contra banco remoto",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight", parents=[common], help="a janela de rotação está aberta?")
    rotate = sub.add_parser("rotate", parents=[common], help="dry-run → confirmação → passe real")
    rotate.add_argument("--yes", action="store_true", help="pula a confirmação interativa")
    verify = sub.add_parser(
        "verify", parents=[common], help="2º dry-run + as duas condições do gate"
    )
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
