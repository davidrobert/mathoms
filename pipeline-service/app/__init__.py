"""Pipeline-as-Service — HTTP boundary for pipeline execution (A6f.1 · ADR-112).

Standalone FastAPI service that wraps `pipeline.orchestrator` behind HTTP.
Runs stateless; no DB. Artifacts cross the HTTP boundary as payloads.
"""
