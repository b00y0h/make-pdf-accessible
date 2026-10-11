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
    <div className="space-y-1.5">
      <label htmlFor={id} className="block font-semibold">
        {label}
      </label>
      {hint ? (
        <p id={`${id}-hint`} className="text-[0.9375rem] text-muted">
          {hint}
        </p>
      ) : null}
      {children}
      {error ? (
        <p
          id={`${id}-error`}
          className="text-[0.9375rem] font-semibold text-warn"
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}

export const inputClass =
  'block w-full min-h-[48px] rounded-sm border border-field bg-bg px-3.5 py-2 text-ink placeholder:text-muted hover:border-ink';
