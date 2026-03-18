import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  api,
  request,
  type ContentRow,
  type GenerateRequest,
} from "@/lib/api";
import {
  Loader2,
  RotateCcw,
  History,
  ChevronRight,
  Sparkles,
  PenLine,
  Copy,
  Save,
} from "lucide-react";

// --- Platform config ---

const PLATFORM_META: Record<string, { label: string; accent: string }> = {
  instagram: { label: "Instagram", accent: "bg-gradient-to-r from-purple-500 to-pink-500" },
  facebook: { label: "Facebook", accent: "bg-blue-600" },
  tiktok: { label: "TikTok", accent: "bg-black" },
  threads: { label: "Threads", accent: "bg-neutral-800" },
  linkedin: { label: "LinkedIn", accent: "bg-sky-700" },
};

// --- Types ---

export type EditorMode = "create" | "refine" | "repurpose";

export interface ContentEditorProps {
  contentRow: ContentRow | null;
  mode: EditorMode;
  isOpen: boolean;
  onClose: () => void;
  onSave: (updatedRow: ContentRow) => void;
}

const MODE_CONFIG: Record<EditorMode, { title: string; icon: React.ReactNode; action: string }> = {
  create: {
    title: "Create Content",
    icon: <Sparkles className="h-4 w-4" />,
    action: "Generate",
  },
  refine: {
    title: "Refine Content",
    icon: <PenLine className="h-4 w-4" />,
    action: "Update",
  },
  repurpose: {
    title: "Repurpose Content",
    icon: <Copy className="h-4 w-4" />,
    action: "Create New",
  },
};

const ALL_PLATFORMS = [
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "threads", label: "Threads" },
  { id: "linkedin", label: "LinkedIn" },
];

// --- Component ---

