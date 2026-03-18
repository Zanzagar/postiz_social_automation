import { useState, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import {
  api,
  request,
  type GenerateRequest,
  type Pillar,
  type Template,
} from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Upload,
  Loader2,
  X,
  FileText,
  RotateCcw,
  Send,
  Save,
  Sparkles,
} from "lucide-react";
import { format } from "date-fns";

const PLATFORMS = [
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "threads", label: "Threads" },
  { id: "linkedin", label: "LinkedIn" },
];

function SendToPostizButton({
  captions,
  formData,
}: {
  captions: Record<string, string>;
  formData: GenerateRequest;
}) {
  const [isSending, setIsSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

  async function handleSend() {
    setIsSending(true);
    setSendResult(null);
    try {
      const result = await api.sendToPostiz({
        captions,
        media_url: formData.media_url,
        scheduled_at: formData.scheduled_date,
      });
      setSendResult(
        `Sent to Postiz: ${result.draft_ids.length} draft(s) created`,
      );
    } catch (err) {
      setSendResult(
        `Error: ${err instanceof Error ? err.message : "Failed to send"}`,
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <>
      <Button onClick={handleSend} disabled={isSending} className="flex-1">
        {isSending ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Send className="mr-2 h-4 w-4" />
        )}
        Send to Postiz
      </Button>
      {sendResult && (
        <p
          className={`text-sm ${sendResult.startsWith("Error") ? "text-destructive" : "text-sage-600"}`}
        >
          {sendResult}
        </p>
      )}
    </>
  );
}

type CreateMode = "template" | "freeform";

export function CreatePage() {
  const [mode, setMode] = useState<CreateMode>("freeform");

  // Pillars
  const { data: pillars = [] } = useQuery({
    queryKey: ["pillars", "active"],
    queryFn: () => api.getPillars(true),
  });
  const [selectedPillar, setSelectedPillar] = useState<string>("");

  // Template state
  const { data: templates = [] } = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.getTemplates(),
  });
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(
    null,
  );
  const [variableValues, setVariableValues] = useState<Record<string, string>>(
    {},
  );

  // Form state
  const [rawText, setRawText] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [scheduledDate, setScheduledDate] = useState(
    format(new Date(), "yyyy-MM-dd"),
  );
  const [scheduledTime, setScheduledTime] = useState("09:00");

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [captions, setCaptions] = useState<Record<string, string> | null>(
    null,
  );
  const [error, setError] = useState("");

  // Inline iteration state (per-platform instructions)
  const [platformInstructions, setPlatformInstructions] = useState<Record<string, string>>({});
  const [iteratePlatform, setIteratePlatform] = useState("");
  const [isIterating, setIsIterating] = useState(false);
  const [contentRowId, setContentRowId] = useState<number | null>(null);

  const [savedMessage, setSavedMessage] = useState("");

  // Batch generation state
  const [batchWeeks, setBatchWeeks] = useState(4);
  const [isBatchGenerating, setIsBatchGenerating] = useState(false);
  const [batchResult, setBatchResult] = useState<{ created: number } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Template handling ---

  function handleTemplateSelect(template: Template) {
    setSelectedTemplate(template);
    setRawText(template.raw_text_template ?? "");
    if (template.schedule_time) setScheduledTime(template.schedule_time);
    const defaults: Record<string, string> = {};
    for (const v of template.variables ?? []) {
      defaults[v.name] = "";
    }
    setVariableValues(defaults);
  }

  function handleClearTemplate() {
    setSelectedTemplate(null);
    setVariableValues({});
    setRawText("");
  }

  // --- Platform toggle ---

  function togglePlatform(platform: string) {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform],
    );
  }

  // --- File upload ---

  const handleFileChange = useCallback(async (file: File) => {
    setUploadedFile(file);
    try {
      const result = await api.uploadFile(file);
      setMediaUrl(result.url);
    } catch {
      setError("Failed to upload file");
      setUploadedFile(null);
    }
  }, []);

  // --- Generate ---

  async function handleGenerate() {
    if (!rawText.trim() || selectedPlatforms.length === 0) {
      setError("Please enter text and select at least one platform.");
      return;
    }

    setError("");
    setIsGenerating(true);
    setStatusMessage("Starting generation...");
    setCaptions(null);
    setContentRowId(null);

    try {
      if (selectedTemplate) {
        // Generate from template
        setStatusMessage("Generating from template...");
        const result = await api.generateFromTemplate(selectedTemplate.id, {
          variable_values: variableValues,
          platforms: selectedPlatforms,
          scheduled_date: scheduledDate,
          scheduled_time: scheduledTime,
        });
        // Extract captions from the returned content row
        const resultCaptions: Record<string, string> = {};
        for (const [k, v] of Object.entries(result.captions)) {
          if (v !== null) resultCaptions[k] = v;
        }
        setCaptions(resultCaptions);
        setContentRowId(result.row_number);
      } else {
        // Direct generation
        setStatusMessage("Generating captions...");
        const data: GenerateRequest = {
          raw_text: rawText,
          media_url: mediaUrl || null,
          platforms: selectedPlatforms,
          scheduled_date: scheduledDate,
          content_pillar: selectedPillar || null,
        };
        const result = await request<{
          captions: Record<string, string>;
          row_id?: number;
        }>("/api/generate-sync", {
          method: "POST",
          body: JSON.stringify(data),
        });
        setCaptions(result.captions);
        if (result.row_id) setContentRowId(result.row_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setIsGenerating(false);
      setStatusMessage("");
    }
  }

  // --- Inline iteration ---

  async function handleIterate(platform: string) {
    const instruction = platformInstructions[platform]?.trim();
    if (!instruction || !contentRowId) return;

    setIsIterating(true);
    setIteratePlatform(platform);
    try {
      const result = await api.iterate({
        content_row_id: contentRowId,
        platform,
        instruction,
        mode: "refine",
      });
      setCaptions((prev) =>
        prev ? { ...prev, [platform]: result.caption } : prev,
      );
      setPlatformInstructions((prev) => ({ ...prev, [platform]: "" }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Iteration failed");
    } finally {
      setIsIterating(false);
      setIteratePlatform("");
    }
  }

  async function handleBatchSchedule() {
    if (!selectedTemplate || selectedPlatforms.length === 0) return;
    setIsBatchGenerating(true);
    setError("");
    setBatchResult(null);
    try {
      const result = await api.batchGenerateFromTemplate(selectedTemplate.id, {
        variable_values: {},
        platforms: selectedPlatforms,
        weeks: batchWeeks,
        scheduled_time: scheduledTime,
      });
      setBatchResult({ created: result.created });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scheduling failed");
    } finally {
      setIsBatchGenerating(false);
    }
  }

  async function handleSaveDraft() {
    if (!contentRowId || !captions) return;
    try {
      await api.editDraft(contentRowId, captions);
      setSavedMessage("Saved to Drafts — find it under Review Drafts.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  const formData: GenerateRequest = {
    raw_text: rawText,
    media_url: mediaUrl || null,
    platforms: selectedPlatforms,
    content_pillar: selectedPillar || null,
    scheduled_date: scheduledDate,
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-sage-800">Create & Generate</h1>

      {/* Workflow toggle */}
      {templates.length > 0 && (
        <Tabs
          value={mode}
          onValueChange={(v) => {
            setMode(v as CreateMode);
            if (v === "freeform") handleClearTemplate();
          }}
        >
          <TabsList className="w-full">
            <TabsTrigger value="freeform" className="flex-1">
              Write from Scratch
            </TabsTrigger>
            <TabsTrigger value="template" className="flex-1">
              Use a Template
            </TabsTrigger>
          </TabsList>
        </Tabs>
      )}

      {/* MODE: Template */}
      {mode === "template" && (
        <Card>
          <CardContent className="space-y-3 pt-4">
            {selectedTemplate ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary">{selectedTemplate.name}</Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearTemplate}
                  >
                    <X className="mr-1 h-3 w-3" />
                    Change
                  </Button>
                </div>

                {/* Variable inputs */}
                {(selectedTemplate.variables ?? []).length > 0 && (
                  <div className="space-y-2">
                    {selectedTemplate.variables.map((v) => (
                      <div key={v.name}>
                        <Label htmlFor={`var-${v.name}`} className="text-xs capitalize">
                          {v.name}
                        </Label>
                        <Input
                          id={`var-${v.name}`}
                          aria-label={v.name}
                          value={variableValues[v.name] ?? ""}
                          onChange={(e) =>
                            setVariableValues((prev) => ({
                              ...prev,
                              [v.name]: e.target.value,
                            }))
                          }
                          placeholder={`Enter ${v.name}...`}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {/* Template preview */}
                <div className="rounded-md border bg-muted/20 px-3 py-2 text-sm leading-relaxed">
                  {rawText.split(/(\{\{.+?\}\})/).map((part, i) =>
                    part.match(/^\{\{(.+?)\}\}$/) ? (
                      <span
                        key={i}
                        className="mx-0.5 inline-block rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800"
                      >
                        {variableValues[part.match(/^\{\{(.+?)\}\}$/)![1]] ||
                          part.match(/^\{\{(.+?)\}\}$/)![1]}
                      </span>
                    ) : (
                      <span key={i}>{part}</span>
                    ),
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Fill in the fields above to complete the template.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Pick a template to get started:
                </p>
                <div className="flex flex-wrap gap-2">
                  {templates.map((t) => (
                    <Button
                      key={t.id}
                      variant="outline"
                      size="sm"
                      onClick={() => handleTemplateSelect(t)}
                    >
                      <FileText className="mr-1.5 h-3.5 w-3.5" />
                      {t.name}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* MODE: Freeform */}
      {mode === "freeform" && (
        <div className="space-y-2">
          <Label htmlFor="raw-text">What do you want to post about?</Label>
          <Textarea
            id="raw-text"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Describe what you want to post — the AI will write platform-specific captions from this..."
            rows={4}
            maxLength={2000}
          />
          <p className="text-right text-xs text-muted-foreground">
            {rawText.length}/2000
          </p>
        </div>
      )}

      {/* Upload zone */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Media</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              if (file) handleFileChange(file);
            }}
            className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-sage-200 p-6 text-muted-foreground transition-colors hover:border-sage-400 hover:bg-sage-50"
          >
            <Upload className="h-6 w-6" />
            <span className="text-sm">
              {uploadedFile
                ? uploadedFile.name
                : "Drop image/video or click to browse"}
            </span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileChange(file);
            }}
          />

          {uploadedFile && (
            <div className="flex items-center justify-between rounded-md bg-muted px-3 py-1.5 text-sm">
              <span className="truncate">{uploadedFile.name}</span>
              <button
                onClick={() => {
                  setUploadedFile(null);
                  setMediaUrl("");
                }}
                className="ml-2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          <div>
            <Label
              htmlFor="media-url"
              className="text-xs text-muted-foreground"
            >
              Or paste Google Drive URL
            </Label>
            <Input
              id="media-url"
              value={mediaUrl}
              onChange={(e) => setMediaUrl(e.target.value)}
              placeholder="https://drive.google.com/..."
              disabled={!!uploadedFile}
            />
          </div>
        </CardContent>
      </Card>

      {/* Platforms */}
      <fieldset>
        <legend className="mb-2 text-sm font-medium">Platforms</legend>
        <div className="flex flex-wrap gap-4">
          {PLATFORMS.map(({ id, label }) => (
            <label key={id} className="flex items-center gap-2 text-sm">
              <Checkbox
                id={id}
                checked={selectedPlatforms.includes(id)}
                onCheckedChange={() => togglePlatform(id)}
                aria-label={label}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      {/* Content pillar */}
      {pillars.length > 0 && (
        <div className="space-y-2">
          <Label htmlFor="content-pillar">Content Pillar (optional)</Label>
          <Select value={selectedPillar} onValueChange={setSelectedPillar}>
            <SelectTrigger id="content-pillar">
              <SelectValue placeholder="Let AI decide..." />
            </SelectTrigger>
            <SelectContent>
              {pillars.map((p) => (
                <SelectItem key={p.id} value={p.name}>
                  <span className="flex items-center gap-2">
                    {p.color && (
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: p.color }}
                      />
                    )}
                    {p.name}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Schedule date & time */}
      <div className="flex gap-3 max-w-sm">
        <div className="space-y-2">
          <Label htmlFor="schedule-date">Date</Label>
          <Input
            id="schedule-date"
            type="date"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="schedule-time">Time</Label>
          <Input
            id="schedule-time"
            type="time"
            value={scheduledTime}
            onChange={(e) => setScheduledTime(e.target.value)}
          />
        </div>
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {/* Action area — unified for both single and batch */}
      {selectedTemplate?.schedule_pattern && !captions ? (
        /* Template with schedule: show both options in one card */
        <Card>
          <CardContent className="space-y-4 pt-4">
            <div className="space-y-3">
              {/* Option 1: Create one post now */}
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || selectedPlatforms.length === 0}
                className="w-full"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Create This Post Now
                  </>
                )}
              </Button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">or</span>
                </div>
              </div>

              {/* Option 2: Schedule multiple slots */}
              <div className="flex gap-2">
                <Button
                  onClick={handleBatchSchedule}
                  disabled={isBatchGenerating || selectedPlatforms.length === 0}
                  variant="outline"
                  className="flex-1"
                >
                  {isBatchGenerating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Scheduling...
                    </>
                  ) : (
                    `Schedule ${batchWeeks} Upcoming Slots`
                  )}
                </Button>
                <Input
                  id="batch-weeks"
                  type="number"
                  min={1}
                  max={12}
                  value={batchWeeks}
                  onChange={(e) => setBatchWeeks(parseInt(e.target.value) || 1)}
                  className="w-16"
                  aria-label="Number of weeks"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Creates {batchWeeks} draft slots{" "}
                ({selectedTemplate.schedule_pattern.replace(":", " every ")}).
                Fill in details for each individually in Drafts.
              </p>
            </div>
            {batchResult && (
              <p className="text-sm text-sage-600 rounded-md bg-sage-50 px-3 py-2">
                {batchResult.created} draft slots created! Open each in Drafts to fill in details and generate captions.
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        /* Freeform or template without schedule: single generate button */
        <Button
          onClick={handleGenerate}
          disabled={isGenerating || selectedPlatforms.length === 0}
          className="w-full"
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              {selectedTemplate ? "Create This Post" : "Generate Captions"}
            </>
          )}
        </Button>
      )}

      {/* Progress */}
      {isGenerating && (
        <div className="space-y-2">
          <Progress value={undefined} className="h-2" />
          <p className="text-center text-sm text-muted-foreground">
            {statusMessage}
          </p>
          <p className="text-center text-xs text-muted-foreground animate-pulse">
            Claude is writing platform-specific captions — this usually takes 30-90 seconds.
          </p>
        </div>
      )}

      {/* Results — per-platform cards with inline iteration */}
      {captions && (
        <div className="space-y-4">
          {Object.entries(captions).map(([platform, caption]) => (
            <Card key={platform}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium capitalize">
                  {platform}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={caption}
                  onChange={(e) =>
                    setCaptions((prev) =>
                      prev ? { ...prev, [platform]: e.target.value } : prev,
                    )
                  }
                  rows={4}
                  className="resize-y font-mono text-sm"
                />

                {/* Inline iteration */}
                {contentRowId && (
                  <div className="flex gap-2">
                    <Input
                      value={platformInstructions[platform] ?? ""}
                      onChange={(e) =>
                        setPlatformInstructions((prev) => ({
                          ...prev,
                          [platform]: e.target.value,
                        }))
                      }
                      placeholder="Iteration instruction (e.g. 'Make shorter')"
                      disabled={isIterating}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleIterate(platform);
                        }
                      }}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleIterate(platform)}
                      disabled={
                        isIterating || !(platformInstructions[platform]?.trim())
                      }
                      aria-label={`Iterate ${platform}`}
                    >
                      {isIterating && iteratePlatform === platform ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <RotateCcw className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}

          {/* Actions: Save Draft + Send to Postiz */}
          <div className="space-y-2">
            {savedMessage && (
              <p className="text-sm text-sage-600 rounded-md bg-sage-50 px-3 py-2">
                {savedMessage}
              </p>
            )}
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleSaveDraft}
                disabled={!contentRowId}
              >
                <Save className="mr-2 h-4 w-4" />
                Save as Draft
              </Button>
              <SendToPostizButton captions={captions} formData={formData} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
