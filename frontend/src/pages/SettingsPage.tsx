import { useState } from "react";
import { Columns3, MessageSquare, Send, Settings, Share2 } from "lucide-react";

import { PageHeader, PastureTabs, type PastureTabItem } from "@/components/pasture";
import { PublishingSection } from "@/components/settings/PublishingSection";
import { BrandVoiceSection } from "@/components/settings/BrandVoiceSection";
import { PillarsSection } from "@/components/settings/PillarsSection";
import { PlatformsSection } from "@/components/settings/PlatformsSection";

type SectionId = "publishing" | "brand" | "pillars" | "platforms";

const SECTIONS: PastureTabItem[] = [
  { id: "publishing", label: "Publishing", icon: Send },
  { id: "brand", label: "Brand voice", icon: MessageSquare },
  { id: "pillars", label: "Pillars", icon: Columns3 },
  { id: "platforms", label: "Platforms", icon: Share2 },
];

/**
 * Settings — "Your farm, your rules." Left rail of sections, with the
 * Publishing (blessing & release) section as the default view.
 */
export function SettingsPage() {
  const [section, setSection] = useState<SectionId>("publishing");

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        greeting="Settings"
        title="Your farm, your rules."
        subtitle="Brand voice, pillars, schedules, and the people who tend this account."
        icon={Settings}
      />
      <div className="mx-auto flex max-w-[1180px] items-start gap-8 px-8 py-6">
        <PastureTabs
          variant="rail"
          items={SECTIONS}
          value={section}
          onChange={(id) => setSection(id as SectionId)}
          aria-label="Settings sections"
          className="w-44 shrink-0"
        />
        <div className="min-w-0 flex-1">
          {section === "publishing" && (
            <>
              <div className="mb-5">
                <div className="t-title-sm ink font-semibold">Publishing</div>
                <p className="t-caption ink-muted mt-0.5">
                  Decide what releases on its own, and what waits for a hand on
                  the gate.
                </p>
              </div>
              <PublishingSection />
            </>
          )}
          {section === "brand" && <BrandVoiceSection />}
          {section === "pillars" && <PillarsSection />}
          {section === "platforms" && <PlatformsSection />}
        </div>
      </div>
    </div>
  );
}
