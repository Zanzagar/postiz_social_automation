import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, AlertTriangle, HardDrive, Loader2, Trash2 } from "lucide-react";
import { format, parseISO } from "date-fns";

const statusColor: Record<string, string> = {
  healthy: "bg-green-500",
  degraded: "bg-yellow-500",
  unhealthy: "bg-red-500",
};

const statusBadge: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  healthy: "default",
  degraded: "secondary",
  unhealthy: "destructive",
};

export function HealthPage() {
  const queryClient = useQueryClient();

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 30_000,
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
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">System Health</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold text-sage-800">System Health</h1>

      {/* Services */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Services</CardTitle>
        </CardHeader>
        <CardContent>
          {health?.services && health.services.length > 0 ? (
            <div className="space-y-3">
              {health.services.map((svc) => (
                <div
                  key={svc.name}
                  className="flex items-center justify-between rounded-md border px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`h-3 w-3 rounded-full ${statusColor[svc.status] ?? "bg-gray-400"}`}
                    />
                    <div>
                      <p className="text-sm font-medium">{svc.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {svc.message}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={statusBadge[svc.status] ?? "outline"}>
                      {svc.status}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">
                      {formatTime(svc.last_checked)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No services configured</p>
          )}
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Postiz Integrations</CardTitle>
        </CardHeader>
        <CardContent>
          {integrations && integrations.length > 0 ? (
            <div className="space-y-2">
              {integrations.map((int) => (
                <div
                  key={int.id}
                  className="flex items-center justify-between rounded-md border px-4 py-2.5"
                >
                  <span className="text-sm font-medium">{int.name}</span>
                  <Badge variant="outline">{int.platform}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No Postiz integrations found
            </p>
          )}
        </CardContent>
      </Card>

      {/* Media Catalog Health */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <HardDrive className="h-4 w-4" />
            Media Catalog
          </CardTitle>
          {mediaHealth && (mediaHealth.missing_file.length > 0 || mediaHealth.orphan_files > 0) && (
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={() => cleanupMutation.mutate()}
              disabled={cleanupMutation.isPending}
            >
              {cleanupMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5" />
              )}
              Clean Up
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {mediaHealth ? (
            <div className="space-y-3">
              {/* Summary row */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-md border px-3 py-2 text-center">
                  <p className="text-lg font-bold">{mediaHealth.total}</p>
                  <p className="text-xs text-muted-foreground">Total Items</p>
                </div>
                <div className="rounded-md border px-3 py-2 text-center">
                  <p className="text-lg font-bold text-green-600">{mediaHealth.healthy}</p>
                  <p className="text-xs text-muted-foreground">Healthy</p>
                </div>
                <div className="rounded-md border px-3 py-2 text-center">
                  <p className="text-lg font-bold">{mediaHealth.drive_refs}</p>
                  <p className="text-xs text-muted-foreground">Drive Refs</p>
                </div>
                <div className="rounded-md border px-3 py-2 text-center">
                  <p className="text-lg font-bold">{mediaHealth.total - mediaHealth.healthy}</p>
                  <p className="text-xs text-muted-foreground">Local Files</p>
                </div>
              </div>

              {/* Status */}
              {mediaHealth.missing_file.length === 0 && mediaHealth.orphan_files === 0 ? (
                <div className="flex items-center gap-2 rounded-md border border-green-200 bg-green-50 px-4 py-2.5">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <span className="text-sm text-green-700">
                    All media files in sync — no issues detected
                  </span>
                </div>
              ) : (
                <div className="space-y-2">
                  {mediaHealth.missing_file.length > 0 && (
                    <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <span className="text-sm text-amber-700">
                        {mediaHealth.missing_file.length} DB entries with missing files
                      </span>
                    </div>
                  )}
                  {mediaHealth.missing_thumb.length > 0 && (
                    <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <span className="text-sm text-amber-700">
                        {mediaHealth.missing_thumb.length} missing thumbnails
                      </span>
                    </div>
                  )}
                  {mediaHealth.orphan_files > 0 && (
                    <div className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <span className="text-sm text-amber-700">
                        {mediaHealth.orphan_files} orphaned files on disk
                      </span>
                    </div>
                  )}
                </div>
              )}

              {cleanupMutation.isSuccess && (
                <p className="text-sm text-green-600">
                  Cleaned up {cleanupMutation.data.removed_entries} entries
                  and {cleanupMutation.data.removed_orphans} orphan files
                </p>
              )}
            </div>
          ) : (
            <Skeleton className="h-20 rounded-md" />
          )}
        </CardContent>
      </Card>
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
