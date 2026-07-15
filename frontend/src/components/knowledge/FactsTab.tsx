import { useMemo, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, ChevronLeft, ChevronRight, Copy, Globe, Search } from "lucide-react";
import { toast } from "sonner";

import { api, type KnowledgeSource, type KnowledgeStats, type Pillar } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Chip,
  EmptyState,
  PastureTabs,
  PillarChip,
  SkeletonText,
  type ChipTone,
} from "@/components/pasture";

const ALL = "all";

/** Design fact-type palette mapped into brand Chip tones (no blue/purple tokens exist). */
const FACT_TYPE_TONES: Record<string, ChipTone> = {
  program: "sage",
  event: "terra",
  quote: "cream",
  link: "sage",
  description: "neutral",
};

/** Common shape across browse (full) and search (no topic/keywords) results. */
interface FactCardData {
  id: number;
  fact_type: string;
  content: string;
  pillar: string | null;
  topic?: string | null;
  keywords?: string[];
  page_title: string | null;
  site: string | null;
}

interface FactsTabProps {
  pillars: Pillar[];
  stats?: KnowledgeStats;
  sources: KnowledgeSource[];
}

function capitalize(s: string): string {
  return s.length === 0 ? s : s[0].toUpperCase() + s.slice(1);
}

async function copyFact(content: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(content);
    toast.success("Fact copied to clipboard");
  } catch {
    toast.error("Couldn't copy — try selecting the text instead");
  }
}

