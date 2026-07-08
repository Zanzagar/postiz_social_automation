import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SkeletonText } from "@/components/pasture";
import { SettingRow } from "./SettingRow";

/**
 * Brand voice — the read-only identity card (supporting.jsx PastureSettings)
 * plus the editable voice-rules list that feeds every generation prompt.
 */
export function BrandVoiceSection() {
  return (
    <div className="max-w-3xl space-y-5">
      <div className="bg-card border-hair shadow-card rounded-2xl p-4">
        <div className="t-title mb-2 text-sage-800 dark:text-sage-100">
          Brand voice
        </div>
        <div className="space-y-3">
          <SettingRow label="Name" value="Gita Valley" hint="Never 'Gita Nagari'" />
          <SettingRow label="Tagline" value="Cultivating Soil and Soul" />
          <SettingRow
            label="Key claim"
            value="Only USDA Certified Slaughter-Free Dairy Farm in North America"
          />
          <SettingRow
            label="Voice"
            value="Warm, welcoming, grounded"
            hint="Lead with cows and farm, not religion."
          />
        </div>
      </div>

      <VoiceRulesCard />
    </div>
  );
}

function VoiceRulesCard() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["voiceRules"],
    queryFn: () => api.getVoiceRules(),
  });

  const [rules, setRules] = useState<string[]>([]);
  const [newRule, setNewRule] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data?.rules) {
      setRules(data.rules);
    }
  }, [data]);

  async function handleSave() {
    setIsSaving(true);
    setSaved(false);
    try {
      await api.updateVoiceRules(rules);
      queryClient.invalidateQueries({ queryKey: ["voiceRules"] });
      setSaved(true);
    } finally {
      setIsSaving(false);
    }
  }

  function handleAdd() {
    if (!newRule.trim()) return;
    setRules((prev) => [...prev, newRule.trim()]);
    setNewRule("");
    setSaved(false);
  }

  function handleRemove(index: number) {
    setRules((prev) => prev.filter((_, i) => i !== index));
    setSaved(false);
  }

  if (isLoading) {
    return (
      <div className="bg-card border-hair shadow-card rounded-2xl p-4">
        <div className="t-title mb-2 text-sage-800 dark:text-sage-100">
          Voice rules
        </div>
        <span className="sr-only">Loading voice rules</span>
        <SkeletonText lines={3} />
      </div>
    );
  }

  return (
    <div className="bg-card border-hair shadow-card rounded-2xl p-4">
      <div className="t-title text-sage-800 dark:text-sage-100">Voice rules</div>
      <p className="t-caption ink-muted mt-0.5 mb-3">
        Rules that guide AI content generation. These are injected into every
        prompt as &ldquo;LEARNED PREFERENCES&rdquo;. Add your own or let the
        system extract them from your editing history.
      </p>

      {rules.length > 0 ? (
        <div className="space-y-2">
          {rules.map((rule, i) => (
            <div
              key={i}
              className="border-hair flex items-start gap-2 rounded-lg px-3 py-2"
            >
              <span className="t-body-sm ink flex-1">{rule}</span>
              <Button
                variant="ghost"
                size="iconSm"
                className="ink-muted shrink-0 hover:text-destructive"
                onClick={() => handleRemove(i)}
                aria-label="Remove rule"
              >
                <Trash2 className="h-3.5 w-3.5" strokeWidth={1.75} />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="t-caption ink-muted border-hair rounded-lg border-dashed py-3 text-center">
          No voice rules yet. Add one below.
        </p>
      )}

      <div className="mt-3 flex gap-2">
        <Textarea
          value={newRule}
          onChange={(e) => setNewRule(e.target.value)}
          placeholder='e.g. "Keep posts under 60 words" or "Always mention cow names when available"'
          className="bg-card min-h-[60px]"
          aria-label="New voice rule"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAdd();
            }
          }}
        />
        <Button
          variant="soft"
          size="sm"
          className="shrink-0 self-end"
          onClick={handleAdd}
          disabled={!newRule.trim()}
        >
          <Plus className="mr-1 h-3.5 w-3.5" strokeWidth={1.75} />
          Add
        </Button>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" strokeWidth={1.75} />
          ) : (
            <Save className="mr-2 h-4 w-4" strokeWidth={1.75} />
          )}
          Save Rules
        </Button>
        {saved && (
          <span role="status" className="t-caption text-sage-600 dark:text-sage-300">
            Rules saved
          </span>
        )}
      </div>
    </div>
  );
}
