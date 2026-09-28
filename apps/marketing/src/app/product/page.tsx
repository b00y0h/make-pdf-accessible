import type { Metadata } from 'next';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
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

export default function ProductPage() {
  return (
    <>
      <Container className="py-14">
        <h1 className="text-4xl font-bold tracking-tight">How it works</h1>
        <p className="mt-4 max-w-copy text-lg text-muted">
          Six stages, one system of record. Each stage is useful on its own;
          together they take an institution from an unknown backlog to a
          defensible position and keep it there.
        </p>
      </Container>

      {STAGES.map((stage, index) => (
        <Section
          key={stage.name}
          id={`stage-${index + 1}`}
          title={`${index + 1}. ${stage.name}`}
          tone={index % 2 ? 'surface' : 'default'}
        >
          <p className="max-w-copy text-lg">{stage.text}</p>
          <p className="mt-6 max-w-copy text-muted">{DETAILS[index]}</p>
        </Section>
      ))}

      <Section
        id="link"
        title="The Accessible Link"
        lede="Remediate on first request, cache for everyone after."
      >
        <p className="max-w-copy">
          Any inventoried PDF gets a stable link. The first visitor who opens it
          triggers remediation and sees an accessible waiting page; every later
          visitor gets the cached, validated version immediately. Large
          libraries have run this model at scale for a fraction of the cost of
          fixing everything upfront, and it is how new documents stay covered
          after the deadline.
        </p>
      </Section>

      <Section id="integrations" title="Where it plugs in" tone="surface">
        <ul className="grid gap-4 md:grid-cols-2">
          <li className="rounded-lg border border-line bg-bg p-5">
            <h3 className="text-xl font-bold">WordPress and Drupal</h3>
            <p className="mt-2 text-muted">
              Inventory sync from the media library, one-click remediation,
              publish-back as a page or replacement file, redirects handled.
            </p>
          </li>
          <li className="rounded-lg border border-line bg-bg p-5">
            <h3 className="text-xl font-bold">
              Canvas, Blackboard, D2L, Moodle
            </h3>
            <p className="mt-2 text-muted">
              An LTI 1.3 tool that lists a course&apos;s files, remediates on
              request and links the accessible version back into the course.
            </p>
          </li>
          <li className="rounded-lg border border-line bg-bg p-5">
            <h3 className="text-xl font-bold">Scanners</h3>
            <p className="mt-2 text-muted">
              Import Siteimprove, DubBot and Pope Tech exports as inventory so
              the tools you already own feed the fix.
            </p>
          </li>
          <li className="rounded-lg border border-line bg-bg p-5">
            <h3 className="text-xl font-bold">API and webhooks</h3>
            <p className="mt-2 text-muted">
              Versioned REST API with scoped keys, signed webhooks and an
              OpenAPI description for anything custom.
            </p>
          </li>
        </ul>
        <div className="mt-8">
          <ButtonLink href="/pilot/">Request a pilot</ButtonLink>
        </div>
      </Section>
    </>
  );
}
