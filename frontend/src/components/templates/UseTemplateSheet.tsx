import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { GVSheet, SegmentedControl } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Template } from "@/lib/api";

import { PlatformPicker } from "./PlatformPicker";
import { isWeeklyPattern, templateVariableNames } from "./template-utils";

interface UseTemplateSheetProps {
  template: Template;
  onClose: () => void;
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/** "Use" flow — fill variables, pick platforms + date, draft (or batch). */
export function UseTemplateSheet({ template, onClose }: UseTemplateSheetProps) {
  const queryClient = useQueryClient();
  const variableNames = templateVariableNames(template);
  const weekly = isWeeklyPattern(template.schedule_pattern);

  const [values, setValues] = useState<Record<string, string>>({});
  const [platforms, setPlatforms] = useState<string[]>(
    Object.keys(template.platform_instructions ?? {}),
  );
  const [mode, setMode] = useState<"single" | "batch">("single");
  const [date, setDate] = useState(todayISO());
  const [time, setTime] = useState("");
  const [weeks, setWeeks] = useState(4);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const canSubmit =
    platforms.length > 0 && (mode === "batch" ? weeks > 0 : date.length > 0);

  async function handleSubmit() {
    setError("");
    setBusy(true);
    try {
      if (mode === "batch") {
        const result = await api.batchGenerateFromTemplate(template.id, {
          variable_values: values,
          platforms,
          weeks,
          scheduled_time: time || undefined,
        });
        setSuccess(
          `${result.created} draft shells created — staff fill each before generating.`,
        );
      } else {
        await api.generateFromTemplate(template.id, {
          variable_values: values,
          platforms,
          scheduled_date: date,
          scheduled_time: time || undefined,
        });
        setSuccess("Draft created — find it in Drafts.");
      }
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  const footer = success ? (
    <div className="flex justify-end">
      <Button variant="dark" className="fr" onClick={onClose}>
        Done
      </Button>
    </div>
  ) : (
    <div className="flex items-center justify-end gap-2">
      <Button variant="ghost" className="fr" onClick={onClose}>
        Cancel
      </Button>
      <Button
        variant="dark"
        className="fr"
        onClick={handleSubmit}
        disabled={!canSubmit || busy}
      >
        {mode === "batch" ? `Create ${weeks} draft shells` : "Create draft"}
      </Button>
    </div>
  );

  return (
    <GVSheet title={template.name} onClose={onClose} footer={footer} width={480}>
      {success ? (
        <p role="status" className="t-body ink">
          {success}
        </p>
      ) : (
        <div className="space-y-5">
          {weekly && (
            <SegmentedControl
              aria-label="Draft mode"
              options={[
                { id: "single", label: "One draft" },
                { id: "batch", label: "Weekly batch" },
              ]}
              value={mode}
              onChange={(id) => setMode(id as "single" | "batch")}
            />
          )}

          {variableNames.length > 0 && (
            <div className="space-y-3">
              <div className="t-label ink-muted">Fill it in</div>
              {variableNames.map((v) => (
                <div key={v} className="space-y-1.5">
                  <Label htmlFor={`use-var-${v}`} className="font-mono">
                    {`{{${v}}}`}
                  </Label>
                  <Input
                    id={`use-var-${v}`}
                    className="fr bg-card"
                    value={values[v] ?? ""}
                    onChange={(e) =>
                      setValues({ ...values, [v]: e.target.value })
                    }
                  />
                </div>
              ))}
            </div>
          )}

          <div className="space-y-1.5">
            <Label id="use-platforms-label">Platforms</Label>
            <div role="group" aria-labelledby="use-platforms-label">
              <PlatformPicker value={platforms} onChange={setPlatforms} />
            </div>
          </div>

          {mode === "single" ? (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="use-date">Scheduled date</Label>
                <Input
                  id="use-date"
                  type="date"
                  className="fr bg-card"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="use-time">Time (optional)</Label>
                <Input
                  id="use-time"
                  type="time"
                  className="fr bg-card"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="use-weeks">Weeks</Label>
                <Input
                  id="use-weeks"
                  type="number"
                  min={1}
                  max={12}
                  className="fr bg-card"
                  value={weeks}
                  onChange={(e) => setWeeks(Number(e.target.value))}
                />
              </div>
              <p className="t-caption ink-muted self-end pb-2">
                One draft shell per week, on the template's day.
              </p>
            </div>
          )}

          {error && (
            <p role="alert" className="t-caption text-terra-600 dark:text-terra-300">
              {error}
            </p>
          )}
        </div>
      )}
    </GVSheet>
  );
}
