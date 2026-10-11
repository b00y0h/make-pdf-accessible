'use client';

import { useEffect, useState } from 'react';
import { DEADLINES } from '@/content/site';
import { daysUntil, formatLongDate } from '@/lib/dates';

// The three compliance dates on one axis, with today marked. "Today" and the day counts render
// on the client so they are current; the server output reserves their space so nothing shifts.
// No motion: the axis is static and the counts sit in a polite live region.

const AXIS_START = '2026-01-01';
const AXIS_END = '2029-01-01';
const YEARS = ['2026', '2027', '2028', '2029'];

const MARKS = [
  {
    ...DEADLINES.titleIILarge,
    key: 'large',
    short: 'Title II, 50,000+',
    side: 'above',
  },
  { ...DEADLINES.hhs504, key: 'hhs', short: 'HHS Section 504', side: 'below' },
  {
    ...DEADLINES.titleIISmall,
    key: 'small',
    short: 'Title II, under 50,000',
    side: 'above',
  },
] as const;

function position(isoDate: string): number {
  const start = Date.parse(`${AXIS_START}T00:00:00Z`);
  const end = Date.parse(`${AXIS_END}T00:00:00Z`);
  const at = Date.parse(`${isoDate}T00:00:00Z`);
  return Math.min(100, Math.max(0, ((at - start) / (end - start)) * 100));
}

function shortDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  });
}

export function DeadlineTimeline() {
  const [today, setToday] = useState<string | null>(null);

  useEffect(() => {
    setToday(new Date().toISOString().slice(0, 10));
  }, []);

  const days = (iso: string) => (today ? daysUntil(iso) : null);
  const todayAt = today ? position(today) : null;

  return (
    <div>
      {/* The axis is a picture of the list below it, so assistive technology reads the list. */}
      <div
        aria-hidden="true"
        className="relative pb-14 pt-12 sm:pb-20 sm:pt-20"
      >
        <div className="relative h-3 rounded-full bg-surface ring-1 ring-line ring-inset">
          {todayAt !== null ? (
            <div
              className="absolute inset-y-0 left-0 rounded-l-full bg-[repeating-linear-gradient(135deg,var(--color-line)_0_2px,transparent_2px_7px)]"
              style={{ width: `${todayAt}%` }}
            />
          ) : null}
        </div>

        {YEARS.map((year, index) => {
          const at = position(`${year}-01-01`);
          // Year labels sit to the right of their tick, so the axis never pushes past the
          // container edge; the closing tick needs no label.
          return (
            <div
              key={year}
              className="absolute top-1/2"
              style={{ left: `${at}%` }}
            >
              <div className="h-3 w-px -translate-x-1/2 -translate-y-1/2 bg-field" />
              {index < YEARS.length - 1 ? (
                <p className="ml-1.5 mt-0.5 text-[0.8125rem] tabular-nums text-muted">
                  {year}
                </p>
              ) : null}
            </div>
          );
        })}

        {MARKS.map((mark) => {
          const at = position(mark.date);
          const above = mark.side === 'above';
          return (
            <div
              key={mark.key}
              className="absolute top-1/2"
              style={{ left: `${at}%` }}
            >
              <div
                className={`absolute left-0 w-0.5 -translate-x-1/2 bg-accent ${above ? 'bottom-0 h-7 sm:h-16' : 'top-0 h-7 sm:h-16'}`}
              />
              <div className="absolute left-0 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bg bg-accent" />
              <p
                className={`absolute hidden whitespace-nowrap pl-2.5 text-[0.875rem] leading-tight sm:block ${above ? 'bottom-9 sm:bottom-10' : 'top-9 sm:top-10'}`}
              >
                <span className="block font-semibold text-ink">
                  {shortDate(mark.date)}
                </span>
                <span className="block text-muted">{mark.short}</span>
              </p>
            </div>
          );
        })}

        {todayAt !== null ? (
          <div className="absolute top-1/2" style={{ left: `${todayAt}%` }}>
            <div className="absolute left-0 top-0 h-6 w-px -translate-x-1/2 bg-ink sm:h-9" />
            <div className="absolute left-0 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-ink" />
            <p className="absolute left-0 top-7 -translate-x-1/2 whitespace-nowrap text-[0.875rem] font-semibold sm:top-10">
              Today
            </p>
          </div>
        ) : null}
      </div>

      <ol className="grid gap-8 border-t border-line pt-8 md:grid-cols-3">
        {MARKS.map((mark) => {
          const remaining = days(mark.date);
          return (
            <li key={mark.key}>
              <p className="font-display text-[1.75rem] font-medium leading-none tabular-nums">
                <span aria-live="polite">
                  {remaining === null ? (
                    <span className="inline-block min-w-[5ch]">&nbsp;</span>
                  ) : remaining >= 0 ? (
                    `${remaining.toLocaleString('en-US')} days`
                  ) : (
                    'In force'
                  )}
                </span>
              </p>
              <p className="mt-3 font-semibold">{formatLongDate(mark.date)}</p>
              <p className="mt-1 text-muted">{mark.label}</p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
