import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Flame,
  LayoutTemplate,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Sprout,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";

import { api, type SuggestionItem } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EmptyState, PageHeader, SkeletonText } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { ContentEditorSheet } from "@/components/content/ContentEditorSheet";

type SuggestionsData = { suggestions: SuggestionItem[] };

type Tone = "sage" | "terra" | "cream";

const TONE_STYLES: Record<Tone, string> = {
  sage: "border-sage-200 bg-sage-50 dark:border-sage-700 dark:bg-sage-800",
  terra:
    "border-terra-200 bg-terra-50 dark:border-terra-600 dark:bg-terra-700/30",
  cream:
    "border-cream-300 bg-cream-100/80 dark:border-cream-400/40 dark:bg-cream-400/15",
};

function toneFor(type: string): Tone {
  switch (type) {
    case "festival":
      return "terra";
    case "pillar_gap":
      return "sage";
    case "template":
      return "cream";
    default:
      return "sage";
  }
}

const TYPE_ICONS: Record<string, LucideIcon> = {
  festival: Flame,
  pillar_gap: Sprout,
  template: LayoutTemplate,
};

/** "pillar_gap" reads as "pillar"; other types just lose their underscores. */
function typeLabel(type: string): string {
  return type === "pillar_gap" ? "pillar" : type.replace(/_/g, " ");
}

