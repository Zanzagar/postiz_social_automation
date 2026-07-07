/**
 * Read-only label / value / hint row used by the Brand voice card
 * (supporting.jsx SettingRow).
 */
interface SettingRowProps {
  label: string;
  value: string;
  hint?: string;
}

export function SettingRow({ label, value, hint }: SettingRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5">
      <div className="w-32 shrink-0">
        <div className="t-label ink-muted">{label}</div>
      </div>
      <div className="flex-1">
        <div className="t-body ink">{value}</div>
        {hint && <div className="t-caption ink-muted mt-0.5 italic">{hint}</div>}
      </div>
    </div>
  );
}
