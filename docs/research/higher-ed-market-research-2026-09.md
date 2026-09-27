# Market Research: PDF Accessibility Remediation for Higher Education

**Date:** 2026-09-27
**Question:** Is a PDF accessibility remediation product useful for colleges and universities that must make their websites accessible, and is it worth reviving this project?

---

## Bottom line

**Yes, the need is real, large, and funded. But the product as originally conceived ("AI auto-tags your PDFs") is no longer defensible on its own.**

1. **The legal driver is intact, and the deadline is now April 26, 2027.** DOJ pushed the ADA Title II web rule back one year on April 20, 2026. The standard is still WCAG 2.1 AA, and nothing else in the rule changed. For public universities that is about 7 months from today.
2. **The backlog is enormous.**
   - Ohio State's libraries got a vendor quote of about **$20M** ($5/page) to fix their noncompliant PDFs.
   - The University of North Dakota deleted 60% of its website PDFs and still has 91% of the rest needing remediation.
   - The University of Delaware has 10M+ files in Canvas.
3. **Basic automated tagging has become a commodity:**
   - An MIT-licensed AWS/ASU pipeline is free to deploy, and Ohio State and Penn State run it.
   - ITHAKA/JSTOR reports **$0.026/page** with a 98% check pass rate.
   - Adobe's Auto-Tag API is about $0.50/page.
   - Siteimprove launched a PDF Remediation Agent in June 2026.
   - YuJa Panorama sells structural PDF fixes inside the LMS.
4. **The open gap is the public-website document backlog, handled end to end.** That means:
   - an inventory of every PDF;
   - triage against the rule's exceptions (delete, archive, convert, or fix);
   - conversion to HTML published back into the CMS;
   - evidence of conformance for each document that a university can defend.

   Scanners find these PDFs but mostly don't fix them. LMS tools don't cover public websites. No product does the whole job.

5. **This codebase is not close to shipping the core feature.**
   - The PDF tagger is a mock.
   - The "accessible PDF" it outputs is the original file.
   - Accessibility scores are hardcoded.
   - The validator never checks the output file.

   The HTML export, the extraction pipeline, the dashboard and the WordPress plugin are real and reusable. They fit the website-backlog positioning well.

