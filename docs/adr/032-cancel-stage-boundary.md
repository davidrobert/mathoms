---
id: ADR-032
type: adr
title: "Cancel stage-boundary"
status: Decidido
phase: "F5"
date: "2026-04-15"
relates_to: []
supersedes: ["[[ADR-030]]"]
superseded_by: []
aliases: ["ADR 032"]
tags:
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 7
---

# ADR-032 — Cancel stage-boundary

**Status:** Decidido (F5)

**Decisão:** Cancel verificado entre stages (não mid-stage). Stages completos são preservados. Seguro, sem cleanup parcial.
