import type * as React from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";

interface GVSheetProps {
  title: string;
  badge?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
}

/**
 * Right-side overlay sheet — the canonical modal surface (hosts the
 * ContentEditor). Radix Dialog provides the portal, scrim, focus trap,
 * Esc-to-close, and role=dialog/aria-modal semantics.
 */
export function GVSheet({
  title,
  badge,
  onClose,
  children,
  footer,
  width = 560,
}: GVSheetProps) {
  return (
    <DialogPrimitive.Root
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-sage-900/30" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="bg-card fixed top-0 right-0 bottom-0 z-40 flex max-w-full flex-col border-l outline-none"
          style={{ width, boxShadow: "var(--shadow-lg)" }}
        >
          <div className="border-hair-b flex shrink-0 items-center gap-3 px-6 py-4">
            {badge}
            <DialogPrimitive.Title className="t-title ink flex-1 truncate font-serif">
              {title}
            </DialogPrimitive.Title>
            <DialogPrimitive.Close asChild>
              <Button size="iconSm" variant="ghost" aria-label="Close">
                <X size={14} strokeWidth={1.75} aria-hidden="true" />
              </Button>
            </DialogPrimitive.Close>
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
          {footer && (
            <div
              className="shrink-0 px-6 py-4"
              style={{
                background: "color-mix(in oklab, var(--surface-warm) 60%, transparent)",
                borderTop: "1px solid color-mix(in oklab, var(--ink) 12%, transparent)",
              }}
            >
              {footer}
            </div>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
