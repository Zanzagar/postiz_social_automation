import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addDays,
  addMonths,
  addWeeks,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  startOfMonth,
  startOfWeek,
} from "date-fns";
import {
  Calendar as CalendarIcon,
  CalendarPlus,
  ChevronLeft,
  ChevronRight,
  Plus,
} from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader, SegmentedControl, SkeletonText } from "@/components/pasture";
import { ContentEditorSheet } from "@/components/content/ContentEditorSheet";
import { CalendarPlanDialog } from "@/components/calendar/CalendarPlanDialog";
import { WeekGrid } from "@/components/calendar/WeekGrid";
import { MonthGrid } from "@/components/calendar/MonthGrid";
import { CalendarListView } from "@/components/calendar/CalendarListView";
import { CalendarRail } from "@/components/calendar/CalendarRail";
import {
  groupEntriesByDate,
  makePillarColorLookup,
  type CalendarEntryX,
} from "@/components/calendar/calendar-utils";

type CalendarView = "week" | "month" | "list";

const VIEW_OPTIONS = [
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "list", label: "List" },
];

export function CalendarPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [view, setView] = useState<CalendarView>("week");
  const [cursor, setCursor] = useState(() => new Date());
  const [editorRowId, setEditorRowId] = useState<number | null>(null);
  const [planDialogOpen, setPlanDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["calendar"],
    queryFn: () => api.getCalendar(),
  });
  const entries = useMemo(
    () => (data?.entries ?? []) as CalendarEntryX[],
    [data],
  );

  const { data: pillars = [] } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
  });

  const { data: festivals = [] } = useQuery({
    queryKey: ["festivals"],
    queryFn: () => api.getFestivals(),
  });

  const colorFor = useMemo(() => makePillarColorLookup(pillars), [pillars]);
  const entriesByDate = useMemo(() => groupEntriesByDate(entries), [entries]);

  const weekDays = useMemo(() => {
    const start = startOfWeek(cursor, { weekStartsOn: 1 });
    return eachDayOfInterval({ start, end: addDays(start, 6) });
  }, [cursor]);

  const rangeLabel =
    view === "month"
      ? format(cursor, "MMMM yyyy")
      : `${format(weekDays[0], "MMM d")} – ${format(weekDays[6], "MMM d, yyyy")}`;

  function step(direction: -1 | 1) {
    setCursor((d) =>
      view === "month" ? addMonths(d, direction) : addWeeks(d, direction),
    );
  }

  function goCreate(dateKey?: string) {
    navigate(dateKey ? `/create?date=${dateKey}` : "/create");
  }

  function handleEntryClick(entry: CalendarEntryX) {
    setEditorRowId(entry.row_number);
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        greeting="Calendar"
        title="The year unfolds."
        subtitle="Every block a pillar, every column a day. The garden grows where you tend it."
        icon={CalendarIcon}
        right={
          <>
            <SegmentedControl
              aria-label="Calendar view"
              options={VIEW_OPTIONS}
              value={view}
              onChange={(id) => setView(id as CalendarView)}
            />
            <Button
              variant="outline"
              size="iconSm"
              className="fr"
              aria-label="Previous"
              onClick={() => step(-1)}
            >
              <ChevronLeft size={13} strokeWidth={1.75} aria-hidden="true" />
            </Button>
            <Button
              variant="soft"
              size="sm"
              className="fr"
              onClick={() => setCursor(new Date())}
            >
              Today
            </Button>
            <Button
              variant="outline"
              size="iconSm"
              className="fr"
              aria-label="Next"
              onClick={() => step(1)}
            >
              <ChevronRight size={13} strokeWidth={1.75} aria-hidden="true" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="fr"
              onClick={() => setPlanDialogOpen(true)}
            >
              <CalendarPlus size={13} strokeWidth={1.75} aria-hidden="true" />
              Plan week
            </Button>
            <Button
              variant="default"
              size="sm"
              className="fr"
              onClick={() => goCreate()}
            >
              <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
              New
            </Button>
          </>
        }
      />

      <div className="flex flex-1 items-stretch">
        {/* Main grid */}
        <div className="min-w-0 flex-1 p-6">
          <div className="t-label ink-muted mb-3">{rangeLabel}</div>

          {isLoading ? (
            <div
              role="status"
              aria-label="Loading calendar"
              className="border-hair bg-card rounded-2xl p-6"
            >
              <SkeletonText lines={8} />
            </div>
          ) : view === "week" ? (
            <WeekGrid
              weekDays={weekDays}
              entriesByDate={entriesByDate}
              colorFor={colorFor}
              onEntryClick={handleEntryClick}
              onAddSlot={(dateKey) => goCreate(dateKey)}
              onPlant={() => goCreate()}
            />
          ) : view === "month" ? (
            <MonthGrid
              cursor={cursor}
              entriesByDate={entriesByDate}
              colorFor={colorFor}
              onEntryClick={handleEntryClick}
            />
          ) : (
            <CalendarListView
              weekDays={weekDays}
              entriesByDate={entriesByDate}
              colorFor={colorFor}
              onEntryClick={handleEntryClick}
              onAddSlot={(dateKey) => goCreate(dateKey)}
            />
          )}
        </div>

        {/* Side rail: density + pillars + festivals */}
        <CalendarRail
          entriesByDate={entriesByDate}
          weekDays={weekDays}
          colorFor={colorFor}
          festivals={festivals}
        />
      </div>

      {/* Unified content editor */}
      <ContentEditorSheet
        rowId={editorRowId}
        mode="refine"
        onClose={() => setEditorRowId(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["calendar"] });
          setEditorRowId(null);
        }}
      />

      {/* AI calendar planning */}
      <CalendarPlanDialog
        open={planDialogOpen}
        onOpenChange={setPlanDialogOpen}
        defaultStart={format(
          view === "month"
            ? startOfMonth(cursor)
            : startOfWeek(cursor, { weekStartsOn: 1 }),
          "yyyy-MM-dd",
        )}
        defaultEnd={format(
          view === "month"
            ? endOfMonth(cursor)
            : endOfWeek(cursor, { weekStartsOn: 1 }),
          "yyyy-MM-dd",
        )}
      />
    </div>
  );
}
