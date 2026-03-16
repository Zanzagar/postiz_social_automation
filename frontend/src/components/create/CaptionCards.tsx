import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { RepromptRequest, GenerateRequest } from "@/lib/api";
import { Loader2, Send, RefreshCw } from "lucide-react";

const platformLabels: Record<string, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  tiktok: "TikTok",
  threads: "Threads",
  linkedin: "LinkedIn",
};

interface CaptionCardsProps {
  captions: Record<string, string>;
  onCaptionsChange: (captions: Record<string, string>) => void;
  formData: GenerateRequest;
}

export function CaptionCards({
  captions,
  onCaptionsChange,
  formData,
}: CaptionCardsProps) {
  const [feedback, setFeedback] = useState("");
  const [isReprompting, setIsReprompting] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);

  async function handleReprompt() {
    if (!feedback.trim()) return;
    setIsReprompting(true);
    try {
      const data: RepromptRequest = { ...formData, feedback };
      const result = await api.reprompt(data);
      onCaptionsChange(result.captions);
      setFeedback("");
    } finally {
      setIsReprompting(false);
    }
  }

  async function handleSendToPostiz() {
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
    <div className="space-y-4">
      {Object.entries(captions).map(([platform, caption]) => (
        <Card key={platform}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {platformLabels[platform] ?? platform}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={caption}
              onChange={(e) =>
                onCaptionsChange({ ...captions, [platform]: e.target.value })
              }
              rows={4}
              className="resize-y"
            />
          </CardContent>
        </Card>
      ))}

      {/* Re-prompt */}
      <div className="flex gap-2">
        <Input
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Feedback for regeneration..."
          disabled={isReprompting}
        />
        <Button
          variant="outline"
          onClick={handleReprompt}
          disabled={isReprompting || !feedback.trim()}
        >
          {isReprompting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          <span className="ml-1.5 hidden sm:inline">Regenerate</span>
        </Button>
      </div>

      {/* Send to Postiz */}
      <Button onClick={handleSendToPostiz} disabled={isSending} className="w-full">
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
