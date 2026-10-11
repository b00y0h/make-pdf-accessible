import type { Metadata } from 'next';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
import { PageHeader } from '@/components/PageHeader';
import { Section } from '@/components/Section';
import { STAGES } from '@/content/site';

export const metadata: Metadata = {
  title: 'Product',
  description:
    'Inventory, triage, remediation or HTML conversion, publish-back, evidence packs and maintenance for every document an institution publishes.',
};

const DETAILS = [
  'Sources: a polite crawler that follows your robots.txt, the WordPress plugin, a Drupal module, LMS listings, sitemap-only mode for sites that cannot be crawled, and analytics or log imports so we know which documents anyone actually opens.',
  'The rules are explicit and versioned. Each decision cites the rule that produced it, and staff can override any decision with a note; the history is kept. The plan exports as CSV and as an accessible PDF for the people who approve budgets.',
  'Documents are split into pages and processed in parallel, so a 300-page scan does not hold up a 2-page form and a single bad page never sinks a document. Tagging uses licensed engines; every output is validated by an independent checker and scored element by element, and low-confidence elements go to human review.',
  'Nothing changes for your users until the fixed document replaces the old one. Publishing is a connector action you can review before it goes live, and the original is always kept.',
  'The pack is portable JSON plus the raw validator reports, rendered as an accessible PDF on request, signed so it can be verified without us, and retained for the period you choose.',
  'Upload hooks handle new documents automatically, scheduled re-crawls detect drift, and the dashboard shows coverage over time, so the deadline becomes a milestone rather than a cliff.',
];

const INTEGRATIONS = [
  {
    title: 'WordPress and Drupal',
    text: 'Inventory sync from the media library, one-click remediation, publish-back as a page or replacement file, redirects handled.',
  },
  {
    title: 'Canvas, Blackboard, D2L, Moodle',
    text: 'An LTI 1.3 tool that lists a course’s files, remediates on request and links the accessible version back into the course.',
  },
  {
    title: 'Scanners',
    text: 'Import Siteimprove, DubBot and Pope Tech exports as inventory so the tools you already own feed the fix.',
  },
  {
    title: 'API and webhooks',
    text: 'Versioned REST API with scoped keys, signed webhooks and an OpenAPI description for anything custom.',
  },
];

export default function ProductPage() {
  return (
    <>
      <PageHeader
        title="How it works"
        lede="Six stages, one system of record. Each stage is useful on its own; together they take an institution from an unknown backlog to a defensible position and keep it there."
      />

      <section aria-labelledby="stages-title">
        <Container className="py-16 lg:py-24">
          <h2 id="stages-title" className="sr-only-focusable">
            The six stages
          </h2>
          <ol className="border-t border-ink">
            {STAGES.map((stage, index) => (
              <li
                key={stage.name}
                id={`stage-${index + 1}`}
                className="grid gap-6 border-b border-line py-10 lg:grid-cols-12 lg:gap-12 lg:py-14"
              >
                <div className="flex items-baseline gap-5 lg:col-span-4">
                  <span
                    aria-hidden="true"
                    className="font-display text-[3rem] font-medium leading-none text-accent tabular-nums"
                  >
                    {index + 1}
                  </span>
                  <h3 className="font-display text-[1.75rem] font-medium leading-tight">
                    <span className="sr-only-focusable">
                      Stage {index + 1}:{' '}
                    </span>
                    {stage.name}
                  </h3>
                </div>
                <div className="lg:col-span-8">
                  <p className="max-w-copy text-lg">{stage.text}</p>
                  <p className="mt-4 max-w-copy text-muted">{DETAILS[index]}</p>
                </div>
              </li>
            ))}
          </ol>
        </Container>
      </section>

      <Section
        id="link"
        title="The Accessible Link"
        lede="Remediate on first request, cache for everyone after."
        tone="surface"
        layout="split"
      >
        <p className="max-w-copy text-lg">
          Any inventoried PDF gets a stable link. The first visitor who opens it
          triggers remediation and sees an accessible waiting page; every later
          visitor gets the cached, validated version immediately. Large
          libraries have run this model at scale for a fraction of the cost of
          fixing everything upfront, and it is how new documents stay covered
          after the deadline.
        </p>
      </Section>

      <Section id="integrations" title="Where it plugs in" layout="split">
        <ul className="grid gap-x-12 gap-y-10 sm:grid-cols-2">
          {INTEGRATIONS.map((item) => (
            <li key={item.title} className="border-t-2 border-accent pt-5">
              <h3 className="text-[1.3125rem] font-semibold leading-snug">
                {item.title}
              </h3>
              <p className="mt-2 text-muted">{item.text}</p>
            </li>
          ))}
        </ul>
        <div className="mt-12 flex flex-wrap gap-3">
          <ButtonLink href="/pilot/">Request a pilot</ButtonLink>
          <ButtonLink href="/free-report/" variant="secondary">
            Get a free inventory of your site
          </ButtonLink>
        </div>
      </Section>
    </>
  );
}
