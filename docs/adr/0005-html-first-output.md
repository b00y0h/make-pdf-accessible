# ADR-0005: HTML first for text-heavy web documents; PDF/UA when the document must remain a PDF

- **Status:** Proposed
- **Date:** 2026-09-28
- **Deciders:** Founder (product and engineering)
- **Scope:** Output formats, triage rules, publish-back connectors
- **Related:** `docs/INVENTORY-TRIAGE-PRD.md`, `docs/INTEGRATIONS-PRD.md`, `docs/REMEDIATION-PIPELINE-PRD.md`

## Context

Universities are adopting HTML-first policies (Michigan State: PDFs are not to be created for class material; UC Office of the President: publish as much as possible as web pages). HTML is easier to make and keep accessible, responsive, searchable and translatable; PDF/UA is still required for forms, print-fidelity documents and archives. The repository already has a real semantic HTML builder (`services/worker/src/semantic_html_builder.py`) and a WordPress plugin, and nothing that publishes HTML back into a CMS with redirects. Tagging engines are weakest exactly where HTML is strongest: long text documents with simple structure.

## Decision

We will make `convert_html` the default triage decision for text-heavy web documents (policies, syllabi, guides, notices, catalog pages under about 30 pages, no forms) and `remediate_pdf` the default for forms, print-fidelity and long or complex documents. HTML output is validated with axe-core and an HTML validator and published back into the CMS as a page with a 301 redirect from the PDF URL and the original kept as a download. Customers can override the decision per document or per site.

## Alternatives Considered

- **PDF/UA for everything** — Simpler pipeline, but worse for users, more expensive per page, and against customer policy.
- **HTML for everything** — Forms, legal documents and print materials need fixed layout; some regulators expect the document form.
- **Leave the choice entirely to customers** — Most do not have the capacity to decide per document; a sensible default with overrides is what they ask for.

## Consequences

**Positive**

- Better outcomes for readers; lower cost per page on the HTML path; a clear differentiator from PDF-only vendors.

**Negative / Trade-offs**

- Publish-back and redirects make us responsible for changes on the customer's site; a bad conversion is visible to everyone.
- Layout-heavy documents (brochures, posters) convert poorly and must be caught by triage.

**Neutral / Follow-ups**

- The HTML template needs its own ACR; MathML support arrives with the STEM slice.
