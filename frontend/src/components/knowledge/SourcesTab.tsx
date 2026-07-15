import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Fingerprint, Globe, MessageSquare } from "lucide-react";
import { toast } from "sonner";

import { api, type KnowledgeSource } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { EmptyState, SkeletonText } from "@/components/pasture";

const SOURCE_LABELS: Record<string, string> = {
  gitavalley: "gitavalley.org (WordPress)",
  iskcon: "iskcongitanagari.org (WordPress)",
  facebook: "Facebook Page — Gita Valley",
  instagram: "Instagram — Gita Valley",
};

interface SourcesTabProps {
  sources: KnowledgeSource[];
  isLoading: boolean;
  /** True when the status fetch failed — render an honest error, not "nothing connected". */
  isError?: boolean;
  /** True while a crawl is running — Re-sync is disabled to avoid double runs. */
  crawlRunning: boolean;
}

export function SourcesTab({ sources, isLoading, isError, crawlRunning }: SourcesTabProps) {
  const queryClient = useQueryClient();

  const crawlMutation = useMutation({
    mutationFn: () => api.triggerCrawl(),
    onSuccess: (res) => {
      if (res.status === "already_running") {
        toast.info("A crawl is already running");
      } else {
        toast.success("Re-sync started — Claude is re-reading the site");
      }
      void queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: () => toast.error("Couldn't start the re-sync"),
  });

  const importMutation = useMutation({
    mutationFn: () => api.triggerSocialImport(),
    onSuccess: () => {
      toast.success("Social import started");
      void queryClient.invalidateQueries({ queryKey: ["knowledge"] });
    },
    onError: () => toast.error("Couldn't start the social import"),
  });

  const resync = (source: KnowledgeSource) => {
    if (source.type === "web") crawlMutation.mutate();
    else importMutation.mutate();
  };

  return (
    <div className="space-y-5 px-4 py-5 sm:px-8">
      <section aria-label="Connected sources">
        <div className="mb-2 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <h3 className="t-body-sm font-semibold text-sage-800 dark:text-sage-100">
            Connected sources
          </h3>
          <span className="t-caption ink-muted">
            From your .env — websites are hard-wired.
          </span>
        </div>

        {isLoading ? (
          <div className="bg-card border-hair rounded-xl p-4">
            <SkeletonText lines={4} />
          </div>
        ) : isError ? (
          // A failed fetch is not an empty library — no call-to-action here.
          <EmptyState
            title="Couldn't load this right now"
            body="Try again in a moment."
          />
        ) : sources.length === 0 ? (
          <EmptyState
            title="Nothing connected yet"
            body="Run a re-crawl to read gitavalley.org and iskcongitanagari.org, or import your Facebook history."
          />
        ) : (
          <div className="bg-card border-hair overflow-hidden rounded-xl">
            {sources.map((s, i) => {
              const isWeb = s.type === "web";
              const Icon = isWeb ? Globe : MessageSquare;
              const count = isWeb ? (s.page_count ?? 0) : (s.post_count ?? 0);
              const last = s.last_crawled ?? s.last_imported;
              const pending = isWeb ? crawlMutation.isPending : importMutation.isPending;
              return (
                <div
                  key={s.name}
                  className={cn(
                    "flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3",
                    i > 0 && "border-t",
                  )}
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-sage-50 text-sage-700 dark:bg-sage-800 dark:text-sage-200">
                    <Icon size={13} strokeWidth={1.75} aria-hidden="true" />
                  </div>
                  <div className="min-w-0 flex-1 basis-48">
                    <div className="t-body ink truncate font-medium">
                      {SOURCE_LABELS[s.name] ?? s.name}
                    </div>
                    <div className="t-caption ink-muted mt-0.5">
                      {isWeb ? "Website" : "Social"}
                    </div>
                  </div>
                  <div className="t-body-sm ink-muted">
                    <span className="font-mono font-semibold text-sage-800 dark:text-sage-100">
                      {count.toLocaleString()}
                    </span>{" "}
                    {isWeb ? "pages" : "posts"}
                  </div>
                  <div className="t-caption flex items-center gap-1.5 text-sage-700 dark:text-sage-200">
                    <span
                      className="h-1.5 w-1.5 rounded-full bg-sage-500"
                      aria-hidden="true"
                    />
                    {last
                      ? `Last: ${new Date(last).toLocaleDateString()}`
                      : "Not synced yet"}
                  </div>
                  <div className="ml-auto">
                    <Button
                      size="sm"
                      variant="outline"
                      className="fr"
                      onClick={() => resync(s)}
                      disabled={pending || crawlRunning}
                      aria-label={`Re-sync ${SOURCE_LABELS[s.name] ?? s.name}`}
                    >
                      Re-sync
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Verified: api/routes/knowledge.py skips pages whose stored SHA-256 matches. */}
      <div className="flex items-start gap-3 rounded-xl border border-sage-100 bg-sage-50 p-4 dark:border-sage-700 dark:bg-sage-800/60">
        <Fingerprint
          size={14}
          strokeWidth={1.75}
          aria-hidden="true"
          className="mt-0.5 shrink-0 text-sage-700 dark:text-sage-200"
        />
        <p className="t-body-sm leading-relaxed text-sage-800 dark:text-sage-100">
          <span className="font-semibold">Content-hash skip:</span> re-syncs compare each
          page's SHA-256 fingerprint against what's stored. Unchanged pages are skipped —
          no re-extraction, no extra calls to Claude.
        </p>
      </div>
    </div>
  );
}
