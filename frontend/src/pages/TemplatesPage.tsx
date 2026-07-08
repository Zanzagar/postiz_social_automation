import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutTemplate, Plus } from "lucide-react";

import { api, type Template } from "@/lib/api";
import { EmptyState, PageHeader, SkeletonText } from "@/components/pasture";
import { Button } from "@/components/ui/button";
import { TemplateCard } from "@/components/templates/TemplateCard";
import { TemplateEditor } from "@/components/templates/TemplateEditor";
import { UseTemplateSheet } from "@/components/templates/UseTemplateSheet";

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.getTemplates(),
  });
  const { data: pillars } = useQuery({
    queryKey: ["pillars"],
    queryFn: () => api.getPillars(true),
  });

  const [mode, setMode] = useState<"browse" | "editor">("browse");
  const [editing, setEditing] = useState<Template | null>(null);
  const [using, setUsing] = useState<Template | null>(null);
  const [deleteError, setDeleteError] = useState("");

  function openEditor(template: Template | null) {
    setEditing(template);
    setMode("editor");
  }

  function backToBrowse() {
    setEditing(null);
    setMode("browse");
  }

  function handleSaved() {
    queryClient.invalidateQueries({ queryKey: ["templates"] });
    backToBrowse();
  }

  function handleRunOnce(saved: Template) {
    queryClient.invalidateQueries({ queryKey: ["templates"] });
    backToBrowse();
    setUsing(saved);
  }

  async function handleDelete(template: Template) {
    if (!window.confirm(`Delete "${template.name}"? This cannot be undone.`)) {
      return;
    }
    setDeleteError("");
    try {
      await api.deleteTemplate(template.id);
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="flex min-h-full flex-col">
      <PageHeader
        greeting="Templates"
        title="Reusable vessels."
        subtitle="Fill them in, schedule them in batches, keep the rhythm without repeating yourself."
        icon={LayoutTemplate}
        right={
          <Button
            className="fr"
            onClick={() => (mode === "editor" ? backToBrowse() : openEditor(null))}
          >
            {mode === "editor" ? (
              "Back to library"
            ) : (
              <>
                <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
                New template
              </>
            )}
          </Button>
        }
      />

      {mode === "browse" ? (
        <div className="flex-1 px-8 py-6" aria-busy={isLoading}>
          {isLoading ? (
            <SkeletonText lines={4} className="max-w-md" />
          ) : !templates || templates.length === 0 ? (
            <EmptyState
              icon={LayoutTemplate}
              title="No vessels yet"
              body="Write a template once — fill it in each week and keep the rhythm without repeating yourself."
              action={
                <Button className="fr" onClick={() => openEditor(null)}>
                  <Plus size={13} strokeWidth={1.75} aria-hidden="true" />
                  New template
                </Button>
              }
            />
          ) : (
            <div className="grid max-w-5xl gap-4 sm:grid-cols-2">
              {templates.map((t) => (
                <TemplateCard
                  key={t.id}
                  template={t}
                  onEdit={() => openEditor(t)}
                  onUse={() => setUsing(t)}
                  onDelete={() => handleDelete(t)}
                />
              ))}
            </div>
          )}
          {deleteError && (
            <p role="alert" className="t-caption mt-3 text-terra-600 dark:text-terra-300">
              {deleteError}
            </p>
          )}
        </div>
      ) : (
        <TemplateEditor
          key={editing?.id ?? "new"}
          template={editing}
          pillars={pillars ?? []}
          onCancel={backToBrowse}
          onSaved={handleSaved}
          onRunOnce={handleRunOnce}
        />
      )}

      {using && (
        <UseTemplateSheet template={using} onClose={() => setUsing(null)} />
      )}
    </div>
  );
}
