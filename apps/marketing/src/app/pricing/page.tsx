import type { Metadata } from 'next';
import { ButtonLink } from '@/components/Button';
import { Container } from '@/components/Container';
import { PricingCalculator } from '@/components/PricingCalculator';
import { Section } from '@/components/Section';
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
      <Container className="py-14">
        <h1 className="text-4xl font-bold tracking-tight">Pricing</h1>
        <p className="mt-4 max-w-prose text-lg text-muted">
          Every price is on this page. Annual plans include a page allowance;
          overage is per page; human verification is an add-on priced per page.
        </p>
      </Container>

      <Section id="plans" title="Plans">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className="flex flex-col rounded-lg border border-line p-5"
            >
              <h3 className="text-xl font-bold">{plan.name}</h3>
              <p className="mt-1 text-3xl font-bold">
                {plan.price}{' '}
                <span className="text-base font-normal text-muted">
                  {plan.cadence}
                </span>
              </p>
              <p className="mt-2 text-muted">{plan.summary}</p>
              <ul className="mt-4 flex-1 list-disc space-y-1 pl-5">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              {plan.overage ? (
                <p className="mt-4 text-sm text-muted">
                  Overage: {plan.overage}
                </p>
              ) : null}
              <div className="mt-4">
                <ButtonLink
                  href={plan.cta.href}
                  variant={plan.id === 'campus' ? 'primary' : 'secondary'}
                  className="w-full"
                >
                  {plan.cta.label}
                </ButtonLink>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section
        id="verified"
        title="Verified add-on"
        lede="Human review where automation is weakest, recorded in the evidence pack."
        tone="surface"
      >
        <table className="w-full max-w-prose border-collapse text-left">
          <caption className="sr-only-focusable">
            Verified tier prices per page
          </caption>
          <thead>
            <tr className="border-b border-line">
              <th scope="col" className="py-2 pr-4">
                Service
              </th>
              <th scope="col" className="py-2">
                Price per page
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-line">
              <th scope="row" className="py-2 pr-4 font-normal">
                {VERIFIED_TIER.flagged.label}
              </th>
              <td className="py-2">
                ${VERIFIED_TIER.flagged.price.toFixed(2)}
              </td>
            </tr>
            <tr className="border-b border-line">
              <th scope="row" className="py-2 pr-4 font-normal">
                {VERIFIED_TIER.full.label}
              </th>
              <td className="py-2">${VERIFIED_TIER.full.price.toFixed(2)}</td>
            </tr>
            <tr className="border-b border-line">
              <th scope="row" className="py-2 pr-4 font-normal">
                {VERIFIED_TIER.stemForms.label}
              </th>
              <td className="py-2">
                ${VERIFIED_TIER.stemForms.priceLow.toFixed(2)} to $
                {VERIFIED_TIER.stemForms.priceHigh.toFixed(2)}
              </td>
            </tr>
          </tbody>
        </table>
        <p className="mt-4 text-muted">
          Turnaround: {VERIFIED_TIER.turnaround}.
        </p>
        <h3 className="mt-8 text-xl font-bold">
          Inventory and triage engagement
        </h3>
        <p className="mt-2 max-w-prose">
          ${INVENTORY_ENGAGEMENT.price.toLocaleString('en-US')}{' '}
          {INVENTORY_ENGAGEMENT.unit}. {INVENTORY_ENGAGEMENT.includes}
        </p>
      </Section>

      <Section
        id="calculator"
        title="Estimate your backlog"
        lede="Compare our published rates with the manual rates institutions report."
      >
        <PricingCalculator />
      </Section>

      <Section id="faq" title="Questions" tone="surface">
        <dl className="max-w-prose space-y-6">
          {FAQ.map((item) => (
            <div key={item.q}>
              <dt className="text-lg font-bold">{item.q}</dt>
              <dd className="mt-1 text-muted">{item.a}</dd>
            </div>
          ))}
        </dl>
      </Section>
    </>
  );
}
