import type { Metadata } from 'next';
import { ButtonLink } from '@/components/Button';
import { PageHeader } from '@/components/PageHeader';
import { PricingCalculator } from '@/components/PricingCalculator';
import { Section } from '@/components/Section';
import { Container } from '@/components/Container';
import { INVENTORY_ENGAGEMENT, PLANS, VERIFIED_TIER } from '@/content/site';

export const metadata: Metadata = {
  title: 'Pricing',
  description:
    'Published per-page prices for automated and human-verified document accessibility, with a calculator.',
};

const FAQ = [
  {
    q: 'What counts as a page?',
    a: 'One page of a PDF submitted for remediation or conversion. Pages that are deleted or archived by a triage decision are not charged. Cached repeats of the same file are free.',
  },
  {
    q: 'What happens when we exceed the included pages?',
    a: 'Processing continues at the overage rate shown for your plan and appears as a line item on the next invoice. Admins can set a hard cap instead.',
  },
  {
    q: 'Do unused pages roll over?',
    a: 'No. Allowances reset annually. Most institutions front-load work before the deadline and settle into a smaller maintenance volume; we will right-size the plan at renewal.',
  },
  {
    q: 'Can we buy through a cooperative contract?',
    a: 'Yes. We are pursuing listings that let public entities buy without a separate procurement; ask us which ones apply to your state.',
  },
  {
    q: 'Is the pilot credited?',
    a: 'The pilot fee is credited to the first year of a Campus or System plan signed within 90 days.',
  },
];

export default function PricingPage() {
  return (
    <>
      <PageHeader
        title="Pricing"
        lede="Every price is on this page. Annual plans include a page allowance; overage is per page; human verification is an add-on priced per page."
      />

      <section aria-labelledby="plans-title">
        <Container className="py-16 lg:py-24">
          <h2
            id="plans-title"
            className="text-[1.875rem] leading-tight sm:text-title"
          >
            Plans
          </h2>
          <ul className="mt-10 grid gap-x-4 gap-y-10 md:grid-cols-2 xl:grid-cols-4">
            {PLANS.map((plan) => {
              const featured = plan.id === 'campus';
              return (
                <li
                  key={plan.id}
                  className={`flex flex-col border-t-2 px-6 pb-8 pt-6 ${featured ? 'border-accent bg-tint' : 'border-ink'}`}
                >
                  <h3 className="font-display text-[1.75rem] font-medium leading-tight">
                    {plan.name}
                  </h3>
                  <p className="mt-1 text-muted xl:min-h-[3.4em]">
                    {plan.summary}
                  </p>
                  <p className="mt-6">
                    {plan.price.startsWith('from ') ? (
                      <span className="mr-1.5 text-muted">from</span>
                    ) : null}
                    <span className="whitespace-nowrap font-display text-[2.25rem] font-medium leading-none tabular-nums">
                      {plan.price.replace(/^from /, '')}
                    </span>
                    {plan.cadence ? (
                      <span className="mt-1 block text-[0.9375rem] text-muted">
                        {plan.cadence}
                      </span>
                    ) : null}
                  </p>
                  <ul className="mt-6 flex-1 space-y-2.5 border-t border-line pt-6">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex gap-3">
                        <svg
                          viewBox="0 0 16 16"
                          className="mt-[0.3em] h-4 w-4 shrink-0 text-accent"
                          aria-hidden="true"
                          focusable="false"
                        >
                          <path
                            d="m3.5 8.5 3 3 6-7"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.8"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  {plan.overage ? (
                    <p className="mt-6 text-[0.9375rem] text-muted">
                      Overage: {plan.overage}
                    </p>
                  ) : null}
                  <div className="mt-6">
                    <ButtonLink
                      href={plan.cta.href}
                      variant={featured ? 'primary' : 'secondary'}
                      className="w-full"
                    >
                      {plan.cta.label}
                    </ButtonLink>
                  </div>
                </li>
              );
            })}
          </ul>
        </Container>
      </section>

      <Section
        id="verified"
        title="Verified add-on"
        lede="Human review where automation is weakest, recorded in the evidence pack."
        tone="surface"
        layout="split"
      >
        <table className="w-full border-collapse text-left">
          <caption className="sr-only-focusable">
            Verified tier prices per page
          </caption>
          <thead>
            <tr className="border-b border-ink text-[0.9375rem]">
              <th scope="col" className="py-3 pr-6 font-semibold">
                Service
              </th>
              <th scope="col" className="py-3 text-right font-semibold">
                Price per page
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-line">
              <th scope="row" className="py-4 pr-6 font-normal">
                {VERIFIED_TIER.flagged.label}
              </th>
              <td className="py-4 text-right font-semibold tabular-nums">
                ${VERIFIED_TIER.flagged.price.toFixed(2)}
              </td>
            </tr>
            <tr className="border-b border-line">
              <th scope="row" className="py-4 pr-6 font-normal">
                {VERIFIED_TIER.full.label}
              </th>
              <td className="py-4 text-right font-semibold tabular-nums">
                ${VERIFIED_TIER.full.price.toFixed(2)}
              </td>
            </tr>
            <tr className="border-b border-line">
              <th scope="row" className="py-4 pr-6 font-normal">
                {VERIFIED_TIER.stemForms.label}
              </th>
              <td className="py-4 text-right font-semibold tabular-nums">
                ${VERIFIED_TIER.stemForms.priceLow.toFixed(2)} to $
                {VERIFIED_TIER.stemForms.priceHigh.toFixed(2)}
              </td>
            </tr>
          </tbody>
        </table>
        <p className="mt-4 text-muted">
          Turnaround: {VERIFIED_TIER.turnaround}.
        </p>
        <h3 className="mt-12 font-display text-[1.5rem] font-medium leading-tight">
          Inventory and triage engagement
        </h3>
        <p className="mt-3 max-w-copy">
          <span className="font-semibold">
            ${INVENTORY_ENGAGEMENT.price.toLocaleString('en-US')}{' '}
            {INVENTORY_ENGAGEMENT.unit}.
          </span>{' '}
          {INVENTORY_ENGAGEMENT.includes}
        </p>
      </Section>

      <Section
        id="calculator"
        title="Estimate your backlog"
        lede="Compare our published rates with the manual rates institutions report."
        layout="split"
      >
        <PricingCalculator />
      </Section>

      <Section id="faq" title="Questions" tone="surface" layout="split">
        <dl className="divide-y divide-line border-y border-line">
          {FAQ.map((item) => (
            <div key={item.q} className="py-6">
              <dt className="text-[1.1875rem] font-semibold">{item.q}</dt>
              <dd className="mt-2 max-w-copy text-muted">{item.a}</dd>
            </div>
          ))}
        </dl>
      </Section>
    </>
  );
}
