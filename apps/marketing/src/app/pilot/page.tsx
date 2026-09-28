import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Request a pilot',
  description:
    'A 30-day pilot on one domain: inventory, triage plan, up to 2,000 pages remediated or converted, evidence packs.',
};

export default function PilotPage() {
  const subject = encodeURIComponent('Pilot request');
  const body = encodeURIComponent(
    'Institution:\nWebsite:\nRole:\nWhat we want to learn in 30 days:\nRough number of PDFs (if known):\n'
  );
  return (
    <Container className="py-14">
      <h1 className="text-4xl font-bold tracking-tight">Request a pilot</h1>
      <p className="mt-4 max-w-prose text-lg text-muted">
        Thirty days, one domain, agreed success criteria. The fee ($5,000 to
        $15,000 depending on size) is credited to a plan signed within 90 days.
      </p>
      <h2 className="mt-8 text-xl font-bold">What happens</h2>
      <ol className="mt-2 max-w-prose list-decimal space-y-2 pl-5">
        <li>
          Week 1: crawl and connector setup, inventory review, triage plan with
          counts and costs.
        </li>
        <li>
          Weeks 2 to 3: up to 2,000 pages remediated or converted; publish-back
          on a staging site if you prefer.
        </li>
        <li>
          Week 4: evidence packs, a screen-reader walkthrough with your
          accessibility lead, and a written summary you can share with counsel.
        </li>
      </ol>
      <h2 className="mt-8 text-xl font-bold">Start the conversation</h2>
      <p className="mt-2 max-w-prose">
        Email{' '}
        <a
          href={`mailto:${SITE.contactEmail}?subject=${subject}&body=${body}`}
          className="font-semibold underline underline-offset-4"
        >
          {SITE.contactEmail}
        </a>{' '}
        with your institution, website and what you want to learn. We reply
        within one business day. A web form with scheduling arrives with the
        next release of this site.
      </p>
    </Container>
  );
}
