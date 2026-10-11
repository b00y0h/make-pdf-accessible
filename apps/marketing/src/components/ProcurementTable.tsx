import { PROCUREMENT } from '@/content/site';

type State = (typeof PROCUREMENT)[number]['state'];

// The status text carries the meaning; the mark beside it is a visual aid only.
const MARK: Record<State, string> = {
  available: 'bg-accent',
  progress: 'bg-accent/50',
  scheduled: 'border-2 border-accent',
  planned: 'border-2 border-field',
};

export function ProcurementTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <caption className="sr-only-focusable">
          Status of procurement and compliance items
        </caption>
        <thead>
          <tr className="border-b border-ink text-[0.9375rem]">
            <th scope="col" className="py-3 pr-6 font-semibold">
              Item
            </th>
            <th scope="col" className="py-3 font-semibold">
              Status today
            </th>
          </tr>
        </thead>
        <tbody>
          {PROCUREMENT.map((row) => (
            <tr key={row.item} className="border-b border-line align-top">
              <th scope="row" className="py-4 pr-6 font-normal">
                {row.item}
              </th>
              <td className="py-4">
                <span className="flex items-start gap-3 text-muted">
                  <span
                    aria-hidden="true"
                    className={`mt-[0.45em] inline-block h-2.5 w-2.5 shrink-0 rounded-full ${MARK[row.state]}`}
                  />
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
