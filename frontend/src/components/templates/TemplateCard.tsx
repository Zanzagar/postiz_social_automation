import { Clock, Trash2 } from "lucide-react";

import { PlatformDots } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import type { Template } from "@/lib/api";

import { TemplatePreviewText } from "./TemplatePreviewText";
import { formatSchedule, templateVariableNames } from "./template-utils";

interface TemplateCardProps {
  template: Template;
  onEdit: () => void;
  onUse: () => void;
  onDelete: () => void;
}

/** Browse card — serif name, schedule, cream preview, variable chips, Use →. */
export function TemplateCard({
  template,
  onEdit,
  onUse,
  onDelete,
}: TemplateCardProps) {
  const platformIds = Object.keys(template.platform_instructions ?? {});
  const variableNames = templateVariableNames(template);

  return (
    <article className="bg-card border-hair rounded-xl p-4 transition hover:border-sage-300 hover:shadow-sm">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <button
            type="button"
            onClick={onEdit}
            className="fr t-title-sm rounded text-left font-serif text-sage-800 hover:underline dark:text-sage-100"
          >
            {template.name}
          </button>
          <div className="t-caption ink-muted mt-0.5 flex items-center gap-1">
            <Clock size={11} strokeWidth={1.75} aria-hidden="true" />
            {formatSchedule(template.schedule_pattern)}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {platformIds.length > 0 && <PlatformDots ids={platformIds} size={11} />}
          <Button
            size="iconSm"
            variant="ghost"
            className="fr"
            aria-label={`Delete ${template.name}`}
            onClick={onDelete}
          >
            <Trash2 size={13} strokeWidth={1.75} aria-hidden="true" />
          </Button>
        </div>
      </div>

      {template.raw_text_template && (
        <div className="t-body-sm ink mb-2 rounded-lg border border-cream-200 bg-cream-100/50 p-3 leading-relaxed dark:border-cream-400/20 dark:bg-cream-400/10">
          <TemplatePreviewText text={template.raw_text_template} />
        </div>
      )}

      <div className="flex items-center gap-2">
        <div className="flex flex-1 flex-wrap gap-1">
          {variableNames.map((v) => (
            <span
              key={v}
              className="t-micro bg-warm ink-muted rounded px-1.5 py-0.5 font-mono"
            >
              {`{{${v}}}`}
            </span>
          ))}
        </div>
        <Button variant="ghost" size="sm" className="fr shrink-0" onClick={onUse}>
          Use →
        </Button>
      </div>
    </article>
  );
}
