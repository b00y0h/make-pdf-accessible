# PDFix SDK licensing for a multi-tenant SaaS

Research for ADR-0003, compiled 10 October 2026 from public sources. Nobody at PDFix has been contacted yet. This is not legal advice.

## What is public

- **Product to license: PDFix SDK Enterprise, built into our own container image.** The SDK comes in Lite (free), Basic, Professional and Enterprise. Only Enterprise includes auto-tagging, PDF/UA conversion and accessibility fixes. PDFix also publishes `pdfix/*` action images on Docker Hub (Docling, Paddle and Textract auto-tagging, veraPDF, OCR) [6], and separate Desktop and Services products. There is no AWS Marketplace listing and no hosted API.
- **Pricing is quote-only today.** The live pricing page says pricing depends on "instance count" without defining an instance [1].
  - An archived Enterprise page from 14 March 2026 [2] (now a 404, and labeled "informative only") listed volume plans of 2k, 5k, 10k and 30k pages a month at $149, $209, $245 and $410. That is $0.079, $0.044, $0.026 and $0.014 per page.
  - The same page listed a Flat License at $9,080 a year for unlimited pages on one server with at most 4 processes. More servers or nodes needed a custom quote.
  - An October 2025 snapshot showed paid tiers from €1,320 a year [3].
- **Cost risk.** At 2k to 5k pages a month, those rates come close to or exceed our whole $0.055 per-page target. ITHAKA's reported $0.026 per page may not include the license [14][15].
- **Licensing mechanics** (licensing guide, January 2025 [4]):
  - Pages count when layout recognition runs and the file is saved.
  - At the monthly limit the SDK returns error 428, and overage is by request only.
  - Standard activation writes a local license file, so every ephemeral Fargate task could count as a new device; the guide's sample shows `max_activations: 5`. PDFix's own images pass an account key per run instead [5][6].
- **License terms (Rev 08-2023)** [7]:
  - The Deployment License covers "servers, hosted services, and the cloud".
  - §4(d) limits third-party use to "End users".
  - §4(e) bans "competitive" works, and PDFix sells remediation services itself [8].
  - §4(f) needs PDFix's consent for custom development done for a third party.
  - The licensee must act as a reference site.
  - Liability is capped at fees paid.
- **Platforms:** Linux x86_64 and aarch64 (Graviton works), one process per parallel worker [9][10].
- **Evaluation:** trial output is watermarked and partly redacted, so it can't produce valid veraPDF benchmarks [9][10]. The SDK bundles veraPDF [11]; we run veraPDF separately so validation stays independent.
- **Discounts:** no startup program found. Nonprofit and university pricing is for "internal, non-commercial purposes" only [12]. The free proof of concept is for government agencies [13].

**veraPDF** is licensed GPLv3+ or MPLv2+ at the user's choice; veraPDF-rest is MIT [16]. Running it unmodified in our own containers isn't distribution. If we ever ship images to customers or modify its files, use the MPL.

**Adobe PDF Services (fallback):** Auto-Tag uses 10 document transactions per page. The free tier is 500 transactions a month (50 pages), with a 200-page cap per document (150 if scanned) [17]. Paid pricing is by quote [18], so ADR-0003's figure of about $0.50 per page is unconfirmed. The ASU pipeline needed an enterprise contract or trial [19].

## What to ask for

SDK Enterprise under a Deployment License, with a written addendum permitting multi-tenant SaaS use. Fargate has no "server", so ask for one of two structures: a multi-node flat license capped by concurrent processes, or a custom volume tier.

## Questions for PDFix

