import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Pillar, type PlatformPublishConfig } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Settings,
  Loader2,
  Save,
  Plus,
  Pencil,
  GripVertical,
  Check,
  X,
} from "lucide-react";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["publishConfig"],
    queryFn: () => api.getPublishConfig(),
  });

  const [configs, setConfigs] = useState<PlatformPublishConfig[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data?.platforms) {
      setConfigs(data.platforms);
    }
  }, [data]);

  function updatePlatform(
    platform: string,
    update: Partial<PlatformPublishConfig>,
  ) {
    setConfigs((prev) =>
      prev.map((c) => (c.platform === platform ? { ...c, ...update } : c)),
    );
    setSaved(false);
  }

  async function handleSave() {
    setIsSaving(true);
    setSaved(false);
    try {
      await api.updatePublishConfig(configs);
      queryClient.invalidateQueries({ queryKey: ["publishConfig"] });
      setSaved(true);
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Settings</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <Settings className="h-6 w-6 text-sage-600" />
        <h1 className="text-2xl font-bold text-sage-800">Settings</h1>
      </div>

      {/* Auto-publish section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Auto-Publish Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Configure automatic publishing per platform. When enabled, approved
            content will be scheduled for publishing after the specified delay.
          </p>

          {configs.map((config) => (
            <div
              key={config.platform}
              className="flex items-center gap-4 rounded-lg border p-3"
            >
              <Checkbox
                id={`${config.platform}-enabled`}
                checked={config.enabled}
                onCheckedChange={(checked) =>
                  updatePlatform(config.platform, {
                    enabled: checked === true,
                  })
                }
                aria-label={`${config.platform} enabled`}
              />
              <div className="flex-1">
                <Label
                  htmlFor={`${config.platform}-enabled`}
                  className="text-sm font-medium capitalize"
                >
                  {config.platform}
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Label
                  htmlFor={`${config.platform}-delay`}
                  className="text-xs text-muted-foreground"
                >
                  Delay (hrs)
                </Label>
                <Input
                  id={`${config.platform}-delay`}
                  type="number"
                  min={0}
                  max={72}
                  value={config.delay_hours}
                  onChange={(e) =>
                    updatePlatform(config.platform, {
                      delay_hours: parseInt(e.target.value) || 0,
                    })
                  }
                  className="w-20"
                  disabled={!config.enabled}
                />
              </div>
            </div>
          ))}

          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save
            </Button>
            {saved && (
              <span className="text-sm text-sage-600">Settings saved</span>
            )}
          </div>
        </CardContent>
      </Card>
      {/* Content Pillars section */}
      <PillarManager />
    </div>
  );
}

// --- Pillar Management ---

function PillarManager() {
  const queryClient = useQueryClient();
  const { data: pillars = [], isLoading } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(),
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({ name: "", description: "", color: "" });
  const [isAdding, setIsAdding] = useState(false);
  const [newForm, setNewForm] = useState({ name: "", description: "", color: "#6b7280" });
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
    setEditForm({ name: "", description: "", color: "" });
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
      setNewForm({ name: "", description: "", color: "#6b7280" });
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function _handleDelete(pillar: Pillar) {
    try {
      await api.deletePillar(pillar.id);
      queryClient.invalidateQueries({ queryKey: ["pillars"] });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }
  void _handleDelete;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Content Pillars</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-24 rounded-xl" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Content Pillars</CardTitle>
          {!isAdding && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsAdding(true);
                setError("");
              }}
            >
              <Plus className="mr-1 h-3.5 w-3.5" />
              Add Pillar
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Manage content categories. Deactivated pillars are hidden from new
          content but preserved on existing posts.
        </p>

        {error && (
          <p className="text-sm text-destructive" role="alert">{error}</p>
        )}

        {/* Add new pillar form */}
        {isAdding && (
          <div className="rounded-lg border border-dashed p-3 space-y-2">
            <div className="flex gap-2">
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={newForm.color}
                  onChange={(e) =>
                    setNewForm((prev) => ({ ...prev, color: e.target.value }))
                  }
                  className="h-8 w-8 cursor-pointer rounded border-0 p-0"
                  aria-label="Pillar color"
                />
              </div>
              <Input
                value={newForm.name}
                onChange={(e) =>
                  setNewForm((prev) => ({ ...prev, name: e.target.value }))
                }
                placeholder="Pillar name (e.g. Farm Updates)"
                className="flex-1"
                aria-label="New pillar name"
              />
            </div>
            <Input
              value={newForm.description}
              onChange={(e) =>
                setNewForm((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder="Brief description (optional)"
              aria-label="New pillar description"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleAdd}>
                <Check className="mr-1 h-3.5 w-3.5" />
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

        {/* Pillar list */}
        {pillars.map((pillar) => (
          <div
            key={pillar.id}
            className={`flex items-center gap-3 rounded-lg border p-3 transition-opacity ${
              !pillar.is_active ? "opacity-50" : ""
            }`}
          >
            <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground/40" />

            {editingId === pillar.id ? (
              /* Editing mode */
              <div className="flex-1 space-y-2">
                <div className="flex gap-2">
                  <input
                    type="color"
                    value={editForm.color}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, color: e.target.value }))
                    }
                    className="h-8 w-8 cursor-pointer rounded border-0 p-0"
                    aria-label="Edit pillar color"
                  />
                  <Input
                    value={editForm.name}
                    onChange={(e) =>
                      setEditForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                    className="flex-1"
                    aria-label="Edit pillar name"
                  />
                </div>
                <Input
                  value={editForm.description}
                  onChange={(e) =>
                    setEditForm((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Description (optional)"
                  aria-label="Edit pillar description"
                />
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => saveEdit(pillar.id)}>
                    <Check className="mr-1 h-3.5 w-3.5" />
                    Save
                  </Button>
                  <Button size="sm" variant="ghost" onClick={cancelEdit}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              /* Display mode */
              <>
                <span
                  className="inline-block h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: pillar.color ?? "#6b7280" }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">
                    {pillar.name}
                    {!pillar.is_active && (
                      <span className="ml-2 text-xs text-muted-foreground">(inactive)</span>
                    )}
                  </p>
                  {pillar.description && (
                    <p className="text-xs text-muted-foreground truncate">
                      {pillar.description}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => startEdit(pillar)}
                    aria-label={`Edit ${pillar.name}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-7 p-0"
                    onClick={() => toggleActive(pillar)}
                    aria-label={`${pillar.is_active ? "Deactivate" : "Activate"} ${pillar.name}`}
                  >
                    {pillar.is_active ? (
                      <X className="h-3.5 w-3.5 text-muted-foreground" />
                    ) : (
                      <Check className="h-3.5 w-3.5 text-sage-600" />
                    )}
                  </Button>
                </div>
              </>
            )}
          </div>
        ))}

        {pillars.length === 0 && !isAdding && (
          <p className="text-center text-sm text-muted-foreground py-4">
            No pillars defined yet. Add one to categorize your content.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
