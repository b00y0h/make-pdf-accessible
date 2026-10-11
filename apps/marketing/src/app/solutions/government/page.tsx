import type { Metadata } from 'next';
import Link from 'next/link';
import { DeadlineTimeline } from '@/components/DeadlineTimeline';
import { ProcurementTable } from '@/components/ProcurementTable';
import { Section } from '@/components/Section';
import { SolutionPage } from '@/components/SolutionPage';
import { DEADLINES, PLANS } from '@/content/site';
import { formatLongDate } from '@/lib/dates';

export const metadata: Metadata = {
  title: 'State and local government',
  description:
    'Make agendas, minutes, ordinances, permits and forms accessible before your ADA Title II compliance date, then handle every new upload as it is posted, with a record of each decision.',
};

const team = PLANS.find((plan) => plan.id === 'team');

export default function GovernmentPage() {
  return (
    <SolutionPage
      title="Agendas, minutes and permits, accessible before your compliance date and after it."
      lede="Cities, counties, special districts and public school districts publish documents every week. Clear the backlog you have, then handle each new upload as it is posted, with a record of every decision."
      challenges={[
        {
          title: 'Documents never stop arriving',
          text: 'Council packets, minutes, ordinances, permits, bids and board policies go up every week. After your date, each new one has to meet the standard too.',
        },
        {
          title: 'Small teams, large archives',
          text: 'Most web teams are one or two people with years of PDFs behind them and no time to open each one.',
        },
        {
          title: 'Not every document needs fixing',
          text: 'Some archived or unused older documents may qualify for an exception, but only if the decision is made and recorded document by document.',
        },
        {
          title: 'Buying takes time',
          text: 'A separate procurement can take longer than the time left before your date.',
        },
      ]}
      outcomes={[
        {
          title: 'Find everything you publish',
          text: 'We crawl your public site and read the CMS media library, then list every PDF with its pages and links and, with analytics or log imports, which ones anyone opens.',
        },
        {
          title: 'Decide, then fix what matters',
          text: 'Triage applies your policy to each document and records the rule behind each decision, including archive and delete decisions, which cost nothing.',
        },
        {
          title: 'New uploads handled as they are posted',
          text: 'Upload hooks process new documents automatically, and scheduled re-crawls report drift before anyone complains.',
        },
        {
          title: 'Publish without breaking links',
          text: 'Fixed documents replace the originals in WordPress or Drupal with redirects handled, or are served from an Accessible Link for any URL.',
        },
      ]}
      start={{
        title: 'Where public agencies start',
        text: (
          <>
            With the free website report. The Team plan ({team?.price}{' '}
            {team?.cadence}) fits a department, a small district or a small
            town. Larger jurisdictions use Campus, and states and large
            districts use System, which includes cooperative-contract pricing.{' '}
            <Link href="/pricing/" className="text-link">
              See all prices
            </Link>
            .
          </>
        ),
      }}
    >
      <Section
        id="dates"
        title="Your compliance date"
        lede={`The ADA Title II rule gives entities serving 50,000 people or more until ${formatLongDate(DEADLINES.titleIILarge.date)}, and smaller entities and special districts until ${formatLongDate(DEADLINES.titleIISmall.date)}. Confirm which applies to you with counsel.`}
        layout="split"
      >
        <DeadlineTimeline />
      </Section>

      <Section
        id="procurement"
        title="Buying without a separate procurement"
        lede="We are pursuing cooperative-contract listings that let public entities buy without running their own procurement; ask us which apply to your state. Every price is published, so there is nothing to negotiate below the System tier."
        tone="surface"
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
    </SolutionPage>
  );
}
