import type { ReactNode } from 'react';
import { Container } from '@/components/Container';

// Opening block for interior pages: one h1, a lede, and optional actions.
export function PageHeader({
  title,
  lede,
  children,
}: {
  title: string;
  lede?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="border-b border-line">
      <Container className="pb-14 pt-14 lg:pb-20 lg:pt-20">
        <h1 className="max-w-4xl text-[2.5rem] leading-[1.08] sm:text-headline lg:text-[3.75rem]">
          {title}
        </h1>
        {lede ? (
          <p className="mt-6 max-w-copy text-lede text-muted">{lede}</p>
        ) : null}
        {children ? <div className="mt-8">{children}</div> : null}
      </Container>
    </div>
  );
}
