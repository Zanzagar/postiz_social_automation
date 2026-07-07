import { useState } from "react";
import { Save, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ContentRow } from "@/lib/api";

interface EditorTemplateShellProps {
  row: ContentRow;
  templateVars: string[];
  busy: boolean;
  onUseAsIs: (finalText: string) => void;
  onGenerate: (finalText: string) => void;
}

/**
 * Template shell fill-in — a batch-scheduled draft with {{variables}} and no
 * captions yet. Staff fills the variables, then either uses the text as-is or
 * asks Claude to write platform captions.
 */
export function EditorTemplateShell({
  row,
  templateVars,
  busy,
  onUseAsIs,
  onGenerate,
}: EditorTemplateShellProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const filled = templateVars.every((v) => values[v]?.trim());

  function substituted(): string {
    let text = row.raw_text;
    for (const v of templateVars) {
      text = text.split(`{{${v}}}`).join(values[v]?.trim() ?? "");
    }
    return text;
  }

  return (
    <div className="space-y-4">
      <div className="bg-warm border-hair t-body-sm ink rounded-xl px-3.5 py-3 leading-relaxed">
        {row.raw_text.split(/(\{\{.+?\}\})/).map((part, i) => {
          const m = part.match(/^\{\{(.+?)\}\}$/);
          return m ? (
            <span
              key={i}
              className="bg-cream-100 text-cream-ink-deep t-micro mx-0.5 inline-block rounded px-1.5 py-0.5 font-medium"
            >
              {values[m[1]]?.trim() || m[1]}
            </span>
          ) : (
            <span key={i}>{part}</span>
          );
        })}
      </div>

      {templateVars.map((v) => (
        <div key={v}>
          <label htmlFor={`shell-var-${v}`} className="t-label ink-muted mb-1.5 block capitalize">
            {v}
          </label>
          <Input
            id={`shell-var-${v}`}
            value={values[v] ?? ""}
            onChange={(e) => setValues((prev) => ({ ...prev, [v]: e.target.value }))}
            placeholder={`Enter ${v}…`}
            className="bg-card h-10"
          />
        </div>
      ))}

      {busy ? (
        <p className="t-caption ink-muted animate-pulse text-center">
          Claude is writing platform-specific captions — this usually takes 30–90 seconds.
        </p>
      ) : (
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            disabled={!filled}
            onClick={() => onUseAsIs(substituted())}
          >
            <Save size={14} strokeWidth={1.75} aria-hidden="true" />
            Use text as-is
          </Button>
          <Button className="flex-1" disabled={!filled} onClick={() => onGenerate(substituted())}>
            <Sparkles size={14} strokeWidth={1.75} aria-hidden="true" />
            Generate captions
          </Button>
        </div>
      )}
    </div>
  );
}
