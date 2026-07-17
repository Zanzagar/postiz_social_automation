import type * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  HardDrive,
  Loader2,
  Trash2,
} from "lucide-react";
import { format, parseISO } from "date-fns";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageHeader, SkeletonText } from "@/components/pasture";

interface HealthStatusMeta {
  label: string;
  dot: string;
  badge: "default" | "secondary" | "destructive" | "outline";
}

/**
 * Backend emits "ok"/"error" (api/routes/health.py); older payloads said
 * "healthy"/"unhealthy" — both vocabularies map onto the same three states.
 */
const HEALTH_STATUS_META: Record<string, HealthStatusMeta> = {
  ok: { label: "Healthy", dot: "bg-sage-500", badge: "default" },
  healthy: { label: "Healthy", dot: "bg-sage-500", badge: "default" },
  degraded: { label: "Degraded", dot: "bg-cream-500", badge: "secondary" },
  error: { label: "Error", dot: "bg-terra-500", badge: "destructive" },
  unhealthy: { label: "Error", dot: "bg-terra-500", badge: "destructive" },
};

function statusMeta(status: string): HealthStatusMeta {
  return (
    HEALTH_STATUS_META[status.toLowerCase()] ?? {
      label: status,
      dot: "bg-neutral-300",
      badge: "outline",
    }
  );
}

/** Backend service ids → display names (same map as the sidebar footer). */
const SERVICE_LABELS: Record<string, string> = {
  postiz: "Postiz",
  claude: "Claude",
  oauth: "Claude login",
  sheets: "Sheets",
};

const CARD = "bg-card border-hair shadow-card rounded-xl p-5";
const SAGE_BANNER =
  "flex items-center gap-2 rounded-lg border border-sage-100 bg-sage-50 px-4 py-2.5 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-100";
const CREAM_BANNER =
  "flex items-center gap-2 rounded-lg border border-cream-300 bg-cream-100 px-4 py-2.5 text-cream-ink dark:border-cream-400/40 dark:bg-cream-400/15";

function Header() {
  return (
    <PageHeader
      greeting="Systems"
      title="Health"
      subtitle="A calm look at every connection the pasture relies on."
      icon={Activity}
    />
  );
}

function CardTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="t-label text-sage-600 dark:text-sage-300">{children}</div>
  );
}

