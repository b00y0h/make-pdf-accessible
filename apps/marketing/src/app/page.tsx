import Link from 'next/link';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
import { DeadlineTimeline } from '@/components/DeadlineTimeline';
import { EvidenceRecord } from '@/components/EvidenceRecord';
import { ProcurementTable } from '@/components/ProcurementTable';
import { Section } from '@/components/Section';
import { SiteReportForm } from '@/components/SiteReportForm';
import { PLANS, SITE, SOLUTIONS, STAGES } from '@/content/site';

const AUDIENCES = [
  {
    ...SOLUTIONS[0],
    body: 'Hundreds of department sites, library collections, and every course in Canvas, Blackboard, D2L or Moodle. One inventory across all of it, a plan the CIO can fund, and evidence the general counsel can read.',
    roles: 'CIOs, digital accessibility officers, web services, libraries',
  },
  {
    ...SOLUTIONS[1],
    body: 'Agendas, minutes, ordinances, permits and forms, posted every week. Clear the backlog before your compliance date, then handle every new upload as it is posted.',
    roles: 'IT directors, ADA coordinators, clerks, school district web teams',
  },
  {
    ...SOLUTIONS[2],
    body: 'Every triage decision cites the rule behind it, every override keeps its note, and every document has a signed evidence pack that can be verified without us.',
    roles:
      'General counsel, outside counsel to public entities, firms publishing their own documents',
  },
];

const OUTPUTS = [
  {
    title: 'An accessible PDF or HTML page',
    text: 'Tagged PDF validated against PDF/UA with veraPDF, or semantic HTML validated with axe-core, chosen per document by a policy you control.',
  },
  {
    title: 'Published where people find it',
    text: 'Written back into WordPress, Drupal or the LMS with redirects and the original kept as a download, or served from an Accessible Link for any URL.',
  },
  {
    title: 'An evidence pack',
    text: 'Validator reports, per-element semantic checks with confidence, reviewer sign-off, tool and model versions, and timestamps, signed and retained for your records.',
  },
];

const NOT_CLAIMED = [
  'We validate every output with independent tools and publish our measured accuracy by document type. Where automation is weak (scans, complex tables, charts, math), we route elements to human review and say so in the evidence.',
  'We use licensed tagging engines and Amazon Bedrock models and record which ones produced each result. Engines are replaceable; the evidence format is not.',
  'Counsel decides what the rule requires of your institution. We give you the inventory, the decision record and the proof to have that conversation with.',
];

const PILOT_WEEKS = [
  {
    when: 'Week 1',
    text: 'Crawl and connector setup, inventory review, and a triage plan with counts and costs.',
  },
  {
    when: 'Weeks 2 and 3',
    text: 'Up to 2,000 pages remediated or converted, published to a staging site if you prefer.',
  },
  {
    when: 'Week 4',
    text: 'Evidence packs, a screen-reader walkthrough with your team, and a written summary for counsel.',
  },
];

function pagesLabel(pages: number | null): string {
  if (pages === null) return 'Negotiated';
  if (pages === 0) return 'Inventory and checks';
  return `${pages.toLocaleString('en-US')}${pages >= 250000 ? '+' : ''} pages`;
}

