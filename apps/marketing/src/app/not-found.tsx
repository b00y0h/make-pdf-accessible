import type { Metadata } from 'next';
import Link from 'next/link';
import { Container } from '@/components/Container';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Page not found',
};

export default function NotFound() {
  return (
    <Container className="py-20 lg:py-28">
      <h1 className="text-[2.5rem] leading-[1.08] sm:text-headline">
        Page not found
      </h1>
      <p className="mt-6 max-w-copy text-lede text-muted">
        The address may have changed. Try the home page, or email us and we will
        point you to the right place.
      </p>
      <p className="mt-8 flex flex-wrap gap-x-8 gap-y-3">
        <Link href="/" className="text-link font-semibold">
          Go to the home page
        </Link>
        <a
          href={`mailto:${SITE.contactEmail}`}
          className="text-link font-semibold"
        >
          {SITE.contactEmail}
        </a>
      </p>
    </Container>
  );
}
