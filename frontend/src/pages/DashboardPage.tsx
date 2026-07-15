import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Moon, Plus, Search, Sparkles, Sunrise, type LucideIcon } from "lucide-react";

import { api, type ContentRow } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/pasture";
import { useDashboardData, type TimelineItem } from "@/hooks/useDashboardData";
import { RitualStrip } from "@/components/dashboard/RitualStrip";
import { TodayTimeline } from "@/components/dashboard/TodayTimeline";
import { PillarBalanceCard } from "@/components/dashboard/PillarBalanceCard";
import { HorizonCard } from "@/components/dashboard/HorizonCard";
import { BlessingCard } from "@/components/dashboard/BlessingCard";
import { PulseCard } from "@/components/dashboard/PulseCard";
import { KnowledgeCard } from "@/components/dashboard/KnowledgeCard";

interface Greeting {
  kicker: string;
  title: string;
  icon: LucideIcon;
}

function greetingFor(now: Date): Greeting {
  const hour = now.getHours();
  if (hour < 12) return { kicker: "Morning Review", title: "Good morning.", icon: Sunrise };
  if (hour < 17)
    return { kicker: "Afternoon Check-in", title: "Good afternoon.", icon: Sparkles };
  return { kicker: "Evening Publish", title: "Good evening.", icon: Moon };
}

function plural(n: number, singular: string, pluralForm: string): string {
  return n === 1 ? singular : pluralForm;
}

export function DashboardPage() {
  const {
    isLoading,
    stats,
    timeline,
    pendingDrafts,
    pillars,
    pillarBalance,
    festivals,
    overview,
    summary,
    summaryError,
    summaryLoading,
    pulseSeries,
    knowledge,
  } = useDashboardData();

  const now = new Date();
  const greeting = greetingFor(now);
  const dateStr = now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const qc = useQueryClient();
  const holdMutation = useMutation({
    mutationFn: ({ id, held }: { id: number; held: boolean }) =>
      held ? api.resumeContent(id) : api.holdContent(id),
    onMutate: async ({ id, held }) => {
      await qc.cancelQueries({ queryKey: ["drafts"] });
      const prev = qc.getQueryData<ContentRow[]>(["drafts"]);
      qc.setQueryData<ContentRow[]>(["drafts"], (rows) =>
        rows?.map((r) =>
          r.row_number === id
            ? { ...r, held_at: held ? null : new Date().toISOString() }
            : r,
        ),
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(["drafts"], ctx.prev);
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  const handleToggleHold = (item: TimelineItem) => {
    holdMutation.mutate({ id: item.id, held: item.held });
  };

  const subtitle = isLoading
    ? undefined
    : `${stats.postedToday} ${plural(stats.postedToday, "post has", "posts have")} gone out, ` +
      `${stats.awaitingReview} ${plural(stats.awaitingReview, "is", "are")} ready for your blessing, ` +
      `and ${stats.scheduledToday} ${plural(stats.scheduledToday, "is", "are")} scheduled for today.`;

  return (
    <div>
      <PageHeader
        greeting={`${greeting.kicker} · ${dateStr}`}
        title={greeting.title}
        subtitle={subtitle}
        icon={greeting.icon}
        right={
          <>
            <Button
              variant="soft"
              size="sm"
              className="fr"
              onClick={() =>
                window.dispatchEvent(new CustomEvent("gv:open-command-palette"))
              }
            >
              <Search size={13} strokeWidth={1.75} aria-hidden="true" />
              Search…
              <span className="t-micro bg-card ml-1 rounded border border-sage-100 px-1 py-0.5 font-mono dark:border-sage-700">
                ⌘K
              </span>
            </Button>
            <Button size="sm" asChild className="fr">
              <Link to="/create">
                <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
                Compose
              </Link>
            </Button>
          </>
        }
      />

      <div className="grid gap-6 px-4 py-7 sm:px-8 xl:grid-cols-[minmax(0,1fr)_340px]">
        {/* LEFT COLUMN */}
        <div className="min-w-0 space-y-6">
          <RitualStrip stats={stats} isLoading={isLoading} />
          <TodayTimeline
            items={timeline}
            pillars={pillars}
            now={now}
            isLoading={isLoading}
            onToggleHold={handleToggleHold}
          />
          <div className="grid gap-5 md:grid-cols-2">
            <PillarBalanceCard rows={pillarBalance} isLoading={isLoading} />
            <HorizonCard festivals={festivals} isLoading={isLoading} />
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="min-w-0 space-y-6">
          <BlessingCard pendingDrafts={pendingDrafts} />
          <PulseCard
            summary={summary}
            summaryError={summaryError}
            overview={overview}
            series={pulseSeries}
            isLoading={isLoading || summaryLoading}
          />
          <KnowledgeCard knowledge={knowledge} />
        </div>
      </div>
    </div>
  );
}
