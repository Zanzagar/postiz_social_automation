import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    refetchInterval: 30_000,
  });

  const { data: integrations, isLoading: intLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: () => api.getIntegrations(),
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
