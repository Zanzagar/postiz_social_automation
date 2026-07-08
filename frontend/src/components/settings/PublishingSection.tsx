import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  api,
  type PlatformPublishConfig,
  type PublishConfigResponse,
} from "@/lib/api";
import { PLATFORMS } from "@/lib/platforms";
import { pillarColor } from "@/lib/pillars";
import { cn } from "@/lib/utils";
import { PlatformDot, SkeletonText, Toggle } from "@/components/pasture";
import { PublishingAside } from "./PublishingAside";

const DEFAULT_DELAY_HOURS = 2;

const DELAY_OPTIONS: ReadonlyArray<{ hours: number; label: string }> = [
  { hours: 0, label: "Immediately on approval" },
  { hours: 1, label: "After 1 hour" },
  { hours: 2, label: "After 2 hours" },
  { hours: 4, label: "After 4 hours" },
];

/** Platform-specific "off" captions from the prototype. */
const PLATFORM_NOTES: Record<string, string> = {
  tiktok: "Video needs eyes — always review.",
};

function delayLabel(hours: number): string {
  return (
    DELAY_OPTIONS.find((o) => o.hours === hours)?.label ?? `After ${hours} hours`
  );
}

function releaseCaption(enabled: boolean, hours: number, note?: string): string {
  if (!enabled) return note ?? "Always waits for your blessing.";
  const when = hours === 0 ? "once approved" : delayLabel(hours).toLowerCase();
  return `Releases on its own ${when} — pause anytime.`;
}

function platformLabel(id: string): string {
  const known = PLATFORMS.find((p) => p.id === id);
  if (known) return known.label;
  return id.charAt(0).toUpperCase() + id.slice(1);
}

interface ReleaseRowProps {
  config: PlatformPublishConfig;
  onChange: (patch: Partial<PlatformPublishConfig>) => void;
}

function ReleaseRow({ config, onChange }: ReleaseRowProps) {
  const label = platformLabel(config.platform);
  const known = PLATFORMS.some((p) => p.id === config.platform);
  const hasStandardDelay = DELAY_OPTIONS.some((o) => o.hours === config.delay_hours);
  return (
    <div className="border-hair-b flex h-16 items-center gap-4 px-4 last:border-b-0">
      <div className="flex w-40 shrink-0 items-center gap-2.5">
        {known && <PlatformDot id={config.platform} size={18} />}
        <span className="t-body ink font-medium">{label}</span>
      </div>
      <Toggle
        checked={config.enabled}
        onChange={(checked) => onChange({ enabled: checked })}
        aria-label={`Auto-release on ${label}`}
      />
      <select
        value={config.delay_hours}
        onChange={(e) => onChange({ delay_hours: Number(e.target.value) })}
        disabled={!config.enabled}
        aria-label={`Release delay for ${label}`}
        className="fr border-hair bg-card ink t-caption h-8 rounded-lg px-2 disabled:opacity-40"
      >
        {DELAY_OPTIONS.map((o) => (
          <option key={o.hours} value={o.hours}>
            {o.label}
          </option>
        ))}
        {!hasStandardDelay && (
          <option value={config.delay_hours}>{delayLabel(config.delay_hours)}</option>
        )}
      </select>
      <span className="t-caption ink-muted flex-1 text-right">
        {releaseCaption(config.enabled, config.delay_hours, PLATFORM_NOTES[config.platform])}
      </span>
    </div>
  );
}

/**
 * Publishing — "blessing & release" (phase1.jsx PastureAutoPublish).
 * Release-by-platform rows, pillar exceptions, and the explainer aside.
 * Every change saves immediately with an optimistic update.
 */
