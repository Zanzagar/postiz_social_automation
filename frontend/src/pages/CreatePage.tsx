import { useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { CaptionCards } from "@/components/create/CaptionCards";
import { api, request, type GenerateRequest } from "@/lib/api";
import { Upload, Loader2, X } from "lucide-react";
import { format } from "date-fns";

const PLATFORMS = [
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "threads", label: "Threads" },
  { id: "linkedin", label: "LinkedIn" },
];

export function CreatePage() {
  const [rawText, setRawText] = useState("");
  const [mediaUrl, setMediaUrl] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [scheduledDate, setScheduledDate] = useState(
    format(new Date(), "yyyy-MM-dd"),
  );

  const [isGenerating, setIsGenerating] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [captions, setCaptions] = useState<Record<string, string> | null>(null);
  const [error, setError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  function togglePlatform(platform: string) {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform],
    );
  }

  const handleFileChange = useCallback(
    async (file: File) => {
      setUploadedFile(file);
      try {
        const result = await api.uploadFile(file);
        setMediaUrl(result.url);
      } catch {
        setError("Failed to upload file");
      }
    },
    [],
  );

  async function handleGenerate() {
    if (!rawText.trim() || selectedPlatforms.length === 0) {
      setError("Please enter text and select at least one platform.");
      return;
    }

    setError("");
    setIsGenerating(true);
    setStatusMessage("Starting generation...");
    setCaptions(null);

    const data: GenerateRequest = {
      raw_text: rawText,
      media_url: mediaUrl || null,
      platforms: selectedPlatforms,
      scheduled_date: scheduledDate,
    };

    try {
      setStatusMessage("Generating captions...");
      const result = await request<{ captions: Record<string, string> }>(
        "/api/generate-sync",
        { method: "POST", body: JSON.stringify(data) },
      );
      setCaptions(result.captions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setIsGenerating(false);
      setStatusMessage("");
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
              {uploadedFile ? uploadedFile.name : "Drop image/video or click to browse"}
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
            <Label htmlFor="media-url" className="text-xs text-muted-foreground">
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

      {/* Results */}
      {captions && (
        <CaptionCards
          captions={captions}
          onCaptionsChange={setCaptions}
          formData={formData}
        />
      )}
    </div>
  );
}
