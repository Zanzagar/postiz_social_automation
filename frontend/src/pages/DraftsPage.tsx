import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type ContentRow } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { ContentEditor } from "@/components/content/ContentEditor";
import { CheckCircle, Loader2 } from "lucide-react";

export function DraftsPage() {
  const queryClient = useQueryClient();
  const { data: allDrafts, isLoading } = useQuery({
    queryKey: ["drafts"],
    queryFn: () => api.getDrafts(),
  });

  const drafts = allDrafts?.filter((d) => d.status === "draft") ?? [];

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [editedCaptions, setEditedCaptions] = useState<
    Record<number, Record<string, string>>
  >({});
  const [isApproving, setIsApproving] = useState(false);
  const [selectedDraft, setSelectedDraft] = useState<ContentRow | null>(null);

  function toggleSelect(rowNumber: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(rowNumber)) next.delete(rowNumber);
      else next.add(rowNumber);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === drafts.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(drafts.map((d) => d.row_number)));
    }
  }

  async function handleBatchApprove() {
    setIsApproving(true);
    try {
      // Save any edits first, then approve
      for (const rowNumber of selected) {
        const edits = editedCaptions[rowNumber];
        if (edits) {
          await api.editDraft(rowNumber, edits);
        }
        await api.approveDraft(rowNumber);
      }
      setSelected(new Set());
      setEditedCaptions({});
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    } finally {
      setIsApproving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Review Drafts</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  if (drafts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <CheckCircle className="mb-4 h-12 w-12 text-sage-400" />
        <h2 className="text-xl font-semibold text-sage-700">All caught up!</h2>
        <p className="mt-1 text-muted-foreground">No pending drafts to review.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6 pb-24">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sage-800">Review Drafts</h1>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={selected.size === drafts.length}
            onCheckedChange={toggleSelectAll}
            aria-label="Select all"
          />
          Select all
        </label>
      </div>

      {/* Draft cards */}
      {drafts.map((draft) => (
        <DraftCard
          key={draft.row_number}
          draft={draft}
          isSelected={selected.has(draft.row_number)}
          onToggleSelect={() => toggleSelect(draft.row_number)}
          onClick={() => setSelectedDraft(draft)}
        />
      ))}

      {/* ContentEditor modal */}
      <ContentEditor
        contentRow={selectedDraft}
        mode="refine"
        isOpen={!!selectedDraft}
        onClose={() => setSelectedDraft(null)}
        onSave={() => {
          queryClient.invalidateQueries({ queryKey: ["drafts"] });
          setSelectedDraft(null);
        }}
      />

      {/* Batch actions bar */}
      {selected.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-lg md:bottom-0 md:left-60 md:pb-3">
          <div className="mx-auto flex max-w-2xl items-center justify-between">
            <span className="text-sm font-medium">
              {selected.size} selected
            </span>
            <Button onClick={handleBatchApprove} disabled={isApproving}>
              {isApproving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="mr-2 h-4 w-4" />
              )}
              Approve & Send to Postiz
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

const platformLabels: Record<string, string> = {
  instagram: "IG",
  facebook: "FB",
  tiktok: "TT",
  threads: "TH",
  linkedin: "LI",
};

function DraftCard({
  draft,
  isSelected,
  onToggleSelect,
  onClick,
}: {
  draft: ContentRow;
  isSelected: boolean;
  onToggleSelect: () => void;
  onClick: () => void;
}) {
  const platforms = Object.entries(draft.platforms)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <Card className={`cursor-pointer transition-colors hover:bg-muted/30 ${isSelected ? "ring-2 ring-sage-400" : ""}`}>
      <CardHeader className="flex flex-row items-start gap-3 pb-2">
        <Checkbox
          checked={isSelected}
          onCheckedChange={onToggleSelect}
          className="mt-1"
        />
        <div className="flex-1 space-y-1" onClick={onClick} role="button" tabIndex={0}>
          <p className="text-sm font-medium leading-tight">
            {draft.raw_text.length > 100
              ? draft.raw_text.slice(0, 100) + "..."
              : draft.raw_text}
          </p>
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>{draft.date}</span>
            {draft.content_pillar && (
              <Badge variant="secondary" className="text-xs px-1.5 py-0">
                {draft.content_pillar}
              </Badge>
            )}
            {draft.source === "template" && (
              <Badge variant="outline" className="text-xs px-1.5 py-0">
                Template
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent onClick={onClick}>
        <div className="flex gap-1.5">
          {platforms.map((p) => (
            <Badge key={p} variant="secondary" className="text-xs">
              {platformLabels[p] ?? p}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
