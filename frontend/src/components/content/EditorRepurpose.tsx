import { Chip, PlatformDots } from "@/components/pasture";
import { Textarea } from "@/components/ui/textarea";
import type { ContentRow } from "@/lib/api";
import { pillarColor } from "@/lib/pillars";
import { platformBy } from "@/lib/platforms";

interface EditorRepurposeProps {
  row: ContentRow;
  title: string;
  platforms: string[];
  chips: string[];
  onRemoveChip: (chip: string) => void;
  direction: string;
  onDirectionChange: (value: string) => void;
}

/**
 * Repurpose mode body — the source post, removable "carry forward" chips,
 * and a new-direction prompt. Generation creates a NEW draft; the original
 * post is never touched.
 */
export function EditorRepurpose({
  row,
  title,
  platforms,
  chips,
  onRemoveChip,
  direction,
  onDirectionChange,
}: EditorRepurposeProps) {
  const labels = platforms.map((id) => platformBy(id).label).join(" + ");
  const postedDay = row.posted_at
    ? new Date(row.posted_at).toLocaleDateString([], { weekday: "short" })
    : null;

  return (
    <div className="space-y-5">
      <div className="bg-warm border-hair rounded-xl p-4">
        <div className="t-label ink-muted mb-2">
          {postedDay ? `Posted ${postedDay} · the source` : "The source"}
        </div>
        <div className="flex items-center gap-3">
          <span
            className="h-9 w-1 shrink-0 rounded-sm"
            style={{ background: pillarColor(row.content_pillar ?? "") }}
            aria-hidden="true"
          />
          <div className="min-w-0 flex-1">
            <div className="t-body ink font-medium">{title}</div>
            <div className="t-micro ink-muted">{labels}</div>
          </div>
          <PlatformDots ids={platforms} size={16} />
        </div>
      </div>

      <div>
        <div className="t-label ink-muted mb-2">Carry forward</div>
        {chips.length === 0 ? (
          <p className="t-caption ink-muted">
            Nothing carried — Claude starts from the source post alone.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {chips.map((chip) => (
              <Chip key={chip} tone="sage" removable onRemove={() => onRemoveChip(chip)}>
                {chip}
              </Chip>
            ))}
          </div>
        )}
      </div>

      <div>
        <label htmlFor="new-direction" className="t-label ink-muted mb-1.5 block">
          New direction
        </label>
        <Textarea
          id="new-direction"
          rows={3}
          value={direction}
          onChange={(e) => onDirectionChange(e.target.value)}
          placeholder='e.g. "Evening bell this time, from the calf barn — same hush"'
        />
      </div>

      <div
        className="rounded-xl border border-dashed p-6 text-center"
        style={{ borderColor: "color-mix(in oklab, var(--ink) 15%, transparent)" }}
      >
        <div className="t-caption ink-muted">
          Claude drafts fresh captions from this post's DNA.
          <br />
          History starts clean — the original keeps its own.
        </div>
      </div>
    </div>
  );
}
