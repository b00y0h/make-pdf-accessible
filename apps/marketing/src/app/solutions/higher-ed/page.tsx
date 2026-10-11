import type { Metadata } from 'next';
import Link from 'next/link';
import { DeadlineTimeline } from '@/components/DeadlineTimeline';
import { ProcurementTable } from '@/components/ProcurementTable';
import { Section } from '@/components/Section';
import { SolutionPage } from '@/components/SolutionPage';
import { CALCULATOR_RATES, PLANS } from '@/content/site';

export const metadata: Metadata = {
  title: 'Colleges and universities',
  description:
    'Inventory every PDF across department sites, library collections and LMS courses, triage it against the rule, fix or convert it, and keep a signed evidence pack for each document.',
};

const campus = PLANS.find((plan) => plan.id === 'campus');

export default function HigherEdPage() {
  return (
    <SolutionPage
      title="Every document across campus, counted, fixed and on the record."
      lede="Department sites, library collections, research PDFs and every course in the LMS. One inventory across all of it, a triage plan the CIO can fund, and a signed evidence pack for each document that your general counsel can review."
      challenges={[
        {
          title: 'Nobody knows the size of the backlog',
          text: 'Documents sit on hundreds of department sites, in CMS media libraries and inside courses. Without a count there is no budget, and without a budget there is no plan.',
        },
        {
          title: 'Course content is the largest pile',
          text: 'Syllabi, readings and slides are uploaded by faculty every term. Fixing them once is not enough, because next term brings more.',
        },
        {
          title: 'Per-page quotes add up fast',
          text: `Universities report paying vendors $${CALCULATOR_RATES.manualLow.toFixed(2)} to $${CALCULATOR_RATES.manualHigh.toFixed(2)} per page for manual remediation. At campus scale that becomes a number no department can absorb.`,
        },
        {
          title: 'Proof is what you will be asked for',
          text: 'If a complaint arrives, the question is what you did about each document and when. A tagging tool’s log does not answer it.',
        },
      ]}
      outcomes={[
        {
          title: 'One inventory for every site and course',
          text: 'A polite crawler for public sites, the WordPress plugin and Drupal module for media libraries, and an LTI 1.3 tool for Canvas, Blackboard, D2L and Moodle. Siteimprove, DubBot and Pope Tech exports import directly.',
        },
        {
          title: 'A plan you can fund',
          text: 'Each document gets a decision (delete, archive, convert to HTML, remediate as PDF, or send to review) with the rule that produced it and a price. Delete and archive decisions cost nothing.',
        },
        {
          title: 'Course files fixed where faculty work',
          text: 'The LTI tool lists a course’s files, remediates on request and links the accessible version back into the course.',
        },
        {
          title: 'Evidence for each document',
          text: 'Validator output, per-element checks, reviewer sign-off and tool versions, signed and retained for the one to seven years you choose.',
        },
      ]}
      start={{
        title: 'Where universities start',
        text: (
          <>
            With the free website report, then a 30-day pilot on one domain. The
            Campus plan ({campus?.price} {campus?.cadence}) covers every domain
            at one institution; the System plan serves multi-campus systems.{' '}
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
        title="The dates that apply"
        lede="Public colleges and universities fall under ADA Title II. Private institutions that receive federal funds are covered by Section 504, and HHS has set its own date for recipients of its funding. Which date applies to you is a question for counsel; these are the published dates."
        layout="split"
      >
        <DeadlineTimeline />
      </Section>

      <Section
        id="procurement"
        title="Ready for your review"
        lede="HECVAT Full is in progress, a FERPA data processing addendum is available on request, and the Campus plan includes single sign-on."
        tone="surface"
        layout="split"
      >
        <ProcurementTable />
        <p className="mt-8">
          <Link href="/security/" className="text-link font-semibold">
            Read the security overview
          </Link>
        </p>
      </Section>
    </SolutionPage>
  );
}
