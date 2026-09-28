# Make PDF Accessible — Business Plan

## The system of record for every document an institution publishes: inventoried, triaged, made accessible or defensibly exempt, with proof.

**Version:** 1.0 (2026-09-28)
**Status:** Draft for founder review. Numbers marked _estimate_ are internal models, not analyst figures.
**Companion docs:** `docs/research/higher-ed-market-research-2026-09.md` (market evidence), `docs/research/ithaka-pipeline-analysis.md` (technical benchmark), `docs/PLATFORM-PRD.md` (product definition), `docs/adr/` (architecture decisions).

---

## 1. Executive summary

Every public university, community college, school district and local government in the United States must make its web content, including PDFs, conform to WCAG 2.1 AA by **April 26, 2027** (entities serving 50,000+ people) or **April 26, 2028** (smaller entities) under the Department of Justice's ADA Title II rule. Private universities that take HHS money face a parallel Section 504 deadline of May 11, 2027. State laws (Colorado, Texas, Illinois, California) and a rising wave of private lawsuits apply pressure regardless of federal timing.

The documents are the hard part. Ohio State's libraries were quoted about $20 million to fix their PDFs by hand. The University of North Dakota deleted 60% of its website PDFs and still has 91% of the remainder needing work. ITHAKA (JSTOR) built its own AWS pipeline rather than pay $156M to $624M for manual remediation of 156 million pages.

Automated tagging has become a commodity: AWS and ASU publish a free open-source pipeline, ITHAKA runs at $0.026 per page, Adobe sells an API at about $0.50 per page. What nobody sells is the **whole job**: find every document, decide which ones the rule actually requires you to fix, fix or convert them, put the result back where users find it, and keep a per-document record that a compliance office can defend. Scanners find PDFs but don't fix them. LMS tools don't cover public websites. Remediation vendors fix what you send them and quote privately.

**Make PDF Accessible is the end-to-end document accessibility platform for institutions that must comply.** It runs a six-stage loop, Inventory → Triage → Remediate or Convert → Publish → Prove → Maintain, on AWS, with published per-page prices, an evidence pack for every document, and connectors for WordPress, Drupal and the LMS. It adopts every architectural best practice from the ITHAKA pipeline (on-demand remediation, page-parallel processing, pluggable engines, independent validation, stage-level events) and adds the seven stages ITHAKA never needed because it owns one corpus and one website.

**Business model:** annual SaaS subscriptions with included page volume (Team $6K, Campus $30K, System from $100K per year), page overages ($0.60 to $0.95), and a human-verified tier at $2.50 to $8 per page. Target automated cost of goods under $0.05 per page.

**Three-year outlook (estimate):** 45 paying institutions and $0.8M ARR twelve months after launch, $4.2M ARR at 24 months, $11.3M ARR at 36 months, cash-flow positive in year three. Cumulative investment required: about $2.4M, or a slower bootstrapped path funded by pilots and verified-tier services.

**Ask:** approve the product plan in `docs/PLATFORM-PRD.md`, fund the first two hires (pipeline engineer and higher-ed go-to-market lead), and start five paid pilots before the end of 2026.

---

## 2. Mission, vision, and principles

**Mission.** Make every public document readable by everyone, and make it easy to prove.

**Vision.** By 2029, Make PDF Accessible is where institutions in the United States go for document accessibility: the place a CIO points to when a regulator, a plaintiff's lawyer, or a student asks "is this document accessible, and how do you know?"

**Product principles**

1. **Evidence over claims.** We never say "automatic compliance." We produce validator output, semantic scores and human sign-off for each document, and we publish our measured accuracy by document type. The FTC's $1M order against accessiBe (2025) for overclaiming AI compliance is the line we will not cross.
2. **Do the whole job.** A feature that finds a problem without offering the fix, or fixes a file without putting it back where users find it, is not done.
3. **HTML first, PDF when it must be PDF.** Text-heavy web documents become web pages. Forms, print-fidelity documents and archives stay PDF and get tagged.
4. **Pay for what you use, at a published price.** Per-page pricing on the website, in the dashboard and on the invoice.
5. **Locked-down by default.** Enterprise accounts have SCPs, private buckets and change control. We design for that instead of fighting it.
6. **Our own product must be accessible.** WCAG 2.2 AA audit of every surface we sell, an ACR/VPAT on the website, and no exceptions.

---

