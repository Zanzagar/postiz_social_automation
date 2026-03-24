import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
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
import {
  Check,
  Download,
  FileImage,
  HardDrive,
  Loader2,
} from "lucide-react";

interface DriveImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DriveImportDialog({
  open,
  onOpenChange,
}: DriveImportDialogProps) {
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
      queryClient.invalidateQueries({ queryKey: ["media"] });
    },
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
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            Import from Google Drive
          </DialogTitle>
          <DialogDescription>
            Browse a shared Drive folder and import images to the media catalog.
          </DialogDescription>
        </DialogHeader>

        {importResult ? (
          <>
            <div className="flex flex-col items-center py-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100 mb-4">
                <Check className="h-6 w-6 text-green-600" />
              </div>
              <p className="text-lg font-medium">
                {importResult.imported} files imported
              </p>
              {importResult.skipped.length > 0 && (
                <p className="text-sm text-muted-foreground mt-1">
                  {importResult.skipped.length} already in catalog (skipped)
                </p>
              )}
            </div>
            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <div className="space-y-4">
              <div>
                <Label>Drive Folder ID</Label>
                <Input
                  placeholder="Paste Google Drive folder ID..."
                  value={folderId}
                  onChange={(e) => {
                    setFolderId(e.target.value);
                    setSelectedFiles(new Set());
                  }}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  The folder must be shared with the service account email
                </p>
              </div>

              {browse.isLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              )}

              {browse.isError && (
                <p className="text-sm text-destructive">
                  Failed to browse Drive folder. Check folder ID and sharing.
                </p>
              )}

              {files.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {files.length} images found
                    </span>
                    <Button variant="ghost" size="sm" onClick={toggleAll}>
                      {selectedFiles.size === files.length
                        ? "Deselect All"
                        : "Select All"}
                    </Button>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[40vh] overflow-y-auto">
                    {files.map((f) => (
                      <label
                        key={f.id}
                        className={`flex items-start gap-2 rounded-lg border p-2 cursor-pointer transition-colors ${
                          selectedFiles.has(f.id)
                            ? "bg-sage-50/50 border-sage-300"
                            : "hover:bg-muted/30"
                        }`}
                      >
                        <Checkbox
                          checked={selectedFiles.has(f.id)}
                          onCheckedChange={() => toggleFile(f.id)}
                          className="mt-1"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="h-16 w-full rounded bg-muted overflow-hidden mb-1">
                            {f.thumbnail_link ? (
                              <img
                                src={f.thumbnail_link}
                                alt={f.name}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <div className="flex h-full w-full items-center justify-center">
                                <FileImage className="h-6 w-6 text-muted-foreground/30" />
                              </div>
                            )}
                          </div>
                          <p className="text-xs truncate">{f.name}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {folderId && !browse.isLoading && files.length === 0 && !browse.isError && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No images found in this folder
                </p>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={() =>
                  importMutation.mutate(Array.from(selectedFiles))
                }
                disabled={selectedFiles.size === 0 || importMutation.isPending}
                className="gap-2"
              >
                {importMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Import {selectedFiles.size} Files
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
