import type { Metadata } from 'next';
import Link from 'next/link';
import { Container } from '@/components/Container';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Trust center',
  description:
    'Accessibility statement, security overview, compliance status, subprocessors and policies.',
};

const CARDS = [
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

const STATUS = [
  {
    item: 'Accessibility conformance report (VPAT 2.5) for this site',
    status:
      'Published with the first production release; audit scheduled before launch',
  },
  {
    item: 'Accessibility conformance report for the dashboard',
    status: 'In progress',
  },
  { item: 'HECVAT Full', status: 'In progress' },
  { item: 'SOC 2 Type I', status: 'Planned within nine months of launch' },
  { item: 'SOC 2 Type II', status: 'Planned within eighteen months of launch' },
  { item: 'FERPA data processing addendum', status: 'Available on request' },
  {
    item: 'Penetration test',
    status: 'Annual, first scheduled before general availability',
  },
];

export default function TrustPage() {
  return (
    <Container className="py-14">
      <h1 className="text-4xl font-bold tracking-tight">Trust center</h1>
      <p className="mt-4 max-w-copy text-lg text-muted">
        What we do with your documents, how we protect them, and where we are on
        the reviews your procurement office asks for. We state the status
        honestly, including what is not done yet.
      </p>
      <ul className="mt-8 grid gap-6 md:grid-cols-3">
        {CARDS.map((card) => (
          <li key={card.href} className="rounded-lg border border-line p-5">
            <h2 className="text-xl font-bold">
              <Link
                href={card.href}
                className="underline-offset-4 hover:underline"
              >
                {card.title}
              </Link>
            </h2>
            <p className="mt-2 text-muted">{card.text}</p>
          </li>
        ))}
      </ul>

      <h2 className="mt-12 text-2xl font-bold">Compliance status</h2>
      <table className="mt-4 w-full max-w-3xl border-collapse text-left">
        <caption className="sr-only-focusable">
          Status of compliance artifacts
        </caption>
        <thead>
          <tr className="border-b border-line">
            <th scope="col" className="py-2 pr-4">
              Item
            </th>
            <th scope="col" className="py-2">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {STATUS.map((row) => (
            <tr key={row.item} className="border-b border-line align-top">
              <th scope="row" className="py-2 pr-4 font-normal">
                {row.item}
              </th>
              <td className="py-2 text-muted">{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="mt-12 text-2xl font-bold">Subprocessors</h2>
      <p className="mt-2 max-w-copy text-muted">
        Amazon Web Services (hosting, storage, Amazon Bedrock models; United
        States regions), a payment processor for invoices, and an email delivery
        provider. Customer content is never used to train models. The full list
        with purposes is provided with the data processing addendum.
      </p>

      <h2 className="mt-12 text-2xl font-bold">Contact</h2>
      <p className="mt-2">
        Security questions and vulnerability reports:{' '}
        <a
          href={`mailto:${SITE.securityEmail}`}
          className="underline underline-offset-4"
        >
          {SITE.securityEmail}
        </a>
        . We acknowledge reports within two business days.
      </p>
    </Container>
  );
}
