import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Download, FileImage, HardDrive, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { errorDetail } from "@/components/media/media-utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface DriveImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Browse a shared Drive folder and batch-import images to the catalog. */
export function DriveImportDialog({ open, onOpenChange }: DriveImportDialogProps) {
  const queryClient = useQueryClient();
  const [folderId, setFolderId] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [importResult, setImportResult] = useState<{
    imported: number;
    skipped: string[];
  } | null>(null);

  const browse = useQuery({
    queryKey: ["drive", "browse", folderId],
    queryFn: () => api.browseDrive(folderId),
    enabled: !!folderId && open,
  });

  const importMutation = useMutation({
    mutationFn: (fileIds: string[]) => api.importFromDrive(fileIds),
    onSuccess: (data) => {
      setImportResult({ imported: data.imported, skipped: data.skipped });
      void queryClient.invalidateQueries({ queryKey: ["media"] });
    },
    onError: (err) => toast.error(errorDetail(err, "Couldn't import from Drive")),
  });

  function toggleFile(id: string) {
    setSelectedFiles((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    const files = browse.data?.files ?? [];
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(files.map((f) => f.id)));
    }
  }

  function handleClose() {
    setImportResult(null);
    setSelectedFiles(new Set());
    onOpenChange(false);
  }

  const files = browse.data?.files ?? [];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="ink flex items-center gap-2.5 font-serif">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-sage-100 bg-sage-50 text-sage-700 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-200">
              <HardDrive size={15} strokeWidth={1.75} aria-hidden="true" />
            </span>
            Import from Google Drive
          </DialogTitle>
          <DialogDescription className="t-caption ink-muted">
            Browse a shared Drive folder and import images to the media catalog.
          </DialogDescription>
        </DialogHeader>

        {importResult ? (
          <>
            <div className="flex flex-col items-center py-8">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-sage-100 bg-sage-50 text-sage-600 dark:border-sage-700 dark:bg-sage-800 dark:text-sage-200">
                <Check size={22} strokeWidth={1.75} aria-hidden="true" />
              </div>
              <p className="t-title ink font-serif">
                {importResult.imported} files imported
              </p>
              {importResult.skipped.length > 0 && (
                <p className="t-caption ink-muted mt-1">
                  {importResult.skipped.length} already in catalog (skipped)
                </p>
              )}
            </div>
            <DialogFooter>
              <Button size="sm" className="fr" onClick={handleClose}>
                Done
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="drive-folder-id" className="t-caption ink font-medium">
                  Drive folder ID
                </Label>
                <Input
                  id="drive-folder-id"
                  placeholder="Paste Google Drive folder ID…"
                  value={folderId}
                  onChange={(e) => {
                    setFolderId(e.target.value);
                    setSelectedFiles(new Set());
                  }}
                  className="fr"
                />
                <p className="t-micro ink-muted">
                  The folder must be shared with the service account email
                </p>
              </div>

              {browse.isLoading && (
                <div
                  role="status"
                  aria-label="Browsing Drive folder"
                  className="flex items-center justify-center py-8"
                >
                  <Loader2 size={18} className="ink-muted animate-spin" aria-hidden="true" />
                </div>
              )}

              {browse.isError && (
                <p className="t-caption text-terra-600 dark:text-terra-300">
                  Couldn't browse that Drive folder. Check the folder ID and sharing.
                </p>
              )}

              {files.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="t-body-sm ink font-medium">
                      {files.length} images found
                    </span>
                    <Button variant="ghost" size="sm" className="fr" onClick={toggleAll}>
                      {selectedFiles.size === files.length
                        ? "Deselect all"
                        : "Select all"}
                    </Button>
                  </div>
                  <div className="grid max-h-[40vh] grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3">
                    {files.map((f) => (
                      <label
                        key={f.id}
                        className={cn(
                          "flex cursor-pointer items-start gap-2 rounded-lg border p-2 transition-colors",
                          selectedFiles.has(f.id)
                            ? "border-sage-300 bg-sage-50/50 dark:border-sage-600 dark:bg-sage-800/40"
                            : "border-hair hover:bg-muted/30",
                        )}
                      >
                        <Checkbox
                          checked={selectedFiles.has(f.id)}
                          onCheckedChange={() => toggleFile(f.id)}
                          className="fr mt-1"
                          aria-label={`Select ${f.name}`}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="bg-warm mb-1 block h-16 w-full overflow-hidden rounded">
                            {f.thumbnail_link ? (
                              <img
                                src={f.thumbnail_link}
                                alt={f.name}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <span className="flex h-full w-full items-center justify-center">
                                <FileImage
                                  size={18}
                                  strokeWidth={1.75}
                                  className="ink-muted"
                                  aria-hidden="true"
                                />
                              </span>
                            )}
                          </span>
                          <span className="t-micro ink block truncate">{f.name}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {folderId &&
                !browse.isLoading &&
                files.length === 0 &&
                !browse.isError && (
                  <p className="t-caption ink-muted py-4 text-center">
                    No images found in this folder
                  </p>
                )}
            </div>

            <DialogFooter>
              <Button variant="outline" size="sm" className="fr" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                size="sm"
                className="fr"
                onClick={() => importMutation.mutate(Array.from(selectedFiles))}
                disabled={selectedFiles.size === 0 || importMutation.isPending}
                aria-busy={importMutation.isPending}
              >
                {importMutation.isPending ? (
                  <Loader2 size={12} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Download size={12} strokeWidth={1.75} aria-hidden="true" />
                )}
                Import {selectedFiles.size} files
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
