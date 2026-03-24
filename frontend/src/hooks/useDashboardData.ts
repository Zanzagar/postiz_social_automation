import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { startOfWeek, endOfWeek, parseISO, isWithinInterval } from "date-fns";

export function useDashboardData() {
  const drafts = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api.getDrafts(),
  });

  const calendar = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.getCalendar(),
  });

  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getHealth(),
    staleTime: 5 * 60 * 1000,
  });

  const now = new Date();
  const weekStart = startOfWeek(now, { weekStartsOn: 0 });
  const weekEnd = endOfWeek(now, { weekStartsOn: 0 });

  const pendingCount = drafts.data?.filter((d) => d.status === "draft").length ?? 0;
  const scheduledThisWeek =
    calendar.data?.entries.filter((e) => {
      try {
        const d = parseISO(e.date);
        return isWithinInterval(d, { start: weekStart, end: weekEnd });
      } catch {
        return false;
      }
    }).length ?? 0;
  const postedCount =
    drafts.data?.filter((d) => d.status === "posted").length ?? 0;

  return {
    pendingCount,
    scheduledThisWeek,
    postedCount,
    calendarEntries: calendar.data?.entries ?? [],
    services: health.data?.services ?? [],
    isLoading: drafts.isLoading || calendar.isLoading,
    isError: drafts.isError || calendar.isError,
  };
}
