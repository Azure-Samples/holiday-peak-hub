# Admin Truth Analytics and Observability

## Purpose

Use this walkthrough to inspect truth-layer KPIs, throughput, tracing, model usage, and retry/error signals.

## Current State Summary

| Item | Current behavior |
| --- | --- |
| Role required | `admin` |
| Main navigation access | `Admin` -> `Truth Analytics` or `Agent Activity` |
| Primary routes | `/admin/truth-analytics`, `/admin/agent-activity` |
| Working status | Implemented and working |

## Workflow A: Truth analytics dashboard

1. Open `/admin`.
2. In `E-Commerce Services`, click `Truth Analytics`.
3. Confirm the dashboard shows KPI cards such as:
   - `Overall Completeness`
   - `Enrichment Jobs`
   - `HITL Queue Pending`
   - `Exports`
4. Review the queue breakdown cards.
5. Review the pipeline flow diagram.
6. Scroll down to inspect:
   - completeness by category
   - pipeline throughput chart

## Workflow B: Agent activity dashboard

1. Return to `/admin`.
2. Click `Agent Activity`.
3. Use the `Time range` selector.
4. Review the top summary cards:
   - `Tracing`
   - `Active traces`
   - `Needs retry`
   - `Recovered`
5. Review the `Agent health cards` section.
6. Review the `Trace feed` table.
7. Review the `Model usage` table.
8. Review the `Error / retry log` section.
9. If tracing is unavailable, confirm the warning card explains that tracing must be enabled.
10. If you want evaluation coverage, click `View evaluations`.

## Success checklist

| Check | Expected result |
| --- | --- |
| Truth analytics | KPI cards and charts load |
| Agent activity | Time-range filter refreshes the observability view |
| Trace feed | Trace IDs link to deeper trace pages when available |
| Error visibility | Failed or retried traces show up in the retry log |
