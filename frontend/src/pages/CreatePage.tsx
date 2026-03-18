import { useState, useCallback, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  api,
  request,
  type GenerateRequest,
  type Template,
} from "@/lib/api";
import {
  Upload,
  Loader2,
  X,
  FileText,
  RotateCcw,
  Send,
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
    <div className="space-y-2">
      <Button onClick={handleSend} disabled={isSending} className="w-full">
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
    </div>
  );
}

export function CreatePage() {
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

  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Template handling ---

  function handleTemplateSelect(template: Template) {
    setSelectedTemplate(template);
    setRawText(template.raw_text_template ?? "");
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

  const formData: GenerateRequest = {
    raw_text: rawText,
    media_url: mediaUrl || null,
    platforms: selectedPlatforms,
    scheduled_date: scheduledDate,
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-sage-800">Create & Generate</h1>

      {/* Template selector */}
      {templates.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <FileText className="h-4 w-4" />
              Template
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
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
                    Clear
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
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {templates.map((t) => (
                  <Button
                    key={t.id}
                    variant="outline"
                    size="sm"
                    onClick={() => handleTemplateSelect(t)}
                  >
                    {t.name}
                  </Button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
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

      {/* Caption / text input */}
      <div className="space-y-2">
        <Label htmlFor="raw-text">Raw Text</Label>
        <Textarea
          id="raw-text"
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Describe what you want to post..."
          rows={4}
          maxLength={2000}
        />
        <p className="text-right text-xs text-muted-foreground">
          {rawText.length}/2000
        </p>
      </div>

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

      {/* Schedule date */}
      <div className="space-y-2">
        <Label htmlFor="schedule-date">Schedule Date</Label>
        <Input
          id="schedule-date"
          type="date"
          value={scheduledDate}
          onChange={(e) => setScheduledDate(e.target.value)}
        />
      </div>

      {/* Error */}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}

      {/* Generate */}
      <Button
        onClick={handleGenerate}
        disabled={isGenerating}
        className="w-full"
      >
        {isGenerating ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Generating...
          </>
        ) : selectedTemplate ? (
          "Generate from Template"
        ) : (
          "Generate Captions"
        )}
      </Button>

      {/* Progress */}
      {isGenerating && statusMessage && (
        <div className="space-y-2">
          <Progress value={undefined} className="h-2" />
          <p className="text-center text-sm text-muted-foreground">
            {statusMessage}
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

          {/* Send to Postiz */}
          <SendToPostizButton captions={captions} formData={formData} />
        </div>
      )}
    </div>
  );
}