**Recommendation:** Revive it, but repositioned. Build the triage and HTML-first website backlog workflow, with quality evidence you can verify. Use an existing open engine (PDFix/veraPDF or Adobe's API) for the PDF output instead of building a tagger from scratch. Details are in [Section 5](#5-recommendation-how-to-revive-it).

---

## 1. The regulatory driver

### Key dates

| Date             | Event                                                                                                                                                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Apr 24, 2024     | DOJ publishes the Title II web accessibility final rule (28 CFR 35, subpart H). It requires WCAG 2.1 AA for state and local government web content and mobile apps, including public colleges and community colleges. |
| Jul 1, 2025      | Colorado HB21-1110 becomes enforceable after its safe harbor ends. Public colleges face a private right of action at $3,500 per violation. The federal extension does not change this.                                |
| Apr 20, 2026     | DOJ Interim Final Rule (FR Doc. 2026-07663) extends the deadlines by one year.                                                                                                                                        |
| May 11, 2026     | HHS extends its parallel Section 504 rule, which reaches private universities with HHS funding such as NIH grants. The new deadline is May 11, 2027 for recipients with 15+ employees.                                |
| May 21, 2026     | The National Federation of the Blind (NFB) sues DOJ and HHS in D. Md. to vacate the extensions. No ruling found as of this writing.                                                                                   |
| Aug 14, 2026     | The Unified Agenda still lists a DOJ proposed rule to make the 2024 rule "less costly" or "less burdensome." Nothing has been published yet.                                                                          |
| **Apr 26, 2027** | **New compliance date for entities with population 50,000+.** This covers nearly all public universities, because a state school takes the state's population.                                                        |
| Apr 26, 2028     | New compliance date for entities under 50,000 and for special districts. Some community college districts fall here.                                                                                                  |

DOJ's stated reason for the delay is notable for this product. It said it "overestimated the capabilities (whether staffing or technology) of covered entities to comply." Reporting on the rule says DOJ pointed in particular to remediation technology maturing more slowly than expected. That is the government saying automated remediation is not yet good enough, which is both the opportunity and the bar to clear.

### What the rule means for PDFs

- **Course content is covered.** The 2023 proposed rule had an exception for password-protected course content. The final rule dropped it, so PDFs uploaded to Canvas, Blackboard or D2L count.
- **Preexisting documents are exempt only if nobody uses them.** PDFs, Word files, slides and spreadsheets posted before the compliance date are exempt, _unless they are currently used to apply for, gain access to, or participate in_ a service or program.
  - Not exempt: financial aid forms, admissions and housing forms, current catalogs, current policies, syllabi, and readings in active courses.
  - Probably exempt: old board minutes and superseded catalogs, if genuinely unused or archived.
- **Archived content has to meet four tests.** It must predate the compliance date, be kept only for reference or recordkeeping, be unaltered, and sit in a clearly labeled archive area.
- **Everything new must conform.** Every document posted after the deadline has to meet WCAG 2.1 AA. The backlog therefore becomes a recurring stream of new work, not a one-time cleanup.
- **Exempt documents still have to be provided accessibly on request.**

**What this means for the product:** the exceptions make _classification_ valuable. A university does not need to fix every PDF. It needs to know which PDFs it must fix, which it can archive, and which it should delete, and to have proof of each decision.

### Enforcement climate

- **The Education Department's Office for Civil Rights (OCR) is weakened.**
  - Roughly half its staff were placed on leave in March 2025, and 7 of 12 regional offices closed.
  - GAO found about 90% of resolved complaints were dismissed between March and September 2025.
  - In June 2026, investigations began moving to DOJ.
  - No 2025 or 2026 OCR resolution agreement on college websites or PDFs was found.
- **Private litigation is rising.** Federal website accessibility suits hit 3,117 in 2025, up 27% (Seyfarth). _Rogers v. WVU_ (NFB, filed March 2025) targets inaccessible online course materials.
- **The pressure now comes from three places:** the fixed deadline, state law (Colorado, Texas TAC 206/213, Illinois IITAA, California), and private suits.

---

## 2. Demand signals

### Scale of the backlog

| Institution                     | Signal                                                                                                                                                                                 |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ohio State University Libraries | 110,000+ PDFs failed standards in 2024. A vendor quoted **$5/page, about $20M** to fix them (Inside Higher Ed, Jan 2026). The libraries built an AI pipeline with ASU and AWS instead. |
| University of North Dakota      | Cut its website PDFs from about 8,000 to 3,179 (-60%). **91% of the remaining files still need remediation** (Aug 2026).                                                               |
| University of Delaware          | 10M+ files in Canvas. Ally score of 64.7% in Fall 2024. 70,000+ images without alt text.                                                                                               |
| University of Washington        | 1M+ accessibility issues in course PDFs in 2023-24. A site-wide PDF tool license was estimated at **$800K to $1.3M**.                                                                  |
| Washington State University     | Set aside a **$300K remediation budget** for large online document repositories, alongside a DubBot scanning contract (Sept 2026).                                                     |
| ITHAKA / JSTOR                  | 156M pages. Manual remediation would have cost $156M to $624M. It built an on-demand pipeline instead.                                                                                 |

### How universities are actually responding

1. **Delete and archive first.**
   - UND's purge.
   - Iowa's "Remove, Revise, Right-First" framework.
   - Minnesota's formal "Remove Content" step.
   - UNC's "PDFebruary" campaign.
   - UNF auto-archives Canvas courses two weeks after each term.
2. **HTML-first policies.**
   - Michigan State: PDFs "are not to be created for class material."
   - UC Office of the President: publish "as much content as possible" as web pages.
3. **Build it themselves on the free AWS/ASU stack.** Ohio State Libraries, Penn State Libraries, Cal State LA, and CSU Fullerton have done this. Penn State needs human review to reach 91-93% compliance.
4. **System-wide licenses.**
   - CSU licenses Equidox and runs its own AI tool, which CSU says "will not produce a fully accessible PDF."
   - UC signed a system-wide YuJa agreement.
5. **Cooperative contracts.** Washington DES Contract 02024 (Document Accessibility and PDF Remediation, effective May 2026) and Minnesota's master contracts give other public buyers a ready-made purchasing path.

### Who buys

- **Budget holders:**
  - central digital accessibility offices
  - CIOs and IT
  - system offices (CSU, UC)
  - libraries
- **Faculty** are end users and a major pain point, but they are not buyers.
- **Procurement needs** a VPAT or accessibility conformance report for the product itself, a security review, and FERPA handling for course content.

### Hardest documents (least served by automation)

- **STEM and math.** Needs MathML and PDF/UA-2. Many checkers still only understand PDF/UA-1.
- **Complex tables and fillable forms.**
- **Degraded scans** in library archives.
- **Scholarly papers.** A CHI 2025 study found Acrobat's auto-tagging got reading order right only 66.7% of the time and headings 70.6%.
- **Chart alt text.** AI alt text can "satisfy a checker while providing little useful information" (UC Tech News).

---

## 3. Competitive landscape

### By category

| Category                     | Players                                                                                                                            | Detect or fix                               | Notes                                                                                                                                                                                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Inside the LMS               | Anthology/Blackboard **Ally**, **YuJa Panorama**, **D2L Accessibility+**, **UDOIT Advantage**, Canvas Course Accessibility Checker | Mostly detect, plus shallow or add-on fixes | Panorama is gaining fast (48% growth per ListEdTech) and sells a "Structural Remediation Max" add-on. Anthology went through Chapter 11 in 2025. Canvas's checker does not scan uploaded PDFs. |
| Website scanners             | **Siteimprove**, DubBot, Pope Tech, Acquia Optimize, Silktide, Deque                                                               | Detect. Siteimprove now also fixes.         | Siteimprove's PDF Remediation Agent (June 2026, paid add-on) added bulk workflows in July 2026. Pope Tech partners with Grackle, and Acquia with Allyant, for fixes.                           |
| Engines and APIs             | Adobe PDF Services Auto-Tag API, **AWS/ASU `PDF_Accessibility` (MIT)**, PDFix + veraPDF                                            | Automated tagging                           | Adobe costs about $0.50/page. The AWS stack costs cents per page plus Adobe fees. ITHAKA runs at $0.026/page with PDFix + veraPDF.                                                             |
| Software plus human services | CommonLook/Allyant, Equidox, Continual Engine PREP, GrackleDocs/AbleDocs, Documenta11y                                             | Fix, hybrid                                 | Human remediation runs **$2.50 to $12/page** (UND about $2.50, Harvard vendors $4-8, Syracuse/Allyant $5-8).                                                                                   |
| AI-native entrants           | CASO Comply, TestParty, Aelira, RemeDocs, CampusMind, UIC Equalify Reflow (open source, Docling + Claude)                          | Automated fix, sometimes HTML conversion    | Priced at $0.30 to $2/page. **No named university contracts found.** Quality claims are self-reported.                                                                                         |

### Where it's crowded

1. **Instructor-facing checkers in the LMS.** Already paid for through enterprise contracts.
2. **Website crawling and detection.**
3. **Human remediation at $2.50 to $12/page.** Dozens of interchangeable vendors.
4. **Raw automated tagging.** The price floor is now pennies per page.

### Where the gaps are

1. **The public-website backlog, handled end to end.** This is the heaviest Title II exposure, and LMS tools don't cover it. Scanners find the PDFs, but no one handles the full inventory → triage → fix or convert → replace-in-CMS loop.
2. **Converting to HTML instead of patching the PDF.** HTML-first is now policy at major universities. UDOIT converts into Canvas pages. Nobody publishes converted documents into WordPress or Drupal with redirects and the original kept as an optional download.
3. **Quality evidence you can verify.** Every vendor cites its own "90%+ automated" number. Nobody offers per-document evidence (machine validation, semantic checks and human sign-off) that a university can use to show good-faith compliance.
4. **STEM content.** LaTeX sources in, MathML out, and PDF/UA-2 validation.
5. **Transparent pricing.** Incumbents quote privately, so budget owners can't plan.

---

## 4. Where this project stands today (code audit)

The README claims "95% Enterprise-Ready." For the core promise, that isn't accurate.

| Component                        | Status                                                                   | Evidence                                                                                                                                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Upload, S3 storage, job queue    | Real                                                                     | `services/api`, `services/worker/worker.py`                                                                                                                                                              |
| Text, table and image extraction | Real (pdfplumber, PyMuPDF)                                               | `services/worker/worker.py:60-120`                                                                                                                                                                       |
| Structure analysis via LLM       | Real call, but not wired in                                              | `services/functions/structure/services.py:142` calls Bedrock with an older model ID. The worker instead uses a heuristic in which all-caps text becomes a heading (`services/worker/worker.py:710-736`). |
| **Tagged PDF output**            | **Mock**                                                                 | `services/functions/tag_pdf/main.py:22-34` (hardcoded `tags_applied = 25`). `services/functions/tagger/main.py` returns canned responses. No code anywhere writes a PDF structure tree.                  |
| **"Accessible PDF" artifact**    | **Returns the original file**                                            | `services/worker/worker.py:516`: `# For now, same as original`                                                                                                                                           |
| **Accessibility scores**         | **Hardcoded**                                                            | `services/worker/worker.py:536-538`: `"overall": 92`                                                                                                                                                     |
| Alt text                         | Mock in the function service                                             | `services/functions/alt_text/main.py:29-94`                                                                                                                                                              |
| Validator                        | Scores the app's internal JSON, not the output PDF                       | `services/functions/validator/validation_service.py`. No veraPDF, PAC or Matterhorn Protocol checks.                                                                                                     |
| Semantic HTML export             | Real and reasonably complete                                             | `services/worker/src/semantic_html_builder.py` (headings, lists, tables with header detection, figures with alt text)                                                                                    |
| Dashboard                        | Real (Next.js 15, about 25K lines)                                       | `dashboard/`                                                                                                                                                                                             |
| WordPress plugin                 | Real scaffold (about 600 lines). Hooks into uploads and posts to an API. | `integrations/wordpress/accesspdf-plugin.php` points at `api.accesspdf.com`                                                                                                                              |
| LTI integration                  | **Does not exist**                                                       | It is mentioned in docs, but there is no code.                                                                                                                                                           |
| Config hygiene                   | LocalStack credentials hardcoded in the worker                           | `services/worker/worker.py:47`                                                                                                                                                                           |

**Takeaway:** the scaffolding (queue, storage, dashboard, HTML export, WordPress hook) is a real head start. The hard, valuable part (correct structure, then either tagged PDF or HTML output, then proof it's correct) still has to be built.

**One positioning risk to fix now.** The JS snippet (`integrations/html-snippets/accesspdf-integration.js`) and the plugin's tagline ("discoverable by AI/LLMs") read like an overlay product. After the FTC's $1M order against accessiBe (final April 2025) for claiming AI could make sites compliant, any "automatic compliance" language is a legal and reputational liability. Market this as remediation with evidence, never as automatic compliance.

---

## 5. Recommendation: how to revive it

### Positioning

> "Clear your website's document backlog before the Title II deadline: every PDF inventoried, triaged, converted or fixed, and backed by a verifiable evidence report, at a published price per page."

### What to build, in priority order

1. **Inventory and triage (the wedge; nobody owns it).**
   - Crawl a university site, or read the WordPress/Drupal media library.
   - Use web analytics or access logs to find which PDFs anyone actually opens.
   - Classify each document against the rule:
     - delete (unused);
     - move to a labeled archive (meets the four archive conditions);
     - convert to HTML (current, text-heavy content);
     - remediate as PDF (forms, print-fidelity documents);
     - flag for human review (STEM, complex tables, scans).
   - Output a prioritized plan with a cost estimate. This alone is sellable, and it matches what UND, Iowa and UNC are doing by hand.
2. **HTML-first conversion that publishes into the CMS.** The existing `semantic_html_builder.py` and WordPress plugin are the head start.
   - Publish converted documents as real pages.
   - Add redirects from the old PDF URLs.
   - Keep the original available as an optional download.
   - Add Drupal next; it is common in higher ed.
3. **Don't build a tagger from scratch.** For documents that must stay PDFs, orchestrate PDFix + veraPDF (the ITHAKA approach) or Adobe's Auto-Tag API. Put the engineering effort into the parts above and below this layer, not into re-implementing tagging.
4. **Evidence pack per document (the moat).** For each document, combine:
   - veraPDF / PDF/UA machine validation;
   - WCAG checks on the HTML output;
   - LLM semantic checks (Is the reading order plausible? Does the alt text describe the chart's meaning?);
   - confidence scores for each element, with human review routed only to low-confidence items;
   - a signed audit trail.

   Replace the hardcoded scores with real measurements, and publish your measured accuracy by document type.

5. **Later: a STEM specialty.** Ingest LaTeX, output MathML in both HTML and PDF/UA-2. This is where faculty pain is highest and incumbents are weakest.
6. **Partner with the LMS incumbents; don't fight them.** Ally and Panorama own the instructor dashboard through bundled contracts. An LTI tool can come later, positioned as the engine that fixes what they flag. Accepting exports from scanners (DubBot, Pope Tech, Siteimprove) as inventory input is a cheaper integration.

### Pricing (suggested starting points, to validate)

- **Triage / inventory:** a flat fee per site or domain, as a low-friction entry offer.
- **Automated conversion or remediation:** about $0.50 to $1.50/page. That is above commodity cost but well below the $2.50 to $12 human rate.
- **Verified tier (human review of flagged items):** about $2 to $4/page.
- **Publish the price list.** Transparency is itself a differentiator in this market.

### Beyond higher ed

The same rule covers:

- about 12,500 independent school districts;
- about 90,800 local governments (cities, counties, townships, special districts such as transit agencies).

Most of these have less staff and budget than universities, plus a later deadline for the smallest ones (April 2028). The website-backlog product applies to them directly, and they tend to run on WordPress and Drupal.

### Timing

- **Buying window.** Public universities have until **April 26, 2027**. Budgets for fiscal year 2027 (starting July 1, 2026) are already set, so near-term deals will come from accessibility offices' discretionary or remediation funds, like WSU's $300K.
- **Plan for pilots now, larger contracts in FY28.** The work doesn't end at the deadline either: every new document must conform after it.
- **Risks that could shift timing:**
  - DOJ's proposed "less costly" rewrite could narrow the scope.
  - The NFB lawsuit could reinstate the original dates, which would increase urgency.

---

## 6. Risks

| Risk                                                                       | Severity  | Mitigation                                                                                                                   |
| -------------------------------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Commoditization. Free AWS/ASU stack, $0.026/page pipelines.                | High      | Don't sell tagging. Sell triage, conversion, CMS integration and evidence.                                                   |
| Incumbent bundling (Panorama add-ons, Siteimprove's agent)                 | High      | Focus on public websites and non-LMS content. Partner rather than compete for the LMS seat.                                  |
| Quality and claims liability (FTC v. accessiBe)                            | High      | Measured accuracy, human review tier, no "automatic compliance" language.                                                    |
| Rule softened by the DOJ proposed rule                                     | Medium    | Private suits, state law and OCR/504 obligations remain. The HTML-first and new-content workflow keeps its value regardless. |
| Higher-ed procurement friction (VPAT, security review, FERPA, long cycles) | Medium    | Start with website content (not FERPA-scoped), use cooperative contracts, pilot with small paid engagements.                 |
| Build time vs. a 7-month deadline window                                   | Medium    | Ship triage first. It needs the least new engineering and is sellable on its own.                                            |
| Our own dashboard must be accessible                                       | Must-have | WCAG 2.2 AA audit of `dashboard/` and `web/` before selling.                                                                 |

---

## 7. Suggested next steps

1. **Talk to 5 to 10 buyers.** Target digital accessibility leads at public universities, starting with those who published their approach: UND, UW, WSU, Iowa, UNC, and CSU campuses. Test whether website-backlog triage is the pain they would pay to remove.
2. **Run a backlog audit on one real university site** as a proof of concept. Count its PDFs, classify them, convert a sample to HTML, and measure the results with veraPDF and a screen reader.
3. **Choose the PDF engine.** Compare PDFix + veraPDF against Adobe's Auto-Tag API on quality, cost and licensing for SaaS use.
4. **Fix the repo's claims.** Update the README and STATUS to reflect what is actually implemented, and remove the hardcoded scores so the demo can't mislead anyone.

---

## Could not verify / open questions

- NFB v. DOJ/HHS: no ruling found after the May 2026 filing.
- Whether the DOJ "less costly" proposed rule has been drafted, and what it would change.
- Exact IPEDS counts of public institutions (roughly 1,600 public degree-granting institutions, unconfirmed).
- The share of website accessibility lawsuits that target higher ed.
- Sales cycle length and cooperative-contract options (E&I, Internet2 NET+) for PDF remediation specifically.
- The public-higher-ed spend estimate of about $30M to $120M/yr during 2026-2028 is a rough internal estimate, not an analyst figure.

Research note: figures were gathered from search-result extracts. Direct page fetches were blocked in the research environment. The key figures were cross-checked: the April 26, 2027 deadline, the Ohio State $20M quote, the ITHAKA $0.026/page cost, and Siteimprove's June 2026 agent. Verify any number against its source before quoting it externally.

---

## Key sources

**Regulation**

- [Federal Register: DOJ extension IFR (Apr 20, 2026)](https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web)
- [Federal Register: 2024 Title II final rule](https://www.federalregister.gov/documents/2024/04/24/2024-07758/nondiscrimination-on-the-basis-of-disability-accessibility-of-web-information-and-services-of-state)
- [Federal Register: HHS 504 extension (May 11, 2026)](https://www.federalregister.gov/documents/2026/05/11/2026-09266/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web)
- [UPCEA: DOJ extends accessibility deadline to April 2027](https://upcea.edu/doj-extends-accessibility-deadline-to-april-2027-policy-matters-april-2026/)
- [EDUCAUSE Review: DOJ and HHS extend deadlines](https://er.educause.edu/articles/2026/6/doj-and-hhs-extend-web-accessibility-deadlines-to-2027-2028)
- [Seyfarth ADA Title III: NFB challenges extensions](https://www.adatitleiii.com/2026/06/national-federation-of-the-blind-challenges-last-minute-deadline-extensions-for-website-and-mobile-app-accessibility/)
- [Seyfarth ADA Title III: 2025 lawsuit filings](https://www.adatitleiii.com/2026/03/federal-court-website-accessibility-lawsuit-filings-bounce-back-in-2025/)
- [NFB press release on lawsuit](https://nfb.org/about-us/press-room/national-federation-blind-sues-government-over-delay-accessibility-rules)
- [UMich guidance on electronic documents](https://accessibility.umich.edu/strategy-policy/um-guidance/electronic-documents)
- [Colorado OIT HB21-1110 FAQ](https://oit.colorado.gov/hb21-1110-faq)
- [Inside Higher Ed: ED shifts civil rights enforcement to DOJ](https://www.insidehighered.com/news/government/2026/06/16/ed-shifts-some-civil-rights-enforcement-justice-department)
- [FTC final order against accessiBe](https://www.ftc.gov/news-events/news/press-releases/2025/04/ftc-approves-final-order-requiring-accessibe-pay-1-million)

**Demand**

- [Inside Higher Ed: Higher Ed Prepares for New Era of Accessibility (Jan 2026)](https://www.insidehighered.com/news/government/colleges-localities/2026/01/21/higher-ed-prepares-new-era-ada)
- [Ohio State Libraries: improving access to digital materials](https://library.osu.edu/news/university-libraries-improves-access-to-digital-materials)
- [UND: PDF remediation updates (Aug 2026)](https://blogs.und.edu/for-your-health/2026/08/13/pdf-remediation-updates-from-und/)
- [University of Washington: PDF report](https://www.washington.edu/accessibility/academic-course-content-action-team/pdf-report/)
- [University of Delaware: Canvas file accessibility](https://sites.udel.edu/canvas/2024/10/accessibility-for-canvas-files-and-course-content/)
- [WSU: enterprise accessibility investment (Sept 2026)](https://news.wsu.edu/news/2026/09/24/wsu-invests-in-new-enterprise-tools-resources-to-support-digital-accessibility/)
- [Harvard: document remediation vendors](https://accessibility.huit.harvard.edu/doc-vendors)
- [Michigan State: file type guidance](https://webaccess.msu.edu/tutorials/basics/file-type)
- [UC Tech News: PDF accessibility trends in higher ed](https://uctechnews.ucop.edu/pdf-accessibility-trends-in-higher-education/)
- [Washington DES Contract 02024](https://apps.des.wa.gov/DESContracts/Home/ContractSummary/02024)
- [CHI 2025 study on scholarly PDF remediation](https://dl.acm.org/doi/full/10.1145/3706598.3713084)

**Competitors**

- [AWS: PDF accessibility remediation solution](https://aws.amazon.com/blogs/publicsector/from-inaccessible-to-inclusive-how-the-new-pdf-accessibility-remediation-solution-helps-institutions-compliantly-address-accessibility-requirements/)
- [GitHub: ASUCICREPO/PDF_Accessibility](https://github.com/ASUCICREPO/PDF_Accessibility)
- [AWS: How ITHAKA built an on-demand PDF remediation pipeline](https://aws.amazon.com/blogs/publicsector/how-ithaka-built-an-on-demand-pdf-remediation-pipeline-on-aws/)
- [PDF Association: 156 million pages at ITHAKA](https://pdfa.org/156-million-pages-how-ithaka-built-pdfua-compliance-on-aws-with-pdfix/)
- [Siteimprove: June 2026 release notes (PDF Remediation Agent)](https://help.siteimprove.com/support/solutions/articles/80001215321-june-2026-release-notes-fix-pdf-accessibility-issues-with-new-agent-shadow-dom-support-for-seo-pag)
- [Siteimprove: July 2026 release notes (bulk workflows)](https://help.siteimprove.com/support/solutions/articles/80001216641-july-2026-release-notes-new-in-the-pdf-remediation-agent-language-detection-bulk-workflows-and-st)
- [YuJa Panorama Structural Remediation](https://www.yuja.com/panorama/structural-remediation/)
- [ListEdTech: Anthology's Chapter 11](https://listedtech.com/blog/anthologys-chapter-11/)
- [ListEdTech: two accessibility vendors to watch](https://listedtech.com/blog/digital-accessibility-in-higher-education-two-vendors-to-watch/)
- [Anthology Ally PDF Quick Fixes](https://community.anthology.com/public/blogs/pdf-assisted-remediation-quick-fixes-is-almost-here-answers-to-the-faqs-youve-been-wondering-about-2025-08-22)
- [D2L Accessibility+](https://www.d2l.com/newsroom/d2l_launches_accessibility_plus_to_transform_digital_learning/)
- [Adobe PDF Services pricing](https://developer.adobe.com/document-services/pricing/main)
- [Penn State Libraries self-serve PDF remediation tool](https://www.psu.edu/news/university-libraries/story/university-libraries-launches-new-self-serve-pdf-remediation-tool)
- [Syracuse: Allyant remediation services](https://itsaccessibility.syr.edu/accessible-documents/allyant-remediation-services/)
- [UIC Equalify Reflow](https://github.com/EqualifyEverything/equalify-reflow)
- [Pope Tech + Grackle partnership](https://blog.pope.tech/2026/05/26/pope-tech-partners-with-grackle-to-introduce-pdf-scanning/)
- [PDF Association: accessible math in PDF](https://pdfa.org/accessible-math-in-pdf-finally/)
