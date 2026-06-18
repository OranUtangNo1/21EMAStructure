# Modularization Refactor Index

## Purpose

This folder is the central specification and work-plan location for the current modularization refactor.

The refactor goal is to turn the current screening platform into reusable functional parts that can be executed independently, recombined for new applications, and evaluated against historical `as_of_date` inputs.

## Refactor Scope

- shared price-data contract
- file-based shared data access
- date-addressable indicator, scan, signal, market, radar, and stock-card execution
- database-dependent tracking and pool behavior paused unless explicitly re-enabled
- service-style module APIs that can be used by Streamlit, scripts, tests, and future apps

## Current Documents

1. `01_SHARED_PRICE_SCHEMA.md`
   - canonical price-history DataFrame contract
   - metadata separation rule
   - `as_of_date` slicing rule

2. `02_MODULARIZATION_WORK_PLAN.md`
   - active refactor principles
   - DB pause decision
   - target service boundaries
   - phased work order

## Operating Rule

During this modularization refactor, specifications and work plans for the refactor must be added or updated in this folder first.

If implementation changes alter any refactor contract in this folder, update the matching document in the same pass or explicitly report the mismatch.

## Relationship To Numbered Specs

The numbered specifications under `doc/SystemDocs/Specifications/` remain the active system reference for implemented behavior.

This folder owns the forward refactor plan and transition contracts. When a refactor contract becomes implemented behavior, update the relevant numbered spec as part of the implementation documentation sync.
