# Analysis: ITHAKA's On-Demand PDF Remediation Pipeline, and How Make PDF Accessible Beats It

**Date:** 2026-09-28
**Source under analysis:** AWS Public Sector Blog, _How ITHAKA built an on-demand PDF remediation pipeline on AWS_ (August 2026, by Dane Hillard, Associate Director of Product Engineering, ITHAKA). Read alongside the PDF Association write-up (_156 Million Pages: How ITHAKA Built PDF/UA Compliance on AWS with PDFix_), the PDFix press release, ITHAKA's AWS Champion announcement, JSTOR's _Building accessibility into every article, on demand_ post, and the open-source ASU/AWS `PDF_Accessibility` repository that ITHAKA adapted.
**Research note:** aws.amazon.com and the secondary sources were blocked by the research environment's egress policy, so the article was reconstructed from indexed excerpts and cross-checked across five sources. Every number below appeared in at least two of them. Verify against the original before quoting it externally.

---

## 1. What ITHAKA built

### The problem they were solving

| Fact                    | Value                                                                                                                                   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Corpus                  | About 20 million PDFs, 156 million pages, content dating back to 1550                                                                   |
| Manual remediation cost | $1 to $4 per page, which is $156M to $624M for the whole corpus                                                                         |
| Deadline pressure       | ADA Title II (originally April 2026, now April 26, 2027 for large public entities) and library customers asking for accessible versions |
| Starting point          | The MIT-licensed ASU/AWS open-source pipeline (Adobe Auto-Tag API + Bedrock alt text + Step Functions)                                  |
| Timeline                | 2-day build-and-demo workshop with AWS solutions architects in February 2026; production about two months later                         |

### The architecture

1. **Trigger.** A user on JSTOR requests an accessible version of an article. Amazon EventBridge starts the workflow. Nothing is remediated ahead of demand.
2. **Split.** A Lambda function splits the PDF into single pages so the expensive work runs in parallel.
3. **Orchestrate.** AWS Step Functions runs the per-page work and the fan-in. The compute mix is Lambda for light steps and Fargate for heavy, long-running steps.
4. **Tag.** PDFix applies structure tags (headings, paragraphs, lists, tables) to each page. ITHAKA replaced the Adobe Auto-Tag API with PDFix without rebuilding the pipeline, which the article calls out as the payoff of a modular design.
5. **Describe.** Amazon Bedrock generates alternative text for images and charts.
6. **Merge and validate.** Pages are reassembled and the document is checked against PDF/UA with veraPDF.
7. **Store and cache.** The remediated PDF is written to Amazon S3 and served to every later requester. The accessible collection grows with real demand.
8. **Observe.** EventBridge emits a status event at each stage (splitting, processing, merging, validation). An event-log aggregator stores the full job history next to the remediated PDF in S3.

JSTOR's user-facing behavior: a researcher clicks to request an accessible version and typically gets it within minutes, depending on length and complexity. Images can get an AI description with one click; the description is stored, used as alt text and shown to all users.

### Results they report

| Metric                                   | Reported value                           |
| ---------------------------------------- | ---------------------------------------- |
| Accessibility check pass rate            | 98%                                      |
| Cost reduction versus manual remediation | More than 97%                            |
| Processing cost                          | About $0.026 per page                    |
| Time to production                       | About two months from the first workshop |

### Operational lessons in the article

- **Service control policies fight deployment scripts.** ITHAKA's SCPs blocked S3 bucket-policy changes the open-source deploy scripts needed. They adjusted the SCPs to permit public-access-block settings without breaking infrastructure-as-code deployments. Lesson: design for locked-down enterprise accounts from day one.
- **Swap engines, keep the pipeline.** The tagging engine is a replaceable step. That is what let them move from Adobe to PDFix + veraPDF.
- **Cache is the product.** On-demand plus caching turned a $156M+ upfront problem into a pay-as-used one.
- **Validate the output, not the intent.** The 98% figure is a machine check (veraPDF against PDF/UA) on the produced file, not an internal score.

---

## 2. What is worth copying (best practices to adopt)

| Practice                                                 | Why it matters                                                                               | How it lands in Make PDF Accessible                                                                                                                                                                                    |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Remediate on demand, cache by content hash               | Nobody can afford to fix a whole backlog upfront; most files are never opened                | The **Accessible Link** feature: any PDF URL gets a stable accessible-version URL; the first request remediates, every later one is served from S3 or CloudFront. See `docs/REMEDIATION-PIPELINE-PRD.md` and ADR-0001. |
| Page-level parallelism with split, process, merge        | Latency drops from minutes-per-document to seconds-per-page; failures are isolated to a page | Step Functions Distributed Map over pages; Fargate for engine steps, Lambda for light steps. ADR-0002.                                                                                                                 |
| Pluggable engine behind a stable contract                | Engines change (Adobe, PDFix, future models). The pipeline should not                        | An `EngineAdapter` interface with PDFix as the first production engine and Adobe Auto-Tag as a second adapter. ADR-0003.                                                                                               |
| Validate the produced file with an independent validator | Self-scored quality is not evidence                                                          | veraPDF (PDF/UA-1 and PDF/UA-2 profiles) on the output, plus WCAG checks on HTML output. ADR-0004.                                                                                                                     |
| Event per stage, stored with the artifact                | Debuggability and a defensible audit trail                                                   | EventBridge events per stage, persisted as the job timeline inside the evidence pack.                                                                                                                                  |
| Design for locked-down accounts                          | Universities and systems have SCPs, private-only S3, and change control                      | Terraform with no public buckets, OAC-only CloudFront origins, per-environment accounts, and no deploy-time policy hacks. ADR-0010.                                                                                    |
| Cost per page as a first-class metric                    | The buyer's mental model is dollars per page                                                 | Metering per page per stage, surfaced in the dashboard and on the public price list.                                                                                                                                   |
| Keep the human in the loop where it matters              | AI alt text for charts is where checkers pass and users lose                                 | Confidence-routed human review workbench (only low-confidence elements go to people).                                                                                                                                  |

