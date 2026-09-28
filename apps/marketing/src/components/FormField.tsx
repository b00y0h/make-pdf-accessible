import type { ReactNode } from 'react';

export function FormField({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block font-semibold">
        {label}
      </label>
      {hint ? (
        <p id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
      {children}
      {error ? (
        <p
          id={`${id}-error`}
          className="text-sm font-semibold text-warn"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}

export const inputClass =
  'block w-full min-h-[44px] rounded-md border border-line bg-bg px-3 py-2 text-ink placeholder:text-muted';
