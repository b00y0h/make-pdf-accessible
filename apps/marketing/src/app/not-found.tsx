import type { Metadata } from 'next';
import Link from 'next/link';
import { Container } from '@/components/Container';

export const metadata: Metadata = {
  title: 'Page not found',
};

export default function NotFound() {
  return (
    <Container className="py-20">
      <h1 className="text-4xl font-bold tracking-tight">Page not found</h1>
      <p className="mt-4 max-w-prose text-lg text-muted">
        The address may have changed. Try the home page, or email us and we will
        point you to the right place.
      </p>
      <p className="mt-6">
        <Link href="/" className="font-semibold underline underline-offset-4">
          Go to the home page
        </Link>
      </p>
    </Container>
  );
}
