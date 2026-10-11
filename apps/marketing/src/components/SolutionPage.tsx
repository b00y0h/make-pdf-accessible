import type { ReactNode } from 'react';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
import { PageHeader } from '@/components/PageHeader';
import { Section } from '@/components/Section';

type Item = { title: string; text: string };

// Shared shape for the audience pages: the problem in the buyer's words, what changes, then
// page-specific sections (dates, the record, procurement), then where to start.
export function SolutionPage({
  title,
  lede,
  challenges,
  outcomes,
  children,
  start,
}: {
  title: string;
  lede: string;
  challenges: Item[];
  outcomes: Item[];
  children: ReactNode;
  start: { title: string; text: ReactNode };
}) {
  return (
    <>
      <PageHeader title={title} lede={lede}>
        <div className="flex flex-wrap gap-3">
          <ButtonLink href="/free-report/">
            Get a free inventory of your site
          </ButtonLink>
          <ButtonLink href="/pilot/" variant="secondary">
            Request a pilot
          </ButtonLink>
        </div>
      </PageHeader>

      <Section id="challenges" title="What you are up against" layout="split">
        <dl className="divide-y divide-line border-y border-line">
          {challenges.map((item) => (
            <div
              key={item.title}
              className="grid gap-2 py-7 md:grid-cols-[15rem_1fr] md:gap-10"
            >
              <dt className="font-display text-[1.3125rem] font-medium leading-snug">
                {item.title}
              </dt>
              <dd className="text-muted">{item.text}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section id="outcomes" title="What changes" tone="surface" layout="split">
        <ul className="grid gap-x-12 gap-y-10 sm:grid-cols-2">
          {outcomes.map((item) => (
            <li key={item.title} className="border-t-2 border-accent pt-5">
              <h3 className="text-[1.3125rem] font-semibold leading-snug">
                {item.title}
              </h3>
              <p className="mt-2 text-muted">{item.text}</p>
            </li>
          ))}
        </ul>
      </Section>

      {children}

      {/* Pages end their own sections on the surface tone, so this one sits on paper. */}
      <section aria-labelledby="start-title">
        <Container className="py-16 lg:py-24">
          <div className="grid gap-8 lg:grid-cols-12 lg:items-end">
            <div className="lg:col-span-7">
              <h2
                id="start-title"
                className="text-[1.875rem] leading-tight sm:text-title"
              >
                {start.title}
              </h2>
              <p className="mt-4 max-w-copy text-lg text-muted">{start.text}</p>
            </div>
            <div className="flex flex-wrap gap-3 lg:col-span-5 lg:justify-end">
              <ButtonLink href="/free-report/">
                Get a free inventory of your site
              </ButtonLink>
              <ButtonLink href="/pilot/" variant="secondary">
                Request a pilot
              </ButtonLink>
            </div>
          </div>
        </Container>
      </section>
    </>
  );
}