## 3. Market

### 3.1 The regulatory driver

| Driver                                               | What it requires                                                                                 | Who it hits                                                                                         | When                                                                                 |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| DOJ ADA Title II web rule (28 CFR 35 subpart H)      | WCAG 2.1 AA for web content and mobile apps, including documents, course content and LMS content | State and local governments, public colleges and universities, community colleges, school districts | Apr 26, 2027 (population 50,000+); Apr 26, 2028 (under 50,000 and special districts) |
| HHS Section 504 rule                                 | Same standard for recipients of HHS funds                                                        | Private universities with NIH or other HHS grants, hospitals, health systems                        | May 11, 2027 (15+ employees)                                                         |
| Section 508                                          | Federal agencies and their contractors                                                           | Federal, vendors selling to federal                                                                 | In force                                                                             |
| Colorado HB21-1110                                   | State accessibility standard, private right of action at $3,500 per violation                    | Colorado public entities including colleges                                                         | Enforceable since Jul 1, 2025                                                        |
| Texas TAC 206/213, Illinois IITAA, California AB 434 | State standards                                                                                  | State agencies and public universities                                                              | In force                                                                             |
| Private litigation                                   | ADA Title II/III suits over inaccessible course materials and websites                           | Everyone above plus private institutions                                                            | 3,117 federal website suits in 2025, up 27%                                          |

Two details of the DOJ rule shape the product:

- **Exceptions make triage valuable.** Pre-existing documents are exempt only if nobody currently uses them to apply for, access or participate in a program. Archived content must meet four tests. An institution does not need to fix every PDF; it needs to know which ones, and to record the decision.
- **Everything new must conform.** After the deadline, every posted document has to meet the standard. The backlog becomes a permanent stream.

DOJ's stated reason for its 2026 delay was that it "overestimated the capabilities (whether staffing or technology) of covered entities to comply," pointing at remediation technology. That is the opportunity and the quality bar in one sentence.

### 3.2 Market size (estimate)

| Segment                                                            | Units (approx.)           | Assumed average annual spend on document accessibility software | Annual spend pool |
| ------------------------------------------------------------------ | ------------------------- | --------------------------------------------------------------- | ----------------- |
| Public degree-granting institutions (US)                           | 1,600                     | $30,000                                                         | $48M              |
| Private nonprofit and for-profit institutions                      | 2,300                     | $15,000                                                         | $35M              |
| K-12 school districts                                              | 13,000                    | $5,000                                                          | $65M              |
| Local governments (cities, counties, townships, special districts) | 90,000                    | $1,500 (most are tiny; a few thousand are material)             | $135M             |
| Healthcare and HHS-funded organizations                            | 6,000 hospitals + systems | $10,000                                                         | $60M              |
| Federal contractors, publishers, libraries and archives            | n/a                       | n/a                                                             | $40M              |
| **Total addressable spend (US, annual)**                           |                           |                                                                 | **≈ $380M**       |

Serviceable market for the first three years (public and private higher education plus the largest 5,000 K-12 districts and local governments, reachable through the channels in section 7): **≈ $150M per year**. The internal estimate in the market research doc, $30M to $120M per year of public higher-ed spend during 2026 to 2028, is consistent with this. Spend is front-loaded around the deadlines, then settles into a recurring maintenance stream.

### 3.3 Demand evidence

- Ohio State University Libraries: 110,000+ failing PDFs, $5 per page vendor quote (~$20M), built an internal AWS pipeline instead.
- University of North Dakota: cut website PDFs from about 8,000 to 3,179; 91% of the remainder still need remediation (August 2026).
- University of Delaware: 10M+ files in Canvas; 70,000+ images without alt text.
- University of Washington: 1M+ accessibility issues in course PDFs; a site-wide license estimated at $800K to $1.3M.
- Washington State University: $300K remediation budget set aside alongside a scanning contract (September 2026).
- Washington DES Contract 02024 (Document Accessibility and PDF Remediation, May 2026) and Minnesota master contracts create ready purchasing paths.
- CSU licenses Equidox system-wide and says its own AI tool "will not produce a fully accessible PDF." UC signed a system-wide YuJa agreement.

### 3.4 Customer segments and personas

