'use client';

import {
  ChangeEvent,
  DragEvent,
  FormEvent,
  useId,
  useRef,
  useState,
} from 'react';
import { Button } from '@/components/Button';
import { getJson, postJson, putFile } from '@/lib/api';

const MAX_BYTES = 25 * 1024 * 1024;

type CheckResult = {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  summary?: {
    page_count: number;
    has_text_layer: boolean;
    is_tagged: boolean;
    title: string | null;
    language: string | null;
    is_form: boolean;
    claims_pdfua: boolean;
    estimated_cost: {
      convert_html: number | null;
      remediate_pdf: number;
      verified: number;
    };
  };
  error?: string;
};

type State =
  | { kind: 'idle' }
  | { kind: 'uploading' }
  | { kind: 'checking' }
  | { kind: 'done'; result: CheckResult }
  | { kind: 'error'; message: string };

const ROWS: {
  key: keyof NonNullable<CheckResult['summary']>;
  label: string;
  explain: string;
}[] = [
  {
    key: 'page_count',
    label: 'Pages',
    explain: 'Cost estimates scale with pages.',
  },
  {
    key: 'has_text_layer',
    label: 'Text layer',
    explain:
      'Without one the document is an image and needs OCR before anything else.',
  },
  {
    key: 'is_tagged',
    label: 'Structure tags',
    explain:
      'Tags exist. This does not tell us whether they are correct; that is what validation and review are for.',
  },
  {
    key: 'title',
    label: 'Title',
    explain:
      'Screen readers announce the title; an empty one reads as the file name.',
  },
  {
    key: 'language',
    label: 'Language',
    explain:
      'Assistive technology needs the language to pronounce text correctly.',
  },
  {
    key: 'is_form',
    label: 'Fillable form',
    explain: 'Forms stay PDF and need labeled fields and a tab order.',
  },
  {
    key: 'claims_pdfua',
    label: 'PDF/UA claim',
    explain: 'A claim in the metadata, not a validation result.',
  },
];

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Not set';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}

export function PdfCheckForm() {
  const id = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [state, setState] = useState<State>({ kind: 'idle' });

  function acceptFile(candidate: File | undefined) {
    if (!candidate) return;
    if (
      candidate.type !== 'application/pdf' &&
      !candidate.name.toLowerCase().endsWith('.pdf')
    ) {
      setFileError('Choose a PDF file.');
      setFile(null);
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setFileError(
        'The file is larger than 25 MB. Sign in to check larger documents.'
      );
      setFile(null);
      return;
    }
    setFileError(null);
    setFile(candidate);
  }

  function onChange(event: ChangeEvent<HTMLInputElement>) {
    acceptFile(event.target.files?.[0]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    acceptFile(event.dataTransfer.files?.[0]);
  }

  async function poll(checkId: string): Promise<CheckResult | null> {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      const result = await getJson<CheckResult>(
        `/v1/public/pdf-check/${checkId}`
      );
      if (!result.ok) return null;
      if (result.data.status === 'completed' || result.data.status === 'failed')
        return result.data;
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    return null;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError('Choose a PDF file to check.');
      inputRef.current?.focus();
      return;
    }
    setState({ kind: 'uploading' });
    const presign = await postJson<{ upload_url: string; check_id: string }>(
      '/v1/public/pdf-check/presign',
      {
        filename: file.name,
        byte_size: file.size,
      }
    );
    if (!presign.ok) {
      setState({
        kind: 'error',
        message:
          presign.status === 429
            ? 'You have used today’s five free checks. Sign in for more, or come back tomorrow.'
            : presign.message,
      });
      return;
    }
    const uploaded = await putFile(presign.data.upload_url, file);
    if (!uploaded) {
      setState({
        kind: 'error',
        message: 'The upload did not complete. Please try again.',
      });
      return;
    }
    setState({ kind: 'checking' });
    const started = await postJson<CheckResult>('/v1/public/pdf-check', {
      check_id: presign.data.check_id,
    });
    if (!started.ok) {
      setState({ kind: 'error', message: started.message });
      return;
    }
    const final = await poll(presign.data.check_id);
    if (!final || final.status === 'failed') {
      setState({
        kind: 'error',
        message: final?.error ?? 'The check did not finish. Please try again.',
      });
      return;
    }
    setState({ kind: 'done', result: final });
  }

  const busy = state.kind === 'uploading' || state.kind === 'checking';

  return (
    <div className="space-y-6">
      <form onSubmit={onSubmit} noValidate>
        <div
          onDragOver={(event) => event.preventDefault()}
          onDrop={onDrop}
          className="rounded-lg border-2 border-dashed border-line p-6 text-center"
        >
          <label htmlFor={`${id}-file`} className="block font-semibold">
            Choose a PDF (up to 25 MB)
          </label>
          <p className="mt-1 text-sm text-muted">
            Drag a file here or use the button. Five checks per day.
          </p>
          <input
            ref={inputRef}
            id={`${id}-file`}
            name="file"
            type="file"
            accept="application/pdf,.pdf"
            onChange={onChange}
            className="mx-auto mt-4 block"
            aria-describedby={fileError ? `${id}-file-error` : undefined}
            aria-invalid={fileError ? true : undefined}
          />
          {file ? (
            <p className="mt-2 text-sm" aria-live="polite">
              Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
            </p>
          ) : null}
          {fileError ? (
            <p
              id={`${id}-file-error`}
              className="mt-2 text-sm font-semibold text-warn"
              role="alert"
            >
              {fileError}
            </p>
          ) : null}
        </div>
        <Button disabled={busy} className="mt-4">
          {state.kind === 'uploading'
            ? 'Uploading…'
            : state.kind === 'checking'
              ? 'Checking…'
              : 'Check this PDF'}
        </Button>
        <p className="mt-4 text-sm text-muted" aria-live="polite">
          {busy ? 'This usually takes under a minute.' : ''}
        </p>
      </form>

      {state.kind === 'error' ? (
        <p className="rounded-md border border-warn p-3 text-warn" role="alert">
          {state.message}
        </p>
      ) : null}

      {state.kind === 'done' && state.result.summary ? (
        <div role="region" aria-labelledby={`${id}-results`}>
          <h3 id={`${id}-results`} className="text-xl font-bold">
            What we found
          </h3>
          <p className="mt-1 text-muted">
            These checks describe the file. They do not prove that it is, or is
            not, accessible; a full validation and review does that, and the
            result comes with an evidence pack.
          </p>
          <table className="mt-4 w-full border-collapse text-left">
            <caption className="sr-only-focusable">
              Summary of the uploaded PDF
            </caption>
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className="py-2 pr-4">
                  Check
                </th>
                <th scope="col" className="py-2 pr-4">
                  Result
                </th>
                <th scope="col" className="py-2">
                  What it means
                </th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.key} className="border-b border-line align-top">
                  <th scope="row" className="py-2 pr-4 font-semibold">
                    {row.label}
                  </th>
                  <td className="py-2 pr-4">
                    {formatValue(state.result.summary?.[row.key])}
                  </td>
                  <td className="py-2 text-muted">{row.explain}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-4">
            Estimated cost on our published prices: HTML conversion{' '}
            {state.result.summary.estimated_cost.convert_html === null
              ? 'not recommended for this document'
              : `$${state.result.summary.estimated_cost.convert_html.toFixed(2)}`}
            , PDF remediation $
            {state.result.summary.estimated_cost.remediate_pdf.toFixed(2)}, with
            human verification $
            {state.result.summary.estimated_cost.verified.toFixed(2)}.
          </p>
        </div>
      ) : null}
    </div>
  );
}