export default function HomePage() {
  return (
    <>
      <section aria-labelledby="hero-title" className="overflow-hidden">
        <Container className="pb-24 pt-14 sm:pt-20 lg:pb-32 lg:pt-24">
          <h1
            id="hero-title"
            className="max-w-[17ch] text-[2.75rem] leading-[1.04] sm:text-[3.75rem] lg:max-w-none xl:text-hero"
          >
            {SITE.tagline}
          </h1>
          <div className="mt-10 grid gap-20 lg:mt-14 lg:grid-cols-12 lg:gap-10">
            <div className="lg:col-span-5">
              <p className="max-w-copy text-lede text-muted">
                Colleges, universities and public agencies face a fixed deadline
                and a backlog of PDFs nobody has counted. {SITE.name} finds
                every document, decides what the rule requires for each one,
                fixes or converts it, publishes it back, and keeps a signed
                record your counsel can review.
              </p>
              <div className="mt-10 flex flex-wrap gap-3">
                <ButtonLink href="/free-report/">
                  Get a free inventory of your site
                </ButtonLink>
                <ButtonLink href="/product/" variant="secondary">
                  See how it works
                </ButtonLink>
              </div>
              <p className="mt-5 text-[0.9375rem] text-muted">
                Free, no credit card. Our crawler identifies itself and follows
                your robots.txt.
              </p>
            </div>
            <div className="sm:px-6 lg:col-span-7 lg:pl-12 lg:pr-0">
              <EvidenceRecord />
            </div>
          </div>
        </Container>
      </section>

      <Section
        id="deadlines"
        title="The dates are fixed"
        lede="The ADA Title II rule sets WCAG 2.1 AA as the standard for the web content and documents public entities provide. After each date, every document posted has to meet it, not only the backlog."
        tone="surface"
        layout="split"
      >
        <DeadlineTimeline />
      </Section>

      <Section
        id="audiences"
        title="Built for the offices that answer for every document"
        lede="The web team publishes, the accessibility office sets policy, counsel signs off. Each gets what it needs from one record."
      >
        <ul className="grid border-t border-ink lg:grid-cols-3">
          {AUDIENCES.map((audience, index) => (
            <li
              key={audience.href}
              className={`flex flex-col border-b border-line py-8 lg:border-b-0 lg:py-10 ${index > 0 ? 'lg:border-l lg:pl-10' : ''} ${index < 2 ? 'lg:pr-10' : ''}`}
            >
              <h3 className="font-display text-[1.5rem] font-medium leading-tight">
                {audience.label}
              </h3>
              <p className="mt-4 flex-1">{audience.body}</p>
              <p className="mt-6 text-[0.9375rem] text-muted">
                {audience.roles}
              </p>
              <p className="mt-6">
                <Link href={audience.href} className="text-link font-semibold">
                  {SITE.name} for {audience.short.toLowerCase()}
                </Link>
              </p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="loop"
        title="The whole job, not just tagging"
        lede="Automated tagging is a commodity. The work institutions cannot buy anywhere else is the loop around it."
        tone="surface"
        layout="split"
      >
        <ol className="grid gap-x-12 sm:grid-cols-2">
          {STAGES.map((stage, index) => (
            <li
              key={stage.name}
              className="grid grid-cols-[2.75rem_1fr] gap-x-3 border-t border-line py-7"
            >
              <span
                aria-hidden="true"
                className="font-display text-[2.25rem] font-medium leading-none text-accent tabular-nums"
              >
                {index + 1}
              </span>
              <div>
                <h3 className="text-[1.3125rem] font-semibold leading-snug">
                  <span className="sr-only-focusable">Stage {index + 1}: </span>
                  {stage.name}
                </h3>
                <p className="mt-2 text-muted">{stage.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-8">
          <Link href="/product/" className="text-link font-semibold">
            See how each stage works
          </Link>
        </p>
      </Section>

      <Section
        id="outputs"
        title="What you get for each document"
        lede="Three things, every time: an accessible output, a place it lives, and proof."
        layout="split"
      >
        <dl className="divide-y divide-line border-y border-line">
          {OUTPUTS.map((output) => (
            <div
              key={output.title}
              className="grid gap-2 py-7 md:grid-cols-[16rem_1fr] md:gap-10"
            >
              <dt className="font-display text-[1.3125rem] font-medium leading-snug">
                {output.title}
              </dt>
              <dd className="text-muted">{output.text}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <section
        id="honest"
        aria-labelledby="honest-title"
        className="bg-surface"
      >
        <Container className="py-16 lg:py-24">
          <h2
            id="honest-title"
            className="max-w-4xl text-[1.875rem] font-normal leading-[1.22] sm:text-[2.625rem]"
          >
            No software makes a document accessible on its own, and we will not
            tell you otherwise.
          </h2>
          <ul className="mt-14 grid gap-10 md:grid-cols-3">
            {NOT_CLAIMED.map((text) => (
              <li key={text} className="border-t-2 border-accent pt-5">
                {text}
              </li>
            ))}
          </ul>
        </Container>
      </section>

      <Section
        id="procurement"
        title="Ready for your procurement office"
        lede="What security and accessibility reviewers ask for, with its status today. We say what is not done yet."
        layout="split"
      >
        <ProcurementTable />
        <p className="mt-8 flex flex-wrap gap-x-8 gap-y-3">
          <Link href="/trust/" className="text-link font-semibold">
            Visit the trust center
          </Link>
          <Link href="/security/" className="text-link font-semibold">
            Read the security overview
          </Link>
        </p>
      </Section>

      <Section
        id="pricing-teaser"
        title="Published prices"
        lede="Per page, on the website, on the invoice."
        tone="surface"
        layout="split"
      >
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only-focusable">
              Plans and annual prices
            </caption>
            <thead>
              <tr className="border-b border-ink text-[0.9375rem]">
                <th scope="col" className="py-3 pr-6 font-semibold">
                  Plan
                </th>
                <th scope="col" className="py-3 pr-6 font-semibold">
                  Price
                </th>
                <th scope="col" className="py-3 pr-6 font-semibold">
                  Included
                </th>
                <th
                  scope="col"
                  className="hidden py-3 font-semibold sm:table-cell"
                >
                  For
                </th>
              </tr>
            </thead>
            <tbody>
              {PLANS.map((plan) => (
                <tr key={plan.id} className="border-b border-line align-top">
                  <th
                    scope="row"
                    className="py-4 pr-6 font-display text-[1.3125rem] font-medium"
                  >
                    {plan.name}
                  </th>
                  <td className="py-4 pr-6">
                    <span className="whitespace-nowrap font-semibold tabular-nums">
                      {plan.price}
                    </span>
                    {plan.cadence ? (
                      <span className="block text-[0.9375rem] text-muted">
                        {plan.cadence}
                      </span>
                    ) : null}
                  </td>
                  <td className="py-4 pr-6 tabular-nums">
                    {pagesLabel(plan.pagesIncluded)}
                  </td>
                  <td className="hidden py-4 text-muted sm:table-cell">
                    {plan.summary}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-8">
          <Link href="/pricing/" className="text-link font-semibold">
            See the full price list and the page calculator
          </Link>
        </p>
      </Section>

      <section id="start" aria-labelledby="start-title">
        <Container className="py-16 lg:py-24">
          <h2
            id="start-title"
            className="text-[1.875rem] leading-tight sm:text-title"
          >
            Two ways to start
          </h2>
          <div className="mt-12 grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="rounded-sm border border-line p-6 sm:p-8">
              <h3 className="font-display text-[1.5rem] font-medium leading-tight">
                Free website report
              </h3>
              <div className="mt-5">
                <SiteReportForm />
              </div>
            </div>
            <div>
              <h3 className="font-display text-[1.5rem] font-medium leading-tight">
                A 30-day pilot
              </h3>
              <p className="mt-4 max-w-copy text-muted">
                One domain, agreed success criteria, and a fee credited to a
                plan signed within 90 days.
              </p>
              <ol className="mt-8 border-t border-line">
                {PILOT_WEEKS.map((week) => (
                  <li
                    key={week.when}
                    className="grid gap-1 border-b border-line py-5 sm:grid-cols-[9rem_1fr] sm:gap-6"
                  >
                    <span className="font-semibold">{week.when}</span>
                    <span className="text-muted">{week.text}</span>
                  </li>
                ))}
              </ol>
              <ButtonLink href="/pilot/" className="mt-8">
                Request a pilot
              </ButtonLink>
            </div>
          </div>
        </Container>
      </section>
    </>
  );
}