export function HealthPage() {
  const queryClient = useQueryClient();

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 120_000,
    staleTime: 60_000,
  });

  const { data: integrations, isLoading: intLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.getIntegrations(),
  });

  const { data: mediaHealth } = useQuery({
    queryKey: ["media-health"],
    queryFn: () => api.getMediaHealth(),
    refetchInterval: 60_000,
  });

  const cleanupMutation = useMutation({
    mutationFn: () => api.mediaCleanup(true, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["media-health"] });
      queryClient.invalidateQueries({ queryKey: ["media"] });
    },
  });

  const isLoading = healthLoading || intLoading;

  if (isLoading) {
    return (
      <div>
        <Header />
        <div
          role="status"
          aria-label="Loading health"
          className="mx-auto w-full max-w-[1180px] space-y-4 px-4 py-6 sm:px-8"
        >
          <div className={CARD}>
            <SkeletonText lines={3} />
          </div>
          <div className={CARD}>
            <SkeletonText lines={2} />
          </div>
        </div>
      </div>
    );
  }

  const mediaIssues =
    mediaHealth !== undefined &&
    (mediaHealth.missing_file.length > 0 || mediaHealth.orphan_files > 0);

  return (
    <div>
      <Header />
      <div className="mx-auto w-full max-w-[1180px] space-y-4 px-4 py-6 sm:px-8">
        {/* Services */}
        <section aria-label="Services" className={CARD}>
          <CardTitle>Services</CardTitle>
          {health?.services && health.services.length > 0 ? (
            <div className="mt-3 space-y-2">
              {health.services.map((svc) => {
                const m = statusMeta(svc.status);
                return (
                  <div
                    key={svc.name}
                    className="border-hair flex items-center justify-between gap-3 rounded-lg px-4 py-3"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className={cn("h-2 w-2 shrink-0 rounded-full", m.dot)}
                        aria-hidden="true"
                      />
                      <div className="min-w-0">
                        <p className="t-body-sm ink font-medium">
                          {SERVICE_LABELS[svc.name] ?? svc.name}
                        </p>
                        <p
                          className="t-caption ink-muted truncate"
                          title={svc.message}
                        >
                          {svc.message}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={m.badge}>{m.label}</Badge>
                      <span className="t-micro ink-muted">
                        {formatTime(svc.last_checked)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="t-body-sm ink-muted mt-3">No services configured</p>
          )}
        </section>

        {/* Postiz integrations */}
        <section aria-label="Postiz integrations" className={CARD}>
          <CardTitle>Postiz integrations</CardTitle>
          {integrations && integrations.length > 0 ? (
            <div className="mt-3 space-y-2">
              {integrations.map((int) => (
                <div
                  key={int.id}
                  className="border-hair flex items-center justify-between gap-3 rounded-lg px-4 py-2.5"
                >
                  <span className="t-body-sm ink font-medium">{int.name}</span>
                  <Badge variant="outline">{int.platform}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="t-body-sm ink-muted mt-3">
              No Postiz integrations found
            </p>
          )}
        </section>

        {/* Media catalog */}
        <section aria-label="Media catalog" className={CARD}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <HardDrive
                size={15}
                strokeWidth={1.75}
                className="text-sage-600 dark:text-sage-300"
                aria-hidden="true"
              />
              <CardTitle>Media catalog</CardTitle>
            </div>
            {mediaIssues && (
              <Button
                variant="outline"
                size="sm"
                className="fr gap-1.5"
                onClick={() => cleanupMutation.mutate()}
                disabled={cleanupMutation.isPending}
              >
                {cleanupMutation.isPending ? (
                  <Loader2
                    className="h-3.5 w-3.5 animate-spin"
                    aria-hidden="true"
                  />
                ) : (
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                Clean up
              </Button>
            )}
          </div>
          {mediaHealth ? (
            <div className="mt-3 space-y-3">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MediaStat value={mediaHealth.total} label="Total items" />
                <MediaStat
                  value={mediaHealth.healthy}
                  label="Healthy"
                  tone="sage"
                />
                <MediaStat value={mediaHealth.drive_refs} label="Drive refs" />
                <MediaStat
                  value={mediaHealth.total - mediaHealth.healthy}
                  label="Local files"
                />
              </div>

              {mediaHealth.missing_file.length === 0 &&
              mediaHealth.orphan_files === 0 ? (
                <div className={SAGE_BANNER}>
                  <CheckCircle2
                    className="h-4 w-4 shrink-0"
                    aria-hidden="true"
                  />
                  <span className="t-body-sm">
                    All media files in sync — no issues detected
                  </span>
                </div>
              ) : (
                <div className="space-y-2">
                  {mediaHealth.missing_file.length > 0 && (
                    <div className={CREAM_BANNER}>
                      <AlertTriangle
                        className="h-4 w-4 shrink-0"
                        aria-hidden="true"
                      />
                      <span className="t-body-sm">
                        {mediaHealth.missing_file.length} DB entries with
                        missing files
                      </span>
                    </div>
                  )}
                  {mediaHealth.missing_thumb.length > 0 && (
                    <div className={CREAM_BANNER}>
                      <AlertTriangle
                        className="h-4 w-4 shrink-0"
                        aria-hidden="true"
                      />
                      <span className="t-body-sm">
                        {mediaHealth.missing_thumb.length} missing thumbnails
                      </span>
                    </div>
                  )}
                  {mediaHealth.orphan_files > 0 && (
                    <div className={CREAM_BANNER}>
                      <AlertTriangle
                        className="h-4 w-4 shrink-0"
                        aria-hidden="true"
                      />
                      <span className="t-body-sm">
                        {mediaHealth.orphan_files} orphaned files on disk
                      </span>
                    </div>
                  )}
                </div>
              )}

              {cleanupMutation.isSuccess && (
                <p className="t-body-sm text-sage-700 dark:text-sage-300">
                  Cleaned up {cleanupMutation.data.removed_entries} entries and{" "}
                  {cleanupMutation.data.removed_orphans} orphan files
                </p>
              )}
            </div>
          ) : (
            <div className="mt-3">
              <SkeletonText lines={2} />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function MediaStat({
  value,
  label,
  tone,
}: {
  value: number;
  label: string;
  tone?: "sage";
}) {
  return (
    <div className="border-hair rounded-lg px-3 py-2 text-center">
      <p
        className={cn(
          "t-title font-semibold",
          tone === "sage" ? "text-sage-700 dark:text-sage-300" : "ink",
        )}
      >
        {value}
      </p>
      <p className="t-caption ink-muted">{label}</p>
    </div>
  );
}

function formatTime(isoStr: string): string {
  try {
    return format(parseISO(isoStr), "HH:mm");
  } catch {
    return "";
  }
}
