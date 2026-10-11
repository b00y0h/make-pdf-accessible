import Link from 'next/link';
import { Container } from '@/components/Container';
import { Mark } from '@/components/Wordmark';
import { FOOTER_LINKS, SITE } from '@/content/site';

const columns = [
  { id: 'footer-product', title: 'Product', links: FOOTER_LINKS.product },
  { id: 'footer-solutions', title: 'Solutions', links: FOOTER_LINKS.solutions },
  { id: 'footer-trust', title: 'Trust', links: FOOTER_LINKS.trust },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-surface">
      <Container className="grid gap-12 py-16 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <p className="flex items-center gap-2.5 font-display text-[1.3125rem] font-semibold">
            <Mark />
            {SITE.name}
          </p>
          <p className="mt-4 max-w-sm text-muted">{SITE.tagline}</p>
          <p className="mt-6 max-w-sm text-[0.9375rem] text-muted">
            We describe what our software does and what it does not do. We do
            not claim that any tool, ours included, makes a document accessible
            by itself; every result ships with evidence you can check.
          </p>
        </div>
        <div className="grid gap-10 sm:grid-cols-3 lg:col-span-7">
          {columns.map((column) => (
            <nav key={column.id} aria-labelledby={column.id}>
              <h2
                id={column.id}
                className="font-sans text-base font-semibold tracking-normal text-ink"
              >
                {column.title}
              </h2>
              <ul className="mt-4 space-y-3">
                {column.links.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="text-muted underline-offset-4 hover:text-ink hover:underline"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
                {column.id === 'footer-trust' ? (
                  <li>
                    <a
                      href={`mailto:${SITE.contactEmail}`}
                      className="text-muted underline-offset-4 hover:text-ink hover:underline"
                    >
                      {SITE.contactEmail}
                    </a>
                  </li>
                ) : null}
              </ul>
            </nav>
          ))}
        </div>
      </Container>
      <Container className="text-[0.9375rem] text-muted">
        <p className="border-t border-line py-6">
          &copy; {new Date().getFullYear()} {SITE.name}. Deadline dates come
          from the Federal Register; verify them for your entity with counsel.
        </p>
      </Container>
    </footer>
  );
}
