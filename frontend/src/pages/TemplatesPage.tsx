import { useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  type Template,
  type CreateTemplateRequest,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { FileText, Plus, Pencil, Trash2, Loader2, Variable } from "lucide-react";

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.getTemplates(),
  });

  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);

  function handleEdit(template: Template) {
    setEditingTemplate(template);
    setIsEditorOpen(true);
  }

  function handleCreate() {
    setEditingTemplate(null);
    setIsEditorOpen(true);
  }

  const [deleteError, setDeleteError] = useState("");

  async function handleDelete(templateId: number) {
    if (!window.confirm("Delete this template? This cannot be undone.")) return;
    setDeleteError("");
    try {
      await api.deleteTemplate(templateId);
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function handleEditorClose() {
    setIsEditorOpen(false);
    setEditingTemplate(null);
  }

  function handleEditorSave() {
    queryClient.invalidateQueries({ queryKey: ["templates"] });
    handleEditorClose();
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Templates</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-sage-800">Templates</h1>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Create Template
        </Button>
      </div>

      {(!templates || templates.length === 0) ? (
        <div className="flex flex-col items-center justify-center p-12">
          <FileText className="mb-4 h-12 w-12 text-sage-400" />
          <h2 className="text-xl font-semibold text-sage-700">No templates</h2>
          <p className="mt-1 text-muted-foreground">
            Create a template to speed up content creation.
          </p>
          <Button onClick={handleCreate} variant="outline" className="mt-4">
            <Plus className="mr-2 h-4 w-4" />
            Create Template
          </Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {templates.map((t) => (
            <Card key={t.id}>
              <CardHeader className="flex flex-row items-start justify-between pb-2">
                <div className="space-y-1">
                  <CardTitle className="text-sm font-medium">
                    {t.name}
                  </CardTitle>
                  <div className="flex gap-1.5">
                    {t.pillar && (
                      <Badge variant="secondary" className="text-xs">
                        {PILLARS.find((p) => p.value === t.pillar)?.label ?? t.pillar}
                      </Badge>
                    )}
                    {t.schedule_pattern && (
                      <Badge variant="outline" className="text-xs">
                        {SCHEDULES.find((s) => s.value === t.schedule_pattern)?.label ?? t.schedule_pattern}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEdit(t)}
                    aria-label={`Edit ${t.name}`}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(t.id)}
                    aria-label={`Delete ${t.name}`}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="line-clamp-2 text-xs text-muted-foreground">
                  {t.raw_text_template}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {(t.variables ?? []).length} variables
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete error */}
      {deleteError && (
        <p className="text-sm text-destructive" role="alert">{deleteError}</p>
      )}

      {/* Template editor dialog — key forces remount on switch */}
      <TemplateEditorDialog
        key={editingTemplate?.id ?? "new"}
        isOpen={isEditorOpen}
        template={editingTemplate}
        onClose={handleEditorClose}
        onSave={handleEditorSave}
      />
    </div>
  );
}

// --- Constants ---

const PILLARS = [
  { value: "spiritual_education", label: "Spiritual Education" },
  { value: "community", label: "Farm & Community" },
  { value: "events", label: "Events" },
  { value: "behind_scenes", label: "Behind the Scenes" },
  { value: "seasonal", label: "Seasonal" },
  { value: "collaborative", label: "Collaborative" },
];

const SCHEDULES = [
  { value: "manual", label: "Manual (post when ready)" },
  { value: "weekly:sunday", label: "Weekly — Sunday" },
  { value: "weekly:monday", label: "Weekly — Monday" },
  { value: "weekly:wednesday", label: "Weekly — Wednesday" },
  { value: "weekly:friday", label: "Weekly — Friday" },
  { value: "weekly:saturday", label: "Weekly — Saturday" },
  { value: "biweekly", label: "Every 2 Weeks" },
  { value: "monthly:1", label: "Monthly — 1st" },
  { value: "monthly:15", label: "Monthly — 15th" },
];

const COMMON_VARIABLES = [
  { name: "topic", hint: "What the post is about" },
  { name: "location", hint: "Where it happened" },
  { name: "date", hint: "When it happened" },
  { name: "name", hint: "A person or cow's name" },
  { name: "event", hint: "Event or festival name" },
  { name: "quote", hint: "A quote or verse" },
];

// --- Template Editor Dialog ---

function TemplateEditorDialog({
  isOpen,
  template,
  onClose,
  onSave,
}: {
  isOpen: boolean;
  template: Template | null;
  onClose: () => void;
  onSave: () => void;
}) {
  const [name, setName] = useState(template?.name ?? "");
  const [pillar, setPillar] = useState(template?.pillar ?? "");
  const [rawTextTemplate, setRawTextTemplate] = useState(template?.raw_text_template ?? "");
  const [schedulePattern, setSchedulePattern] = useState(template?.schedule_pattern ?? "manual");
  const [isSaving, setIsSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isEdit = !!template;

  function insertVariable(varName: string) {
    const ta = textareaRef.current;
    if (!ta) {
      setRawTextTemplate((prev) => prev + `{{${varName}}}`);
      return;
    }
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const text = rawTextTemplate;
    const insert = `{{${varName}}}`;
    setRawTextTemplate(text.slice(0, start) + insert + text.slice(end));
    // Restore cursor after the inserted variable
    requestAnimationFrame(() => {
      ta.selectionStart = ta.selectionEnd = start + insert.length;
      ta.focus();
    });
  }

  async function handleSave() {
    if (!name.trim() || !rawTextTemplate.trim()) return;

    setIsSaving(true);
    try {
      const data: CreateTemplateRequest = {
        name: name.trim(),
        pillar: pillar || undefined,
        raw_text_template: rawTextTemplate,
        schedule_pattern: schedulePattern === "manual" ? undefined : schedulePattern,
      };

      if (isEdit && template) {
        await api.updateTemplate(template.id, data);
      } else {
        await api.createTemplate(data);
      }
      onSave();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Edit Template" : "Create Template"}
          </DialogTitle>
          <DialogDescription>
            Templates let you reuse post formats. Fill in the blanks each time you use one.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <Label htmlFor="template-name">Template Name</Label>
            <Input
              id="template-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Weekly Farm Update"
            />
          </div>

          {/* Pillar dropdown */}
          <div>
            <Label>Content Pillar</Label>
            <Select value={pillar} onValueChange={setPillar}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a pillar (optional)" />
              </SelectTrigger>
              <SelectContent>
                {PILLARS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Schedule dropdown */}
          <div>
            <Label>Posting Schedule</Label>
            <Select value={schedulePattern} onValueChange={setSchedulePattern}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCHEDULES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Template text with variable inserter */}
          <div>
            <Label htmlFor="template-raw-text">Post Template</Label>
            <Textarea
              ref={textareaRef}
              id="template-raw-text"
              value={rawTextTemplate}
              onChange={(e) => setRawTextTemplate(e.target.value)}
              placeholder="Write your post template here. Use the buttons below to add fill-in-the-blank fields."
              rows={5}
            />

            {/* Variable inserter */}
            <div className="mt-2">
              <p className="text-xs text-muted-foreground mb-1.5 flex items-center gap-1">
                <Variable className="h-3 w-3" />
                Insert a fill-in-the-blank field:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {COMMON_VARIABLES.map((v) => (
                  <Button
                    key={v.name}
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => insertVariable(v.name)}
                    title={v.hint}
                  >
                    + {v.name}
                  </Button>
                ))}
              </div>
            </div>

            {/* Preview */}
            {rawTextTemplate && (
              <div className="mt-3 rounded-md border bg-muted/20 px-3 py-2">
                <p className="text-[10px] font-medium uppercase text-muted-foreground mb-1">
                  Preview
                </p>
                <p className="text-sm leading-relaxed">
                  {rawTextTemplate.split(/(\{\{.+?\}\})/).map((part, i) =>
                    part.match(/^\{\{(.+?)\}\}$/) ? (
                      <span
                        key={i}
                        className="mx-0.5 inline-block rounded bg-sage-100 px-1.5 py-0.5 text-xs font-medium text-sage-700"
                      >
                        {part.match(/^\{\{(.+?)\}\}$/)![1]}
                      </span>
                    ) : (
                      <span key={i}>{part}</span>
                    ),
                  )}
                </p>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving || !name.trim() || !rawTextTemplate.trim()}
          >
            {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
