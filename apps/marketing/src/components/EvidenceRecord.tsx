import type { CSSProperties, ReactNode } from 'react';

// A sample of the product's own output: one document's evidence record, set as a document of
// record. The data is illustrative and the institution is fictional (example.edu is a reserved
// domain); the caption says so.

type Row = { term: string; detail: ReactNode; note?: string };

const ROWS: Row[] = [
  {
    term: 'Document',
    detail: 'Undergraduate catalog 2026–27',
    note: 'www.example.edu/registrar/catalog.pdf, 412 pages',
  },
  {
    term: 'Decision',
    detail: 'Remediate as PDF',
    note: 'In active use for enrollment; policy rule cited, version 3',
  },
  {
    term: 'PDF/UA-1',
    detail: <Pass>Passed in veraPDF</Pass>,
  },
  {
    term: 'Semantic checks',
    detail: '2,906 elements scored',
    note: '23 below threshold, sent to human review',
  },
  {
    term: 'Reviewer',
    detail: 'Signed off by the accessibility lead',
    note: 'October 9, 2026, 3:42 PM ET',
  },
  {
    term: 'Published',
    detail: 'Replaced in WordPress',
    note: 'Redirect verified; original kept as a download',
  },
];

function Pass({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 font-semibold text-ok">
      <svg
        viewBox="0 0 16 16"
        className="h-4 w-4"
        aria-hidden="true"
        focusable="false"
      >
        <circle
          cx="8"
          cy="8"
          r="7"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        />
        <path
          d="m5 8.2 2 2 4-4.4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {children}
    </span>
  );
}

function Seal() {
  return (
    <svg
      viewBox="0 0 120 120"
      className="record-seal h-24 w-24 text-accent sm:h-32 sm:w-32"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <path
          id="seal-ring"
          d="M60 60m-41 0a41 41 0 1 1 82 0a41 41 0 1 1-82 0"
        />
      </defs>
      <circle
        cx="60"
        cy="60"
        r="56"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <circle
        cx="60"
        cy="60"
        r="49"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
      />
      <circle
        cx="60"
        cy="60"
        r="31"
        className="fill-tint"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <text className="fill-current font-sans" fontSize="10" fontWeight="600">
        <textPath
          href="#seal-ring"
          startOffset="0"
          textLength="252"
          lengthAdjust="spacing"
        >
          Signed record • Verifiable without us •
        </textPath>
      </text>
      <path
        d="m47 60.5 9 9 17-18"
        fill="none"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function EvidenceRecord() {
  return (
    <figure className="relative isolate">
      <div className="relative rounded-sm border border-line bg-bg shadow-[0_1px_0_rgb(20_32_44/0.04),0_30px_60px_-30px_rgb(20_32_44/0.35)]">
        {/* Stacked sheets behind the record: one pack per document. */}
        <div
          aria-hidden="true"
          className="absolute inset-x-3 -bottom-2 -z-10 h-full rounded-sm border border-line bg-surface"
        />
        <div
          aria-hidden="true"
          className="absolute inset-x-6 -bottom-4 -z-20 h-full rounded-sm border border-line bg-surface"
        />

        <div className="flex items-start justify-between gap-4 border-b border-line px-6 pb-5 pt-6 sm:px-8">
          <div>
            <p className="font-display text-[1.3125rem] font-semibold leading-tight">
              Evidence record
            </p>
            <p className="mt-1 text-[0.9375rem] text-muted">
              Record 0412-7731 of 18,204 for www.example.edu
            </p>
          </div>
        </div>

        <dl className="px-6 py-2 sm:px-8">
          {ROWS.map((row, index) => (
            <div
              key={row.term}
              className="record-row grid gap-1 border-b border-line py-3.5 last:border-b-0 sm:grid-cols-[9.5rem_1fr] sm:gap-4"
              style={{ '--row': index } as CSSProperties}
            >
              <dt className="text-[0.9375rem] text-muted">{row.term}</dt>
              <dd>
                <span className="block font-semibold">{row.detail}</span>
                {row.note ? (
                  <span className="mt-0.5 block text-[0.9375rem] leading-snug text-muted">
                    {row.note}
                  </span>
                ) : null}
              </dd>
            </div>
          ))}
        </dl>

        <div
          className="record-row flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-t border-line bg-surface px-6 py-4 sm:px-8"
          style={{ '--row': ROWS.length } as CSSProperties}
        >
          <p className="text-[0.9375rem] text-muted">
            Signature{' '}
            <code className="font-mono text-[0.8125rem] text-ink">
              sha256:9f2c…a41e
            </code>
          </p>
          <p className="text-[0.9375rem] text-muted">Retained for 7 years</p>
        </div>

        <div className="pointer-events-none absolute -right-1 -top-9 sm:-right-8 sm:-top-10">
          <Seal />
        </div>
      </div>
      <figcaption className="mt-8 text-[0.9375rem] text-muted">
        A sample record. The data is illustrative and the institution is
        fictional.
      </figcaption>
    </figure>
  );
}
