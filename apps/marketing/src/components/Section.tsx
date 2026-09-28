import type { ReactNode } from 'react';
import { Container } from '@/components/Container';

export function Section({
  id,
  title,
  lede,
  children,
  tone = 'default',
}: {
  id: string;
  title: string;
  lede?: string;
  children: ReactNode;
  tone?: 'default' | 'surface';
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className={tone === 'surface' ? 'bg-surface' : ''}
    >
      <Container className="py-14">
        <h2 id={`${id}-title`} className="text-3xl font-bold tracking-tight">
          {title}
        </h2>
        {lede ? (
          <p className="mt-3 max-w-copy text-lg text-muted">{lede}</p>
        ) : null}
        <div className="mt-8">{children}</div>
      </Container>
    </section>
  );
}