| Segment                                  | Buyer                                                     | Champion                                  | Pain                                                             | Budget source                                                |
| ---------------------------------------- | --------------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| Public research universities and systems | CIO, Chief Digital Accessibility Officer, General Counsel | Web/digital accessibility lead, libraries | Public-website backlog, LMS course content, evidence for OCR/DOJ | Central IT, accessibility office, one-time remediation funds |
| Community colleges and small publics     | CIO or Director of Web Services                           | Marketing/web team                        | Thin staff, WordPress/Drupal sites, deadline anxiety             | State system funds, cooperative contracts                    |
| Private universities (504)               | CIO, Compliance                                           | Disability services, libraries            | Course content, research PDFs                                    | IT budget, grant compliance                                  |
| K-12 districts                           | Director of Technology, Communications                    | Webmaster                                 | Board policies, forms, newsletters in PDF; tiny staff            | E-rate-adjacent tech budgets, state grants                   |
| Local governments                        | IT Director, City Clerk, ADA Coordinator                  | Web team                                  | Agendas, minutes, ordinances, permits in PDF                     | General fund, ADA compliance line                            |
| Publishers, libraries, archives          | Head of Product/Engineering                               | Accessibility lead                        | Large corpora, on-demand delivery                                | Product budget                                               |

Faculty and content authors are end users, not buyers. Procurement requires a VPAT/ACR for our product, a security review (HECVAT for higher ed), FERPA handling for course content and, increasingly, a SOC 2 report.

---

## 4. Product

### 4.1 The six-stage loop

| Stage                    | What it does                                                                                                                                                                                                  | Standalone value                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **Inventory**            | Crawls public sites, reads WordPress/Drupal media libraries and LMS courses, imports scanner exports (Siteimprove, DubBot, Pope Tech) and analytics; records every PDF with pages, owner, location, usage     | A complete, prioritized list. Sellable alone; matches what UND, Iowa and UNC do by hand |
| **Triage**               | Classifies each document against the rule: delete, archive, convert to HTML, remediate as PDF, or route to review; estimates cost; records the rationale                                                      | A defensible plan and a budget number                                                   |
| **Remediate or Convert** | Page-parallel pipeline with pluggable engines (PDFix + veraPDF first, Adobe Auto-Tag second) for PDFs; HTML-first conversion with MathML and CSV tables for web documents; AI alt text with confidence scores | Accessible outputs                                                                      |
| **Publish**              | Writes results back into WordPress, Drupal and the LMS with redirects, keeps the original as an optional download, serves an Accessible Link for any URL                                                      | Users actually get the accessible version                                               |
| **Prove**                | Signed, immutable evidence pack per document: validator output, semantic scores, reviewer sign-off, tool versions, timestamps; exportable as JSON and PDF; institution-wide conformance dashboard             | Something to hand a regulator or a plaintiff                                            |
| **Maintain**             | Upload hooks, scheduled re-crawls, drift detection, on-demand remediation with caching, alerts                                                                                                                | Compliance after the deadline, not just before                                          |

### 4.2 Why this beats the alternatives

| Alternative                                                   | What it does well                                   | Where it stops                                                                  | Our answer                                                                 |
| ------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| ITHAKA's pipeline (internal)                                  | On-demand, cheap, validated                         | Single corpus, PDF only, no inventory/triage/publish/evidence                   | Same architecture, plus the other five stages, as a product                |
| ASU/AWS open-source pipeline                                  | Free, AWS-native                                    | Not production-ready, no auth, no tenant model, Adobe fees, you operate it      | Managed SaaS with SSO, SLA, evidence, support                              |
| Adobe Auto-Tag API, PDFix SDK                                 | Good engines                                        | Engines, not workflows                                                          | We orchestrate them; engine choice is ours to swap                         |
| Siteimprove PDF Remediation Agent, DubBot, Pope Tech          | Site scanning, fixes in Siteimprove's case          | Detection-centric, no triage against the rule, no CMS publish, no evidence pack | Import their scans as inventory input; partner, don't fight                |
| Ally, YuJa Panorama, D2L Accessibility+, UDOIT                | LMS instructor dashboards through bundled contracts | LMS only; public website untouched                                              | LTI tool positions us as the engine that fixes what they flag              |
| CommonLook/Allyant, Equidox, Continual Engine, GrackleDocs    | Human-quality output                                | $2.50 to $12 per page, private quotes, slow                                     | Automated tiers at $0.60 to $1.50, verified tier at $2.50 to $8, published |
| AI-native entrants (CASO Comply, TestParty, Aelira, RemeDocs) | Cheap automated fixes                               | Self-reported quality, no named university contracts, no end-to-end loop        | Measured accuracy, evidence, integrations                                  |

