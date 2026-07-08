/**
 * Local-draft persistence for the Create flow.
 *
 * Compose state is written (debounced) to localStorage under
 * `gv-draft-create` so an in-progress post survives the 1-hour session
 * expiry and accidental reloads. Cleared after a successful
 * Save-to-Drafts / Send-to-Postiz.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { format } from "date-fns";

export type CreateStage = "compose" | "generate" | "refine";

export interface CreateDraft {
  seed: string;
  platforms: string[];
  pillar: string;
  scheduledDate: string;
  scheduledTime: string;
  mediaUrl: string;
  altText: string;
  stage: CreateStage;
  rowId: number | null;
  captions: Record<string, string>;
}

export const DRAFT_STORAGE_KEY = "gv-draft-create";
const PERSIST_DELAY_MS = 400;

export function emptyDraft(): CreateDraft {
  return {
    seed: "",
    platforms: [],
    pillar: "",
    scheduledDate: format(new Date(), "yyyy-MM-dd"),
    scheduledTime: "09:00",
    mediaUrl: "",
    altText: "",
    stage: "compose",
    rowId: null,
    captions: {},
  };
}

function restoreDraft(key: string): CreateDraft {
  const base = emptyDraft();
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return base;
    const parsed = JSON.parse(raw) as Partial<CreateDraft>;
    const draft: CreateDraft = { ...base, ...parsed };
    // Never restore into the middle of a generation stream.
    if (draft.stage === "generate") draft.stage = "compose";
    // Refine with no captions to refine makes no sense — start over.
    if (draft.stage === "refine" && Object.keys(draft.captions).length === 0) {
      draft.stage = "compose";
    }
    return draft;
  } catch {
    return base;
  }
}

export function useLocalDraft(key: string = DRAFT_STORAGE_KEY): {
  draft: CreateDraft;
  update: (patch: Partial<CreateDraft>) => void;
  clear: () => void;
} {
  const [draft, setDraft] = useState<CreateDraft>(() => restoreDraft(key));
  const isFirstRun = useRef(true);
  const skipNextPersist = useRef(false);

  useEffect(() => {
    if (isFirstRun.current) {
      isFirstRun.current = false;
      return;
    }
    if (skipNextPersist.current) {
      skipNextPersist.current = false;
      return;
    }
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(key, JSON.stringify(draft));
      } catch {
        // Storage full or unavailable — draft persistence is best-effort.
      }
    }, PERSIST_DELAY_MS);
    return () => clearTimeout(timer);
  }, [draft, key]);

  const update = useCallback((patch: Partial<CreateDraft>) => {
    setDraft((d) => ({ ...d, ...patch }));
  }, []);

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
    skipNextPersist.current = true;
    setDraft(emptyDraft());
  }, [key]);

  return { draft, update, clear };
}
