import type { Metadata } from 'next';
import Link from 'next/link';
import { PageHeader } from '@/components/PageHeader';
import { ProcurementTable } from '@/components/ProcurementTable';
import { Section } from '@/components/Section';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Trust center',
  description:
    'Accessibility statement, security overview, compliance status, subprocessors and policies.',
};

const DOCUMENTS = [
  {
    href: '/accessibility/',
    title: 'Accessibility statement',
    text: 'How this site and the product meet WCAG 2.2 AA, known issues, and how to report a barrier.',
  },
  {
    href: '/security/',
    title: 'Security',
    text: 'Architecture, encryption, tenant isolation, access control, and the status of our SOC 2 and HECVAT work.',
  },
  {
    href: '/bot/',
    title: 'Our crawler',
    text: 'User agent, rate limits and how to allow or block MakePDFAccessibleBot.',
  },
];

export default function TrustPage() {
  return (
    <>
      <PageHeader
        title="Trust center"
        lede="What we do with your documents, how we protect them, and where we are on the reviews your procurement office asks for. We state the status honestly, including what is not done yet."
      />

      <Section id="documents" title="Policies and statements" layout="split">
        <ul className="divide-y divide-line border-y border-line">
          {DOCUMENTS.map((doc) => (
            <li
              key={doc.href}
              className="grid gap-2 py-7 md:grid-cols-[15rem_1fr] md:gap-10"
            >
              <h3 className="font-display text-[1.3125rem] font-medium leading-snug">
                <Link href={doc.href} className="text-link">
                  {doc.title}
                </Link>
              </h3>
              <p className="text-muted">{doc.text}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section
        id="status"
        title="Compliance status"
        lede="Updated as each item changes. Ask us for current drafts of anything in progress."
        tone="surface"
        layout="split"
      >
        <ProcurementTable />
      </Section>

      <Section id="subprocessors" title="Subprocessors" layout="split">
        <p className="max-w-copy">
          Amazon Web Services (hosting, storage, Amazon Bedrock models; United
          States regions), a payment processor for invoices, and an email
          delivery provider. Customer content is never used to train models. The
          full list with purposes is provided with the data processing addendum.
        </p>
      </Section>

      <Section id="contact" title="Contact" tone="surface" layout="split">
        <p className="max-w-copy">
          Security questions and vulnerability reports:{' '}
          <a href={`mailto:${SITE.securityEmail}`} className="text-link">
            {SITE.securityEmail}
          </a>
          . We acknowledge reports within two business days.
        </p>
      </Section>
    </>
  );
}