### 4.3 Product roadmap (slices, each independently shippable)

| Slice                 | Target   | Scope                                                                                                                                     |
| --------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| S0 Truth              | Oct 2026 | Remove hardcoded scores and mock outputs from the demo; README and STATUS reflect reality (a sales prerequisite)                          |
| S1 Inventory & Triage | Nov 2026 | Crawler, WordPress plugin inventory sync, classification, plan + cost estimate, CSV/PDF export, free website report on the marketing site |
| S2 Real remediation   | Dec 2026 | PDFix engine on Fargate, veraPDF validation, page-parallel Step Functions, evidence pack v1, on-demand Accessible Link with caching       |
| S3 HTML-first publish | Jan 2027 | HTML conversion hardened, WordPress publish-back with redirects, Drupal module beta                                                       |
| S4 Verified tier      | Feb 2027 | Human review workbench with confidence routing, reviewer sign-off in the evidence pack, service operations                                |
| S5 Enterprise         | Mar 2027 | SAML SSO (InCommon, Entra ID), RBAC, quotas, metering and billing, audit log, SOC 2 Type I controls, HECVAT, ACR                          |
| S6 LMS & STEM         | Q2 2027  | LTI 1.3 tool for Canvas/Blackboard/D2L/Moodle, MathML and PDF/UA-2, forms remediation                                                     |
| S7 Scale              | H2 2027  | Multi-region, dedicated-account tier, marketplace listings, K-12 and local-government packaging                                           |

The deadline for large public entities is April 26, 2027. S1 through S5 land before it; S6 and S7 serve the after-deadline stream and the 2028 cohort.

---

## 5. Pricing and packaging

All prices are public on the marketing site. Annual billing by default; monthly available on Team.

| Plan                              | Annual price      | Included                                                                                                                                                          | Overage    | Notes                                              |
| --------------------------------- | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------- |
| **Free**                          | $0                | WordPress inventory plugin, 5 single-PDF checks per day on the website, one free website inventory report (up to 5,000 PDFs)                                      | n/a        | Lead generation; no credit card                    |
| **Team**                          | $6,000            | 6,000 automated pages/year, 1 domain, 5 users, WordPress connector, evidence packs, email support                                                                 | $0.95/page | Departments, small districts, small towns          |
| **Campus**                        | $30,000           | 50,000 automated pages/year, unlimited domains, SSO, Drupal + LTI connectors, API and webhooks, priority queue, 99.5% SLA                                         | $0.60/page | Single institution                                 |
| **System / Enterprise**           | from $100,000     | 250,000+ automated pages/year, multi-institution tenancy, dedicated KMS keys or dedicated AWS account option, 99.9% SLA, custom DPA, cooperative-contract pricing | negotiated | Systems, states, large districts                   |
| **Verified add-on**               | per page          | Human review of flagged elements: $2.50/page. Full human review: $4.00/page. STEM (MathML) and fillable forms: $6 to $8/page                                      |            | 5-business-day turnaround standard; rush available |
| **Inventory & Triage engagement** | $2,500 per domain | Crawl, triage plan, cost estimate, quarterly re-crawl, for institutions not yet on a plan                                                                         |            | Converts to Campus credit                          |

Rationale: automated prices sit above commodity engine cost (pennies) and well below human rates ($2.50 to $12), with the verified tier priced at the low end of human rates for a better product (automation plus targeted review plus evidence). Transparency is itself a differentiator; incumbents quote privately.

---

## 6. Unit economics (estimate)

| Item                                                                                  | Automated page | Verified page (flagged review) |
| ------------------------------------------------------------------------------------- | -------------- | ------------------------------ |
| AWS compute, storage, orchestration                                                   | $0.020         | $0.020                         |
| LLM calls (alt text, semantic checks)                                                 | $0.015         | $0.015                         |
| Engine license (PDFix SDK, amortized)                                                 | $0.010         | $0.010                         |
| Human review labor (about 20 pages per reviewer-hour at $25/hour, flagged pages only) |                | $1.25                          |
| Support and success allocation                                                        | $0.010         | $0.050                         |
| **Cost of goods**                                                                     | **≈ $0.055**   | **≈ $1.35**                    |
| Effective price                                                                       | $0.60 to $1.00 | $2.50                          |
| **Gross margin**                                                                      | **≈ 90%**      | **≈ 46%**                      |

