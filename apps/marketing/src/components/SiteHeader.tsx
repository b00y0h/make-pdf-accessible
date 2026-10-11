'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
import { Wordmark } from '@/components/Wordmark';
import { FREE_TOOLS, NAV, SITE, SOLUTIONS } from '@/content/site';

const navLink =
  'text-ink no-underline decoration-accent decoration-2 underline-offset-[0.45em] hover:underline aria-[current=page]:underline';

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 12 12"
      className={`h-3 w-3 transition-transform duration-150 ${open ? 'rotate-180' : ''}`}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M2.5 4.5 6 8l3.5-3.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Disclosure pattern (button + aria-expanded) for both the Solutions menu and the small-screen
// menu. Escape, a click outside, or navigating closes them.
function useDisclosure() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  useEffect(() => setOpen(false), [pathname]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
        ref.current?.querySelector<HTMLButtonElement>('button')?.focus();
      }
    }
    function onPointer(event: PointerEvent) {
      if (ref.current && !ref.current.contains(event.target as Node))
        setOpen(false);
    }
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  return { open, setOpen, ref };
}

export function SiteHeader() {
  const pathname = usePathname();
  const solutions = useDisclosure();
  const mobile = useDisclosure();
  const current = (href: string) => (pathname === href ? 'page' : undefined);
  const inSolutions = pathname?.startsWith('/solutions/');

  return (
    <header className="relative z-20 border-b border-line bg-bg">
      <Container className="flex min-h-[76px] items-center justify-between gap-4 lg:gap-6">
        <Wordmark />

        <nav aria-label="Primary" className="hidden lg:block">
          <ul className="flex items-center gap-8">
            <li>
              <Link
                href={NAV[0].href}
                className={navLink}
                aria-current={current(NAV[0].href)}
              >
                {NAV[0].label}
              </Link>
            </li>
            <li>
              <div ref={solutions.ref} className="relative">
                <button
                  type="button"
                  aria-expanded={solutions.open}
                  aria-controls="solutions-menu"
                  onClick={() => solutions.setOpen(!solutions.open)}
                  className={`inline-flex items-center gap-1.5 text-ink decoration-accent decoration-2 underline-offset-[0.45em] hover:underline ${inSolutions ? 'underline' : ''}`}
                >
                  Solutions
                  <Chevron open={solutions.open} />
                </button>
                <div
                  id="solutions-menu"
                  hidden={!solutions.open}
                  className="absolute left-1/2 top-full z-30 mt-5 w-[26rem] -translate-x-1/2 rounded-sm border border-line bg-bg p-2 shadow-[0_18px_40px_-18px_rgb(20_32_44/0.35)]"
                >
                  <ul>
                    {SOLUTIONS.map((item) => (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          aria-current={current(item.href)}
                          className="block rounded-sm px-4 py-3 no-underline hover:bg-surface aria-[current=page]:bg-surface"
                        >
                          <span className="block font-semibold text-ink">
                            {item.label}
                          </span>
                          <span className="mt-0.5 block text-[0.9375rem] leading-snug text-muted">
                            {item.text}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </li>
            {NAV.slice(1).map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={navLink}
                  aria-current={current(item.href)}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden items-center gap-6 lg:flex">
          <a href={SITE.appUrl} className={navLink}>
            Sign in
          </a>
          <ButtonLink href="/pilot/">Request a pilot</ButtonLink>
        </div>

        <div ref={mobile.ref} className="lg:hidden">
          <button
            type="button"
            aria-expanded={mobile.open}
            aria-controls="mobile-menu"
            onClick={() => mobile.setOpen(!mobile.open)}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-sm border border-field px-3.5 font-semibold text-ink"
          >
            Menu
            <Chevron open={mobile.open} />
          </button>
          <div
            id="mobile-menu"
            hidden={!mobile.open}
            className="absolute inset-x-0 top-full z-30 border-b border-line bg-bg shadow-[0_24px_40px_-24px_rgb(20_32_44/0.35)]"
          >
            <nav aria-label="Primary">
              <Container className="grid gap-8 py-8 sm:grid-cols-2">
                <ul className="space-y-4">
                  {NAV.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`${navLink} text-lg`}
                        aria-current={current(item.href)}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                  {FREE_TOOLS.map((item) => (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        className={`${navLink} text-lg`}
                        aria-current={current(item.href)}
                      >
                        {item.label}
                      </Link>
                    </li>
                  ))}
                  <li>
                    <a href={SITE.appUrl} className={`${navLink} text-lg`}>
                      Sign in
                    </a>
                  </li>
                </ul>
                <div>
                  <p className="font-semibold text-muted" id="mobile-solutions">
                    Solutions
                  </p>
                  <ul
                    className="mt-3 space-y-4"
                    aria-labelledby="mobile-solutions"
                  >
                    {SOLUTIONS.map((item) => (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          className={`${navLink} text-lg`}
                          aria-current={current(item.href)}
                        >
                          {item.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                  <ButtonLink href="/pilot/" className="mt-8 w-full sm:w-auto">
                    Request a pilot
                  </ButtonLink>
                </div>
              </Container>
            </nav>
          </div>
        </div>
      </Container>
    </header>
  );
}
