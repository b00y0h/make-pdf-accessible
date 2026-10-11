import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { PageHeader } from '@/components/PageHeader';
import { PdfCheckForm } from '@/components/PdfCheckForm';

export const metadata: Metadata = {
  title: 'Free PDF check',
  description:
    'Upload one PDF and see whether it has a text layer, structure tags, a title and a language, with an estimated cost to fix.',
};

export default function CheckPage() {
  return (
    <>
      <PageHeader
        title="Free PDF check"
        lede="See what a document is made of before deciding what to do with it. Five checks per day, no account needed."
      />
      <Container className="py-16 lg:py-24">
        <div className="max-w-3xl">
          <PdfCheckForm />
          <p className="mt-10 max-w-copy text-[0.9375rem] text-muted">
            Files are scanned for malware, kept only long enough to run the
            check, and deleted within 24 hours. Do not upload documents
            containing personal data; sign in to process those under a data
            processing agreement.
          </p>
        </div>
      </Container>
    </>
  );
}