export function PublishingSection() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["publishConfig"],
    queryFn: () => api.getPublishConfig(),
  });
  const { data: pillars = [] } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
  });

  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const mutation = useMutation({
    mutationFn: (platforms: PlatformPublishConfig[]) =>
      api.updatePublishConfig(platforms),
    onMutate: async (platforms) => {
      await queryClient.cancelQueries({ queryKey: ["publishConfig"] });
      const previous = queryClient.getQueryData<PublishConfigResponse>([
        "publishConfig",
      ]);
      queryClient.setQueryData<PublishConfigResponse>(["publishConfig"], {
        platforms,
      });
      setSaved(false);
      setSaveError(false);
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["publishConfig"], context.previous);
      }
      setSaveError(true);
    },
    onSuccess: () => {
      setSaved(true);
      if (savedTimer.current) clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaved(false), 2500);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["publishConfig"] });
    },
  });

  // When the backend has no rows yet, seed editable rows from the static
  // platform catalog so staff can configure from scratch; the first change
  // PUTs the full seeded set.
  const configs: PlatformPublishConfig[] =
    data?.platforms && data.platforms.length > 0
      ? data.platforms
      : PLATFORMS.map((p) => ({
          platform: p.id,
          enabled: false,
          delay_hours: DEFAULT_DELAY_HOURS,
          pillar_overrides: {},
        }));

  function updatePlatform(platform: string, patch: Partial<PlatformPublishConfig>) {
    mutation.mutate(
      configs.map((c) => (c.platform === platform ? { ...c, ...patch } : c)),
    );
  }

  function isHeld(pillarName: string): boolean {
    return configs.some((c) => c.pillar_overrides?.[pillarName] === false);
  }

  function togglePillarHold(pillarName: string) {
    const held = isHeld(pillarName);
    mutation.mutate(
      configs.map((c) => {
        const overrides = { ...c.pillar_overrides };
        if (held) {
          delete overrides[pillarName];
        } else {
          overrides[pillarName] = false;
        }
        return { ...c, pillar_overrides: overrides };
      }),
    );
  }

  if (isLoading) {
    return (
      <div className="bg-card border-hair shadow-card rounded-2xl p-5">
        <span className="sr-only">Loading publishing settings</span>
        <SkeletonText lines={4} />
      </div>
    );
  }

  const activePillars = pillars.filter((p) => p.is_active);

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="space-y-5">
        <div className="bg-card border-hair shadow-card overflow-hidden rounded-2xl">
          <div className="flex items-start justify-between px-4 pt-4 pb-2">
            <div>
              <div className="t-title-sm ink font-semibold">Release by platform</div>
              <div className="t-caption ink-muted mt-0.5">
                Approved posts on these platforms publish themselves after a rest
                window. Everything else holds for review.
              </div>
            </div>
            <span
              role="status"
              className={cn(
                "t-caption shrink-0 pt-0.5 transition-opacity",
                saved ? "text-sage-600 dark:text-sage-300" : "opacity-0",
                saveError && "text-red-700 opacity-100 dark:text-red-400",
              )}
            >
              {saveError ? "Couldn't save — try again." : saved ? "Saved" : ""}
            </span>
          </div>
          {configs.map((config) => (
            <ReleaseRow
              key={config.platform}
              config={config}
              onChange={(patch) => updatePlatform(config.platform, patch)}
            />
          ))}
        </div>

        <div className="bg-card border-hair shadow-card rounded-2xl p-4">
          <div className="t-title-sm ink font-semibold">Pillar exceptions</div>
          <div className="t-caption ink-muted mt-0.5 mb-3">
            These pillars always wait for a blessing, on every platform.
          </div>
          <div className="flex flex-wrap gap-2">
            {activePillars.map((pillar) => {
              const held = isHeld(pillar.name);
              return (
                <button
                  key={pillar.id}
                  type="button"
                  aria-pressed={held}
                  onClick={() => togglePillarHold(pillar.name)}
                  className={cn(
                    "fr t-caption inline-flex h-8 items-center gap-1.5 rounded-full border px-2.5 font-medium transition-colors",
                    held
                      ? "bg-cream-100 border-cream-300 text-cream-ink-deep dark:bg-cream-400/15 dark:border-cream-400/40"
                      : "bg-card border-hair ink-muted hover:border-sage-200",
                  )}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: pillarColor(pillar) }}
                    aria-hidden="true"
                  />
                  {pillar.name}{" "}
                  {held && (
                    <span className="t-micro font-semibold tracking-wide uppercase opacity-80">
                      holds
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <p className="t-micro ink-muted mt-3">
            Spiritual and Support posts carry the farm's voice furthest — a person
            signs off on every one.
          </p>
        </div>
      </div>

      <PublishingAside />
    </div>
  );
}