/** "2026-03-26" → "Mar 26" */
function fmtDate(iso: string): string {
  const d = new Date(`${iso.split("T")[0]}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

interface SuggestionCardProps {
  suggestion: SuggestionItem;
  drafting: boolean;
  /** True while a Refresh is in flight — acting on a card mid-refresh races the new list. */
  refreshing: boolean;
  onDraft: () => void;
  onDismiss: () => void;
}

function SuggestionCard({
  suggestion: s,
  drafting,
  refreshing,
  onDraft,
  onDismiss,
}: SuggestionCardProps) {
  const Icon = TYPE_ICONS[s.type] ?? Lightbulb;
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl border p-5",
        TONE_STYLES[toneFor(s.type)],
      )}
    >
      <div className="flex items-start gap-3">
        <div className="bg-card border-hair flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sage-700 dark:text-sage-200">
          <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex flex-wrap items-center gap-2">
            <span className="t-label ink-muted">{typeLabel(s.type)}</span>
            {s.date && (
              <span className="t-micro ink-muted">· {fmtDate(s.date)}</span>
            )}
            {s.days_until != null && s.days_until >= 0 && (
              <span className="t-micro ink-muted font-mono">
                in {s.days_until}d
              </span>
            )}
          </div>
          <h3 className="t-title leading-tight text-sage-800 dark:text-sage-100">
            {s.title}
          </h3>
          <p className="t-body-sm ink-muted mt-1.5 leading-relaxed">{s.note}</p>
          <div className="mt-3 flex gap-2">
            <Button
              size="sm"
              className="fr"
              onClick={onDraft}
              disabled={drafting || refreshing}
              aria-disabled={drafting || refreshing}
            >
              <Sparkles size={12} strokeWidth={1.75} aria-hidden="true" />
              {drafting ? "Drafting…" : "Draft it"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="fr"
              onClick={onDismiss}
              disabled={refreshing}
              aria-disabled={refreshing}
            >
              Dismiss
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SuggestionsPage() {
  const queryClient = useQueryClient();
  const [openId, setOpenId] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => api.getSuggestions(),
  });
  const suggestions = data?.suggestions ?? [];

  // Ids removed from the list this session (dismissed or drafted). An
  // in-flight Refresh response must not resurrect them when it lands.
  const removedIdsRef = useRef<Set<number>>(new Set());

  const refreshMutation = useMutation({
    mutationFn: () => api.refreshSuggestions(),
    onSuccess: (res) =>
      queryClient.setQueryData<SuggestionsData>(["suggestions"], {
        suggestions: res.suggestions.filter(
          (s) => !removedIdsRef.current.has(s.id),
        ),
      }),
    onError: () =>
      toast.error("Couldn't refresh suggestions — try again in a moment."),
  });
  const { mutate: refreshNow, isPending: refreshing } = refreshMutation;

  const draftMutation = useMutation({
    mutationFn: (id: number) => api.draftSuggestion(id),
    onSuccess: (res, id) => {
      removedIdsRef.current.add(id);
      queryClient.setQueryData<SuggestionsData>(["suggestions"], (prev) =>
        prev
          ? { suggestions: prev.suggestions.filter((s) => s.id !== id) }
          : prev,
      );
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      toast.success("Draft started — refine it here.");
      setOpenId(res.content_row_id);
    },
    onError: () => toast.error("Couldn't draft that suggestion — try again."),
  });

  const dismissMutation = useMutation({
    mutationFn: (id: number) => api.dismissSuggestion(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["suggestions"] });
      removedIdsRef.current.add(id);
      const prev = queryClient.getQueryData<SuggestionsData>(["suggestions"]);
      queryClient.setQueryData<SuggestionsData>(["suggestions"], (cur) =>
        cur ? { suggestions: cur.suggestions.filter((s) => s.id !== id) } : cur,
      );
      return { prev };
    },
    onError: (_err, id, ctx) => {
      removedIdsRef.current.delete(id);
      if (ctx?.prev) queryClient.setQueryData(["suggestions"], ctx.prev);
      toast.error("Couldn't dismiss that suggestion.");
    },
    onSuccess: () => toast.success("Dismissed."),
  });

  // Self-seed: on the FIRST successful fetch only, an empty list means the
  // generator hasn't run yet — ask the backend once so the page fills itself.
  const seededRef = useRef(false);
  useEffect(() => {
    if (!data || seededRef.current) return;
    seededRef.current = true;
    if (data.suggestions.length === 0) refreshNow();
  }, [data, refreshNow]);

  // While the self-seed (or a refresh from empty) runs, stay on the skeleton
  // instead of flashing the empty state.
  const showSkeleton = isLoading || (refreshing && suggestions.length === 0);

  const refreshButton = (
    <Button
      variant="outline"
      size="sm"
      className="fr"
      onClick={() => refreshNow()}
      disabled={refreshing}
    >
      <RefreshCw
        size={12}
        strokeWidth={1.75}
        aria-hidden="true"
        className={cn(refreshing && "animate-spin motion-reduce:animate-none")}
      />
      {refreshing ? "Refreshing…" : "Refresh"}
    </Button>
  );

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        greeting="Suggestions"
        title="What the season is asking for."
        subtitle="Pulled from the festival calendar, your pillar balance, the knowledge base, and what's trending."
        icon={Lightbulb}
        right={refreshButton}
      />

      <div className="flex-1 px-4 py-6 sm:px-8">
        {showSkeleton ? (
          <div
            role="status"
            aria-label="Loading suggestions"
            className="grid max-w-5xl grid-cols-1 gap-4 md:grid-cols-2"
          >
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="bg-card border-hair rounded-2xl p-5">
                <SkeletonText lines={3} />
              </div>
            ))}
          </div>
        ) : isError ? (
          <EmptyState
            icon={Lightbulb}
            title="Suggestions are resting."
            body="We couldn't reach the field just now — try a refresh."
            action={refreshButton}
          />
        ) : suggestions.length === 0 ? (
          <EmptyState
            icon={Lightbulb}
            title="The season is quiet."
            body="Refresh to ask again."
            action={refreshButton}
          />
        ) : (
          <div className="grid max-w-5xl grid-cols-1 gap-4 md:grid-cols-2">
            {suggestions.map((s) => (
              <SuggestionCard
                key={s.id}
                suggestion={s}
                drafting={
                  draftMutation.isPending && draftMutation.variables === s.id
                }
                refreshing={refreshing}
                onDraft={() => {
                  if (!draftMutation.isPending) draftMutation.mutate(s.id);
                }}
                onDismiss={() => dismissMutation.mutate(s.id)}
              />
            ))}
          </div>
        )}
      </div>

      <ContentEditorSheet
        rowId={openId}
        mode="refine"
        onClose={() => setOpenId(null)}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ["drafts"] });
          setOpenId(null);
        }}
      />
    </div>
  );
}
