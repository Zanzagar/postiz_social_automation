export interface CrawlProgress {
  running: boolean;
  source: string;
  current: number;
  total: number;
  phase: string;
}

interface CrawlBannerProps {
  progress?: CrawlProgress;
}

/**
 * Crawl progress banner — only visible while a crawl is running.
 * Mirrors the real GET /api/knowledge/progress shape (source, phase, N/total).
 */
export function CrawlBanner({ progress }: CrawlBannerProps) {
  if (!progress?.running) return null;

  const pct =
    progress.total > 0
      ? Math.min(100, Math.round((progress.current / progress.total) * 100))
      : 0;

  return (
    <div className="border-hair-b flex items-center gap-3 bg-sage-50 px-4 py-3 sm:px-8 dark:bg-sage-800/60">
      <span
        className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-sage-600 border-t-transparent motion-reduce:animate-none dark:border-sage-300 dark:border-t-transparent"
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <div className="t-body-sm flex items-center justify-between gap-3">
          <span className="truncate text-sage-800 dark:text-sage-100">
            <span className="font-semibold">Crawling {progress.source}</span>
            {progress.phase && <span className="ink-muted"> · {progress.phase}</span>}
          </span>
          <span className="t-caption shrink-0 font-mono text-sage-700 dark:text-sage-200">
            {progress.current}/{progress.total}
          </span>
        </div>
        {progress.total > 0 && (
          <div
            role="progressbar"
            aria-label={`Crawling ${progress.source}`}
            aria-valuemin={0}
            aria-valuemax={progress.total}
            aria-valuenow={progress.current}
            className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sage-100 dark:bg-sage-700"
          >
            <div
              className="h-full bg-sage-600 transition-all dark:bg-sage-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
