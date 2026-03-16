import { Link } from "react-router-dom";
import { useDashboardData } from "@/hooks/useDashboardData";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  FileCheck,
  CalendarDays,
  CheckCircle,
  PenSquare,
} from "lucide-react";

const statusColor: Record<string, string> = {
  healthy: "bg-green-500",
  degraded: "bg-yellow-500",
  unhealthy: "bg-red-500",
};

export function DashboardPage() {
  const {
    pendingCount,
    scheduledThisWeek,
    postedCount,
    services,
    isLoading,
  } = useDashboardData();

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Dashboard</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} data-testid="skeleton-card" className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold text-sage-800">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending Drafts
            </CardTitle>
            <FileCheck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{pendingCount}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Scheduled This Week
            </CardTitle>
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{scheduledThisWeek}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Posts Published
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{postedCount}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Quick create */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Create</CardTitle>
          </CardHeader>
          <CardContent>
            <Link
              to="/create"
              className="flex items-center gap-3 rounded-lg border-2 border-dashed border-sage-200 p-4 text-sage-600 transition-colors hover:border-sage-400 hover:bg-sage-50"
            >
              <PenSquare className="h-5 w-5" />
              <span className="font-medium">Create Content</span>
            </Link>
          </CardContent>
        </Card>

        {/* Health status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">System Health</CardTitle>
          </CardHeader>
          <CardContent data-testid="health-status">
            <div className="space-y-3">
              {services.map((svc) => (
                <div key={svc.name} className="flex items-center justify-between">
                  <span className="text-sm">{svc.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {svc.message}
                    </span>
                    <span
                      data-status={svc.status}
                      className={`h-2.5 w-2.5 rounded-full ${statusColor[svc.status] ?? "bg-gray-400"}`}
                    />
                  </div>
                </div>
              ))}
              {services.length === 0 && (
                <p className="text-sm text-muted-foreground">No services configured</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
