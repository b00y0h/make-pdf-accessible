import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Security',
  description:
    'How Make PDF Accessible protects documents: AWS-native architecture, encryption, tenant isolation, access control and audit.',
};

const SECTIONS = [
  {
    title: 'Architecture',
    body: 'The platform runs entirely on Amazon Web Services in United States regions: private networks, no public storage buckets, a web application firewall at the edge, and infrastructure defined as code and reviewed before every change.',
  },
  {
    title: 'Encryption',
    body: 'All data is encrypted in transit with TLS 1.2 or later and at rest with AWS KMS keys. Each customer tier has its own key; System-tier customers can have a dedicated key or a dedicated AWS account.',
  },
  {
    title: 'Tenant isolation',
    body: 'Every record and object carries the owning institution. Database row-level security, per-tenant storage prefixes with attribute-based access control, and per-tenant encryption context are enforced by the platform, not by application code alone.',
  },
  {
    title: 'Identity and access',
    body: 'Single sign-on through your SAML or OpenID Connect identity provider, multi-factor authentication for local privileged accounts, role-based permissions, scoped API keys, and an audit log of every change.',
  },
  {
    title: 'AI models',
    body: 'Alternative text and semantic checks use Anthropic Claude models on Amazon Bedrock. Your content is not used to train models, requests stay within AWS, and the model and prompt version that produced each result are recorded in the evidence pack.',
  },
  {
    title: 'Retention and deletion',
    body: 'Originals and outputs are retained for the life of the subscription and deleted on request or termination; evidence packs are kept for the retention period you choose (one to seven years). A deletion certificate is issued.',
  },
  {
    title: 'Operations',
    body: 'Separate development, staging and production accounts; deployments through short-lived federated credentials only; dependency, container and infrastructure scanning on every change; backups with cross-region copies and a tested restore procedure.',
  },
];

export default function SecurityPage() {
  return (
    <Container className="py-14">
      <h1 className="text-4xl font-bold tracking-tight">Security</h1>
      <p className="mt-4 max-w-copy text-lg text-muted">
        A summary for security reviewers. The full whitepaper, HECVAT and
        policies are available on request.
      </p>
      <dl className="mt-8 grid max-w-4xl gap-8 md:grid-cols-2">
        {SECTIONS.map((section) => (
          <div key={section.title}>
            <dt className="text-xl font-bold">{section.title}</dt>
            <dd className="mt-2 text-muted">{section.body}</dd>
          </div>
        ))}
      </dl>
      <h2 className="mt-12 text-2xl font-bold">Responsible disclosure</h2>
      <p className="mt-2 max-w-copy">
        Report vulnerabilities to{' '}
        <a
          href={`mailto:${SITE.securityEmail}`}
          className="underline underline-offset-4"
        >
          {SITE.securityEmail}
        </a>
        . We acknowledge within two business days, keep you informed, and do not
        pursue legal action against good-faith research that respects user
        privacy and availability.
      </p>
    </Container>
  );
}
