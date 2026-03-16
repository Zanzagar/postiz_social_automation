import { useQuery } from "@tanstack/react-query";
import { api, type CalendarEntry } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CalendarDays } from "lucide-react";
import { format, parseISO } from "date-fns";

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  draft: "outline",
  scheduled: "default",
  posted: "secondary",
};

export function CalendarPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.getCalendar(),
  });

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Content Calendar</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
    );
  }

  const entries = data?.entries ?? [];

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <CalendarDays className="mb-4 h-12 w-12 text-sage-400" />
        <h2 className="text-xl font-semibold text-sage-700">
          No scheduled content
        </h2>
        <p className="mt-1 text-muted-foreground">
          Create content to see it on the calendar.
        </p>
      </div>
    );
  }

  // Group by date
  const grouped = entries.reduce<Record<string, CalendarEntry[]>>(
    (acc, entry) => {
      const key = entry.date;
      if (!acc[key]) acc[key] = [];
      acc[key].push(entry);
      return acc;
    },
    {},
  );

  const sortedDates = Object.keys(grouped).sort();

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold text-sage-800">Content Calendar</h1>

      {sortedDates.map((date) => (
        <div key={date}>
          <h2 className="mb-2 text-sm font-semibold text-muted-foreground">
            {formatDate(date)}
          </h2>
          <div className="space-y-2">
            {grouped[date].map((entry) => (
              <Card key={entry.row_number}>
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <CardTitle className="text-sm font-medium">
                    {entry.raw_text.length > 80
                      ? entry.raw_text.slice(0, 80) + "..."
                      : entry.raw_text}
                  </CardTitle>
                  <Badge variant={statusVariant[entry.status] ?? "outline"}>
                    {entry.status}
                  </Badge>
                </CardHeader>
                <CardContent className="flex gap-2 pt-0">
                  {entry.content_pillar && (
                    <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                      {entry.content_pillar}
                    </span>
                  )}
                  {Object.entries(entry.platforms)
                    .filter(([, v]) => v)
                    .map(([p]) => (
                      <span
                        key={p}
                        className="rounded bg-sage-100 px-1.5 py-0.5 text-xs text-sage-700"
                      >
                        {p}
                      </span>
                    ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), "EEEE, MMMM d, yyyy");
  } catch {
    return dateStr;
  }
}
