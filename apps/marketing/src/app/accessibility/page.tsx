import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { PageHeader } from '@/components/PageHeader';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Accessibility statement',
  description:
    'Our commitment to WCAG 2.2 AA for this website and the product, how we test, known issues and how to report a barrier.',
};

export default function AccessibilityPage() {
  return (
    <>
      <PageHeader
        title="Accessibility statement"
        lede="A company that sells document accessibility has to be accessible itself. This statement covers this website and, as they ship, the dashboard and the documents we generate."
      />
      <Container className="py-16 lg:py-24">
        <article className="record-copy max-w-copy">
          <h2>Standard</h2>
          <p>
            We design and test against the Web Content Accessibility Guidelines
            (WCAG) 2.2 at level AA. The evidence packs and reports we produce as
            PDF are tagged and validated against PDF/UA-1.
          </p>
          <h2>How we test</h2>
          <ul>
            <li>
              Automated checks with axe-core on every page in our build
              pipeline; a failure blocks release.
            </li>
            <li>Keyboard-only walkthroughs of every page and form.</li>
            <li>
              Screen reader testing with NVDA on Windows and VoiceOver on macOS
              and iOS before launch and each quarter.
            </li>
            <li>
              Color contrast verified in both light and dark themes; motion
              respects the reduced-motion preference.
            </li>
          </ul>
          <h2>Conformance report</h2>
          <p>
            An accessibility conformance report (VPAT 2.5 format) for this site
            is published with the first production release and updated with each
            major release. The dashboard&apos;s report follows. Until then, this
            page lists known issues.
          </p>
          <h2>Known issues</h2>
          <p>None recorded for this release of the website.</p>
          <h2>Report a barrier</h2>
          <p>
            If anything on this site or in the product is hard to use with
            assistive technology, email{' '}
            <a
              href={`mailto:${SITE.contactEmail}?subject=Accessibility%20barrier`}
            >
              {SITE.contactEmail}
            </a>
            . We respond within two business days and fix confirmed barriers as
            a priority.
          </p>
        </article>
      </Container>
    </>
  );
}
