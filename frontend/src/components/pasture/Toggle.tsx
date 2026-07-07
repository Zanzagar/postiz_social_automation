import { cn } from "@/lib/utils";

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  size?: "sm" | "md";
  disabled?: boolean;
  "aria-label"?: string;
  className?: string;
}

/**
 * The ONE toggle (manifest P2 resolution). Real button with role="switch",
 * aria-checked, and the .fr focus ring. sage-500 when on.
 */
export function Toggle({
  checked,
  onChange,
  size = "md",
  disabled,
  "aria-label": ariaLabel,
  className,
}: ToggleProps) {
  const dims =
    size === "sm"
      ? { track: "h-4 w-7", knob: "h-3 w-3", on: "translate-x-3.5", off: "translate-x-0.5" }
      : { track: "h-5 w-9", knob: "h-4 w-4", on: "translate-x-4", off: "translate-x-0.5" };
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "fr relative rounded-full transition-colors disabled:pointer-events-none disabled:opacity-50",
        dims.track,
        checked ? "bg-sage-500" : "bg-neutral-300 dark:bg-sage-700",
        className,
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 rounded-full bg-white shadow transition-transform",
          dims.knob,
          checked ? dims.on : dims.off,
        )}
      />
    </button>
  );
}
