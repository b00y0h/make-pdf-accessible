import type { Metadata, Viewport } from 'next';
import { Besley, Public_Sans } from 'next/font/google';
import type { ReactNode } from 'react';
import { SkipLink } from '@/components/SkipLink';
import { SiteHeader } from '@/components/SiteHeader';
import { SiteFooter } from '@/components/SiteFooter';
import { SITE } from '@/content/site';
import './globals.css';

// Self-hosted at build time by next/font, so the static export makes no third-party font
// requests. Besley (a Clarendon revival) sets headings; Public Sans (the US Web Design
// System face) sets everything else.
const besley = Besley({
  subsets: ['latin'],
  weight: 'variable',
  display: 'swap',
  variable: '--font-besley',
});

const publicSans = Public_Sans({
  subsets: ['latin'],
  weight: 'variable',
  display: 'swap',
  variable: '--font-public-sans',
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: {
    default: `${SITE.name}: document accessibility for institutions`,
    template: `%s | ${SITE.name}`,
  },
  description: SITE.description,
  openGraph: {
    type: 'website',
    siteName: SITE.name,
    title: SITE.name,
    description: SITE.description,
    url: SITE.url,
  },
  twitter: {
    card: 'summary',
    title: SITE.name,
    description: SITE.description,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0e1922' },
  ],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${besley.variable} ${publicSans.variable}`}
    >
      <body className="flex min-h-screen flex-col">
        <SkipLink />
        <SiteHeader />
        <main id="main" tabIndex={-1} className="flex-1 focus:outline-hidden">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
