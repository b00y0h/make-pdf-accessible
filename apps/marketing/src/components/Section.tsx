import type { ReactNode } from 'react';
import { Container } from '@/components/Container';

// `split` puts the heading in a left column beside the content, the way a report or a
// statute sets section titles in the margin. `stacked` puts it above.
export function Section({
  id,
  title,
  lede,
  children,
  tone = 'default',
  layout = 'stacked',
}: {
  id: string;
  title: string;
  lede?: ReactNode;
  children: ReactNode;
  tone?: 'default' | 'surface';
  layout?: 'stacked' | 'split';
}) {
  const heading = (
    <>
      <h2
        id={`${id}-title`}
        className="text-[1.875rem] leading-tight sm:text-title"
      >
        {title}
      </h2>
      {lede ? (
        <p className="mt-4 max-w-copy text-lg text-muted">{lede}</p>
      ) : null}
    </>
  );

  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className={tone === 'surface' ? 'bg-surface' : ''}
    >
      <Container className="py-16 lg:py-24">
        {layout === 'split' ? (
          <div className="grid gap-10 lg:grid-cols-12 lg:gap-12">
            <div className="min-w-0 lg:col-span-4">{heading}</div>
            <div className="min-w-0 lg:col-span-8">{children}</div>
          </div>
        ) : (
          <>
            {heading}
            <div className="mt-10">{children}</div>
          </>
        )}
      </Container>
    </section>
  );
}
