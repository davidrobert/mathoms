"""Serviços de domínio tributário PJ (Sprint A16 L2 · [[ADR-236]]).

Este package centraliza serviços de domínio puros para a Cascata Fiscal PJ:

- :mod:`irpf_renda_tributavel` (P2) — agrega base PGBL canônica do artifact
  ``extract_irpf_full`` ([[ADR-157]]).
- ``cascata_calculator`` (P3) — calculator canônico por regime (Simples
  Anexo III/V, Lucro Presumido, MEI) com fator-R derivado, base PGBL
  correta e decision triggers parametrizados.

Boundary ([[ADR-097]]): zero imports de ``fastapi`` / ``celery`` /
``sqlalchemy``. Adapter backend injeta dados.
"""
