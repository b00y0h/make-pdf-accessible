import type { Metadata } from 'next';
import Link from 'next/link';
import { Container } from '@/components/Container';
import { SiteReportForm } from '@/components/SiteReportForm';

export const metadata: Metadata = {
  title: 'Free website inventory report',
  description:
    'Enter your institution website and get an emailed inventory of every PDF we can find, with page counts and estimated costs.',
};

export default function FreeReportPage() {
  return (
    <Container className="grid gap-10 py-14 lg:grid-cols-2">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">
          Free website inventory report
        </h1>
        <p className="mt-4 max-w-copy text-lg text-muted">
          Most institutions do not know how many PDFs they publish. Within two
          hours you will.
        </p>
        <h2 className="mt-8 text-xl font-bold">What the report contains</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>
            Every PDF linked from your public site (up to 5,000), with page
            counts
          </li>
          <li>
            How many are scanned, untagged, encrypted, forms, or missing a title
            or language
          </li>
          <li>
            Orphaned files nothing links to, which may qualify for deletion or
            archiving
          </li>
          <li>The twenty largest documents by page count</li>
          <li>
            An estimated cost by path: convert to HTML, remediate as PDF,
            human-verified
          </li>
        </ul>
        <h2 className="mt-8 text-xl font-bold">How we crawl</h2>
        <p className="mt-2 max-w-copy text-muted">
          Our crawler identifies itself, follows robots.txt, fetches no more
          than four pages per second, and reads only the metadata it needs. It
          never stores your documents after the report is sent. See{' '}
          <Link href="/bot/" className="underline underline-offset-4">
            our crawler page
          </Link>{' '}
          for details.
        </p>
      </div>
      <div className="rounded-lg border border-line p-6">
        <h2 className="text-2xl font-bold">Request your report</h2>
        <div className="mt-4">
          <SiteReportForm />
        </div>
      </div>
    </Container>
  );
}
