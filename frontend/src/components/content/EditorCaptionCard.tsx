import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Chip, PlatformDot } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { platformBy } from "@/lib/platforms";

/** Count hashtags in a caption ("#farmlife" style tokens). */
function countHashtags(text: string): number {
  return (text.match(/#[\p{L}\d_]+/gu) ?? []).length;
}

interface EditorCaptionCardProps {
  platformId: string;
  caption: string;
  onCaptionChange: (value: string) => void;
  onIterate: (instruction: string) => void;
  iterating: boolean;
}

/**
 * Per-platform caption card — editable caption body, live char count vs the
 * platform limit, hashtag health chip, and an inline iterate input that
 * rewrites only this platform's caption.
 */
export function EditorCaptionCard({
  platformId,
  caption,
  onCaptionChange,
  onIterate,
  iterating,
}: EditorCaptionCardProps) {
  const p = platformBy(platformId);
  const [instruction, setInstruction] = useState("");

  const tags = countHashtags(caption);
  // Threads (hashMax 0) wants zero hashtags; everyone else has a min–max band.
  const tagsOk = p.hashMax === 0 ? tags === 0 : tags >= p.hashMin && tags <= p.hashMax;
  const rows = Math.min(
    12,
    Math.max(3, Math.ceil(caption.length / 60) + caption.split("\n").length - 1),
  );

  function submit() {
    const trimmed = instruction.trim();
    if (!trimmed || iterating) return;
    onIterate(trimmed);
    setInstruction("");
  }

  return (
    <div className="bg-card border-hair overflow-hidden rounded-xl">
      <div className="bg-warm/70 flex h-10 items-center gap-2 px-3.5">
        <PlatformDot id={platformId} size={14} />
        <span className="t-body-sm ink font-semibold">{p.label}</span>
        <span className="flex-1" />
        <span className="t-micro ink-muted font-mono">
          {caption.length} / {p.max}
        </span>
        <Chip tone={tagsOk ? "sage" : "cream"} className="ml-1">
          {tags} {tags === 1 ? "tag" : "tags"} {tagsOk ? "✓" : "!"}
        </Chip>
      </div>
      <textarea
        value={caption}
        onChange={(e) => onCaptionChange(e.target.value)}
        rows={rows}
        aria-label={`${p.label} caption`}
        className="fr t-body-sm ink block w-full resize-y border-0 bg-transparent px-3.5 py-3 leading-relaxed"
      />
      <div className="flex gap-2 px-3.5 pb-3">
        <Input
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          placeholder='Refine just this caption — e.g. "warmer, mention the calves"'
          aria-label={`Refine ${p.label} caption`}
          disabled={iterating}
          className="bg-warm/60 h-9 flex-1"
        />
        <Button
          size="sm"
          variant="soft"
          onClick={submit}
          disabled={iterating || !instruction.trim()}
        >
          {iterating && (
            <Loader2 size={14} strokeWidth={1.75} className="animate-spin" aria-hidden="true" />
          )}
          Iterate
        </Button>
      </div>
    </div>
  );
}