---

## 3. Where ITHAKA's pipeline stops (and where the market is unserved)

ITHAKA solved ITHAKA's problem: one publisher, one corpus, one platform that already knows every document and every request. A university, a college system, a school district or a city faces a different problem, and neither the ITHAKA pipeline nor the ASU/AWS open-source solution addresses it:

1. **They do not know what they have.** No inventory of the PDFs on the public website, in the CMS media library, in the LMS, in shared drives. ITHAKA has a catalog. A campus has a crawl problem.
2. **They should not fix everything.** The Title II rule's exceptions (archived content, unused pre-existing documents, third-party content) mean a large share of the backlog should be deleted, archived or left alone, with the decision recorded. ITHAKA remediates whatever is requested; a campus needs triage.
3. **PDF is often the wrong output.** Major universities now have HTML-first policies. A syllabus, a policy, a catalog page should become a web page, not a tagged PDF. ITHAKA's output is always a PDF because a scholarly article is a PDF.
4. **They need to publish the result back.** The fixed file must replace the old one in WordPress, Drupal or Canvas, with redirects, or nothing changes for users. ITHAKA controls its own delivery platform; a campus has dozens.
5. **They need evidence they can defend.** A 98% pass rate is a fleet statistic. A compliance office needs a per-document record: what was checked, by which tool and version, what a human signed off, when. Neither pipeline produces a portable evidence pack.
6. **Automated tagging is not the whole standard.** veraPDF checks PDF/UA syntax. It cannot tell whether reading order is right, whether a table's headers are correct, or whether chart alt text conveys meaning. Studies of auto-taggers put reading-order accuracy near 67% on scholarly PDFs. Passing the checker is not the same as being accessible, and DOJ said as much when it delayed the rule.
7. **The open-source solution is explicitly not production-ready.** The ASU/AWS README says the code takes shortcuts, with relaxed authentication and authorization. Campuses that adopt it inherit an operations burden with no tenant model, no billing, no SLA and no support.
8. **STEM is unaddressed.** Math needs MathML and PDF/UA-2. Neither pipeline handles LaTeX-sourced documents or equation semantics.
9. **Forms are unaddressed.** Fillable forms (financial aid, admissions, HR) need field labels, tab order and error semantics, not just structure tags.
10. **Ongoing compliance is unaddressed.** Everything posted after the deadline must conform. A backlog tool with no intake path for new documents solves half the problem.

---

## 4. How Make PDF Accessible becomes the only place to go

The product thesis: **be the system of record for every document an institution publishes, and make each one accessible, or defensibly exempt, with proof.** ITHAKA-style remediation is one stage in a six-stage loop:

```
 Inventory  ->  Triage  ->  Remediate or Convert  ->  Publish  ->  Prove  ->  Maintain
 (find every  (apply the   (page-parallel engine     (push HTML   (evidence  (new uploads
  PDF, rank    rule's       for PDF; HTML-first       or PDF back  pack per   auto-remediate;
  by use)      exceptions)  conversion for web docs)  into the CMS) document)  drift alerts)
```

What each stage adds beyond ITHAKA and the open-source pipeline:

| Stage     | Capability                                                                                                                                                                   | Beats ITHAKA/ASU because                                        |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Inventory | Crawler + CMS/LMS connectors + analytics import; every PDF with page count, usage, owner, location                                                                           | They assume you already know your documents                     |
| Triage    | Rule-aware classification (delete, archive, convert, remediate, review) with cost estimate and recorded rationale                                                            | They remediate indiscriminately                                 |
| Remediate | Same page-parallel, pluggable, validated design, plus semantic QA (reading order, table headers, alt-text meaning) scored by an LLM and routed to humans when low confidence | They stop at the syntax checker                                 |
| Convert   | HTML-first output with semantic HTML, MathML for equations, CSV for tables, EPUB on request                                                                                  | They only produce PDF                                           |
| Publish   | WordPress, Drupal and LTI connectors write the result back with redirects and keep the original as an optional download                                                      | They control one platform                                       |
| Prove     | Signed, immutable evidence pack per document: tool versions, checker output, semantic scores, reviewer identity, timestamps; portable as JSON and PDF                        | Fleet statistics only                                           |
| Maintain  | Upload hooks, scheduled re-crawls, drift detection, and an Accessible Link that remediates on first click and caches thereafter                                              | On-demand only inside their own site                            |
| Operate   | Multi-tenant SaaS with SSO (SAML via InCommon, Entra ID), RBAC, quotas, metering, published prices, SLA, SOC 2 controls, FERPA handling                                      | A single-tenant internal system, or unauthenticated sample code |

