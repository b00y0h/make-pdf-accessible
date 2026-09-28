import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { PdfCheckForm } from '@/components/PdfCheckForm';

export const metadata: Metadata = {
  title: 'Free PDF check',
  description:
    'Upload one PDF and see whether it has a text layer, structure tags, a title and a language, with an estimated cost to fix.',
};

export default function CheckPage() {
  return (
    <Container className="py-14">
      <h1 className="text-4xl font-bold tracking-tight">Free PDF check</h1>
      <p className="mt-4 max-w-copy text-lg text-muted">
        See what a document is made of before deciding what to do with it. Five
        checks per day, no account needed.
      </p>
      <div className="mt-8 max-w-copy">
        <PdfCheckForm />
      </div>
      <p className="mt-8 max-w-copy text-sm text-muted">
        Files are scanned for malware, kept only long enough to run the check,
        and deleted within 24 hours. Do not upload documents containing personal
        data; sign in to process those under a data processing agreement.
      </p>
    </Container>
  );
}