Blended gross margin target: 75% in year one rising to 78% as the subscription share grows. ITHAKA's $0.026 per page validates the AWS line; our number is higher because we add semantic checks, evidence storage and engine licensing.

---

## 7. Go-to-market

### 7.1 Motion

1. **Land with free inventory.** The WordPress plugin (already published to WordPress.org's pipeline) inventories a site's PDFs at no cost. The marketing site offers a free website inventory report: enter a domain, get an emailed report with counts, page totals and an estimated cost by remediation path. Both feed a triage conversation.
2. **Paid pilot.** $5,000 to $15,000, 30 days, one domain: inventory, triage plan, 500 to 2,000 pages remediated or converted, evidence packs, a screen-reader walkthrough with the customer's own team. Success criteria agreed in writing.
3. **Convert to Campus.** Pilot fee credited to the first year.
4. **Expand to the system.** Reference from the first campus; system-office pricing.
5. **After the deadline, maintain.** Upload hooks and re-crawls keep the subscription valuable when the backlog is gone.

### 7.2 Channels

- **Direct sales to higher education**, starting with institutions that have publicly described their backlog: UND, UW, WSU, Iowa, UNC, CSU campuses, Ohio State and Penn State libraries (who run the free pipeline and need the rest of the loop).
- **Cooperative contracts:** Washington DES 02024 via a partner, Minnesota master contracts, E&I Cooperative, Sourcewell, TIPS. Long lead times; start applications in Q4 2026.
- **AWS Marketplace and AWS Public Sector co-sell.** The ITHAKA story makes AWS's public sector team a warm channel; a Marketplace listing lets institutions buy against committed AWS spend.
- **Partners:** scanners (DubBot, Pope Tech, Siteimprove import), CMS agencies serving higher ed (WordPress and Drupal shops), LMS vendors via LTI, accessibility consultancies who resell the verified tier.
- **Content and community:** Title II countdown, state-law guides, a public accuracy report, backlog calculators; talks at EDUCAUSE Annual, Accessing Higher Ground, CSUN, AHEAD, HighEdWeb, WPCampus, DrupalCon higher-ed track, NAGW and the Digital Government Summit.

### 7.3 Sales cycle and targets (estimate)

| Metric                            | Target                                                      |
| --------------------------------- | ----------------------------------------------------------- |
| Pilot to paid conversion          | 60%                                                         |
| Team/Campus sales cycle           | 45 to 90 days (pilot-led)                                   |
| System sales cycle                | 6 to 9 months                                               |
| Net revenue retention             | 115% (page growth after the deadline, verified tier attach) |
| Customer acquisition cost payback | under 12 months                                             |

### 7.4 Procurement readiness checklist

ACR/VPAT for the dashboard and the marketing site; HECVAT Full; SOC 2 Type I within 9 months of launch and Type II by month 18; FERPA data processing addendum; accessibility statement; security whitepaper; data retention and deletion policy; W-9 and cooperative-contract paperwork.

---

## 8. Operations

- **Verified tier operations.** A reviewer pool (in-house lead plus contracted certified accessibility professionals) works from the review workbench, which shows only flagged elements. Throughput, accuracy and turnaround are tracked per reviewer. Reviewer identity and timestamp go into the evidence pack.
- **Support.** Email and in-app for Team; named success manager for Campus and above; status page; 99.5%/99.9% SLAs with credits.
- **Trust and compliance.** SOC 2 program from day one (access reviews, change management, vendor management, incident response), annual penetration test, FERPA and state data-privacy handling, no training of models on customer content, region pinning for data residency.
- **Cost management.** Per-page cost metering by stage, budgets and anomaly alerts on AWS spend, engine license utilization tracking.

---

## 9. Technology and intellectual property

The platform runs on AWS: S3 for documents and evidence, Step Functions Distributed Map for page-parallel orchestration, Lambda and Fargate for compute, Amazon Bedrock (Anthropic Claude models) for alt text and semantic checks, Textract for OCR, Aurora PostgreSQL and DynamoDB for state, Cognito for identity with SAML federation, CloudFront and WAF at the edge, EventBridge for stage events. The marketing site is a static Next.js export on S3 and CloudFront. All infrastructure is Terraform in this repository. Architecture decisions are recorded in `docs/adr/`.

Defensible assets are not the tagging engine (licensed, swappable) but: the inventory and triage rules engine, the evidence pack format and its signing chain, the CMS and LMS connectors, the eval set and published accuracy by document class, the confidence-routing model that decides what humans look at, and the customer data on what institutions actually have and use.

---

## 10. Team and hiring plan

**Now:** founder (product and engineering), fractional accessibility specialist.

| Hire                                                   | When           | Why                                                              |
| ------------------------------------------------------ | -------------- | ---------------------------------------------------------------- |
| Senior pipeline engineer (Python, AWS, PDF)            | Q4 2026        | Replace mocks with the real engine, validation and evidence pack |
| Higher-ed go-to-market lead                            | Q4 2026        | Pilots, cooperative contracts, conference presence               |
| Accessibility QA lead (IAAP CPACC/WAS)                 | Q1 2027        | Own the eval set, the verified tier and the ACR                  |
| Integrations engineer (PHP/Drupal/LTI)                 | Q1 2027        | Publish-back connectors                                          |
| Customer success manager                               | Q2 2027        | Pilot delivery and renewals                                      |
| Security and compliance lead (fractional to full-time) | Q2 2027        | SOC 2, HECVAT, pen tests                                         |
| Reviewers (contract pool)                              | Q1 2027 onward | Verified tier                                                    |

Headcount (average): 7 in year one, 16 in year two, 30 in year three.

Advisors to recruit: a higher-ed accessibility officer, a disability-law practitioner, a former state procurement official, a PDF standards contributor.

---

## 11. Financial plan (estimate)

Fiscal years run October to September, starting with the launch quarter (Q4 2026).

### 11.1 Assumptions

| Assumption                                                                     | FY1 (Oct 2026–Sep 2027) | FY2         | FY3         |
| ------------------------------------------------------------------------------ | ----------------------- | ----------- | ----------- |
| Paying institutions at year end                                                | 45                      | 175         | 420         |
| Average contract value (subscription)                                          | $18,000                 | $24,000     | $27,000     |
| Subscription ARR at year end                                                   | $0.81M                  | $4.2M       | $11.3M      |
| Recognized subscription revenue (ramped)                                       | $0.37M                  | $2.4M       | $7.4M       |
| Verified tier and pilot services revenue                                       | $0.20M                  | $0.9M       | $2.2M       |
| **Total revenue**                                                              | **$0.57M**              | **$3.3M**   | **$9.6M**   |
| Blended gross margin                                                           | 72%                     | 75%         | 77%         |
| Average headcount                                                              | 7                       | 16          | 30          |
| People cost (fully loaded, $170K average)                                      | $1.2M                   | $2.7M       | $5.1M       |
| Non-people operating cost (marketing, events, tools, legal, audits, insurance) | $0.45M                  | $0.9M       | $1.6M       |
| **Operating result**                                                           | **−$1.24M**             | **−$1.12M** | **+$0.69M** |

Cumulative cash need before break-even: about **$2.4M**. With a 25% buffer, the raise is **$3.0M** (seed), or a bootstrapped variant that delays the FY2 hires by two quarters and funds growth from pilot and verified-tier revenue.

### 11.2 Volume sanity check

FY3 subscription revenue of $7.4M at a blended effective price near $0.70 per page implies about 10.6M pages per year, or roughly 0.9M pages per month. At $0.055 per page the automated cost of goods is about $0.6M, under 8% of subscription revenue, which supports the 85% subscription margin assumption. The verified tier at 46% margin pulls the blend down to the 75% to 78% range.

### 11.3 Sensitivities

- **Rule softened by the DOJ proposed rewrite:** private suits, state law and HHS 504 remain; assume a 30% slower FY2 ramp. Break-even slips two quarters.
- **NFB lawsuit reinstates original deadlines:** urgency rises; pipeline capacity and reviewer pool become the constraint. Pre-contract reviewer capacity in Q1 2027.
- **Engine license terms change:** the Adobe adapter is the fallback; per-page cost of goods rises to about $0.10, margin stays above 80%.

---

## 12. Risks and mitigations

| Risk                                                                 | Severity  | Mitigation                                                                                                                                  |
| -------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Commoditized tagging (free AWS/ASU stack, $0.026 per page pipelines) | High      | Don't sell tagging. Sell inventory, triage, conversion, publish-back and evidence. Use the commodity engines ourselves.                     |
| Incumbent bundling (Siteimprove's agent, Panorama add-ons)           | High      | Own the public-website document loop and evidence; integrate with scanners and LMS tools instead of replacing them.                         |
| Quality and claims liability (FTC v. accessiBe)                      | High      | Measured accuracy, verified tier, evidence packs, no "automatic compliance" language, legal review of all marketing copy.                   |
| Rule delayed or narrowed again                                       | Medium    | Multi-driver demand (state law, litigation, 504, 508); maintenance value after the backlog.                                                 |
| Procurement friction (VPAT, HECVAT, FERPA, SOC 2, long cycles)       | Medium    | Start with public website content (not FERPA-scoped), cooperative contracts, pilots under signature thresholds, SOC 2 program from day one. |
| Seven-month build window to the 2027 deadline                        | Medium    | Ship inventory and triage first; they need the least new engineering and sell alone.                                                        |
| Codebase currently overstates readiness                              | Must fix  | Slice S0 removes mocks and hardcoded scores before any external demo.                                                                       |
| Our own product accessibility                                        | Must have | WCAG 2.2 AA audit of dashboard, marketing site and evidence pack PDFs before launch; ACR published.                                         |
| Key-person dependency                                                | Medium    | Documented architecture (ADRs, specs), two engineers on the pipeline by Q1 2027.                                                            |

---

## 13. Milestones and KPIs

| Milestone                                               | Date     | Evidence                                                          |
| ------------------------------------------------------- | -------- | ----------------------------------------------------------------- |
| Truthful demo (no mocks) and marketing site live on AWS | Oct 2026 | S0 done; site at makepdfaccessible.com with free inventory report |
| First five paid pilots signed                           | Dec 2026 | Signed SOWs                                                       |
| Real remediation with evidence packs in production      | Dec 2026 | veraPDF pass rate ≥ 95% on the eval set; evidence pack v1         |
| WordPress publish-back and Drupal beta                  | Jan 2027 | Two customers publishing HTML back into their CMS                 |
| Verified tier live                                      | Feb 2027 | Reviewer pool, turnaround ≤ 5 business days                       |
| SSO, billing, SOC 2 Type I controls, ACR, HECVAT        | Mar 2027 | Documents delivered to two procurement offices                    |
| 45 paying institutions                                  | Sep 2027 | ARR ≥ $0.8M                                                       |
| LTI tool and STEM support                               | Jun 2027 | Canvas and Blackboard certified                                   |
| SOC 2 Type II report                                    | Mar 2028 | Auditor's report                                                  |
| 175 paying institutions                                 | Sep 2028 | ARR ≥ $4.2M                                                       |

**Operating KPIs:** pages processed per month; automated veraPDF pass rate; semantic QA pass rate; share of pages needing human review; cost per page by stage; time from upload to evidence pack (target p95 under 10 minutes for a 50-page document); on-demand Accessible Link cache hit rate; inventory coverage (documents found vs. documents the customer knows about); pilot conversion; NRR; support tickets per 100 customers; ACR defects open.

---

## 14. Use of funds ($3.0M seed, estimate)

| Use                                                          | Amount | Share |
| ------------------------------------------------------------ | ------ | ----- |
| Engineering and product (5 FTE over 18 months)               | $1.5M  | 50%   |
| Go-to-market (2 FTE, events, content, cooperative contracts) | $0.7M  | 23%   |
| Verified tier operations and QA                              | $0.3M  | 10%   |
| Compliance (SOC 2, pen tests, ACR, legal)                    | $0.2M  | 7%    |
| AWS and engine licenses                                      | $0.2M  | 7%    |
| Reserve                                                      | $0.1M  | 3%    |

---

## 15. Appendix: sources and assumptions

- Regulatory dates, backlog figures, competitor prices and the code audit are documented with links in `docs/research/higher-ed-market-research-2026-09.md`.
- ITHAKA's architecture and results are documented in `docs/research/ithaka-pipeline-analysis.md`.
- Institution counts: roughly 3,900 degree-granting institutions (about 1,600 public), about 13,000 school districts and about 90,000 local government units are round numbers from public statistics and should be confirmed against IPEDS and the Census of Governments before external use.
- All revenue, cost, margin and headcount figures in sections 6, 11 and 14 are internal estimates for planning, not forecasts of record.
