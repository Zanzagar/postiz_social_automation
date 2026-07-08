import { useNavigate } from "react-router-dom";
import { BookOpen } from "lucide-react";

import { TextLink } from "@/components/pasture";
import type { KnowledgeStatusResponse } from "@/lib/api";

interface KnowledgeCardProps {
  knowledge?: KnowledgeStatusResponse;
}

/** Cream knowledge-base status card with the "Ask Claude" entry point. */
export function KnowledgeCard({ knowledge }: KnowledgeCardProps) {
  const navigate = useNavigate();
  const pages = (knowledge?.sources ?? []).reduce(
    (sum, s) => sum + (s.page_count ?? 0) + (s.post_count ?? 0),
    0,
  );

  return (
    <section className="rounded-2xl border border-cream-200 bg-cream-100/60 p-4 shadow-card dark:border-cream-400/30 dark:bg-cream-400/10">
      <div className="flex items-start gap-3">
        <div className="text-cream-ink flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cream-300 dark:bg-cream-400/30">
          <BookOpen size={15} strokeWidth={1.75} aria-hidden="true" />
        </div>
        <div className="flex-1">
          <div className="t-body-sm text-cream-ink-deep font-medium">Knowledge base</div>
          <div className="t-caption text-cream-ink/80 mt-0.5">
            {knowledge
              ? `${knowledge.knowledge_entries.toLocaleString()} entries · ${pages.toLocaleString()} pages indexed`
              : "Checking the library…"}
          </div>
          <TextLink
            className="t-caption mt-2 inline-block text-sage-700 hover:text-sage-800"
            onClick={() => navigate("/knowledge")}
          >
            Ask Claude a question →
          </TextLink>
        </div>
      </div>
    </section>
  );
}
