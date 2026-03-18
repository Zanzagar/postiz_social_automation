import { useState } from "react";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { FileText, Plus, Pencil, Trash2, Loader2 } from "lucide-react";

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

  async function handleDelete(templateId: number) {
    await api.deleteTemplate(templateId);
    queryClient.invalidateQueries({ queryKey: ["templates"] });
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
                        {t.pillar}
                      </Badge>
                    )}
                    {t.schedule_pattern && (
                      <Badge variant="outline" className="text-xs">
                        {t.schedule_pattern}
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

      {/* Template editor dialog */}
      <TemplateEditorDialog
        isOpen={isEditorOpen}
        template={editingTemplate}
        onClose={handleEditorClose}
        onSave={handleEditorSave}
      />
    </div>
  );
}

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
  const [schedulePattern, setSchedulePattern] = useState(template?.schedule_pattern ?? "");
  const [isSaving, setIsSaving] = useState(false);

  const isEdit = !!template;

  async function handleSave() {
    if (!name.trim() || !rawTextTemplate.trim()) return;

    setIsSaving(true);
    try {
      const data: CreateTemplateRequest = {
        name: name.trim(),
        pillar: pillar || undefined,
        raw_text_template: rawTextTemplate,
        schedule_pattern: schedulePattern || undefined,
      };

      if (isEdit && template) {
        await api.updateTemplate(template.id, data);
      } else {
        await api.createTemplate(data);
      }
      onSave();
      // Reset form
      setName("");
      setPillar("");
      setRawTextTemplate("");
      setSchedulePattern("");
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
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="template-name">Template Name</Label>
            <Input
              id="template-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Weekly Farm Update"
            />
          </div>

          <div>
            <Label htmlFor="template-pillar">Pillar (optional)</Label>
            <Input
              id="template-pillar"
              value={pillar}
              onChange={(e) => setPillar(e.target.value)}
              placeholder="e.g. farm, spiritual, events"
            />
          </div>

          <div>
            <Label htmlFor="template-raw-text">Raw Text Template</Label>
            <Textarea
              id="template-raw-text"
              value={rawTextTemplate}
              onChange={(e) => setRawTextTemplate(e.target.value)}
              placeholder="Use {{variable}} for dynamic parts..."
              rows={4}
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Use {"{{variable}}"} syntax for dynamic content
            </p>
          </div>

          <div>
            <Label htmlFor="template-schedule">Schedule Pattern (optional)</Label>
            <Input
              id="template-schedule"
              value={schedulePattern}
              onChange={(e) => setSchedulePattern(e.target.value)}
              placeholder="e.g. weekly, monthly"
            />
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
