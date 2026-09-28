import Link from 'next/link';
import { Container } from '@/components/Container';
import { ButtonLink } from '@/components/Button';
import { NAV, SITE } from '@/content/site';

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-bg">
      <Container className="flex flex-wrap items-center justify-between gap-4 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 text-lg font-bold text-ink no-underline"
        >
          <span
            aria-hidden="true"
            className="inline-block h-6 w-6 rounded-sm bg-accent"
          />
          {SITE.name}
        </Link>
        <nav aria-label="Primary">
          <ul className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {NAV.map((item) => (
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
                href={SITE.appUrl}
                className="text-ink underline-offset-4 hover:underline"
              >
                Sign in
              </a>
            </li>
            <li>
              <ButtonLink href="/pilot/">Request a pilot</ButtonLink>
            </li>
          </ul>
        </nav>
      </Container>
    </header>
  );
}
