# Modularization Refactor Index

## Purpose

This folder contains reference specifications and an optional work plan for the modularization refactor.

The refactor goal is to turn the current screening platform into reusable functional parts that can be executed independently, recombined for new applications, and evaluated against historical `as_of_date` inputs.

## Refactor Scope

- shared price-data contract
- file-based shared data access
- date-addressable indicator, scan, signal, market, radar, and stock-card execution
- database-dependent tracking and pool behavior paused unless explicitly re-enabled
- service-style module APIs that can be used by CLI commands, scripts, tests, and future automation without a GUI dependency

## Current Documents

1. `01_SHARED_PRICE_SCHEMA.md`
   - canonical price-history DataFrame contract
   - metadata separation rule
   - `as_of_date` slicing rule

2. `02_MODULARIZATION_WORK_PLAN.md`
   - reference refactor principles
   - DB pause decision
   - target service boundaries
   - reference work order

3. `03_SERVICE_ARTIFACT_AND_REUSE_CONTRACT.md`
   - final no-GUI output layout
   - retained `service_outputs` and `documents` paths
   - downstream output reuse instead of global saved-run restoration
   - legacy and GUI-only directory removal contract

## Operating Rule

Implementation may proceed directly when the requested scope is clear.
Creating or updating a specification or work plan is not a prerequisite for implementation.
Update this folder only when documentation work is explicitly requested or a material design decision needs a durable record.
Implementation changes do not require same-pass documentation synchronization.

## Relationship To Numbered Specs

The numbered specifications under `doc/SystemDocs/Specifications/` remain the active system reference for implemented behavior.

This folder preserves forward-refactor and transition-contract references.
Update numbered specifications only as a dedicated documentation task, not as an automatic implementation step.
