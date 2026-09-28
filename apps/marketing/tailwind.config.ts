import type { Config } from 'tailwindcss';

// Colors reference CSS custom properties defined in src/app/globals.css so light and dark
// themes share one token set and contrast is controlled in one place.
const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bg: 'rgb(var(--color-bg) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        muted: 'rgb(var(--color-muted) / <alpha-value>)',
        line: 'rgb(var(--color-line) / <alpha-value>)',
        accent: 'rgb(var(--color-accent) / <alpha-value>)',
        'accent-ink': 'rgb(var(--color-accent-ink) / <alpha-value>)',
        warn: 'rgb(var(--color-warn) / <alpha-value>)',
        ok: 'rgb(var(--color-ok) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      maxWidth: {
        content: '72rem',
        prose: '42rem',
      },
    },
  },
  plugins: [],
};

export default config;
