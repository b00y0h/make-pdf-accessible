import Link from 'next/link';
import { Container } from '@/components/Container';
import { FOOTER_LINKS, SITE } from '@/content/site';

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-line bg-surface">
      <Container className="grid gap-10 py-12 md:grid-cols-3">
        <div>
          <p className="text-lg font-bold">{SITE.name}</p>
          <p className="mt-2 max-w-copy text-muted">{SITE.tagline}</p>
          <p className="mt-4 text-sm text-muted">
            We describe what our software does and what it does not do. We do
            not claim that any tool, ours included, makes a document accessible
            by itself; every result ships with evidence you can check.
          </p>
        </div>
        <nav aria-labelledby="footer-product">
          <h2
            id="footer-product"
            className="text-sm font-semibold uppercase tracking-wide text-muted"
          >
            Product
          </h2>
          <ul className="mt-3 space-y-2">
            {FOOTER_LINKS.product.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="text-ink underline-offset-4 hover:underline"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <nav aria-labelledby="footer-trust">
          <h2
            id="footer-trust"
            className="text-sm font-semibold uppercase tracking-wide text-muted"
          >
            Trust
          </h2>
          <ul className="mt-3 space-y-2">
            {FOOTER_LINKS.trust.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="text-ink underline-offset-4 hover:underline"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              <a
                href={`mailto:${SITE.contactEmail}`}
                className="text-ink underline-offset-4 hover:underline"
              >
                {SITE.contactEmail}
              </a>
            </li>
          </ul>
        </nav>
      </Container>
      <Container className="border-t border-line py-6 text-sm text-muted">
        <p>
          &copy; {new Date().getFullYear()} {SITE.name}. Deadline dates come
          from the Federal Register; verify them for your entity with counsel.
        </p>
      </Container>
    </footer>
  );
}
