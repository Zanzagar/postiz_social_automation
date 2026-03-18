import { useState, useEffect, useCallback, useMemo } from "react";
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
import {
  api,
  type ContentRow,
  type Suggestion,
  type IterationRecord,
} from "@/lib/api";
import {
  Loader2,
  RotateCcw,
  History,
  ChevronDown,
  ChevronUp,
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
  suggestion?: Suggestion;
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
  const [historyOpen, setHistoryOpen] = useState(false);

  // Parse captions from contentRow
  const platforms = useMemo(() => {
    if (!contentRow) return [];
    return Object.keys(contentRow.captions).filter(
      (k) => contentRow.captions[k] !== null,
    );
  }, [contentRow]);

  // Initialize state when contentRow changes
  useEffect(() => {
    if (contentRow) {
      const parsed: Record<string, string> = {};
      for (const [k, v] of Object.entries(contentRow.captions)) {
        if (v !== null) parsed[k] = v;
      }
      setCaptions(parsed);
      if (platforms.length > 0 && !platforms.includes(activeTab)) {
        setActiveTab(platforms[0]);
      }
    }
  }, [contentRow, platforms, activeTab]);

  // Fetch iteration history
  const { data: iterations = [] } = useQuery({
    queryKey: ["iterations", contentRow?.row_number],
    queryFn: () =>
      contentRow ? api.getIterations(contentRow.row_number) : Promise.resolve([]),
    enabled: isOpen && !!contentRow,
  });

  // Filter history for active platform
  const platformHistory = useMemo(
    () => iterations.filter((i) => i.platform === activeTab),
    [iterations, activeTab],
  );

  // --- Handlers ---

  const handleIterate = useCallback(async () => {
    if (!contentRow || !instruction.trim() || !activeTab) return;

    setIsIterating(true);
    try {
      const result = await api.iterate({
        content_row_id: contentRow.row_number,
        platform: activeTab,
        instruction: instruction.trim(),
        mode,
      });
      setCaptions((prev) => ({ ...prev, [activeTab]: result.caption }));
      setInstruction("");
      // Refresh iteration history
      queryClient.invalidateQueries({
        queryKey: ["iterations", contentRow.row_number],
      });
    } finally {
      setIsIterating(false);
    }
  }, [contentRow, instruction, activeTab, mode, queryClient]);

  const handleSave = useCallback(async () => {
    if (!contentRow) return;
    setIsSaving(true);
    try {
      const updated = await api.editDraft(contentRow.row_number, captions);
      onSave(updated);
      onClose();
    } finally {
      setIsSaving(false);
    }
  }, [contentRow, captions, onSave, onClose]);

  const handleRestoreCaption = useCallback(
    (caption: string) => {
      setCaptions((prev) => ({ ...prev, [activeTab]: caption }));
    },
    [activeTab],
  );

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

        {/* Platform tabs */}
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

              {/* Iteration history (collapsible) */}
              {platformHistory.length > 0 && (
                <div className="rounded-lg border bg-muted/30">
                  <button
                    onClick={() => setHistoryOpen(!historyOpen)}
                    className="flex w-full items-center justify-between px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
                    aria-label="Toggle history"
                  >
                    <span className="flex items-center gap-1.5">
                      <History className="h-3.5 w-3.5" />
                      {platformHistory.length} revision{platformHistory.length !== 1 ? "s" : ""}
                    </span>
                    {historyOpen ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </button>

                  {historyOpen && (
                    <div className="max-h-48 space-y-1 overflow-y-auto border-t px-3 py-2">
                      {platformHistory.map((iter) => (
                        <button
                          key={iter.id}
                          onClick={() => handleRestoreCaption(iter.new_caption)}
                          className="w-full rounded-md px-2 py-1.5 text-left text-xs hover:bg-muted transition-colors"
                        >
                          <div className="flex items-center justify-between text-muted-foreground">
                            <span className="italic">
                              "{iter.refinement_instruction}"
                            </span>
                            <span className="shrink-0">
                              {new Date(iter.created_at).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                          <p className="mt-0.5 line-clamp-2 text-foreground">
                            {iter.new_caption}
                          </p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </TabsContent>
          ))}
        </Tabs>

        {/* Footer actions */}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            {config.action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
