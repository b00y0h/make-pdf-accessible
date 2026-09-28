# ADR-0003: Pluggable remediation engine; PDFix with veraPDF first, Adobe Auto-Tag second, no in-house tagger

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** PDF tagging and validation
- **Related:** `docs/REMEDIATION-PIPELINE-PRD.md`, `docs/research/ithaka-pipeline-analysis.md`, ADR-0002, ADR-0004

## Context

Nothing in the repository writes a PDF structure tree; `services/functions/tag_pdf/main.py` returns a fixed `tags_applied = 25`. Writing a correct PDF/UA tagger (structure tree, role map, artifacts, reading order, table semantics, OCR text placement) is years of work that Adobe, PDFix, and others have already done. ITHAKA started with Adobe's Auto-Tag API and swapped to PDFix plus veraPDF without rebuilding the pipeline; they report a 98% check pass rate at $0.026 per page. Adobe's API is about $0.50 per page, which alone consumes most of our automated price. Engine quality differs by document class, and licensing terms differ for SaaS use.

Constraints: cost of goods under $0.055 per page; the deadline is seven months out; validation must be independent of the engine.

## Decision

We will define an `EngineAdapter` contract (tag a page, merge pages, declare capabilities) and ship PDFix SDK as the first production engine running in a Fargate container, with veraPDF as the validator of record. We will implement Adobe Auto-Tag as the second adapter for evaluation, fallback and customers who require it. We will not build a tagging engine. Engine name and version are part of the artifact cache key and the evidence pack.

## Alternatives Considered

- **Build our own tagger on pikepdf/PyMuPDF** — The market research and the code audit show this is the hard, valuable part that would take the team past the deadline; quality would trail engines with a decade of work.
- **Adobe Auto-Tag only** — Best-known brand, but per-page cost is too high for our price list and the API is whole-document (no page-level fan-out).
- **Open-source only (pdf-lib, OCRmyPDF, Docling to HTML)** — Fine for HTML-first output, insufficient for PDF/UA structure trees on complex layouts.
- **Rely on the engine's own validator** — Not independent; buyers need a report from a tool they can cite (veraPDF is the PDF Association's reference implementation).

## Consequences

**Positive**

- Engine independence proven by two adapters; licensing risk hedged.
- Independent validation output ships in every evidence pack.

**Negative / Trade-offs**

- Engine license cost and terms for SaaS are an open question; margins depend on them.
- Two engines mean two sets of quirks in merge and metadata handling.
- veraPDF checks PDF/UA syntax, not meaning; semantic QA and human review remain necessary.

**Neutral / Follow-ups**

- Negotiate PDFix SaaS terms before slice P1; keep Adobe credentials in Secrets Manager.
- Publish measured accuracy per engine and document class from the eval set.
