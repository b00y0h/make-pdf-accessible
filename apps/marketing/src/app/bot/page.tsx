import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Our crawler',
  description:
    'How MakePDFAccessibleBot identifies itself, how fast it crawls, and how to allow or block it.',
};

const ROBOTS_EXAMPLE = `User-agent: MakePDFAccessibleBot
Disallow: /private/

# or, to block entirely
User-agent: MakePDFAccessibleBot
Disallow: /`;

export default function BotPage() {
  return (
    <Container className="py-14">
      <article className="max-w-copy">
        <h1 className="text-4xl font-bold tracking-tight">
          MakePDFAccessibleBot
        </h1>
        <p className="mt-4 text-lg text-muted">
          Our crawler finds PDF documents on websites whose owners asked for an
          inventory. It does not index page content and it does not crawl sites
          nobody asked us to look at.
        </p>
        <h2 className="mt-8 text-2xl font-bold">Identification</h2>
        <p className="mt-2">
          User agent:{' '}
          <code className="rounded-sm bg-surface px-1 py-0.5 font-mono text-sm">
            {SITE.crawlerUserAgent}
          </code>
        </p>
        <h2 className="mt-8 text-2xl font-bold">Behavior</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>
            Reads and obeys robots.txt, including Disallow and Crawl-delay.
          </li>
          <li>
            Fetches at most four requests per second per host, and backs off on
            429 or 503 responses.
          </li>
          <li>
            Follows links to PDFs and reads only the bytes needed to determine
            page count, tags, text layer, title, language, forms and encryption.
          </li>
          <li>
            Runs on request (a free report or a customer crawl) and on schedules
            customers set.
          </li>
        </ul>
        <h2 className="mt-8 text-2xl font-bold">Allow or block</h2>
        <pre className="mt-2 overflow-x-auto rounded-md bg-surface p-4 font-mono text-sm">
          <code>{ROBOTS_EXAMPLE}</code>
        </pre>
        <p className="mt-4">
          Questions or an unexpected visit? Email{' '}
          <a
            href={`mailto:${SITE.contactEmail}?subject=Crawler`}
            className="underline underline-offset-4"
          >
            {SITE.contactEmail}
          </a>{' '}
          with the timestamps and we will explain or stop.
        </p>
      </article>
    </Container>
  );
}
