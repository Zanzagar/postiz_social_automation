import { useState, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type CalendarEntry, type ContentRow } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
} from "date-fns";

type CalendarView = "monthly" | "weekly" | "list";

const statusVariant: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  draft: "outline",
  scheduled: "default",
  posted: "secondary",
};

const PILLAR_COLORS: Record<string, string> = {
  spiritual_education: "bg-amber-500",
  spiritual: "bg-amber-500",
  community: "bg-emerald-500",
  farm: "bg-lime-500",
  events: "bg-blue-500",
  behind_scenes: "bg-purple-500",
  seasonal: "bg-rose-500",
  collaborative: "bg-cyan-500",
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
    source: "manual",
  };
}

export function CalendarPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<CalendarView>("list");
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedContent, setSelectedContent] = useState<ContentRow | null>(
    null,
  );

  const { data, isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.getCalendar(),
  });

  const entries = data?.entries ?? [];
  const editorMode = selectedContent?.status === "posted" ? "repurpose" : "refine";

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

      {/* Views */}
      {view === "monthly" && (
        <MonthlyGrid
          currentDate={currentDate}
          entries={entries}
          onEntryClick={handleEntryClick}
        />
      )}
      {view === "weekly" && (
        <WeeklyView
          currentDate={currentDate}
          entries={entries}
          onEntryClick={handleEntryClick}
        />
      )}
      {view === "list" && (
        <ListView entries={entries} onEntryClick={handleEntryClick} />
      )}

      {/* ContentEditor modal */}
      <ContentEditor
        contentRow={selectedContent}
        mode={editorMode}
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
  onEntryClick,
}: {
  currentDate: Date;
  entries: CalendarEntry[];
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
      if (!map[e.date]) map[e.date] = [];
      map[e.date].push(e);
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
                      className={`inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                        PILLAR_COLORS[entry.content_pillar ?? ""] ?? "bg-gray-400"
                      }`}
                    />
                    <span className="truncate">
                      {entry.raw_text.slice(0, 20)}
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
  onEntryClick,
}: {
  currentDate: Date;
  entries: CalendarEntry[];
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
      if (!map[e.date]) map[e.date] = [];
      map[e.date].push(e);
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
                      className={`inline-block h-2 w-2 shrink-0 rounded-full ${
                        PILLAR_COLORS[entry.content_pillar ?? ""] ?? "bg-gray-400"
                      }`}
                    />
                    <Badge
                      variant={statusVariant[entry.status] ?? "outline"}
                      className="text-[9px] px-1 py-0"
                    >
                      {entry.status}
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
  onEntryClick,
}: {
  entries: CalendarEntry[];
  onEntryClick: (entry: CalendarEntry) => void;
}) {
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
                    <Badge variant="secondary" className="text-xs">
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
