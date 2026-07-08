import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Pencil, Plus } from "lucide-react";

import { api, type Pillar } from "@/lib/api";
import { pillarColor } from "@/lib/pillars";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SkeletonText, Toggle } from "@/components/pasture";

interface PillarFormState {
  name: string;
  description: string;
  color: string;
}

const EMPTY_FORM: PillarFormState = { name: "", description: "", color: "#6b7280" };

/**
 * Content pillars — CRUD list restyled per supporting.jsx PastureSettings:
 * color swatch + name + active Toggle + edit pencil per row.
 */
export function PillarsSection() {
  const queryClient = useQueryClient();
  const { data: pillars = [], isLoading } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<PillarFormState>(EMPTY_FORM);
  const [isAdding, setIsAdding] = useState(false);
  const [newForm, setNewForm] = useState<PillarFormState>(EMPTY_FORM);
  const [error, setError] = useState("");

  function startEdit(pillar: Pillar) {
    setEditingId(pillar.id);
    setEditForm({
      name: pillar.name,
      description: pillar.description ?? "",
      color: pillar.color ?? "#6b7280",
    });
    setError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm(EMPTY_FORM);
    setError("");
  }

  async function saveEdit(id: number) {
    if (!editForm.name.trim()) {
      setError("Name is required");
      return;
    }
    try {
      await api.updatePillar(id, {
        name: editForm.name.trim(),
        description: editForm.description.trim() || undefined,
        color: editForm.color || undefined,
      });
      queryClient.invalidateQueries({ queryKey: ["pillars"] });
      setEditingId(null);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function toggleActive(pillar: Pillar) {
    try {
      await api.updatePillar(pillar.id, { is_active: !pillar.is_active });
      queryClient.invalidateQueries({ queryKey: ["pillars"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleAdd() {
    if (!newForm.name.trim()) {
      setError("Name is required");
      return;
    }
    try {
      await api.createPillar({
        name: newForm.name.trim(),
        description: newForm.description.trim() || undefined,
        color: newForm.color || undefined,
        sort_order: pillars.length + 1,
      });
      queryClient.invalidateQueries({ queryKey: ["pillars"] });
      setIsAdding(false);
      setNewForm(EMPTY_FORM);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  if (isLoading) {
    return (
      <div className="bg-card border-hair shadow-card max-w-3xl rounded-2xl p-4">
        <div className="t-title mb-2 text-sage-800 dark:text-sage-100">
          Content pillars
        </div>
        <span className="sr-only">Loading pillars</span>
        <SkeletonText lines={4} />
      </div>
    );
  }

  return (
    <div className="bg-card border-hair shadow-card max-w-3xl rounded-2xl p-4">
      <div className="flex items-center justify-between">
        <div className="t-title text-sage-800 dark:text-sage-100">
          Content pillars
        </div>
        {!isAdding && (
          <Button
            variant="soft"
            size="sm"
            onClick={() => {
              setIsAdding(true);
              setError("");
            }}
          >
            <Plus className="mr-1 h-3.5 w-3.5" strokeWidth={1.75} />
            Add pillar
          </Button>
        )}
      </div>
      <p className="t-caption ink-muted mt-0.5 mb-3">
        Manage content categories. Deactivated pillars are hidden from new content
        but preserved on existing posts.
      </p>

      {error && (
        <p className="t-caption mb-2 text-red-700 dark:text-red-400" role="alert">
          {error}
        </p>
      )}

      {isAdding && (
        <div className="border-hair mb-3 space-y-2 rounded-xl border-dashed p-3">
          <div className="flex gap-2">
            <input
              type="color"
              value={newForm.color}
              onChange={(e) =>
                setNewForm((prev) => ({ ...prev, color: e.target.value }))
              }
              className="fr h-8 w-8 cursor-pointer rounded border-0 p-0"
              aria-label="Pillar color"
            />
            <Input
              value={newForm.name}
              onChange={(e) =>
                setNewForm((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder="Pillar name (e.g. Farm Updates)"
              className="bg-card flex-1"
              aria-label="New pillar name"
            />
          </div>
          <Input
            value={newForm.description}
            onChange={(e) =>
              setNewForm((prev) => ({ ...prev, description: e.target.value }))
            }
            placeholder="Brief description (optional)"
            className="bg-card"
            aria-label="New pillar description"
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleAdd}>
              <Check className="mr-1 h-3.5 w-3.5" strokeWidth={1.75} />
              Add
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setIsAdding(false);
                setError("");
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        {pillars.map((pillar) =>
          editingId === pillar.id ? (
            <div key={pillar.id} className="border-hair space-y-2 rounded-xl p-3">
              <div className="flex gap-2">
                <input
                  type="color"
                  value={editForm.color}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, color: e.target.value }))
                  }
                  className="fr h-8 w-8 cursor-pointer rounded border-0 p-0"
                  aria-label="Edit pillar color"
                />
                <Input
                  value={editForm.name}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, name: e.target.value }))
                  }
                  className="bg-card flex-1"
                  aria-label="Edit pillar name"
                />
              </div>
              <Input
                value={editForm.description}
                onChange={(e) =>
                  setEditForm((prev) => ({ ...prev, description: e.target.value }))
                }
                placeholder="Description (optional)"
                className="bg-card"
                aria-label="Edit pillar description"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={() => saveEdit(pillar.id)}>
                  <Check className="mr-1 h-3.5 w-3.5" strokeWidth={1.75} />
                  Save
                </Button>
                <Button size="sm" variant="ghost" onClick={cancelEdit}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div
              key={pillar.id}
              className={cn(
                "hover:bg-warm flex items-center gap-3 rounded-lg px-2 py-2 transition-colors",
                !pillar.is_active && "opacity-50",
              )}
            >
              <span
                className="h-4 w-4 shrink-0 rounded"
                style={{ background: pillarColor(pillar) }}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <span className="t-body ink font-medium">
                  {pillar.name}
                  {!pillar.is_active && (
                    <span className="t-caption ink-muted ml-2">(inactive)</span>
                  )}
                </span>
                {pillar.description && (
                  <p className="t-caption ink-muted truncate">{pillar.description}</p>
                )}
              </div>
              <Toggle
                checked={pillar.is_active}
                onChange={() => toggleActive(pillar)}
                aria-label={`${pillar.name} active`}
              />
              <Button
                variant="ghost"
                size="iconSm"
                onClick={() => startEdit(pillar)}
                aria-label={`Edit ${pillar.name}`}
              >
                <Pencil className="h-3 w-3" strokeWidth={1.75} />
              </Button>
            </div>
          ),
        )}
      </div>

      {pillars.length === 0 && !isAdding && (
        <p className="t-caption ink-muted py-4 text-center">
          No pillars defined yet. Add one to categorize your content.
        </p>
      )}
    </div>
  );
}
