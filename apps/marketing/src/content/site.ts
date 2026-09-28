// Single source of truth for navigation, dates and prices shown on the marketing site.
// Prices mirror docs/business/BUSINESS-PLAN.md section 5; keep both in sync.

export const SITE = {
  name: 'Make PDF Accessible',
  url: process.env.NEXT_PUBLIC_SITE_URL ?? 'https://makepdfaccessible.com',
  appUrl:
    process.env.NEXT_PUBLIC_APP_URL ??
    'https://dashboard.makepdfaccessible.com',
  apiBaseUrl:
    process.env.NEXT_PUBLIC_API_BASE_URL ?? 'https://api.makepdfaccessible.com',
  tagline: 'Every document on your site, made accessible, with proof.',
  description:
    'Inventory every PDF, decide what the ADA Title II rule requires for each one, fix or convert it, publish it back, and keep an evidence pack for every document.',
  contactEmail: 'hello@makepdfaccessible.com',
  securityEmail: 'security@makepdfaccessible.com',
  crawlerUserAgent:
    'MakePDFAccessibleBot/1.0 (+https://makepdfaccessible.com/bot)',
} as const;

export const DEADLINES = {
  titleIILarge: {
    label: 'ADA Title II, entities serving 50,000+ people',
    date: '2027-04-26',
  },
  titleIISmall: {
    label: 'ADA Title II, entities under 50,000 and special districts',
    date: '2028-04-26',
  },
  hhs504: {
    label: 'HHS Section 504, recipients with 15+ employees',
    date: '2027-05-11',
  },
} as const;

export const NAV = [
  { href: '/product/', label: 'Product' },
  { href: '/pricing/', label: 'Pricing' },
  { href: '/free-report/', label: 'Free website report' },
  { href: '/check/', label: 'Free PDF check' },
  { href: '/trust/', label: 'Trust' },
] as const;

export const FOOTER_LINKS = {
  product: [
    { href: '/product/', label: 'How it works' },
    { href: '/pricing/', label: 'Pricing' },
    { href: '/free-report/', label: 'Free website report' },
    { href: '/check/', label: 'Free PDF check' },
    { href: '/pilot/', label: 'Request a pilot' },
  ],
  trust: [
    { href: '/trust/', label: 'Trust center' },
    { href: '/accessibility/', label: 'Accessibility statement' },
    { href: '/security/', label: 'Security' },
    { href: '/bot/', label: 'Our crawler' },
  ],
} as const;

export type Plan = {
  id: string;
  name: string;
  price: string;
  cadence: string;
  pagesIncluded: number | null;
  overage: string | null;
  summary: string;
  features: string[];
  cta: { label: string; href: string };
};

export const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    cadence: '',
    pagesIncluded: 0,
    overage: null,
    summary: 'Find out what you have.',
    features: [
      'WordPress inventory plugin',
      'One free website inventory report (up to 5,000 PDFs)',
      '5 single-PDF checks per day',
      'No credit card',
    ],
    cta: { label: 'Get the free report', href: '/free-report/' },
  },
  {
    id: 'team',
    name: 'Team',
    price: '$6,000',
    cadence: 'per year',
    pagesIncluded: 6000,
    overage: '$0.95 per page',
    summary: 'A department, a small district, a small town.',
    features: [
      '6,000 automated pages per year',
      '1 domain, 5 users',
      'WordPress connector with publish-back',
      'Evidence pack for every document',
      'Email support',
    ],
    cta: { label: 'Start with a pilot', href: '/pilot/' },
  },
  {
    id: 'campus',
    name: 'Campus',
    price: '$30,000',
    cadence: 'per year',
    pagesIncluded: 50000,
    overage: '$0.60 per page',
    summary: 'One institution, every site.',
    features: [
      '50,000 automated pages per year',
      'Unlimited domains',
      'Single sign-on (SAML, Entra ID, Google)',
      'Drupal and LMS (LTI 1.3) connectors',
      'API, webhooks and the Accessible Link',
      'Priority queue and a 99.5% SLA',
    ],
    cta: { label: 'Start with a pilot', href: '/pilot/' },
  },
  {
    id: 'system',
    name: 'System',
    price: 'from $100,000',
    cadence: 'per year',
    pagesIncluded: 250000,
    overage: 'negotiated',
    summary: 'Systems, states and large districts.',
    features: [
      '250,000+ automated pages per year',
      'Multi-institution tenancy',
      'Dedicated encryption keys or a dedicated AWS account',
      '99.9% SLA, custom data processing terms',
      'Cooperative-contract pricing',
    ],
    cta: { label: 'Talk to us', href: '/pilot/' },
  },
];

export const VERIFIED_TIER = {
  flagged: { label: 'Human review of flagged elements', price: 2.5 },
  full: { label: 'Full human review, every page', price: 4.0 },
  stemForms: {
    label: 'STEM (MathML) and fillable forms',
    priceLow: 6.0,
    priceHigh: 8.0,
  },
  turnaround: '5 business days standard; rush available',
} as const;

export const INVENTORY_ENGAGEMENT = {
  price: 2500,
  unit: 'per domain',
  includes:
    'Crawl, triage plan, cost estimate, quarterly re-crawl. Credited to a Campus plan.',
} as const;

// Per-page rates used by the calculator, in dollars.
export const CALCULATOR_RATES = {
  automatedLow: 0.6,
  automatedHigh: 0.95,
  verifiedFlagged: 2.5,
  manualLow: 2.5,
  manualHigh: 12.0,
} as const;

export const STAGES = [
  {
    name: 'Inventory',
    text: 'Crawl your sites, read your CMS media libraries and LMS courses, import scanner exports. Every PDF, with pages, owner, links and usage.',
  },
  {
    name: 'Triage',
    text: 'Apply the rule to each document: delete, archive, convert to HTML, remediate as PDF, or send to review. Each decision has a rationale and a price.',
  },
  {
    name: 'Remediate or convert',
    text: 'Page-parallel remediation with licensed tagging engines and independent PDF/UA validation, or semantic HTML for text-heavy documents.',
  },
  {
    name: 'Publish',
    text: 'The result goes back where people find it: WordPress, Drupal, the LMS, or an Accessible Link for any URL, with redirects and the original kept.',
  },
  {
    name: 'Prove',
    text: 'A signed evidence pack per document: validator output, semantic checks, reviewer sign-off, tool versions, timestamps.',
  },
  {
    name: 'Maintain',
    text: 'New uploads are handled automatically, sites are re-crawled on a schedule, and drift is reported before anyone complains.',
  },
] as const;
