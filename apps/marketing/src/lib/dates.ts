const MS_PER_DAY = 24 * 60 * 60 * 1000;

/** Whole days from `now` until the ISO date (UTC midnight). Negative when the date has passed. */
export function daysUntil(isoDate: string, now: Date = new Date()): number {
  const target = Date.parse(`${isoDate}T00:00:00Z`);
  return Math.ceil((target - now.getTime()) / MS_PER_DAY);
}

export function formatLongDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC',
  });
}
