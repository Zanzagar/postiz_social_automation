import { PlatformDot } from "@/components/pasture";
import { PLATFORMS } from "@/lib/platforms";
import { cn } from "@/lib/utils";

interface PlatformPickerProps {
  value: string[];
  onChange: (platforms: string[]) => void;
}

/** Multi-select platform toggle row (editor + use flow). */
export function PlatformPicker({ value, onChange }: PlatformPickerProps) {
  function toggle(id: string) {
    onChange(
      value.includes(id) ? value.filter((p) => p !== id) : [...value, id],
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {PLATFORMS.map((p) => {
        const selected = value.includes(p.id);
        return (
          <button
            key={p.id}
            type="button"
            aria-pressed={selected}
            onClick={() => toggle(p.id)}
            className={cn(
              "fr t-body-sm flex h-7 items-center gap-1.5 rounded-md border px-2.5 transition-colors",
              selected
                ? "border-sage-500 bg-sage-500 text-white"
                : "bg-card border-hair ink hover:border-sage-300",
            )}
          >
            <PlatformDot id={p.id} size={10} />
            {p.label}
          </button>
        );
      })}
    </div>
  );
}
