'use client';

import { useId, useState } from 'react';
import { CALCULATOR_RATES } from '@/content/site';

const money = (value: number) =>
  value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  });

export function PricingCalculator() {
  const id = useId();
  const [pages, setPages] = useState(10000);
  const [verifiedShare, setVerifiedShare] = useState(20);

  const verifiedPages = Math.round((pages * verifiedShare) / 100);
  const automatedPages = pages - verifiedPages;
  const low =
    automatedPages * CALCULATOR_RATES.automatedLow +
    verifiedPages * CALCULATOR_RATES.verifiedFlagged;
  const high =
    automatedPages * CALCULATOR_RATES.automatedHigh +
    verifiedPages * CALCULATOR_RATES.verifiedFlagged;
  const manualLow = pages * CALCULATOR_RATES.manualLow;
  const manualHigh = pages * CALCULATOR_RATES.manualHigh;

  return (
    <div className="rounded-lg border border-line bg-surface p-6">
      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <label htmlFor={`${id}-pages`} className="block font-semibold">
            Pages to remediate or convert
          </label>
          <input
            id={`${id}-pages`}
            type="number"
            min={0}
            step={100}
            value={pages}
            onChange={(event) =>
              setPages(Math.max(0, Number(event.target.value) || 0))
            }
            className="mt-1 block w-full min-h-[44px] rounded-md border border-line bg-bg px-3 py-2"
          />
        </div>
        <div>
          <label htmlFor={`${id}-verified`} className="block font-semibold">
            Share sent to human review: {verifiedShare}%
          </label>
          <input
            id={`${id}-verified`}
            type="range"
            min={0}
            max={100}
            step={5}
            value={verifiedShare}
            onChange={(event) => setVerifiedShare(Number(event.target.value))}
            className="mt-3 block w-full"
            aria-valuetext={`${verifiedShare} percent`}
          />
          <p className="mt-1 text-sm text-muted">
            Scanned, STEM and complex-table documents typically need review.
          </p>
        </div>
      </div>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2" aria-live="polite">
        <div className="rounded-md border border-line bg-bg p-4">
          <dt className="text-sm font-semibold uppercase tracking-wide text-muted">
            With Make PDF Accessible
          </dt>
          <dd className="mt-1 text-2xl font-bold">
            {money(low)} to {money(high)}
          </dd>
          <dd className="text-sm text-muted">
            {automatedPages.toLocaleString('en-US')} automated pages at $
            {CALCULATOR_RATES.automatedLow.toFixed(2)} to $
            {CALCULATOR_RATES.automatedHigh.toFixed(2)};{' '}
            {verifiedPages.toLocaleString('en-US')} verified pages at $
            {CALCULATOR_RATES.verifiedFlagged.toFixed(2)}.
          </dd>
        </div>
        <div className="rounded-md border border-line bg-bg p-4">
          <dt className="text-sm font-semibold uppercase tracking-wide text-muted">
            Typical manual remediation
          </dt>
          <dd className="mt-1 text-2xl font-bold">
            {money(manualLow)} to {money(manualHigh)}
          </dd>
          <dd className="text-sm text-muted">
            ${CALCULATOR_RATES.manualLow.toFixed(2)} to $
            {CALCULATOR_RATES.manualHigh.toFixed(2)} per page, the range
            universities report paying vendors.
          </dd>
        </div>
      </dl>
      <p className="mt-4 text-sm text-muted">
        Estimates only. Plan fees include page allowances; overage rates apply
        above them. Delete and archive decisions cost nothing.
      </p>
    </div>
  );
}
