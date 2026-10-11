import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { PageHeader } from '@/components/PageHeader';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Request a pilot',
  description:
    'A 30-day pilot on one domain: inventory, triage plan, up to 2,000 pages remediated or converted, evidence packs.',
};

const WEEKS = [
  {
    when: 'Week 1',
    text: 'Crawl and connector setup, inventory review, triage plan with counts and costs.',
  },
  {
    when: 'Weeks 2 and 3',
    text: 'Up to 2,000 pages remediated or converted; publish-back on a staging site if you prefer.',
  },
  {
    when: 'Week 4',
    text: 'Evidence packs, a screen-reader walkthrough with your accessibility lead, and a written summary you can share with counsel.',
  },
];

export default function PilotPage() {
  const subject = encodeURIComponent('Pilot request');
  const body = encodeURIComponent(
    'Institution:\nWebsite:\nRole:\nWhat we want to learn in 30 days:\nRough number of PDFs (if known):\n'
  );
  return (
    <>
      <PageHeader
        title="Request a pilot"
        lede="Thirty days, one domain, agreed success criteria. The fee ($5,000 to $15,000 depending on size) is credited to a plan signed within 90 days."
      />
      <Container className="grid gap-16 py-16 lg:grid-cols-12 lg:gap-12 lg:py-24">
        <section aria-labelledby="weeks-title" className="lg:col-span-7">
          <h2
            id="weeks-title"
            className="text-[1.875rem] leading-tight sm:text-title"
          >
            What happens
          </h2>
          <ol className="mt-8 border-t border-ink">
            {WEEKS.map((week) => (
              <li
                key={week.when}
                className="grid gap-1 border-b border-line py-6 sm:grid-cols-[10rem_1fr] sm:gap-8"
              >
                <span className="font-display text-[1.3125rem] font-medium">
                  {week.when}
                </span>
                <span className="text-muted">{week.text}</span>
              </li>
            ))}
          </ol>
        </section>
        <section
          aria-labelledby="contact-title"
          className="self-start border-t-4 border-accent bg-tint p-6 sm:p-8 lg:col-span-5"
        >
          <h2 id="contact-title" className="text-[1.75rem] leading-tight">
            Start the conversation
          </h2>
          <p className="mt-4">
            Email{' '}
            <a
              href={`mailto:${SITE.contactEmail}?subject=${subject}&body=${body}`}
              className="text-link font-semibold"
            >
              {SITE.contactEmail}
            </a>{' '}
            with your institution, website and what you want to learn. We reply
            within one business day.
          </p>
          <p className="mt-4 text-[0.9375rem] text-muted">
            A web form with scheduling arrives with the next release of this
            site.
          </p>
        </section>
      </Container>
    </>
  );
}
