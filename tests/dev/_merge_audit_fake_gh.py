"""Fake do `gh` para o detector da proteção de main (ADR-415 · ADR-448).
Responde aos endpoints reais por path e grava a chamada INTEIRA — gravar só
`args[1]` registrava "create" para `["issue","create",...]` e o guard de
dry-run passava sem nunca casar nada (5 mutações sobreviviam)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from dev.merge_incident_issues import marker
from dev.ruleset_bypass_alarm import ADR_448_APPLIED, GATE_CHECK, RULESET_ID

MERGE_TS = "2026-08-25T11:57:42Z"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
DEPOIS_DA_448 = "2026-10-09T16:30:00Z"


def iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def at(**delta: float) -> str:
    """Instante relativo à aplicação da ADR-448, no formato da API."""
    return iso(ADR_448_APPLIED + timedelta(**delta))


def check(conclusion: str = "success", completed_at: str | None = "2026-08-25T11:50:00Z") -> dict:
    return {"name": GATE_CHECK, "conclusion": conclusion, "completed_at": completed_at}


def ruleset_state(
    bypass: int = 0, enforcement: str = "active", gate: bool = True, strict: bool = True
) -> dict[str, Any]:
    contexts = [{"context": GATE_CHECK}] if gate else []
    params = {"strict_required_status_checks_policy": strict, "required_status_checks": contexts}
    return {
        "enforcement": enforcement,
        "bypass_actors": [{"actor_id": 5}] * bypass,
        "rules": [{"type": "required_status_checks", "parameters": params}],
    }


def ruleset(updated_at: str = "2026-10-09T15:53:52.112Z", admin: bool = True, **kw: Any) -> dict:
    """GET do ruleset. Sem admin a API OMITE `bypass_actors` (medido sem auth
    em 2026-10-09) — o fake reproduz a omissão, não um `[]`."""
    data = {**ruleset_state(**kw), "id": RULESET_ID, "updated_at": updated_at}
    if not admin:
        data.pop("bypass_actors")
    return data


def incident(key: str, number: int = 99, state: str = "open") -> dict:
    kind, value = key.split("=", 1)
    return {"number": number, "state": state, "body": f"{marker(kind, value)}\ncorpo"}


class FakeGh:
    """Runner com as respostas do repo de produção, tabeladas por teste."""

    def __init__(self, **tables: Any) -> None:
        self.pulls: dict[str, list[dict]] = tables.get("pulls", {})
        self.checks: dict[str, list[dict]] = tables.get("checks", {})
        self.suites: list[dict] = tables.get("suites", [])
        self.suites_error: str | None = tables.get("suites_error")
        self.issues: list[dict] = tables.get("issues", [])
        self.ruleset: dict | None = tables.get("ruleset", ruleset())
        self.ruleset_error: str | None = tables.get("ruleset_error")
        self.history: list[tuple[int, str, dict]] = tables.get("history", [])
        self.merged_by: dict[int, str] = tables.get("merged_by", {})
        self.calls: list[str] = []

    def __call__(self, args: list[str]) -> str:
        self.calls.append(" ".join(args))
        if args[0] == "issue":
            return "https://github.com/o/r/issues/1234\n" if args[1] == "create" else ""
        return self._api(args[1])

    @property
    def writes(self) -> list[str]:
        prefixes = ("issue create", "issue edit", "issue comment", "issue reopen", "issue close")
        return [c for c in self.calls if c.startswith(prefixes)]

    def _api(self, path: str) -> str:
        for needle, answer in self._routes():
            if needle in path:
                return answer(path)
        return self._commit_endpoints(path)

    def _routes(self) -> list[tuple[str, Any]]:
        return [
            ("rulesets/rule-suites", self._suites_page),
            (f"rulesets/{RULESET_ID}/history/", self._version),
            (f"rulesets/{RULESET_ID}/history?", self._history_page),
            (f"rulesets/{RULESET_ID}", self._ruleset),
            ("/issues?", self._issues_page),
            ("/pulls/", self._pull),
        ]

    @staticmethod
    def _page(path: str) -> int:
        return int(path.split("page=")[-1]) if "page=" in path else 1

    def _paged(self, items: list, path: str) -> str:
        start = (self._page(path) - 1) * 100
        return json.dumps(items[start : start + 100])

    def _suites_page(self, path: str) -> str:
        if self.suites_error:
            raise RuntimeError(self.suites_error)
        return self._paged(self.suites, path)

    def _ruleset(self, path: str) -> str:
        if self.ruleset_error:
            raise RuntimeError(self.ruleset_error)
        return json.dumps(self.ruleset)

    def _history_page(self, path: str) -> str:
        versions = [
            {"version_id": v, "updated_at": ts, "actor": {"id": 1}} for v, ts, _ in self.history
        ]
        return self._paged(versions, path)

    def _version(self, path: str) -> str:
        wanted = int(path.rsplit("/", 1)[1])
        return json.dumps(next({"state": s} for v, _, s in self.history if v == wanted))

    def _issues_page(self, path: str) -> str:
        return self._paged(self.issues, path)

    def _pull(self, path: str) -> str:
        login = self.merged_by.get(int(path.rsplit("/", 1)[1]))
        return json.dumps({"merged_by": {"login": login} if login else None})

    def _commit_endpoints(self, path: str) -> str:
        for sha, payload in self.pulls.items():
            if f"commits/{sha}/pulls" in path:
                return json.dumps(payload)
        for sha, payload in self.checks.items():
            if f"commits/{sha}/check-runs" in path:
                return json.dumps({"check_runs": payload})
        return json.dumps([])