### Quality bar we commit to publicly

- Every remediated PDF is validated with veraPDF (PDF/UA-1, and PDF/UA-2 where math is present). The raw report ships in the evidence pack.
- Every HTML conversion is validated with axe-core and an HTML validator; the raw reports ship in the evidence pack.
- Semantic checks (reading order, heading hierarchy, table header assignment, alt-text adequacy) are scored per element with confidence. Elements under the confidence threshold are routed to human review before the document is marked verified.
- We publish measured accuracy by document class (born-digital text, scanned, tables, forms, STEM) from our own eval set, and we never use the phrase "automatic compliance."

### Cost model we target

ITHAKA's $0.026 per page is AWS cost for a fully automated PDF path. Our engineering target is a fully automated cost of goods under $0.05 per page including the engine license, the LLM semantic checks and storage, so that a published price of $0.50 to $1.50 per page for automated tiers and $2 to $4 per page for verified tiers leaves room for support, sales and a human review operation. Human remediation today runs $2.50 to $12 per page.

---

## 5. Mapping to the current codebase

| ITHAKA stage | Current repo state                                                                                                                                          | Gap to close                                                                          |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Trigger      | SQS ingest queue and router Lambda exist (`services/functions/router/main.py`); EventBridge not used                                                        | Add the on-demand link endpoint and content-hash lookup; EventBridge events per stage |
| Split        | None. The worker processes whole documents (`services/worker/worker.py`)                                                                                    | Page splitter and Distributed Map                                                     |
| Tag          | `services/functions/tag_pdf/main.py` is a mock (`tags_applied = 25`)                                                                                        | Engine adapter with PDFix on Fargate; Adobe adapter second                            |
| Alt text     | `services/functions/alt_text/main.py` is a mock in the function; the worker has a real Bedrock client under `services/worker/src/pdf_worker/aws/bedrock.py` | One Bedrock alt-text service used by both paths, with confidence output               |
| Validate     | `services/functions/validator/validation_service.py` scores internal JSON, never the output PDF                                                             | veraPDF container on Fargate, results into the evidence pack                          |
| Merge        | None                                                                                                                                                        | Page merge with structure-tree stitching (engine-provided)                            |
| Cache        | None (artifacts keyed by document id, not content hash)                                                                                                     | Content-addressed artifact index in DynamoDB                                          |
| Observe      | Powertools logging and CloudWatch alarms exist (`infra/terraform/monitoring.tf`)                                                                            | Stage events, job timeline in evidence pack, per-page cost metrics                    |
| Output       | `services/worker/src/semantic_html_builder.py` produces real semantic HTML                                                                                  | Keep; add MathML, CSV export exists, add publish connectors                           |

The full, ordered implementation plan is in `docs/REMEDIATION-PIPELINE-SPECS.md`.

---

## 6. Sources

- AWS Public Sector Blog: How ITHAKA built an on-demand PDF remediation pipeline on AWS. https://aws.amazon.com/blogs/publicsector/how-ithaka-built-an-on-demand-pdf-remediation-pipeline-on-aws/
- PDF Association: 156 Million Pages. How ITHAKA Built PDF/UA Compliance on AWS with PDFix. https://pdfa.org/156-million-pages-how-ithaka-built-pdfua-compliance-on-aws-with-pdfix/
- PR Newswire: AWS Public Sector Blog Highlights PDFix's Role in ITHAKA's On-Demand PDF Accessibility Pipeline. https://www.prnewswire.com/news-releases/aws-public-sector-blog-highlights-pdfixs-role-in-ithakas-on-demand-pdf-accessibility-pipeline-302865907.html
- About JSTOR: ITHAKA named an AWS Champion for JSTOR accessibility remediation work. https://about.jstor.org/news/ithaka-named-an-aws-champion-for-jstor-accessibility-remediation-work/
- About JSTOR: Building accessibility into every article, on demand. https://about.jstor.org/blog/building-accessibility-into-every-article-on-demand/
- GovTech: 2026 Champions, ITHAKA. https://www.govtech.com/champions/2026/edtech/ithaka
- ASU/AWS open-source pipeline. https://github.com/ASUCICREPO/PDF_Accessibility
- AWS Public Sector Blog: From inaccessible to inclusive (the open-source solution announcement). https://aws.amazon.com/blogs/publicsector/from-inaccessible-to-inclusive-how-the-new-pdf-accessibility-remediation-solution-helps-institutions-compliantly-address-accessibility-requirements/
- Internal: `docs/research/higher-ed-market-research-2026-09.md` (market and regulatory context, code audit).
