import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CalendarEntry, type ContentRow } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ContentEditor } from "@/components/content/ContentEditor";
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import {
  format,
  parseISO,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addMonths,
  addWeeks,
  addDays,
  isWithinInterval,
} from "date-fns";

type CalendarView = "monthly" | "weekly" | "list";

type ListRange = "upcoming" | "past_week" | "past_month" | "next_2_weeks" | "next_month" | "all";

const LIST_RANGE_OPTIONS: { value: ListRange; label: string }[] = [
  { value: "upcoming", label: "2 weeks back + 4 weeks ahead" },
  { value: "past_week", label: "Past week" },
  { value: "past_month", label: "Past month" },
  { value: "next_2_weeks", label: "Next 2 weeks" },
  { value: "next_month", label: "Next month" },
  { value: "all", label: "All content" },
];

const statusVariant: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  draft: "outline",
  scheduled: "default",
  posted: "secondary",
};

const DAY_HEADERS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function entryToContentRow(entry: CalendarEntry): ContentRow {
  return {
    row_number: entry.row_number,
    date: entry.date,
    content_pillar: entry.content_pillar,
    raw_text: entry.raw_text,
    media_url: null,
    platforms: entry.platforms,
    status: entry.status,
    captions: entry.captions as Record<string, string | null>,
    feedback: null,
    postiz_ids: null,
    posted_at: null,
    error_msg: null,
    source: entry.source ?? "manual",
    auto_publish_at: null,
  };
}

function getListDateRange(range: ListRange): { start: Date; end: Date } | null {
  const now = new Date();
  switch (range) {
    case "upcoming":
      return { start: addDays(now, -14), end: addDays(now, 28) };
    case "past_week":
      return { start: addDays(now, -7), end: now };
    case "past_month":
      return { start: addDays(now, -30), end: now };
    case "next_2_weeks":
      return { start: now, end: addDays(now, 14) };
    case "next_month":
      return { start: now, end: addDays(now, 30) };
    case "all":
      return null;
  }
}

export function CalendarPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<CalendarView>("weekly");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [listRange, setListRange] = useState<ListRange>("upcoming");
  const [selectedContent, setSelectedContent] = useState<ContentRow | null>(
    null,
  );

  const { data, isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.getCalendar(),
  });

  const entries = data?.entries ?? [];

  // Fetch pillars for color dots
  const { data: pillars = [] } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
  });

  const pillarColors = useMemo(() => {
    const map: Record<string, string> = {};
    for (const p of pillars) {
      if (p.color) map[p.name] = p.color;
    }
    return map;
  }, [pillars]);

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

  function handleEntryClick(entry: CalendarEntry) {
    setSelectedContent(entryToContentRow(entry));
  }

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sage-800">Content Calendar</h1>

        <Tabs
          value={view}
          onValueChange={(v) => setView(v as CalendarView)}
        >
          <TabsList>
            <TabsTrigger value="monthly">Monthly</TabsTrigger>
            <TabsTrigger value="weekly">Weekly</TabsTrigger>
            <TabsTrigger value="list">List</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Navigation for monthly/weekly */}
      {view !== "list" && (
        <div className="flex items-center justify-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setCurrentDate((d) =>
                view === "monthly" ? addMonths(d, -1) : addWeeks(d, -1),
              )
            }
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium">
            {view === "monthly"
              ? format(currentDate, "MMMM yyyy")
              : `Week of ${format(startOfWeek(currentDate), "MMM d")} – ${format(endOfWeek(currentDate), "MMM d, yyyy")}`}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setCurrentDate((d) =>
                view === "monthly" ? addMonths(d, 1) : addWeeks(d, 1),
              )
            }
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Date range selector for list view */}
      {view === "list" && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Showing:</span>
          <Select value={listRange} onValueChange={(v) => setListRange(v as ListRange)}>
            <SelectTrigger className="w-[260px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LIST_RANGE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Views */}
      {view === "monthly" && (
        <MonthlyGrid
          currentDate={currentDate}
          entries={entries}
          pillarColors={pillarColors}
          onEntryClick={handleEntryClick}
        />
      )}
      {view === "weekly" && (
        <WeeklyView
          currentDate={currentDate}
          entries={entries}
          pillarColors={pillarColors}
          onEntryClick={handleEntryClick}
        />
      )}
      {view === "list" && (
        <ListView
          entries={entries}
          listRange={listRange}
          pillarColors={pillarColors}
          onEntryClick={handleEntryClick}
        />
      )}

      {/* ContentEditor modal */}
      <ContentEditor
        contentRow={selectedContent}
        mode="refine"
        isOpen={!!selectedContent}
        onClose={() => setSelectedContent(null)}
        onSave={() => {
          queryClient.invalidateQueries({ queryKey: ["calendar"] });
          setSelectedContent(null);
        }}
      />
    </div>
  );
}