export function ContentEditor({
  contentRow,
  mode,
  isOpen,
  onClose,
  onSave,
}: ContentEditorProps) {
  const queryClient = useQueryClient();
  const config = MODE_CONFIG[mode];

  // Local caption state (editable)
  const [captions, setCaptions] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<string>("");
  const [instruction, setInstruction] = useState("");
  const [isIterating, setIsIterating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [expandedIter, setExpandedIter] = useState<Set<number>>(new Set());
  const prevRowIdRef = useRef<number | null>(null);

  // Repurpose state
  const [repurposePlatforms, setRepurposePlatforms] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [repurposeGenerated, setRepurposeGenerated] = useState(false);
  const [repurposeRowId, setRepurposeRowId] = useState<number | null>(null);

  // Stable platform list derived from contentRow only (no captions dependency)
  const basePlatforms = useMemo(() => {
    if (!contentRow) return [];
    return Object.keys(contentRow.captions).filter(
      (k) => contentRow.captions[k] !== null,
    );
  }, [contentRow]);

  // Display platforms: after repurpose generation, show generated platforms
  const platforms =
    mode === "repurpose" && repurposeGenerated
      ? Object.keys(captions)
      : basePlatforms;

  // Initialize state when contentRow changes
  useEffect(() => {
    if (contentRow && contentRow.row_number !== prevRowIdRef.current) {
      const parsed: Record<string, string> = {};
      for (const [k, v] of Object.entries(contentRow.captions)) {
        if (v !== null) parsed[k] = v;
      }
      setCaptions(parsed);
      setError("");
      setActiveTab(basePlatforms[0] ?? "");
      setInstruction("");
      setExpandedIter(new Set());
      setRepurposePlatforms([]);
      setRepurposeGenerated(false);
      setRepurposeRowId(null);
      prevRowIdRef.current = contentRow.row_number;
    }
  }, [contentRow, basePlatforms]);

  // Fetch iteration history
  const { data: iterations = [] } = useQuery({
    queryKey: ["iterations", contentRow?.row_number],
    queryFn: () =>
      contentRow ? api.getIterations(contentRow.row_number) : Promise.resolve([]),
    enabled: isOpen && !!contentRow,
  });

  // --- Handlers ---

  async function handleIterate() {
    if (!contentRow || !instruction.trim() || !activeTab) return;

    setIsIterating(true);
    setError("");
    try {
      const result = await api.iterate({
        content_row_id: contentRow.row_number,
        platform: activeTab,
        instruction: instruction.trim(),
        mode,
      });
      setCaptions((prev) => ({ ...prev, [activeTab]: result.caption }));
      setInstruction("");
      queryClient.invalidateQueries({
        queryKey: ["iterations", contentRow.row_number],
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Iteration failed");
    } finally {
      setIsIterating(false);
    }
  }

  async function handleSave() {
    if (!contentRow) return;
    setIsSaving(true);
    setError("");
    try {
      const updated = await api.editDraft(contentRow.row_number, captions);
      onSave(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRepurpose() {
    if (!contentRow || repurposePlatforms.length === 0) return;
    setIsGenerating(true);
    setError("");
    try {
      const data: GenerateRequest = {
        raw_text: contentRow.raw_text,
        platforms: repurposePlatforms,
        scheduled_date: contentRow.date?.split("T")[0] ?? new Date().toISOString().split("T")[0],
      };
      const result = await request<{
        captions: Record<string, string>;
        row_id?: number;
      }>("/api/generate-sync", {
        method: "POST",
        body: JSON.stringify(data),
      });
      setCaptions(result.captions);
      if (result.row_id) setRepurposeRowId(result.row_id);
      setRepurposeGenerated(true);
      setActiveTab(repurposePlatforms[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleSaveRepurpose() {
    if (!repurposeRowId) return;
    setIsSaving(true);
    setError("");
    try {
      const updated = await api.editDraft(repurposeRowId, captions);
      onSave(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  }

  function toggleRepurposePlatform(platform: string) {
    setRepurposePlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform],
    );
  }

  function handleRestoreCaption(caption: string) {
    setCaptions((prev) => ({ ...prev, [activeTab]: caption }));
  }

  if (!contentRow) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {config.icon}
            <DialogTitle>{config.title}</DialogTitle>
          </div>
          <DialogDescription className="flex items-center gap-2">
            <span className="truncate">{contentRow.raw_text}</span>
            {contentRow.source === "template" && (
              <Badge variant="secondary" className="shrink-0">
                Template
              </Badge>
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Repurpose: platform selector + original content reference */}
        {mode === "repurpose" && !repurposeGenerated && (
          <div className="space-y-4">
            {/* Original content reference */}
            <div className="rounded-md border bg-muted/20 px-3 py-2">
              <p className="text-[10px] font-medium uppercase text-muted-foreground mb-1">
                Original Content
              </p>
              {Object.entries(contentRow.captions)
                .filter(([, v]) => v !== null)
                .map(([platform, caption]) => (
                  <div key={platform} className="mt-2">
                    <span className="text-xs font-medium capitalize">{platform}:</span>
                    <p className="text-sm text-muted-foreground mt-0.5 line-clamp-3">{caption}</p>
                  </div>
                ))}
            </div>

            {/* Platform selector */}
            <div>
              <Label className="text-sm font-medium">Repurpose for these platforms:</Label>
              <div className="flex flex-wrap gap-3 mt-2">
                {ALL_PLATFORMS.map(({ id, label }) => (
                  <label key={id} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={repurposePlatforms.includes(id)}
                      onCheckedChange={() => toggleRepurposePlatform(id)}
                      aria-label={label}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>

            {/* Generate button */}
            <Button
              onClick={handleRepurpose}
              disabled={isGenerating || repurposePlatforms.length === 0}
              className="w-full"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Copy className="mr-2 h-4 w-4" />
                  Generate Repurposed Captions
                </>
              )}
            </Button>
          </div>
        )}

        {/* Platform tabs — shown for refine/create, and repurpose after generation */}
        {(mode !== "repurpose" || repurposeGenerated) && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full">
            {platforms.map((platform) => {
              const meta = PLATFORM_META[platform] ?? {
                label: platform,
                accent: "bg-gray-500",
              };
              return (
                <TabsTrigger key={platform} value={platform} className="gap-1.5">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${meta.accent}`}
                  />
                  {meta.label}
                </TabsTrigger>
              );
            })}
          </TabsList>

          {platforms.map((platform) => (
            <TabsContent key={platform} value={platform} className="space-y-3 pt-2">
              {/* Caption editor */}
              <Textarea
                value={captions[platform] ?? ""}
                onChange={(e) =>
                  setCaptions((prev) => ({
                    ...prev,
                    [platform]: e.target.value,
                  }))
                }
                rows={5}
                className="resize-y font-mono text-sm leading-relaxed"
                placeholder={`${PLATFORM_META[platform]?.label ?? platform} caption...`}
              />

              {/* Iteration input */}
              <div className="flex gap-2">
                <Input
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder="Iteration instruction (e.g. 'Make it shorter')"
                  disabled={isIterating}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleIterate();
                    }
                  }}
                />
                <Button
                  variant="outline"
                  onClick={handleIterate}
                  disabled={isIterating || !instruction.trim()}
                  aria-label="Iterate"
                >
                  {isIterating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RotateCcw className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </TabsContent>
          ))}
        </Tabs>
        )}

        {/* Error display */}
        {error && (
          <p className="text-sm text-destructive" role="alert">{error}</p>
        )}

        {/* Iteration history log — always visible, full content */}
        {iterations.length > 0 && (
          <div className="rounded-lg border">
            <div className="flex items-center gap-1.5 bg-muted/30 px-4 py-2.5 text-sm font-medium">
              <History className="h-4 w-4" />
              Iteration Log ({iterations.length})
            </div>
            <div className="max-h-[400px] overflow-y-auto">
              {[...iterations].reverse().map((iter) => {
                const isOpen = expandedIter.has(iter.id);
                return (
                  <div key={iter.id} className="border-t">
                    {/* Collapsed row — click to expand */}
                    <button
                      onClick={() =>
                        setExpandedIter((prev) => {
                          const next = new Set(prev);
                          if (next.has(iter.id)) next.delete(iter.id);
                          else next.add(iter.id);
                          return next;
                        })
                      }
                      className="flex w-full items-center gap-2 px-4 py-2.5 text-left hover:bg-muted/20 transition-colors"
                    >
                      <ChevronRight
                        className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${
                          isOpen ? "rotate-90" : ""
                        }`}
                      />
                      <span
                        className={`inline-block h-2 w-2 shrink-0 rounded-full ${
                          PLATFORM_META[iter.platform]?.accent ?? "bg-gray-400"
                        }`}
                      />
                      <span className="text-xs font-medium shrink-0">
                        {PLATFORM_META[iter.platform]?.label ?? iter.platform}
                      </span>
                      <span className="text-xs italic text-muted-foreground truncate flex-1">
                        &ldquo;{iter.refinement_instruction}&rdquo;
                      </span>
                      <span className="text-[10px] text-muted-foreground shrink-0">
                        {new Date(iter.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </button>

                    {/* Expanded content */}
                    {isOpen && (
                      <div className="px-4 pb-3 pt-0">
                        <div className="rounded-md bg-muted/30 px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap">
                          {iter.new_caption}
                        </div>
                        <div className="mt-2 flex justify-end">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => {
                              setActiveTab(iter.platform);
                              handleRestoreCaption(iter.new_caption);
                            }}
                          >
                            Restore this version
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Footer actions */}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {mode === "repurpose" && repurposeGenerated ? (
            <Button onClick={handleSaveRepurpose} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save as New Draft
            </Button>
          ) : mode !== "repurpose" ? (
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              {config.action}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
