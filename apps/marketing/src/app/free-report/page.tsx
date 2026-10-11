import type { Metadata } from 'next';
import Link from 'next/link';
import { Container } from '@/components/Container';
import { SiteReportForm } from '@/components/SiteReportForm';

export const metadata: Metadata = {
  title: 'Free website inventory report',
  description:
    'Enter your institution website and get an emailed inventory of every PDF we can find, with page counts and estimated costs.',
};

const CONTENTS = [
  'Every PDF linked from your public site (up to 5,000), with page counts',
  'How many are scanned, untagged, encrypted, forms, or missing a title or language',
  'Orphaned files nothing links to, which may qualify for deletion or archiving',
  'The twenty largest documents by page count',
  'An estimated cost by path: convert to HTML, remediate as PDF, human-verified',
];

export default function FreeReportPage() {
  return (
    <Container className="grid gap-16 pb-20 pt-14 lg:grid-cols-12 lg:gap-12 lg:pb-28 lg:pt-20">
      <div className="lg:col-span-6">
        <h1 className="text-[2.5rem] leading-[1.08] sm:text-headline">
          Free website inventory report
        </h1>
        <p className="mt-6 max-w-copy text-lede text-muted">
          Most institutions do not know how many PDFs they publish. Within two
          hours you will.
        </p>
        <h2 className="mt-12 text-[1.75rem] leading-tight">
          What the report contains
        </h2>
        <ul className="mt-5 border-t border-line">
          {CONTENTS.map((item) => (
            <li key={item} className="flex gap-3 border-b border-line py-3.5">
              <svg
                viewBox="0 0 16 16"
                className="mt-[0.35em] h-4 w-4 shrink-0 text-accent"
                aria-hidden="true"
                focusable="false"
              >
                <path
                  d="m3.5 8.5 3 3 6-7"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>{item}</span>
            </li>
          ))}
        </ul>
        <h2 className="mt-12 text-[1.75rem] leading-tight">How we crawl</h2>
        <p className="mt-4 max-w-copy text-muted">
          Our crawler identifies itself, follows robots.txt, fetches no more
          than four pages per second, and reads only the metadata it needs. It
          never stores your documents after the report is sent. See{' '}
          <Link href="/bot/" className="text-link">
            our crawler page
          </Link>{' '}
          for details.
        </p>
      </div>
      <div className="self-start rounded-sm border border-line p-6 shadow-[0_30px_60px_-36px_rgb(20_32_44/0.35)] sm:p-8 lg:col-span-6 lg:ml-6">
        <h2 className="text-[1.75rem] leading-tight">Request your report</h2>
        <div className="mt-5">
          <SiteReportForm />
        </div>
      </div>
    </Container>
  );
}