export function FactsTab({ pillars, stats, sources }: FactsTabProps) {
  const [queryInput, setQueryInput] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [pillar, setPillar] = useState(ALL);
  const [factType, setFactType] = useState(ALL);
  const [site, setSite] = useState(ALL);
  const [page, setPage] = useState(1);

  const searching = submittedQuery.length > 0;

  const browse = useQuery({
    queryKey: ["knowledge", "browse", pillar, factType, site, page],
    queryFn: () =>
      api.browseKnowledge({
        pillar: pillar === ALL ? undefined : pillar,
        fact_type: factType === ALL ? undefined : factType,
        site: site === ALL ? undefined : site,
        page,
      }),
    enabled: !searching,
  });

  const search = useQuery({
    queryKey: ["knowledge", "search", submittedQuery, pillar],
    queryFn: () =>
      api.searchKnowledge(submittedQuery, pillar === ALL ? undefined : pillar),
    enabled: searching,
  });

  const typeOptions = useMemo(
    () =>
      [...(stats?.by_type ?? [])]
        .sort((a, b) => b.count - a.count)
        .map((t) => t.type),
    [stats],
  );
  const siteOptions = useMemo(
    () => sources.filter((s) => s.type === "web").map((s) => s.name),
    [sources],
  );

  // Search results lack server-side type/site filtering — filter honestly on the client.
  const facts: FactCardData[] = useMemo(() => {
    if (searching) {
      return (search.data?.results ?? []).filter(
        (f) =>
          (factType === ALL || f.fact_type === factType) &&
          (site === ALL || f.site === site),
      );
    }
    return browse.data?.results ?? [];
  }, [searching, search.data, browse.data, factType, site]);

  const totalCount = searching ? (search.data?.count ?? 0) : (browse.data?.total ?? 0);
  const isLoading = searching ? search.isLoading : browse.isLoading;
  const isError = searching ? search.isError : browse.isError;
  const totalPages = browse.data?.total_pages ?? 1;

  const anyFilterActive =
    pillar !== ALL || factType !== ALL || site !== ALL || searching || queryInput !== "";

  const clearFilters = () => {
    setPillar(ALL);
    setFactType(ALL);
    setSite(ALL);
    setQueryInput("");
    setSubmittedQuery("");
    setPage(1);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSubmittedQuery(queryInput.trim());
    setPage(1);
  };

  return (
    <div className="px-4 py-4 sm:px-8">
      {/* Search + filters */}
      <div className="space-y-2.5">
        <form role="search" onSubmit={handleSubmit} className="flex items-center gap-2">
          <label htmlFor="knowledge-search" className="sr-only">
            Search facts
          </label>
          <div className="relative max-w-xl flex-1">
            <Search
              size={13}
              strokeWidth={1.75}
              aria-hidden="true"
              className="ink-muted absolute top-1/2 left-3 -translate-y-1/2"
            />
            <input
              id="knowledge-search"
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder="Search facts, programs, events, quotes…"
              className="fr bg-card border-hair t-body ink h-9 w-full rounded-lg pr-3 pl-8 outline-none"
            />
          </div>
          <Button type="submit" size="sm" variant="soft" className="fr">
            Search
          </Button>
          {!isLoading && !isError && (
            <span className="t-caption ink-muted font-mono whitespace-nowrap">
              {facts.length} of {totalCount}
            </span>
          )}
        </form>

        <div className="t-caption flex flex-wrap items-center gap-x-4 gap-y-2">
          <FilterRow
            label="Pillar"
            value={pillar}
            onChange={(v) => {
              setPillar(v);
              setPage(1);
            }}
            options={pillars.map((p) => p.name)}
          />
          <FilterRow
            label="Type"
            value={factType}
            onChange={(v) => {
              setFactType(v);
              setPage(1);
            }}
            options={typeOptions}
          />
          <FilterRow
            label="Site"
            value={site}
            onChange={(v) => {
              setSite(v);
              setPage(1);
            }}
            options={siteOptions}
          />
          {anyFilterActive && (
            <button
              type="button"
              onClick={clearFilters}
              className="fr t-caption rounded text-sage-600 hover:underline dark:text-sage-300"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Fact list */}
      <div className="mt-4 space-y-2">
        {isLoading ? (
          <div role="status" aria-label="Loading facts" className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="bg-card border-hair rounded-xl p-3.5">
                <SkeletonText lines={2} />
              </div>
            ))}
          </div>
        ) : isError ? (
          // A failed fetch is not an empty library — no call-to-action here.
          <EmptyState
            title="Couldn't load this right now"
            body="Try again in a moment."
          />
        ) : facts.length === 0 ? (
          <EmptyState
            icon={Search}
            title="Nothing in the hayloft for that"
            body={
              anyFilterActive
                ? "No facts match those filters. Try loosening them or clearing the search."
                : "Claude hasn't read anything yet — run a re-crawl to fill the library."
            }
          />
        ) : (
          facts.map((f) => <FactCard key={f.id} fact={f} pillars={pillars} />)
        )}
      </div>

      {/* Server-side pagination (browse mode only) */}
      {!searching && !isLoading && !isError && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="t-caption ink-muted font-mono">
            Page {browse.data?.page ?? page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <Button
              size="sm"
              variant="outline"
              className="fr"
              aria-label="Previous page"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft size={13} strokeWidth={1.75} aria-hidden="true" />
              Prev
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="fr"
              aria-label="Next page"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
              <ChevronRight size={13} strokeWidth={1.75} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

interface FilterRowProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}

function FilterRow({ label, value, onChange, options }: FilterRowProps) {
  if (options.length === 0) return null;
  return (
    <div className="flex items-center gap-1.5">
      <span className="t-label ink-muted">{label}</span>
      <PastureTabs
        variant="pill"
        aria-label={`Filter by ${label.toLowerCase()}`}
        value={value}
        onChange={onChange}
        items={[
          { id: ALL, label: "All" },
          ...options.map((o) => ({ id: o, label: capitalize(o) })),
        ]}
      />
    </div>
  );
}

function FactCard({ fact, pillars }: { fact: FactCardData; pillars: Pillar[] }) {
  const pillarObj = pillars.find((p) => p.name === fact.pillar);
  return (
    <article className="group bg-card border-hair shadow-card rounded-xl p-3.5 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <p className="t-body ink flex-1 font-serif leading-relaxed">{fact.content}</p>
        <Chip
          tone={FACT_TYPE_TONES[fact.fact_type] ?? "neutral"}
          className="shrink-0 capitalize"
        >
          {fact.fact_type}
        </Chip>
      </div>
      <div className="t-caption ink-muted mt-2.5 flex flex-wrap items-center gap-2">
        {fact.pillar && <PillarChip pillar={pillarObj ?? fact.pillar} size="xs" />}
        {fact.topic && <Chip tone="neutral" className="t-micro">{fact.topic}</Chip>}
        {fact.site && (
          <span className="flex items-center gap-1">
            <Globe size={10} strokeWidth={1.75} aria-hidden="true" />
            {fact.site}
          </span>
        )}
        {fact.page_title && (
          <span className="flex max-w-[220px] items-center gap-1 truncate">
            <BookOpen size={10} strokeWidth={1.75} aria-hidden="true" className="shrink-0" />
            <span className="truncate">{fact.page_title}</span>
          </span>
        )}
        <button
          type="button"
          aria-label="Copy fact"
          onClick={() => void copyFact(fact.content)}
          className="fr ml-auto flex h-6 items-center gap-1 rounded-md px-2 text-sage-600 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 hover:bg-sage-50 focus-visible:opacity-100 dark:text-sage-300 dark:hover:bg-sage-800"
        >
          <Copy size={11} strokeWidth={1.75} aria-hidden="true" />
          Copy
        </button>
      </div>
      {(fact.keywords?.length ?? 0) > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1">
          {fact.keywords?.slice(0, 5).map((k) => (
            <span
              key={k}
              className={cn(
                "t-micro rounded px-1.5 py-0.5 font-mono",
                "bg-sage-50 text-sage-600 dark:bg-sage-800 dark:text-sage-300",
              )}
            >
              #{k}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