1. Which license fits ephemeral, autoscaled Fargate tasks, and what counts as an "instance"?
2. Is a multi-node flat license capped by concurrent processes available?
3. Prices at 30k, 100k, 300k and 1M pages a month. Do the March 2026 prices still apply?
4. Can metered overage replace the error-428 hard stop? Can pages pool across a year?
5. When we split a document into pages and merge them back, is each page counted once? Do retries and evaluation runs count?
6. Which activation method should ephemeral containers use? What are the activation limits, and must tasks deactivate on shutdown?
7. Is there a grace period if the license server is unreachable?
8. Will you confirm in writing that our institutions are "End users" under §4(d), and that §4(e) and §4(f) don't apply?
9. Can the reference-site clause be waived?
10. A watermark-free evaluation license for 60 to 90 days.
11. Startup or ramp pricing, a 12 to 24 month price lock, or monthly billing.
12. Which entity is the licensor (PDFix-US LLC or PDFix s.r.o.), and under which law?
13. What does the license check transmit? Confirm that no document content leaves our environment (FERPA).
14. Are the Docling and Paddle models included, and can they run offline?
15. What is the support SLA, and do you indemnify against IP claims?

## How to reach PDFix

- **PDFix-US LLC** (Frederick, Maryland) is the exclusive US distributor: sales@pdfix-us.com, +1 866-883-8750. Ask for David Herr (President) or Andrea Combs (Strategic Enterprise Account Executive).
- **PDFix s.r.o.** is the headquarters (Stupava, Slovakia; founded 2016). Its support@pdfix.net address is the one the licensing guide gives for custom licensing.
- The web quote form has no fields for deployment model or volume [20], so email is better.

### Draft email

**To:** sales@pdfix-us.com (Attn: Andrea Combs, David Herr). **Cc:** support@pdfix.net
**Subject:** SaaS licensing and evaluation: PDFix SDK Enterprise

> Hello Andrea and David,
>
> I'm the founder of Make PDF Accessible, a two-person startup building a document accessibility platform for colleges and universities. ITHAKA's AWS pipeline led us to choose PDFix SDK Enterprise as our primary tagging engine.
>
> The SDK would run in our own containers on AWS Fargate. Step Functions fans each document out to page-level tasks that scale with demand, and veraPDF validates the output. Many institutions share the service, and documents never leave our AWS account. We expect tens of thousands of pages a month in 2027, growing toward a million.
>
> Since your Flat License is priced per server, could you propose terms that fit Fargate? Either a multi-node license capped by concurrency or a custom volume tier would work. We'd also need a written addendum permitting multi-tenant hosted use.
>
> Could you also provide a 60-day watermark-free evaluation license, so we can benchmark before our December build? I've attached a few licensing questions, mostly about activation in short-lived containers, and would welcome a 30-minute call.
>
> Thank you,
> Bob Smith
> Founder, Make PDF Accessible

## Sources

Undated unless a date is shown.

1. https://pdfix.net/pricing/sdk/ (checked 2026-10-10)
2. https://web.archive.org/web/20260314085016/https://pdfix.net/pricing/sdk-enterprise/ (2026-03-14)
3. https://web.archive.org/web/20251012054646/https://pdfix.net/pricing/sdk/ (2025-10-12)
4. https://github.com/pdfix/pdfix_sdk_builds/blob/main/volume-licensing.md (2025-01-24)
5. https://github.com/pdfix/pdfix_sdk_example_python/blob/master/src/License.py
6. https://hub.docker.com/r/pdfix/pdf-accessibility-docling (about 2026-08)
7. https://pdfix.net/terms/ (Rev 08-2023)
8. https://pdfix.net/pricing/services/
9. https://pdfix.net/download/
10. https://github.com/pdfix/pdfix_sdk_builds
11. https://pdfix.net/products/pdfix-sdk/
12. https://pdfix.net/pricing/buy-now/
13. https://www.webull.com/news/15344695172539392 (2026-08-04)
14. https://aws.amazon.com/blogs/publicsector/how-ithaka-built-an-on-demand-pdf-remediation-pipeline-on-aws/ (2026-08-27)
15. https://www.prnewswire.com/news-releases/aws-public-sector-blog-highlights-pdfixs-role-in-ithakas-on-demand-pdf-accessibility-pipeline-302865907.html (2026-09-01)
16. https://verapdf.org/home/ and https://github.com/veraPDF/veraPDF-rest
17. https://developer.adobe.com/document-services/docs/overview/limits/
18. https://developer.adobe.com/document-services/pricing/main/
19. https://github.com/ASUCICREPO/PDF_Accessibility
20. https://pdfix.net/about-us/contact-us/ and https://pdfix.net/request-a-quote/
