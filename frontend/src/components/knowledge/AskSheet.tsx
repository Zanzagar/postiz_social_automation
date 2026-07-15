import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { BookOpen, Globe, Search, Sparkles } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { EmptyState, GVSheet, SkeletonText } from "@/components/pasture";

const SUGGESTIONS = [
  "What festivals are coming up?",
  "Who are our named cows?",
  "What is our stance on dairy?",
  "When did we last post about volunteering?",
];

interface AskSheetProps {
  onClose: () => void;
}

/** "Ask the farm" — grounded Q&A over the knowledge base (POST /api/knowledge/ask). */
export function AskSheet({ onClose }: AskSheetProps) {
  const [question, setQuestion] = useState("");

  const ask = useMutation({
    mutationFn: (q: string) => api.askKnowledge(q),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (q && !ask.isPending) ask.mutate(q);
  };

  const result = ask.data;

  return (
    <GVSheet title="Ask the farm" onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <label htmlFor="ask-knowledge-input" className="sr-only">
          Ask what Claude knows
        </label>
        <div className="flex h-10 items-center gap-2 rounded-full border border-sage-100 bg-sage-50 px-3 dark:border-sage-700 dark:bg-sage-800">
          <Search
            size={13}
            strokeWidth={1.75}
            aria-hidden="true"
            className="shrink-0 text-sage-600 dark:text-sage-300"
          />
          <input
            id="ask-knowledge-input"
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What do you want to know?"
            className="t-body ink fr min-w-0 flex-1 rounded bg-transparent outline-none"
          />
          <Button
            type="submit"
            size="sm"
            className="fr shrink-0"
            disabled={ask.isPending || question.trim().length === 0}
          >
            Ask
          </Button>
        </div>
      </form>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="t-caption ink-muted">Try:</span>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setQuestion(s)}
            className="fr t-caption bg-card border-hair h-6 rounded-md px-2 text-sage-700 hover:bg-sage-50 dark:text-sage-200 dark:hover:bg-sage-800"
          >
            {s}
          </button>
        ))}
      </div>

      {ask.isPending && <SkeletonText lines={4} className="mt-6" />}

      {ask.isError && (
        <p className="t-caption ink-muted mt-6">
          The library didn't answer just now — give it a moment and try again.
        </p>
      )}

      {result && !ask.isPending && (
        <div className="mt-6">
          {!result.answer && result.sources.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="Nothing on that yet"
              body="Claude hasn't read anything matching that question. A re-crawl might turn something up."
            />
          ) : (
            <div className="flex items-start gap-2.5">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sage-100 text-sage-700 dark:bg-sage-800 dark:text-sage-200">
                <Sparkles size={13} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                {result.answered_by === "claude" && result.answer && (
                  <p className="t-body ink font-serif leading-relaxed">
                    {result.answer}
                  </p>
                )}
                {result.answered_by === "search_only" && (
                  <p className="t-caption ink-muted">
                    Here's what I found — a written answer wasn't available just now.
                  </p>
                )}

                {result.sources.length > 0 && (
                  <>
                    <div className="t-label mt-3 text-sage-700 dark:text-sage-300">
                      Sources Claude used
                    </div>
                    <ul className="mt-1.5 space-y-1">
                      {result.sources.map((src, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 rounded-lg border border-sage-100 bg-sage-50 px-3 py-2 dark:border-sage-700 dark:bg-sage-800/60"
                        >
                          <div className="bg-card border-hair flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-sage-700 dark:text-sage-200">
                            <BookOpen size={11} strokeWidth={1.75} aria-hidden="true" />
                          </div>
                          <div className="min-w-0 flex-1">
                            {src.page_title && (
                              <div className="t-body-sm truncate font-medium text-sage-800 dark:text-sage-100">
                                {src.page_title}
                              </div>
                            )}
                            <p className="t-caption ink-muted mt-0.5 line-clamp-2 font-serif italic">
                              {src.content}
                            </p>
                            {src.site && (
                              <div className="t-micro ink-muted mt-1 flex items-center gap-1">
                                <Globe size={9} strokeWidth={1.75} aria-hidden="true" />
                                {src.site}
                              </div>
                            )}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </GVSheet>
  );
}