// --- Monthly Grid ---

function MonthlyGrid({
  currentDate,
  entries,
  pillarColors,
  onEntryClick,
}: {
  currentDate: Date;
  entries: CalendarEntry[];
  pillarColors: Record<string, string>;
  onEntryClick: (entry: CalendarEntry) => void;
}) {
  const days = useMemo(() => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const gridStart = startOfWeek(monthStart);
    const gridEnd = endOfWeek(monthEnd);
    return eachDayOfInterval({ start: gridStart, end: gridEnd });
  }, [currentDate]);

  const entriesByDate = useMemo(() => {
    const map: Record<string, CalendarEntry[]> = {};
    for (const e of entries) {
      const key = format(parseISO(e.date), "yyyy-MM-dd");
      if (!map[key]) map[key] = [];
      map[key].push(e);
    }
    return map;
  }, [entries]);

  return (
    <div>
      {/* Day headers */}
      <div className="grid grid-cols-7 gap-px text-center text-xs font-medium text-muted-foreground">
        {DAY_HEADERS.map((d) => (
          <div key={d} className="py-2">
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7 gap-px">
        {days.map((day) => {
          const dateKey = format(day, "yyyy-MM-dd");
          const dayEntries = entriesByDate[dateKey] ?? [];
          const inMonth = isSameMonth(day, currentDate);
          const isToday = isSameDay(day, new Date());

          return (
            <div
              key={dateKey}
              className={`min-h-[80px] rounded-md border p-1.5 ${
                inMonth ? "bg-background" : "bg-muted/30"
              } ${isToday ? "ring-2 ring-sage-400" : ""}`}
            >
              <span
                className={`text-xs ${
                  inMonth ? "text-foreground" : "text-muted-foreground"
                } ${isToday ? "font-bold" : ""}`}
              >
                {format(day, "d")}
              </span>
              <div className="mt-1 space-y-0.5">
                {dayEntries.slice(0, 3).map((entry) => (
                  <button
                    key={entry.row_number}
                    onClick={() => onEntryClick(entry)}
                    className="flex w-full items-center gap-1 rounded px-1 py-0.5 text-left text-[10px] leading-tight hover:bg-muted transition-colors"
                  >
                    <span
                      className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                      style={{ backgroundColor: pillarColors[entry.content_pillar ?? ""] ?? "#9ca3af" }}
                    />
                    <span className="shrink-0 text-muted-foreground">
                      {format(parseISO(entry.date), "h:mma").toLowerCase()}
                    </span>
                    <span className="truncate">
                      {entry.raw_text.slice(0, 15)}
                    </span>
                  </button>
                ))}
                {dayEntries.length > 3 && (
                  <span className="text-[10px] text-muted-foreground pl-1">
                    +{dayEntries.length - 3} more
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// --- Weekly View ---

function WeeklyView({
  currentDate,
  entries,
  pillarColors,
  onEntryClick,
}: {
  currentDate: Date;
  entries: CalendarEntry[];
  pillarColors: Record<string, string>;
  onEntryClick: (entry: CalendarEntry) => void;
}) {
  const weekDays = useMemo(() => {
    const weekStart = startOfWeek(currentDate);
    const weekEnd = endOfWeek(currentDate);
    return eachDayOfInterval({ start: weekStart, end: weekEnd });
  }, [currentDate]);

  const entriesByDate = useMemo(() => {
    const map: Record<string, CalendarEntry[]> = {};
    for (const e of entries) {
      const key = format(parseISO(e.date), "yyyy-MM-dd");
      if (!map[key]) map[key] = [];
      map[key].push(e);
    }
    return map;
  }, [entries]);

  return (
    <div className="grid grid-cols-7 gap-2">
      {weekDays.map((day) => {
        const dateKey = format(day, "yyyy-MM-dd");
        const dayEntries = entriesByDate[dateKey] ?? [];
        const isToday = isSameDay(day, new Date());

        return (
          <div key={dateKey} className="space-y-1.5">
            <div
              className={`text-center text-xs font-medium ${
                isToday ? "text-sage-700" : "text-muted-foreground"
              }`}
            >
              <div>{format(day, "EEE")}</div>
              <div
                className={`mx-auto mt-0.5 flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                  isToday ? "bg-sage-600 text-white" : ""
                }`}
              >
                {format(day, "d")}
              </div>
            </div>
            <div className="space-y-1">
              {dayEntries.map((entry) => (
                <button
                  key={entry.row_number}
                  onClick={() => onEntryClick(entry)}
                  className="w-full rounded-md border p-1.5 text-left text-xs hover:bg-muted transition-colors"
                >
                  <div className="flex items-center gap-1">
                    <span
                      className="inline-block h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: pillarColors[entry.content_pillar ?? ""] ?? "#9ca3af" }}
                    />
                    <span className="text-[9px] text-muted-foreground">
                      {format(parseISO(entry.date), "h:mm a")}
                    </span>
                    <Badge
                      variant={statusVariant[entry.status] ?? "outline"}
                      className="text-[9px] px-1 py-0"
                    >
                      {entry.status.replace("_", " ")}
                    </Badge>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-tight">
                    {entry.raw_text}
                  </p>
                </button>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// --- List View ---

function ListView({
  entries,
  listRange,
  pillarColors,
  onEntryClick,
}: {
  entries: CalendarEntry[];
  listRange: ListRange;
  pillarColors: Record<string, string>;
  onEntryClick: (entry: CalendarEntry) => void;
}) {
  const filteredEntries = useMemo(() => {
    const range = getListDateRange(listRange);
    if (!range) return entries;
    return entries.filter((e) => {
      const d = parseISO(e.date);
      return isWithinInterval(d, { start: range.start, end: range.end });
    });
  }, [entries, listRange]);

  const grouped = filteredEntries.reduce<Record<string, CalendarEntry[]>>(
    (acc, entry) => {
      const key = format(parseISO(entry.date), "yyyy-MM-dd");
      if (!acc[key]) acc[key] = [];
      acc[key].push(entry);
      return acc;
    },
    {},
  );

  // Sort entries within each day by time
  for (const key of Object.keys(grouped)) {
    grouped[key].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }

  const sortedDates = Object.keys(grouped).sort();

  if (sortedDates.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No content in this date range.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {sortedDates.map((date) => (
        <div key={date}>
          <h2 className="mb-2 text-sm font-semibold text-muted-foreground">
            {formatDate(date)}
          </h2>
          <div className="space-y-2">
            {grouped[date].map((entry) => (
              <Card
                key={entry.row_number}
                className="cursor-pointer transition-colors hover:bg-muted/30"
                onClick={() => onEntryClick(entry)}
              >
                <CardHeader className="flex flex-row items-center justify-between pb-1">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {format(parseISO(entry.date), "h:mm a")}
                    </span>
                    <CardTitle className="truncate text-sm font-medium">
                      {entry.raw_text.length > 80
                        ? entry.raw_text.slice(0, 80) + "..."
                        : entry.raw_text}
                    </CardTitle>
                  </div>
                  <Badge variant={statusVariant[entry.status] ?? "outline"} className="shrink-0 ml-2">
                    {entry.status.replace("_", " ")}
                  </Badge>
                </CardHeader>
                <CardContent className="flex gap-2 pt-0">
                  {entry.content_pillar && (
                    <Badge
                      variant="secondary"
                      className="text-xs gap-1"
                    >
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: pillarColors[entry.content_pillar] ?? "#9ca3af" }}
                      />
                      {entry.content_pillar}
                    </Badge>
                  )}
                  {Object.entries(entry.platforms)
                    .filter(([, v]) => v)
                    .map(([p]) => (
                      <Badge
                        key={p}
                        variant="outline"
                        className="text-xs"
                      >
                        {p}
                      </Badge>
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
