import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { PageHeader } from '@/components/PageHeader';
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
    <>
      <PageHeader
        title="MakePDFAccessibleBot"
        lede="Our crawler finds PDF documents on websites whose owners asked for an inventory. It does not index page content and it does not crawl sites nobody asked us to look at."
      />
      <Container className="py-16 lg:py-24">
        <article className="record-copy max-w-copy">
          <h2>Identification</h2>
          <p>User agent:</p>
          <p>
            <code className="block break-all rounded-sm border border-line bg-surface px-4 py-3 font-mono text-[0.9375rem]">
              {SITE.crawlerUserAgent}
            </code>
          </p>
          <h2>Behavior</h2>
          <ul>
            <li>
              Reads and obeys robots.txt, including Disallow and Crawl-delay.
            </li>
            <li>
              Fetches at most four requests per second per host, and backs off
              on 429 or 503 responses.
            </li>
            <li>
              Follows links to PDFs and reads only the bytes needed to determine
              page count, tags, text layer, title, language, forms and
              encryption.
            </li>
            <li>
              Runs on request (a free report or a customer crawl) and on
              schedules customers set.
            </li>
          </ul>
          <h2>Allow or block</h2>
          <pre className="overflow-x-auto rounded-sm border border-line bg-surface p-4 font-mono text-[0.9375rem]">
            <code>{ROBOTS_EXAMPLE}</code>
          </pre>
          <p>
            Questions or an unexpected visit? Email{' '}
            <a href={`mailto:${SITE.contactEmail}?subject=Crawler`}>
              {SITE.contactEmail}
            </a>{' '}
            with the timestamps and we will explain or stop.
          </p>
        </article>
      </Container>
    </>
  );
}
