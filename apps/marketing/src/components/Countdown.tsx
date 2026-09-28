'use client';

import { useEffect, useState } from 'react';
import { DEADLINES } from '@/content/site';
import { daysUntil, formatLongDate } from '@/lib/dates';

// Renders on the client so the number is current; the server output reserves the space so
// nothing shifts when it fills in. No motion, no autoplay: a static number with a live region.
export function Countdown() {
  const [days, setDays] = useState<number | null>(null);

  useEffect(() => {
    setDays(daysUntil(DEADLINES.titleIILarge.date));
  }, []);

  return (
    <div
      className="rounded-lg border border-line bg-surface p-6"
      role="group"
      aria-labelledby="countdown-title"
    >
      <p
        id="countdown-title"
        className="text-sm font-semibold uppercase tracking-wide text-muted"
      >
        {DEADLINES.titleIILarge.label}
      </p>
      <p className="mt-2 text-4xl font-bold tabular-nums" aria-live="polite">
        {days === null ? (
          <span className="inline-block min-w-[6ch]">&nbsp;</span>
        ) : days >= 0 ? (
          <>
            {days.toLocaleString('en-US')}{' '}
            <span className="text-2xl font-semibold">days</span>
          </>
        ) : (
          'In force'
        )}
      </p>
      <p className="mt-1 text-muted">
        Compliance date {formatLongDate(DEADLINES.titleIILarge.date)}. Smaller
        entities: {formatLongDate(DEADLINES.titleIISmall.date)}. HHS Section
        504: {formatLongDate(DEADLINES.hhs504.date)}.
      </p>
    </div>
  );
}
