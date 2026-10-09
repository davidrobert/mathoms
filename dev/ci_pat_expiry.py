#!/usr/bin/env python3
"""Aviso antecipado de expiração do AUTOUPDATE_PAT (ADR-322 §Emenda 2026-10-08):
lê o header de expiração e mantém UMA issue rotulada a partir de T-14. Falha da
medição vira warning, nunca run vermelho. Uso: python3 dev/ci_pat_expiry.py --label X [--dry-run]"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.ci_advance_automerge_train import GhCallFailed, _gh  # noqa: E402

WARN_DAYS = 14
# Resposta 200 prova que o token vale agora; vencimento a <1h dela é leitura incoerente
# (bug do GitHub de ago–set/2025 devolvia agora+1min para PAT fine-grained).
MIN_PLAUSIBLE_LEFT = timedelta(hours=1)
EXPIRY_HEADER = "github-authentication-token-expiration"
ISSUE_TITLE = "AUTOUPDATE_PAT perto de expirar — rotacionar"
RUNBOOK = "docs/reference/runbooks/automerge_train.md"
_FORMATS = ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S %z")


def parse_expiration(value: str) -> datetime:
    """Normaliza para UTC: fine-grained vem no fuso do dono (`... -0300`), classic em `UTC`."""
    for fmt in _FORMATS:
        try:
            parsed = datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
        aware = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return aware.astimezone(timezone.utc)
    raise ValueError(f"expected '{_FORMATS[0]}' em {EXPIRY_HEADER}, got {value!r}")


def expiration_header(raw: str) -> str | None:
    """Valor do header na saída de `gh api -i` (cabeçalhos até a 1ª linha vazia)."""
    head = raw.replace("\r\n", "\n").split("\n\n", 1)[0]
    for line in head.splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip().lower() == EXPIRY_HEADER:
            return value.strip()
    return None


def expiry_warning(expires_at: datetime | None, now: datetime) -> str | None:
    """Frase do aviso, ou None com folga. Sem header = sem expiração (viola D2)."""
    if expires_at is None:
        return "o PAT **não tem expiração** — viola a D2 da ADR-322 (≤90 dias)"
    days_left = (expires_at - now).days
    if days_left > WARN_DAYS:
        return None
    when = expires_at.strftime("%Y-%m-%d %H:%M UTC")
    if expires_at <= now:
        return f"o PAT **expirou** em {when}"
    return f"o PAT expira em **{days_left} dia(s)** ({when})"


def rotation_url(today: datetime) -> str:
    """Formulário de PAT fine-grained pré-preenchido com as permissões da D2."""
    query = {
        "name": f"mathoms-autoupdate-train-{today:%Y-%m}",
        "description": f"AUTOUPDATE_PAT do trem de auto-merge (ADR-322). Rotacao: {RUNBOOK}",
        "target_name": "davidrobert",
        "expires_in": "90",
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "actions": "read",
    }
    return "https://github.com/settings/personal-access-tokens/new?" + urlencode(query)


def issue_body(warning: str, now: datetime) -> str:
    return (
        f"Aviso: {warning}. Sem ele o trem de auto-merge e o watchdog param "
        f"(HTTP 401) e, 3 dias depois, o `S3` do `ops-train` reprova o `Lint` de todo PR.\n\n"
        f"1. Gere o token: {rotation_url(now)}\n"
        f"   - **Repository access:** Only select repositories → `davidrobert/mathoms` "
        f"(o único campo que a URL não preenche).\n"
        f"2. `gh secret set AUTOUPDATE_PAT --repo davidrobert/mathoms` (cola o token).\n"
        f"3. `gh workflow run automerge-watchdog.yml` — esta issue fecha sozinha "
        f"quando a folga passa de {WARN_DAYS} dias.\n\n"
        f"Runbook: `{RUNBOOK}` §2.\n\n"
        f"_Mantida por `dev/ci_pat_expiry.py`; limite `S3` de 11 dias = bloqueio em T-3._"
    )


def _open_issue(label: str) -> dict | None:
    out = _gh("issue", "list", "--state", "open", "--label", label, "--json", "number,body")
    issues = json.loads(out)
    return issues[0] if issues else None


def sync_issue(warning: str | None, now: datetime, label: str, dry_run: bool) -> None:
    """Uma issue só, editada no lugar: o `S3` conta idade pelo createdAt."""
    issue = _open_issue(label)
    if warning is None:
        if issue is not None and not dry_run:
            _gh("issue", "close", str(issue["number"]), "--comment", "PAT rotacionado.")
        return
    body = issue_body(warning, now)
    if dry_run or (issue is not None and issue.get("body") == body):
        return
    if issue is None:
        _gh("issue", "create", "--title", ISSUE_TITLE, "--label", label, "--body", body)
    else:
        _gh("issue", "edit", str(issue["number"]), "--body", body)


def measure_expiration(repo: str, now: datetime) -> datetime | None:
    raw = expiration_header(_gh("api", "-i", f"repos/{repo}"))
    expires_at = parse_expiration(raw) if raw is not None else None
    if expires_at is not None and expires_at - now < MIN_PLAUSIBLE_LEFT:
        raise ValueError(f"{EXPIRY_HEADER}={raw!r} a <1h com HTTP 200 — leitura incoerente")
    return expires_at


def _slack_line(expires_at: datetime) -> str:
    """A data no log é o que a validação pós-rotação confere (~90 dias à frente)."""
    return f"folga > {WARN_DAYS} dias (vence {expires_at:%Y-%m-%d %H:%M} UTC)"


def check_pat_expiry(label: str, dry_run: bool) -> None:
    """Só mede com o PAT explícito: o fallback GITHUB_TOKEN vive ~1h e mentiria."""
    if os.environ.get("AUTOMERGE_KICK") != "1":
        print("pat-expiry: sem AUTOUPDATE_PAT no job — nada a medir")
        return
    now = datetime.now(timezone.utc)
    try:
        expires_at = measure_expiration(os.environ["GH_REPO"], now)
        warning = expiry_warning(expires_at, now)
        print(f"pat-expiry: {warning or _slack_line(expires_at)}")
        sync_issue(warning, now, label, dry_run)
    except (GhCallFailed, ValueError, KeyError) as exc:
        print(f"::warning title=pat-expiry sem medição::{exc} — o run segue (ADR-322)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="label da issue (declarado no manifesto)")
    parser.add_argument("--dry-run", action="store_true", help="só reporta, não age")
    args = parser.parse_args()
    check_pat_expiry(args.label, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
