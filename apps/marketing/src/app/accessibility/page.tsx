import type { Metadata } from 'next';
import { Container } from '@/components/Container';
import { SITE } from '@/content/site';

export const metadata: Metadata = {
  title: 'Accessibility statement',
  description:
    'Our commitment to WCAG 2.2 AA for this website and the product, how we test, known issues and how to report a barrier.',
};

export default function AccessibilityPage() {
  return (
    <Container className="py-14">
      <article className="max-w-copy">
        <h1 className="text-4xl font-bold tracking-tight">
          Accessibility statement
        </h1>
        <p className="mt-4 text-lg text-muted">
          A company that sells document accessibility has to be accessible
          itself. This statement covers this website and, as they ship, the
          dashboard and the documents we generate.
        </p>
        <h2 className="mt-8 text-2xl font-bold">Standard</h2>
        <p className="mt-2">
          We design and test against the Web Content Accessibility Guidelines
          (WCAG) 2.2 at level AA. The evidence packs and reports we produce as
          PDF are tagged and validated against PDF/UA-1.
        </p>
        <h2 className="mt-8 text-2xl font-bold">How we test</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>
            Automated checks with axe-core on every page in our build pipeline;
            a failure blocks release.
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
        <h2 className="mt-8 text-2xl font-bold">Conformance report</h2>
        <p className="mt-2">
          An accessibility conformance report (VPAT 2.5 format) for this site is
          published with the first production release and updated with each
          major release. The dashboard&apos;s report follows. Until then, this
          page lists known issues.
        </p>
        <h2 className="mt-8 text-2xl font-bold">Known issues</h2>
        <p className="mt-2">None recorded for this release of the website.</p>
        <h2 className="mt-8 text-2xl font-bold">Report a barrier</h2>
        <p className="mt-2">
          If anything on this site or in the product is hard to use with
          assistive technology, email{' '}
          <a
            href={`mailto:${SITE.contactEmail}?subject=Accessibility%20barrier`}
            className="underline underline-offset-4"
          >
            {SITE.contactEmail}
          </a>
          . We respond within two business days and fix confirmed barriers as a
          priority.
        </p>
      </article>
    </Container>
  );
}
