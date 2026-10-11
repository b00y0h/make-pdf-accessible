import type { Metadata } from 'next';
import Link from 'next/link';
import { EvidenceRecord } from '@/components/EvidenceRecord';
import { Section } from '@/components/Section';
import { SolutionPage } from '@/components/SolutionPage';

export const metadata: Metadata = {
  title: 'Counsel and law firms',
  description:
    'A versioned decision record and a signed, independently verifiable evidence pack for every document, for counsel advising public institutions and firms publishing their own documents.',
};

const CONFIDENTIALITY = [
  {
    title: 'Where documents live',
    text: 'Amazon Web Services in United States regions, in private networks with no public storage buckets.',
  },
  {
    title: 'Encryption',
    text: 'TLS 1.2 or later in transit and AWS KMS keys at rest, with a dedicated key or a dedicated AWS account on the System plan.',
  },
  {
    title: 'Models',
    text: 'Customer content is never used to train models, and requests to Amazon Bedrock stay within AWS.',
  },
  {
    title: 'Deletion',
    text: 'Originals and outputs are deleted on request or termination, and a deletion certificate is issued.',
  },
];

export default function LegalPage() {
  return (
    <SolutionPage
      title="A record of every document decision, built to be reviewed."
      lede="For general counsel at public institutions, outside counsel advising public entities, and firms that publish their own documents. Every decision cites the rule behind it, and every document has a signed evidence pack that can be verified without us."
      challenges={[
        {
          title: 'Clients ask what they must do',
          text: 'An institution with thousands of PDFs needs to know which documents the rule reaches, which may be exempt, and what fixing the rest will cost.',
        },
        {
          title: 'A tool log is not a record',
          text: 'Automated tagging output says a file was processed. It does not say what was decided, why, by whom, or whether the result passed independent validation.',
        },
        {
          title: 'Vendor claims carry risk',
          text: 'The FTC has acted against an accessibility vendor over claims that its software made websites compliant. Advice that rests on a vendor’s promise inherits that risk.',
        },
        {
          title: 'Your own documents count too',
          text: 'Client alerts, briefs, guides and forms posted as PDFs are hard or impossible to read for clients who use screen readers.',
        },
      ]}
      outcomes={[
        {
          title: 'Decisions that cite their rule',
          text: 'Triage rules are explicit and versioned. Each decision cites the rule that produced it, staff can override any decision with a note, and the history is kept.',
        },
        {
          title: 'An evidence pack per document',
          text: 'Validator reports, per-element semantic checks with confidence, reviewer sign-off, and tool and model versions with timestamps, as portable JSON plus the raw reports.',
        },
        {
          title: 'Verifiable without us',
          text: 'Packs are signed so anyone can check they have not changed, and retained for the period you choose, from one to seven years.',
        },
        {
          title: 'Exports for the people who approve',
          text: 'The plan exports as CSV and as an accessible PDF for counsel, finance and leadership.',
        },
      ]}
      start={{
        title: 'Where counsel starts',
        text: (
          <>
            With a free inventory of one client site, requested with your
            client’s authorization, or a 30-day pilot that ends with evidence
            packs and a written summary for counsel. We do not give legal
            advice; counsel decides what the rule requires.{' '}
            <Link href="/trust/" className="text-link">
              Visit the trust center
            </Link>
            .
          </>
        ),
      }}
    >
      <Section
        id="record"
        title="What a record contains"
        lede="One record per document: what was found, what was decided and why, what was checked, who signed off, and where the result was published."
        layout="split"
      >
        <div className="pt-6 sm:px-6 lg:max-w-2xl lg:px-0">
          <EvidenceRecord />
        </div>
      </Section>

      <Section
        id="confidentiality"
        title="How documents are handled"
        lede="A summary for firms and their clients. The full security whitepaper and data processing terms are available on request."
        tone="surface"
        layout="split"
      >
        <dl className="grid gap-x-12 gap-y-10 sm:grid-cols-2">
          {CONFIDENTIALITY.map((item) => (
            <div key={item.title} className="border-t-2 border-accent pt-5">
              <dt className="text-[1.3125rem] font-semibold leading-snug">
                {item.title}
              </dt>
              <dd className="mt-2 text-muted">{item.text}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-10">
          <Link href="/security/" className="text-link font-semibold">
            Read the security overview
          </Link>
        </p>
      </Section>
    </SolutionPage>
  );
}
