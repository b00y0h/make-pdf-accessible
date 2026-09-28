'use client';

import { FormEvent, useId, useState } from 'react';
import { Button } from '@/components/Button';
import { FormField, inputClass } from '@/components/FormField';
import { postJson } from '@/lib/api';

type State =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'done'; email: string }
  | { kind: 'error'; message: string };

const INSTITUTION_TYPES = [
  'Public university or college',
  'Community college',
  'Private university or college',
  'K-12 district',
  'City, county or special district',
  'Healthcare',
  'Other',
];

function normalizeUrl(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const withScheme = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
  try {
    const url = new URL(withScheme);
    if (!url.hostname.includes('.')) return null;
    return url.origin;
  } catch {
    return null;
  }
}

export function SiteReportForm() {
  const id = useId();
  const [state, setState] = useState<State>({ kind: 'idle' });
  const [errors, setErrors] = useState<{
    site?: string;
    email?: string;
    consent?: string;
  }>({});

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const site = normalizeUrl(String(data.get('site') ?? ''));
    const email = String(data.get('email') ?? '').trim();
    const institutionType = String(data.get('institution_type') ?? '');
    const consent = data.get('consent') === 'on';
    const honeypot = String(data.get('company_website') ?? '');

    const next: typeof errors = {};
    if (!site)
      next.site =
        'Enter your institution website, for example www.example.edu.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      next.email = 'Enter a work email address.';
    if (!consent)
      next.consent = 'Please confirm you may request a crawl of this site.';
    setErrors(next);
    if (Object.keys(next).length > 0) {
      const first = Object.keys(next)[0];
      form.querySelector<HTMLElement>(`[name="${first}"]`)?.focus();
      return;
    }
    if (honeypot) {
      // Bots fill hidden fields; humans never see this one. Pretend success without a request.
      setState({ kind: 'done', email });
      return;
    }

    setState({ kind: 'submitting' });
    const result = await postJson<{ report_id: string }>(
      '/v1/public/site-report',
      {
        site_url: site,
        email,
        institution_type: institutionType,
        consent: true,
        source: 'marketing-site',
      }
    );
    if (result.ok) {
      setState({ kind: 'done', email });
      return;
    }
    if (result.status === 429) {
      setState({
        kind: 'error',
        message:
          'A report for this site was requested recently. You can request another one tomorrow, or email us and we will run it now.',
      });
      return;
    }
    setState({ kind: 'error', message: result.message });
  }

  if (state.kind === 'done') {
    return (
      <div
        className="rounded-lg border border-line bg-surface p-6"
        role="status"
      >
        <h3 className="text-xl font-bold">We are crawling your site</h3>
        <p className="mt-2">
          Your report will arrive at <strong>{state.email}</strong> within two
          hours. It lists every PDF we found, how many pages, which ones look
          scanned or untagged, and an estimated cost for each path. We keep only
          the metadata needed for the report.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      className="space-y-5"
      aria-describedby={`${id}-intro`}
    >
      <p id={`${id}-intro`} className="text-muted">
        Free, no credit card. We crawl up to 5,000 PDFs from your public site,
        following your robots.txt, and email you the inventory.
      </p>

      <FormField
        id={`${id}-site`}
        label="Institution website"
        error={errors.site}
      >
        <input
          id={`${id}-site`}
          name="site"
          type="url"
          inputMode="url"
          autoComplete="url"
          placeholder="www.example.edu"
          className={inputClass}
          aria-invalid={errors.site ? true : undefined}
          aria-describedby={errors.site ? `${id}-site-error` : undefined}
          required
        />
      </FormField>

      <FormField id={`${id}-email`} label="Work email" error={errors.email}>
        <input
          id={`${id}-email`}
          name="email"
          type="email"
          autoComplete="email"
          className={inputClass}
          aria-invalid={errors.email ? true : undefined}
          aria-describedby={errors.email ? `${id}-email-error` : undefined}
          required
        />
      </FormField>

      <FormField id={`${id}-type`} label="Institution type">
        <select
          id={`${id}-type`}
          name="institution_type"
          className={inputClass}
          defaultValue={INSTITUTION_TYPES[0]}
        >
          {INSTITUTION_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </FormField>

      <div className="hp-field" aria-hidden="true">
        <label htmlFor={`${id}-company`}>Company website</label>
        <input
          id={`${id}-company`}
          name="company_website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      <div className="flex items-start gap-3">
        <input
          id={`${id}-consent`}
          name="consent"
          type="checkbox"
          className="mt-1 h-5 w-5"
          aria-invalid={errors.consent ? true : undefined}
          aria-describedby={errors.consent ? `${id}-consent-error` : undefined}
        />
        <label htmlFor={`${id}-consent`}>
          I am authorized to request a crawl of this website and agree to
          receive the report by email.
        </label>
      </div>
      {errors.consent ? (
        <p
          id={`${id}-consent-error`}
          className="text-sm font-semibold text-warn"
          role="alert"
        >
          {errors.consent}
        </p>
      ) : null}

      {state.kind === 'error' ? (
        <p className="rounded-md border border-warn p-3 text-warn" role="alert">
          {state.message}
        </p>
      ) : null}

      <Button disabled={state.kind === 'submitting'}>
        {state.kind === 'submitting'
          ? 'Starting the crawl…'
          : 'Send me the free report'}
      </Button>
    </form>
  );
}
