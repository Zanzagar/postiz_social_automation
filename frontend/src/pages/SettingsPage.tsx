import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type PlatformPublishConfig } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Settings, Loader2, Save } from "lucide-react";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["publishConfig"],
    queryFn: () => api.getPublishConfig(),
  });

  const [configs, setConfigs] = useState<PlatformPublishConfig[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data?.platforms) {
      setConfigs(data.platforms);
    }
  }, [data]);

  function updatePlatform(
    platform: string,
    update: Partial<PlatformPublishConfig>,
  ) {
    setConfigs((prev) =>
      prev.map((c) => (c.platform === platform ? { ...c, ...update } : c)),
    );
    setSaved(false);
  }

  async function handleSave() {
    setIsSaving(true);
    setSaved(false);
    try {
      await api.updatePublishConfig(configs);
      queryClient.invalidateQueries({ queryKey: ["publishConfig"] });
      setSaved(true);
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <h1 className="text-2xl font-bold text-sage-800">Settings</h1>
        <p className="text-muted-foreground">Loading...</p>
        <Skeleton className="h-32 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <div className="flex items-center gap-2">
        <Settings className="h-6 w-6 text-sage-600" />
        <h1 className="text-2xl font-bold text-sage-800">Settings</h1>
      </div>

      {/* Auto-publish section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Auto-Publish Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Configure automatic publishing per platform. When enabled, approved
            content will be scheduled for publishing after the specified delay.
          </p>

          {configs.map((config) => (
            <div
              key={config.platform}
              className="flex items-center gap-4 rounded-lg border p-3"
            >
              <Checkbox
                id={`${config.platform}-enabled`}
                checked={config.enabled}
                onCheckedChange={(checked) =>
                  updatePlatform(config.platform, {
                    enabled: checked === true,
                  })
                }
                aria-label={`${config.platform} enabled`}
              />
              <div className="flex-1">
                <Label
                  htmlFor={`${config.platform}-enabled`}
                  className="text-sm font-medium capitalize"
                >
                  {config.platform}
                </Label>
              </div>
              <div className="flex items-center gap-2">
                <Label
                  htmlFor={`${config.platform}-delay`}
                  className="text-xs text-muted-foreground"
                >
                  Delay (hrs)
                </Label>
                <Input
                  id={`${config.platform}-delay`}
                  type="number"
                  min={0}
                  max={72}
                  value={config.delay_hours}
                  onChange={(e) =>
                    updatePlatform(config.platform, {
                      delay_hours: parseInt(e.target.value) || 0,
                    })
                  }
                  className="w-20"
                  disabled={!config.enabled}
                />
              </div>
            </div>
          ))}

          <div className="flex items-center gap-3">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save
            </Button>
            {saved && (
              <span className="text-sm text-sage-600">Settings saved</span>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
