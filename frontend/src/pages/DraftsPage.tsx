import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  ClipboardCheck,
  Filter,
  Loader2,
  Plus,
} from "lucide-react";
import { toast } from "sonner";

import { api, type ContentRow, type Pillar } from "@/lib/api";
import { cn } from "@/lib/utils";
import { EmptyState, PageHeader, SkeletonText } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { ContentEditorSheet } from "@/components/content/ContentEditorSheet";
import { DraftRow } from "@/components/content/DraftRow";
import { draftTitle } from "@/components/content/draft-utils";

const FILTERS = [
  { id: "all", label: "All", statuses: null },
  { id: "needs-review", label: "Needs review", statuses: ["pending_approval"] },
  { id: "draft", label: "In progress", statuses: ["draft"] },
  { id: "scheduled", label: "Scheduled", statuses: ["approved", "scheduled"] },
  { id: "posted", label: "Posted", statuses: ["posted"] },
] as const;

type FilterId = (typeof FILTERS)[number]["id"];

export function DraftsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: allDrafts, isLoading } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api.getDrafts(),
  });

  const { data: pillars } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
    staleTime: 60_000,
  });

  const pillarByName = useMemo(() => {
    const map = new Map<string, Pillar>();
    for (const p of pillars ?? []) map.set(p.name, p);
    return map;
  }, [pillars]);

  const drafts = useMemo(
    () =>
      [...(allDrafts ?? [])].sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
      ),
    [allDrafts],
  );

  const [filter, setFilter] = useState<FilterId>("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [isApproving, setIsApproving] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);

  const counts = useMemo(() => {
    const c: Record<FilterId, number> = {
      all: drafts.length,
      "needs-review": 0,
      draft: 0,
      scheduled: 0,
      posted: 0,
    };
    for (const d of drafts) {
      for (const f of FILTERS) {
        if (f.statuses && (f.statuses as readonly string[]).includes(d.status)) {
          c[f.id] += 1;
        }
      }
    }
    return c;
  }, [drafts]);

  const filtered = useMemo(() => {
    const def = FILTERS.find((f) => f.id === filter);
    if (!def?.statuses) return drafts;
    return drafts.filter((d) =>
      (def.statuses as readonly string[]).includes(d.status),
    );
  }, [drafts, filter]);

  // --- Auto-publish hold / resume (optimistic) ---

  const holdMutation = useMutation({
    mutationFn: (id: number) => api.holdContent(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["drafts"] });
      const prev = queryClient.getQueryData<ContentRow[]>(["drafts"]);
      queryClient.setQueryData<ContentRow[]>(["drafts"], (rows) =>
        rows?.map((r) =>
          r.row_number === id ? { ...r, held_at: new Date().toISOString() } : r,
        ),
      );
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["drafts"], ctx.prev);
      toast.error("Couldn't hold this post");
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["drafts"] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => api.resumeContent(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["drafts"] });
      const prev = queryClient.getQueryData<ContentRow[]>(["drafts"]);
      queryClient.setQueryData<ContentRow[]>(["drafts"], (rows) =>
        rows?.map((r) => (r.row_number === id ? { ...r, held_at: null } : r)),
      );
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["drafts"], ctx.prev);
      toast.error("Couldn't resume auto-release");
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["drafts"] }),
  });

  // --- Batch approve ---

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBatchApprove() {
    const ids = [...selected];
    setIsApproving(true);
    const results = await Promise.allSettled(
      ids.map((id) => api.approveDraft(id)),
    );
    const failedIds: number[] = [];
    results.forEach((res, i) => {
      if (res.status === "rejected") {
        failedIds.push(ids[i]);
        const row = drafts.find((d) => d.row_number === ids[i]);
        toast.error(
          `Couldn't approve "${row ? draftTitle(row.raw_text) : `draft ${ids[i]}`}"`,
        );
      }
    });
    const okCount = ids.length - failedIds.length;
    if (okCount > 0) {
      toast.success(
        okCount === 1 ? "1 draft approved" : `${okCount} drafts approved`,
      );
    }
    setSelected(new Set(failedIds));
    setIsApproving(false);
    queryClient.invalidateQueries({ queryKey: ["drafts"] });
  }

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        greeting="Drafts"
        title="The workbench"
        subtitle="Everything in motion. Review, refine, and send on."
        icon={ClipboardCheck}
        right={
          <>
            <Button variant="outline" size="sm" className="fr">
              <Filter size={12} strokeWidth={1.75} aria-hidden="true" />
              Filter
            </Button>
            <Button
              variant="default"
              size="sm"
              className="fr"
              onClick={() => navigate("/create")}
            >
              <Plus size={12} strokeWidth={1.75} aria-hidden="true" />
              New draft
            </Button>
          </>
        }
      />

      <div className="border-hair-b flex flex-wrap items-center gap-1.5 px-8 pt-4 pb-2">
        {FILTERS.map((f) => {
          const active = filter === f.id;
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              aria-pressed={active}
              className={cn(
                "fr t-body-sm flex h-8 items-center gap-1.5 rounded-full px-3 font-medium transition",
                active
                  ? "bg-sage-500 text-white"
                  : "bg-card border-hair ink hover:bg-sage-50 dark:hover:bg-sage-800",
              )}
            >
              {f.label}
              <span
                className={cn(
                  "t-micro rounded-full px-1.5 py-px",
                  active ? "bg-white/20" : "bg-warm ink-muted",
                )}
              >
                {counts[f.id]}
              </span>
            </button>
          );
        })}
      </div>

      <div className="flex-1 px-8 py-5 pb-24">
        {isLoading ? (
          <div
            role="status"
            aria-label="Loading drafts"
            className="space-y-2.5"
          >
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="bg-card border-hair rounded-2xl px-5 py-4">
                <SkeletonText lines={2} />
              </div>
            ))}
          </div>
        ) : drafts.length === 0 ? (
          <EmptyState
            title="Nothing on the workbench yet…"
            action={
              <Button
                variant="default"
                size="sm"
                className="fr"
                onClick={() => navigate("/create")}
              >
                Start a post
              </Button>
            }
          />
        ) : filtered.length === 0 ? (
          <p className="t-body-sm ink-muted py-10 text-center">
            Nothing in this view.
          </p>
        ) : (
          <div className="space-y-2.5">
            {filtered.map((d) => (
              <DraftRow
                key={d.row_number}
                draft={d}
                pillar={
                  d.content_pillar
                    ? (pillarByName.get(d.content_pillar) ?? d.content_pillar)
                    : null
                }
                selectable={d.status === "pending_approval"}
                selected={selected.has(d.row_number)}
                onToggleSelect={() => toggleSelect(d.row_number)}
                onOpen={() => setOpenId(d.row_number)}
                onHold={() => holdMutation.mutate(d.row_number)}
                onResume={() => resumeMutation.mutate(d.row_number)}
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

      {selected.size > 0 && (
        <div className="bg-card border-hair fixed inset-x-0 bottom-0 z-40 px-8 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-lg md:left-60 md:pb-3">
          <div className="flex items-center justify-between">
            <span className="t-body-sm ink font-medium">
              {selected.size} selected
            </span>
            <Button
              variant="default"
              size="sm"
              className="fr"
              onClick={handleBatchApprove}
              disabled={isApproving}
            >
              {isApproving ? (
                <Loader2
                  size={14}
                  strokeWidth={1.75}
                  className="animate-spin"
                  aria-hidden="true"
                />
              ) : (
                <CheckCircle2 size={14} strokeWidth={1.75} aria-hidden="true" />
              )}
              Approve {selected.size}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
