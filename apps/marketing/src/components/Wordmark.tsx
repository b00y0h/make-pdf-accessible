import Link from 'next/link';
import { SITE } from '@/content/site';

// A sheet of paper with a seal on it: the document and the proof.
export function Mark({ className = 'h-7 w-7' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M6.5 3.5h13l6 6v19h-19z"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M19.5 3.5v6h6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="22" cy="23" r="7" className="fill-accent" />
      <path
        d="m18.8 23 2.2 2.2 4.2-4.4"
        fill="none"
        className="stroke-accent-ink"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark() {
  return (
    <Link
      href="/"
      className="inline-flex items-center gap-2.5 text-ink no-underline"
    >
      <Mark />
      <span className="whitespace-nowrap font-display text-[1.125rem] font-semibold tracking-[-0.01em] sm:text-[1.3125rem]">
        {SITE.name}
      </span>
    </Link>
  );
}
