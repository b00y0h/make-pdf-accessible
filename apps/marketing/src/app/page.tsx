import Link from 'next/link';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
import { Countdown } from '@/components/Countdown';
import { Section } from '@/components/Section';
import { SiteReportForm } from '@/components/SiteReportForm';
import { PLANS, SITE, STAGES } from '@/content/site';

export default function HomePage() {
  return (
    <>
      <section aria-labelledby="hero-title">
        <Container className="grid gap-10 py-16 lg:grid-cols-2 lg:items-start">
          <div>
            <h1
              id="hero-title"
              className="text-4xl font-bold tracking-tight sm:text-5xl"
            >
              {SITE.tagline}
            </h1>
            <p className="mt-5 max-w-copy text-lg text-muted">
              Public universities, colleges, school districts and local
              governments have a fixed deadline and a backlog of PDFs nobody has
              counted. {SITE.name} finds every document, decides what the rule
              requires for each one, fixes or converts it, publishes it back,
              and keeps a signed evidence pack per document.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/free-report/">
                Get a free inventory of your site
              </ButtonLink>
              <ButtonLink href="/product/" variant="secondary">
                See how it works
              </ButtonLink>
            </div>
            <div className="mt-10">
              <Countdown />
            </div>
          </div>
          <div className="rounded-lg border border-line p-6">
            <h2 className="text-2xl font-bold">
              Start with the free website report
            </h2>
            <div className="mt-4">
              <SiteReportForm />
            </div>
          </div>
        </Container>
      </section>

      <Section
        id="loop"
        title="The whole job, not just tagging"
        lede="Automated tagging is a commodity. The work institutions cannot buy anywhere is the loop around it."
        tone="surface"
      >
        <ol className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {STAGES.map((stage, index) => (
            <li
              key={stage.name}
              className="rounded-lg border border-line bg-bg p-5"
            >
              <p className="text-sm font-semibold uppercase tracking-wide text-muted">
                Stage {index + 1}
              </p>
              <h3 className="mt-1 text-xl font-bold">{stage.name}</h3>
              <p className="mt-2 text-muted">{stage.text}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section
        id="outputs"
        title="What you get for each document"
        lede="Three things, every time: an accessible output, a place it lives, and proof."
      >
        <div className="grid gap-6 md:grid-cols-3">
          <div>
            <h3 className="text-xl font-bold">Accessible PDF or HTML</h3>
            <p className="mt-2 text-muted">
              Tagged PDF validated against PDF/UA with veraPDF, or semantic HTML
              validated with axe-core, chosen per document by policy you
              control.
            </p>
          </div>
          <div>
            <h3 className="text-xl font-bold">
              Published where people find it
            </h3>
            <p className="mt-2 text-muted">
              Written back into WordPress, Drupal or the LMS with redirects and
              the original kept as a download, or served from an Accessible Link
              for any URL.
            </p>
          </div>
          <div>
            <h3 className="text-xl font-bold">An evidence pack</h3>
            <p className="mt-2 text-muted">
              Validator reports, per-element semantic checks with confidence,
              reviewer sign-off, tool and model versions, and timestamps, signed
              and retained for your records.
            </p>
          </div>
        </div>
      </Section>

      <Section
        id="honest"
        title="What we do not claim"
        lede="No software makes a document accessible on its own, and we will not tell you otherwise."
        tone="surface"
      >
        <ul className="max-w-copy list-disc space-y-2 pl-5">
          <li>
            We validate every output with independent tools and publish our
            measured accuracy by document type. Where automation is weak (scans,
            complex tables, charts, math), we route elements to human review and
            say so in the evidence.
          </li>
          <li>
            We use licensed tagging engines and Amazon Bedrock models and record
            which ones produced each result. Engines are replaceable; the
            evidence format is not.
          </li>
          <li>
            Counsel decides what the rule requires of your institution. We give
            you the inventory, the decision record and the proof to have that
            conversation with.
          </li>
        </ul>
      </Section>

      <Section
        id="pricing-teaser"
        title="Published prices"
        lede="Per page, on the website, on the invoice."
      >
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <div key={plan.id} className="rounded-lg border border-line p-5">
              <h3 className="text-xl font-bold">{plan.name}</h3>
              <p className="mt-1 text-2xl font-bold">
                {plan.price}{' '}
                <span className="text-base font-normal text-muted">
                  {plan.cadence}
                </span>
              </p>
              <p className="mt-2 text-muted">{plan.summary}</p>
            </div>
          ))}
        </div>
        <p className="mt-6">
          <Link
            href="/pricing/"
            className="font-semibold underline underline-offset-4"
          >
            See the full price list and the page calculator
          </Link>
        </p>
      </Section>

      <Section
        id="pilot"
        title="Run a 30-day pilot"
        lede="One domain, a triaged inventory, up to 2,000 pages remediated or converted, evidence packs, and a screen-reader walkthrough with your team."
        tone="surface"
      >
        <ButtonLink href="/pilot/">Request a pilot</ButtonLink>
      </Section>
    </>
  );
}
