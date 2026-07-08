import { useState } from "react";
import { Play, Save } from "lucide-react";

import { api, type CreateTemplateRequest, type Pillar, type Template } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

import { PlatformPicker } from "./PlatformPicker";
import {
  TRIGGER_OPTIONS,
  fillTemplate,
  parseVariables,
  sampleValue,
} from "./template-utils";

interface TemplateEditorProps {
  template: Template | null;
  pillars: Pillar[];
  onCancel: () => void;
  onSaved: (template: Template) => void;
  /** "Run once — draft now": saves, then opens the Use dialog. */
  onRunOnce: (template: Template) => void;
}

/** Full-page template editor (v2 TemplatesEditor layout). */
export function TemplateEditor({
  template,
  pillars,
  onCancel,
  onSaved,
  onRunOnce,
}: TemplateEditorProps) {
  const [name, setName] = useState(template?.name ?? "");
  const [trigger, setTrigger] = useState(template?.schedule_pattern ?? "manual");
  const [pillar, setPillar] = useState(template?.pillar ?? "");
  const [platforms, setPlatforms] = useState<string[]>(
    Object.keys(template?.platform_instructions ?? {}),
  );
  const [body, setBody] = useState(template?.raw_text_template ?? "");
  const [preview, setPreview] = useState(false);
  const [descriptions, setDescriptions] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const variableNames = parseVariables(body);
  const canSave = name.trim().length > 0 && body.trim().length > 0;

  async function save(): Promise<Template | null> {
    setError("");
    setSaving(true);
    try {
      const payload: CreateTemplateRequest = {
        name: name.trim(),
        pillar: pillar || undefined,
        raw_text_template: body,
        schedule_pattern: trigger === "manual" ? undefined : trigger,
        platform_instructions: Object.fromEntries(platforms.map((p) => [p, ""])),
        variables: variableNames.map((n) => ({ name: n, type: "text" })),
      };
      return template
        ? await api.updateTemplate(template.id, payload)
        : await api.createTemplate(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function handleSave() {
    const saved = await save();
    if (saved) onSaved(saved);
  }

  async function handleRunOnce() {
    const saved = await save();
    if (saved) onRunOnce(saved);
  }

  return (
    <div className="max-w-3xl flex-1 space-y-5 overflow-y-auto px-8 py-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="tpl-name">Template name</Label>
          <Input
            id="tpl-name"
            className="fr bg-card"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Weekly cow spotlight"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="tpl-trigger">Trigger</Label>
          <select
            id="tpl-trigger"
            className="fr bg-card border-hair t-ui ink h-9 w-full rounded-lg px-3"
            value={trigger}
            onChange={(e) => setTrigger(e.target.value)}
          >
            {TRIGGER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label id="tpl-pillar-label">Pillar</Label>
        <div
          role="group"
          aria-labelledby="tpl-pillar-label"
          className="flex flex-wrap gap-1.5"
        >
          {pillars.map((p) => {
            const selected = pillar === p.name;
            return (
              <button
                key={p.id}
                type="button"
                aria-pressed={selected}
                onClick={() => setPillar(selected ? "" : p.name)}
                className={cn(
                  "fr t-body-sm h-7 rounded-md border px-2.5 transition-colors",
                  selected
                    ? "border-sage-500 bg-sage-500 text-white"
                    : "bg-card border-hair ink hover:border-sage-300",
                )}
              >
                {p.name}
              </button>
            );
          })}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label id="tpl-platforms-label">Platforms</Label>
        <div role="group" aria-labelledby="tpl-platforms-label">
          <PlatformPicker value={platforms} onChange={setPlatforms} />
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="tpl-body">
            <span>
              Body — use{" "}
              <span className="font-mono text-sage-600 dark:text-sage-300">
                {"{{variable}}"}
              </span>{" "}
              where Claude should fill in
            </span>
          </Label>
          <button
            type="button"
            onClick={() => setPreview(!preview)}
            className="fr t-caption rounded text-sage-600 hover:underline dark:text-sage-300"
          >
            {preview ? "Edit" : "Preview filled"}
          </button>
        </div>
        <div className="bg-card border-hair t-body min-h-[200px] rounded-xl p-4 font-serif leading-relaxed">
          {!preview ? (
            <Textarea
              id="tpl-body"
              rows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="This week we introduce {{cow_name}} — {{trait}}."
              className="t-body min-h-[170px] border-0 bg-transparent p-0 font-serif leading-relaxed shadow-none focus-visible:ring-0"
            />
          ) : (
            <div className="ink">
              {fillTemplate(body, sampleValue)
                .split("\n")
                .map((line, i) => (
                  <p key={i} className={i > 0 ? "mt-3" : undefined}>
                    {line}
                  </p>
                ))}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label id="tpl-variables-label">Variables</Label>
        <div
          role="group"
          aria-labelledby="tpl-variables-label"
          className="bg-card border-hair overflow-hidden rounded-xl"
        >
          {variableNames.length === 0 ? (
            <p className="t-caption ink-muted px-4 py-3">
              No variables yet — add {"{{variable}}"} tokens to the body and
              they appear here.
            </p>
          ) : (
            variableNames.map((v) => (
              <div
                key={v}
                className="border-hair-b grid grid-cols-[170px_1fr] items-center gap-3 px-4 py-2 last:border-b-0"
              >
                <span className="t-body-sm font-mono text-sage-700 dark:text-sage-300">
                  {`{{${v}}}`}
                </span>
                <Input
                  aria-label={`Description for ${v}`}
                  placeholder="What should fill this in?"
                  className="fr bg-transparent"
                  value={descriptions[v] ?? ""}
                  onChange={(e) =>
                    setDescriptions({ ...descriptions, [v]: e.target.value })
                  }
                />
              </div>
            ))
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="t-caption text-terra-600 dark:text-terra-300">
          {error}
        </p>
      )}

      <div className="flex items-center gap-2 pt-2">
        <Button
          variant="dark"
          className="fr"
          onClick={handleSave}
          disabled={!canSave || saving}
        >
          <Save size={13} strokeWidth={1.75} aria-hidden="true" />
          Save template
        </Button>
        <Button
          variant="outline"
          className="fr"
          onClick={handleRunOnce}
          disabled={!canSave || saving}
        >
          <Play size={13} strokeWidth={1.75} aria-hidden="true" />
          Run once — draft now
        </Button>
        <Button variant="ghost" className="fr" onClick={onCancel}>
          Cancel
        </Button>
        <span className="t-caption ink-muted ml-auto">
          Changes apply to future posts only.
        </span>
      </div>
    </div>
  );
}
