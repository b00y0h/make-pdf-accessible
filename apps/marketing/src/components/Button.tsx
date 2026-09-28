import Link from 'next/link';
import type { ReactNode } from 'react';

type Variant = 'primary' | 'secondary';

const styles: Record<Variant, string> = {
  primary:
    'bg-accent text-accent-ink hover:opacity-90 border border-transparent',
  secondary: 'bg-transparent text-ink border border-line hover:bg-surface',
};

const base =
  'inline-flex min-h-[44px] items-center justify-center rounded-md px-5 py-2.5 text-base font-semibold no-underline';

export function ButtonLink({
  href,
  children,
  variant = 'primary',
  className = '',
}: {
  href: string;
  children: ReactNode;
  variant?: Variant;
  className?: string;
}) {
  return (
    <Link href={href} className={`${base} ${styles[variant]} ${className}`}>
      {children}
    </Link>
  );
}

export function Button({
  children,
  variant = 'primary',
  type = 'submit',
  disabled = false,
  className = '',
}: {
  children: ReactNode;
  variant?: Variant;
  type?: 'submit' | 'button';
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      aria-disabled={disabled || undefined}
      className={`${base} ${styles[variant]} disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
    >
      {children}
    </button>
  );
}
